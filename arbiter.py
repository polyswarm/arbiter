import os
import glob
import sys
import argparse
import time
import importlib
from eth_abi import decode_single
from heapq import heappush, heappop
from uuid import UUID
import requests
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware

KEYDIR = "./keystore"

polyswarmd = os.environ.get("POLYSWARM_HOST")
geth = os.environ.get("GETH")
address = os.environ.get("ADDRESS")
password = os.environ.get("PASSWORD")
chain = os.environ.get("CHAIN")

w3 = Web3(HTTPProvider(geth))
w3.middleware_stack.inject(geth_poa_middleware, layer=0)

def check_uuid(uuid):
    # Check that the uuid i pass is valid.
    try:
        converted = UUID(uuid, version=4)
    except ValueError:
        return False
    return str(converted) == uuid

def check_address(address):
    return w3.isAddress(address)

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

# This will settle any bounties
def settle_bounties(session, isTest, heap, blocknumber):
    settled = []
    while heap:
        head = heap[0]

        #  For any bounties blocknumber exceeds the reveal & vote windows... settle
        if int(head[0]) < blocknumber:
            guid = head[1]
            response = session.post(polyswarmd + "/bounties/" + guid + "/settle", params={"account": address, "chain": chain})
            transactions = response.json()["result"]["transactions"]
            if verify_settle(guid, transactions):
                response = sign_transactions(session, transactions)
                if "errors" not in response.json()["result"]:
                    heappop(heap)
                    settled.append(guid)
                else:
                    print_error(isTest, "Failed to settle bounty.", 13)
            else:
                print_error(True, "Settle transaction does not match expectations", 1)
        else:
            break
    return settled

def sign_transactions(session, transactions):
    signed_transactions = []
    key = decrypt_key(address, password)
    for transaction in transactions:
        signed = w3.eth.account.signTransaction(transaction, key)
        raw = bytes(signed["rawTransaction"]).hex()
        signed_transactions.append(raw)
    return session.post(polyswarmd + "/transactions", json={"transactions": signed_transactions})

def stake(session):
    minimumStake = 10000000000000000000000000
    response = session.get(polyswarmd + "/balances/" + address + "/staking/total", params={"chain": chain})
    if response.json()["status"] != "OK":
        return False

    currentStake = int(response.json()["result"])
    if minimumStake <= currentStake:
        return True

    amount = str(minimumStake - currentStake)
    response = session.post(polyswarmd + "/staking/deposit", params={"account": address, "chain": chain}, json={"amount": amount})
    transactions = response.json()["result"]["transactions"]
    if verify_stake(amount, transactions):
        response = sign_transactions(session, transactions)
        return response.json()["status"] == "OK"
    # We exit here, no need to return
    print_error(True, "Staking transactions do not match expectations", 1)

def verify_vote(guid, verdicts, transactions):
    return True

def verify_settle(guid, transactions):
    return True

def verify_stake(amount, transactions):
    transaction_count = len(transactions)
    # We should add in address validation later
    (address, approved) = decode_single("(address,uint256)", bytes.fromhex(transactions[0]["data"][10:]))
    stake = decode_single("uint256", w3.toBytes(hexstr=transactions[1]["data"][10:]))
    return transaction_count == 2 and check_address(address) and int(stake) == int(amount) and int(approved) == int(amount)

def vote(session, guid, verdicts):
    response = session.post(polyswarmd + "/bounties/" + guid + "/vote", params={"account": address, "chain": chain}, json={"verdicts": verdicts, "valid_bloom": True})

    transactions = response.json()["result"]["transactions"]
    if verify_vote(guid, verdicts, transactions):
        response = sign_transactions(session, transactions)
        return "errors" not in response.json()["result"]
    else:
        print_error(True, "Vote transaction does not match expectations", 1)

# Listen to polyswarmd /bounties/pending route to find expired bounties
def listen_and_arbitrate(isTest, backend):
    session = requests.Session()
    if not stake(session):
        # Always exit, because it is unusable without staking
        print_error(True, "Failed to Stake Arbiter.", 9)
    # to_settle is a head of bounty objects ordered by block number when then assertion reveal phase ends
    to_settle = []
    voted_bounties = set()
    voting_window = get_vote_window()
    reveal_window = get_reveal_window()

    if not voting_window or not get_reveal_window:
        print_error(isTest, "Failed to get bounty windows.", 14)

    while True:
        # Check bounties route
        response = session.get(polyswarmd + "/bounties/pending", params={"chain": chain})
        decoded = response.json()
        if decoded["status"] == "OK":
            bounties = response.json()["result"]
            for bounty in bounties:
                if bounty["guid"] not in voted_bounties:
                    if not check_uuid(bounty["guid"]):
                        print_error(isTest, "Bad GUID: %s" % bounty["guid"], 10)
                        continue
                    # Vote
                    verdicts = backend.scan(polyswarmd, bounty["uri"])
                    if verdicts:
                        # If successfully volted, add to heap to be settled
                        if vote(session, bounty["guid"], verdicts):
                            # Mark voted
                            voted_bounties.add(bounty["guid"])
                            # Add to heap so it can be settled
                            heappush(to_settle, (int(bounty["expiration"]) + voting_window + reveal_window, bounty["guid"]))
                        else:
                            print_error(isTest, "Failed to submit vote.", 11)
                    else:
                        print_error(isTest, "Failed to retrieve files from IPFS.", 12)

            blocknumber = w3.eth.blockNumber
            settled = settle_bounties(session, isTest, to_settle, blocknumber)
            for b in settled:
                voted_bounties.remove(b)
            if settled and isTest:
                print_error(True, "Test exited when some bounties were settled", 0)
        time.sleep(1)

def print_error(test, message, code):
    print(message)
    if test:
        sys.exit(code)

def get_vote_window():
    response = requests.get(polyswarmd + "/bounties/window/vote?chain=" + chain)
    if response.json()['status'] == "OK":
        return response.json()['result']['blocks']

def get_reveal_window():
    response = requests.get(polyswarmd + "/bounties/window/reveal?chain=" + chain)
    if response.json()['status'] == "OK":
        return response.json()['result']['blocks']

def main():
    sys.path.append('./backends')
    parser = argparse.ArgumentParser(description="Run an arbiter backend.")

    parser.add_argument("--backend", help="Select the backend", default="verbatim")
    parser.add_argument("--test", help="Exits on successful settle", action="store_true",)
    args = parser.parse_args()

    backend = importlib.import_module(args.backend)
    if not check_address(address):
        # Always exit. Unusable with a bad address
        print_error(True, "Invalid address %s" % address, 7)
    listen_and_arbitrate(args.test, backend)

if __name__ == "__main__":
    main()
