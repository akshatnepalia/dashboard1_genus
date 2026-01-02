import pandas as pd

@st.cache_data
def load_data():
    df = pd.read_excel("data/meter_data.xlsx")
    df["date"] = pd.to_datetime(df["date"])
    return df

def filter_data(df, meter_type):
    if meter_type == "WC":
        return df[df["Meter_Type"] == "WC"]
    elif meter_type == "DT":
        return df[df["Meter_Type"] == "DT"]
    return df
