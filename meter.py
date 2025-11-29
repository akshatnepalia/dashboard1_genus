import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ================= PAGE CONFIG ================= #
st.set_page_config(layout="wide")

# ================= RESPONSIVE CSS ================= #
st.markdown("""
<style>
    /* Desktop Base Style */
    div.block-container {
        padding-top: 1rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    thead tr th {
        background-color: #003A8C !important;
        color: white !important;
        font-weight: bold !important;
        text-align:center !important;
    }

    /* 🔹 Mobile Responsive Style - width < 768px */
    @media(max-width: 768px) {
        div.block-container {
            padding-left: 0.4rem !important;
            padding-right: 0.4rem !important;
        }

        h4, span {
            font-size: 18px !important;
        }

        .stRadio > label {
            font-size: 12px !important;
        }

        .modebar {
            display: none !important;
        }

        .stPlotlyChart {
            height: 350px !important;
        }

        table {
            font-size: 10px !important;
        }

        th {
            font-size: 11px !important;
        }
        td {
            font-size: 10px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ================= HEADER ================= #
st.markdown("""
<div style='text-align:center; margin-bottom:0.5rem;'>
    <span style='font-size:55px; font-weight:800; color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:260px; height:4px; margin:6px auto 0 auto;
                background: linear-gradient(to right, #003A8C, #FFD700);
                border-radius: 4px;'></div>
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

# Full November range
full_dates = pd.date_range("2025-11-01", "2025-11-26")

# ================= FILTERS ================= #
st.subheader("🔍 Filters")
view = st.radio("Select View", ["Combined View", "Package Wise View"], horizontal=True)

start_date = st.date_input("Start Date", df["Date"].min())
end_date = st.date_input("End Date", df["Date"].max())

package = None
if view == "Package Wise View":
    package = st.selectbox("Select Package", sorted(df["Package"].unique()))

df_filtered = df[(df["Date"] >= pd.to_datetime(start_date)) &
                 (df["Date"] <= pd.to_datetime(end_date))]

# ================= PLOT + TABLE FUNCTION ================= #
def graph_and_table(data, title):
    data = data.copy()
    data["Total_WC_DT"] = data["WC-MI"] + data["DT"]
    peak_mp = data["Total_Manpower"].max()

    fig = go.Figure()

    # WC-MI bars
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["WC-MI"],
        name="WC-MI",
        marker_color="#FF7C7C",
        hoverinfo="skip"
    ))

    # Tooltip
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

    # DT bars (tooltip owner)
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["DT"], base=data["WC-MI"],
        name="DT",
        marker_color="#FFD400",
        customdata=data[["Total_Manpower","CI","MI","IN-HOUSE",
                         "Supervisory","Total_WC_DT","WC-MI","DT"]],
        hovertemplate=hovertemplate
    ))

    # Total Meters labels near bottom
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=[v * 0.01 for v in data["Total_WC_DT"]],
        text=[str(int(v)) for v in data["Total_WC_DT"]],
        mode="text",
        textfont=dict(color="black", size=11, family="Arial Black"),
        showlegend=False,
        hoverinfo="skip"
    ))

    # Total Manpower line with labels
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=data["Total_Manpower"] + peak_mp * 0.12,
        mode="lines+markers+text",
        text=[str(int(v)) for v in data["Total_Manpower"]],
        textposition="top center",
        textfont=dict(color="black", size=12),
        line=dict(color="#003A8C", width=3),
        marker=dict(size=8, color="#003A8C"),
        name="Total Manpower",
        yaxis="y2",
        hoverinfo="skip"
    ))

    fig.update_layout(
        title=title,
        height=550,
        barmode="stack",
        hovermode="x unified",
        xaxis=dict(
            tickvals=data["Date"],
            ticktext=[d.strftime("%d-%b") for d in data["Date"]],
            tickangle=45,
        ),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
        margin=dict(l=10, r=10, t=30, b=80)
    )

    st.plotly_chart(fig, use_container_width=True)

    # ================= TABLE (FIXED ORDER) ================= #
    pivot = data.pivot_table(
        columns="Date",
        values=["WC-MI", "DT", "Total_WC_DT", "Total_Manpower",
                "CI", "MI", "IN-HOUSE", "Supervisory"],
        aggfunc="sum"
    )

    # Make sure rows are in the correct logical order
    order = ["Total_WC_DT", "WC-MI", "DT",
             "Total_Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"]
    pivot = pivot.reindex(order)

    # Now label the rows properly
    pivot.index = [
        "🔷 Total Meters (WC+DT)",
        "WC-MI",
        "DT",
        "🟢 Total Manpower",
        "CI",
        "MI",
        "IN-HOUSE",
        "Supervisory"
    ]

    pivot = pivot.astype(int)
    pivot.columns = [d.strftime("%d-%b") for d in pivot.columns]

    st.subheader("📋 Daily Summary Table")
    st.dataframe(pivot, use_container_width=True)


# ================= APPLY VIEW ================= #
if view == "Combined View":
    grp = df_filtered.groupby("Date")[["WC-MI", "DT", "CI", "MI",
                                       "IN-HOUSE","Supervisory",
                                       "Total_Manpower"]].sum()

    grp = grp.reindex(full_dates, fill_value=0)
    grp.index.name = "Date"
    grp = grp.reset_index()

    graph_and_table(grp, "📌 All Packages")

else:
    pkg_df = df_filtered[df_filtered["Package"] == package]
    pkg = pkg_df.groupby("Date")[["WC-MI", "DT", "CI", "MI",
                                  "IN-HOUSE","Supervisory",
                                  "Total_Manpower"]].sum()

    pkg = pkg.reindex(full_dates, fill_value=0)
    pkg.index.name = "Date"
    pkg = pkg.reset_index()

    graph_and_table(pkg, f"📦 {package}")
