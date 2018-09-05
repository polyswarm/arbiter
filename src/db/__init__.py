import sqlite3
import hashlib
import os

def generate_db(db_file, malicious_dir, benign_dir):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS files (name text, truth int)''')
    benign = os.listdir(benign_dir)
    for b in benign:
        insert(cursor, os.path.join(benign_dir, b), 0)
        conn.commit()

    malicious = os.listdir(malicious_dir)
    for m in malicious:
        insert(cursor, os.path.join(malicious_dir, m), 1)
        conn.commit()

    conn.close()

def insert(cursor, path, result):
    with open (path, "rb") as f:
        data = f.read()
        h = hashlib.sha256(data).hexdigest()
        value = (h, result)
        cursor.execute('''INSERT INTO files values (?, ?)''', value)
