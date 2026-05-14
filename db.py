import sqlite3
from contextlib import closing

def init_db():
    with closing(sqlite3.connect('members.db')) as conn:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT NOT NULL,
                    password TEXT NOT NULL,
                    is_admin INTEGER DEFAULT 0
                )
            ''')

def add_member(email, phone, password, is_admin=0):
    with closing(sqlite3.connect('members.db')) as conn:
        with conn:
            conn.execute('INSERT INTO members (email, phone, password, is_admin) VALUES (?, ?, ?, ?)', (email, phone, password, is_admin))

def get_member(email):
    with closing(sqlite3.connect('members.db')) as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM members WHERE email = ?', (email,))
        return cur.fetchone()

def reset_password(email, phone, new_password):
    with closing(sqlite3.connect('members.db')) as conn:
        with conn:
            cur = conn.cursor()
            cur.execute('UPDATE members SET password = ? WHERE email = ? AND phone = ?', (new_password, email, phone))
            return cur.rowcount > 0
