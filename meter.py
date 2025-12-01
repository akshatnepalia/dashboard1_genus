import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ================= PAGE CONFIG ================= #
st.set_page_config(layout="wide")

# ================= CUSTOM CSS ================= #
st.markdown("""
<style>
    div.block-container {padding-top: 1.2rem;}
    thead tr th {
        background-color: #003A8C !important;
        color: white !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= HEADER ================= #
st.markdown("""
<div style='text-align:center;margin-bottom:0.5rem;'>
    <span style='font-size:35px;font-weight:800;color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:260px;height:4px;margin:6px auto;background:#FFD700;border-radius:4px;'></div>
</div>
<h4 style='text-align:center;font-weight:700;margin-top:0.2rem;margin-bottom:0.8rem;'>
📊 Meter Dashboard — WC/DT + Manpower
</h4>
""", unsafe_allow_html=True)

# ================= LOAD DATA ================= #
df = pd.read_excel("meter_data.xlsx")
df["Date"] = pd.to_datetime(df["Date"]).dt.date  # 🚀 Removed 00:00

num_cols = ["WC-MI", "DT", "CI", "MI", "IN-HOUSE", "Supervisory"]
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

df["Total_Manpower"] = df["CI"] + df["MI"] + df["IN-HOUSE"] + df["Supervisory"]
df["Total_WC_DT"] = df["WC-MI"] + df["DT"]

# ================= FILTERS UI ================= #
st.markdown("### 🔍 Filters")

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    view = st.radio("View Mode", ["Combined View", "Package Wise View"], horizontal=True)
with c2:
    start_date = st.date_input("Start Date", df["Date"].min())
with c3:
    end_date = st.date_input("End Date", df["Date"].max())

package = None
if view == "Package Wise View":
    package = st.selectbox("Select Package", sorted(df["Package"].unique()))

df_filtered = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]
full_dates = pd.date_range("2025-11-01", "2025-11-26").date

# ================= KPI CARDS ================= #
def kfmt(v):
    return f"{v/1000:.1f}k" if v >= 1000 else str(int(v))

total_meters = df_filtered["Total_WC_DT"].sum()
peak_manpower = df_filtered["Total_Manpower"].max()

k1, k2 = st.columns(2)
k1.metric("📦 Total Meters Installed", kfmt(total_meters))
k2.metric("🚀 Peak Manpower", int(peak_manpower))

# ================= GRAPH + TABLE ================= #
def graph_and_table(data, title):
    data = data.copy()
    max_man = data["Total_Manpower"].max()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=data["Date"], y=data["WC-MI"],
        name="WC-MI", marker_color="#FF7B7B",
        hoverinfo="skip"
    ))

    hovertemplate = (
        "Date: %{x}<br>"
        "Total Manpower: %{customdata[0]:.0f}<br>"
        "CI: %{customdata[1]:.0f}<br>"
        "MI: %{customdata[2]:.0f}<br>"
        "IN-HOUSE: %{customdata[3]:.0f}<br>"
        "Supervisory: %{customdata[4]:.0f}<br>"
        "<b>Total Meters: %{customdata[5]:.0f}</b><br>"
        "WC-MI: %{customdata[6]:.0f}<br>"
        "DT: %{customdata[7]:.0f}<br><extra></extra>"
    )

    fig.add_trace(go.Bar(
        x=data["Date"], y=data["DT"], base=data["WC-MI"],
        name="DT", marker_color="#FFD700",
        customdata=data[["Total_Manpower", "CI", "MI",
                         "IN-HOUSE", "Supervisory",
                         "Total_WC_DT", "WC-MI", "DT"]],
        hovertemplate=hovertemplate
    ))

    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=[int(v * 0.10) for v in data["Total_WC_DT"]],
        text=[f"<b>{kfmt(v)}</b>" for v in data["Total_WC_DT"]],
        mode="text",
        textfont=dict(color="black", size=11),
        hoverinfo="skip",
        showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=data["Total_Manpower"] + max_man * 0.20,
        name="Total Manpower",
        mode="lines+markers+text",
        text=[f"<b>{int(v)}</b>" for v in data["Total_Manpower"]],
        textposition="top center",
        textfont=dict(color="black", size=13),
        line=dict(color="#003A8C", width=3),
        marker=dict(size=8, color="#003A8C"),
        yaxis="y2",
        hoverinfo="skip"
    ))

    fig.update_layout(
        title=title,
        height=540,
        barmode="stack",
        bargap=0.18,
        hovermode="x unified",
        xaxis=dict(tickangle=45),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------------- TABLE ---------------- #
    table = data.set_index("Date")[
        ["Total_WC_DT", "WC-MI", "DT",
         "Total_Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"]
    ].T

    table.index = [
        "🔷 Total Meters (WC+DT)", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]

    table.columns = [d.strftime("%d-%b") for d in table.columns]
    table = table.fillna(0).astype(int)

    def style_row(r):
        if r.name in ["🔷 Total Meters (WC+DT)", "🟢 Total Manpower"]:
            return ['font-weight:bold;background:#E6F2FF'] * len(r)
        return [''] * len(r)

    st.dataframe(table.style.apply(style_row, axis=1), use_container_width=True)

# ================= VIEW EXECUTION ================= #
if view == "Combined View":
    grp = df_filtered.groupby("Date").sum().reindex(full_dates, fill_value=0).reset_index()
    graph_and_table(grp, "📌 All Packages")
else:
    pkg_df = df_filtered[df_filtered["Package"] == package]
    grp = pkg_df.groupby("Date").sum().reindex(full_dates, fill_value=0).reset_index()
    graph_and_table(grp, f"📦 Package — {package}")
