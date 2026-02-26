import sqlite3
import os
import sys

# Path to the SQLite database
db_path = os.path.join(os.path.dirname(__file__), "data", "fincopilot.db")

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    print("Run the application once to create the database file.")
    sys.exit(1)

print(f"Connecting to database: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get existing columns in the users table
cursor.execute("PRAGMA table_info(users)")
columns = [info[1] for info in cursor.fetchall()]

changes_made = False

# Add is_superuser if missing
if 'is_superuser' not in columns:
    print("Adding 'is_superuser' column to 'users' table...")
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT 0")
        changes_made = True
    except sqlite3.OperationalError as e:
        print(f"Error adding is_superuser: {e}")

# Add base_currency if missing
if 'base_currency' not in columns:
    print("Adding 'base_currency' column to 'users' table...")
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN base_currency VARCHAR(3) DEFAULT 'USD' NOT NULL")
        changes_made = True
    except sqlite3.OperationalError as e:
        print(f"Error adding base_currency: {e}")
        
if changes_made:
    print("Committing changes...")
    conn.commit()
    print("✅ Migration completed successfully!")
else:
    print("✅ Database schema is already up to date. No changes needed.")

conn.close()
