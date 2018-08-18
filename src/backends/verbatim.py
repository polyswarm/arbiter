
import sqlite3
import hashlib
import requests
import os

async def scan(content):
    conn = sqlite3.connect(os.path.join(os.getcwd(), "artifacts", "truth.db"))
    hash = hashlib.sha256(content).hexdigest()
    verdict = find_truth(conn, hash)
    conn.close()
    return verdict

    # Finds the file in the truth table. Returns a boolean or None.
def find_truth(conn, filehash):
    h = (filehash,)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM files WHERE name=?', h)
    row = cursor.fetchone()
    return row is not None and row[1] == 1
