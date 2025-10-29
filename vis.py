import os
import io
import base64
from typing import List, Tuple, Optional, Dict, Any

import streamlit as st
from dotenv import load_dotenv
from google import genai  # pip install google-genai

# =========================
# App Config
# =========================
st.set_page_config(page_title="Gemini Chart Analyzer", page_icon="📊", layout="wide")

# Session state defaults
def _init_state():
    st.session_state.setdefault("uploads", [])  # list of dicts: {name, data(bytes), img(PIL), b64(str)}
    st.session_state.setdefault("analysis_summary", "")
    st.session_state.setdefault("model_name", "gemini-2.0-flash")
    st.session_state.setdefault("level", "Business (concise)")
    st.session_state.setdefault("word_limit", 200)
    st.session_state.setdefault("output_style", "Structured (bulleted)")
    st.session_state.setdefault("conversation", [])
    st.session_state.setdefault("prompt_text", "")
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
# Controls row
# =========================
def render_controls_row():
    c1, c2, c3, c4 = st.columns([1.3, 1.3, 1.3, 1.0])
    with c1:
        st.session_state.model_name = st.selectbox(
            "Model",
            MODEL_CHOICES,
            index=(MODEL_CHOICES.index(st.session_state.model_name)
                   if st.session_state.model_name in MODEL_CHOICES else 0),
            help="Use flash for speed (free tier), pro for higher quality if available."
        )
    with c2:
        st.session_state.level = st.selectbox(
            "Tone",
            ["Business (concise)", "Scientific (detailed)"],
            index=0 if st.session_state.level.startswith("Business") else 1
        )
    with c3:
        st.session_state.word_limit = st.slider(
            "Word limit",
            min_value=80, max_value=600, value=st.session_state.word_limit, step=20
        )
    with c4:
        st.session_state.output_style = st.selectbox(
            "Output format",
            ["Structured (bulleted)", "Narrative (story)"],
            index=(0 if st.session_state.output_style.startswith("Structured") else 1)
        )

# =========================
# Prompt builder
# =========================
def build_prompt(level: str, word_limit: int, output_style: str) -> str:
    if level.startswith("Business"):
        audience = "Audience: business stakeholders; avoid jargon; crisp, decision-focused."
    else:
        audience = "Audience: technical stakeholders; be precise and analytical."
    if output_style == "Structured (bulleted)":
        head = f"You are analyzing chart images (bar/line/pie/scatter). {audience}\n"
        instr = (
            "For each chart, provide bullet points covering:\n"
            "- **Chart:** file name or title (if available)\n"
            "- **Axes:** x-axis label (unit) and y-axis label (unit)\n"
            "- **Data series:** names of series\n"
            "- **Summary:** key trends or changes\n"
            "- **Max:** highest value and where\n"
            "- **Min:** lowest value and where\n"
            "- **Anomalies:** any unusual data points or drops/spikes\n"
            "- **Insights:** actionable observations (3 bullet points)\n\n"
            "After all charts, include a section **Overall Summary:** with bullet points combining insights across charts.\n"
            f"Keep the output under {word_limit} words, in Markdown format."
        )
        return head + instr
    else:
        body = (
            f"You are a senior data storyteller. {audience}\n"
            "Write an insightful narrative based on the uploaded charts.\n\n"
            "Requirements:\n"
            "1) Start with a bold one-line headline capturing the key message.\n"
            f"2) Use 2–3 short paragraphs (<= {word_limit} words total) describing the changes and importance.\n"
            "3) Mention leading series, magnitudes, and any anomalies or reversals.\n"
            "4) End with three action-oriented bullet points.\n"
            "Write in Markdown (no JSON)."
        )
        return body

# =========================
# Image helpers
# =========================
from PIL import Image

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
        out.append({"name": f.name, "data": data, "img": img, "b64": b64})
    return out

# =========================
# Main App
# =========================
render_controls_row()
home_tab, ask_tab = st.tabs(["Home", "Ask"])

with home_tab:
    files = st.file_uploader(
        "Upload chart images",
        type=["png", "jpg", "jpeg", "webp", "bmp", "jfif"],
        accept_multiple_files=True
    )
    if files:
        st.session_state.uploads = decode_uploaded_files(files)
    if st.session_state.uploads:
        with st.expander("Preview Charts", expanded=True):
            cols = st.columns(min(4, len(st.session_state.uploads)))
            for i, rec in enumerate(st.session_state.uploads):
                cols[i % len(cols)].image(rec["img"], caption=rec["name"], use_container_width=True)

    auto_prompt = build_prompt(
        level=st.session_state.level,
        word_limit=st.session_state.word_limit,
        output_style=st.session_state.output_style
    )
    st.session_state.prompt_text = st.text_area(
        "Prompt (editable):",
        value=auto_prompt,
        height=200
    )
    analyze = st.button("🔍 Analyze Charts", type="primary")
    if analyze:
        if not st.session_state.uploads:
            st.warning("Please upload one or more chart images first.")
        else:
            contents = [{"role": "user", "parts": [{"text": st.session_state.prompt_text}]}]
            for rec in st.session_state.uploads:
                contents[0]["parts"].append({"inline_data": {"mime_type": "image/png", "data": rec["b64"]}})
            with st.spinner(f"Analyzing charts with {st.session_state.model_name}..."):
                try:
                    result = client.models.generate_content(
                        model=st.session_state.model_name,
                        contents=contents
                    )
                    output_text = result.text or ""
                except Exception as e:
                    st.error(f"API Error: {e}")
                    st.stop()
            st.session_state.analysis_summary = output_text[:4000]
            st.success("Analysis complete.")
            st.subheader("Analysis Result")
            st.markdown(output_text)

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
                    answer = res.text or ""
                except Exception as e:
                    st.error(f"API Error: {e}")
                    st.stop()
            st.session_state.conversation.append({"user": user_input, "assistant": answer})
        for msg in st.session_state.conversation:
            st.chat_message("user").markdown(msg["user"])
            st.chat_message("assistant").markdown(msg["assistant"])
        with st.expander("Analysis Summary", expanded=False):
            st.markdown(st.session_state.analysis_summary)
