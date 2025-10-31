# app.py — Chartify: Minimal 3-tab app with hidden preview + chat download
# -----------------------------------------------------------------------
# Quick Start:
#   1) pip install streamlit python-dotenv pillow tinydb reportlab google-genai groq
#   2) put GEMINI_API_KEY=... and GROQ_API_KEY=... in a .env file
#   3) streamlit run app.py
#
# Tabs:
#   • Home     → upload charts, run Single/Cross analysis, export PDF
#   • Chat Bot → ask follow-ups using ONLY the latest analysis (hidden preview)
#   • History  → browse/delete previous runs (with thumbnails)
# -----------------------------------------------------------------------

import os
from typing import List, Dict, Any

import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from tinydb import TinyDB, where

# Import only what we actually use from tools.py
from tools import (
    blue_theme_css, decode_uploaded_files, build_pdf_bytes,
    generate_individual_insight_from_rec, generate_cross_chart_insight,
    save_analysis, load_latest_analysis, load_analyses,
    make_thumbnails, thumbnails_gallery, build_chat_markdown, _clear_current_run
)

# Local DB handle (same filename as tools.py uses)
DB = TinyDB("analysis_history_db.json")

# =============================================================================
# Streamlit page + theme
# =============================================================================
st.set_page_config(page_title="Chartify", page_icon="", layout="wide")
st.title("Chartify AI")

blue_theme_css()


# =============================================================================
# Session State (what we keep between reruns)
# =============================================================================
def _init_state():
    st.session_state.setdefault("uploads", [])                 # [{name, data, img, b64, mime}]
    st.session_state.setdefault("analysis_summary", "")
    st.session_state.setdefault("analysis_details", [])        # [{name, insight}]
    st.session_state.setdefault("combined_insight", "")
    st.session_state.setdefault("analysis_done", False)
    st.session_state.setdefault("pdf_bytes", None)
    st.session_state.setdefault("latest_thumbs", [])
    st.session_state.setdefault("rendered_inline", False)      # prevents double-render after progressive flow

    # settings
    st.session_state.setdefault("model_name", "gemini-2.0-flash")  # default
    st.session_state.setdefault("output_style", "Structured (bulleted)")
    st.session_state.setdefault("audience", "Business Professional")
    st.session_state.setdefault("analysis_mode", "Single Chart Analysis")

    # Keep a snapshot of dropdown settings to detect changes (for clearing Home)
    st.session_state.setdefault(
        "prev_settings",
        ("gemini-2.0-flash", "Single Chart Analysis", "Structured (bulleted)", "Business Professional")
    )

    # Ask tab chat (not persisted)
    st.session_state.setdefault("conversation", [])            # [{user, assistant}]

_init_state()

# Supported models (one Google, one Groq multimodal)
MODEL_CHOICES = [
    "gemini-2.0-flash",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

# =============================================================================
# Sidebar (Settings, Exports, Chat download)
# =============================================================================
with st.sidebar:
    st.header("🛠️ Workspace")

    # Model selector
    st.session_state.model_name = st.selectbox(
        "Model provider & mode",
        MODEL_CHOICES,
        index=(MODEL_CHOICES.index(st.session_state.model_name)
               if st.session_state.model_name in MODEL_CHOICES else 0),
        help="Engine used to analyze charts and answer follow-ups."
    )

    # Analysis scope
    st.session_state.analysis_mode = st.selectbox(
        "Analysis scope",
        ["Single Chart Analysis", "Cross Chart Analysis"],
        index=(0 if st.session_state.analysis_mode == "Single Chart Analysis" else 1),
        help="Single = one-by-one insights. Cross = combined insights across all uploads."
    )

    # Output style
    st.session_state.output_style = st.selectbox(
        "Answer style",
        ["Structured (bulleted)", "Narrative (story)"],
        index=(0 if st.session_state.output_style.startswith("Structured") else 1),
        help="Choose concise bullets or a short narrative."
    )

    # Audience tone
    st.session_state.audience = st.selectbox(
        "Select that suits you : ",
        ["Business Person", "Tech Person"],
        index=0 if st.session_state.audience == "Business Professional" else 1,
        help="Tunes wording and emphasis in the insights."
    )

    # Detect ANY change → clear current Home run (uploads + outputs)
    prev = st.session_state.prev_settings
    curr = (
        st.session_state.model_name,
        st.session_state.analysis_mode,
        st.session_state.output_style,
        st.session_state.audience,
    )
    if curr != prev:
        _clear_current_run()
        st.session_state.prev_settings = curr
        st.toast("🧹 Settings changed — cleared current uploads and results.", icon="⚙️")

    st.divider()
    st.subheader("📄 Exports")
    if st.button("⬇️ Prepare PDF Report"):
        if not st.session_state.uploads or not st.session_state.analysis_summary:
            st.warning("No analysis to export yet. Upload and run analysis first.")
            st.session_state.pdf_bytes = None
        else:
            st.session_state.pdf_bytes = build_pdf_bytes(
                st.session_state.uploads, st.session_state.analysis_summary
            )
            st.toast("📄 PDF is ready — click Download.", icon="✅")

    if st.session_state.get("pdf_bytes"):
        st.download_button(
            "Download PDF Report",
            data=st.session_state.pdf_bytes,
            file_name="Chart_Analysis_Report.pdf",
            mime="application/pdf",
            key="pdf_dl_btn"
        )

    st.divider()
    st.subheader("💬 Conversation")
    if st.session_state.conversation:
        chat_md = build_chat_markdown(st.session_state.conversation)
        st.download_button(
            "Download Chat (.md)",
            data=chat_md.encode("utf-8"),
            file_name="chat_history.md",
            mime="text/markdown",
            key="chat_dl_btn"
        )
    else:
        st.caption("No chat yet — ask a follow-up on the **Chat Bot** tab to enable download.")

# =============================================================================
# Tabs
# =============================================================================
home_tab, ask_tab, history_tab = st.tabs(["Home", "Chat Bot", "History"])

# ── Home ───────────────────────────────────────────────────────────────────
with home_tab:
    st.subheader("📥 Upload & Analyze")
    st.caption("Tip: For **Cross** analysis, upload multiple charts. For **Single**, you can still upload several; each gets its own insight.")

    files = st.file_uploader(
        "Drop chart images",
        type=["png", "jpg", "jpeg", "webp", "bmp", "jfif"],
        accept_multiple_files=True,
        help="Accepted: PNG, JPG/JPEG, WEBP, BMP."
    )
    if files:
        decoded = decode_uploaded_files(files)
        if decoded:
            st.session_state.uploads = decoded

    analyze = st.button("🔍 Run Analysis", type="primary")

    # Cross mode → offer a hidden preview of all charts
    if st.session_state.analysis_mode == "Cross Chart Analysis" and st.session_state.uploads:
        with st.expander("📉 Preview uploaded charts (optional)", expanded=False):
            recs = st.session_state.uploads
            cols = st.columns(min(4, max(1, len(recs))))
            for i, rec in enumerate(recs):
                with cols[i % len(cols)]:
                    st.image(rec["img"], caption=rec["name"], use_container_width=True)

    if analyze:
        if not st.session_state.uploads:
            st.error("Please upload charts to analyze.")
        else:
            model_name   = st.session_state.model_name
            audience     = st.session_state.audience
            output_style = st.session_state.output_style
            mode         = st.session_state.analysis_mode

            # Reset current outputs
            st.session_state.analysis_details = []
            st.session_state.combined_insight = ""
            st.session_state.analysis_summary = ""
            st.session_state.pdf_bytes = None
            st.session_state.latest_thumbs = make_thumbnails(st.session_state.uploads)
            st.session_state.rendered_inline = False

            summary_blocks: List[str] = []

            if mode == "Single Chart Analysis":
                # Progressive rendering area
                st.markdown("### 📈 Current Result")
                results_area = st.container()

                for rec in st.session_state.uploads:
                    with results_area:
                        st.markdown(f"#### {rec['name']}")
                        col1, col2 = st.columns([1, 2])

                        with col1:
                            st.image(rec["img"], caption="Chart", use_container_width=True)

                        with col2:
                            insight_placeholder = st.empty()
                            with st.spinner(f"Analyzing {rec['name']}…"):
                                insight = generate_individual_insight_from_rec(
                                    rec, audience, model_name, output_style
                                )
                            # show immediately
                            insight_placeholder.markdown(insight)

                    # update session + summary as we go (immediate persistence)
                    st.session_state.analysis_details.append({"name": rec["name"], "insight": insight})
                    summary_blocks.append(f"**{rec['name']}**\n\n{insight}")

                # finalize shared summary for PDF/Chat
                st.session_state.analysis_summary = "\n\n---\n\n".join(summary_blocks)
                st.session_state.analysis_done = True
                st.session_state.rendered_inline = True
                st.toast("✅ Analysis complete.", icon="✅")

                # Save to history with thumbnails + auto title
                save_analysis({
                    "analysis_mode": st.session_state.analysis_mode,
                    "analysis_summary": st.session_state.analysis_summary,
                    "analysis_details": st.session_state.analysis_details,
                    "combined_insight": st.session_state.combined_insight,
                    "thumbnails": st.session_state.latest_thumbs,
                })

            else:
                # Cross mode stays as a single combined call (cannot stream parts easily)
                with st.spinner("Aggregating cross-chart insights…"):
                    combined = generate_cross_chart_insight(
                        st.session_state.uploads, audience, model_name, output_style
                    )
                st.session_state.combined_insight = combined
                st.session_state.analysis_summary = combined
                st.session_state.analysis_done = True
                st.toast("✅ Analysis complete.", icon="✅")

                save_analysis({
                    "analysis_mode": st.session_state.analysis_mode,
                    "analysis_summary": st.session_state.analysis_summary,
                    "analysis_details": st.session_state.analysis_details,
                    "combined_insight": st.session_state.combined_insight,
                    "thumbnails": st.session_state.latest_thumbs,
                })

    # Render the CURRENT run (no history here) — skip if we already rendered inline
    if (
        st.session_state.analysis_done
        and st.session_state.analysis_summary
        and st.session_state.uploads
        and not st.session_state.get("rendered_inline")
    ):
        if st.session_state.analysis_mode == "Single Chart Analysis":
            st.markdown("### 📈 Current Result")
            name_to_insight = {d["name"]: d["insight"] for d in st.session_state.analysis_details}
            for rec in st.session_state.uploads:
                st.markdown(f"#### {rec['name']}")
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(rec["img"], caption="Chart", use_container_width=True)
                with col2:
                    st.markdown(name_to_insight.get(rec["name"], "No insight available."))
        else:
            st.subheader("🧠 Combined Cross-Chart Insights")
            st.markdown(st.session_state.combined_insight)

# ── Chat Bot (Ask) ─────────────────────────────────────────────────────────
with ask_tab:
    st.header("❓ Follow-up Q&A")

    # Hidden preview of the latest analysis for context
    with st.expander("🔎 Peek latest analysis (optional)", expanded=False):
        latest = load_latest_analysis()
        if latest:
            st.markdown(latest.get("analysis_summary", ""))
        else:
            st.info("No analysis found yet. Run one on the Home tab.")

    latest = load_latest_analysis()
    if not latest:
        st.info("Run an analysis first on the **Home** tab.")
    else:
        col_ask, col_clear = st.columns([0.8, 0.2])
        with col_ask:
            user_input = st.chat_input("Ask a question. Answers use ONLY the latest analysis…")
        with col_clear:
            if st.button("🧹 Clear chat"):
                st.session_state.conversation = []
                st.toast("Chat cleared.", icon="🧽")
                st.rerun()

        if user_input:
            # IMPORTANT: We answer strictly from the analysis summary (no images here)
            context = latest.get("analysis_summary", "")
            prompt = f"Answer based only on the analysis below.\n\n{context}\n\nQuestion: {user_input}"
            parts = [{"text": prompt}]
            with st.spinner("Thinking…"):
                from tools import _generate_with_backend  # import here to keep top clean
                try:
                    answer = _generate_with_backend(st.session_state.model_name, parts)
                except Exception as e:
                    answer = f"API Error: {e}"
            st.session_state.conversation.append({"user": user_input, "assistant": answer})
            st.toast("💬 Answer added to chat.", icon="✅")
            st.rerun()

        # Render chat messages
        if not st.session_state.conversation:
            st.info("No chat yet. Ask a question above.")
        else:
            for msg in st.session_state.conversation:
                if msg.get("user"):
                    st.chat_message("user").markdown(msg["user"])
                if msg.get("assistant"):
                    st.chat_message("assistant").markdown(msg["assistant"])

# ── History ────────────────────────────────────────────────────────────────
with history_tab:
    st.header("📚 Past Runs")

    analyses_tbl = DB.table("analyses")
    items = load_analyses()

    # Clear All
    if items:
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            st.caption(f"Showing {len(items)} saved analyses.")
        with col2:
            if st.button("🧹 Clear All History", use_container_width=True):
                analyses_tbl.truncate()
                st.toast("🧽 All history cleared from database.", icon="✅")
                st.rerun()
    else:
        st.info("No saved analyses yet.")

    # Cards
    for h in items:
        ts = h.get("ts", "")[:19].replace("T", " ")
        title = h.get("title") or ("Single" if h.get("analysis_mode", "").startswith("Single") else "Cross")
        label = f"{ts} — {title}"

        cols = st.columns([0.95, 0.05])
        with cols[0]:
            exp = st.expander(label, expanded=False)
        with cols[1]:
            # Use timestamp as stable key for delete
            if st.button("✖️", key=f"del_{ts}"):
                analyses_tbl.remove(where("ts") == h["ts"])
                st.toast(f"Deleted history entry from {ts}", icon="🗑️")
                st.rerun()

        with exp:
            if h.get("thumbnails"):
                thumbnails_gallery(h["thumbnails"])
                st.markdown("---")
            st.markdown(h.get("analysis_summary", ""))
