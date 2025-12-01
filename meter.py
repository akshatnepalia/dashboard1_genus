import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ================= PAGE CONFIG ================= #
st.set_page_config(layout="wide")

# Styling
st.markdown("""
<style>
    div.block-container {padding-top: 1rem;}
    .stDateInput > div > input {font-size: 0.9rem;}
    thead tr th {background-color: #003A8C !important; color:white !important; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ================= HEADER ================= #
st.markdown("""
<div style='text-align:center; margin-bottom:0.4rem;'>
    <span style='font-size:35px; font-weight:800; color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:260px; height:4px; margin:6px auto;
                background: linear-gradient(to right, #003A8C, #FFD700);
                border-radius:4px;'></div>
</div>
<h4 style='text-align:center; font-weight:700; margin-top:0.2rem;'>
📊 Meter Dashboard — WC/DT + Manpower
</h4>
""", unsafe_allow_html=True)

# ================= LOAD DATA ================= #
df = pd.read_excel("meter_data.xlsx")
df["Date"] = pd.to_datetime(df["Date"])

for col in ["WC-MI", "DT", "CI", "MI", "IN-HOUSE", "Supervisory"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df["Total_Manpower"] = df["CI"] + df["MI"] + df["IN-HOUSE"] + df["Supervisory"]
df["Total_WC_DT"] = df["WC-MI"] + df["DT"]

full_dates = pd.date_range("2025-11-01", "2025-11-26")

# ================= FILTERS ================= #
st.subheader("🔍 Filters")

col1, col2, col3 = st.columns([1.8, 1, 1])

with col1:
    view = st.radio("Select View", ["Combined View", "Package Wise View"], horizontal=True)

with col2:
    start_date = st.date_input("Start Date", df["Date"].min())

with col3:
    end_date = st.date_input("End Date", df["Date"].max())

package = None
if view == "Package Wise View":
    package = st.selectbox("Select Package", sorted(df["Package"].unique()))

df_filtered = df[(df["Date"] >= pd.to_datetime(start_date)) &
                 (df["Date"] <= pd.to_datetime(end_date))]


# ================= KPI SECTION ================= #
def number_k(n): return f"{n/1000:.1f}k" if n >= 1000 else str(int(n))

colK1, colK2, colK3 = st.columns(3)
colK1.metric("📦 Total Meters Installed", number_k(df_filtered["Total_WC_DT"].sum()))
colK2.metric("👥 Avg Manpower", number_k(df_filtered["Total_Manpower"].mean()))
colK3.metric("🚀 Peak Manpower", number_k(df_filtered["Total_Manpower"].max()))


# ================= GRAPH + TABLE ================= #
def graph_and_table(data, title):

    data = data.copy()
    max_man = data["Total_Manpower"].max()

    fig = go.Figure()

    # WC-MI bar
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["WC-MI"],
        name="WC-MI", marker_color="#FF7666", hoverinfo="skip"
    ))

    # DT bar
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["DT"], base=data["WC-MI"],
        name="DT", marker_color="#FFD700",
        customdata=data[["Total_Manpower", "CI", "MI", "IN-HOUSE", "Supervisory", "Total_WC_DT", "WC-MI", "DT"]],
        hovertemplate=(
            "Date: %{x|%d-%b}<br>"
            "Total Manpower: %{customdata[0]}<br>"
            "CI: %{customdata[1]}<br>"
            "MI: %{customdata[2]}<br>"
            "IN-HOUSE: %{customdata[3]}<br>"
            "Supervisory: %{customdata[4]}<br>"
            "Total Meters: %{customdata[5]}<br>"
            "WC-MI: %{customdata[6]}<br>"
            "DT: %{customdata[7]}<br><extra></extra>"
        )
    ))

    # Total Meter label bottom
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=[int(v * 0.015) for v in data["Total_WC_DT"]],
        text=[str(int(v)) for v in data["Total_WC_DT"]],
        mode="text",
        textfont=dict(size=11, color="black"),
        hoverinfo="skip", showlegend=False
    ))

    # Manpower line + labels
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=data["Total_Manpower"],
        mode="lines+markers+text",
        name="Total Manpower",
        text=[f"<b>{int(v)}</b>" for v in data["Total_Manpower"]],
        textposition="top center",
        line=dict(color="#003A8C", width=3),
        marker=dict(size=7, color="#003A8C"),
        yaxis="y2"
    ))

    fig.update_layout(
        barmode="stack",
        height=600,
        hovermode="x unified",
        template="plotly_white",
        xaxis=dict(
            tickvals=data["Date"],
            ticktext=[d.strftime("%d-%b") for d in data["Date"]],
            tickangle=45
        ),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
        margin=dict(l=10, r=10, t=20, b=90)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Table
    pivot = data.pivot_table(
        index=["WC-MI", "DT", "Total_Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"],
        columns="Date", aggfunc="sum"
    )

    pivot.index = [
        "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]

    pivot.loc["🔷 Total Meters (WC+DT)"] = data["Total_WC_DT"].tolist()
    pivot = pivot.reindex([
        "🔷 Total Meters (WC+DT)", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ])

    pivot.columns = [c.strftime("%d-%b") for c in pivot.columns]
    pivot = pivot.fillna(0).astype(int)

    def color_row(row):
        if row.name in ["🔷 Total Meters (WC+DT)", "🟢 Total Manpower"]:
            return ['background-color:#E6F0FF; font-weight:bold'] * len(row)
        return [''] * len(row)

    st.dataframe(pivot.style.apply(color_row, axis=1), use_container_width=True)


# ================= VIEW ================= #
if view == "Combined View":
    grp = df_filtered.groupby("Date").sum().reindex(full_dates, fill_value=0).reset_index()
    grp.rename(columns={"index": "Date"}, inplace=True)
    graph_and_table(grp, "📌 All Packages")
else:
    df_pkg = df_filtered[df_filtered["Package"] == package]
    grp = df_pkg.groupby("Date").sum().reindex(full_dates, fill_value=0).reset_index()
    grp.rename(columns={"index": "Date"}, inplace=True)
    graph_and_table(grp, f"📦 {package}")
