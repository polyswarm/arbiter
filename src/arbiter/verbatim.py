import sqlite3
import hashlib
import os

from polyswarmclient.arbiter import Arbiter

class VerbatimArbiter(Arbiter):
    def __init__(self, polyswarmd_addr, keyfile, password, api_key=None, testing=0, insecure_transport=False):
        super().__init__(polyswarmd_addr, keyfile, password, api_key, testing, insecure_transport)
        self.conn = sqlite3.connect(os.path.join(os.getcwd(), "artifacts", "truth.db"))

    async def scan(self, guid, content, chain):
        h = hashlib.sha256(content).hexdigest()
        return True, self.find_truth(h), ''

    # Finds the file in the truth table. Returns a boolean or None.
    def find_truth(self, filehash):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM files WHERE name=?', (filehash,))
        row = cursor.fetchone()
        return row is not None and row[1] == 1
