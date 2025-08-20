import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def test_db_connection():
    try:
        db_path = os.getenv("DATABASE")
        conn = sqlite3.connect(db_path)

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tracks")
        track_count = cursor.fetchone()[0]
        conn.close()
        print(f"Database connection successful. Found {track_count} tracks.")
        return True

    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

if __name__ == "__main__":
    test_db_connection()