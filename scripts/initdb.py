import sqlite3
import hashlib
import os

def init():
    conn = sqlite3.connect('../artifacts/truth.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS files (name text, truth int)''')
    benign = os.listdir(os.path.join(os.getcwd(), 'artifacts', 'benign'))
    for b in benign:
        insert(cursor, os.path.join(os.getcwd(), 'artifacts', 'benign', b), 0)

    malicious = os.listdir(os.path.join(os.getcwd(), 'artifacts', 'malicious'))
    for m in malicious:
        insert(cursor, os.path.join(os.getcwd(), 'artifacts', 'malicious', m), 1)

    conn.commit()
    conn.close()

def insert(cursor, path, result):
    with open (path, encoding='utf-8') as f:
        data = f.read()
        h = hashlib.sha256(data.encode('utf-8')).hexdigest()
        value = (h, result)
        cursor.execute('''INSERT INTO files values (?, ?)''', value)

if __name__ == "__main__":
    init()