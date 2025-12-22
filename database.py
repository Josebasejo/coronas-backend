import sqlite3

DB = "models.db"

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS modelos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seccion TEXT,
            modelo TEXT,
            cliente TEXT,
            fecha TEXT
        )
    """)
    conn.commit()
    conn.close()

def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv
