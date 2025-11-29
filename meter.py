import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ================= PAGE CONFIG ================= #
st.set_page_config(layout="wide")

st.markdown("""
    <style>
        div.block-container {
            padding-top: 1.3rem;
        }
        thead tr th {
            background-color: #003A8C !important;
            color: white !important;
            font-weight: bold !important;
        }
        @media(max-width: 768px) {
            div.block-container {
                padding-left: 0.4rem;
                padding-right: 0.4rem;
            }
            h4, span {
                font-size: 18px !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

# ================= HEADER ================= #
st.markdown("""
<div style='text-align:center; margin-bottom:0.4rem;'>
    <span style='font-size:45px; font-weight:800; color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:240px; height:4px; margin:6px auto 0 auto;
                background: linear-gradient(to right, #003A8C, #FFD700);
                border-radius: 4px;'></div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<h4 style='text-align:center; font-weight:700; margin-top:0.4rem; margin-bottom:1rem;'>
📊 Meter Dashboard — WC/DT + Manpower
</h4>
""", unsafe_allow_html=True)

# ================= LOAD DATA ================= #
df = pd.read_excel("meter_data.xlsx")
df["Date"] = pd.to_datetime(df["Date"])

num_cols = ["WC-MI", "DT", "CI", "MI", "IN-HOUSE", "Supervisory"]
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

df["Total_Manpower"] = df["CI"] + df["MI"] + df["IN-HOUSE"] + df["Supervisory"]

# ================= FILTERS ================= #
st.markdown("<p style='font-size:16px; font-weight:600; margin-bottom:0.3rem;'>🔍 Filters</p>",
            unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    view = st.radio("View Mode", ["Combined View", "Package Wise View"], horizontal=True)
with col2:
    start_date = st.date_input("Start Date", df["Date"].min())
with col3:
    end_date = st.date_input("End Date", df["Date"].max())

package = None
if view == "Package Wise View":
    package = st.selectbox("Select Package", sorted(df["Package"].unique()))

df_filtered = df[
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))
]

full_dates = pd.date_range("2025-11-01", "2025-11-26")

# ================= GRAPH + TABLE ================= #
def graph_and_table(data, title):
    data = data.copy()
    data["Total_WC_DT"] = data["WC-MI"] + data["DT"]
    max_man = data["Total_Manpower"].max()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=data["Date"], y=data["WC-MI"],
        name="WC-MI", marker_color="#FF7666", hoverinfo="skip"
    ))

    hovertemplate = (
        "Date: %{x|%d-%b}<br>"
        "Total Manpower: %{customdata[0]:.0f}<br>"
        "CI: %{customdata[1]:.0f}<br>"
        "MI: %{customdata[2]:.0f}<br>"
        "IN-HOUSE: %{customdata[3]:.0f}<br>"
        "Supervisory: %{customdata[4]:.0f}<br>"
        "Total Meters: %{customdata[5]:.0f}<br>"
        "WC-MI: %{customdata[6]:.0f}<br>"
        "DT: %{customdata[7]:.0f}<br><extra></extra>"
    )

    fig.add_trace(go.Bar(
        x=data["Date"], y=data["DT"], base=data["WC-MI"],
        name="DT", marker_color="#FFD700",
        customdata=data[["Total_Manpower","CI","MI","IN-HOUSE","Supervisory",
                         "Total_WC_DT","WC-MI","DT"]],
        hovertemplate=hovertemplate
    ))

    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=[v*0.03 for v in data["Total_WC_DT"]],
        text=[str(int(v)) for v in data["Total_WC_DT"]],
        mode="text",
        textposition="bottom center",
        textfont=dict(color="black", size=11, family="Arial Black"),
        hoverinfo="skip", showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=data["Total_Manpower"] + max_man * 0.15,
        text=[f"<b>{int(v)}</b>" for v in data["Total_Manpower"]],
        mode="lines+markers+text",
        textposition="top center",
        textfont=dict(color="black", size=12),
        marker=dict(size=7, color="#003A8C"),
        line=dict(color="#003A8C", width=3),
        name="Total Manpower",
        yaxis="y2", hoverinfo="skip"
    ))

    fig.update_layout(
        title=title,barmode="stack",
        hovermode="x unified",
        height=570,
        template="plotly_white",
        xaxis=dict(
            tickvals=data["Date"],
            ticktext=[d.strftime("%d-%b") for d in data["Date"]],
            tickangle=45
        ),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ================= TABLE ================= #
    st.subheader("📋 Daily Summary Table")

    pivot = data.pivot_table(
        columns="Date",
        values=["Total_WC_DT","WC-MI","DT","Total_Manpower","CI","MI","IN-HOUSE","Supervisory"],
        aggfunc="sum"
    )

    pivot = pivot.reindex([
        "Total_WC_DT","WC-MI","DT",
        "Total_Manpower","CI","MI","IN-HOUSE","Supervisory"
    ])

    pivot.index = [
        "🔷 Total Meters (WC+DT)", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]

    pivot.columns = [c.strftime("%d-%b") for c in pivot.columns]
    pivot = pivot.astype(int)

    def highlight_rows(row):
        if row.name in ["🔷 Total Meters (WC+DT)", "🟢 Total Manpower"]:
            return ['background-color: #E6F5FF; font-weight: 900; color:black;' for _ in row]
        return ['font-weight: 600;' for _ in row]

    styled = pivot.style.apply(highlight_rows, axis=1).format("{:,.0f}")
    st.dataframe(styled, use_container_width=True)

# ================= VIEW HANDLING ================= #
if view == "Combined View":
    grp = df_filtered.groupby("Date")[["WC-MI","DT","CI","MI","IN-HOUSE","Supervisory","Total_Manpower"]].sum()
    grp = grp.reindex(full_dates, fill_value=0)
    grp.index.name = "Date"
    grp = grp.reset_index()
    graph_and_table(grp, "📌 All Packages")
else:
    pkg = df_filtered[df_filtered["Package"] == package]
    pkg = pkg.groupby("Date")[["WC-MI","DT","CI","MI","IN-HOUSE","Supervisory","Total_Manpower"]].sum()
    pkg = pkg.reindex(full_dates, fill_value=0)
    pkg.index.name = "Date"
    pkg = pkg.reset_index()
    graph_and_table(pkg, f"📦 {package}")

