import sqlite3

db_file = "database/hr_information/hr_data.db"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables in database: {tables}")

cursor.execute("SELECT COUNT(*) FROM 인사자료")
count = cursor.fetchone()[0]
print(f"\nTotal records in 인사자료 table: {count}")

cursor.execute("SELECT * FROM 인사자료 LIMIT 3")
rows = cursor.fetchall()
print(f"\nFirst 3 rows (sample):")
for i, row in enumerate(rows, 1):
    print(f"Row {i}: {row[:5]}...")

cursor.execute("PRAGMA table_info(인사자료)")
columns = cursor.fetchall()
print(f"\nTotal columns: {len(columns)}")

conn.close()
print("\nDatabase verification complete.")