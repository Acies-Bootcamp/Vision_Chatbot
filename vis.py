# app.py — Minimal 3-tab app (Home, Ask, History) with hidden-preview history + chat download
import os
import io
import base64
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

# === LLM SDKs ===
from google import genai as google_genai   # pip install google-genai
from groq import Groq                      # pip install groq

# PDF (reportlab)
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

# ============== TinyDB (simple global history, no threads) =================
from tinydb import TinyDB
DB = TinyDB("analysis_history_db.json")

def _now_iso():
    return datetime.utcnow().isoformat()

def _summarize_line(text: str, words: int = 10) -> str:
    if not text:
        return ""
    # take first non-empty line
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if not line:
        return ""
    toks = line.split()
    short = " ".join(toks[:words])
    if len(toks) > words:
        short += "…"
    return short

def _make_history_title(payload: Dict[str, Any]) -> str:
    mode = payload.get("analysis_mode", "Single Chart Analysis")
    if mode.startswith("Cross"):
        base = _summarize_line(payload.get("combined_insight", "")) or "Cross-chart summary"
        return f"Cross • {base}"
    # Single: try first detail -> “<file>: <first few insight words>”
    details = payload.get("analysis_details", [])
    if details:
        first = details[0]
        name = first.get("name", "Chart")
        peek = _summarize_line(first.get("insight", ""), 8) or "Insights"
        return f"{name} • {peek}"
    # Fallback from summary
    base = _summarize_line(payload.get("analysis_summary", ""), 10) or "Single-chart summary"
    return f"Single • {base}"

def save_analysis(payload: Dict[str, Any]):
    analyses = DB.table("analyses")
    title = _make_history_title(payload)
    analyses.insert({"ts": _now_iso(), "title": title, **payload})

def load_analyses() -> List[Dict[str, Any]]:
    analyses = DB.table("analyses")
    items = analyses.all()
    items = sorted(items, key=lambda d: d.get("ts", ""), reverse=True)
    for it in items:
        it.setdefault("title", "")
        it.setdefault("analysis_mode", "Single Chart Analysis")
        it.setdefault("analysis_summary", "")
        it.setdefault("analysis_details", [])
        it.setdefault("combined_insight", "")
        it.setdefault("thumbnails", [])
    return items

def load_latest_analysis() -> Dict[str, Any]:
    items = load_analyses()
    return items[0] if items else {}

# =========================
# App Config
# =========================
st.set_page_config(page_title="Gemini Chart Analyzer", page_icon="📊", layout="wide")
st.title("📊 Chartify")

# --- Blue Light UI (drop-in) ---
def blue_theme_css():
    st.markdown("""
    <style>
      :root{
        --primary:#1e88e5; --primary-700:#1976d2; --primary-100:#e3f2fd;
        --bg:#ffffff; --bg-soft:#f5f9ff; --text:#0f172a; --muted:#64748b;
        --card:#ffffff; --shadow:0 6px 24px rgba(30,136,229,0.08); --radius:14px;
      }
      .block-container{max-width: 1100px !important;}
      body { background: linear-gradient(180deg, var(--bg) 0%, var(--bg-soft) 100%) !important; }
      h1,h2,h3,h4 { color: var(--primary-700) !important; }
      [data-baseweb="tab-list"]{ border-bottom: 1px solid #e6eefc; }
      [data-baseweb="tab"]{ color: var(--muted); font-weight: 600; }
      [aria-selected="true"][data-baseweb="tab"]{ color: var(--primary-700) !important; border-bottom: 3px solid var(--primary) !important; }
      [data-testid="stSidebar"]{
        background: linear-gradient(180deg, var(--primary-100) 0%, #ffffff 70%);
        border-right: 1px solid #e6eefc;
      }
      [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{
        color: var(--primary-700) !important;
      }
      .stButton > button, .stDownloadButton > button{
        background: var(--primary) !important; color: white !important; border: none !important;
        border-radius: var(--radius) !important; box-shadow: var(--shadow) !important;
        transition: transform .03s ease-in-out, filter .15s ease;
      }
      .stButton > button:hover, .stDownloadButton > button:hover{ filter: brightness(1.05); }
      .stButton > button:active, .stDownloadButton > button:active{ transform: translateY(1px); }
      [data-testid="stFileUploader"]{
        background: var(--card); padding: 14px 16px; border-radius: var(--radius);
        box-shadow: var(--shadow); border: 1px solid #e6eefc;
      }
      [data-testid="stExpander"]{
        background: var(--card); border-radius: var(--radius);
        border: 1px solid #e6eefc; box-shadow: var(--shadow);
      }
      [data-testid="stExpander"] summary{ color: var(--primary-700); font-weight: 600; }
      .stAlert{ border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid #e6eefc; }
      .analysis-card{
        background: var(--card); padding: 16px 18px; border-radius: var(--radius);
        border: 1px solid #e6eefc; box-shadow: var(--shadow); margin-bottom: 14px;
      }
      .history-label{
        font-weight: 600; color: #0f172a;
      }
      .history-sub{ color: #64748b; font-size: 0.9rem; }
      img{ border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

blue_theme_css()

# =========================
# Session State Defaults
# =========================
def _init_state():
    st.session_state.setdefault("uploads", [])                 # [{name, data, img, b64, mime}]
    st.session_state.setdefault("analysis_summary", "")
    st.session_state.setdefault("analysis_details", [])        # [{name, insight}]
    st.session_state.setdefault("combined_insight", "")
    st.session_state.setdefault("analysis_done", False)
    st.session_state.setdefault("pdf_bytes", None)
    st.session_state.setdefault("latest_thumbs", [])

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

# =========================
# Env & Clients
# =========================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")

google_client: Optional[google_genai.Client] = None
groq_client: Optional[Groq] = None

if GEMINI_API_KEY:
    google_client = google_genai.Client(api_key=GEMINI_API_KEY)
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# Available models (Groq vision model updated to a supported one)
MODEL_CHOICES = [
    "gemini-2.0-flash",                         # Google GenAI (vision via inline_data)
    "meta-llama/llama-4-scout-17b-16e-instruct" # Groq multimodal (text+image)
]

# =========================
# Helpers
# =========================
def guess_mime(name: str) -> str:
    nl = name.lower()
    if nl.endswith(".png"): return "image/png"
    if nl.endswith(".webp"): return "image/webp"
    if nl.endswith(".bmp"): return "image/bmp"
    if nl.endswith(".jpg") or nl.endswith(".jpeg"): return "image/jpeg"
    return "image/png"

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

def _clear_current_run():
    st.session_state.uploads = []
    st.session_state.analysis_summary = ""
    st.session_state.analysis_details = []
    st.session_state.combined_insight = ""
    st.session_state.analysis_done = False
    st.session_state.pdf_bytes = None
    st.session_state.latest_thumbs = []

def _ensure_backend(model_name: str) -> str:
    """
    Return backend type: 'google' or 'groq'. Raise helpful errors if key/client missing.
    """
    if model_name.startswith("gemini"):
        if not google_client:
            raise RuntimeError("GEMINI_API_KEY missing. Set it in .env.")
        return "google"
    else:
        if not groq_client:
            raise RuntimeError("GROQ_API_KEY missing. Set it in .env.")
        return "groq"

def _call_google_generate(model_name: str, parts: list) -> str:
    res = google_client.models.generate_content(
        model=model_name,
        contents=[{"role": "user", "parts": parts}]
    )
    return (getattr(res, "text", "") or "").strip()

def _call_groq_generate(model_name: str, parts: list) -> str:
    """
    Build Groq-compatible 'messages[0].content' where each item is either:
      {"type":"text","text":"..."} OR {"type":"image_url","image_url":{"url":"data:..."}}
    """
    groq_content = []
    for p in parts:
        if "text" in p:
            groq_content.append({"type": "text", "text": p["text"]})
        elif "inline_data" in p:
            mime = p["inline_data"].get("mime_type", "image/png")
            b64  = p["inline_data"].get("data", "")
            data_url = f"data:{mime};base64,{b64}"
            groq_content.append({"type": "image_url", "image_url": {"url": data_url}})

    resp = groq_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": groq_content if groq_content else ""}],
        temperature=0.2,
        max_tokens=1200,
    )
    return (resp.choices[0].message.content or "").strip()

def _generate_with_backend(model_name: str, parts: list) -> str:
    backend = _ensure_backend(model_name)
    if backend == "google":
        return _call_google_generate(model_name, parts)
    else:
        if len(parts) == 1 and "text" in parts[0]:
            resp = groq_client.chat_completions.create(  # fallback in case of SDK differences
                model=model_name,
                messages=[{"role": "user", "content": parts[0]["text"]}],
                temperature=0.2,
                max_tokens=1200,
            ) if hasattr(groq_client, "chat_completions") else groq_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": parts[0]["text"]}],
                temperature=0.2,
                max_tokens=1200,
            )
            # Normalize
            choice = getattr(resp, "choices", [])[0]
            msg = getattr(choice, "message", None) or getattr(choice, "delta", None)
            content = (getattr(msg, "content", None) if msg else None) or getattr(choice, "text", None)
            return (content or "").strip()
        return _call_groq_generate(model_name, parts)

def generate_individual_insight_from_rec(rec, audience, model_name, output_style):
    tone_note = "business-friendly" if audience == "Business Professional" else "technically precise"
    prompt = f"""
You are a professional data analyst. Analyze the uploaded chart image and provide a structured, professional response.
Audience: {audience}.
Instructions:
1) Short overview.
2) Key findings & insights.
3) Tone: {tone_note}.
4) {"Use concise bullets." if output_style.startswith("Structured") else "Write a short narrative paragraph."}
"""
    parts = [{"text": prompt}, {"inline_data": {"mime_type": rec["mime"], "data": rec["b64"]}}]
    try:
        text = _generate_with_backend(model_name, parts)
        return text or "No insights generated."
    except Exception as e:
        return f"API Error: {e}"

def generate_cross_chart_insight(recs, audience, model_name, output_style):
    tone_note = "business-friendly" if audience == "Business Professional" else "technically precise"
    prompt = f"""
You are a professional data analyst. Analyze relationships and trends across all charts and provide a concise summary.
Audience: {audience}.
Instructions:
1) Overall trends across charts.
2) Comparisons/correlations/differences.
3) Tone: {tone_note}.
4) {"Use concise bullets." if output_style.startswith("Structured") else "Write a short narrative paragraph."}
"""
    parts = [{"text": prompt}]
    for rec in recs:
        parts.append({"inline_data": {"mime_type": rec["mime"], "data": rec["b64"]}})
    try:
        text = _generate_with_backend(model_name, parts)
        return text or "No insights generated."
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
    temp_paths, pdf_path = [], None
    try:
        max_width = 440
        for rec in uploads:
            story.append(Paragraph(f"<b>{rec['name']}</b>", styles["Heading2"]))
            img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img_tmp.close()
            temp_paths.append(img_tmp.name)
            rec["img"].save(img_tmp.name)
            story.append(RLImage(img_tmp.name, width=max_width))
            story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Analysis Summary:</b>", styles["Heading2"]))
        story.append(Paragraph(summary_text.replace("\n", "<br/>"), styles["Normal"]))
        pdf_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf"); pdf_path = pdf_tmp.name; pdf_tmp.close()
        doc = SimpleDocTemplate(pdf_path, pagesize=A4); doc.build(story)
        with open(pdf_path, "rb") as f:
            return f.read()
    finally:
        for p in temp_paths:
            try: os.unlink(p)
            except Exception: pass
        if pdf_path:
            try: os.unlink(pdf_path)
            except Exception: pass

def make_thumbnails(uploads: List[Dict[str, Any]], max_w=320) -> List[Dict[str, str]]:
    thumbs = []
    for rec in uploads:
        img: Image.Image = rec["img"].copy()
        w, h = img.size
        if w > max_w:
            new_h = int(h * (max_w / float(w)))
            img = img.resize((max_w, new_h))
        buf = io.BytesIO(); img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        thumbs.append({"name": rec["name"], "b64": b64})
    return thumbs

def thumbnails_gallery(thumbnails: List[Dict[str, str]]):
    if not thumbnails: return
    cols = st.columns(min(4, max(1, len(thumbnails))))
    for i, th in enumerate(thumbnails):
        with cols[i % len(cols)]:
            st.image(f"data:image/png;base64,{th['b64']}", caption=th["name"], use_container_width=True)

def build_chat_markdown(convo: List[Dict[str, str]]) -> str:
    """Return a markdown transcript of the Ask tab chat."""
    if not convo:
        return "# Chat History\n\n_No chat yet._\n"
    lines = ["# Chat History\n"]
    for i, m in enumerate(convo, 1):
        u = (m.get("user") or "").strip()
        a = (m.get("assistant") or "").strip()
        if u:
            lines.append(f"**You {i}:** {u}")
        if a:
            lines.append(f"**Assistant {i}:** {a}")
        lines.append("")  # blank line
    return "\n".join(lines)

# =========================
# SIDEBAR — Workspace & Export
# =========================
with st.sidebar:
    st.header("🛠️ Workspace")

    # Model selector
    st.session_state.model_name = st.selectbox(
        "Model provider & mode",
        MODEL_CHOICES,
        index=(MODEL_CHOICES.index(st.session_state.model_name)
               if st.session_state.model_name in MODEL_CHOICES else 0),
        help="Pick the engine used to analyze charts and answer follow-ups."
    )

    # Analysis type
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
        help="Choose concise bullets or a short narrative paragraph."
    )

    # Audience
    st.session_state.audience = st.selectbox(
        "Audience tone",
        ["Business Professional", "Data Scientist"],
        index=0 if st.session_state.audience == "Business Professional" else 1,
        help="This tunes wording and emphasis in the insights."
    )

    # Detect ANY dropdown change → clear the Home run (uploads + outputs)
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
                st.session_state.uploads,
                st.session_state.analysis_summary
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
        st.caption("No chat yet — ask a follow-up on the **Ask** tab to enable download.")

# =========================
# TABS — Home | Ask | History
# =========================t

home_tab, ask_tab, history_tab = st.tabs(["Home", "Chat Bot", "History"])

with home_tab:
    st.subheader("📥 Upload & Analyze")
    st.caption("Tip: For **Cross** analysis, upload multiple charts. For **Single**, you can still upload several; each gets its own insight.")

    files = st.file_uploader(
        "Drop chart images",
        type=["png", "jpg", "jpeg", "webp", "bmp", "jfif"],
        accept_multiple_files=True,
        help="Accepted: PNG, JPG, WEBP, BMP. Images only."
    )
    if files:
        decoded = decode_uploaded_files(files)
        if decoded:
            st.session_state.uploads = decoded

    analyze = st.button("🔍 Run Analysis", type="primary")

    # Cross: preview charts (hidden by default)
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
            model_name  = st.session_state.model_name
            audience    = st.session_state.audience
            output_style= st.session_state.output_style
            mode        = st.session_state.analysis_mode

            st.session_state.analysis_details = []
            st.session_state.combined_insight = ""
            summary_blocks = []

            if mode == "Single Chart Analysis":
                for rec in st.session_state.uploads:
                    with st.spinner(f"Analyzing {rec['name']}…"):
                        insight = generate_individual_insight_from_rec(rec, audience, model_name, output_style)
                    st.session_state.analysis_details.append({"name": rec["name"], "insight": insight})
                    summary_blocks.append(f"**{rec['name']}**\n\n{insight}")
            else:
                with st.spinner("Aggregating cross-chart insights…"):
                    combined = generate_cross_chart_insight(st.session_state.uploads, audience, model_name, output_style)
                st.session_state.combined_insight = combined
                summary_blocks.append(combined)

            st.session_state.analysis_summary = "\n\n---\n\n".join(summary_blocks)
            st.session_state.pdf_bytes = None
            st.session_state.analysis_done = True
            st.session_state.latest_thumbs = make_thumbnails(st.session_state.uploads)
            st.toast("✅ Analysis complete.", icon="✅")

            # Save to history (with thumbnails + auto title)
            save_analysis({
                "analysis_mode": st.session_state.analysis_mode,
                "analysis_summary": st.session_state.analysis_summary,
                "analysis_details": st.session_state.analysis_details,
                "combined_insight": st.session_state.combined_insight,
                "thumbnails": st.session_state.latest_thumbs
            })

    # Render CURRENT result (no history shown here)
    if st.session_state.analysis_done and st.session_state.analysis_summary and st.session_state.uploads:
        st.markdown("### 📈 Current Result")
        if st.session_state.analysis_mode == "Single Chart Analysis":
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

with ask_tab:
    st.header("❓ Follow-up Q&A")

    # hidden preview of latest analysis
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
            context = latest.get("analysis_summary", "")
            prompt = f"Answer based only on the analysis below.\n\n{context}\n\nQuestion: {user_input}"
            parts = [{"text": prompt}]  # Ask tab is text-only
            with st.spinner("Thinking…"):
                try:
                    answer = _generate_with_backend(st.session_state.model_name, parts)
                except Exception as e:
                    answer = f"API Error: {e}"
            st.session_state.conversation.append({"user": user_input, "assistant": answer})
            st.toast("💬 Answer added to chat.", icon="✅")
            st.rerun()

        # Chat history render (with empty-state message)
        if not st.session_state.conversation:
            st.info("No chat yet. Ask a question above.")
        else:
            for msg in st.session_state.conversation:
                if msg.get("user"):
                    st.chat_message("user").markdown(msg["user"])
                if msg.get("assistant"):
                    st.chat_message("assistant").markdown(msg["assistant"])

with history_tab:
    st.header("📚 Past Runs")
    items = load_analyses()
    if not items:
        st.info("No saved analyses yet.")
    else:
        for h in items:
            ts = h.get('ts','')[:19].replace('T',' ')
            title = h.get("title") or ("Single" if h.get('analysis_mode','').startswith('Single') else "Cross")
            label = f"{ts} — {title}"
            with st.expander(label, expanded=False):
                if h.get("thumbnails"):
                    thumbnails_gallery(h["thumbnails"])
                    st.markdown("---")
                st.markdown(h.get("analysis_summary",""))
