
import sqlite3
import hashlib
import requests
import os

def scan(host, uri):
    session = requests.Session()
    conn = sqlite3.connect(os.path.join(os.getcwd(), "artifacts", "truth.db"))
    artifacts = get_artifacts(session, host, uri)
    hashes = [hash_file(session, host, uri, i) for i, v in enumerate(artifacts)]
    verdicts = [find_truth(conn, h) for i, h in enumerate(hashes)]
    conn.close()
    return verdicts

def hash_file(session, host, uri, index):
    response = session.get(host + "/artifacts/" + uri + "/" + str(index))
    content = response.content
    return hashlib.sha256(content).hexdigest()

# Get the file hash from ipfs
def get_artifacts(session, host, uri):
    response = session.get(host + "/artifacts/" + uri)
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
