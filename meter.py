import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import date

# ===================== BASIC CONFIG ===================== #
st.set_page_config(page_title="Genus Meter Dashboard",
                   layout="wide",
                   initial_sidebar_state="expanded")

# ---------- CSS ---------- #
st.markdown("""
<style>
    div.block-container {padding-top: 1.2rem;}
    thead tr th {
        background-color: #003A8C !important;
        color: white !important;
        font-weight: bold !important;
    }
    .kpi-card {
        padding: 0.8rem 1rem;
        border-radius: 0.9rem;
        background: #f8fafc;
        border: 1px solid #e5e7eb;
    }
    .kpi-label {
        font-size: 0.9rem;
        color: #6b7280;
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #111827;
    }
</style>
""", unsafe_allow_html=True)

# ===================== HEADER ===================== #
st.markdown("""
<div style='text-align:center;margin-bottom:0.5rem;'>
    <span style='font-size:42px;font-weight:800;color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:260px;height:4px;margin:6px auto;
                background: linear-gradient(to right,#003A8C,#FFD700);
                border-radius:4px;'></div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<h4 style='text-align:center;font-weight:700;margin-top:0.1rem;margin-bottom:0.8rem;'>
📊 Meter Dashboard — WC/DT + Manpower
</h4>
""", unsafe_allow_html=True)

# ===================== CONSTANTS ===================== #
ALLOWED_PACKAGES = [
    "TN-95", "TN-96", "TN-97",
    "TN-58", "TN-59", "TN-60",
    "TN-32", "TN-33", "TN-34",
]

ADMIN_USER = st.secrets.get("ADMIN_USER", "admin")
ADMIN_PASS = st.secrets.get("ADMIN_PASS", "12345")

# ===================== DB CONNECTION ===================== #
@st.cache_resource
def get_engine():
    db_url = st.secrets["DB_URL"]
    engine = create_engine(db_url, pool_pre_ping=True)
    return engine


@st.cache_resource
def init_db():
    """Create table & unique index if they don't exist."""
    engine = get_engine()
    ddl_table = """
    CREATE TABLE IF NOT EXISTS meter_data (
        id SERIAL PRIMARY KEY,
        date DATE NOT NULL,
        package TEXT NOT NULL,
        wc_mi INTEGER NOT NULL DEFAULT 0,
        dt INTEGER NOT NULL DEFAULT 0,
        ci INTEGER NOT NULL DEFAULT 0,
        mi INTEGER NOT NULL DEFAULT 0,
        in_house INTEGER NOT NULL DEFAULT 0,
        supervisory INTEGER NOT NULL DEFAULT 0
    );
    """
    ddl_index = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_meter_date_package
    ON meter_data(date, package);
    """
    with engine.begin() as conn:
        conn.execute(text(ddl_table))
        conn.execute(text(ddl_index))
    return True


@st.cache_data
def load_data():
    """Read all data from DB with computed columns."""
    engine = get_engine()
    query = """
    SELECT
        date,
        package,
        wc_mi,
        dt,
        ci,
        mi,
        in_house,
        supervisory
    FROM meter_data
    ORDER BY date ASC;
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"]).dt.date

    num_cols = ["wc_mi", "dt", "ci", "mi", "in_house", "supervisory"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]
    return df


def clear_cache():
    load_data.clear()


def upsert_row(row):
    """Insert or update a single Date+Package row."""
    engine = get_engine()
    stmt = text("""
        INSERT INTO meter_data
            (date, package, wc_mi, dt, ci, mi, in_house, supervisory)
        VALUES
            (:date, :package, :wc_mi, :dt, :ci, :mi, :in_house, :supervisory)
        ON CONFLICT (date, package)
        DO UPDATE SET
            wc_mi      = EXCLUDED.wc_mi,
            dt         = EXCLUDED.dt,
            ci         = EXCLUDED.ci,
            mi         = EXCLUDED.mi,
            in_house   = EXCLUDED.in_house,
            supervisory= EXCLUDED.supervisory;
    """)
    with engine.begin() as conn:
        conn.execute(stmt, row)
    clear_cache()


def kfmt(v: float) -> str:
    return f"{v/1000:.1f}k" if v >= 1000 else str(int(v))


# Ensure table exists
init_db()

# ===================== NAVIGATION ===================== #
mode = st.sidebar.radio("🔀 Navigate", ["Dashboard", "Admin Panel"])

# ====================================================== #
#                       DASHBOARD                        #
# ====================================================== #
def graph_and_table(df_view: pd.DataFrame):
    if df_view.empty:
        st.info("No data available for the selected filters.")
        return

    # ---------- KPI Calculations ---------- #
    total_meters = int(df_view["Total_WC_DT"].sum())

    peak_m_idx = df_view["Total_WC_DT"].idxmax()
    peak_install_label = (
        f"{int(df_view.loc[peak_m_idx, 'Total_WC_DT'])} on "
        f"{df_view.loc[peak_m_idx, 'date'].strftime('%d-%b')}"
    )

    peak_mp_idx = df_view["Total_Manpower"].idxmax()
    peak_mp_label = (
        f"{int(df_view.loc[peak_mp_idx, 'Total_Manpower'])} on "
        f"{df_view.loc[peak_mp_idx, 'date'].strftime('%d-%b')}"
    )

    # ---------- KPI cards ---------- #
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"<div class='kpi-card'>"
            f"<div class='kpi-label'>📦 Total Meters (WC+DT)</div>"
            f"<div class='kpi-value'>{kfmt(total_meters)}</div>"
            f"</div>", unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"<div class='kpi-card'>"
            f"<div class='kpi-label'>📈 Peak Installation (Meters)</div>"
            f"<div class='kpi-value'>{peak_install_label}</div>"
            f"</div>", unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"<div class='kpi-card'>"
            f"<div class='kpi-label'>👥 Peak Manpower</div>"
            f"<div class='kpi-value'>{peak_mp_label}</div>"
            f"</div>", unsafe_allow_html=True
        )

    # ---------- Graph ---------- #
    full_dates = pd.date_range(df_view["date"].min(), df_view["date"].max()).date

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

    fig = go.Figure()

    # WC-MI bars
    fig.add_trace(go.Bar(
        x=df_view["date"],
        y=df_view["wc_mi"],
        name="WC-MI",
        marker_color="#FF7B7B",
        customdata=df_view[[
            "Total_Manpower", "ci", "mi",
            "in_house", "supervisory",
            "Total_WC_DT", "wc_mi", "dt"
        ]],
        hovertemplate=hovertemplate
    ))

    # DT stacked bars
    fig.add_trace(go.Bar(
        x=df_view["date"],
        y=df_view["dt"],
        name="DT",
        marker_color="#FFD700",
        customdata=df_view[[
            "Total_Manpower", "ci", "mi",
            "in_house", "supervisory",
            "Total_WC_DT", "wc_mi", "dt"
        ]],
        hovertemplate=hovertemplate
    ))

    # Manpower line
    fig.add_trace(go.Scatter(
        x=df_view["date"],
        y=df_view["Total_Manpower"],
        name="Total Manpower",
        mode="lines+markers+text",
        text=[f"<b>{int(v)}</b>" for v in df_view["Total_Manpower"]],
        textposition="top center",
        line=dict(color="#003A8C", width=3),
        marker=dict(size=9, color="#003A8C"),
        yaxis="y2",
        hoverinfo="skip"
    ))

    # ===== NEW: Total meters (k) labels just below bar tops ===== #
    fig.add_trace(go.Scatter(
        x=df_view["date"],
        y=df_view["Total_WC_DT"],
        mode="text",
        text=[kfmt(v) for v in df_view["Total_WC_DT"]],
        textposition="bottom center",      # just below the bar top
        textfont=dict(size=11, color="#444"),
        hoverinfo="skip",
        showlegend=False
    ))
    # ============================================================ #

    fig.update_layout(
        height=580,
        barmode="stack",
        hovermode="closest",
        xaxis=dict(
            tickvals=full_dates,
            ticktext=[d.strftime("%d-%b") for d in full_dates],
            tickangle=45
        ),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------- TABLE ---------- #
    table = df_view.set_index("date")[[
        "Total_WC_DT", "wc_mi", "dt",
        "Total_Manpower", "ci", "mi", "in_house", "supervisory"
    ]]

    # FIX: make index datetime before strftime (prevents AttributeError)
    table.index = pd.to_datetime(table.index).strftime("%d-%b")

    table = table.T

    table.index = [
        "🔷 Total Meters (WC+DT)", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
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
        use_container_width=True
    )


def show_dashboard():
    df = load_data()
    if df.empty:
        st.info("No data in database yet. Add data from the **Admin Panel**.")
        return

    st.markdown("### 🔍 Filters")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        view = st.radio(
            "View Mode",
            ["Combined View", "Package Wise View"],
            horizontal=True
        )

    min_d = df["date"].min()
    max_d = df["date"].max()

    with col2:
        start_date = st.date_input(
            "Start Date",
            min_d,
            min_value=min_d,
            max_value=max_d
        )
    with col3:
        end_date = st.date_input(
            "End Date",
            max_d,
            min_value=min_d,
            max_value=max_d
        )

    if start_date > end_date:
        st.error("Start Date cannot be after End Date.")
        return

    mask = (df["date"] >= start_date) & (df["date"] <= end_date)
    df_range = df[mask]

    if view == "Combined View":
        grp = df_range.groupby("date")[[
            "wc_mi", "dt", "ci", "mi", "in_house",
            "supervisory", "Total_Manpower", "Total_WC_DT"
        ]].sum().reset_index()
        graph_and_table(grp)
    else:
        pkg = st.selectbox("Select Package", ALLOWED_PACKAGES)
        df_pkg = df_range[df_range["package"] == pkg]
        grp = df_pkg.groupby("date")[[
            "wc_mi", "dt", "ci", "mi", "in_house",
            "supervisory", "Total_Manpower", "Total_WC_DT"
        ]].sum().reset_index()
        graph_and_table(grp)


# ====================================================== #
#                        ADMIN PANEL                     #
# ====================================================== #
def parse_date_col(series: pd.Series) -> pd.Series:
    """Parse dates from CSV in flexible formats."""
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
    mask = parsed.isna()
    if mask.any():
        parsed2 = pd.to_datetime(series[mask], errors="coerce", yearfirst=True)
        parsed.loc[mask] = parsed2
    return parsed.dt.date


def handle_csv_upload(uploaded):
    try:
        df_csv = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Unable to read CSV: {e}")
        return

    df_csv.columns = [c.strip() for c in df_csv.columns]

    col_map = {
        "Date": "date",
        "Package": "package",
        "WC-MI": "wc_mi",
        "DT": "dt",
        "CI": "ci",
        "MI": "mi",
        "IN-HOUSE": "in_house",
        "Supervisory": "supervisory",
        "sum": "sum_col"
    }
    df_csv = df_csv.rename(columns=col_map)

    required = ["date", "package", "wc_mi", "dt", "ci", "mi", "in_house", "supervisory"]
    missing = [c for c in required if c not in df_csv.columns]
    if missing:
        st.error(f"CSV missing required columns: {missing}")
        return

    df_csv["date"] = parse_date_col(df_csv["date"])
    df_csv = df_csv.dropna(subset=["date"])

    df_csv["package"] = df_csv["package"].astype(str).str.strip()
    df_csv = df_csv[df_csv["package"].isin(ALLOWED_PACKAGES)]

    num_cols = ["wc_mi", "dt", "ci", "mi", "in_house", "supervisory"]
    for c in num_cols:
        df_csv[c] = pd.to_numeric(df_csv[c], errors="coerce").fillna(0).astype(int)

    count = 0
    for _, r in df_csv.iterrows():
        row = dict(
            date=r["date"],
            package=r["package"],
            wc_mi=int(r["wc_mi"]),
            dt=int(r["dt"]),
            ci=int(r["ci"]),
            mi=int(r["mi"]),
            in_house=int(r["in_house"]),
            supervisory=int(r["supervisory"])
        )
        upsert_row(row)
        count += 1

    st.success(f"CSV processed successfully. {count} rows inserted/updated.")


def show_admin():
    st.markdown("## 🔐 Admin Panel")

    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if not st.session_state.is_admin:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            if u == ADMIN_USER and p == ADMIN_PASS:
                st.session_state.is_admin = True
                st.success("Logged in ✅")
            else:
                st.error("Incorrect username or password.")
        return

    st.success("Logged In ✅")

    # ----- Insert New Data Card ----- #
    with st.expander("➕ Insert New Data", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            d = st.date_input("Date", value=date.today())
        with c2:
            pkg = st.selectbox("Package", ALLOWED_PACKAGES)

        c3, c4, c5 = st.columns(3)
        with c3:
            wc_mi = st.number_input("WC-MI", min_value=0, step=1, value=0)
        with c4:
            dt_val = st.number_input("DT", min_value=0, step=1, value=0)
        with c5:
            ci = st.number_input("CI", min_value=0, step=1, value=0)

        c6, c7, c8 = st.columns(3)
        with c6:
            mi = st.number_input("MI", min_value=0, step=1, value=0)
        with c7:
            in_house = st.number_input("IN-HOUSE", min_value=0, step=1, value=0)
        with c8:
            sup = st.number_input("Supervisory", min_value=0, step=1, value=0)

        if st.button("Save / Update Row", type="primary"):
            row = dict(
                date=d,
                package=pkg,
                wc_mi=int(wc_mi),
                dt=int(dt_val),
                ci=int(ci),
                mi=int(mi),
                in_house=int(in_house),
                supervisory=int(sup)
            )
            upsert_row(row)
            st.success(f"Saved data for {d.strftime('%d-%b')} — {pkg}")

    # ----- CSV Upload Card ----- #
    with st.expander("📂 Bulk Upload via CSV", expanded=False):
        st.write("CSV must have columns:")
        st.code("Date, Package, WC-MI, DT, CI, MI, IN-HOUSE, Supervisory, sum")
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded is not None:
            handle_csv_upload(uploaded)

    # ----- Preview Latest Data ----- #
    st.subheader("🧾 Latest 20 Rows in Database")
    df_all = load_data()
    if df_all.empty:
        st.info("No data in database yet.")
    else:
        df_prev = df_all.sort_values(
            ["date", "package"],
            ascending=[False, True]
        ).head(20)
        st.dataframe(df_prev, use_container_width=True)


# ===================== MAIN RENDER ===================== #
if mode == "Dashboard":
    show_dashboard()
else:
    show_admin()
