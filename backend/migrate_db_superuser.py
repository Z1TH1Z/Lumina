import sqlite3
def run_migration():
    conn = sqlite3.connect('data/fincopilot.db')
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT 0")
        print("Added is_superuser to users")
    except Exception as e:
        print(f"Users table: {e}")
    conn.commit()
    conn.close()
if __name__ == '__main__':
    run_migration()
