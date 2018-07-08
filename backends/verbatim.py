
import sqlite3
import hashlib
import requests

def scan(host, uri):
    conn = sqlite3.connect('../artifacts/truth.db')
    artifacts = get_artifacts(host, uri)
    hashes = [hash_file(host, uri, i) for i, v in enumerate(artifacts)]
    verdicts = [find_truth(conn, h) for i, h in enumerate(hashes)]
    conn.close()
    return verdicts

def hash_file(host, uri, index):
    response = requests.get(host + "/artifacts/" + uri + "/" + str(index))
    content = response.content
    return hashlib.sha256(content).hexdigest()

# Get the file hash from ipfs
def get_artifacts(host, uri):
    response = requests.get(host + "/artifacts/" + uri)
    decoded = response.json()
    if decoded["status"] == "OK":
        return decoded["result"]
    return list()

    # Finds the file in the truth table. Returns a boolean or None.
def find_truth(conn, filehash):
    h = (filehash,)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM files WHERE name=?', h)
    row = cursor.fetchone()
    return row is not None and row[1] == 1