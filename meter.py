import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import date

# ===================== BASIC CONFIG ===================== #
st.set_page_config(page_title="Genus Meter Dashboard",
                   layout="wide",
                   initial_sidebar_state="expanded")

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

# ===================== TITLE ===================== #
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
    return create_engine(st.secrets["DB_URL"], pool_pre_ping=True)

@st.cache_resource
def init_db():
    engine = get_engine()
    engine.execute("""
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
        CREATE UNIQUE INDEX IF NOT EXISTS idx_date_pkg
        ON meter_data(date, package);
    """)
    return True

@st.cache_data
def load_data():
    df = pd.read_sql("SELECT * FROM meter_data ORDER BY date ASC", get_engine())
    if df.empty: return df

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]
    return df

init_db()

def kfmt(v): return f"{v/1000:.1f}k" if v>=1000 else str(int(v))

# ====================================================== #
#                       DASHBOARD                        #
# ====================================================== #
def graph_and_table(df):
    if df.empty:
        st.warning("No data found for selected range.")
        return

    total = int(df["Total_WC_DT"].sum())
    pmx = df.loc[df["Total_Manpower"].idxmax()]
    mx = df.loc[df["Total_WC_DT"].idxmax()]

    c1,c2,c3 = st.columns(3)
    c1.markdown(f"<div class='kpi-card'><div class='kpi-label'>📦 Total Meters</div><div class='kpi-value'>{kfmt(total)}</div></div>",unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card'><div class='kpi-label'>📈 Peak Installation</div><div class='kpi-value'>{int(mx.Total_WC_DT)} on {mx.date.strftime('%d-%b')}</div></div>",unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card'><div class='kpi-label'>👥 Peak Manpower</div><div class='kpi-value'>{int(pmx.Total_Manpower)} on {pmx.date.strftime('%d-%b')}</div></div>",unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_bar(x=df["date"],y=df["wc_mi"],name="WC-MI",marker_color="#FF7B7B")
    fig.add_bar(x=df["date"],y=df["dt"],name="DT",marker_color="#FFD700")

    fig.add_trace(go.Scatter(
        x=df["date"],y=df["Total_Manpower"],
        mode="lines+markers+text",
        text=[int(v) for v in df["Total_Manpower"]],
        textposition="top center",
        name="Total Manpower",
        yaxis="y2",line=dict(color="#003A8C",width=3)
    ))

    # 🆕 Total Meter Label BELOW Bars (near dates)
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=[0]*len(df),
        mode="text",
        text=[kfmt(v) for v in df["Total_WC_DT"]],
        textposition="bottom center",
        textfont=dict(size=12,color="black"),
        showlegend=False,
        hoverinfo="skip"
    ))

    fig.update_layout(
        barmode="stack",
        height=560,
        xaxis=dict(tickangle=50),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower",overlaying="y",side="right"),
        legend=dict(orientation="h",y=1.02,x=0.5,xanchor="center")
    )

    st.plotly_chart(fig,use_container_width=True)

    table=df.set_index("date")[
        ["Total_WC_DT","wc_mi","dt","Total_Manpower","ci","mi","in_house","supervisory"]
    ].T
    table.index=[
        "🔷 Total Meters (WC+DT)","WC-MI","DT",
        "🟢 Total Manpower","CI","MI","IN-HOUSE","Supervisory"
    ]
    table.index.name=""

    def color(r):
        if "Total Meters" in r.name: return ["background-color:#D7E8FF;font-weight:bold"]*len(r)
        if "Total Manpower" in r.name: return ["background-color:#D5F8D7;font-weight:bold"]*len(r)
        return [""]*len(r)

    st.subheader("📋 Date Wise Table")
    st.dataframe(table.style.apply(color,axis=1),use_container_width=True)

def show_dashboard():
    df=load_data()
    if df.empty:
        st.info("Please upload data in Admin Panel.")
        return

    c1,c2,c3=st.columns([1.4,1,1])
    with c1: view = st.radio("View Mode",["Combined","Package Wise"],horizontal=True)
    with c2: start = st.date_input("Start",df.date.min())
    with c3: end = st.date_input("End",df.date.max())

    if start>end: return st.error("Start date cannot be greater.")

    dfr=df[(df.date>=start)&(df.date<=end)]

    if view=="Combined":
        graph_and_table(dfr.groupby("date").sum().reset_index())
    else:
        pkg=st.selectbox("Package",ALLOWED_PACKAGES)
        graph_and_table(dfr[dfr.package==pkg].groupby("date").sum().reset_index())

# ====================================================== #
#                       ADMIN PANEL                      #
# ====================================================== #
def parse_date(s):
    try: return pd.to_datetime(s,dayfirst=True).date()
    except: return None

def show_admin():
    st.subheader("🔐 Admin Panel")

    if "admin" not in st.session_state:
        st.session_state.admin=False

    if not st.session_state.admin:
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("Login") and u==ADMIN_USER and p==ADMIN_PASS:
            st.session_state.admin=True
        return

    st.success("Logged in!")

    # Insert Single Row
    with st.expander("➕ Insert Data",True):
        d=st.date_input("Date")
        pkg=st.selectbox("Package",ALLOWED_PACKAGES)
        wc=st.number_input("WC-MI",0)
        dtv=st.number_input("DT",0)
        ci=st.number_input("CI",0)
        mi=st.number_input("MI",0)
        ih=st.number_input("IN-HOUSE",0)
        sp=st.number_input("Supervisory",0)
        if st.button("Save"):
            row=dict(date=d,package=pkg,wc_mi=int(wc),dt=int(dtv),ci=int(ci),mi=int(mi),in_house=int(ih),supervisory=int(sp))
            get_engine().execute(text("""
            INSERT INTO meter_data VALUES (DEFAULT,:date,:package,:wc_mi,:dt,:ci,:mi,:in_house,:supervisory)
            ON CONFLICT(date,package) DO UPDATE SET
            wc_mi=EXCLUDED.wc_mi,dt=EXCLUDED.dt,ci=EXCLUDED.ci,mi=EXCLUDED.mi,
            in_house=EXCLUDED.in_house,supervisory=EXCLUDED.supervisory
            """),row)
            load_data.clear()
            st.success("Saved!")

    # CSV Upload
    with st.expander("📂 Upload CSV"):
        up=st.file_uploader("CSV",type="csv")
        if up:
            df=pd.read_csv(up)
            df["date"]=df["Date"].apply(parse_date)
            df=df.dropna(subset=["date"])
            count=0
            for _,r in df.iterrows():
                get_engine().execute(text("""
                INSERT INTO meter_data VALUES (DEFAULT,:date,:pkg,:w,:d,:c,:m,:ih,:sp)
                ON CONFLICT(date,package) DO UPDATE SET
                wc_mi=:w,dt=:d,ci=:c,mi=:m,in_house=:ih,supervisory=:sp
                """),{"date":r["date"],"pkg":r["Package"],"w":r["WC-MI"],"d":r["DT"],"c":r["CI"],"m":r["MI"],"ih":r["IN-HOUSE"],"sp":r["Supervisory"]})
                count+=1
            load_data.clear()
            st.success(f"{count} rows added")

    st.subheader("🧾 Latest Data")
    df=load_data().sort_values("date",ascending=False).head(15)
    st.dataframe(df,use_container_width=True)

# ===================== MAIN ===================== #
mode=st.sidebar.radio("🔀 Navigate",["Dashboard","Admin Panel"])
if mode=="Dashboard": show_dashboard()
else: show_admin()
