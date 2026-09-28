"""
app.py — Streamlit UI for the Forensic Evidence Management System.

Run with:
    streamlit run src/app.py
"""
from __future__ import annotations

import os
import sys

# Ensure src/ is on the path so sibling imports work when invoked from the
# project root (e.g. `streamlit run src/app.py`).
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import streamlit as st
import pandas as pd
from datetime import datetime

from constants import (
    EvidenceCategory,
    EvidenceStatus,
    Priority,
    LabDepartment,
)
from models import EvidenceItem, Case
from classifier import EvidenceClassifier
from scoring import score_batch
from scheduler import LabScheduler
from database import EvidenceStore
from demo_data import get_demo_cases, get_demo_items
from watsonx_client import get_watsonx_client


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ForensIQ — Evidence Management",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Session state bootstrap ───────────────────────────────────────────────────

def _init_session() -> None:
    if "store" not in st.session_state:
        st.session_state.store = EvidenceStore()

    if "wx_client" not in st.session_state:
        st.session_state.wx_client = get_watsonx_client()

    if "classifier" not in st.session_state:
        st.session_state.classifier = EvidenceClassifier(
            watsonx_client=st.session_state.wx_client
        )

    if "demo_loaded" not in st.session_state:
        st.session_state.demo_loaded = False


_init_session()

store: EvidenceStore = st.session_state.store
classifier: EvidenceClassifier = st.session_state.classifier
wx_client = st.session_state.wx_client


# ── Helpers ───────────────────────────────────────────────────────────────────

PRIORITY_COLOURS = {
    Priority.CRITICAL: "🔴",
    Priority.HIGH: "🟠",
    Priority.MEDIUM: "🟡",
    Priority.LOW: "🟢",
}

STATUS_COLOURS = {
    EvidenceStatus.RECEIVED: "🔵",
    EvidenceStatus.IN_ANALYSIS: "🟣",
    EvidenceStatus.PENDING_REVIEW: "🟡",
    EvidenceStatus.COMPLETED: "🟢",
    EvidenceStatus.ON_HOLD: "⚪",
}


def _pipeline(items: list[EvidenceItem]) -> list[EvidenceItem]:
    """Classify → score → schedule a list of items."""
    classifier.classify_batch(items)
    scored = score_batch(items)
    scheduler = LabScheduler()
    scheduler.schedule_batch(scored)
    return scored


def _items_to_df(items: list[EvidenceItem]) -> pd.DataFrame:
    rows = []
    for i in items:
        rows.append(
            {
                "ID": i.id,
                "Case": i.case_id or "—",
                "Description": i.description[:60] + ("…" if len(i.description) > 60 else ""),
                "Category": i.category.value if i.category else "—",
                "Priority": (PRIORITY_COLOURS.get(i.priority, "") + " " + i.priority.value)
                if i.priority
                else "—",
                "Score": i.urgency_score,
                "Status": (STATUS_COLOURS.get(i.status, "") + " " + i.status.value),
                "Department": i.assigned_department.value if i.assigned_department else "—",
                "Scheduled": i.scheduled_date.strftime("%d %b %Y") if i.scheduled_date else "—",
                "Est. Completion": i.estimated_completion.strftime("%d %b %Y")
                if i.estimated_completion
                else "—",
            }
        )
    return pd.DataFrame(rows)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🔬 ForensIQ")
    st.caption("Forensic Evidence Management System")
    st.divider()

    page = st.radio(
        "Navigation",
        ["Dashboard", "Evidence List", "Add Evidence", "Case View", "About"],
        label_visibility="collapsed",
    )

    st.divider()

    # watsonx status
    if wx_client is not None:
        st.success("✅ IBM watsonx.ai connected")
    else:
        st.info("🔌 Offline mode (rule-based AI)")

    st.divider()

    if st.button("🗂 Load demo data", use_container_width=True):
        if not st.session_state.demo_loaded:
            cases = get_demo_cases()
            items = get_demo_items()
            for c in cases:
                store.add_case(c)
            _pipeline(items)
            for item in items:
                store.add_item(item)
            st.session_state.demo_loaded = True
            st.success(f"Loaded {len(items)} demo items across {len(cases)} cases.")
        else:
            st.warning("Demo data already loaded.")

    if st.button("🗑 Clear all data", use_container_width=True):
        store.clear()
        st.session_state.demo_loaded = False
        st.success("All data cleared.")


# ── Pages ─────────────────────────────────────────────────────────────────────

# ── Dashboard ─────────────────────────────────────────────────────────────────
if page == "Dashboard":
    st.title("📊 Dashboard")

    summary = store.summary()
    items = store.all_items()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Evidence Items", summary["total_items"])
    col2.metric("Active Cases", summary["total_cases"])
    col3.metric(
        "Critical / High",
        summary["by_priority"].get("Critical", 0)
        + summary["by_priority"].get("High", 0),
    )
    col4.metric(
        "Awaiting Analysis",
        summary["by_status"].get("Received", 0)
        + summary["by_status"].get("On Hold", 0),
    )

    st.divider()

    if not items:
        st.info("No evidence loaded yet. Use **Load demo data** in the sidebar or add items manually.")
    else:
        st.subheader("Priority distribution")
        priority_data = {
            k: v for k, v in summary["by_priority"].items() if v > 0
        }
        if priority_data:
            prio_df = pd.DataFrame(
                {"Priority": list(priority_data.keys()), "Count": list(priority_data.values())}
            )
            st.bar_chart(prio_df.set_index("Priority"))

        st.subheader("Top 10 most urgent items")
        top10 = sorted(items, key=lambda i: i.urgency_score, reverse=True)[:10]
        st.dataframe(_items_to_df(top10), use_container_width=True, hide_index=True)

        st.subheader("Status breakdown")
        status_data = {k: v for k, v in summary["by_status"].items() if v > 0}
        if status_data:
            st.bar_chart(
                pd.DataFrame(
                    {"Status": list(status_data.keys()), "Count": list(status_data.values())}
                ).set_index("Status")
            )


# ── Evidence List ─────────────────────────────────────────────────────────────
elif page == "Evidence List":
    st.title("📋 Evidence List")

    items = store.all_items()

    if not items:
        st.info("No evidence items yet.")
    else:
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_priority = st.multiselect(
                "Priority",
                [p.value for p in Priority],
                default=[],
            )
        with col_f2:
            filter_status = st.multiselect(
                "Status",
                [s.value for s in EvidenceStatus],
                default=[],
            )
        with col_f3:
            filter_category = st.multiselect(
                "Category",
                [c.value for c in EvidenceCategory],
                default=[],
            )

        filtered = items
        if filter_priority:
            filtered = [i for i in filtered if i.priority and i.priority.value in filter_priority]
        if filter_status:
            filtered = [i for i in filtered if i.status.value in filter_status]
        if filter_category:
            filtered = [i for i in filtered if i.category and i.category.value in filter_category]

        st.caption(f"Showing {len(filtered)} of {len(items)} items")
        st.dataframe(
            _items_to_df(sorted(filtered, key=lambda i: i.urgency_score, reverse=True)),
            use_container_width=True,
            hide_index=True,
        )

        # Detail expander
        st.divider()
        st.subheader("Item detail")
        item_ids = [i.id for i in filtered]
        if item_ids:
            selected_id = st.selectbox("Select item ID", item_ids)
            selected = store.get_item(selected_id)
            if selected:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Description:** {selected.description}")
                    st.markdown(f"**Category:** {selected.category.value if selected.category else '—'} (confidence: {selected.category_confidence:.0%}, source: {selected.category_source})")
                    st.markdown(f"**Status:** {selected.status.value}")
                    st.markdown(f"**Received:** {selected.received_at.strftime('%d %b %Y %H:%M')}")
                with c2:
                    st.markdown(f"**Urgency score:** {selected.urgency_score} / 100")
                    st.markdown(f"**Priority:** {selected.priority.value if selected.priority else '—'}")
                    st.markdown(f"**Department:** {selected.assigned_department.value if selected.assigned_department else '—'}")
                    st.markdown(f"**Scheduled:** {selected.scheduled_date.strftime('%d %b %Y') if selected.scheduled_date else '—'}")
                    st.markdown(f"**Est. completion:** {selected.estimated_completion.strftime('%d %b %Y') if selected.estimated_completion else '—'}")
                if selected.score_breakdown:
                    with st.expander("Score breakdown"):
                        bd = selected.score_breakdown
                        bd_df = pd.DataFrame(
                            {"Factor": list(bd.keys()), "Points": list(bd.values())}
                        ).query("Factor != 'total'")
                        st.bar_chart(bd_df.set_index("Factor"))

                # Status update
                st.divider()
                new_status = st.selectbox(
                    "Update status",
                    [s.value for s in EvidenceStatus],
                    index=[s.value for s in EvidenceStatus].index(selected.status.value),
                    key=f"status_{selected_id}",
                )
                if st.button("Save status", key=f"save_{selected_id}"):
                    selected.status = EvidenceStatus(new_status)
                    store.update_item(selected)
                    st.success("Status updated.")
                    st.rerun()


# ── Add Evidence ──────────────────────────────────────────────────────────────
elif page == "Add Evidence":
    st.title("➕ Add Evidence Item")

    with st.form("add_evidence_form"):
        case_options = ["— (no case)"] + [f"{c.id} — {c.title}" for c in store.all_cases()]
        case_selection = st.selectbox("Link to case", case_options)
        description = st.text_area("Description *", height=120, placeholder="Describe the evidence item in plain language…")
        notes = st.text_input("Additional notes")
        submitted = st.form_submit_button("Add & analyse", use_container_width=True)

    if submitted:
        if not description.strip():
            st.error("Description is required.")
        else:
            case_id = ""
            if case_selection != "— (no case)":
                case_id = case_selection.split(" — ")[0]

            item = EvidenceItem(
                case_id=case_id,
                description=description.strip(),
                notes=notes.strip(),
            )
            # Run full pipeline
            classifier.classify(item)
            from scoring import score_item
            score_item(item, has_active_case=bool(case_id))
            scheduler = LabScheduler()
            scheduler.schedule(item)
            store.add_item(item)

            st.success(f"Evidence item **{item.id}** added successfully.")
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("Category", item.category.value if item.category else "Unknown")
            col_r2.metric("Urgency Score", item.urgency_score)
            col_r3.metric("Priority", item.priority.value if item.priority else "—")
            st.info(f"Assigned to: **{item.assigned_department.value if item.assigned_department else '—'}** | Scheduled: **{item.scheduled_date.strftime('%d %b %Y') if item.scheduled_date else '—'}**")

    st.divider()
    st.subheader("Add a new case")
    with st.form("add_case_form"):
        case_title = st.text_input("Case title *")
        case_desc = st.text_area("Case description")
        case_submitted = st.form_submit_button("Create case", use_container_width=True)

    if case_submitted:
        if not case_title.strip():
            st.error("Case title is required.")
        else:
            new_case = Case(title=case_title.strip(), description=case_desc.strip())
            store.add_case(new_case)
            st.success(f"Case **{new_case.id}** created: {new_case.title}")


# ── Case View ─────────────────────────────────────────────────────────────────
elif page == "Case View":
    st.title("🗂 Case View")

    cases = store.all_cases()
    if not cases:
        st.info("No cases loaded yet.")
    else:
        case_options = {f"{c.id} — {c.title}": c.id for c in cases}
        selected_key = st.selectbox("Select case", list(case_options.keys()))
        selected_case = store.get_case(case_options[selected_key])

        if selected_case:
            st.markdown(f"**Case ID:** {selected_case.id}")
            st.markdown(f"**Created:** {selected_case.created_at.strftime('%d %b %Y')}")
            st.markdown(f"**Description:** {selected_case.description or '—'}")
            st.markdown(f"**Highest Priority:** {selected_case.highest_priority.value if selected_case.highest_priority else '—'}")
            st.divider()

            case_items = store.items_for_case(selected_case.id)
            st.subheader(f"{len(case_items)} evidence item(s)")
            if case_items:
                st.dataframe(
                    _items_to_df(sorted(case_items, key=lambda i: i.urgency_score, reverse=True)),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No evidence items linked to this case.")


# ── About ─────────────────────────────────────────────────────────────────────
elif page == "About":
    st.title("ℹ️ About ForensIQ")
    st.markdown(
        """
**ForensIQ** is a forensic evidence management system that helps forensic labs
automatically classify, score, and schedule evidence items for analysis.

### How it works

1. **Ingest** — A forensic officer submits an evidence item with a plain-language description.
2. **Classify** — The rule-based engine (optionally enhanced by IBM watsonx.ai Granite) assigns the item to a forensic category (Biological, Digital, Document, Trace, Impression, or Video).
3. **Score** — An urgency score (0–100) is computed from category, age, case link, current status, and urgency keywords in the description.
4. **Schedule** — The item is routed to the correct lab department and assigned a scheduled analysis date based on its priority tier and department capacity.
5. **Track** — Officers can update the status of each item as it progresses through the lab.

### Evidence categories

| Category | Examples |
|---|---|
| Biological | Hair strand, blood, swab, saliva |
| Digital | Mobile phone, laptop, USB drive |
| Video | CCTV recording, dashcam footage |
| Document | Handwritten note, printed letter |
| Impression | Footwear impression, tyre mark |
| Trace | Fingerprint, fabric fibre, paint transfer |

### Offline mode vs. IBM watsonx.ai

The application works **fully offline** with no credentials required.
Set `USE_WATSONX=true` in `.env` and supply your IBM credentials to enable
the Granite model as an optional classifier enhancement for ambiguous descriptions.

### Technology stack

- Python 3.11+
- Streamlit (UI)
- IBM watsonx.ai / Granite (optional AI classifier)
        """
    )
