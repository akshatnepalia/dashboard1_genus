def get_basic_kpis(df):
    return {
        "installed": df["Installed"].sum(),
        "pending": df["Pending"].sum(),
        "total": df["Planned"].sum()
    }
