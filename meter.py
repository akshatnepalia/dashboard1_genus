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
    return create_engine(db_url, pool_pre_ping=True)


@st.cache_resource
def init_db():
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
    engine = get_engine()
    query = """
    SELECT date, package, wc_mi, dt, ci, mi, in_house, supervisory
    FROM meter_data ORDER BY date ASC;
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"]).dt.date
    num_cols = ["wc_mi","dt","ci","mi","in_house","supervisory"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]
    return df


def clear_cache():
    load_data.clear()


def upsert_row(row):
    engine = get_engine()
    stmt = text("""
        INSERT INTO meter_data
            (date, package, wc_mi, dt, ci, mi, in_house, supervisory)
        VALUES
            (:date, :package, :wc_mi, :dt, :ci, :mi, :in_house, :supervisory)
        ON CONFLICT (date, package)
        DO UPDATE SET
            wc_mi=EXCLUDED.wc_mi, dt=EXCLUDED.dt,
            ci=EXCLUDED.ci, mi=EXCLUDED.mi,
            in_house=EXCLUDED.in_house,
            supervisory=EXCLUDED.supervisory;
    """)
    with engine.begin() as conn:
        conn.execute(stmt, row)
    clear_cache()


def kfmt(v):
    return f"{v/1000:.1f}k" if v >= 1000 else str(v)


# Ensure DB OK
init_db()

# ===================== NAVIGATION ===================== #
mode = st.sidebar.radio("🔀 Navigate", ["Dashboard", "Admin Panel"])


# ====================================================== #
#                       DASHBOARD                        #
# ====================================================== #
def graph_and_table(df_view):

    if df_view.empty:
        st.info("No data available for selection.")
        return

    # KPI
    total_meters = int(df_view["Total_WC_DT"].sum())

    # Graph Figure
    fig = go.Figure()

    # Bars
    fig.add_trace(go.Bar(x=df_view["date"], y=df_view["wc_mi"],
                         name="WC-MI", marker_color="#FF7B7B"))
    fig.add_trace(go.Bar(x=df_view["date"], y=df_view["dt"],
                         name="DT", marker_color="#FFD700"))

    # Manpower line
    fig.add_trace(go.Scatter(
        x=df_view["date"], y=df_view["Total_Manpower"],
        name="Total Manpower",
        mode="lines+markers+text",
        text=[str(v) for v in df_view["Total_Manpower"]],
        textposition="top center",
        line=dict(color="#003A8C", width=3),
        marker=dict(size=9, color="#003A8C"),
        yaxis="y2",
        hoverinfo="skip"
    ))

    # K value labels under bars
    fig.add_trace(go.Scatter(
        x=df_view["date"],
        y=[0]*len(df_view),
        mode="text",
        text=[kfmt(v) for v in df_view["Total_WC_DT"]],
        textposition="bottom center",
        textfont=dict(size=10, color="black"),
        showlegend=False,
        hoverinfo="skip"
    ))

    fig.update_layout(
        height=580,
        barmode="stack",
        xaxis=dict(tickangle=45, tickformat="%d-%b"),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)

    # TABLE (FIXED .strftime)
    table = df_view.set_index("date")[[
        "Total_WC_DT","wc_mi","dt",
        "Total_Manpower","ci","mi","in_house","supervisory"
    ]]

    table.index = pd.to_datetime(table.index).strftime("%d-%b")  # FIX ✔
    table = table.T

    table.index = [
        "🔷 Total Meters (WC+DT)", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]

    st.subheader("📋 Date-wise Summary Table")
    st.dataframe(table.astype(int), use_container_width=True)


def show_dashboard():
    df = load_data()
    if df.empty:
        st.warning("No database data. Upload from Admin Panel.")
        return

    view = st.radio("Mode", ["Combined", "Package Wise"], horizontal=True)

    min_d, max_d = df["date"].min(), df["date"].max()
    col1, col2 = st.columns(2)
    start = col1.date_input("Start Date", min_d, min_value=min_d, max_value=max_d)
    end = col2.date_input("End Date", max_d, min_value=min_d, max_value=max_d)

    if start > end:
        st.error("Start Date must be <= End Date.")
        return

    df_filtered = df[(df["date"] >= start) & (df["date"] <= end)]

    if view == "Combined":
        grp = df_filtered.groupby("date")[[
            "wc_mi","dt","ci","mi","in_house","supervisory",
            "Total_Manpower","Total_WC_DT"
        ]].sum().reset_index()
        graph_and_table(grp)
    else:
        pkg = st.selectbox("Package", ALLOWED_PACKAGES)
        grp = df_filtered[df_filtered["package"] == pkg].groupby("date")[[
            "wc_mi","dt","ci","mi","in_house","supervisory",
            "Total_Manpower","Total_WC_DT"
        ]].sum().reset_index()
        graph_and_table(grp)


# ====================================================== #
#                        ADMIN PANEL                     #
# ====================================================== #
def parse_date(series):
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return parsed.dt.date


def handle_upload(file):
    try:
        df = pd.read_csv(file)
    except:
        st.error("CSV Error")
        return

    df.columns = [c.strip() for c in df.columns]
    df.rename(columns={
        "Date":"date","MI":"mi","CI":"ci",
        "IN-HOUSE":"in_house","Supervisory":"supervisory",
        "WC-MI":"wc_mi","DT":"dt"
    }, inplace=True)

    df["date"] = parse_date(df["date"])
    df = df[df["package"].isin(ALLOWED_PACKAGES)]

    for c in ["wc_mi","dt","ci","mi","in_house","supervisory"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    for _, r in df.iterrows():
        upsert_row(r)

    st.success("Uploaded successfully!")


def show_admin():
    st.header("Admin Panel")

    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u == ADMIN_USER and p == ADMIN_PASS:
                st.session_state.auth = True
                st.success("Logged in!")
            else:
                st.error("Wrong Login")
        return

    st.success("Admin verified!")

    with st.expander("Add Row"):
        d = st.date_input("Date", date.today())
        pkg = st.selectbox("Package", ALLOWED_PACKAGES)
        wc = st.number_input("WC-MI",0)
        dt = st.number_input("DT",0)
        ci = st.number_input("CI",0)
        mi = st.number_input("MI",0)
        ih = st.number_input("IN-HOUSE",0)
        sup = st.number_input("Supervisory",0)

        if st.button("Save Row"):
            upsert_row(dict(date=d, package=pkg, wc_mi=wc,
                            dt=dt, ci=ci, mi=mi,
                            in_house=ih, supervisory=sup))
            st.success("Row Saved!")

    with st.expander("Upload CSV"):
        uploaded = st.file_uploader("Choose CSV", type=["csv"])
        if uploaded:
            handle_upload(uploaded)

    df = load_data().sort_values(["date","package"],
                                 ascending=[False,True]).head(20)
    st.dataframe(df, use_container_width=True)


# ===================== MAIN UI ===================== #
if mode == "Dashboard":
    show_dashboard()
else:
    show_admin()
