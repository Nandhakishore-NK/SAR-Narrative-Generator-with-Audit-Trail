"""
SAR Narrative Generator - Main Streamlit Application
Barclays AML Compliance Tool
"""
import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="SAR Narrative Generator | Barclays AML",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- Bootstrap DB and data ----
from app.models.database import create_tables
from app.utils.auth import seed_default_users
from app.utils.data_processor import seed_sample_data

@st.cache_resource
def bootstrap():
    create_tables()
    seed_default_users()
    seed_sample_data()
    return True

bootstrap()

# ---- Login Wall ----
from app.utils.auth import authenticate_user, has_permission, ROLE_COLORS
from app.services.alert_service import alert_service
from app.services.audit_service import audit_service

def apply_styles():
    st.markdown("""
    <style>
    /* ---- Global ---- */
    body { font-family: 'Segoe UI', sans-serif; }
    .block-container { padding-top: 1.5rem; }

    /* ---- Sidebar background (force dark regardless of theme) ---- */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child,
    section[data-testid="stSidebar"] > div {
        background: linear-gradient(175deg, #00205b 0%, #001640 100%) !important;
    }
    [data-testid="stSidebar"] * { box-sizing: border-box; }

    /* ---- All text inside sidebar ---- */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] .stCaption { color: #e8eaf6 !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #ffffff !important; }

    /* ---- Navigation buttons (secondary = inactive) ---- */
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.08) !important;
        color: #e8eaf6 !important;
        border: 1px solid rgba(255,255,255,0.18) !important;
        border-radius: 8px !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        padding: 0.45rem 0.9rem !important;
        transition: background 0.15s;
        width: 100% !important;
        margin-bottom: 3px !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.18) !important;
        color: #ffffff !important;
        border-color: rgba(255,255,255,0.4) !important;
    }
    /* ---- Active nav button (primary) ---- */
    [data-testid="stSidebar"] .stButton > button[kind="primary"],
    [data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
        background: rgba(255,255,255,0.22) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.55) !important;
        font-weight: 700 !important;
    }
    /* ---- Sign out button ---- */
    [data-testid="stSidebar"] .stButton:last-child > button {
        background: rgba(220,53,69,0.25) !important;
        color: #ffcdd2 !important;
        border: 1px solid rgba(220,53,69,0.45) !important;
    }
    [data-testid="stSidebar"] .stButton:last-child > button:hover {
        background: rgba(220,53,69,0.5) !important;
        color: #ffffff !important;
    }

    /* ---- Cards ---- */
    .metric-card {
        background: white;
        border-left: 4px solid #00205b;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        margin-bottom: 0.5rem;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #00205b; }
    .metric-label { font-size: 0.75rem; color: #607d8b; text-transform: uppercase; letter-spacing: 0.05em; }

    /* ---- Alert Badges ---- */
    .alert-critical { background:#ffebee; border-left:4px solid #c62828; padding:0.7rem 1rem; border-radius:6px; margin:0.3rem 0; }
    .alert-high     { background:#fff3e0; border-left:4px solid #e65100; padding:0.7rem 1rem; border-radius:6px; margin:0.3rem 0; }
    .alert-medium   { background:#fff8e1; border-left:4px solid #f9a825; padding:0.7rem 1rem; border-radius:6px; margin:0.3rem 0; }
    .alert-low      { background:#e8f5e9; border-left:4px solid #2e7d32; padding:0.7rem 1rem; border-radius:6px; margin:0.3rem 0; }

    /* ---- Narrative Box ---- */
    .narrative-box {
        background: #f8f9fc;
        border: 1px solid #d0d7de;
        border-radius: 8px;
        padding: 1.2rem;
        font-family: 'Georgia', serif;
        font-size: 0.92rem;
        line-height: 1.75;
        white-space: pre-wrap;
    }
    .audit-box {
        background: #0d1b2a;
        color: #a8d8a8;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Courier New', monospace;
        font-size: 0.82rem;
        line-height: 1.5;
        white-space: pre-wrap;
        max-height: 420px;
        overflow-y: auto;
    }
    /* ---- Role Badge ---- */
    .role-badge {
        display:inline-block;
        padding:2px 10px;
        border-radius:12px;
        font-size:0.72rem;
        font-weight:700;
        text-transform:uppercase;
        color:white;
    }
    /* ---- Header Banner ---- */
    .app-header {
        background: linear-gradient(90deg, #00205b 0%, #003DA5 100%);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .stButton > button {
        border-radius: 6px;
        font-weight: 600;
    }
    .stTextArea textarea { font-family: 'Georgia', serif; font-size: 0.91rem; line-height: 1.7; }
    </style>
    """, unsafe_allow_html=True)


def login_page():
    st.markdown("""
    <div style="max-width:420px;margin:60px auto;text-align:center;">
        <div style="background:linear-gradient(135deg,#00205b,#003DA5);padding:40px;border-radius:16px;color:white;box-shadow:0 8px 32px rgba(0,32,91,0.3);">
            <h1 style="margin:0;font-size:2rem;">🏦</h1>
            <h2 style="margin:8px 0 4px;">SAR Narrative Generator</h2>
            <p style="margin:0;opacity:0.8;font-size:0.9rem;">Barclays AML Compliance Platform</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### Sign In")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("🔐 Sign In", use_container_width=True)
            if submitted:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state["user"] = {
                            "id": user.id,
                            "username": user.username,
                            "full_name": user.full_name,
                            "email": user.email,
                            "role": user.role.value,
                            "department": user.department
                        }
                        audit_service.log(
                            action="USER_LOGIN",
                            user_id=user.id,
                            details={"username": username, "role": user.role.value}
                        )
                        st.success(f"Welcome, {user.full_name}!")
                        st.rerun()
                    else:
                        audit_service.log(
                            action="USER_LOGIN_FAILED",
                            details={"username": username},
                            success=False,
                            error_message="Invalid credentials"
                        )
                        st.error("Invalid username or password.")
                else:
                    st.warning("Please enter both username and password.")
    st.markdown("""
    <div style="max-width:420px;margin:0 auto;text-align:center;padding:16px;">
    <p style="color:#888;font-size:0.8rem;">
    <b>Demo Credentials:</b><br>
    admin / Admin@2024! &nbsp;|&nbsp; analyst1 / Analyst@2024!<br>
    supervisor1 / Supervisor@2024! &nbsp;|&nbsp; readonly1 / Readonly@2024!
    </p>
    </div>
    """, unsafe_allow_html=True)


def sidebar(user: dict):
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:16px 0 8px;">
            <div style="font-size:2.5rem;">🏦</div>
            <div style="color:white;font-size:1.1rem;font-weight:700;">SAR Generator</div>
            <div style="color:#90caf9;font-size:0.78rem;">Barclays AML Platform</div>
        </div>
        <hr style="border-color:rgba(255,255,255,0.15);margin:8px 0;">
        """, unsafe_allow_html=True)
        # User info
        role_color = ROLE_COLORS.get(user["role"], "#95a5a6")
        st.markdown(f"""
        <div style="padding:10px;background:rgba(255,255,255,0.08);border-radius:8px;margin-bottom:12px;">
            <div style="color:white;font-weight:600;">👤 {user["full_name"]}</div>
            <div style="margin-top:4px;">
                <span class="role-badge" style="background:{role_color};">{user["role"]}</span>
            </div>
            <div style="color:#90caf9;font-size:0.75rem;margin-top:4px;">{user["department"]}</div>
        </div>
        """, unsafe_allow_html=True)
        # Alert summary
        alert_summary = alert_service.get_alert_summary()
        if alert_summary["total"] > 0:
            critical_badge = f"🔴 {alert_summary['critical']}" if alert_summary['critical'] > 0 else ""
            high_badge = f"🟠 {alert_summary['high']}" if alert_summary['high'] > 0 else ""
            st.markdown(f"""
            <div style="background:rgba(255,80,80,0.15);border:1px solid rgba(255,80,80,0.3);border-radius:6px;padding:8px 12px;margin-bottom:10px;">
                <div style="color:#ff8a80;font-size:0.78rem;font-weight:600;">⚠️ UNREAD ALERTS ({alert_summary['total']})</div>
                <div style="color:white;font-size:0.82rem;">{critical_badge} {high_badge}</div>
            </div>
            """, unsafe_allow_html=True)
        # Navigation
        st.markdown("<div style='color:#90caf9;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;margin:8px 0 4px;'>Navigation</div>", unsafe_allow_html=True)
        pages = [
            ("🏠", "Dashboard", "dashboard"),
            ("📋", "Case Management", "cases"),
            ("✍️", "Generate SAR", "generate"),
            ("🔍", "Review & Approve", "review"),
            ("🔔", "Alerts", "alerts"),
            ("📊", "Audit Trail", "audit"),
            ("📈", "Reports & Analytics", "analytics"),
        ]
        if has_permission(user["role"], "manage_users"):
            pages.append(("👥", "User Management", "users"))
        for icon, label, key in pages:
            is_active = st.session_state.get("page") == key
            btn_style = "primary" if is_active else "secondary"
            if st.button(f"{icon} {label}", key=f"nav_{key}", use_container_width=True, type=btn_style if is_active else "secondary"):
                st.session_state["page"] = key
                st.rerun()
        st.markdown("<hr style='border-color:rgba(255,255,255,0.15);margin:16px 0 8px;'>", unsafe_allow_html=True)
        if st.button("🚪 Sign Out", use_container_width=True):
            audit_service.log(
                action="USER_LOGOUT",
                user_id=user["id"],
                details={"username": user["username"]}
            )
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def main():
    apply_styles()
    if "user" not in st.session_state:
        login_page()
        return
    user = st.session_state["user"]
    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"
    sidebar(user)
    page = st.session_state.get("page", "dashboard")
    if page == "dashboard":
        from app.views.dashboard import show_dashboard
        show_dashboard(user)
    elif page == "cases":
        from app.views.case_management import show_case_management
        show_case_management(user)
    elif page == "generate":
        from app.views.sar_generator_page import show_sar_generator
        show_sar_generator(user)
    elif page == "review":
        from app.views.review_approve import show_review_approve
        show_review_approve(user)
    elif page == "alerts":
        from app.views.alerts_page import show_alerts
        show_alerts(user)
    elif page == "audit":
        from app.views.audit_trail_page import show_audit_trail
        show_audit_trail(user)
    elif page == "analytics":
        from app.views.analytics_page import show_analytics
        show_analytics(user)
    elif page == "users":
        if has_permission(user["role"], "manage_users"):
            from app.views.user_management import show_user_management
            show_user_management(user)
        else:
            st.error("Access denied. Insufficient permissions.")
    else:
        st.session_state["page"] = "dashboard"
        st.rerun()


if __name__ == "__main__":
    main()
