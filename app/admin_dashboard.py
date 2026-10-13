from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin_db import STATUSES, get_admin_complaints

NAVY = "#12355B"
ORANGE = "#E07A1F"
GREEN = "#258765"
TEAL = "#087E83"
GREY = "#64748B"
BLACK = "#000000"

STATUS_COLORS = {
    "Submitted": ORANGE,
    "Routed": NAVY,
    "In Progress": TEAL,
    "Resolved": GREEN,
    "Closed": GREY,
}


def load_dashboard_css():
    css_path = BASE_DIR / "admin_dashboard.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


@st.cache_data(ttl=60, show_spinner=False)
def _load_complaints():
    return get_admin_complaints()


def _prepare_dataframe(rows):
    columns = ["complaint_id", "category", "department", "authority", "location", "status", "created_at", "citizen_name"]
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    for col, fallback in [
        ("category", "Uncategorised"),
        ("department", "Unassigned"),
        ("location", "Location not provided"),
        ("status", "Unknown"),
        ("citizen_name", "Citizen"),
    ]:
        df[col] = df[col].fillna(fallback).replace("", fallback)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    return df


def _metric_card(label, value, caption, accent):
    st.markdown(
        f"""<div class="cb-dashboard-metric" style="border-top:4px solid {accent}">
        <div class="cb-dashboard-metric-label">{label}</div>
        <div class="cb-dashboard-metric-value">{value}</div>
        <div class="cb-dashboard-metric-caption">{caption}</div></div>""",
        unsafe_allow_html=True,
    )


def _section_title(title, subtitle=None):
    st.markdown(f'<div class="cb-dashboard-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="cb-dashboard-section-subtitle">{subtitle}</div>', unsafe_allow_html=True)



def _style_chart(fig, height=320):
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            color="#000000",
            family="Arial, sans-serif",
            size=12,
        ),
        margin=dict(l=12, r=35, t=25, b=15),
        showlegend=False,

        # Force axis titles to black
        xaxis_title_font=dict(color="#000000", size=14),
        yaxis_title_font=dict(color="#000000", size=14),
    )

    fig.update_xaxes(
        title_font=dict(color="#000000", size=14),
        tickfont=dict(color="#000000", size=12),
        tickcolor="#000000",
        linecolor="#000000",
        gridcolor="#E5E7EB",
        zeroline=False,
    )

    fig.update_yaxes(
        title_font=dict(color="#000000", size=14),
        tickfont=dict(color="#000000", size=12),
        tickcolor="#000000",
        linecolor="#000000",
        gridcolor="#E5E7EB",
        zeroline=False,
    )

    fig.update_traces(
        textfont=dict(color="#000000", size=12)
    )

    return fig


def render_admin_dashboard():
    """A simple, unfiltered overview of all complaints; leaves admin workflows unchanged."""
    load_dashboard_css()
    st.markdown(
        """<div class="cb-dashboard-header">
        <div class="cb-dashboard-eyebrow">CIVICBRIDGE · OPERATIONS</div>
        <div class="cb-dashboard-title">Grievance Dashboard</div>
        <div class="cb-dashboard-description">An overview of complaint status, reported issues, assigned departments and locations.</div>
        </div>""",
        unsafe_allow_html=True,
    )

    try:
        df = _prepare_dataframe(_load_complaints())
    except Exception:
        st.error("Unable to load grievance records for analytics. Check the database connection and try again.")
        return

    if df.empty:
        st.info("No grievance records are available yet. Analytics will appear when complaints are submitted.")
        return

    status_counts = df["status"].value_counts()
    total = len(df)
    submitted = int(status_counts.get("Submitted", 0))
    in_progress = int(status_counts.get("In Progress", 0))
    resolved_closed = int(status_counts.get("Resolved", 0) + status_counts.get("Closed", 0))
    completion_rate = resolved_closed / total * 100 if total else 0

    kpis = st.columns(4, gap="medium")
    metrics = [
        ("Total complaints", f"{total:,}", "All recorded complaints", NAVY),
        ("Submitted", f"{submitted:,}", "Awaiting review", ORANGE),
        ("In progress", f"{in_progress:,}", "Currently being handled", TEAL),
        ("Resolved / closed", f"{resolved_closed:,}", f"{completion_rate:.1f}% of all complaints", GREEN),
    ]
    for col, metric in zip(kpis, metrics):
        with col:
            _metric_card(*metric)

    st.markdown("<div class='cb-dashboard-gap'></div>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")

    with left:
        _section_title("Complaint status")
        order = [s for s in STATUSES if s in status_counts.index]
        order += [s for s in status_counts.index if s not in order]
        status_df = pd.DataFrame({"Status": order, "Complaints": [int(status_counts[s]) for s in order]})
        fig = px.bar(status_df, x="Status", y="Complaints", text="Complaints",
                     color="Status", color_discrete_map=STATUS_COLORS)
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig = _style_chart(fig, 310)
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        _section_title("Complaints by category")
        category_df = (df.groupby("category", as_index=False).size()
                       .rename(columns={"size": "Complaints"})
                       .sort_values("Complaints", ascending=True))
        fig = px.bar(category_df, x="Complaints", y="category", orientation="h",
                     text="Complaints", color_discrete_sequence=[ORANGE])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig = _style_chart(fig, max(310, 30 * len(category_df) + 40))
        fig.update_layout(
                    yaxis_title=None,
                    xaxis_title=dict(
                            text="Number of complaints",
                            font=dict(color="#000000", size=14)
                        ),
                        xaxis=dict(
                            title=dict(font=dict(color="#000000", size=14))
                        )
                )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        fig.update_xaxes(title_font=dict(color="#000000", size=14))

    left, right = st.columns(2, gap="large")
    with left:
        _section_title("Department workload")
        dept_df = (df.groupby("department", as_index=False).size()
                   .rename(columns={"size": "Complaints"})
                   .sort_values("Complaints", ascending=True))
        fig = px.bar(dept_df, x="Complaints", y="department", orientation="h",
                     text="Complaints", color_discrete_sequence=[NAVY])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig = _style_chart(fig, max(310, 30 * len(dept_df) + 40))
        fig.update_layout(
                    yaxis_title=None,
                    xaxis_title=dict(
                            text="Number of complaints",
                            font=dict(color="#000000", size=14)
                        ),
                        xaxis=dict(
                            title=dict(font=dict(color="#000000", size=14))
                        )
                )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        fig.update_xaxes(title_font=dict(color="#000000", size=14))

    with right:
        _section_title("Top reported locations")
        loc_df = (df.groupby("location", as_index=False).size()
                  .rename(columns={"size": "Complaints"})
                  .sort_values("Complaints", ascending=False)
                  .head(10)
                  .sort_values("Complaints", ascending=True))
        fig = px.bar(loc_df, x="Complaints", y="location", orientation="h",
                     text="Complaints", color_discrete_sequence=[GREEN])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig = _style_chart(fig, max(310, 30 * len(loc_df) + 40))
        fig.update_layout(
            yaxis_title=None,
            xaxis_title=dict(
                    text="Number of complaints",
                    font=dict(color="#000000", size=14)
                ),
                xaxis=dict(
                    title=dict(font=dict(color="#000000", size=14))
                )
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        fig.update_xaxes(title_font=dict(color="#000000", size=14))

    st.caption(f"Showing all {total:,} complaint records. Charts reflect current complaint records and their current statuses.")
