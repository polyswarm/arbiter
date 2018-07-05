import requests
import os
import csv
import glob

from heapq import heappush, heappop
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware

keydir = "./keystore"
truthcsv = "./artifacts/truth.csv"

polyswarmd = os.environ.get("POLYSWARMD")
geth = os.environ.get("GETH")
address = os.environ.get("ADDRESS")
password = os.environ.get("PASSWORD")

w3 = Web3(HTTPProvider(geth))
w3.middleware_stack.inject(geth_poa_middleware, layer=0)

def decrypt_key(address, password):
    os.chdir(keydir)
    if address.starts_with('0x'):
        temp = address[2:]
    possible_matches = glob.glob("*" + temp)
    os.chdir('..')
    if len(possible_matches) == 1:
        with open(possible_matches[0]) as keyfile:
            encrypted = keyfile.read()
            return w3.decrypt_key(encrypted, password)
    return None

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
        reader = csv.reader(ground_truth, delimeter=",")
        for row in reader:
            if row[0] == filehash:
                return row[1] == 1
    return False

# This will settle any bounties
def settle_bounties(heap, blocknumber):
    while len(heap) > 0:
        head = heap[0]

        #  For any bounties blocknumber exceeds the reveal & vote windows... settle
        if int(head[0]) < blocknumber:
            guid = head[1]
            response = requests.post( polyswarmd + "/bounties/" + guid + "/settle" )
            transactions = response.json()["result"]["transactions"]
            response = sign_transactions(transactions)

            if response.json()["status"] == "OK":
                heappop(heap)
            else:
                print("Failed to settle "+ guid)
                break
        else:
            break

def vote(guid, verdicts):
    response = requests.post( polyswarmd + "/bounties/" + guid + "/vote", json={"verdicts": verdicts, "valid_bloom": True} )
    transactions = response.json()["result"]["transactions"]
    response = sign_transactions(transactions)
    return response.json()["status"] == "OK"

def sign_transactions(transactions):
    signed_transactions = []
    key = decrypt_key(address, password)
    for transaction in transactions:
        signed = w3.eth.account.signTransaction(transaction, key)
        raw = bytes(signed["rawTransaction"]).hex()
        signed_transactions.append(raw)
    return requests.post( polyswarmd + "/transactions", json={"transactions": signed_transactions} )

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
                        # Add to heap so it can be settled
                        heappush(to_settle, (int(bounty["blocknumber"])+50, bounty["guid"]))

            blocknumber = w3.eth.blockNumber
            settle_bounties(to_settle, blocknumber)

if __name__ == "__main__":
    listen_and_arbitrate()