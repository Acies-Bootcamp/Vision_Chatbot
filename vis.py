import os
import io
import base64
from typing import List, Dict, Any
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from google import genai

st.set_page_config(page_title="Gemini Chart Analyzer", page_icon="📊", layout="wide")
st.title("📊 Gemini Chart Analyzer")

def _init_state():
    st.session_state.setdefault("uploads", [])
    st.session_state.setdefault("analysis_summary", "")
    st.session_state.setdefault("model_name", "gemini-2.0-flash")
    st.session_state.setdefault("output_style", "Structured (bulleted)")
    st.session_state.setdefault("conversation", [])
    st.session_state.setdefault("audience", "Business Professional")
    st.session_state.setdefault("analysis_mode", "Single Chart Analysis")

_init_state()

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("⚠️ GEMINI_API_KEY missing. Create a .env file with GEMINI_API_KEY=your_key")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_CHOICES = ["gemini-2.0-flash", "gemini-2.0-pro"]

# Helper functions
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
            st.warning(f"⚠️ {f.name} is empty or corrupted. Skipping.")
            continue
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as e:
            st.warning(f"⚠️ Skipping {f.name}: not a valid image ({e})")
            continue
        b64 = base64.b64encode(data).decode("utf-8")
        out.append({
            "name": f.name, "data": data, "img": img, "b64": b64, "mime": guess_mime(f.name)
        })
    return out

def generate_individual_insight_from_rec(rec: Dict[str, Any], audience: str, model_name: str, output_style: str) -> str:
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

def generate_cross_chart_insight(recs: List[Dict[str, Any]], audience: str, model_name: str, output_style: str) -> str:
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

# Styling
PALE_PINK = "#FFDDEE"
PEACH = "#FFE5B4"
st.markdown(
    f"""
    <style>
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) > div[data-testid="stTab"] {{
        background-color: {PALE_PINK} !important;
        border-radius: 5px 5px 0 0 !important;
        padding: 10px 15px !important;
    }}
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) > div[data-testid="stTab"] {{
        background-color: {PEACH} !important;
        border-radius: 5px 5px 0 0 !important;
        padding: 10px 15px !important;
    }}
    .control-row > div {{
        display: inline-block;
        vertical-align: middle;
        margin-right: 12px;
        background: #fff0f5;
        border-radius: 8px;
        padding: 8px 12px;
    }}
    [data-testid="stChatMessage"] {{
        max-width: 80%;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Control Panel
def render_controls_row():
    cols = st.columns([1.3, 1.3, 1.3, 1.3], gap="large")
    with cols[0]:
        st.session_state.model_name = st.selectbox(
            "Model",
            MODEL_CHOICES,
            index=(MODEL_CHOICES.index(st.session_state.model_name)
                   if st.session_state.model_name in MODEL_CHOICES else 0),
            help="Use flash for speed; pro for higher quality."
        )
    with cols[1]:
        st.session_state.analysis_mode = st.selectbox(
            "Analysis Type",
            ["Single Chart Analysis", "Cross Chart Analysis"],
            index=(0 if st.session_state.analysis_mode == "Single Chart Analysis" else 1)
        )
    with cols[2]:
        st.session_state.output_style = st.selectbox(
            "Output format",
            ["Structured (bulleted)", "Narrative (story)"],
            index=(0 if st.session_state.output_style.startswith("Structured") else 1)
        )
    with cols[3]:
        st.session_state.audience = st.selectbox(
            "Audience",
            ["Business Professional", "Data Scientist"],
            index=0 if st.session_state.audience == "Business Professional" else 1
        )

st.markdown('<div class="control-row">', unsafe_allow_html=True)
render_controls_row()
st.markdown('</div>', unsafe_allow_html=True)

# Tabs
home_tab, ask_tab = st.tabs(["Home", "Ask"])

with home_tab:
    files = st.file_uploader(
        "Upload chart images",
        type=["png", "jpg", "jpeg", "webp", "bmp", "jfif"],
        accept_multiple_files=True
    )
    if files:
        st.session_state.uploads = decode_uploaded_files(files)

    analyze = st.button("🔍 Analyze Charts", type="primary")

    # ✅ Collapsible preview instead of dropdown
    if st.session_state.analysis_mode == "Cross Chart Analysis" and st.session_state.uploads:
        with st.expander("🖼️ Preview Charts", expanded=False):
            st.subheader("🖼️ Charts Preview")
            recs = st.session_state.uploads
            num_charts = len(recs)
            cols_per_row = min(4, num_charts)
            rows = (num_charts + cols_per_row - 1) // cols_per_row
            for i in range(rows):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    idx = i * cols_per_row + j
                    if idx < num_charts:
                        with cols[j]:
                            rec = recs[idx]
                            st.image(rec["img"], caption=rec["name"], use_container_width=True)

    if analyze:
        if not st.session_state.uploads:
            st.error("Please upload at least one chart to analyze.")
        else:
            model_name = st.session_state.model_name
            audience = st.session_state.audience
            output_style = st.session_state.output_style
            analysis_mode = st.session_state.analysis_mode
            summary_blocks = []

            if analysis_mode == "Single Chart Analysis":
                for rec in st.session_state.uploads:
                    st.markdown(f"### Chart — {rec['name']}")
                    col_chart, col_insight = st.columns([1, 2], gap="large")
                    with col_chart:
                        st.image(rec["img"], caption=rec["name"], use_container_width=True)
                    with col_insight:
                        with st.spinner(f"Analyzing {rec['name']} with {model_name}..."):
                            insight = generate_individual_insight_from_rec(
                                rec, audience, model_name, output_style
                            )
                        st.markdown(insight)
                        summary_blocks.append(f"{rec['name']}:\n{insight}")
            else:
                with st.spinner(f"Performing cross-chart analysis with {model_name}..."):
                    cross_insight = generate_cross_chart_insight(
                        st.session_state.uploads, audience, model_name, output_style
                    )
                st.subheader("Combined Cross-Chart Insights")
                st.markdown(cross_insight)
                summary_blocks.append(cross_insight)

            st.session_state.analysis_summary = "\n\n---\n\n".join(summary_blocks)
            st.success("✅ Analysis complete. Switch to the **Ask** tab to query the results.")

with ask_tab:
    st.header("❓ Ask a question about the charts")
    if not st.session_state.analysis_summary:
        st.info("No analysis found. Please analyze charts on the Home tab first.")
    else:
        user_input = st.chat_input("Type your question about the charts...")
        if user_input:
            prompt = (
                "Answer based only on the analysis below.\n\n"
                f"Context:\n{st.session_state.analysis_summary}\n\n"
                "Question: " + user_input
            )
            contents = [{"role": "user", "parts": [{"text": prompt}]}]
            with st.spinner(f"Getting answer from {st.session_state.model_name}..."):
                try:
                    res = client.models.generate_content(
                        model=st.session_state.model_name,
                        contents=contents
                    )
                    answer = (res.text or "").strip()
                except Exception as e:
                    st.error(f"API Error: {e}")
                    answer = ""
            if answer:
                st.session_state.conversation.append({"user": user_input, "assistant": answer})
        for msg in st.session_state.conversation:
            st.chat_message("user").markdown(msg["user"])
            st.chat_message("assistant").markdown(msg["assistant"])
        with st.expander("Analysis Summary", expanded=False):
            st.markdown(st.session_state.analysis_summary)

