import asyncio
import os
import glob
import logging
import sys
import time
import json
from eth_abi import decode_single
from arbiter.scheduler import SchedulerQueue
from arbiter.scheduler import SchedulerTask

from uuid import UUID
import requests
from web3.auto import w3
import aiohttp
import websockets

logging.basicConfig(level='INFO')

KEYDIR = os.environ.get("KEYDIR", "./keystore")
polyswarmd = os.environ.get("POLYSWARMD_HOST")
port = os.environ.get("POLYSWARMD_PORT")
address = os.environ.get("ADDRESS")
password = os.environ.get("PASSWORD")
api_key = os.environ.get("API_KEY")
chain = os.environ.get("CHAIN")

ws_url = "ws://{0}:{1}/events".format(polyswarmd, port)
base_url = "http://{0}:{1}".format(polyswarmd, port)

base_nonce_lock = asyncio.Lock()
base_nonce = 0

def check_response(response):
    """Check the status of responses from polyswarmd

    Args:
        response: Response dict parsed from JSON from polyswarmd
    Returns:
        (bool): True if successful else False
    """
    status = response.get('status')
    ret = status and status == 'OK'
    if not ret:
        logging.error('Received unexpected failure response from polyswarmd: %s', response)
    return ret


def check_address(address):
    return w3.isAddress(address)

def check_uuid(uuid):
    """Check that the uuid i pass is valid."""
    try:
        converted = UUID(uuid, version=4)
    except ValueError:
        return False

    return str(converted) == uuid

def check_int_uuid(uuid):
    """Check that the int uuid i pass is valid."""
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

async def get_base_nonce(session):
    url = "{0}/nonce".format(base_url)
    params = [("account", address), ("chain", chain)]
    global base_nonce
    async with base_nonce_lock:
        async with session.get(url, params=params) as response:
            message = await response.json()
            if not check_response(message):
                fatal_error(True, 'Invalid nonce response', 1)

            base_nonce = message['result']
            logging.info('Got base nonce of: %s %s', base_nonce, message)

async def get_reveal_window(session):
    url = "{0}/bounties/window/reveal".format(base_url)
    params = [("account", address), ("chain", chain)]
    async with session.get(url, params=params) as response:
        message = await response.json()
        if not check_response(message):
            fatal_error(True, 'Invalid reveal window response', 1)

        return int(message['result']['blocks'])

async def get_vote_window(session):
    url = "{0}/bounties/window/vote".format(base_url)
    params = [("account", address), ("chain", chain)]
    async with session.get(url, params=params) as response:
        message = await response.json()
        if not check_response(message):
            fatal_error(True, 'Invalid vote window response', 1)

        return int(message['result']['blocks'])

# This will settle any bounties
async def post_settle(session, isTest, guid):
    url = "{0}/bounties/{1}/settle".format(base_url, guid)

    global base_nonce
    async with base_nonce_lock:
        params = [("account", address), ("chain", chain), ("base_nonce", str(base_nonce))]
        async with session.post(url, params=params) as response:
            message = await response.json()

        if not check_response(message):
            fatal_error(True, 'Invalid settle response', 1)
            return False

        transactions = message["result"]["transactions"]
        if not verify_settle(guid, transactions):
            fatal_error(True, 'Invalid settle transactions', 1)
            return False

        base_nonce += len(transactions)

    logging.info('Firing off settle transactions: %s %s', guid, transactions)
    asyncio.ensure_future(post_transactions(session, guid, {}, transactions))
    return True

async def post_stake(session):
    minimumStake = 10000000000000000000000000
    url = "{0}/balances/{1}/staking/total".format(base_url, address)
    params = [("account", address), ("chain", chain)]
    async with session.get(url, params=params) as query_response:
        message = await query_response.json()

    if not check_response(message):
        return False

    currentStake = int(message["result"])
    if minimumStake <= currentStake:
        return True

    amount = str(minimumStake - currentStake)
    deposit_url = "{0}/staking/deposit".format(base_url)
    data = {"amount": amount}

    global base_nonce
    async with base_nonce_lock:
        params = [("account", address), ("chain", chain), ("base_nonce", str(base_nonce))]
        async with session.post(deposit_url, params=params, json=data) as deposit_response:
            message = await deposit_response.json()
            if not check_response(message):
                fatal_error(True, 'Invalid stake response', 1)
                return False

            transactions = message["result"]["transactions"]
            if not verify_stake(amount, transactions):
                fatal_error(True, 'Invalid stake transasctions', 1)
                return False

            base_nonce += len(transactions)

    logging.info('Awaiting stake transactions: %s', transactions)
    return await post_transactions(session, '', data, transactions)

# This can be awaited on for initialization transactions (e.g. staking), but
# should be called asynchronously with e.g. asyncio.ensure_future once we enter
# the main event loop
async def post_transactions(session, guid, data, transactions):
    url = "{0}/transactions".format(base_url)
    signed_transactions = []
    key = decrypt_key(address, password)
    for transaction in transactions:
        signed = w3.eth.account.signTransaction(transaction, key)
        raw = bytes(signed["rawTransaction"]).hex()
        signed_transactions.append(raw)
    params = [("account", address), ("chain", chain)]
    async with session.post(url, params=params, json={"transactions": signed_transactions}) as response:
        transaction_response = await response.json()

    if not check_response(transaction_response):
        fatal_error(True, 'Invalid transaction response', 1)
        return False

    if "errors" in transaction_response["result"]:
        logging.error('Transaction failed: %s %s, %s', guid, data, transaction_response)
        fatal_error(True, "Failed to send transactions.", 13)
        return False

    logging.info('Received transaction events: %s %s', guid, transaction_response)
    return True

async def post_vote(session, isTest, guid, verdicts):
    url = "{0}/bounties/{1}/vote".format(base_url, guid)
    data = {"verdicts": verdicts, "valid_bloom": True}

    global base_nonce
    async with base_nonce_lock:
        params = [("account", address), ("chain", chain), ("base_nonce", str(base_nonce))]
        async with session.post(url, params=params, json=data) as response:
            message = await response.json()
            if not check_response(message):
                fatal_error(True, 'Invalid vote response', 1)
                return False

            transactions = message["result"]["transactions"]
            if not verify_vote(guid, verdicts, transactions):
                fatal_error(True, 'Invalid vote transasctions', 1)
                return False

            base_nonce += len(transactions)

    logging.info('Firing off vote transactions: %s %s', guid, transactions)
    asyncio.ensure_future(post_transactions(session, guid, data, transactions))
    return True

def fatal_error(test, message, code):
    if test:
        logging.error('Test mode fail: %s, exiting with %s', message, code)
        sys.exit(code)
    else:
        logging.error('Failure detected: %s, code: %s', message, code)

def verify_vote(guid, verdicts, transactions):
    (vote_guid, vote_verdicts, validBloom) = decode_single("(uint256,uint256,bool)", w3.toBytes(hexstr=transactions[0]["data"][10:]))
    verdicts_int = sum([1 << n if b else 0 for n, b in enumerate(verdicts)])
    transaction_count = len(transactions)
    return transaction_count == 1 and check_int_uuid(vote_guid) and check_uuid(guid) and str(UUID(int=vote_guid, version=4)) == guid and verdicts_int == vote_verdicts

def verify_settle(guid, transactions):
    settle_guid = decode_single("uint256", w3.toBytes(hexstr=transactions[0]["data"][10:]))
    transaction_count = len(transactions)
    return transaction_count == 1 and check_int_uuid(settle_guid) and check_uuid(guid) and str(UUID(int=settle_guid, version=4)) == guid

def verify_stake(amount, transactions):
    transaction_count = len(transactions)
    # We should add in address validation later
    (address, approved) = decode_single("(address,uint256)", bytes.fromhex(transactions[0]["data"][10:]))
    stake = decode_single("uint256", w3.toBytes(hexstr=transactions[1]["data"][10:]))
    return transaction_count == 2 and check_address(address) and int(stake) == int(amount) and int(approved) == int(amount)

async def get_artifacts(session, isTest, uri):
    url = "{0}/artifacts/{1}".format(base_url, uri)
    params = [("account", address), ("chain", chain)]
    async with session.get(url, params=params) as response:
        decoded = await response.json()

    if not check_response(decoded):
        return []

    return decoded["result"]

async def get_artifact_contents(session, isTest, uri, index):
    url = "{0}/artifacts/{1}/{2}".format(base_url, uri, index)
    params = [("account", address), ("chain", chain)]
    async with session.get(url, params=params) as response:
        if response.status == 200:
            return bytearray(await response.read())

        fatal_error(isTest, "Failed to retrieve files from IPFS.", 12)
        return None

# Listen to polyswarmd /bounties/pending route to find expired bounties
async def listen_and_arbitrate(isTest, backend):
    """Listens for bounties & vote reveals to establish ground truth"""
    if not check_address(address):
        # Always exit. Unusable with a bad address
        fatal_error(True, "Invalid address %s" % address, 7)

    scheduler = SchedulerQueue()
    scanner = backend.Scanner()
    headers = {'Authorization': api_key} if api_key else {}
    async with aiohttp.ClientSession(headers=headers) as session:
        # Get base_nonce and bounty registry parameters
        await get_base_nonce(session)
        voting_window = await get_vote_window(session)
        reveal_window = await get_reveal_window(session)

        if not voting_window or not get_reveal_window:
            # Cannot vote/settle without this info
            fatal_error(True, "Failed to get bounty windows.", 14)

        if not await post_stake(session):
            # Always exit, because it is unusable without staking
            fatal_error(True, "Failed to Stake Arbiter.", 9)

        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            while True:
                message = json.loads(await ws.recv())
                if message["event"] == "block":
                    number = message["data"]["number"]
                    if number % 100 == 0:
                        logging.info('Block %s', number)

                    asyncio.get_event_loop().create_task(scheduler.execute_scheduled(number))
                elif message["event"] == "bounty":
                    bounty = message["data"]
                    asyncio.get_event_loop().create_task(handle_bounty(isTest, session, scheduler, reveal_window, voting_window, scanner, bounty))

async def handle_bounty(isTest, session, scheduler, reveal_window, voting_window, scanner, bounty):
    logging.info('Received bounty: %s', bounty)
    if not check_uuid(bounty["guid"]):
        fail_test(isTest, "Bad GUID: %s" % bounty["guid"], 10)
        return

    verdicts = []
    artifacts = await get_artifacts(session, isTest, bounty["uri"])
    for i, f in enumerate(artifacts):
        file = await get_artifact_contents(session, isTest, bounty["uri"], i)
        if file is None:
            fail_test(isTest, "Failed to retrieve files from IPFS.", 12)
            # If not exiting, just send zero
            verdict.append(False)
            return

        verdicts.append(await scanner.scan(file))

# Create vote task
    vote_args = {
        "priority": int(bounty["expiration"])+reveal_window,
        "function": post_vote,
        "args": {"session": session, "isTest": isTest, "guid": bounty["guid"], "verdicts": verdicts}
    }

    vote_task = SchedulerTask(**vote_args)
    await scheduler.schedule(vote_task)

    # Create settle task
    settle_args = {
        "priority": int(bounty["expiration"])+reveal_window+voting_window,
        "function": post_settle,
        "args": {"session": session, "isTest": isTest, "guid": bounty["guid"]}
    }

    settle_task = SchedulerTask(**settle_args)
    await scheduler.schedule(settle_task)
