import sqlite3

db_file = "database/sales_performance_db/clients_info.db"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables in database: {tables}")

cursor.execute("SELECT COUNT(*) FROM 거래처정보")
count = cursor.fetchone()[0]
print(f"\n총 거래처 수: {count}개")

cursor.execute("SELECT 지역구, COUNT(*) as cnt FROM 거래처정보 GROUP BY 지역구 ORDER BY cnt DESC LIMIT 5")
regions = cursor.fetchall()
print(f"\n지역구별 거래처 분포 (상위 5개):")
for region in regions:
    print(f"  {region[0]}: {region[1]}개")

cursor.execute("PRAGMA table_info(거래처정보)")
columns = cursor.fetchall()
print(f"\n테이블 구조:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
print("\nDatabase verification complete.")