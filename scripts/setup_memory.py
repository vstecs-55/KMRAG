import sqlite3
import os

def setup_memory():
    db_path = "chat_history.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                user_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, timestamp)
            )
        ''')

        conn.commit()
        print(f"Successfully initialized database at {db_path} with table 'history'.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    setup_memory()
