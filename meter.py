import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="Genus Meter Dashboard",
                   layout="wide",
                   page_icon="📊")

# =========================================================
# CUSTOM CSS
# =========================================================
st.markdown(
    """
<style>
    div.block-container {padding-top: 1.2rem;}
    thead tr th {
        background-color: #003A8C !important;
        color: white !important;
        font-weight: bold !important;
    }
    .kpi-card {
        padding: 0.7rem 1rem;
        border-radius: 12px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
    }
    .kpi-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748b;
        margin-bottom: 0.15rem;
    }
    .kpi-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0f172a;
    }
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
<div style='text-align:center;margin-bottom:0.5rem;'>
    <span style='font-size:42px;font-weight:800;color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:260px;height:4px;margin:6px auto;
                background: linear-gradient(to right, #003A8C, #FFD700);
                border-radius:4px;'>
    </div>
</div>
<h4 style='text-align:center;font-weight:700;margin-top:0.2rem;margin-bottom:0.8rem;'>
📊 Meter Dashboard — WC/DT + Manpower
</h4>
""",
    unsafe_allow_html=True,
)

# =========================================================
# DB ENGINE + TABLE INIT
# =========================================================


@st.cache_resource
def get_engine():
    db_url = st.secrets["DB_URL"]
    return create_engine(db_url, pool_pre_ping=True)


@st.cache_resource
def init_db():
    engine = get_engine()
    create_sql = """
    CREATE TABLE IF NOT EXISTS meter_data (
        id SERIAL PRIMARY KEY,
        date DATE NOT NULL,
        package TEXT NOT NULL,
        wc_mi INTEGER NOT NULL,
        dt INTEGER NOT NULL,
        ci INTEGER NOT NULL,
        mi INTEGER NOT NULL,
        in_house INTEGER NOT NULL,
        supervisory INTEGER NOT NULL
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))
    return True


init_db()  # ensure table exists


# =========================================================
# DATA LOADING
# =========================================================
@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    """Load data from Postgres and compute totals."""
    engine = get_engine()
    query = """
        SELECT date, package, wc_mi, dt, ci, mi, in_house, supervisory
        FROM meter_data
        ORDER BY date ASC;
    """
    df = pd.read_sql(query, engine)

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"]).dt.date

    num_cols = ["wc_mi", "dt", "ci", "mi", "in_house", "supervisory"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]

    return df


def clear_data_cache():
    load_data.clear()


# =========================================================
# UTILS
# =========================================================
def kfmt(v: float) -> str:
    """Short k formatting for KPIs."""
    try:
        v = float(v)
    except Exception:
        return str(v)
    if v >= 1000:
        return f"{v/1000:.1f}k"
    return str(int(v))


# =========================================================
# DASHBOARD GRAPH + TABLE
# =========================================================
def graph_and_table(data: pd.DataFrame, start_date, end_date):
    if data.empty:
        st.info("No data available for selected range.")
        return

    # --- Reindex to show all dates between start & end ---
    date_range = pd.date_range(start_date, end_date, freq="D").date
    grp = (
        data.groupby("date")[["wc_mi", "dt", "ci", "mi", "in_house", "supervisory",
                              "Total_Manpower", "Total_WC_DT"]]
        .sum()
        .reindex(date_range, fill_value=0)
        .reset_index()
        .rename(columns={"index": "date"})
    )

    # KPI values
    total_meters = grp["Total_WC_DT"].sum()

    peak_m_idx = grp["Total_WC_DT"].idxmax()
    peak_install_label = (
        f"{int(grp.loc[peak_m_idx,'Total_WC_DT'])} "
        f"on {grp.loc[peak_m_idx,'date'].strftime('%d-%b')}"
        if len(grp) > 0
        else "N/A"
    )

    peak_mp_idx = grp["Total_Manpower"].idxmax()
    peak_mp_label = (
        f"{int(grp.loc[peak_mp_idx,'Total_Manpower'])} "
        f"on {grp.loc[peak_mp_idx,'date'].strftime('%d-%b')}"
        if len(grp) > 0
        else "N/A"
    )

    # ---------- KPI CARDS ----------
    kc1, kc2, kc3 = st.columns(3)
    with kc1:
        st.markdown(
            f"""
        <div class="kpi-card">
            <div class="kpi-title">📦 Total Meters (WC+DT)</div>
            <div class="kpi-value">{kfmt(total_meters)}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with kc2:
        st.markdown(
            f"""
        <div class="kpi-card">
            <div class="kpi-title">📈 Peak Installation Day</div>
            <div class="kpi-value">{peak_install_label}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with kc3:
        st.markdown(
            f"""
        <div class="kpi-card">
            <div class="kpi-title">👥 Peak Manpower Day</div>
            <div class="kpi-value">{peak_mp_label}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # ---------- GRAPH ----------
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
        "DT: %{customdata[7]}<br>"
        "<extra></extra>"
    )

    custom = grp[
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
    ]

    # WC-MI bars
    fig.add_trace(
        go.Bar(
            x=grp["date"],
            y=grp["wc_mi"],
            name="WC-MI",
            marker_color="#FF7B7B",
            customdata=custom,
            hovertemplate=hovertemplate,
        )
    )

    # DT stacked on WC-MI
    fig.add_trace(
        go.Bar(
            x=grp["date"],
            y=grp["dt"],
            name="DT",
            marker_color="#FFD700",
            customdata=custom,
            hovertemplate=hovertemplate,
        )
    )

    # Total meters labels near bottom of bars
    fig.add_trace(
        go.Scatter(
            x=grp["date"],
            y=[m * 0.02 for m in grp["Total_WC_DT"]],
            mode="text",
            text=[str(int(v)) for v in grp["Total_WC_DT"]],
            textposition="bottom center",
            textfont=dict(color="black", size=11, family="Arial Black"),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Manpower line with labels
    fig.add_trace(
        go.Scatter(
            x=grp["date"],
            y=grp["Total_Manpower"],
            name="Total Manpower",
            mode="lines+markers+text",
            text=[f"<b>{int(v)}</b>" for v in grp["Total_Manpower"]],
            textposition="top center",
            line=dict(color="#003A8C", width=3),
            marker=dict(size=10, color="#003A8C"),
            yaxis="y2",
            hoverinfo="skip",
        )
    )

    tick_dates = grp["date"]
    fig.update_layout(
        height=550,
        barmode="stack",
        hovermode="closest",
        xaxis=dict(
            tickvals=tick_dates,
            ticktext=[d.strftime("%d-%b") for d in tick_dates],
            tickangle=45,
        ),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=30, b=80),
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------- TABLE ----------
    table = grp.set_index("date")[
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
    # format index into dd-MMM
    idx_dt = pd.to_datetime(table.index)
    table.index = idx_dt.strftime("%d-%b")

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
        table.style.apply(highlight_rows, axis=1), use_container_width=True
    )


# =========================================================
# ADMIN PANEL
# =========================================================
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False


def admin_login_ui():
    st.header("🔐 Admin Panel")

    if not st.session_state.admin_logged_in:
        with st.form("login_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            valid_user = st.secrets.get("ADMIN_USER", "admin")
            valid_pass = st.secrets.get("ADMIN_PASS", "12345")
            if user == valid_user and pwd == valid_pass:
                st.session_state.admin_logged_in = True
                st.success("Logged in ✔")
                st.experimental_rerun()
            else:
                st.error("Incorrect username or password.")
        return False
    else:
        st.success("Logged In ✔")
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.experimental_rerun()
        return True


def admin_panel():
    logged_in = admin_login_ui()
    if not logged_in:
        return

    st.markdown("### ➕ Insert New Data")

    with st.form("insert_form"):
        c1, c2 = st.columns(2)
        with c1:
            date_val = st.date_input("Date")
            package = st.text_input("Package", value="PKG-1")
        with c2:
            wc_mi = st.number_input("WC-MI", min_value=0, step=1)
            dt = st.number_input("DT", min_value=0, step=1)

        col3, col4, col5, col6 = st.columns(4)
        with col3:
            ci = st.number_input("CI", min_value=0, step=1)
        with col4:
            mi = st.number_input("MI", min_value=0, step=1)
        with col5:
            in_house = st.number_input("IN-HOUSE", min_value=0, step=1)
        with col6:
            supervisory = st.number_input("Supervisory", min_value=0, step=1)

        submitted = st.form_submit_button("Insert Row")

    if submitted:
        try:
            engine = get_engine()
            insert_sql = text(
                """
                INSERT INTO meter_data
                (date, package, wc_mi, dt, ci, mi, in_house, supervisory)
                VALUES (:date, :package, :wc_mi, :dt, :ci, :mi, :in_house, :supervisory)
                """
            )
            with engine.begin() as conn:
                conn.execute(
                    insert_sql,
                    dict(
                        date=date_val,
                        package=package,
                        wc_mi=int(wc_mi),
                        dt=int(dt),
                        ci=int(ci),
                        mi=int(mi),
                        in_house=int(in_house),
                        supervisory=int(supervisory),
                    ),
                )
            clear_data_cache()
            st.success("Row inserted & dashboard updated ✅")
        except Exception as e:
            st.error(f"Insert failed: {e}")

    st.markdown("### 🔎 Latest Records")
    try:
        df = load_data()
        if not df.empty:
            st.dataframe(df.tail(20), use_container_width=True)
        else:
            st.info("No data available yet.")
    except Exception as e:
        st.error(f"Error loading data: {e}")


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:
    st.markdown("## 📂 Navigation")
    page = st.radio("Go to", ["Dashboard", "Admin Panel"])

# =========================================================
# MAIN ROUTING
# =========================================================
try:
    df_all = load_data()
except Exception as e:
    st.error(f"Database connection error: {e}")
    df_all = pd.DataFrame()

if page == "Dashboard":
    st.markdown("### 🔍 Filters")

    if df_all.empty:
        st.info("No data in database yet. Add some rows from the Admin Panel.")
    else:
        min_d = df_all["date"].min()
        max_d = df_all["date"].max()

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            view_mode = st.radio(
                "View Mode", ["Combined View", "Package Wise View"], horizontal=True
            )
        with c2:
            start_d = st.date_input("Start Date", min_d, min_value=min_d, max_value=max_d)
        with c3:
            end_d = st.date_input("End Date", max_d, min_value=min_d, max_value=max_d)

        if start_d > end_d:
            st.error("Start Date cannot be after End Date.")
        else:
            df_filtered = df_all[
                (df_all["date"] >= start_d) & (df_all["date"] <= end_d)
            ]

            if view_mode == "Combined View":
                graph_and_table(df_filtered, start_d, end_d)
            else:
                pkg_list = sorted(df_all["package"].unique())
                pkg = st.selectbox("Select Package", pkg_list)
                df_pkg = df_filtered[df_filtered["package"] == pkg]
                graph_and_table(df_pkg, start_d, end_d)

elif page == "Admin Panel":
    admin_panel()
