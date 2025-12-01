import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ================= PAGE CONFIG ================= #
st.set_page_config(layout="wide")

# ================= UI STYLING ================= #
st.markdown("""
<style>
div.block-container {padding-top: 1.2rem;}
thead tr th {background-color:#003A8C !important; color:white !important; font-weight:bold !important;}
.stMetric {border-radius:12px !important;}
</style>
""", unsafe_allow_html=True)

# ================= HEADER ================= #
st.markdown("""
<div style='text-align:centessssr;'>
    <span style='font-size:48px; font-weight:800; color:#003A8C;'>Genus Power Infrastructures Ltd.</span>
    <div style='width:260px;height:4px;margin:6px auto;background:linear-gradient(to right,#003A8C,#FFD700);border-radius:4px;'></div>
</div>
<h4 style='text-align:center;font-weight:700;margin-top:0.2rem;margin-bottom:1rem;'>📊 Meter Dashboard — WC/DT + Manpower</h4>
""", unsafe_allow_html=True)

# ================= LOAD DATA ================= #
df = pd.read_excel("meter_data.xlsx")
df["Date"] = pd.to_datetime(df["Date"])

num_cols = ["WC-MI", "DT", "CI", "MI", "IN-HOUSE", "Supervisory"]
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

df["Total_Manpower"] = df["CI"] + df["MI"] + df["IN-HOUSE"] + df["Supervisory"]
df["Total_WC_DT"] = df["WC-MI"] + df["DT"]

# ================= FILTERS ================= #
st.subheader("🔍 Filters")
col1, col2, col3 = st.columns([2,1,1])
with col1:
    view = st.radio("Select View", ["Combined View", "Package Wise View"], horizontal=True)
with col2:
    start_date = st.date_input("Start Date", df["Date"].min())
with col3:
    end_date = st.date_input("End Date", df["Date"].max())

pkg = None
if view == "Package Wise View":
    pkg = st.selectbox("Select Package", sorted(df["Package"].unique()))

df_filtered = df[(df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))]
full_dates = pd.date_range(df["Date"].min(), df["Date"].max())

# ================= K FORMATTER ================= #
def k_fmt(v):
    return f"{v/1000:.1f}K" if v >= 1000 else str(int(v))

# ================= GRAPH + TABLE FUNCTION ================= #
def graph_and_table(data, title):
    data = data.copy()

    # KPI Values
    total_meters = data["Total_WC_DT"].sum()
    peak_meter_row = data.loc[data["Total_WC_DT"].idxmax()]
    peak_meter_day = f"{k_fmt(peak_meter_row['Total_WC_DT'])} on {peak_meter_row['Date'].strftime('%d-%b')}"
    
    peak_mp_row = data.loc[data["Total_Manpower"].idxmax()]
    peak_mp_day = f"{k_fmt(peak_mp_row['Total_Manpower'])} on {peak_mp_row['Date'].strftime('%d-%b')}"

    # KPI Display
    k1, k2, k3 = st.columns(3)
    k1.metric("📈 Total Meters Installed", k_fmt(total_meters))
    k2.metric("👷 Peak Manpower Day", peak_mp_day)
    k3.metric("📍 Peak Meter Day", peak_meter_day)

    # Hover Tooltip
    hover_text = (
        "Date: %{x|%d-%b}<br>"
        "<b>Total Manpower: %{customdata[0]:.0f}</b><br>"
        "CI: %{customdata[1]:.0f}<br>"
        "MI: %{customdata[2]:.0f}<br>"
        "IN-HOUSE: %{customdata[3]:.0f}<br>"
        "Supervisory: %{customdata[4]:.0f}<br><br>"
        "<b>Total Meters: %{customdata[5]:.0f}</b><br>"
        "WC-MI: %{customdata[6]:.0f}<br>"
        "DT: %{customdata[7]:.0f}<br><extra></extra>"
    )

    # Graph Building
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=data["Date"], y=data["WC-MI"],
        name="WC-MI", marker_color="#FF7666", hoverinfo="skip"
    ))

    fig.add_trace(go.Bar(
        x=data["Date"], y=data["DT"], base=data["WC-MI"],
        name="DT", marker_color="#FFD700",
        customdata=data[["Total_Manpower","CI","MI","IN-HOUSE","Supervisory","Total_WC_DT","WC-MI","DT"]],
        hovertemplate=hover_text
    ))

    fig.add_trace(go.Scatter(
        x=data["Date"], y=data["Total_Manpower"],
        mode="lines+markers+text",
        name="Total Manpower",
        text=[str(int(v)) for v in data["Total_Manpower"]],
        textposition="top center",
        marker=dict(color="#003A8C", size=8),
        line=dict(color="#003A8C", width=3),
        yaxis="y2",
        hoverinfo="skip"
    ))

    fig.update_layout(
        title=title,
        barmode="stack",
        height=620,
        hovermode="x unified",
        template="plotly_white",
        xaxis=dict(
            tickvals=data["Date"],
            ticktext=[d.strftime("%d-%b") for d in data["Date"]],
            tickangle=45,
        ),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ================= TABLE ================= #
    table = data.set_index("Date")[["Total_WC_DT","WC-MI","DT","Total_Manpower","CI","MI","IN-HOUSE","Supervisory"]]
    table = table.T.astype(int)

    table.index = [
        "🔷 Total Meters (WC+DT)", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]

    def style_rows(row):
        if "Total" in row.name:
            return ["font-weight:bold;background-color:#E6F0FF"]*len(row)
        return [""]*len(row)

    st.subheader("📋 Date-wise Summary Table")
    st.dataframe(table.style.apply(style_rows, axis=1), use_container_width=True)

# ================= VIEW RENDERING ================= #
if view == "Combined View":
    grp = df_filtered.groupby("Date")[["WC-MI","DT","CI","MI","IN-HOUSE","Supervisory","Total_Manpower","Total_WC_DT"]].sum().reset_index()
    graph_and_table(grp, "📌 All Packages")
else:
    pkg_data = df_filtered[df_filtered["Package"] == pkg]
    grp = pkg_data.groupby("Date")[["WC-MI","DT","CI","MI","IN-HOUSE","Supervisory","Total_Manpower","Total_WC_DT"]].sum().reset_index()
    graph_and_table(grp, f"📦 {pkg}")
