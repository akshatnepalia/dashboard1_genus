import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ================= PAGE CONFIG ================= #
st.set_page_config(layout="wide")

# Compact Styling + Title visible
st.markdown("""
    <style>
        div.block-container {
            padding-top: 1.4rem;
        }
        .stDateInput > div > input, .stSelectbox > div > div {
            padding: 0.25rem !important;
            font-size: 0.85rem !important;
            background: white !important;
            color: black !important;
        }
        .stRadio > label {
            font-size: 0.92rem !important;
        }
        .element-container {
            margin-bottom: 0.35rem !important;
        }
        thead tr th {
            background-color: #003A8C !important;
            color: white !important;
            font-weight: bold !important;
        }
    </style>
""", unsafe_allow_html=True)

# ================= COMPANY NAME + DASHBOARD TITLE ================= #
st.markdown("""
<div style='text-align:center; margin-bottom:0.3rem;'>
    <span style='font-size:28px; font-weight:800; color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:260px; height:4px; margin:6px auto 0 auto;
                background: linear-gradient(to right, #003A8C, #FFD700);
                border-radius: 4px;'>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<h4 style='text-align:center; font-weight:700; margin-top:0.4rem; margin-bottom:0.8rem;'>
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
st.markdown("<p style='font-size:16px; font-weight:600; margin-bottom:0.2rem;'>🔍 Filters</p>",
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

# Filtered Data
df_filtered = df[
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))
]

full_dates = pd.date_range("2025-11-01", "2025-11-26")

# ================= GRAPH + TABLE ================= #
def graph_and_table(data, title):
    data = data.copy()
    data["Total_WC_DT"] = data["WC-MI"] + data["DT"]
    max_manpower = data["Total_Manpower"].max()

    fig = go.Figure()

    # WC-MI Bars
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["WC-MI"],
        name="WC-MI", marker_color="#FF6666", hoverinfo="skip"
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

    # DT Bars with Hover
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["DT"], base=data["WC-MI"],
        name="DT", marker_color="#FFD700",
        customdata=data[["Total_Manpower", "CI", "MI",
                         "IN-HOUSE", "Supervisory",
                         "Total_WC_DT", "WC-MI", "DT"]],
        hovertemplate=hovertemplate
    ))

    # Total Meters Labels — cleaner & visible
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=[int(v * 0.02) for v in data["Total_WC_DT"]],
        text=[f"{int(v)}" for v in data["Total_WC_DT"]],
        mode="text",
        textposition="bottom center",
        textfont=dict(color="black", size=11, family="Arial Black"),
        hoverinfo="skip",
        showlegend=False
    ))

    # Manpower Line + Labels
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=data["Total_Manpower"] + max_manpower * 0.18,
        mode="lines+markers+text",
        name="Total Manpower",
        text=[f"<b>{int(v)}</b>" for v in data["Total_Manpower"]],
        textposition="top center",
        textfont=dict(color="black", size=12),
        line=dict(color="#003A8C", width=3),
        marker=dict(size=8, color="#003A8C"),
        yaxis="y2",
        hoverinfo="skip"
    ))

    # Layout
    fig.update_layout(
        barmode="stack",
        bargap=0.18,
        height=550,
        hovermode="x unified",
        template="plotly_white",
        xaxis=dict(
            tickvals=data["Date"],
            ticktext=[d.strftime("%d-%b") for d in data["Date"]],
            tickangle=45,
            tickfont=dict(size=11, family="Arial Black", color="black")
        ),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
        margin=dict(l=10, r=10, t=30, b=80),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Table
    pivot = data.pivot_table(
        columns="Date",
        values=["WC-MI", "DT", "Total_WC_DT", "Total_Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"],
        aggfunc="sum"
    )

    pivot.index = [
        "🔷 Total Meters (WC+DT)", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]

    pivot.columns = [c.strftime("%d-%b") for c in pivot.columns]
    pivot = pivot.astype(int)

    def highlight(row):
        if row.name in ["🔷 Total Meters (WC+DT)", "🟢 Total Manpower"]:
            return ['font-weight: bold; background-color: #E6F0FF'] * len(row)
        return [''] * len(row)

    st.dataframe(pivot.style.apply(highlight, axis=1), use_container_width=True)

# ================= VIEW HANDLING ================= #
if view == "Combined View":
    df_grp = df_filtered.groupby("Date")[["WC-MI", "DT", "CI", "MI",
                                          "IN-HOUSE", "Supervisory",
                                          "Total_Manpower"]].sum()

    df_grp = df_grp.reindex(full_dates, fill_value=0).reset_index()
    df_grp = df_grp.rename(columns={"index": "Date"})
    graph_and_table(df_grp, "📌 All Packages")

else:
    df_pkg = df_filtered[df_filtered["Package"] == package]
    df_pkg = df_pkg.groupby("Date")[["WC-MI", "DT", "CI", "MI",
                                     "IN-HOUSE", "Supervisory",
                                     "Total_Manpower"]].sum()

    df_pkg = df_pkg.reindex(full_dates, fill_value=0).reset_index()
    df_pkg = df_pkg.rename(columns={"index": "Date"})
    graph_and_table(df_pkg, f"📦 {package}")
