import sqlite3

db_file = "database/hr_information/hr_data.db"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Total tables in database: {len(tables)}\n")

for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM '{table_name}'")
    count = cursor.fetchone()[0]

    cursor.execute(f"PRAGMA table_info('{table_name}')")
    columns = cursor.fetchall()

    print(f"Table: {table_name}")
    print(f"  - Records: {count}")
    print(f"  - Columns: {len(columns)}")
    print()

conn.close()
print("Database verification complete.")