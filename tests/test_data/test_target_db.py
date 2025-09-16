import sqlite3

db_file = "database/sales_performance_db/sales_target_db.db"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables in database: {tables}")

cursor.execute("SELECT * FROM 지점별목표")
rows = cursor.fetchall()
print(f"\n지점별목표 데이터:")
for row in rows:
    print(f"  {row[0]} ({row[1]}): 최근 목표 = {row[-1]:,}")

cursor.execute("PRAGMA table_info(지점별목표)")
columns = cursor.fetchall()
print(f"\n총 컬럼 수: {len(columns)}")
print("월별 목표 컬럼: 202312 ~ 202411")

conn.close()
print("\nDatabase verification complete.")