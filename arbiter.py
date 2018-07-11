import os
import glob
import sys
import argparse
import time
import importlib
from heapq import heappush, heappop
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

def decrypt_key(addr, secret):
    orig = os.getcwd()
    os.chdir(KEYDIR)
    if addr.startswith('0x'):
        temp = addr[2:]
    else:
        temp = addr
    possible_matches = glob.glob("*" + temp)
    os.chdir(orig)
    if len(possible_matches) == 1:
        with open(KEYDIR + "/" + possible_matches[0]) as keyfile:
            encrypted = keyfile.read()
            return w3.eth.account.decrypt(encrypted, secret)
    return None

# This will settle any bounties
def settle_bounties(heap, blocknumber):
    settled = []
    while heap:
        head = heap[0]

        #  For any bounties blocknumber exceeds the reveal & vote windows... settle
        if int(head[0]) < blocknumber:
            guid = head[1]
            response = requests.post(polyswarmd + "/bounties/" + guid + "/settle?account=" + address + "&chain=" + chain)
            transactions = response.json()["result"]["transactions"]
            response = sign_transactions(transactions)

            if "errors" not in response.json()["result"]:
                heappop(heap)
                settled.append(guid)
            else:
                print("Failed to settle bounty.")
                sys.exit(13)
        else:
            break
    return settled

def vote(guid, verdicts):
    response = requests.post(polyswarmd + "/bounties/" + guid + "/vote?account=" + address + "&chain=" + chain, json={"verdicts": verdicts, "valid_bloom": True})

    transactions = response.json()["result"]["transactions"]
    response = sign_transactions(transactions)
    return "errors" not in response.json()["result"]

def sign_transactions(transactions):
    signed_transactions = []
    key = decrypt_key(address, password)
    for transaction in transactions:
        signed = w3.eth.account.signTransaction(transaction, key)
        raw = bytes(signed["rawTransaction"]).hex()
        signed_transactions.append(raw)
    return requests.post(polyswarmd + "/transactions", json={"transactions": signed_transactions})

# Listen to polyswarmd /bounties/pending route to find expired bounties
def listen_and_arbitrate(test, backend):
    if not stake():
        print("Failed to Stake Arbiter.")
        sys.exit(14)
    # to_settle is a head of bounty objects ordered by block number when then assertion reveal phase ends
    to_settle = []
    voted_bounties = set()
    while True:
        # Check bounties route
        response = requests.get(polyswarmd + "/bounties/pending?chain=" + chain)
        decoded = response.json()
        if decoded["status"] == "OK":
            bounties = response.json()["result"]
            for bounty in bounties:
                if bounty["guid"] not in voted_bounties:
                    verdicts = backend.scan(polyswarmd, bounty["uri"])
                    if verdicts:
                        if vote(bounty["guid"], verdicts):
                            # Mark voted
                            voted_bounties.add(bounty["guid"])
                            # If successfully voted, add to heap to be settled
                            heappush(to_settle, (int(bounty["expiration"]) + 50, bounty["guid"]))
                        else:
                            print("Failed to submit vote.")
                            sys.exit(11)

            blocknumber = w3.eth.blockNumber
            settled = settle_bounties(to_settle, blocknumber)
            for b in settled:
                voted_bounties.remove(b)
            if settled and test:
                print("Test exited when some bounties were settled")
                sys.exit(0)
        time.sleep(1)

def stake():
    minimumStake = 10000000000000000000000000
    response = requests.get(polyswarmd + "/balances/" + address + "/staking/total?chain=" + chain)
    if response.json()["status"] != "OK":
        return False

    currentStake = int(response.json()["result"])
    if minimumStake <= currentStake:
        return True

    response = requests.post(polyswarmd + "/staking/deposit?account=" + address + "&chain=" + chain, json={"amount": str(minimumStake - currentStake)})
    transactions = response.json()["result"]["transactions"]
    response = sign_transactions(transactions)
    return response.json()["status"] == "OK"

def main():
    sys.path.append('./backends')
    parser = argparse.ArgumentParser(description="Run an arbiter backend.")

    parser.add_argument("--backend", help="Select the backend", default="verbatim")
    parser.add_argument("--test", help="Exits on successful settle", action="store_true",)
    args = parser.parse_args()

    backend = importlib.import_module(args.backend)
    listen_and_arbitrate(args.test, backend)

if __name__ == "__main__":
    main()
