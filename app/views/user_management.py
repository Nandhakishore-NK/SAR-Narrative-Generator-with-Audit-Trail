"""User Management Page — Admin only"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.utils.auth import (
    create_user, get_all_users, ROLE_COLORS, ROLE_DESCRIPTIONS,
    has_permission, hash_password
)
from app.models.database import User, UserRole, SessionLocal
from app.services.audit_service import audit_service


def show_user_management(user: dict):
    st.markdown("""
    <div class="app-header">
        <div>
            <h2 style="margin:0;color:white;">👥 User Management</h2>
            <p style="margin:0;opacity:0.8;font-size:0.85rem;">
                Role-based access control — manage user accounts and permissions
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if not has_permission(user["role"], "manage_users"):
        st.error("🚫 Access Denied: Admin role required.")
        return
    tab_list, tab_create, tab_roles = st.tabs(["👥 User List", "➕ Create User", "🔐 Role Permissions"])
    with tab_list:
        users = get_all_users()
        if users:
            rows = []
            for u in users:
                rows.append({
                    "ID": u.id,
                    "Username": u.username,
                    "Full Name": u.full_name,
                    "Email": u.email,
                    "Role": u.role.value,
                    "Department": u.department,
                    "Active": "✅" if u.is_active else "❌",
                    "Last Login": u.last_login.strftime("%d/%m/%Y %H:%M") if u.last_login else "Never",
                    "Created": u.created_at.strftime("%d/%m/%Y") if u.created_at else "-",
                })
            df = pd.DataFrame(rows)
            def style_role(val):
                colors = {
                    "ADMIN": "background:#ffebee;color:#c62828",
                    "SUPERVISOR": "background:#fff3e0;color:#e65100",
                    "ANALYST": "background:#e3f2fd;color:#1565c0",
                    "READ_ONLY": "background:#f5f5f5;color:#607d8b"
                }
                return colors.get(val, "")
            st.dataframe(df.style.applymap(style_role, subset=["Role"]), use_container_width=True, height=350)
            # Toggle active
            st.markdown("---")
            st.markdown("##### Toggle User Status")
            tc1, tc2 = st.columns(2)
            with tc1:
                toggle_user = st.selectbox("Select User", [f"{u.username} ({u.id})" for u in users if u.username != user["username"]])
                toggle_uid = int(toggle_user.split("(")[1].strip(")"))
            with tc2:
                new_status = st.selectbox("New Status", ["Active", "Inactive"])
                if st.button("Update Status"):
                    db = SessionLocal()
                    try:
                        target = db.query(User).filter(User.id == toggle_uid).first()
                        if target:
                            target.is_active = (new_status == "Active")
                            db.commit()
                            audit_service.log(
                                "USER_CREATED", user_id=user["id"],
                                details={"action": "status_update", "target_user_id": toggle_uid, "new_status": new_status}
                            )
                            st.success(f"User {target.username} set to {new_status}")
                            st.rerun()
                    finally:
                        db.close()
    with tab_create:
        st.markdown("#### Create New User Account")
        with st.form("create_user_form"):
            cc1, cc2 = st.columns(2)
            with cc1:
                new_username = st.text_input("Username*", placeholder="e.g. analyst2")
                new_full_name = st.text_input("Full Name*", placeholder="e.g. Jane Doe")
                new_role = st.selectbox("Role*", ["ANALYST", "SUPERVISOR", "ADMIN", "READ_ONLY"])
            with cc2:
                new_email = st.text_input("Email*", placeholder="e.g. jane.doe@barclays.com")
                new_department = st.text_input("Department", value="AML Compliance")
                new_password = st.text_input("Password*", type="password", placeholder="Min 8 characters")
            submit_user = st.form_submit_button("➕ Create User", type="primary", use_container_width=True)
            if submit_user:
                if not all([new_username, new_full_name, new_email, new_password]):
                    st.error("All required fields must be completed.")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    created = create_user(
                        username=new_username, email=new_email,
                        full_name=new_full_name, password=new_password,
                        role=new_role, department=new_department
                    )
                    if created:
                        audit_service.log(
                            "USER_CREATED", user_id=user["id"],
                            details={"created_by": user["username"], "new_user": new_username, "role": new_role}
                        )
                        st.success(f"✅ User '{new_username}' created successfully with role {new_role}.")
                    else:
                        st.error("User creation failed. Username or email may already exist.")
    with tab_roles:
        st.markdown("#### 🔐 Role-Based Access Control Matrix")
        st.caption("""
        Data domain boundaries are enforced to prevent cross-domain data leakage.
        Each role has explicit access to customer, transaction, and fraud data domains.
        """)
        for role_name, color in ROLE_COLORS.items():
            with st.expander(f"**{role_name}** — {ROLE_DESCRIPTIONS.get(role_name, '')}", expanded=False):
                st.markdown(f'<span style="background:{color};color:white;padding:4px 12px;border-radius:10px;font-weight:700;">{role_name}</span>', unsafe_allow_html=True)
                from app.utils.auth import PERMISSIONS, DATA_DOMAIN_ACCESS
                perms = PERMISSIONS.get(UserRole(role_name), [])
                da_allowed = [domain for domain, roles in DATA_DOMAIN_ACCESS.items() if UserRole(role_name) in roles]
                col_p, col_d = st.columns(2)
                with col_p:
                    st.markdown("**Permissions:**")
                    for p in perms:
                        st.markdown(f"✅ {p}")
                with col_d:
                    st.markdown("**Data Domain Access:**")
                    all_domains = list(DATA_DOMAIN_ACCESS.keys())
                    for d in all_domains:
                        allowed = UserRole(role_name) in DATA_DOMAIN_ACCESS[d]
                        icon = "✅" if allowed else "🚫"
                        st.markdown(f"{icon} {d.upper()}")
