import pandas as pd
import sqlite3
from pathlib import Path

excel_file = Path("database/raw_data/realtion_db/좋은제약_지점별_목표._목표만xlsx.xlsx")
db_path = Path("database/sales_performance_db")
db_path.mkdir(parents=True, exist_ok=True)
db_file = db_path / "sales_target_db.db"

print(f"Reading Excel file: {excel_file}")
df = pd.read_excel(excel_file)

print(f"Excel data shape: {df.shape}")
try:
    print(f"Columns: {df.columns.tolist()}")
except:
    print(f"Number of columns: {len(df.columns)}")

conn = sqlite3.connect(db_file)

table_name = "지점별목표"
df.to_sql(table_name, conn, if_exists='replace', index=False)

cursor = conn.cursor()
cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
count = cursor.fetchone()[0]
print(f"\nSuccessfully created SQLite database: {db_file}")
print(f"Table '{table_name}' created with {count} rows")

cursor.execute(f"PRAGMA table_info({table_name})")
columns_info = cursor.fetchall()
print(f"\nTable structure:")
for col in columns_info:
    try:
        print(f"  - {col[1]} ({col[2]})")
    except:
        print(f"  - Column {col[0]} ({col[2]})")

conn.close()
print("\nDatabase connection closed.")