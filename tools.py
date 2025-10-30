import os
import io
import base64
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional

import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from tools import *
from google import genai as google_genai           
from groq import Groq                              
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from tinydb import TinyDB, where

DB = TinyDB("analysis_history_db.json")
# =============================================================================
# Environment & clients
# =============================================================================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")

google_client: Optional[google_genai.Client] = google_genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
groq_client: Optional[Groq] = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _summarize_line(text: str, words: int = 10) -> str:
    """Take the first non-empty line and truncate to N words for display."""
    if not text:
        return ""
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if not line:
        return ""
    toks = line.split()
    short = " ".join(toks[:words])
    if len(toks) > words:
        short += "…"
    return short
def _clear_current_run():
    st.session_state.uploads = []
    st.session_state.analysis_summary = ""
    st.session_state.analysis_details = []
    st.session_state.combined_insight = ""
    st.session_state.analysis_done = False
    st.session_state.pdf_bytes = None
    st.session_state.latest_thumbs = []


def _make_history_title(payload: Dict[str, Any]) -> str:
    """Generate a human-readable title for a saved history entry."""
    mode = payload.get("analysis_mode", "Single Chart Analysis")
    if mode.startswith("Cross"):
        base = _summarize_line(payload.get("combined_insight", "")) or "Cross-chart summary"
        return f"Cross • {base}"
    details = payload.get("analysis_details", [])
    if details:
        first = details[0]
        name = first.get("name", "Chart")
        peek = _summarize_line(first.get("insight", ""), 8) or "Insights"
        return f"{name} • {peek}"
    base = _summarize_line(payload.get("analysis_summary", ""), 10) or "Single-chart summary"
    return f"Single • {base}"


def save_analysis(payload: Dict[str, Any]) -> None:
    analyses = DB.table("analyses")
    title = _make_history_title(payload)
    analyses.insert({"ts": _now_iso(), "title": title, **payload})


def load_analyses() -> List[Dict[str, Any]]:
    """Return history entries newest→oldest with safe defaults."""
    items = sorted(DB.table("analyses").all(), key=lambda d: d.get("ts", ""), reverse=True)
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


def guess_mime(name: str) -> str:
    nl = name.lower()
    if nl.endswith(".png"): return "image/png"
    if nl.endswith(".webp"): return "image/webp"
    if nl.endswith(".bmp"): return "image/bmp"
    if nl.endswith(".jpg") or nl.endswith(".jpeg"): return "image/jpeg"
    return "image/png"


def decode_uploaded_files(files) -> List[Dict[str, Any]]:
    """Read Streamlit uploaded files into [{name,data,img,b64,mime}] safe list."""
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



def _ensure_backend(model_name: str) -> str:
    """Return 'google' or 'groq'; raise helpful errors if not configured."""
    if model_name.startswith("gemini"):
        if not google_client:
            raise RuntimeError("GEMINI_API_KEY missing. Put it in .env")
        return "google"
    else:
        if not groq_client:
            raise RuntimeError("GROQ_API_KEY missing. Put it in .env")
        return "groq"


def _call_google_generate(model_name: str, parts: list) -> str:
    """Google GenAI: send multimodal parts (text + inline_data images)."""
    res = google_client.models.generate_content(
        model=model_name,
        contents=[{"role": "user", "parts": parts}]
    )
    return (getattr(res, "text", "") or "").strip()


def _call_groq_generate(model_name: str, parts: list) -> str:
    """
    Groq: build messages content supporting text & images via data URLs.
    Each item is {"type":"text","text":...} or {"type":"image_url","image_url":{"url":...}}
    """
    groq_content = []
    for p in parts:
        if "text" in p:
            groq_content.append({"type": "text", "text": p["text"]})
        elif "inline_data" in p:
            mime = p["inline_data"].get("mime_type", "image/png")
            b64  = p["inline_data"].get("data", "")
            groq_content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    resp = groq_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": groq_content if groq_content else ""}],
        temperature=0.2,
        max_tokens=1200,
    )
    return (resp.choices[0].message.content or "").strip()


def _generate_with_backend(model_name: str, parts: list) -> str:
    """Route generation to Google or Groq."""
    backend = _ensure_backend(model_name)
    return _call_google_generate(model_name, parts) if backend == "google" else _call_groq_generate(model_name, parts)


def generate_individual_insight_from_rec(rec, audience, model_name, output_style):
    """Generate simple, audience-specific insights for one chart."""
    if audience == "Business Professional":
        prompt = f"""
You are a business analyst explaining this chart to non-technical managers.
Avoid technical words like skewness or kurtosis.

Focus on:
1) Main takeaway – what the chart clearly shows.
2) Key patterns – rises, drops, or differences that matter.
3) Simple reason or meaning – what this could imply for business.
4) Next step – one or two practical actions.

Style: {"short bullets" if output_style.startswith("Structured") else "short clear sentences"}.
"""
    else:  # Data Scientist
        prompt = f"""
You are a data scientist writing concise technical observations.

Focus on:
1) Summary of trend or relationship.
2) Notable variations or anomalies.
3) Short notes on possible causes or data issues.
4) One next analytical step to verify or extend the result.

Keep it brief and factual.
Style: {"bullet points" if output_style.startswith("Structured") else "compact technical paragraph"}.
"""

    parts = [{"text": prompt}, {"inline_data": {"mime_type": rec["mime"], "data": rec["b64"]}}]
    try:
        return _generate_with_backend(model_name, parts) or "No insights generated."
    except Exception as e:
        return f"API Error: {e}"


def generate_cross_chart_insight(recs, audience, model_name, output_style):
    """Generate overall summary across several charts, tailored by audience."""
    if audience == "Business Professional":
        prompt = f"""
You are explaining the combined message from all charts to business leaders.

Focus on:
1) Overall story – what’s happening across all charts.
2) Key contrasts or changes – which areas lead or lag.
3) What this means for goals or performance.
4) Simple actions or decisions to consider.

Avoid stats terms; keep it straightforward.
Style: {"short bullets" if output_style.startswith("Structured") else "plain short paragraph"}.
"""
    else:  # Data Scientist
        prompt = f"""
You are a data scientist summarizing multiple related plots.

Focus on:
1) Common trends or contrasts across charts.
2) Patterns that might suggest causal or correlated effects.
3) Data quality or sampling issues worth checking.
4) Next analyses to confirm findings.

Keep the answer tight and technical.
Style: {"bullet list" if output_style.startswith("Structured") else "compact paragraph"}.
"""

    parts = [{"text": prompt}] + [
        {"inline_data": {"mime_type": r["mime"], "data": r["b64"]}} for r in recs
    ]
    try:
        return _generate_with_backend(model_name, parts) or "No insights generated."
    except Exception as e:
        return f"API Error: {e}"

def make_thumbnails(uploads: List[Dict[str, Any]], max_w=320) -> List[Dict[str, str]]:
    """Small PNG previews for the History expander."""
    thumbs = []
    for rec in uploads:
        img: Image.Image = rec["img"].copy()
        w, h = img.size
        if w > max_w:
            img = img.resize((max_w, int(h * (max_w / float(w)))))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        thumbs.append({"name": rec["name"], "b64": b64})
    return thumbs


def thumbnails_gallery(thumbnails: List[Dict[str, str]]):
    if not thumbnails:
        return
    cols = st.columns(min(4, max(1, len(thumbnails))))
    for i, th in enumerate(thumbnails):
        with cols[i % len(cols)]:
            st.image(f"data:image/png;base64,{th['b64']}", caption=th["name"], use_container_width=True)


def build_chat_markdown(convo: List[Dict[str, str]]) -> str:
    """Create a simple .md transcript for download."""
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
        lines.append("")
    return "\n".join(lines)


def build_pdf_bytes(uploads, summary_text) -> bytes:
    """
    Build a tidy PDF:
      • Scales each image to fit A4 content box (keeps aspect).
      • Lets long text wrap across pages (Paragraph).
      • Never clears UI state — caller stores result in session.
    """
    if not uploads or not summary_text:
        return b""

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body", parent=styles["Normal"], fontName="Helvetica",
        fontSize=10, leading=14, spaceAfter=8, allowWidowsOrphans=True, splitLongWords=True,
    )
    h2 = styles["Heading2"]

    # Page margins
    left = right = top = bottom = 0.75 * inch
    page_w, page_h = A4
    max_img_w = page_w - left - right
    max_img_h = page_h - top - bottom

    story = [
        Paragraph("📊 Gemini Chart Analysis Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body),
        Paragraph("Generated by: Chartify", body),
        Spacer(1, 18),
    ]

    # Images
    for rec in uploads:
        try:
            story.append(Paragraph(rec.get("name", "Chart"), h2))
            img_bytes = io.BytesIO(rec["data"])
            iw, ih = ImageReader(img_bytes).getSize()
            scale = min(max_img_w / float(iw), max_img_h / float(ih), 1.0)
            img_bytes.seek(0)
            story.append(RLImage(img_bytes, width=iw * scale, height=ih * scale))
            story.append(Spacer(1, 10))
        except Exception as e:
            story.append(Paragraph(f"<i>Image error: {e}</i>", body))
            story.append(Spacer(1, 6))

    story.append(PageBreak())

    # Analysis summary (convert newlines for Paragraph)
    story.append(Paragraph("Analysis Summary", h2))
    safe_html = (
        summary_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    )
    story.append(Paragraph(safe_html, body))

    # Build → return bytes
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp.name
    tmp.close()
    try:
        doc = SimpleDocTemplate(
            tmp_path, pagesize=A4,
            leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom,
            title="Gemini Chart Analysis Report", author="Chartify"
        )
        doc.build(story)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def blue_theme_css():
    st.markdown("""
    <style>
      /* ================================
         Pastel Palette (Blue • Peach • Rose)
         ================================ */
      :root{
        /* Core pastels */
        --blue:#6ea8fe;       --blue-700:#3f83f8;   --blue-100:#e7f0ff;
        --peach:#fec5bb;      --peach-700:#fb8f74;  --peach-100:#fff1ed;
        --rose:#ffd1e8;       --rose-700:#f38bb2;   --rose-100:#fff0f7;
        --mint:#c8f7dc;       --mint-700:#22c55e;   --mint-100:#edfff6;
        --lemon:#fde68a;      --lemon-700:#eab308;  --lemon-100:#fffbea;

        /* Defaults (primary = blue) */
        --primary:var(--blue);
        --primary-700:var(--blue-700);
        --primary-100:var(--blue-100);

        /* Text / Surfaces */
        --bg:#ffffff;
        --bg-soft:linear-gradient(180deg, #ffffff 0%, #fff7fb 40%, #f5fbff 100%); /* rose→blue whisper */
        --text:#0f172a; 
        --muted:#64748b;
        --card:#ffffff;

        /* Accents */
        --radius:14px;
        --shadow:0 8px 32px rgba(63,131,248,0.10);
        --ring:0 0 0 3px rgba(110,168,254,0.35);
        --border:#eae8f2;
      }

      /* ===== Layout / Typography ===== */
      .block-container{max-width:1100px !important;}
      body{ background: var(--bg-soft) !important; }
      h1,h2,h3,h4{ color:var(--primary-700) !important; }

      /* ===== Tabs ===== */
      [data-baseweb="tab-list"]{
        border-bottom:1px solid var(--border);
        background:linear-gradient(90deg, var(--rose-100), #ffffff 50%, var(--blue-100));
        border-radius:12px;
        padding:2px 6px;
      }
      [data-baseweb="tab"]{ color:var(--muted); font-weight:600; }
      [aria-selected="true"][data-baseweb="tab"]{
        color:var(--primary-700) !important;
        border-bottom:3px solid var(--primary) !important;
      }

      /* ===== Sidebar ===== */
      [data-testid="stSidebar"]{
        background:
          radial-gradient(1200px 400px at -20% -10%, var(--rose-100), transparent),
          radial-gradient(1200px 400px at 120% 0%, var(--blue-100), transparent),
          #ffffff;
        border-right:1px solid var(--border);
      }
      [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{
        color:var(--primary-700) !important;
      }

      /* ===== Cards / Expanders / Alerts ===== */
      [data-testid="stFileUploader"],
      [data-testid="stExpander"],
      .stAlert,
      .analysis-card{
        background:var(--card);
        border-radius:var(--radius);
        border:1px solid var(--border);
        box-shadow:var(--shadow);
      }
      [data-testid="stFileUploader"]{ padding:14px 16px; }
      [data-testid="stExpander"] summary{ 
        color:var(--primary-700); font-weight:600;
        background:linear-gradient(90deg, #fff, var(--peach-100));
        border-radius:12px;
        padding:6px 8px;
      }
      .analysis-card{ padding:16px 18px; margin-bottom:14px; }
      .stAlert{ border-color:var(--border); background:linear-gradient(180deg, #fff, var(--rose-100)); }
      .history-label{ font-weight:600; color:#0f172a; }
      .history-sub{ color:#64748b; font-size:.9rem; }
      img{ border-radius:10px; }

      /* ===== Form controls ===== */
      input[type="range"]{ accent-color:var(--primary); }
      input[type="checkbox"], input[type="radio"]{ accent-color:var(--primary); }
      .stSelectbox [data-baseweb="select"]{ border-radius:12px; }

      /* ===== Base Buttons (Primary = Blue) ===== */
      .stButton > button, .stDownloadButton > button{
        background:linear-gradient(180deg, var(--primary), var(--primary-700)) !important;
        color:#fff !important; border:none !important;
        border-radius:12px !important; box-shadow:var(--shadow) !important;
        transition:transform .04s ease-in-out, filter .15s ease, box-shadow .15s ease;
      }
      .stButton > button:hover, .stDownloadButton > button:hover{ filter:brightness(1.04); }
      .stButton > button:active, .stDownloadButton > button:active{ transform:translateY(1px); }
      .stButton > button:focus, .stDownloadButton > button:focus{ outline:none !important; box-shadow:var(--ring) !important; }

      /* ===== Pastel Button Variants (opt-in wrappers) =====
         Wrap a widget in <div class="btn-peach">...</div> / <div class="btn-rose">...</div>
         / <div class="btn-mint">...</div> / <div class="btn-lemon">...</div> / <div class="btn-neutral">...</div>
      */
      .btn-peach .stButton > button, .btn-peach .stDownloadButton > button{
        background:linear-gradient(180deg, var(--peach), var(--peach-700)) !important; color:#1f2937 !important;
      }
      .btn-rose .stButton > button, .btn-rose .stDownloadButton > button{
        background:linear-gradient(180deg, var(--rose), var(--rose-700)) !important; color:#3b1d2a !important;
      }
      .btn-mint .stButton > button, .btn-mint .stDownloadButton > button{
        background:linear-gradient(180deg, var(--mint), var(--mint-700)) !important; color:#064e3b !important;
      }
      .btn-lemon .stButton > button, .btn-lemon .stDownloadButton > button{
        background:linear-gradient(180deg, var(--lemon), var(--lemon-700)) !important; color:#111827 !important;
      }
      .btn-neutral .stButton > button, .btn-neutral .stDownloadButton > button{
        background:linear-gradient(180deg, #cbd5e1, #94a3b8) !important; color:#111827 !important;
      }

      /* ===== Outline & Ghost (pair with color wrappers) ===== */
      .btn-outline .stButton > button, .btn-outline .stDownloadButton > button{
        background:transparent !important; color:var(--primary-700) !important;
        border:2px solid var(--primary-700) !important;
      }
      .btn-outline.btn-peach .stButton > button, .btn-outline.btn-peach .stDownloadButton > button{
        color:var(--peach-700) !important; border-color:var(--peach-700) !important; background:#fff7f4 !important;
      }
      .btn-outline.btn-rose .stButton > button, .btn-outline.btn-rose .stDownloadButton > button{
        color:var(--rose-700) !important; border-color:var(--rose-700) !important; background:#fff5fb !important;
      }
      .btn-outline.btn-mint .stButton > button, .btn-outline.btn-mint .stDownloadButton > button{
        color:var(--mint-700) !important; border-color:var(--mint-700) !important; background:#f5fff9 !important;
      }
      .btn-outline.btn-lemon .stButton > button, .btn-outline.btn-lemon .stDownloadButton > button{
        color:var(--lemon-700) !important; border-color:var(--lemon-700) !important; background:#fffdf0 !important;
      }

      .btn-ghost .stButton > button, .btn-ghost .stDownloadButton > button{
        background:transparent !important; color:var(--text) !important;
        border:1px dashed #e9d7ff !important;
      }

      /* ===== Chips (for tiny badges in markdown) ===== */
      .chip{
        display:inline-block; padding:4px 10px; border-radius:999px; font-size:.85rem; font-weight:600;
        background:var(--primary-100); color:var(--primary-700); border:1px solid #dbeafe;
      }
      .chip.peach{  background:var(--peach-100); color:var(--peach-700); border-color:#ffdcd2; }
      .chip.rose{   background:var(--rose-100);  color:var(--rose-700);  border-color:#ffd9ec; }
      .chip.mint{   background:var(--mint-100);  color:var(--mint-700);  border-color:#d1fae5; }
      .chip.lemon{  background:var(--lemon-100); color:var(--lemon-700); border-color:#fde68a; }
    </style>
    """, unsafe_allow_html=True)


