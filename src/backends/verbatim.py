
import sqlite3
import hashlib
import requests
import os

class Scanner:
    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(os.getcwd(), "artifacts", "truth.db"))

    async def scan(self, content):
        hash = hashlib.sha256(content).hexdigest()
        verdict = self.find_truth(hash)
        return verdict

        # Finds the file in the truth table. Returns a boolean or None.
    def find_truth(self, filehash):
        h = (filehash,)
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM files WHERE name=?', h)
        row = cursor.fetchone()
        return row is not None and row[1] == 1
