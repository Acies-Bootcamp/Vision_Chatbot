# # import io, base64, json, os
# # from PIL import Image
# # import streamlit as st
# # from google import genai
# # from dotenv import load_dotenv

# # # -----------------------------
# # # SETUP
# # # -----------------------------
# # load_dotenv()  # Load .env file
# # API_KEY = os.getenv("GEMINI_API_KEY")

# # if not API_KEY:
# #     st.error("❌ Gemini API key not found. Please set GEMINI_API_KEY in your .env file.")
# #     st.stop()

# # client = genai.Client(api_key=API_KEY)

# # # Streamlit Page Settings
# # st.set_page_config(page_title="📊 Gemini Chart Analyzer Pro", page_icon="📈", layout="wide")
# # st.title("📊 Gemini Chart Analyzer Pro")
# # st.caption("Analyze chart images → structured JSON insights using **Gemini 2.0 Models** ⚡")

# # # -----------------------------
# # # SIDEBAR CONTROLS
# # # -----------------------------
# # st.sidebar.header("⚙️ Settings")
# # MODEL_NAME = st.sidebar.selectbox(
# #     "Choose Model",
# #     ["gemini-2.0-flash", "gemini-1.5-pro"],
# #     index=0
# # )
# # st.sidebar.markdown("💡 **Tip:** Flash = Fast, Pro = More Accurate")

# # # Prompt controls
# # default_prompt = (
# #     "You are analyzing chart images (bar/line/pie/scatter). "
# #     "For EACH image:\n"
# #     "1️⃣ Identify axes (labels, units)\n"
# #     "2️⃣ Summarize key trends\n"
# #     "3️⃣ Find extrema (max/min)\n"
# #     "4️⃣ Note anomalies\n"
# #     "5️⃣ Give 3 concise insights\n\n"
# #     "Return JSON FIRST as list of objects:\n"
# #     "[{\"image\":\"<filename>\",\"axes\":{},\"summary\":\"\",\"insights\":[]}]"
# #     "\nThen add line '---' and a short Markdown comparison."
# # )

# # user_prompt = st.text_area("🧠 Prompt (Editable)", value=default_prompt, height=220)
# # if st.button("🔁 Reset Prompt"):
# #     st.session_state.prompt = default_prompt

# # # -----------------------------
# # # FILE UPLOAD
# # # -----------------------------
# # files = st.file_uploader(
# #     "📁 Upload chart images",
# #     type=["png", "jpg", "jpeg", "webp"],
# #     accept_multiple_files=True
# # )

# # # Helper to convert PIL to base64
# # def pil_to_b64(img: Image.Image) -> str:
# #     buf = io.BytesIO()
# #     img.save(buf, format="PNG")
# #     return base64.b64encode(buf.getvalue()).decode("utf-8")

# # # -----------------------------
# # # RUN ANALYSIS
# # # -----------------------------
# # if files and st.button("🚀 Analyze with Gemini"):
# #     st.toast("Uploading and analyzing images...", icon="🪄")
# #     previews = []
# #     parts = [{"role": "user", "parts": [{"text": user_prompt}]}]

# #     for f in files:
# #         data = f.read()
# #         img = Image.open(io.BytesIO(data)).convert("RGB")
# #         previews.append((f.name, img))
# #         b64 = pil_to_b64(img)
# #         parts[0]["parts"].append({
# #             "inline_data": {"mime_type": "image/png", "data": b64}
# #         })

# #     with st.expander("👀 Image Previews", expanded=True):
# #         cols = st.columns(min(3, len(previews)))
# #         for i, (name, img) in enumerate(previews):
# #             cols[i % len(cols)].image(img, caption=name, use_container_width=True)

# #     with st.spinner(f"Analyzing charts using {MODEL_NAME}..."):
# #         try:
# #             result = client.models.generate_content(
# #                 model=MODEL_NAME,
# #                 contents=parts
# #             )
# #             output_text = result.text
# #         except Exception as e:
# #             st.error(f"⚠️ API Error: {e}")
# #             st.stop()

# #     st.success("✅ Analysis complete!")

# #     # -----------------------------
# #     # DISPLAY RAW OUTPUT
# #     # -----------------------------
# #     with st.expander("🧾 Raw Model Output"):
# #         st.write(output_text)

# #     # -----------------------------
# #     # PARSE JSON SECTION
# #     # -----------------------------
# #     json_block, comparison = None, None
# #     if "---" in output_text:
# #         json_block, comparison = output_text.split("---", 1)
# #     else:
# #         start, end = output_text.find("["), output_text.rfind("]")
# #         if start != -1 and end != -1:
# #             json_block = output_text[start:end+1]

# #     parsed = None
# #     if json_block:
# #         try:
# #             parsed = json.loads(json_block)
# #         except Exception:
# #             st.warning("⚠️ Could not parse JSON. Check output format.")
# #             parsed = None

# #     # -----------------------------
# #     # DISPLAY INSIGHTS
# #     # -----------------------------
# #     if parsed:
# #         st.subheader("📊 Parsed Insights (Interactive)")
# #         for entry in parsed:
# #             with st.expander(f"📈 {entry.get('image', 'Unnamed Chart')}", expanded=False):
# #                 st.markdown(f"**Summary:** {entry.get('summary', 'N/A')}")
# #                 st.markdown("**Axes:**")
# #                 st.json(entry.get("axes", {}))
# #                 st.markdown("**🔍 Key Insights:**")
# #                 for i, ins in enumerate(entry.get("insights", []), start=1):
# #                     st.markdown(f"➡️ {i}. {ins}")

# #         # Download option
# #         json_str = json.dumps(parsed, indent=2)
# #         st.download_button(
# #             "💾 Download Insights JSON",
# #             data=json_str,
# #             file_name="chart_insights.json",
# #             mime="application/json"
# #         )
# #     else:
# #         st.info("ℹ️ Couldn’t extract valid JSON insights.")

# #     # -----------------------------
# #     # COMPARISON SECTION
# #     # -----------------------------
# #     if comparison:
# #         st.subheader("📊 Cross-Chart Comparison")
# #         st.markdown(comparison.strip())
# # else:
# #     st.info("📤 Upload one or more chart images and click **Analyze with Gemini**.")

# import io, base64, json, os
# from PIL import Image
# import streamlit as st
# from google import genai
# from dotenv import load_dotenv

# # -----------------------------
# # SETUP
# # -----------------------------
# load_dotenv()
# API_KEY = os.getenv("GEMINI_API_KEY")

# if not API_KEY:
#     st.error("❌ Gemini API key not found. Please set GEMINI_API_KEY in your .env file.")
#     st.stop()

# client = genai.Client(api_key=API_KEY)

# # -----------------------------
# # PAGE CONFIG
# # -----------------------------
# st.set_page_config(page_title="📊 Gemini Chart Analyzer Pro", page_icon="📈", layout="wide")
# st.title("📊 Gemini Chart Analyzer Pro")
# st.caption("Analyze chart images → structured JSON insights using **Gemini 2.0 Models** ⚡")

# # -----------------------------
# # SIDEBAR SETTINGS
# # -----------------------------
# st.sidebar.header("⚙️ Settings")

# # Theme toggle
# theme = st.sidebar.radio("🎨 Select Theme", ["Light", "Dark"], index=0)
# if theme == "Dark":
#     st.markdown(
#         """
#         <style>
#         body, .stApp { background-color: #0e1117; color: #FAFAFA; }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )

# # Model selector
# MODEL_NAME = st.sidebar.selectbox(
#     "🤖 Choose Gemini Model",
#     ["gemini-2.0-flash", "gemini-1.5-pro"],
#     index=0
# )
# st.sidebar.markdown("💡 *Flash = Fast | Pro = More Accurate*")

# # Tone selector
# tone = st.sidebar.selectbox(
#     "🗣️ Insight Tone",
#     ["Professional", "Analytical", "Casual"],
#     index=0
# )
# st.sidebar.markdown(
#     {
#         "Professional": "✅ Clear and formal — ideal for business use.",
#         "Analytical": "📈 Deep and data-driven — perfect for insights and trends.",
#         "Casual": "💬 Friendly and simplified — good for general audiences."
#     }[tone]
# )

# # -----------------------------
# # HIDDEN PROMPT (INTERNAL USE)
# # -----------------------------
# base_prompt = (
#     "You are analyzing chart images (bar, line, pie, scatter). For EACH image:\n"
#     "1. Identify axes (labels, units)\n"
#     "2. Summarize key trends\n"
#     "3. Find extrema (max/min)\n"
#     "4. Note anomalies\n"
#     "5. Provide 3 concise insights\n\n"
#     "Return JSON FIRST as a list of objects:\n"
#     "[{\"image\":\"<filename>\",\"axes\":{},\"summary\":\"\",\"insights\":[]}]"
#     "\nThen add line '---' and a short Markdown comparison summary."
# )

# tone_instructions = {
#     "Professional": "Use a formal, concise tone suitable for executive dashboards.",
#     "Analytical": "Use a technical tone focusing on trends, anomalies, and numeric reasoning.",
#     "Casual": "Use a friendly, conversational tone as if explaining to a non-technical person."
# }
# final_prompt = f"{base_prompt}\nTone: {tone_instructions[tone]}"

# # -----------------------------
# # FILE UPLOAD
# # -----------------------------
# files = st.file_uploader(
#     "📁 Upload chart images",
#     type=["png", "jpg", "jpeg", "webp"],
#     accept_multiple_files=True
# )

# # Helper: Convert PIL → base64
# def pil_to_b64(img: Image.Image) -> str:
#     buf = io.BytesIO()
#     img.save(buf, format="PNG")
#     return base64.b64encode(buf.getvalue()).decode("utf-8")

# # -----------------------------
# # RUN ANALYSIS
# # -----------------------------
# if files and st.button("🚀 Analyze with Gemini"):
#     st.toast("🪄 Uploading and analyzing charts...", icon="🔍")
#     previews = []
#     parts = [{"role": "user", "parts": [{"text": final_prompt}]}]

#     for f in files:
#         data = f.read()
#         img = Image.open(io.BytesIO(data)).convert("RGB")
#         previews.append((f.name, img))
#         b64 = pil_to_b64(img)
#         parts[0]["parts"].append({
#             "inline_data": {"mime_type": "image/png", "data": b64}
#         })

#     with st.expander("👀 Chart Previews", expanded=True):
#         cols = st.columns(min(3, len(previews)))
#         for i, (name, img) in enumerate(previews):
#             cols[i % len(cols)].image(img, caption=name, use_container_width=True)

#     with st.spinner(f"Analyzing with {MODEL_NAME} ({tone} tone)..."):
#         try:
#             result = client.models.generate_content(
#                 model=MODEL_NAME,
#                 contents=parts
#             )
#             output_text = result.text
#         except Exception as e:
#             st.error(f"⚠️ API Error: {e}")
#             st.stop()

#     st.success("✅ Analysis complete!")

#     # -----------------------------
#     # RAW MODEL OUTPUT
#     # -----------------------------
#     with st.expander("🧾 Raw Model Output"):
#         st.write(output_text)

#     # -----------------------------
#     # PARSE JSON
#     # -----------------------------
#     json_block, comparison = None, None
#     if "---" in output_text:
#         json_block, comparison = output_text.split("---", 1)
#     else:
#         start, end = output_text.find("["), output_text.rfind("]")
#         if start != -1 and end != -1:
#             json_block = output_text[start:end+1]

#     parsed = None
#     if json_block:
#         try:
#             parsed = json.loads(json_block)
#         except Exception:
#             st.warning("⚠️ Could not parse JSON. Check output format.")
#             parsed = None

#     # -----------------------------
#     # SHOW INSIGHTS
#     # -----------------------------
#     if parsed:
#         st.subheader("📊 Parsed Insights")
#         for entry in parsed:
#             with st.expander(f"📈 {entry.get('image', 'Unnamed Chart')}", expanded=False):
#                 st.markdown(f"**Summary:** {entry.get('summary', 'N/A')}")
#                 st.markdown("**Axes:**")
#                 st.json(entry.get("axes", {}))
#                 st.markdown("**🔍 Key Insights:**")
#                 for i, ins in enumerate(entry.get("insights", []), start=1):
#                     st.markdown(f"➡️ {i}. {ins}")

#         # Download JSON
#         json_str = json.dumps(parsed, indent=2)
#         st.download_button(
#             "💾 Download Insights as JSON",
#             data=json_str,
#             file_name="chart_insights.json",
#             mime="application/json"
#         )
#     else:
#         st.info("ℹ️ Couldn’t extract valid JSON insights.")

#     # -----------------------------
#     # COMPARISON
#     # -----------------------------
#     if comparison:
#         st.subheader("📈 Cross-Chart Comparison")
#         st.markdown(comparison.strip())

# else:
#     st.info("📤 Upload one or more chart images and click **Analyze with Gemini**.")

import io, base64, json, os
from PIL import Image
import streamlit as st
from google import genai
from dotenv import load_dotenv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image as RLImage, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# -----------------------------
# LOAD API KEY
# -----------------------------
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("❌ Gemini API key not found. Please set GEMINI_API_KEY in your .env file.")
    st.stop()

client = genai.Client(api_key=API_KEY)

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="📊 Gemini Chart Analyzer Pro", page_icon="📈", layout="wide")
st.title("📊 Gemini Chart Analyzer Pro")
st.caption("Analyze chart images → structured insights & export as PDF using Gemini models ⚡")

# -----------------------------
# SIDEBAR SETTINGS
# -----------------------------
st.sidebar.header("⚙️ Settings")

theme = st.sidebar.radio("🎨 Select Theme", ["Light", "Dark"], index=0)
if theme == "Dark":
    background_color = "#0E1117"
    text_color = "#FAFAFA"
else:
    background_color = "#FFFFFF"
    text_color = "#000000"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {background_color};
        color: {text_color};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Model selector (only valid models)
MODEL_NAME = st.sidebar.selectbox(
    "🤖 Choose Gemini Model",
    ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
    index=0
)

tone = st.sidebar.selectbox("🗣️ Insight Tone", ["Professional", "Analytical", "Casual"], index=0)

# -----------------------------
# HIDDEN PROMPT
# -----------------------------
base_prompt = (
    "You are analyzing chart images (bar, line, pie, scatter). For each image:\n"
    "1. Identify axes (labels, units)\n"
    "2. Summarize key trends\n"
    "3. Find extrema and anomalies\n"
    "4. Provide 3 concise insights\n\n"
    "After analyzing all charts, find relationships or correlations between them "
    "(e.g., trends that match or oppose) and write a unified overall summary.\n\n"
    "Return JSON format as:\n"
    "[{{'image':'<filename>', 'summary':'', 'insights':[]}}]\n"
    "---\n"
    "Then write 'Relationships & Overall Summary' in Markdown."
)

tone_instructions = {
    "Professional": "Use a formal tone suitable for executive dashboards.",
    "Analytical": "Use a technical tone focusing on data-driven insights.",
    "Casual": "Use a friendly, simple tone like explaining to a non-expert."
}
final_prompt = f"{base_prompt}\nTone: {tone_instructions[tone]}"

# -----------------------------
# FILE UPLOAD
# -----------------------------
files = st.file_uploader(
    "📁 Upload chart images",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True
)

def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# -----------------------------
# ANALYZE BUTTON
# -----------------------------
if files and st.button("🚀 Analyze Charts"):
    st.toast(f"🧠 Analyzing charts using {MODEL_NAME}...", icon="📊")
    previews = []
    parts = [{"role": "user", "parts": [{"text": final_prompt}]}]

    for f in files:
        data = f.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        previews.append((f.name, img))
        b64 = pil_to_b64(img)
        parts[0]["parts"].append({
            "inline_data": {"mime_type": "image/png", "data": b64}
        })

    with st.expander("👀 Chart Previews", expanded=True):
        cols = st.columns(min(3, len(previews)))
        for i, (name, img) in enumerate(previews):
            cols[i % len(cols)].image(img, caption=name, use_container_width=True)

    with st.spinner(f"Generating insights with {MODEL_NAME}..."):
        try:
            result = client.models.generate_content(model=MODEL_NAME, contents=parts)
            output_text = result.text
        except Exception as e:
            st.error(f"⚠️ API Error: {e}")
            st.stop()

    st.success("✅ Analysis complete!")

    # -----------------------------
    # PARSE OUTPUT
    # -----------------------------
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
            parsed = None
            st.warning("⚠️ Could not parse JSON properly.")

    # -----------------------------
    # DISPLAY RESULTS
    # -----------------------------
    if parsed:
        st.subheader("📊 Chart Insights")
        for entry in parsed:
            with st.expander(f"📈 {entry.get('image', 'Chart')}", expanded=False):
                st.markdown(f"**Summary:** {entry.get('summary', 'N/A')}")
                st.markdown("**Key Insights:**")
                for i, ins in enumerate(entry.get('insights', []), start=1):
                    st.markdown(f"➡️ {i}. {ins}")

        if comparison:
            st.subheader("🔗 Relationships & Overall Summary")
            st.markdown(comparison.strip())

        # -----------------------------
        # PDF EXPORT
        # -----------------------------
        pdf_buf = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buf, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Styles
        style_header = ParagraphStyle(name='Header', fontSize=18, textColor=text_color, leading=22, spaceAfter=14)
        style_sub = ParagraphStyle(name='SubHeader', fontSize=13, textColor=text_color, spaceAfter=8)
        style_text = ParagraphStyle(name='Text', fontSize=10, textColor=text_color, leading=14)

        today = datetime.now().strftime("%B %d, %Y")

        # Add Logo if available
        logo_path = "https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.linkedin.com%2Fcompany%2Facies-global&psig=AOvVaw28RnYg7M_IaxuxA137F-kO&ust=1761825204400000&source=images&cd=vfe&opi=89978449&ved=0CBUQjRxqFwoTCLjGzL2syZADFQAAAAAdAAAAABAE"
        if os.path.exists(logo_path):
            story.append(RLImage(logo_path, width=2.5 * inch, height=1 * inch))
        story.append(Paragraph("📊 Gemini Chart Analyzer Report", style_header))
        story.append(Paragraph(f"<b>Generated by:</b> Srimukhi Pulluri", style_text))
        story.append(Paragraph(f"<b>Organization:</b> Acies Global", style_text))
        story.append(Paragraph(f"<b>Date:</b> {today}", style_text))
        story.append(Spacer(1, 12))

        # Add chart summaries
        for (fname, img), entry in zip(previews, parsed):
            img_path = io.BytesIO()
            img.save(img_path, format="PNG")
            img_path.seek(0)

            story.append(Paragraph(f"<b>{fname}</b>", style_sub))
            story.append(RLImage(img_path, width=5.5 * inch, height=3 * inch))
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Summary:</b> {entry.get('summary', '')}", style_text))
            for i, ins in enumerate(entry.get("insights", []), start=1):
                story.append(Paragraph(f"➡️ {i}. {ins}", style_text))
            story.append(Spacer(1, 10))

        if comparison:
            story.append(Paragraph("<b>🔗 Relationships & Overall Summary</b>", style_sub))
            story.append(Paragraph(comparison.strip(), style_text))

        story.append(Spacer(1, 20))
        footer_text = f"Report generated by Gemini Chart Analyzer | © {datetime.now().year} Acies Global"
        story.append(Paragraph(footer_text, ParagraphStyle(name="Footer", fontSize=8, textColor=text_color, alignment=1)))

        doc.build(story)
        st.download_button(
            "💾 Download PDF Report",
            data=pdf_buf.getvalue(),
            file_name=f"Gemini_Chart_Insights_{today}.pdf",
            mime="application/pdf"
        )

    else:
        st.info("⚠️ No structured insights were extracted.")
