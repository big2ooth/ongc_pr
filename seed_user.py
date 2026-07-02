import sqlite3
import hashlib

DB_PATH = "backend/violations.db"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def seed_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            role        TEXT DEFAULT 'supervisor',
            full_name   TEXT
        )
    """)

    users = [
        ("admin",      hash_password("admin123"),   "admin",      "Admin User"),
        ("supervisor", hash_password("ongc2026"),   "supervisor", "Site Supervisor"),
        ("manager",    hash_password("manager123"), "supervisor", "Safety Manager"),
    ]

    for user in users:
        try:
            cursor.execute(
                "INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
                user
            )
            print(f"[+] Created user: {user[0]} ({user[2]})")
        except sqlite3.IntegrityError:
            print(f"[~] User already exists: {user[0]}")

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    seed_users()