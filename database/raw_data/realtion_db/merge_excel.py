import pandas as pd
import os
from pathlib import Path

base_dir = Path("database/raw_data/realtion_db")

files = [
    "좋은제약_실적자료_윤수아_2.xlsx",
    "좋은제약_실적자료_윤하은_2.xlsx",
    "좋은제약_실적자료_정예준_2.xlsx",
    "좋은제약_실적자료_조시현_2.xlsx",
    "좋은제약_실적자료_조하은_2.xlsx",
    "좋은제약_실적자료_최수아_2.xlsx"
]

dfs = []
for file in files:
    file_path = base_dir / file
    df = pd.read_excel(file_path)
    dfs.append(df)

merged_df = pd.concat(dfs, ignore_index=True)

output_file = base_dir / "좋은제약_실적자료_통합.xlsx"
merged_df.to_excel(output_file, index=False)

print(f"Successfully merged {len(files)} files into {output_file}")
print(f"Total rows: {len(merged_df)}")
print(f"Columns: {list(merged_df.columns)}")