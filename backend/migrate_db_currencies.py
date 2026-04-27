import sqlite3

def run_migration():
    conn = sqlite3.connect('data/fincopilot.db')
    try:
        conn.execute("ALTER TABLE users ADD COLUMN base_currency VARCHAR DEFAULT 'USD'")
        print("Added base_currency to users")
    except Exception as e:
        print(f"Users table: {e}")
        
    try:
        conn.execute("ALTER TABLE transactions ADD COLUMN currency VARCHAR DEFAULT 'USD'")
        print("Added currency to transactions")
    except Exception as e:
        print(f"Transactions table: {e}")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    run_migration()
