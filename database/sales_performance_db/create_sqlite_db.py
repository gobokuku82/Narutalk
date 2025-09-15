import pandas as pd
import sqlite3
from pathlib import Path

excel_file = Path("database/raw_data/realtion_db/좋은제약_실적자료_통합.xlsx")
db_path = Path("c:/kdy/Projects/Narutalk_V003/beta_v0031/database/sales_performance_db.db")

db_path.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(excel_file)

print(f"Reading Excel file: {excel_file}")
print(f"Data shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

conn = sqlite3.connect(str(db_path))

df.to_sql('sales_performance', conn, if_exists='replace', index=False)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM sales_performance")
row_count = cursor.fetchone()[0]

cursor.execute("PRAGMA table_info(sales_performance)")
columns_info = cursor.fetchall()

print(f"\nDatabase created successfully at: {db_path}")
print(f"Table: sales_performance")
print(f"Total rows: {row_count}")
print(f"\nColumn information:")
for col in columns_info:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
print("\nDatabase connection closed.")