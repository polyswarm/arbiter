
import sqlite3
import hashlib

conn = sqlite3.connect('../artifacts/truth.db')

def scan(self, host, artifactUri):
    artifacts = get_artifacts(host, artifactUri)
    hashes = [hash(host, uri, i) for i, v in enumerate(artifacts)]
    return list(map(find_truth, hashes))

def hash(host, uri, index):
    response = requests.get(host + "/artifacts/" + uri + "/" + index)
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
def find_truth(filehash):
    h = (filehash,)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM files WHERE name=?', h)
    row = c.fetchone()
    return row["malicious"] == 1
