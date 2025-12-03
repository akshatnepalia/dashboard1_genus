import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ================= PAGE CONFIG ================= #
st.set_page_config(layout="wide", page_title="Genus Meter Dashboard")

# ================= CUSTOM CSS ================= #
st.markdown("""
<style>
    div.block-container {padding-top: 1.0rem;}
    thead tr th {
        background-color: #003A8C !important;
        color: white !important;
        font-weight: bold !important;
    }
    .kpi-block {
        background-color: #F2F7FF;
        border: 2px solid #003A8C;
        border-radius: 10px;
        padding: 10px 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 900;
        color: #003A8C;
        margin-top: 4px;
    }
    .kpi-label {
        font-size: 14px;
        font-weight: 600;
        color: #333;
    }
    .footer-small {
        font-size: 12px;
        color: #555;
        text-align:center;
        margin-top: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# ================= HEADER ================= #
st.markdown("""
<div style='text-align:center;margin-bottom:0.5rem;'>
    <a href='https://genuspower.com' target='_blank'
       style='text-decoration:none;'>
        <span style='font-size:42px;font-weight:800;color:#003A8C;'>
            Genus Power Infrastructures Ltd.
        </span>
    </a>
    <div style='width:260px;height:4px;margin:6px auto;
                background:#FFD700;border-radius:4px;'></div>
</div>

<h4 style='text-align:center;font-weight:700;margin-top:0.2rem;margin-bottom:0.8rem;'>
📊 Meter Dashboard — WC/DT + Manpower
</h4>
""", unsafe_allow_html=True)

# ================= DB LOAD ================= #
engine = create_engine(st.secrets["DB_URL"])

@st.cache_data
def load_data():
    df = pd.read_sql("SELECT * FROM meter_data ORDER BY date ASC", engine)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    num_cols = ["wc_mi", "dt", "ci", "mi", "in_house", "supervisory"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]
    return df

df = load_data()

# FULL dynamic date range based on DB
full_dates = pd.date_range(df["date"].min(), df["date"].max()).date

# ================= SESSION FOR ADMIN LOGIN ================= #
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

# ================= HELPERS ================= #
def kfmt(v):
    return f"{v/1000:.1f}k" if v >= 1000 else str(int(v))

def show_footer():
    st.markdown(
        "<div class='footer-small'>"
        "Developed for <b>Genus Power</b> • "
        "<a href='mailto:analytics@genuspower.com'>Contact Analytics Team</a>"
        "</div>",
        unsafe_allow_html=True,
    )

def admin_login_ui():
    st.markdown("### 🔐 Admin Login")
    with st.form("admin_login_form", clear_on_submit=True):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        ok = st.form_submit_button("Login")
    if ok:
        if (
            user == st.secrets.get("ADMIN_USER", "")
            and pwd == st.secrets.get("ADMIN_PASS", "")
        ):
            st.session_state["admin_logged_in"] = True
            st.success("Login successful ✅")
            st.rerun()
        else:
            st.error("Incorrect username or password.")

# ================= GRAPH + TABLE FUNCTION ================= #
def graph_and_table(data: pd.DataFrame):
    data = data.copy()

    # --- KPI values --- #
    total_meters = data["Total_WC_DT"].sum()

    if len(data) > 0 and data["Total_WC_DT"].sum() > 0:
        peak_m_idx = data["Total_WC_DT"].idxmax()
        peak_install_label = (
            f"{int(data.loc[peak_m_idx,'Total_WC_DT'])} on "
            f"{data.loc[peak_m_idx,'date'].strftime('%d-%b')}"
        )
    else:
        peak_install_label = "N/A"

    if len(data) > 0 and data["Total_Manpower"].sum() > 0:
        peak_mp_idx = data["Total_Manpower"].idxmax()
        peak_mp_label = (
            f"{int(data.loc[peak_mp_idx,'Total_Manpower'])} on "
            f"{data.loc[peak_mp_idx,'date'].strftime('%d-%b')}"
        )
    else:
        peak_mp_label = "N/A"

    # --- KPI Scoreboard --- #
    k1, k2, k3 = st.columns(3)
    k1.markdown(
        f"<div class='kpi-block'>"
        f"<div class='kpi-label'>📦 Total Meters Installed</div>"
        f"<div class='kpi-value'>{kfmt(total_meters)}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    k2.markdown(
        f"<div class='kpi-block'>"
        f"<div class='kpi-label'>📈 Peak Installation</div>"
        f"<div class='kpi-value'>{peak_install_label}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    k3.markdown(
        f"<div class='kpi-block'>"
        f"<div class='kpi-label'>👥 Peak Manpower</div>"
        f"<div class='kpi-value'>{peak_mp_label}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # --- GRAPH --- #
    fig = go.Figure()

    hovertemplate = (
        "Date: %{x}<br><br>"
        "Total Manpower: %{customdata[0]}<br>"
        "CI: %{customdata[1]}<br>"
        "MI: %{customdata[2]}<br>"
        "IN-HOUSE: %{customdata[3]}<br>"
        "Supervisory: %{customdata[4]}<br><br>"
        "Total Meters: %{customdata[5]}<br>"
        "WC-MI: %{customdata[6]}<br>"
        "DT: %{customdata[7]}<br><extra></extra>"
    )

    fig.add_trace(
        go.Bar(
            x=data["date"],
            y=data["wc_mi"],
            name="WC-MI",
            marker_color="#FF7B7B",
            customdata=data[
                [
                    "Total_Manpower",
                    "ci",
                    "mi",
                    "in_house",
                    "supervisory",
                    "Total_WC_DT",
                    "wc_mi",
                    "dt",
                ]
            ],
            hovertemplate=hovertemplate,
        )
    )

    fig.add_trace(
        go.Bar(
            x=data["date"],
            y=data["dt"],
            name="DT",
            marker_color="#FFD700",
            customdata=data[
                [
                    "Total_Manpower",
                    "ci",
                    "mi",
                    "in_house",
                    "supervisory",
                    "Total_WC_DT",
                    "wc_mi",
                    "dt",
                ]
            ],
            hovertemplate=hovertemplate,
        )
    )

    # Total meters labels near bottom
    max_total = data["Total_WC_DT"].max() if len(data) else 0
    baseline_y = max_total * 0.03 if max_total > 0 else 5

    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=[baseline_y] * len(data),
            text=[kfmt(v) for v in data["Total_WC_DT"]],
            mode="text",
            textposition="bottom center",
            textfont=dict(size=11, color="black"),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Total Manpower line
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["Total_Manpower"],
            name="Total Manpower",
            mode="lines+markers+text",
            text=[f"<b>{int(v)}</b>" for v in data["Total_Manpower"]],
            textposition="top center",
            line=dict(color="#003A8C", width=3),
            marker=dict(size=10, color="#003A8C"),
            yaxis="y2",
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        height=550,
        barmode="stack",
        hovermode="closest",
        xaxis=dict(
            tickvals=data["date"],
            ticktext=[d.strftime("%d-%b") for d in data["date"]],
            tickangle=45,
        ),
        yaxis2=dict(overlaying="y", side="right"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- TABLE --- #
    if len(data) == 0:
        st.info("No data available for selected filters.")
        return

    table = data.set_index("date")[
        [
            "Total_WC_DT",
            "wc_mi",
            "dt",
            "Total_Manpower",
            "ci",
            "mi",
            "in_house",
            "supervisory",
        ]
    ]

    table.index = pd.to_datetime(table.index, errors="coerce")
    table.index = table.index.strftime("%d-%b")

    table = table.T
    table.index = [
        "🔷 Total Meters (WC+DT)",
        "WC-MI",
        "DT",
        "🟢 Total Manpower",
        "CI",
        "MI",
        "IN-HOUSE",
        "Supervisory",
    ]
    table = table.astype(int)

    def highlight_rows(row):
        if row.name == "🔷 Total Meters (WC+DT)":
            return ["background-color:#CDE4FF;font-weight:bold"] * len(row)
        if row.name == "🟢 Total Manpower":
            return ["background-color:#D4F7D4;font-weight:bold"] * len(row)
        return [""] * len(row)

    st.subheader("📋 Date-wise Summary Table")
    st.dataframe(
        table.style.apply(highlight_rows, axis=1),
        use_container_width=True,
    )

# ================= ADMIN PANEL ================= #
def admin_panel_ui():
    st.markdown("### 🛠 Admin Panel — Add Data")

    with st.form("data_entry_form"):
        c1, c2 = st.columns(2)
        with c1:
            date_val = st.date_input("Date")
            package_val = st.selectbox("Package", sorted(df["package"].unique()))
        with c2:
            wc_mi_val = st.number_input("WC-MI", min_value=0, step=1)
            dt_val = st.number_input("DT", min_value=0, step=1)

        c3, c4, c5, c6 = st.columns(4)
        with c3:
            ci_val = st.number_input("CI", min_value=0, step=1)
        with c4:
            mi_val = st.number_input("MI", min_value=0, step=1)
        with c5:
            in_house_val = st.number_input("IN-HOUSE", min_value=0, step=1)
        with c6:
            supervisory_val = st.number_input("Supervisory", min_value=0, step=1)

        submitted = st.form_submit_button("✅ Save to Database")

    if submitted:
        try:
            ins_query = text("""
                INSERT INTO meter_data (date, package, wc_mi, dt, ci, mi, in_house, supervisory)
                VALUES (:date, :package, :wc_mi, :dt, :ci, :mi, :in_house, :supervisory)
            """)
            with engine.begin() as conn:
                conn.execute(
                    ins_query,
                    {
                        "date": date_val,
                        "package": package_val,
                        "wc_mi": wc_mi_val,
                        "dt": dt_val,
                        "ci": ci_val,
                        "mi": mi_val,
                        "in_house": in_house_val,
                        "supervisory": supervisory_val,
                    },
                )
            st.success("✅ Data added successfully. Dashboard will reflect it on next load.")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"❌ Database Error: {e}")

    st.markdown("---")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🔁 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    with c2:
        if st.button("🚪 Logout Admin"):
            st.session_state["admin_logged_in"] = False
            st.success("Logged out.")
            st.rerun()

# ================= TABS: DASHBOARD & ADMIN ================= #
tab1, tab2 = st.tabs(["📊 Dashboard", "🔐 Admin Panel"])

with tab1:
    # ----- Dashboard Tab ----- #
    st.markdown("### 📈 Dashboard View")

    fc1, fc2, fc3 = st.columns([2, 1, 1])
    with fc1:
        view = st.radio("View Mode", ["Combined View", "Package Wise View"], horizontal=True)
    with fc2:
        start_date = st.date_input("Start Date", df["date"].min())
    with fc3:
        end_date = st.date_input("End Date", df["date"].max())

    df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

    if view == "Package Wise View":
        package = st.selectbox("Select Package", sorted(df["package"].unique()))
        df_filtered = df_filtered[df_filtered["package"] == package]

    # Group & Reindex
    grp = (
        df_filtered.groupby("date")[
            [
                "wc_mi",
                "dt",
                "ci",
                "mi",
                "in_house",
                "supervisory",
                "Total_Manpower",
                "Total_WC_DT",
            ]
        ]
        .sum()
        .reindex(full_dates, fill_value=0)
        .reset_index()
    )

    graph_and_table(grp)
    show_footer()

with tab2:
    # ----- Admin Tab ----- #
    if not st.session_state["admin_logged_in"]:
        admin_login_ui()
    else:
        admin_panel_ui()
    show_footer()
