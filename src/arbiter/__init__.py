import os
import glob
import sys
import time
import json
from eth_abi import decode_single
from heapq import heappush, heappop
from uuid import UUID
import requests
from web3.auto import w3
import aiohttp
import websockets

KEYDIR = "./keystore"

polyswarmd = os.environ.get("POLYSWARMD_HOST")
port = os.environ.get("POLYSWARMD_PORT")
address = os.environ.get("ADDRESS")
password = os.environ.get("PASSWORD")
chain = os.environ.get("CHAIN")

ws_url = "ws://{0}:{1}/events".format(polyswarmd, port)
base_url = "http://{0}:{1}".format(polyswarmd, port)

def check_address(address):
    return w3.isAddress(address)

def check_uuid(uuid):
    # Check that the uuid i pass is valid.
    try:
        converted = UUID(uuid, version=4)
    except ValueError:
        return False
    return str(converted) == uuid

def check_int_uuid(uuid):
    # Check that the uuid i pass is valid.
    try:
        converted = UUID(int=uuid, version=4)
    except ValueError:
        return False
    return converted.int == uuid

def decrypt_key(addr, secret):
    os.chdir(KEYDIR)
    if addr.startswith('0x'):
        temp = addr[2:]
    else:
        temp = addr
    possible_matches = glob.glob("*" + temp)
    os.chdir('..')
    if len(possible_matches) == 1:
        with open(os.path.join(KEYDIR, possible_matches[0])) as keyfile:
            encrypted = keyfile.read()
            return w3.eth.account.decrypt(encrypted, secret)
    return None

async def get_reveal_window(session):
    url = "{0}/bounties/window/reveal".format(base_url)
    async with session.get(url, params=[("chain", chain)]) as response:
        message = await response.json()
        if message['status'] == "OK":
            return message['result']['blocks']

async def get_vote_window(session):
    url = "{0}/bounties/window/vote".format(base_url)
    async with session.get(url, params=[("chain", chain)]) as response:
        message = await response.json()
        if message['status'] == "OK":
            return message['result']['blocks']

# This will settle any bounties
async def post_settle(session, isTest, heap, blocknumber):
    settled = []
    while heap:
        expiration = heap[0][0]
        guid = heap[0][1]
        url = "{0}/bounties/{1}/settle".format(base_url, guid)
        params = [("account", address), ("chain", chain)]
        #  For any bounties blocknumber exceeds the reveal & vote windows... settle
        if int(expiration) < blocknumber:
            async with session.post(url, params=params) as response:
                message = await response.json()
                transactions = message["result"]["transactions"]
                if verify_settle(guid, transactions):
                    response = await post_transactions(session, transactions)
                    if "errors" not in message["result"]:
                        heappop(heap)
                        settled.append(guid)
                    else:
                        print_error(isTest, "Failed to settle bounty.", 13)
                else:
                    print_error(True, "Settle transaction does not match expectations", 1)
        else:
            break
    return settled

async def post_stake(session):
    minimumStake = 10000000000000000000000000
    url = "{0}/balances/{1}/staking/total".format(base_url, address)
    async with session.get(url, params=[("chain", chain)]) as query_response:
        message = await query_response.json()
        if message["status"] != "OK":
            return False

        currentStake = int(message["result"])
        if minimumStake <= currentStake:
            return True

        amount = str(minimumStake - currentStake)
        deposit_url = "{0}/staking/deposit".format(base_url)
        params = [("account", address), ("chain", chain)]
        data = {"amount": amount}
        async with session.post(deposit_url, params=params, json=data) as deposit_response:
            message = await deposit_response.json()
            transactions = message["result"]["transactions"]
            if verify_stake(amount, transactions):
                response = await post_transactions(session, transactions)
                return message["status"] == "OK"
    # We exit here, no need to return
    print_error(True, "Staking transactions do not match expectations", 1)

async def post_transactions(session, transactions):
    url = "{0}/transactions".format(base_url)
    signed_transactions = []
    key = decrypt_key(address, password)
    for transaction in transactions:
        signed = w3.eth.account.signTransaction(transaction, key)
        raw = bytes(signed["rawTransaction"]).hex()
        signed_transactions.append(raw)
        async with session.post(url, json={"transactions": signed_transactions}) as response:
            return await response.json()

async def post_vote(session, isTest, heap, blocknumber):
    success = True
    while heap:
        expiration = heap[0][0]
        guid = heap[0][1]
        verdicts = heap[0][2]
        url = "{0}/bounties/{1}/vote".format(base_url, guid)
        params = [("account", address), ("chain", chain)]
        data = {"verdicts": verdicts, "valid_bloom": True}
        #  For any bounties blocknumber exceeds the reveal & vote windows... settle
        if int(expiration) < blocknumber:
            async with session.post(url, params=params, json=data) as response:
                message = await response.json()
                transactions = message["result"]["transactions"]
                if verify_vote(guid, verdicts, transactions):
                    response = await post_transactions(session, transactions)
                    if "errors" not in message["result"]:
                        heappop(heap)
                    else:
                        success = False
                else:
                    print_error(True, "Vote transaction does not match expectations", 1)
        else:
            break;

def print_error(test, message, code):
    print(message)
    if test:
        sys.exit(code)

def verify_vote(guid, verdicts, transactions):
    (vote_guid, vote_verdicts, validBloom) = decode_single("(uint256,uint256,bool)", w3.toBytes(hexstr=transactions[0]["data"][10:]))
    verdicts_int = sum([1 << n if b else 0 for n, b in enumerate(verdicts)])
    return check_int_uuid(vote_guid) and check_uuid(guid) and str(UUID(int=vote_guid, version=4)) == guid and verdicts_int == vote_verdicts

def verify_settle(guid, transactions):
    settle_guid = decode_single("uint256", w3.toBytes(hexstr=transactions[0]["data"][10:]))
    return check_int_uuid(settle_guid) and check_uuid(guid) and str(UUID(int=settle_guid, version=4)) == guid

def verify_stake(amount, transactions):
    transaction_count = len(transactions)
    # We should add in address validation later
    (address, approved) = decode_single("(address,uint256)", bytes.fromhex(transactions[0]["data"][10:]))
    stake = decode_single("uint256", w3.toBytes(hexstr=transactions[1]["data"][10:]))
    return transaction_count == 2 and check_address(address) and int(stake) == int(amount) and int(approved) == int(amount)

async def get_artifacts(session, isTest, uri):
    url = "{0}/artifacts/{1}".format(base_url, uri)
    async with session.get(url) as response:
        decoded = await response.json()
        if decoded["status"] == "OK":
            files = decoded["result"]
            return files
    return list()

async def get_artifact_contents(session, isTest, uri, index):
    url = "{0}/artifacts/{1}/{2}".format(base_url, uri, index)
    async with session.get(url) as response:
        if response.status == 200:
            return bytearray(await response.read())
        print_error(isTest, "Failed to retrieve files from IPFS.", 12)
        return None

# Listen to polyswarmd /bounties/pending route to find expired bounties
async def listen_and_arbitrate(isTest, backend):
    """Listens for bounties & vote reveals to establish ground truth"""
    if not check_address(address):
        # Always exit. Unusable with a bad address
        print_error(True, "Invalid address %s" % address, 7)

    to_settle = []
    to_vote = []

    async with aiohttp.ClientSession() as session:
        if not await post_stake(session):
            # Always exit, because it is unusable without staking
            print_error(True, "Failed to Stake Arbiter.", 9)
        # Get the window length for phases
        voting_window = await get_vote_window(session)
        reveal_window = await get_reveal_window(session)
        if not voting_window or not get_reveal_window:
            # Cannot vote/settle without this info
            print_error(True, "Failed to get bounty windows.", 14)
        async with websockets.connect(ws_url) as ws:
            while True:
                message = json.loads(await ws.recv())
                if message["event"] == "block":
                    await post_vote(session, isTest, to_vote, message["data"]["number"])
                    settled = await post_settle(session, isTest, to_settle, message["data"]["number"])
                    if settled and isTest:
                        print_error(True, "Test exited when some bounties were settled", 0)
                elif message["event"] == "bounty":
                    bounty = message["data"]
                    if not check_uuid(bounty["guid"]):
                        print_error(isTest, "Bad GUID: %s" % bounty["guid"], 10)
                        continue

                    verdicts = []
                    artifacts = await get_artifacts(session, isTest, bounty["uri"])
                    for i, f in enumerate(artifacts):
                        file = await get_artifact_contents(session, isTest, bounty["uri"], i)
                        if file is None:
                            print_error(isTest, "Failed to retrieve files from IPFS.", 12)
                            # If not exiting, just send zero
                            verdict.append(False)

                        verdicts.append(await backend.scan(file))
                    # Add bounty to vote & settle queues (Should take a func & number tuple)
                    heappush(to_vote, (int(bounty["expiration"])+reveal_window, bounty["guid"], verdicts))
                    heappush(to_settle, (int(bounty["expiration"])+reveal_window+voting_window, bounty["guid"]))
