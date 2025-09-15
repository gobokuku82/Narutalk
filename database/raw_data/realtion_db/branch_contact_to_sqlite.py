import pandas as pd
import sqlite3
from pathlib import Path

excel_file = Path("database/raw_data/realtion_db/지점연락처_연락처_업데이트.xlsx")
db_file = Path("database/hr_information/hr_data.db")

print(f"Reading Excel file: {excel_file}")
df = pd.read_excel(excel_file)

print(f"Excel data shape: {df.shape}")
try:
    print(f"Columns: {df.columns.tolist()}")
except:
    print(f"Number of columns: {len(df.columns)}")

conn = sqlite3.connect(db_file)

table_name = "지점연락처"
df.to_sql(table_name, conn, if_exists='replace', index=False)

cursor = conn.cursor()
cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
count = cursor.fetchone()[0]
print(f"\nSuccessfully added table to SQLite database: {db_file}")
print(f"Table '{table_name}' created with {count} rows")

cursor.execute(f"PRAGMA table_info({table_name})")
columns_info = cursor.fetchall()
print(f"\nTable structure:")
for col in columns_info:
    try:
        print(f"  - {col[1]} ({col[2]})")
    except:
        print(f"  - Column {col[0]} ({col[2]})")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
all_tables = cursor.fetchall()
print(f"\nAll tables in database:")
for table in all_tables:
    print(f"  - {table[0]}")

conn.close()
print("\nDatabase connection closed.")