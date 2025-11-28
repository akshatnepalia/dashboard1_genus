import pandas as pd

df = pd.read_excel("meter_data.xlsx")
df["Date"] = pd.to_datetime(df["Date"])

df_grouped = df.groupby("Date").sum().reset_index()

print("Columns BEFORE grouping:", df.columns.tolist())
print("Columns AFTER grouping:", df_grouped.columns.tolist())
