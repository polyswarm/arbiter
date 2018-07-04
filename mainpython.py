import requests
import os
import csv

from heapq import heappush, heappop
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware

keyfile = './key/keyfile'
truthcsv = './artifacts/truth.csv'
password = 'password'

polyswarmd = os.environ.get("POLYSWARMD")
geth = os.environ.get("GETH")


w3 = Web3(HTTPProvider(geth))
w3.middleware_stack.inject(geth_poa_middleware, layer=0)

# Get the file hash from ipfs
def get_artifacts(uri):
    response = requests.get( polyswarmd + "/artifacts/" + uri )
    decoded = response.json()
    if decoded["status"] == "OK":
        return list(map(lambda f: f["hash"], decoded["result"]))
    else:
        return list()

# Finds the file in the truth table. Returns a boolean or None.
def find_value_in_truth_table(filehash):
    with open(truthcsv, newline='') as ground_truth:
        reader = csv.reader(ground_truth, delimeter=',')
        for row in reader:
            if row[0] == filehash:
                return row[1] == 1
    return False

# This will settle any bounties
def settle_bounties(heap, blocknumber):
    while len(heap) > 0:
        head = heap[0]

        # request settle
        if int(head[0]) < blocknumber:
            guid = head[1]
            response = requests.post( polyswarmd + "/bounties/" + guid + "/settle" )
            transactions = response.json()['result']['transactions']
            response = sign_transactions(transactions)

            if response.json()["status"] == "OK":
                heappop(heap)
            else:
                print("Failed to settle "+ guid)
                break
        else:
            break

def vote(guid, verdicts):
    data = {
        "verdicts": verdicts,
        "valid_bloom": True
    }
    response = requests.post( polyswarmd + "/bounties/" + guid + "/vote", data = data )
    transactions = response.json()['result']['transactions']
    response = sign_transactions(transactions)
    return response.json()["status"] == "OK"

def sign_transactions(transactions):
    signed_transactions = []
    key = w3.eth.account.decrypt(open(keyfile,'r').read(), password)
    for transaction in transactions:
        signed = w3.eth.account.signTransaction(transaction, key)
        raw = bytes(signed['rawTransaction']).hex()
        signed_transactions.append(raw)
    return requests.post('http://polyswarmd:31337/transactions', json={'transactions': signed_transactions})


# Listen to polyswarmd /bounties/pending route to find expired bounties
def listen_and_arbitrate():
    # to_settle is a head of bounty objects ordered by block number when then assertion reveal phase ends
    to_settle = []
    voted_bounties = set()
    while (True):
        # Check bounties route
        # TODO chain in env
        response = requests.get( polyswarmd + "/bounties/pending" )
        decoded = response.json()
        if decoded["status"] == "OK":
            bounties = response.json()["result"]
            for bounty in bounties:
                if bounty["guid"] not in voted_bounties:
                    # Vote
                    hashes = get_artifacts(bounty["artifactUri"])
                    verdicts = list(map(lambda hash: find_value_in_truth_table(hash), hashes))
                    # If successfully volted, add to heap to be settled
                    if vote(bounty["guid"], verdicts):
                        # Mark voted
                        voted_bounties.add(bounty["guid"])
                        # Add to head so it can be settled
                        heappush(to_settle, (int(bounty["blocknumber"])+50, bounty["guid"]))

            blocknumber = w3.eth.blockNumber
            settle_bounties(to_settle, blocknumber)

if __name__ == "__main__":
    listen_and_arbitrate()