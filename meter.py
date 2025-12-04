import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine

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
    <span style='font-size:42px;font-weight:800;color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:260px;height:4px;margin:6px auto;background:#FFD700;border-radius:4px;'></div>
</div>

<h4 style='text-align:center;font-weight:700;margin-top:0.2rem;margin-bottom:0.8rem;'>
📊 Meter Dashboard — WC/DT + Manpower
</h4>
""", unsafe_allow_html=True)


# =============== DB LOADER =============== #
@st.cache_data(show_spinner=True)
def load_data() -> pd.DataFrame:
    """
    Load data from Neon Postgres via SQLAlchemy.
    Assumes table: meter_data(date, package, wc_mi, dt, ci, mi, in_house, supervisory, sum).
    """
    db_url = st.secrets["DB_URL"]
    engine = create_engine(db_url)

    query = """
        SELECT
            date,
            package,
            wc_mi,
            dt,
            ci,
            mi,
            in_house,
            supervisory,
            sum
        FROM meter_data
        ORDER BY date ASC, package ASC
    """
    df = pd.read_sql(query, engine)

    # Normalize column names to match your old Excel-style names
    df = df.rename(columns={
        "date": "Date",
        "package": "Package",
        "wc_mi": "WC-MI",
        "dt": "DT",
        "ci": "CI",
        "mi": "MI",
        "in_house": "IN-HOUSE",
        "supervisory": "Supervisory"
    })

    # Convert types
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    num_cols = ["WC-MI", "DT", "CI", "MI", "IN-HOUSE", "Supervisory"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    # Calculated columns
    df["Total_Manpower"] = df["CI"] + df["MI"] + df["IN-HOUSE"] + df["Supervisory"]
    df["Total_Meters"] = df["WC-MI"] + df["DT"]

    return df


# =============== SMALL HELPERS =============== #
def kfmt(v: float) -> str:
    """Format number for 'k' style labels at bottom."""
    v = float(v)
    if v >= 1000:
        return f"{v/1000:.1f}k"
    return str(int(v))


# =============== MAIN GRAPH + TABLE BLOCK =============== #
def graph_and_table(data: pd.DataFrame, title: str):
    data = data.sort_values("Date").copy()

    # Safety: recalc totals
    data["Total_Manpower"] = data["CI"] + data["MI"] + data["IN-HOUSE"] + data["Supervisory"]
    data["Total_Meters"] = data["WC-MI"] + data["DT"]

    # ===== KPIs ===== #
    total_meters_sum = data["Total_Meters"].sum()

    peak_meter_idx = data["Total_Meters"].idxmax()
    peak_install_label = f"{int(data.loc[peak_meter_idx, 'Total_Meters'])} on {data.loc[peak_meter_idx, 'Date'].strftime('%d-%b')}"

    peak_mp_idx = data["Total_Manpower"].idxmax()
    peak_mp_label = f"{int(data.loc[peak_mp_idx, 'Total_Manpower'])} on {data.loc[peak_mp_idx, 'Date'].strftime('%d-%b')}"

    k1, k2, k3 = st.columns(3)
    k1.metric("📦 Total Meters (WC+DT)", kfmt(total_meters_sum))
    k2.metric("📈 Peak Installation (Meters)", peak_install_label)
    k3.metric("👥 Peak Manpower", peak_mp_label)

    # ===== GRAPH ===== #
    fig = go.Figure()

    # Tooltip exactly as you wanted
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

    custom = data[["Total_Manpower", "CI", "MI",
                   "IN-HOUSE", "Supervisory",
                   "Total_Meters", "WC-MI", "DT"]]

    # WC-MI bar (bottom)
    fig.add_trace(go.Bar(
        x=data["Date"],
        y=data["WC-MI"],
        name="WC-MI",
        marker_color="#FF7B7B",
        customdata=custom,
        hovertemplate=hovertemplate
    ))

    # DT bar (stacked on WC-MI)
    fig.add_trace(go.Bar(
        x=data["Date"],
        y=data["DT"],
        name="DT",
        marker_color="#FFD700",
        customdata=custom,
        hovertemplate=hovertemplate
    ))

    # Total Meters label at bottom (inside or just above axes) in k format
    peak_meter = data["Total_Meters"].max() or 1
    bottom_y = peak_meter * 0.02  # small positive height, same for all

    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=[bottom_y] * len(data),
        text=[f"<b>{kfmt(v)}</b>" for v in data["Total_Meters"]],
        mode="text",
        textposition="bottom center",
        textfont=dict(color="black", size=11, family="Arial Black"),
        showlegend=False,
        hoverinfo="skip"
    ))

    # Total manpower line + value labels above points
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=data["Total_Manpower"],
        name="Total Manpower",
        mode="lines+markers+text",
        text=[f"<b>{int(v)}</b>" for v in data["Total_Manpower"]],
        textposition="top center",
        textfont=dict(color="black", size=12),
        line=dict(color="#003A8C", width=3),
        marker=dict(size=8, color="#003A8C"),
        yaxis="y2",
        hoverinfo="skip"
    ))

    # X-axis ticks = all dates
    full_dates = pd.date_range(data["Date"].min(), data["Date"].max())

    fig.update_layout(
        title=title,
        barmode="stack",
        height=550,
        hovermode="closest",
        xaxis=dict(
            tickvals=full_dates,
            ticktext=[d.strftime("%d-%b") for d in full_dates],
            tickangle=45
        ),
        yaxis=dict(title="Meters (WC-MI + DT)"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=10, r=10, t=50, b=80),
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ===== TABLE (old format: rows = metrics, columns = dates) ===== #
    table = data.set_index("Date")[[
        "Total_Meters", "WC-MI", "DT",
        "Total_Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]]

    # Index is Date → convert to dd-MMM and transpose
    table.index = pd.to_datetime(table.index).strftime("%d-%b")
    table = table.T

    table.index = [
        "🔷 Total Meters (WC+DT)",
        "WC-MI",
        "DT",
        "🟢 Total Manpower",
        "CI",
        "MI",
        "IN-HOUSE",
        "Supervisory"
    ]

    table = table.astype(int)

    def highlight_rows(row):
        if row.name == "🔷 Total Meters (WC+DT)":
            return ['background-color:#CDE4FF;font-weight:bold'] * len(row)
        if row.name == "🟢 Total Manpower":
            return ['background-color:#D4F7D4;font-weight:bold'] * len(row)
        return [''] * len(row)

    st.subheader("📋 Date-wise Summary Table")
    st.dataframe(
        table.style.apply(highlight_rows, axis=1),
        use_container_width=True
    )


# ================= MAIN APP ================= #
try:
    df = load_data()
except Exception as e:
    st.error("❌ Could not connect to the database. Please check DB_URL in secrets.")
    st.exception(e)
    st.stop()

# ===== Filters ===== #
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

mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
df_filtered = df.loc[mask]

if df_filtered.empty:
    st.warning("No data for selected period.")
    st.stop()

# ===== View Logic ===== #
if view == "Combined View":
    grp = df_filtered.groupby("Date")[[
        "WC-MI", "DT", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]].sum().reset_index()
    graph_and_table(grp, "📌 All Packages — Combined View")

else:
    df_pkg = df_filtered[df_filtered["Package"] == package]
    grp = df_pkg.groupby("Date")[[
        "WC-MI", "DT", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]].sum().reset_index()
    graph_and_table(grp, f"📦 Package — {package}")
