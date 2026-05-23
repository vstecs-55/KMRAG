import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def setup_memory():
    db_path = os.path.abspath("chat_history.db")
    conn = None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create index on user_id for faster retrieval
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON history(user_id)')

        conn.commit()
        logging.info(f"Successfully initialized database at {db_path} with table 'history'.")

    except sqlite3.Error as e:
        logging.error(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    setup_memory()
