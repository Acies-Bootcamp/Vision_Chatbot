
'''import io, base64, json
from PIL import Image
import streamlit as st
from google import genai   
import os
from dotenv import load_dotenv


load_dotenv()  # reads .env file
api_key = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash"               # free, fast, multimodal

# -----------------------------
# SETUP
# -----------------------------
client = genai.Client(api_key=api_key)

st.set_page_config(page_title="Gemini Chart Analyzer", page_icon="📊")
st.title("📊 Gemini Chart Analyzer")
st.caption("Upload multiple charts → structured JSON insights using Gemini 2.0")

files = st.file_uploader(
    "Upload chart images",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True
)

default_prompt = (
    "You are analyzing chart images (bar/line/pie/scatter). "
    "For EACH image:\n"
    "1) Identify axes (labels, units)\n"
    "2) Summarize key trends\n"
    "3) Find extrema (max/min)\n"
    "4) Note anomalies\n"
    "5) Give 3 concise insights\n\n"
    "Return JSON FIRST as list of objects:\n"
    "[{\"image\":\"<filename>\",\"axes\":{},\"summary\":\"\",\"insights\":[]}]"
    "\nThen add line '---' and a short Markdown comparison."
)
user_prompt = st.text_area("Prompt", value=default_prompt, height=200)

def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# -----------------------------
# RUN
# -----------------------------
if files and st.button("Analyze with Gemini"):
    previews = []
    parts = [{"role": "user", "parts": [{"text": user_prompt}]}]

    for f in files:
        data = f.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        previews.append((f.name, img))
        b64 = pil_to_b64(img)
        parts[0]["parts"].append({
            "inline_data": {"mime_type": "image/png", "data": b64}
        })

    with st.expander("Preview"):
        cols = st.columns(min(3, len(previews)))
        for i, (name, img) in enumerate(previews):
            cols[i % len(cols)].image(img, caption=name, use_container_width=True)

    with st.spinner(f"Analyzing with {MODEL_NAME}..."):
        try:
            result = client.models.generate_content(
                model=MODEL_NAME,
                contents=parts
            )
            output_text = result.text
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

    st.subheader("Raw Model Output")
    st.write(output_text)

    # --- Parse JSON if possible ---
    json_block, comparison = None, None
    if "---" in output_text:
        json_block, comparison = output_text.split("---", 1)
    else:
        start, end = output_text.find("["), output_text.rfind("]")
        if start != -1 and end != -1:
            json_block = output_text[start:end+1]

    parsed = None
    if json_block:
        try:
            parsed = json.loads(json_block)
        except Exception:
            pass

    if parsed:
        st.subheader("Parsed JSON")
        st.json(parsed)
    else:
        st.info("Couldn’t parse JSON; check raw output.")

    if comparison:
        st.subheader("Comparison")
        st.markdown(comparison.strip())
else:
    st.info("Upload images and click **Analyze with Gemini**.")'''

import io
import base64
import json
import os
from PIL import Image
import streamlit as st
from google import genai
from dotenv import load_dotenv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage

# -----------------------------
# SETUP
# -----------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash"

st.set_page_config(page_title="📈 Business Chart Analyzer", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .main-title {
        text-align: center;
        font-size: 36px;
        color: #2B4162;
        margin-bottom: 5px;
    }
    .subtitle {
        text-align: center;
        font-size: 18px;
        color: gray;
    }
    .stButton>button {
        background-color: #2B4162;
        color: white;
        border-radius: 10px;
        height: 3em;
        width: 100%;
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">📊 Gemini Business Chart Analyzer</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI-powered chart understanding for business insights</p>', unsafe_allow_html=True)

client = genai.Client(api_key=api_key)

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("⚙️ Settings")
analysis_mode = st.sidebar.selectbox(
    "Select Analysis Mode",
    ["Technical Insights", "Business Summary", "Executive Overview"]
)
st.sidebar.markdown("---")
st.sidebar.info("Upload multiple chart images to extract insights using Gemini 2.0.")

logo = st.sidebar.file_uploader("Upload your logo (optional)", type=["png", "jpg", "jpeg"])

# -----------------------------
# Prompts
# -----------------------------
prompts = {
    "Technical Insights": (
        "Analyze each chart for:\n"
        "1. Axes labels & units\n"
        "2. Key trends and outliers\n"
        "3. Statistical observations\n"
        "4. 3 concise data-driven insights\n"
        "Return output as structured JSON."
    ),
    "Business Summary": (
        "For each chart, summarize in a business-friendly tone:\n"
        "1. What the data implies for performance or revenue\n"
        "2. Growth or risk areas\n"
        "3. 3 strategic recommendations\n"
        "Return JSON with fields: image, summary, business_insights."
    ),
    "Executive Overview": (
        "Create a high-level executive summary:\n"
        "1. Overall story from all charts\n"
        "2. Market or operational implications\n"
        "3. Key takeaways in bullet form.\n"
        "Return Markdown summary."
    )
}

user_prompt = st.text_area("🧠 Custom Prompt (Optional)", value=prompts[analysis_mode], height=180)

# -----------------------------
# File Upload
# -----------------------------
files = st.file_uploader(
    "📂 Upload chart images",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True
)

# -----------------------------
# Helper Functions
# -----------------------------
def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def parse_output(output_text: str):
    json_block, summary = None, None
    if "---" in output_text:
        json_block, summary = output_text.split("---", 1)
    else:
        start, end = output_text.find("["), output_text.rfind("]")
        if start != -1 and end != -1:
            json_block = output_text[start:end+1]
    try:
        parsed = json.loads(json_block)
        return parsed, summary
    except Exception:
        return None, output_text

'''def generate_pdf(parsed, summary=None, logo_path=None):
    """Generate a PDF report and return as bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    if logo_path:
        elements.append(RLImage(logo_path, width=120, height=60))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("<b>📊 Gemini Business Chart Insights Report</b>", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # Add chart insights
    if parsed:
        for item in parsed:
            if isinstance(item, dict):
                elements.append(Paragraph(f"<b>Chart:</b> {item.get('image', 'Unnamed Chart')}", styles["Heading2"]))
                if "summary" in item:
                    elements.append(Paragraph(f"<b>Summary:</b> {item['summary']}", styles["Normal"]))
                if "insights" in item:
                    elements.append(Paragraph("<b>Insights:</b>", styles["Heading3"]))
                    for ins in item["insights"]:
                        elements.append(Paragraph(f"- {ins}", styles["Normal"]))
                if "business_insights" in item:
                    elements.append(Paragraph("<b>Business Insights:</b>", styles["Heading3"]))
                    for ins in item["business_insights"]:
                        elements.append(Paragraph(f"- {ins}", styles["Normal"]))
                elements.append(Spacer(1, 12))

    # Executive summary
    if summary:
        elements.append(Spacer(1, 24))
        elements.append(Paragraph("<b>Executive Summary</b>", styles["Heading2"]))
        elements.append(Paragraph(summary.strip(), styles["Normal"]))

    doc.build(elements)
    buf.seek(0)
    return buf'''

def generate_pdf(parsed, summary=None, logo_path=None):
    """Generate a visually styled PDF report with full analysis text."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=60)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SectionTitle", fontSize=14, leading=18, textColor=colors.HexColor("#2B4162"), spaceAfter=8))
    styles.add(ParagraphStyle(name="Body", fontSize=11, leading=15))

    elements = []

    # --- Header ---
    if logo_path:
        elements.append(RLImage(logo_path, width=100, height=50))
        elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>📊 Gemini Business Chart Insights Report</b>", styles["Title"]))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    elements.append(Spacer(1, 15))

    if parsed:
        for i, item in enumerate(parsed, start=1):
            elements.append(Paragraph(f"Chart {i}", styles["SectionTitle"]))

            # Handle dict or string gracefully
            if isinstance(item, dict):
                # Try different possible keys (Gemini sometimes varies output)
                for key, value in item.items():
                    if isinstance(value, (str, int, float)):
                        elements.append(Paragraph(f"<b>{key.title()}:</b> {value}", styles["Body"]))
                        elements.append(Spacer(1, 6))
                    elif isinstance(value, list):
                        elements.append(Paragraph(f"<b>{key.title()}:</b>", styles["Body"]))
                        for v in value:
                            elements.append(Paragraph(f"- {v}", styles["Body"]))
                        elements.append(Spacer(1, 6))
                    elif isinstance(value, dict):
                        elements.append(Paragraph(f"<b>{key.title()}:</b>", styles["Body"]))
                        for subk, subv in value.items():
                            elements.append(Paragraph(f"• {subk}: {subv}", styles["Body"]))
                        elements.append(Spacer(1, 6))
            else:
                elements.append(Paragraph(str(item), styles["Body"]))

            elements.append(Spacer(1, 12))
            elements.append(Paragraph("<hr width='100%' color='#ccc'/>", styles["Body"]))
            elements.append(Spacer(1, 10))

    # --- Executive Summary ---
    if summary:
        elements.append(Spacer(1, 24))
        elements.append(Paragraph("<b>Executive Summary</b>", styles["SectionTitle"]))
        elements.append(Paragraph(summary.strip(), styles["Body"]))

    doc.build(elements)
    buf.seek(0)
    return buf


# -----------------------------
# Run Analysis
# -----------------------------
if files and st.button("🔍 Analyze Charts"):
    previews = []
    parts = [{"role": "user", "parts": [{"text": user_prompt}]}]

    for f in files:
        data = f.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        previews.append((f.name, img))
        parts[0]["parts"].append({
            "inline_data": {"mime_type": "image/png", "data": pil_to_b64(img)}
        })

    st.subheader("📸 Uploaded Previews")
    cols = st.columns(min(3, len(previews)))
    for i, (name, img) in enumerate(previews):
        cols[i % len(cols)].image(img, caption=name, use_container_width=True)

    with st.spinner(f"🔮 Generating insights with {MODEL_NAME}..."):
        try:
            result = client.models.generate_content(model=MODEL_NAME, contents=parts)
            output_text = result.text
        except Exception as e:
            st.error(f"❌ API Error: {e}")
            st.stop()

    parsed, summary = parse_output(output_text)
    st.success("✅ Analysis Complete!")

    # --- Display Results ---
    st.subheader("🧾 Raw Model Output")
    with st.expander("View Full Text"):
        st.write(output_text)

    if parsed:
        st.subheader("🧠 Structured Insights")
        for item in parsed:
            if isinstance(item, dict):
                st.markdown(f"### 📈 {item.get('image', 'Chart')}")
                st.json(item)
            else:
                st.write("Unstructured item:", item)

        # --- Download JSON ---
        st.download_button(
            "💾 Download Insights JSON",
            json.dumps(parsed, indent=2),
            file_name=f"chart_insights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

        # --- Generate PDF Report ---
        logo_path = None
        if logo:
            logo_path = f"temp_logo.{logo.type.split('/')[-1]}"
            with open(logo_path, "wb") as f:
                f.write(logo.getbuffer())

        pdf_buffer = generate_pdf(parsed, summary, logo_path)
        st.download_button(
            "📄 Download Executive PDF Report",
            pdf_buffer,
            file_name=f"Gemini_Chart_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf"
        )

    else:
        st.warning("⚠️ Could not parse structured JSON. Check raw output above.")

    if summary:
        st.subheader("🗒️ Executive Summary")
        st.markdown(summary.strip())

else:
    st.info("👆 Upload chart images and click **Analyze Charts** to begin.")
