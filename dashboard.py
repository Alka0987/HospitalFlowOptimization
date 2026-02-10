import streamlit as st
import pandas as pd
import time
import uuid
import random
import altair as alt
from datetime import datetime
from db_manager import DatabaseManager
from predict import predict_wait_time

# Page Config
st.set_page_config(
    page_title="Hospital Queue AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR "PREMIUM" LOOK ---
st.markdown("""
<style>
    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background-color: #262730; /* Dark Grey */
        border: 1px solid #41424C;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #00ADB5;
    }
    div[data-testid="stMetricLabel"] {
        color: #A0A0A5;
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF;
        font-weight: 700;
    }
    
    /* Header Styling */
    h1 {
        background: -webkit-linear-gradient(45deg, #00ADB5, #EEEEEE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #0E1117;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #262730;
        border-bottom: 2px solid #00ADB5;
    }
</style>
""", unsafe_allow_html=True)

# Initialize DB
db = DatabaseManager()

# --- SIDEBAR: CONTROLS ---
with st.sidebar:
    st.title("🏥 Controls")
    st.markdown("---")
    
    # 1. ADD PATIENT
    with st.expander("📝 **Check In Patient**", expanded=True):
        with st.form("checkin_form"):
            p_name = st.text_input("Name", placeholder="e.g. John Doe")
            p_modality = st.selectbox("Modality", ["Consultation", "MRI", "CT"])
            col1, col2 = st.columns(2)
            with col1:
                p_emergency = st.checkbox("Emergency?", value=False)
            with col2:
                p_contrast = st.checkbox("Contrast?", value=False)
            
            submitted = st.form_submit_button("Add to Queue", type="primary")
            
            if submitted and p_name:
                active = db.get_active_patients()
                q_len = len(active) if active else 0
                wait_time = predict_wait_time(
                    modality=p_modality,
                    is_emergency=p_emergency,
                    current_queue=q_len,
                    contrast_queue=1 if p_contrast else 0,
                    avg_age=45
                )
                new_p = {
                    'patient_id': str(uuid.uuid4())[:8],
                    'patient_name': p_name,
                    'arrival_time': datetime.now(),
                    'patient_type': 'Emergency' if p_emergency else 'Scheduled',
                    'modality': p_modality,
                    'predicted_wait_minutes': wait_time
                }
                db.add_patient(new_p)
                st.toast(f"✅ Checked in: {p_name}")

    st.markdown("###")

    # 2. COMPLETE PATIENT
    with st.container():
        st.caption("✅ **Quick Complete**")
        target_id = st.text_input("Patient ID", placeholder="Paste ID to complete...")
        if st.button("Mark Completed", type="secondary"):
            if target_id:
                db.update_patient_status(target_id, 'COMPLETED')
                st.success(f"Completed {target_id}")

# --- DATA LOADING ---
def load_data():
    """Fetch active patients and stats."""
    data = db.get_active_patients()
    stats = db.get_queue_stats()
    
    if not data:
        return pd.DataFrame(), pd.DataFrame(stats)
    
    df = pd.DataFrame(data)
    
    # Calculate Real-Time Elapsed Wait
    now = datetime.now()
    df['elapsed_wait_minutes'] = (now - df['arrival_time']).dt.total_seconds() / 60
    
    # Alert Logic
    df['status_color'] = df.apply(
        lambda x: 'critical' if x['elapsed_wait_minutes'] > (x['predicted_wait_minutes'] + 15)
        else 'warning' if x['elapsed_wait_minutes'] > x['predicted_wait_minutes']
        else 'normal', axis=1
    )
    
    return df, pd.DataFrame(stats)

# --- MAIN UI ---
st.title("Smart Hospital Monitor")
st.caption("AI-Powered Queue Prediction & Resource Management")

# Placeholder for dynamic content
dashboard_placeholder = st.empty()

while True:
    try:
        df_queue, df_stats = load_data()
        
        with dashboard_placeholder.container():
            # 1. KPIs
            k1, k2, k3, k4 = st.columns(4)
            
            total_q = len(df_queue) if not df_queue.empty else 0
            avg_wait = df_queue['predicted_wait_minutes'].mean() if not df_queue.empty else 0
            emergency_cnt = len(df_queue[df_queue['patient_type'] == 'Emergency']) if not df_queue.empty else 0
            
            # Count critical (overdue)
            crit_cnt = 0
            if not df_queue.empty:
                crit_cnt = len(df_queue[df_queue['status_color'] == 'critical'])
            
            k1.metric("Waiting Patients", total_q, delta="Live", delta_color="off")
            k2.metric("Avg Wait Time", f"{avg_wait:.0f} min", delta=f"{avg_wait-20:.1f} vs Target" if total_q > 0 else None, delta_color="inverse")
            k3.metric("Emergencies", emergency_cnt, delta="High Priority" if emergency_cnt > 0 else None, delta_color="normal")
            k4.metric("Critical Alerts", crit_cnt, delta="Requires Action" if crit_cnt > 0 else "All Good", delta_color="inverse")
            
            st.divider()

            # 2. AI Recommendation Area
            if avg_wait > 25:
                st.error("🚨 **CRITICAL STAFFING ALERT**: Average wait > 25m. Deploy 2 additional staff members immediately!", icon="📢")
            elif avg_wait > 15:
                st.warning("⚠️ **HIGH LOAD**: Queue is building up. Consider adding 1 staff member.", icon="⚠️")
            
            # 3. TABS
            t1, t2 = st.tabs(["📋 Live Operations", "📊 Analytics Hub"])
            
            with t1:
                if not df_queue.empty:
                    # Logic: Urgency Sorting
                    df_queue['minutes_until_breach'] = (df_queue['predicted_wait_minutes'] + 15) - df_queue['elapsed_wait_minutes']
                    df_queue = df_queue.sort_values('minutes_until_breach', ascending=True)

                    # Better Column config
                    st.dataframe(
                        df_queue,
                        column_order=("patient_name", "status", "modality", "patient_type", "arrival_time", "predicted_wait_minutes", "elapsed_wait_minutes", "patient_id"),
                        column_config={
                            "patient_name": st.column_config.TextColumn("Patient Name", width="medium"),
                            "status": st.column_config.TextColumn("Status", width="small"),
                            "modality": st.column_config.TextColumn("Modality", width="small"),
                            "patient_type": st.column_config.TextColumn("Type", width="small"),
                            "arrival_time": st.column_config.DatetimeColumn("Arrival", format="HH:mm:ss"),
                            "predicted_wait_minutes": st.column_config.ProgressColumn(
                                "Predicted Wait",
                                help="AI Estimated wait time",
                                format="%.0f m",
                                min_value=0,
                                max_value=60,
                            ),
                            "elapsed_wait_minutes": st.column_config.NumberColumn(
                                "Elapsed",
                                format="%.1f m"
                            ),
                            "patient_id": st.column_config.TextColumn("ID (Copy)", width="small")
                        },
                        use_container_width=True,
                        hide_index=True 
                    )
                else:
                    st.success("🎉  waiting room is empty!", icon="🏥")

            with t2:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### ⏳ Bottleneck Analysis")
                    if not df_stats.empty and 'modality' in df_stats.columns:
                        # ALTAIR BAR CHART
                        chart = alt.Chart(df_stats).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                            x=alt.X('modality', title=None),
                            y=alt.Y('avg_wait', title='Avg Wait (min)'),
                            color=alt.Color('avg_wait', scale=alt.Scale(scheme='tealblues'), legend=None),
                            tooltip=['modality', 'count', 'avg_wait']
                        ).properties(height=300)
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.caption("No data available.")

                with c2:
                    st.markdown("#### 📈 Arrival Volume")
                    if not df_queue.empty:
                        # ALTAIR AREA CHART
                        df_trend = df_queue.sort_values('arrival_time')
                        line = alt.Chart(df_trend).mark_area(
                            line={'color':'#00ADB5'},
                            color=alt.Gradient(
                                gradient='linear',
                                stops=[alt.GradientStop(color='#00ADB5', offset=0),
                                       alt.GradientStop(color='rgba(0,0,0,0)', offset=1)],
                                x1=1, x2=1, y1=1, y2=0
                            )
                        ).encode(
                            x=alt.X('arrival_time:T', title='Time'),
                            y=alt.Y('predicted_wait_minutes:Q', title='Wait (m)'),
                            tooltip=['patient_name', 'predicted_wait_minutes']
                        ).properties(height=300)
                        st.altair_chart(line, use_container_width=True)
                    else:
                        st.caption("No data to plot.")

        time.sleep(1)
        
    except Exception as e:
        # In case of glitch, don't crash, just wait a bit
        st.error(f"Render Error: {e}")
        time.sleep(5)
