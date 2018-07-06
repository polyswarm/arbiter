import sqlite3
import hashlib

def init():
    conn = sqlite3.connect('../artifacts/truth.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS files (name text, truth int)''')
    insert(cursor, './artifacts/benign', 0)
    insert(cursor, './artifacts/malicious', 1)
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