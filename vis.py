import os
import io
import base64
import tempfile
from datetime import datetime
from typing import List, Dict, Any

import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from google import genai  # pip install google-genai

# PDF (reportlab)
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

# =========================
# App Config
# =========================
st.set_page_config(page_title="Gemini Chart Analyzer", page_icon="📊", layout="wide")
st.title("📊 Gemini Chart Analyzer")

# =========================
# Session State Defaults
# =========================
def _init_state():
    st.session_state.setdefault("uploads", [])
    st.session_state.setdefault("analysis_summary", "")
    st.session_state.setdefault("analysis_details", [])  # list of {name, insight}
    st.session_state.setdefault("combined_insight", "")
    st.session_state.setdefault("model_name", "gemini-2.0-flash")
    st.session_state.setdefault("output_style", "Structured (bulleted)")
    st.session_state.setdefault("conversation", [])
    st.session_state.setdefault("audience", "Business Professional")
    st.session_state.setdefault("analysis_mode", "Single Chart Analysis")
    st.session_state.setdefault("prev_analysis_mode", "Single Chart Analysis")
    st.session_state.setdefault("pdf_bytes", None)
    st.session_state.setdefault("analysis_done", False)

_init_state()

# =========================
# Env & Client
# =========================
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("⚠️ GEMINI_API_KEY missing. Create a .env file with GEMINI_API_KEY=your_key")
    st.stop()
client = genai.Client(api_key=API_KEY)

MODEL_CHOICES = ["gemini-2.0-flash", "gemini-2.0-pro"]

# =========================
# Helpers
# =========================
def guess_mime(name: str) -> str:
    nl = name.lower()
    if nl.endswith(".png"): return "image/png"
    if nl.endswith(".webp"): return "image/webp"
    if nl.endswith(".bmp"): return "image/bmp"
    return "image/jpeg"

def decode_uploaded_files(files) -> List[Dict[str, Any]]:
    out = []
    if not files:
        return out
    for f in files:
        data = f.getvalue()
        if not data or len(data) < 10:
            continue
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            continue
        b64 = base64.b64encode(data).decode("utf-8")
        out.append({"name": f.name, "data": data, "img": img, "b64": b64, "mime": guess_mime(f.name)})
    return out

def generate_individual_insight_from_rec(rec, audience, model_name, output_style):
    tone_note = "business-friendly" if audience == "Business Professional" else "technically precise"
    prompt = f"""
You are a professional data analyst. Analyze the uploaded chart image and provide a structured, professional response.
Audience: {audience}.
Instructions:
1) Begin with a short overview summary.
2) Follow with key findings and insights.
3) Keep the tone {tone_note}.
4) {"Use concise bullets." if output_style.startswith("Structured") else "Write it as a short narrative paragraph."}
"""
    contents = [{
        "role": "user",
        "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": rec["mime"], "data": rec["b64"]}},
        ],
    }]
    try:
        response = client.models.generate_content(model=model_name, contents=contents)
        return (getattr(response, "text", "") or "").strip() or "No insights generated."
    except Exception as e:
        return f"API Error: {e}"

def generate_cross_chart_insight(recs, audience, model_name, output_style):
    tone_note = "business-friendly" if audience == "Business Professional" else "technically precise"
    prompt = f"""
You are a professional data analyst. Analyze the relationship and trends across multiple charts and provide a structured summary.
Audience: {audience}.
Instructions:
1) Summarize overall trends observed across all charts.
2) Mention comparisons, correlations, or differences if visible.
3) Keep the tone {tone_note}.
4) {"Use concise bullets." if output_style.startswith("Structured") else "Write it as a short narrative paragraph."}
"""
    parts = [{"text": prompt}]
    for rec in recs:
        parts.append({"inline_data": {"mime_type": rec["mime"], "data": rec["b64"]}})
    contents = [{"role": "user", "parts": parts}]
    try:
        response = client.models.generate_content(model=model_name, contents=contents)
        return (getattr(response, "text", "") or "").strip() or "No insights generated."
    except Exception as e:
        return f"API Error: {e}"

def build_pdf_bytes(uploads, summary_text) -> bytes:
    if not uploads or not summary_text:
        return b""
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>📊 Gemini Chart Analysis Report</b>", styles["Title"]),
        Spacer(1, 20),
        Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]),
        Paragraph("Generated by: Gemini Chart Analyzer", styles["Normal"]),
        Spacer(1, 20),
    ]
    for rec in uploads:
        story.append(Paragraph(f"<b>{rec['name']}</b>", styles["Heading2"]))
        img_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        rec["img"].save(img_temp.name)
        story.append(RLImage(img_temp.name, width=400, height=250))
        story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Analysis Summary:</b>", styles["Heading2"]))
    story.append(Paragraph(summary_text.replace("\n", "<br/>"), styles["Normal"]))
    pdf_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(pdf_temp.name, pagesize=A4)
    doc.build(story)
    with open(pdf_temp.name, "rb") as f:
        return f.read()

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("⚙️ Settings")

    st.session_state.model_name = st.selectbox(
        "Model", MODEL_CHOICES,
        index=MODEL_CHOICES.index(st.session_state.model_name)
        if st.session_state.model_name in MODEL_CHOICES else 0
    )

    prev_mode = st.session_state.get("prev_analysis_mode", st.session_state.analysis_mode)
    st.session_state.analysis_mode = st.selectbox(
        "Analysis Type",
        ["Single Chart Analysis", "Cross Chart Analysis"],
        index=(0 if st.session_state.analysis_mode == "Single Chart Analysis" else 1)
    )

    # ✅ Clear uploads + output once on mode switch
    if st.session_state.analysis_mode != prev_mode:
        st.session_state.uploads = []
        st.session_state.analysis_summary = ""
        st.session_state.analysis_details = []
        st.session_state.combined_insight = ""
        st.session_state.pdf_bytes = None
        st.session_state.analysis_done = False
        st.toast("🧹 Cleared uploads and analysis due to mode switch.", icon="⚙️")
    st.session_state.prev_analysis_mode = st.session_state.analysis_mode

    st.session_state.output_style = st.selectbox(
        "Output Format",
        ["Structured (bulleted)", "Narrative (story)"],
        index=(0 if st.session_state.output_style.startswith("Structured") else 1)
    )

    st.session_state.audience = st.selectbox(
        "Audience",
        ["Business Professional", "Data Scientist"],
        index=0 if st.session_state.audience == "Business Professional" else 1
    )

    st.divider()
    st.subheader("📄 Export")

    if st.button("⬇️ Generate PDF Report", key="gen_pdf_btn"):
        if not st.session_state.uploads or not st.session_state.analysis_summary:
            st.warning("No analysis data available to export.")
            st.session_state.pdf_bytes = None
        else:
            st.session_state.pdf_bytes = build_pdf_bytes(
                st.session_state.uploads, st.session_state.analysis_summary
            )
            st.toast("📄 PDF prepared. Click Download.", icon="✅")

    if st.session_state.get("pdf_bytes"):
        st.download_button(
            "Download PDF Report",
            data=st.session_state.pdf_bytes,
            file_name="Chart_Analysis_Report.pdf",
            mime="application/pdf",
        )

    if st.session_state.conversation:
        chat_text = "\n\n".join(
            [f"User: {m['user']}\nAssistant: {m['assistant']}" for m in st.session_state.conversation]
        )
        st.download_button("💾 Download Chat History", data=chat_text, file_name="conversation.txt", mime="text/plain")
    else:
        st.info("No chat history yet.")

# =========================
# MAIN UI
# =========================
home_tab, ask_tab = st.tabs(["Home", "Ask"])

with home_tab:
    files = st.file_uploader(
        "Upload chart images",
        type=["png", "jpg", "jpeg", "webp", "bmp", "jfif"],
        accept_multiple_files=True
    )
    if files:
        decoded = decode_uploaded_files(files)
        if decoded:
            st.session_state.uploads = decoded

    analyze = st.button("🔍 Analyze Charts", type="primary")

    # 🔎 Cross-chart: optional preview grid BEFORE analysis
    if st.session_state.analysis_mode == "Cross Chart Analysis" and st.session_state.uploads:
        with st.expander("📉 Preview Uploaded Charts", expanded=False):
            st.subheader("🖼️ Charts Preview")
            recs = st.session_state.uploads
            cols = st.columns(min(4, len(recs)))
            for i, rec in enumerate(recs):
                with cols[i % len(cols)]:
                    st.image(rec["img"], caption=rec["name"], use_container_width=True)

    if analyze:
        if not st.session_state.uploads:
            st.error("Please upload at least one chart to analyze.")
        else:
            # IMPORTANT: compute & store ONLY. Do not render here.
            model_name = st.session_state.model_name
            audience = st.session_state.audience
            output_style = st.session_state.output_style
            mode = st.session_state.analysis_mode

            st.session_state.analysis_details = []
            st.session_state.combined_insight = ""
            summary_blocks = []

            if mode == "Single Chart Analysis":
                for rec in st.session_state.uploads:
                    with st.spinner(f"Analyzing {rec['name']}..."):
                        insight = generate_individual_insight_from_rec(rec, audience, model_name, output_style)
                    st.session_state.analysis_details.append({"name": rec["name"], "insight": insight})
                    summary_blocks.append(f"**{rec['name']}**\n\n{insight}")
            else:
                with st.spinner("Performing cross-chart analysis..."):
                    combined = generate_cross_chart_insight(st.session_state.uploads, audience, model_name, output_style)
                st.session_state.combined_insight = combined
                summary_blocks.append(combined)

            st.session_state.analysis_summary = "\n\n---\n\n".join(summary_blocks)
            st.session_state.pdf_bytes = None  # reset pdf; analysis changed
            st.session_state.analysis_done = True
            st.toast("✅ Analysis complete.", icon="✅")

# ✅ Render analysis ONCE (persistent, no duplicates)
if st.session_state.analysis_done and st.session_state.analysis_summary:
    if st.session_state.analysis_mode == "Single Chart Analysis":
        # Side-by-side chart + insight per file
        name_to_insight = {d["name"]: d["insight"] for d in st.session_state.analysis_details}
        for rec in st.session_state.uploads:
            st.markdown(f"### {rec['name']}")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(rec["img"], caption="Chart", use_container_width=True)
            with col2:
                st.markdown(name_to_insight.get(rec["name"], "No insight available."))
    else:
        st.subheader("Combined Cross-Chart Insights")
        st.markdown(st.session_state.combined_insight)

with ask_tab:
    st.header("❓ Ask a question about the charts")
    if not st.session_state.analysis_summary:
        st.info("No analysis found. Please analyze charts on the Home tab first.")
    else:
        user_input = st.chat_input("Type your question...")
        if user_input:
            prompt = f"Answer based only on the analysis below.\n\n{st.session_state.analysis_summary}\n\nQuestion: {user_input}"
            contents = [{"role": "user", "parts": [{"text": prompt}]}]
            with st.spinner("Getting answer..."):
                try:
                    res = client.models.generate_content(model=st.session_state.model_name, contents=contents)
                    answer = (getattr(res, "text", "") or "").strip()
                except Exception as e:
                    answer = f"API Error: {e}"
            if answer:
                st.session_state.conversation.append({"user": user_input, "assistant": answer})

        for msg in st.session_state.conversation:
            st.chat_message("user").markdown(msg["user"])
            st.chat_message("assistant").markdown(msg["assistant"])
