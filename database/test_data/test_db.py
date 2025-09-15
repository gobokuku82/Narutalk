import sqlite3

db_file = "database/sales_performance_db/sales_data.db"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables in database: {tables}")

cursor.execute("SELECT * FROM 거래처자료 LIMIT 5")
rows = cursor.fetchall()
print(f"\nFirst 5 rows:")
for row in rows:
    print(row)

cursor.execute("SELECT 담당자, COUNT(*) as count FROM 거래처자료 GROUP BY 담당자")
summary = cursor.fetchall()
print(f"\nData summary by 담당자:")
for row in summary:
    print(f"  {row[0]}: {row[1]} rows")

conn.close()