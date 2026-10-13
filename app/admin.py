import os
import sys
import hashlib
import hmac
from datetime import datetime, timedelta
from pathlib import Path
from admin_dashboard import render_admin_dashboard
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from dotenv import load_dotenv

from admin_db import (
    STATUSES,
    get_admin_stats,
    get_admin_complaints,
    get_admin_complaint,
    get_admin_status_history,
    get_admin_evidence,
    get_department_list,
    forward_complaint,
    update_admin_status,
)


load_dotenv(
    BASE_DIR / ".env",
    override=True,
)


st.set_page_config(
    page_title="CivicBridge Admin",
    page_icon="🏛️",
    layout="wide",
)


def load_styles():
    paths = [
        BASE_DIR / "style.css",
        BASE_DIR / "admin_style.css",
    ]

    css_parts = []

    for path in paths:
        if path.exists():
            css_parts.append(
                path.read_text(encoding="utf-8")
            )

    if css_parts:
        st.markdown(
            "<style>"
            + "\n".join(css_parts)
            + "</style>",
            unsafe_allow_html=True,
        )


load_styles()


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

ADMIN_EMAIL = os.getenv(
    "CIVICBRIDGE_ADMIN_EMAIL",
    "",
).strip().lower()

ADMIN_PASSWORD = os.getenv(
    "CIVICBRIDGE_ADMIN_PASSWORD",
    "",
)


def check_admin_credentials(email, password):
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        return False, "not_configured"

    email_ok = hmac.compare_digest(
        email.strip().lower(),
        ADMIN_EMAIL,
    )

    password_ok = hmac.compare_digest(
        password,
        ADMIN_PASSWORD,
    )

    return email_ok and password_ok, "invalid"



def load_admin_login_background():
    """Apply a full-page translucent background to the admin login screen."""
    import base64

    image_path = BASE_DIR / "images" / "CB Admin.png"

    if not image_path.exists():
        st.warning(
            "Admin illustration not found. Make sure "
            "'images/CB Admin.png' exists in the CivicBridge project folder."
        )
        return

    encoded_image = base64.b64encode(
        image_path.read_bytes()
    ).decode("utf-8")

    st.markdown(
        f"""
        <style>
        /* Let the illustration show behind the Streamlit top toolbar. */
        [data-testid="stAppViewContainer"] {{
            background:
                linear-gradient(
                    rgba(246, 249, 253, 0.30),
                    rgba(246, 249, 253, 0.30)
                ),
                url("data:image/png;base64,{encoded_image}")
                center center / cover no-repeat fixed !important;
        }}

        [data-testid="stHeader"],
        [data-testid="stToolbar"] {{
            background: transparent !important;
        }}

        [data-testid="stAppViewContainer"] > .main {{
            background: transparent !important;
        }}

        [data-testid="stAppViewContainer"] > .main .block-container {{
            padding-top: 3.5rem !important;
            padding-bottom: 3rem !important;
            max-width: 1500px !important;
        }}

        /* Translucent login card */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background: rgba(255, 255, 255, 0.78) !important;
            border: 1px solid rgba(255, 255, 255, 0.92) !important;
            border-radius: 18px !important;
            padding: 24px 28px !important;
            box-shadow: 0 10px 34px rgba(18, 53, 91, 0.10) !important;
            backdrop-filter: blur(10px);
        }}

        /* Brand above the admin login panel */
        .cb-admin-login-brand {{
            text-align: center;
            padding: 0 0 20px 0;
        }}

        .cb-admin-brand-name {{
            color: #12355B;
            font-size: 42px;
            font-weight: 850;
            letter-spacing: -1.5px;
            line-height: 1.15;
        }}

        .cb-admin-brand-name span {{
            color: #087E83;
        }}

        .cb-admin-tagline {{
            margin-top: 8px;
            color: #536B83;
            font-size: 10px;
            font-weight: 750;
            letter-spacing: 2px;
        }}

        .cb-admin-accent {{
            width: 58px;
            height: 4px;
            margin: 18px auto 0 auto;
            border-radius: 5px;
            background: #E07A1F;
        }}

        .admin-login-title {{
            color: #12355B;
            font-size: 30px;
            line-height: 1.2;
            font-weight: 800;
            margin: 0 0 8px 0;
        }}

        .admin-login-subtitle {{
            color: #536B83;
            font-size: 14px;
            margin-bottom: 22px;
        }}

        [data-testid="stTextInput"] label p {{
            color: #12355B !important;
            font-weight: 650 !important;
        }}

        [data-testid="stTextInput"] input {{
            min-height: 46px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.97);
            border: 1px solid #CBD5E1;
        }}

        @media (max-width: 900px) {{
            [data-testid="stAppViewContainer"] {{
                background-position: 30% center !important;
            }}

            [data-testid="stAppViewContainer"] > .main .block-container {{
                padding-top: 2rem !important;
            }}

            .cb-admin-brand-name {{
                font-size: 34px;
            }}

            [data-testid="stVerticalBlockBorderWrapper"] {{
                background: rgba(255, 255, 255, 0.91) !important;
                padding: 18px !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )



def render_admin_login():
    load_admin_login_background()

    left, right = st.columns(
        [1.15, 0.85],
        gap="large",
    )

    with left:
        # Space reserved for the illustration and its four admin icons.
        st.markdown(
            '<div style="min-height: 470px;"></div>',
            unsafe_allow_html=True,
        )

    with right:
        # CivicBridge branding above the login card.
        st.markdown(
            """
            <div class="cb-admin-login-brand">
                <div class="cb-admin-brand-name">
                    Civic<span>Bridge</span>
                </div>
                <div class="cb-admin-tagline">
                    REPORT TODAY. CLEANER CITIES TOMORROW.
                </div>
                <div class="cb-admin-accent"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown(
                '<div class="admin-login-title">'
                'Administrator Access</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="admin-login-subtitle">'
                'Restricted access for the CivicBridge administrator.'
                '</div>',
                unsafe_allow_html=True,
            )

            email = st.text_input(
                "Admin Email",
                placeholder="Enter administrator email",
                key="admin_login_email",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter administrator password",
                key="admin_login_password",
            )

            if st.button(
                "Sign In to Admin Portal",
                use_container_width=True,
                key="admin_login_button",
            ):
                attempts = int(
                    st.session_state.get(
                        "admin_failed_attempts",
                        0,
                    )
                )

                locked_until = st.session_state.get(
                    "admin_locked_until"
                )

                if locked_until and datetime.now() < locked_until:
                    remaining = int(
                        (
                            locked_until - datetime.now()
                        ).total_seconds() / 60
                    ) + 1

                    st.error(
                        f"Too many failed attempts. "
                        f"Try again in about {remaining} minute(s)."
                    )
                    return

                success, reason = check_admin_credentials(
                    email,
                    password,
                )

                if reason == "not_configured":
                    st.error(
                        "Admin access is not configured. Add "
                        "CIVICBRIDGE_ADMIN_EMAIL and "
                        "CIVICBRIDGE_ADMIN_PASSWORD to your .env file."
                    )
                    return

                if success:
                    st.session_state["admin_authenticated"] = True
                    st.session_state["admin_failed_attempts"] = 0
                    st.session_state.pop("admin_locked_until", None)
                    st.rerun()

                attempts += 1
                st.session_state["admin_failed_attempts"] = attempts

                if attempts >= 5:
                    st.session_state["admin_locked_until"] = (
                        datetime.now() + timedelta(minutes=5)
                    )
                    st.error(
                        "Too many failed attempts. "
                        "Admin access is temporarily locked."
                    )
                else:
                    st.error("Invalid administrator credentials.")

            st.markdown(
                '<div class="admin-security-note">'
                'Restricted portal • Credentials are read from '
                'environment variables.'
                '</div>',
                unsafe_allow_html=True,
            )


def status_badge(status):
    labels = {
        "Submitted": "Submitted",
        "Routed": "Routed",
        "In Progress": "In Progress",
        "Resolved": "Resolved",
        "Closed": "Closed",
    }

    return labels.get(
        status,
        str(status or "Unknown"),
    )


def render_admin_header():
    left, right = st.columns(
        [4, 1],
    )

    with left:
        st.markdown(
            '<div class="cb-brand">CivicBridge</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="cb-tagline">'
            'Operations &amp; Grievance Desk'
            '</div>',
            unsafe_allow_html=True,
        )

    with right:
        st.caption("Administrator")
        if st.button(
            "Sign Out",
            use_container_width=True,
            key="admin_logout",
        ):
            st.session_state.clear()
            st.rerun()


def render_stat_cards(stats):
    cards = [
        ("Total", stats["total"], "All grievances"),
        ("Pending Review", stats["submitted"], "Awaiting admin action"),
        ("Routed", stats["routed"], "Forwarded externally"),
        ("In Progress", stats["in_progress"], "Being handled"),
        ("Resolved", stats["resolved"], "Marked resolved"),
    ]

    cols = st.columns(5)

    for col, (title, value, caption) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="admin-stat-card">
                    <div class="admin-stat-title">{title}</div>
                    <div class="admin-stat-number">{value}</div>
                    <div class="admin-stat-caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_overview():
    st.markdown(
        '<div class="admin-section-title">Operations Overview</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "Monitor incoming grievances, review the AI-assisted routing, "
        "and record when a grievance is forwarded to the appropriate external department."
    )

    try:
        stats = get_admin_stats()
        render_stat_cards(stats)
    except Exception as exc:
        st.error("Unable to load dashboard statistics.")
        st.exception(exc)
        return

    st.markdown(
        '<div class="admin-section-title">Administrator Workflow</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="admin-workflow">
            <div class="admin-step active">
                <b>1</b>
                <strong>Received</strong>
                <span>Citizen submits a grievance.</span>
            </div>
            <div class="admin-line"></div>
            <div class="admin-step">
                <b>2</b>
                <strong>Reviewed</strong>
                <span>Administrator verifies the complaint and routing.</span>
            </div>
            <div class="admin-line"></div>
            <div class="admin-step">
                <b>3</b>
                <strong>Forwarded</strong>
                <span>Administrator forwards it through the relevant official channel.</span>
            </div>
            <div class="admin-line"></div>
            <div class="admin-step">
                <b>4</b>
                <strong>Monitored</strong>
                <span>Department responses and status changes are recorded.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        complaints = get_admin_complaints(
            status="Submitted"
        )[:5]
    except Exception as exc:
        st.error("Unable to load pending grievances.")
        st.exception(exc)
        return

    st.markdown(
        '<div class="admin-section-title">Latest Pending Grievances</div>',
        unsafe_allow_html=True,
    )

    if not complaints:
        st.success("No grievances are currently waiting for review.")
        return

    for row in complaints:
        cid = int(row["complaint_id"])
        st.markdown(
            f"""
            <div class="admin-queue-row">
                <div><strong>CB-{cid:05d}</strong><br><small>{row.get('citizen_name', 'Citizen')}</small></div>
                <div><strong>{row.get('category', '—')}</strong><br><small>{row.get('location') or 'Location not provided'}</small></div>
                <div><strong>{row.get('department') or 'Unassigned'}</strong><br><small>{status_badge(row.get('status'))}</small></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_complaint_queue():
    st.markdown(
        '<div class="admin-section-title">Complaint Queue</div>',
        unsafe_allow_html=True,
    )

    f1, f2, f3 = st.columns([1, 1, 1.5])

    with f1:
        status_filter = st.selectbox(
            "Status",
            ["All"] + STATUSES,
            key="admin_status_filter",
        )

    try:
        departments = get_department_list()
        department_names = [
            row["department"]
            for row in departments
            if row.get("department")
        ]
    except Exception:
        department_names = []

    with f2:
        department_filter = st.selectbox(
            "Department",
            ["All"] + sorted(set(department_names)),
            key="admin_department_filter",
        )

    with f3:
        search = st.text_input(
            "Search",
            placeholder="Complaint number, citizen, location...",
            key="admin_search",
        )

    try:
        rows = get_admin_complaints(
            status=status_filter,
            department=department_filter,
            search=search.strip(),
        )
    except Exception as exc:
        st.error("Unable to load the complaint queue.")
        st.exception(exc)
        return

    st.caption(f"{len(rows)} grievance(s) found.")

    if not rows:
        st.info("No grievances match the selected filters.")
        return

    for row in rows:
        cid = int(row["complaint_id"])
        title = (
            f"CB-{cid:05d}  •  "
            f"{row.get('category') or 'Civic Issue'}  •  "
            f"{row.get('status') or 'Submitted'}"
        )

        with st.expander(title):
            render_admin_complaint(row)


def render_admin_complaint(row):
    complaint_id = int(row["complaint_id"])

    info1, info2, info3, info4 = st.columns(4)

    with info1:
        st.markdown('<div class="field-label">Citizen</div>', unsafe_allow_html=True)
        st.write(row.get("citizen_name") or "—")

    with info2:
        st.markdown('<div class="field-label">Category</div>', unsafe_allow_html=True)
        st.write(row.get("category") or "—")

    with info3:
        st.markdown('<div class="field-label">Department</div>', unsafe_allow_html=True)
        st.write(row.get("department") or "—")

    with info4:
        st.markdown('<div class="field-label">Status</div>', unsafe_allow_html=True)
        st.write(row.get("status") or "—")

    st.markdown('<div class="admin-detail-label">Citizen Complaint</div>', unsafe_allow_html=True)
    st.write(row.get("original_complaint") or "—")

    d1, d2, d3 = st.columns(3)

    with d1:
        st.markdown('<div class="field-label">Issue</div>', unsafe_allow_html=True)
        st.write(row.get("issue") or "—")

    with d2:
        st.markdown('<div class="field-label">Location</div>', unsafe_allow_html=True)
        st.write(row.get("location") or "—")

    with d3:
        st.markdown('<div class="field-label">Duration</div>', unsafe_allow_html=True)
        st.write(row.get("duration") or "—")

    st.markdown('<div class="admin-detail-label">Routing Recommendation</div>', unsafe_allow_html=True)

    r1, r2 = st.columns(2)

    with r1:
        st.write(f"**Authority:** {row.get('authority') or '—'}")

    with r2:
        st.write(f"**Department:** {row.get('department') or '—'}")

    try:
        evidence = get_admin_evidence(complaint_id)
        history = get_admin_status_history(complaint_id)
    except Exception as exc:
        st.error("Unable to load complaint records.")
        st.exception(exc)
        return

    if evidence:
        with st.expander(f"Evidence ({len(evidence)})"):
            for item in evidence:
                st.write(item.get("file_name") or "Evidence")
                st.caption(item.get("file_path") or "")
    else:
        st.caption("No supporting evidence attached.")

    if history:
        with st.expander("Status History"):
            for item in history:
                stamp = item.get("updated_at") or ""
                st.write(
                    f"**{item.get('status')}** — {stamp}"
                )
                if item.get("remarks"):
                    st.caption(item["remarks"])

    current_status = str(row.get("status") or "Submitted")

    # --------------------------------------------------------
    # FORWARD
    # --------------------------------------------------------

    if current_status == "Submitted":
        st.markdown(
            '<div class="admin-action-title">Forward to Department</div>',
            unsafe_allow_html=True,
        )

        st.caption(
            "The selected department is the AI-assisted recommendation. "
            "The administrator may correct it before forwarding."
        )

        options = []
        try:
            all_departments = get_department_list()
            options = [
                (
                    item.get("department"),
                    item.get("authority"),
                )
                for item in all_departments
                if item.get("department")
            ]
        except Exception:
            pass

        if row.get("department") and row.get("department") not in [x[0] for x in options]:
            options.insert(
                0,
                (
                    row.get("department"),
                    row.get("authority") or "",
                ),
            )

        department_names = [x[0] for x in options]
        default_index = (
            department_names.index(row.get("department"))
            if row.get("department") in department_names
            else 0
        )

        selected_department = st.selectbox(
            "Forward to",
            department_names or ["No department available"],
            index=default_index,
            key=f"forward_department_{complaint_id}",
        )

        authority_map = {
            dep: authority
            for dep, authority in options
        }

        external_ref = st.text_input(
            "External reference (optional)",
            placeholder="e.g. official portal / letter / email reference",
            key=f"external_ref_{complaint_id}",
        )

        remarks = st.text_area(
            "Forwarding remarks",
            value=(
                f"Forwarded to {selected_department}."
            ),
            height=90,
            key=f"forward_remarks_{complaint_id}",
        )

        if st.button(
            "Forward Grievance",
            type="primary",
            key=f"forward_button_{complaint_id}",
        ):
            final_remarks = remarks.strip()

            if external_ref.strip():
                final_remarks += (
                    f" External reference: {external_ref.strip()}."
                )

            try:
                success = forward_complaint(
                    complaint_id=complaint_id,
                    department=selected_department,
                    authority=authority_map.get(
                        selected_department,
                        row.get("authority") or "",
                    ),
                    remarks=final_remarks,
                )

                if success:
                    st.success(
                        f"CB-{complaint_id:05d} has been marked as Routed to {selected_department}."
                    )
                    st.rerun()

            except Exception as exc:
                st.error("The grievance could not be forwarded.")
                st.exception(exc)

    else:
        # --------------------------------------------------------
        # MONITOR STATUS
        # --------------------------------------------------------

        st.markdown(
            '<div class="admin-action-title">Monitor Grievance</div>',
            unsafe_allow_html=True,
        )

        st.caption(
            "Use this section to record updates received from the external department."
        )

        next_status_options = [
            status
            for status in STATUSES
            if status != current_status
        ]

        status_col, remarks_col = st.columns([1, 2])

        with status_col:
            new_status = st.selectbox(
                "Update status",
                next_status_options,
                key=f"new_status_{complaint_id}",
            )

        with remarks_col:
            status_remarks = st.text_input(
                "Update remarks",
                placeholder="e.g. Department acknowledged the complaint.",
                key=f"status_remarks_{complaint_id}",
            )

        if st.button(
            "Record Status Update",
            key=f"status_button_{complaint_id}",
        ):
            try:
                success = update_admin_status(
                    complaint_id=complaint_id,
                    status=new_status,
                    remarks=status_remarks,
                )

                if success:
                    st.success(
                        f"Status updated to {new_status}."
                    )
                    st.rerun()

            except Exception as exc:
                st.error("The status could not be updated.")
                st.exception(exc)



def render_admin_portal():
    render_admin_header()

    pages = [
        "Overview",
        "Dashboard",
        "Complaint Queue",
    ]

    page = st.radio(
        "Admin navigation",
        pages,
        horizontal=True,
        label_visibility="collapsed",
        key="admin_navigation",
    )

    if page == "Overview":
        render_overview()

    elif page == "Dashboard":
        render_admin_dashboard()

    else:
        render_complaint_queue()

    st.markdown(
        """
        <div class="cb-footer">
            CivicBridge • Internal Operations Desk
            <br>
            Administrator-controlled grievance review, forwarding and monitoring.
        </div>
        """,
        unsafe_allow_html=True,
    )


if not st.session_state.get("admin_authenticated"):
    render_admin_login()
else:
    render_admin_portal()
