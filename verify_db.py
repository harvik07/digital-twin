import os
import sqlite3

db_path = "instance/site.db"   # Ensure this is the correct database filename

# Check if the database file exists
if os.path.exists(db_path):
    print("✅ Database exists:", db_path)
else:
    print("❌ Database does not exist.")
    exit()  # Exit the script if the database doesn't exist

# Connect to the SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Fetch all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [table[0] for table in cursor.fetchall()]
print("Tables in database:", tables)

# Check if the 'User' table exists
table_name = "user"  # Ensure the correct table name (case-sensitive)
if table_name in tables:
    print(f"✅ Table '{table_name}' exists.")

    # Try fetching user data
    try:
        cursor.execute(f"SELECT email, password FROM {table_name}")
        users = cursor.fetchall()
        if users:
            for email, password in users:
                print(f"Email: {email}, Password Hash: {password}")
        else:
            print("ℹ️ No users found in the database.")
    except sqlite3.OperationalError as e:
        print(f"❌ Error fetching user data: {e}")
else:
    print(f"❌ Table '{table_name}' does not exist. Check migration!")

# Close the database connection
conn.close()
