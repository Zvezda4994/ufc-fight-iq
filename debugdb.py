import sqlite3
import pandas as pd

conn = sqlite3.connect("ufc_data.db")
df = pd.read_sql("SELECT winner, count(*) as count FROM fights GROUP BY winner ORDER BY count DESC LIMIT 10", conn)
print(df)
conn.close()