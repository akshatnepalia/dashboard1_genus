import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ================= PAGE CONFIG ================= #
st.set_page_config(layout="wide")

# Custom Styling
st.markdown("""
    <style>
        div.block-container {
            padding-top: 1.4rem;
        }
        thead tr th {
            background-color: #003A8C !important;
            color: white !important;
            font-weight: bold !important;
        }
        .stDateInput > div > input, .stSelectbox > div > div {
            padding: 0.30rem !important;
            font-size: 0.90rem !important;
        }
        .stRadio > label {
            font-size: 0.95rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# ================= HEADER ================= #
st.markdown("""
<div style='text-align:center; margin-bottom:0.5rem;'>
    <span style='font-size:35px; font-weight:800; color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:260px; height:4px; margin:6px auto 0 auto;
                background: linear-gradient(to right, #003A8C, #FFD700);
                border-radius: 4px;'>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<h4 style='text-align:center;'>📊 Meter Dashboard — WC/DT + Manpower</h4>",
    unsafe_allow_html=True
)

# ================= LOAD DATA ================= #
df = pd.read_excel("meter_data.xlsx")
df["Date"] = pd.to_datetime(df["Date"])

for col in ["WC-MI", "DT", "CI", "MI", "IN-HOUSE", "Supervisory"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df["Total_Manpower"] = df["CI"] + df["MI"] + df["IN-HOUSE"] + df["Supervisory"]

# ================= FILTERS ================= #
st.subheader("🔍 Filters")
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

df_filtered = df[(df["Date"] >= pd.to_datetime(start_date)) &
                 (df["Date"] <= pd.to_datetime(end_date))]

full_dates = pd.date_range("2025-11-01", "2025-11-26")


# ================= GRAPH + TABLE ================= #
def graph_and_table(data, title):

    data = data.copy()
    data["Total_WC_DT"] = data["WC-MI"] + data["DT"]
    max_mp = data["Total_Manpower"].max()

    fig = go.Figure()

    # WC-MI bars
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["WC-MI"], name="WC-MI",
        marker_color="#FF7C7C", hoverinfo="skip"
    ))

    # Tooltip formatting
    hovertemplate = (
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

    # DT bars with tooltip
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["DT"], base=data["WC-MI"], name="DT",
        marker_color="#FFD400",
        customdata=data[["Total_Manpower", "CI", "MI",
                         "IN-HOUSE", "Supervisory",
                         "Total_WC_DT", "WC-MI", "DT"]],
        hovertemplate=hovertemplate
    ))

    # Total Meters labels near bottom
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=[v * 0.02 for v in data["Total_WC_DT"]],
        text=[f"{v}" for v in data["Total_WC_DT"]],
        mode="text",
        textfont=dict(color="black", size=12),
        hoverinfo="skip",
        showlegend=False
    ))

    # Manpower line
    fig.add_trace(go.Scatter(
        x=data["Date"], y=data["Total_Manpower"] + max_mp * 0.20,
        mode="lines+markers+text", text=[f"{v}" for v in data["Total_Manpower"]],
        textposition="top center",
        textfont=dict(color="black", size=14),
        name="Total Manpower",
        line=dict(color="#003A8C", width=3),
        marker=dict(size=9, color="#003A8C"),
        yaxis="y2", hoverinfo="skip"
    ))

    fig.update_layout(
        height=600,
        hovermode="x unified",
        barmode="stack",
        template="plotly_white",
        margin=dict(l=10, r=10, t=30, b=80),
        xaxis=dict(
            tickvals=data["Date"],
            ticktext=[d.strftime("%d-%b") for d in data["Date"]],
            tickangle=45,
            tickfont=dict(size=12, color="black")
        ),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right")
    )

    st.plotly_chart(fig, use_container_width=True)

    # ================= TABLE FIXED ORDER ================= #
    pivot = data.pivot_table(
        columns="Date",
        values=["WC-MI", "DT", "Total_WC_DT", "Total_Manpower",
                "CI", "MI", "IN-HOUSE", "Supervisory"],
        aggfunc="sum"
    )

    order = ["Total_WC_DT", "WC-MI", "DT",
             "Total_Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"]

    pivot = pivot.reindex(order)
    pivot.index = [
        "🔷 Total Meters (WC+DT)", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]

    pivot = pivot.astype(int)
    pivot.columns = [d.strftime("%d-%b") for d in pivot.columns]

    st.subheader("📋 Daily Meter Deployment Summary")
    st.dataframe(pivot, use_container_width=True)


# ================= VIEW HANDLING ================= #
if view == "Combined View":
    grp = df_filtered.groupby("Date")[["WC-MI", "DT", "CI", "MI",
                                       "IN-HOUSE", "Supervisory",
                                       "Total_Manpower"]].sum()

    grp = grp.reindex(full_dates, fill_value=0).reset_index()
    grp.rename(columns={"index": "Date"}, inplace=True)

    graph_and_table(grp, "📌 All Packages")

else:
    pkg = df_filtered[df_filtered["Package"] == package]
    pkg = pkg.groupby("Date")[["WC-MI", "DT", "CI", "MI",
                               "IN-HOUSE", "Supervisory",
                               "Total_Manpower"]].sum()

    pkg = pkg.reindex(full_dates, fill_value=0).reset_index()
    pkg.rename(columns={"index": "Date"}, inplace=True)

    graph_and_table(pkg, f"📦 {package}")
