# # # # import io, base64, json, os
# # # # from PIL import Image
# # # # import streamlit as st
# # # # from google import genai
# # # # from dotenv import load_dotenv

# # # # # -----------------------------
# # # # # SETUP
# # # # # -----------------------------
# # # # load_dotenv()  # Load .env file
# # # # API_KEY = os.getenv("GEMINI_API_KEY")

# # # # if not API_KEY:
# # # #     st.error("❌ Gemini API key not found. Please set GEMINI_API_KEY in your .env file.")
# # # #     st.stop()

# # # # client = genai.Client(api_key=API_KEY)

# # # # # Streamlit Page Settings
# # # # st.set_page_config(page_title="📊 Gemini Chart Analyzer Pro", page_icon="📈", layout="wide")
# # # # st.title("📊 Gemini Chart Analyzer Pro")
# # # # st.caption("Analyze chart images → structured JSON insights using **Gemini 2.0 Models** ⚡")

# # # # # -----------------------------
# # # # # SIDEBAR CONTROLS
# # # # # -----------------------------
# # # # st.sidebar.header("⚙️ Settings")
# # # # MODEL_NAME = st.sidebar.selectbox(
# # # #     "Choose Model",
# # # #     ["gemini-2.0-flash", "gemini-1.5-pro"],
# # # #     index=0
# # # # )
# # # # st.sidebar.markdown("💡 **Tip:** Flash = Fast, Pro = More Accurate")

# # # # # Prompt controls
# # # # default_prompt = (
# # # #     "You are analyzing chart images (bar/line/pie/scatter). "
# # # #     "For EACH image:\n"
# # # #     "1️⃣ Identify axes (labels, units)\n"
# # # #     "2️⃣ Summarize key trends\n"
# # # #     "3️⃣ Find extrema (max/min)\n"
# # # #     "4️⃣ Note anomalies\n"
# # # #     "5️⃣ Give 3 concise insights\n\n"
# # # #     "Return JSON FIRST as list of objects:\n"
# # # #     "[{\"image\":\"<filename>\",\"axes\":{},\"summary\":\"\",\"insights\":[]}]"
# # # #     "\nThen add line '---' and a short Markdown comparison."
# # # # )

# # # # user_prompt = st.text_area("🧠 Prompt (Editable)", value=default_prompt, height=220)
# # # # if st.button("🔁 Reset Prompt"):
# # # #     st.session_state.prompt = default_prompt

# # # # # -----------------------------
# # # # # FILE UPLOAD
# # # # # -----------------------------
# # # # files = st.file_uploader(
# # # #     "📁 Upload chart images",
# # # #     type=["png", "jpg", "jpeg", "webp"],
# # # #     accept_multiple_files=True
# # # # )

# # # # # Helper to convert PIL to base64
# # # # def pil_to_b64(img: Image.Image) -> str:
# # # #     buf = io.BytesIO()
# # # #     img.save(buf, format="PNG")
# # # #     return base64.b64encode(buf.getvalue()).decode("utf-8")

# # # # # -----------------------------
# # # # # RUN ANALYSIS
# # # # # -----------------------------
# # # # if files and st.button("🚀 Analyze with Gemini"):
# # # #     st.toast("Uploading and analyzing images...", icon="🪄")
# # # #     previews = []
# # # #     parts = [{"role": "user", "parts": [{"text": user_prompt}]}]

# # # #     for f in files:
# # # #         data = f.read()
# # # #         img = Image.open(io.BytesIO(data)).convert("RGB")
# # # #         previews.append((f.name, img))
# # # #         b64 = pil_to_b64(img)
# # # #         parts[0]["parts"].append({
# # # #             "inline_data": {"mime_type": "image/png", "data": b64}
# # # #         })

# # # #     with st.expander("👀 Image Previews", expanded=True):
# # # #         cols = st.columns(min(3, len(previews)))
# # # #         for i, (name, img) in enumerate(previews):
# # # #             cols[i % len(cols)].image(img, caption=name, use_container_width=True)

# # # #     with st.spinner(f"Analyzing charts using {MODEL_NAME}..."):
# # # #         try:
# # # #             result = client.models.generate_content(
# # # #                 model=MODEL_NAME,
# # # #                 contents=parts
# # # #             )
# # # #             output_text = result.text
# # # #         except Exception as e:
# # # #             st.error(f"⚠️ API Error: {e}")
# # # #             st.stop()

# # # #     st.success("✅ Analysis complete!")

# # # #     # -----------------------------
# # # #     # DISPLAY RAW OUTPUT
# # # #     # -----------------------------
# # # #     with st.expander("🧾 Raw Model Output"):
# # # #         st.write(output_text)

# # # #     # -----------------------------
# # # #     # PARSE JSON SECTION
# # # #     # -----------------------------
# # # #     json_block, comparison = None, None
# # # #     if "---" in output_text:
# # # #         json_block, comparison = output_text.split("---", 1)
# # # #     else:
# # # #         start, end = output_text.find("["), output_text.rfind("]")
# # # #         if start != -1 and end != -1:
# # # #             json_block = output_text[start:end+1]

# # # #     parsed = None
# # # #     if json_block:
# # # #         try:
# # # #             parsed = json.loads(json_block)
# # # #         except Exception:
# # # #             st.warning("⚠️ Could not parse JSON. Check output format.")
# # # #             parsed = None

# # # #     # -----------------------------
# # # #     # DISPLAY INSIGHTS
# # # #     # -----------------------------
# # # #     if parsed:
# # # #         st.subheader("📊 Parsed Insights (Interactive)")
# # # #         for entry in parsed:
# # # #             with st.expander(f"📈 {entry.get('image', 'Unnamed Chart')}", expanded=False):
# # # #                 st.markdown(f"**Summary:** {entry.get('summary', 'N/A')}")
# # # #                 st.markdown("**Axes:**")
# # # #                 st.json(entry.get("axes", {}))
# # # #                 st.markdown("**🔍 Key Insights:**")
# # # #                 for i, ins in enumerate(entry.get("insights", []), start=1):
# # # #                     st.markdown(f"➡️ {i}. {ins}")

# # # #         # Download option
# # # #         json_str = json.dumps(parsed, indent=2)
# # # #         st.download_button(
# # # #             "💾 Download Insights JSON",
# # # #             data=json_str,
# # # #             file_name="chart_insights.json",
# # # #             mime="application/json"
# # # #         )
# # # #     else:
# # # #         st.info("ℹ️ Couldn’t extract valid JSON insights.")

# # # #     # -----------------------------
# # # #     # COMPARISON SECTION
# # # #     # -----------------------------
# # # #     if comparison:
# # # #         st.subheader("📊 Cross-Chart Comparison")
# # # #         st.markdown(comparison.strip())
# # # # else:
# # # #     st.info("📤 Upload one or more chart images and click **Analyze with Gemini**.")

# # # import io, base64, json, os
# # # from PIL import Image
# # # import streamlit as st
# # # from google import genai
# # # from dotenv import load_dotenv

# # # # -----------------------------
# # # # SETUP
# # # # -----------------------------
# # # load_dotenv()
# # # API_KEY = os.getenv("GEMINI_API_KEY")

# # # if not API_KEY:
# # #     st.error("❌ Gemini API key not found. Please set GEMINI_API_KEY in your .env file.")
# # #     st.stop()

# # # client = genai.Client(api_key=API_KEY)

# # # # -----------------------------
# # # # PAGE CONFIG
# # # # -----------------------------
# # # st.set_page_config(page_title="📊 Gemini Chart Analyzer Pro", page_icon="📈", layout="wide")
# # # st.title("📊 Gemini Chart Analyzer Pro")
# # # st.caption("Analyze chart images → structured JSON insights using **Gemini 2.0 Models** ⚡")

# # # # -----------------------------
# # # # SIDEBAR SETTINGS
# # # # -----------------------------
# # # st.sidebar.header("⚙️ Settings")

# # # # Theme toggle
# # # theme = st.sidebar.radio("🎨 Select Theme", ["Light", "Dark"], index=0)
# # # if theme == "Dark":
# # #     st.markdown(
# # #         """
# # #         <style>
# # #         body, .stApp { background-color: #0e1117; color: #FAFAFA; }
# # #         </style>
# # #         """,
# # #         unsafe_allow_html=True,
# # #     )

# # # # Model selector
# # # MODEL_NAME = st.sidebar.selectbox(
# # #     "🤖 Choose Gemini Model",
# # #     ["gemini-2.0-flash", "gemini-1.5-pro"],
# # #     index=0
# # # )
# # # st.sidebar.markdown("💡 *Flash = Fast | Pro = More Accurate*")

# # # # Tone selector
# # # tone = st.sidebar.selectbox(
# # #     "🗣️ Insight Tone",
# # #     ["Professional", "Analytical", "Casual"],
# # #     index=0
# # # )
# # # st.sidebar.markdown(
# # #     {
# # #         "Professional": "✅ Clear and formal — ideal for business use.",
# # #         "Analytical": "📈 Deep and data-driven — perfect for insights and trends.",
# # #         "Casual": "💬 Friendly and simplified — good for general audiences."
# # #     }[tone]
# # # )

# # # # -----------------------------
# # # # HIDDEN PROMPT (INTERNAL USE)
# # # # -----------------------------
# # # base_prompt = (
# # #     "You are analyzing chart images (bar, line, pie, scatter). For EACH image:\n"
# # #     "1. Identify axes (labels, units)\n"
# # #     "2. Summarize key trends\n"
# # #     "3. Find extrema (max/min)\n"
# # #     "4. Note anomalies\n"
# # #     "5. Provide 3 concise insights\n\n"
# # #     "Return JSON FIRST as a list of objects:\n"
# # #     "[{\"image\":\"<filename>\",\"axes\":{},\"summary\":\"\",\"insights\":[]}]"
# # #     "\nThen add line '---' and a short Markdown comparison summary."
# # # )

# # # tone_instructions = {
# # #     "Professional": "Use a formal, concise tone suitable for executive dashboards.",
# # #     "Analytical": "Use a technical tone focusing on trends, anomalies, and numeric reasoning.",
# # #     "Casual": "Use a friendly, conversational tone as if explaining to a non-technical person."
# # # }
# # # final_prompt = f"{base_prompt}\nTone: {tone_instructions[tone]}"

# # # # -----------------------------
# # # # FILE UPLOAD
# # # # -----------------------------
# # # files = st.file_uploader(
# # #     "📁 Upload chart images",
# # #     type=["png", "jpg", "jpeg", "webp"],
# # #     accept_multiple_files=True
# # # )

# # # # Helper: Convert PIL → base64
# # # def pil_to_b64(img: Image.Image) -> str:
# # #     buf = io.BytesIO()
# # #     img.save(buf, format="PNG")
# # #     return base64.b64encode(buf.getvalue()).decode("utf-8")

# # # # -----------------------------
# # # # RUN ANALYSIS
# # # # -----------------------------
# # # if files and st.button("🚀 Analyze with Gemini"):
# # #     st.toast("🪄 Uploading and analyzing charts...", icon="🔍")
# # #     previews = []
# # #     parts = [{"role": "user", "parts": [{"text": final_prompt}]}]

# # #     for f in files:
# # #         data = f.read()
# # #         img = Image.open(io.BytesIO(data)).convert("RGB")
# # #         previews.append((f.name, img))
# # #         b64 = pil_to_b64(img)
# # #         parts[0]["parts"].append({
# # #             "inline_data": {"mime_type": "image/png", "data": b64}
# # #         })

# # #     with st.expander("👀 Chart Previews", expanded=True):
# # #         cols = st.columns(min(3, len(previews)))
# # #         for i, (name, img) in enumerate(previews):
# # #             cols[i % len(cols)].image(img, caption=name, use_container_width=True)

# # #     with st.spinner(f"Analyzing with {MODEL_NAME} ({tone} tone)..."):
# # #         try:
# # #             result = client.models.generate_content(
# # #                 model=MODEL_NAME,
# # #                 contents=parts
# # #             )
# # #             output_text = result.text
# # #         except Exception as e:
# # #             st.error(f"⚠️ API Error: {e}")
# # #             st.stop()

# # #     st.success("✅ Analysis complete!")

# # #     # -----------------------------
# # #     # RAW MODEL OUTPUT
# # #     # -----------------------------
# # #     with st.expander("🧾 Raw Model Output"):
# # #         st.write(output_text)

# # #     # -----------------------------
# # #     # PARSE JSON
# # #     # -----------------------------
# # #     json_block, comparison = None, None
# # #     if "---" in output_text:
# # #         json_block, comparison = output_text.split("---", 1)
# # #     else:
# # #         start, end = output_text.find("["), output_text.rfind("]")
# # #         if start != -1 and end != -1:
# # #             json_block = output_text[start:end+1]

# # #     parsed = None
# # #     if json_block:
# # #         try:
# # #             parsed = json.loads(json_block)
# # #         except Exception:
# # #             st.warning("⚠️ Could not parse JSON. Check output format.")
# # #             parsed = None

# # #     # -----------------------------
# # #     # SHOW INSIGHTS
# # #     # -----------------------------
# # #     if parsed:
# # #         st.subheader("📊 Parsed Insights")
# # #         for entry in parsed:
# # #             with st.expander(f"📈 {entry.get('image', 'Unnamed Chart')}", expanded=False):
# # #                 st.markdown(f"**Summary:** {entry.get('summary', 'N/A')}")
# # #                 st.markdown("**Axes:**")
# # #                 st.json(entry.get("axes", {}))
# # #                 st.markdown("**🔍 Key Insights:**")
# # #                 for i, ins in enumerate(entry.get("insights", []), start=1):
# # #                     st.markdown(f"➡️ {i}. {ins}")

# # #         # Download JSON
# # #         json_str = json.dumps(parsed, indent=2)
# # #         st.download_button(
# # #             "💾 Download Insights as JSON",
# # #             data=json_str,
# # #             file_name="chart_insights.json",
# # #             mime="application/json"
# # #         )
# # #     else:
# # #         st.info("ℹ️ Couldn’t extract valid JSON insights.")

# # #     # -----------------------------
# # #     # COMPARISON
# # #     # -----------------------------
# # #     if comparison:
# # #         st.subheader("📈 Cross-Chart Comparison")
# # #         st.markdown(comparison.strip())

# # # else:
# # #     st.info("📤 Upload one or more chart images and click **Analyze with Gemini**.")

# # import io, base64, json, os
# # from PIL import Image
# # import streamlit as st
# # from google import genai
# # from dotenv import load_dotenv
# # from datetime import datetime
# # from reportlab.lib.pagesizes import A4
# # from reportlab.lib.units import inch
# # from reportlab.platypus import SimpleDocTemplate, Paragraph, Image as RLImage, Spacer
# # from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# # # -----------------------------
# # # LOAD API KEY
# # # -----------------------------
# # load_dotenv()
# # API_KEY = os.getenv("GEMINI_API_KEY")

# # if not API_KEY:
# #     st.error("❌ Gemini API key not found. Please set GEMINI_API_KEY in your .env file.")
# #     st.stop()

# # client = genai.Client(api_key=API_KEY)

# # # -----------------------------
# # # PAGE CONFIG
# # # -----------------------------
# # st.set_page_config(page_title="📊 Gemini Chart Analyzer Pro", page_icon="📈", layout="wide")
# # st.title("📊 Gemini Chart Analyzer Pro")
# # st.caption("Analyze chart images → structured insights & export as PDF using Gemini models ⚡")

# # # -----------------------------
# # # SIDEBAR SETTINGS
# # # -----------------------------
# # st.sidebar.header("⚙️ Settings")

# # theme = st.sidebar.radio("🎨 Select Theme", ["Light", "Dark"], index=0)
# # if theme == "Dark":
# #     background_color = "#0E1117"
# #     text_color = "#FAFAFA"
# # else:
# #     background_color = "#FFFFFF"
# #     text_color = "#000000"

# # st.markdown(
# #     f"""
# #     <style>
# #     .stApp {{
# #         background-color: {background_color};
# #         color: {text_color};
# #     }}
# #     </style>
# #     """,
# #     unsafe_allow_html=True,
# # )

# # # Model selector (only valid models)
# # MODEL_NAME = st.sidebar.selectbox(
# #     "🤖 Choose Gemini Model",
# #     ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
# #     index=0
# # )

# # tone = st.sidebar.selectbox("🗣️ Insight Tone", ["Professional", "Analytical", "Casual"], index=0)

# # # -----------------------------
# # # HIDDEN PROMPT
# # # -----------------------------
# # base_prompt = (
# #     "You are analyzing chart images (bar, line, pie, scatter). For each image:\n"
# #     "1. Identify axes (labels, units)\n"
# #     "2. Summarize key trends\n"
# #     "3. Find extrema and anomalies\n"
# #     "4. Provide 3 concise insights\n\n"
# #     "After analyzing all charts, find relationships or correlations between them "
# #     "(e.g., trends that match or oppose) and write a unified overall summary.\n\n"
# #     "Return JSON format as:\n"
# #     "[{{'image':'<filename>', 'summary':'', 'insights':[]}}]\n"
# #     "---\n"
# #     "Then write 'Relationships & Overall Summary' in Markdown."
# # )

# # tone_instructions = {
# #     "Professional": "Use a formal tone suitable for executive dashboards.",
# #     "Analytical": "Use a technical tone focusing on data-driven insights.",
# #     "Casual": "Use a friendly, simple tone like explaining to a non-expert."
# # }
# # final_prompt = f"{base_prompt}\nTone: {tone_instructions[tone]}"

# # # -----------------------------
# # # FILE UPLOAD
# # # -----------------------------
# # files = st.file_uploader(
# #     "📁 Upload chart images",
# #     type=["png", "jpg", "jpeg", "webp"],
# #     accept_multiple_files=True
# # )

# # def pil_to_b64(img: Image.Image) -> str:
# #     buf = io.BytesIO()
# #     img.save(buf, format="PNG")
# #     return base64.b64encode(buf.getvalue()).decode("utf-8")

# # # -----------------------------
# # # ANALYZE BUTTON
# # # -----------------------------
# # if files and st.button("🚀 Analyze Charts"):
# #     st.toast(f"🧠 Analyzing charts using {MODEL_NAME}...", icon="📊")
# #     previews = []
# #     parts = [{"role": "user", "parts": [{"text": final_prompt}]}]

# #     for f in files:
# #         data = f.read()
# #         img = Image.open(io.BytesIO(data)).convert("RGB")
# #         previews.append((f.name, img))
# #         b64 = pil_to_b64(img)
# #         parts[0]["parts"].append({
# #             "inline_data": {"mime_type": "image/png", "data": b64}
# #         })

# #     with st.expander("👀 Chart Previews", expanded=True):
# #         cols = st.columns(min(3, len(previews)))
# #         for i, (name, img) in enumerate(previews):
# #             cols[i % len(cols)].image(img, caption=name, use_container_width=True)

# #     with st.spinner(f"Generating insights with {MODEL_NAME}..."):
# #         try:
# #             result = client.models.generate_content(model=MODEL_NAME, contents=parts)
# #             output_text = result.text
# #         except Exception as e:
# #             st.error(f"⚠️ API Error: {e}")
# #             st.stop()

# #     st.success("✅ Analysis complete!")

# #     # -----------------------------
# #     # PARSE OUTPUT
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
# #             parsed = None
# #             st.warning("⚠️ Could not parse JSON properly.")

# #     # -----------------------------
# #     # DISPLAY RESULTS
# #     # -----------------------------
# #     if parsed:
# #         st.subheader("📊 Chart Insights")
# #         for entry in parsed:
# #             with st.expander(f"📈 {entry.get('image', 'Chart')}", expanded=False):
# #                 st.markdown(f"**Summary:** {entry.get('summary', 'N/A')}")
# #                 st.markdown("**Key Insights:**")
# #                 for i, ins in enumerate(entry.get('insights', []), start=1):
# #                     st.markdown(f"➡️ {i}. {ins}")

# #         if comparison:
# #             st.subheader("🔗 Relationships & Overall Summary")
# #             st.markdown(comparison.strip())

# #         # -----------------------------
# #         # PDF EXPORT
# #         # -----------------------------
# #         pdf_buf = io.BytesIO()
# #         doc = SimpleDocTemplate(pdf_buf, pagesize=A4)
# #         styles = getSampleStyleSheet()
# #         story = []

# #         # Styles
# #         style_header = ParagraphStyle(name='Header', fontSize=18, textColor=text_color, leading=22, spaceAfter=14)
# #         style_sub = ParagraphStyle(name='SubHeader', fontSize=13, textColor=text_color, spaceAfter=8)
# #         style_text = ParagraphStyle(name='Text', fontSize=10, textColor=text_color, leading=14)

# #         today = datetime.now().strftime("%B %d, %Y")

# #         # Add Logo if available
# #         logo_path = "https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.linkedin.com%2Fcompany%2Facies-global&psig=AOvVaw28RnYg7M_IaxuxA137F-kO&ust=1761825204400000&source=images&cd=vfe&opi=89978449&ved=0CBUQjRxqFwoTCLjGzL2syZADFQAAAAAdAAAAABAE"
# #         if os.path.exists(logo_path):
# #             story.append(RLImage(logo_path, width=2.5 * inch, height=1 * inch))
# #         story.append(Paragraph("📊 Gemini Chart Analyzer Report", style_header))
# #         story.append(Paragraph(f"<b>Generated by:</b> Srimukhi Pulluri", style_text))
# #         story.append(Paragraph(f"<b>Organization:</b> Acies Global", style_text))
# #         story.append(Paragraph(f"<b>Date:</b> {today}", style_text))
# #         story.append(Spacer(1, 12))

# #         # Add chart summaries
# #         for (fname, img), entry in zip(previews, parsed):
# #             img_path = io.BytesIO()
# #             img.save(img_path, format="PNG")
# #             img_path.seek(0)

# #             story.append(Paragraph(f"<b>{fname}</b>", style_sub))
# #             story.append(RLImage(img_path, width=5.5 * inch, height=3 * inch))
# #             story.append(Spacer(1, 6))
# #             story.append(Paragraph(f"<b>Summary:</b> {entry.get('summary', '')}", style_text))
# #             for i, ins in enumerate(entry.get("insights", []), start=1):
# #                 story.append(Paragraph(f"➡️ {i}. {ins}", style_text))
# #             story.append(Spacer(1, 10))

# #         if comparison:
# #             story.append(Paragraph("<b>🔗 Relationships & Overall Summary</b>", style_sub))
# #             story.append(Paragraph(comparison.strip(), style_text))

# #         story.append(Spacer(1, 20))
# #         footer_text = f"Report generated by Gemini Chart Analyzer | © {datetime.now().year} Acies Global"
# #         story.append(Paragraph(footer_text, ParagraphStyle(name="Footer", fontSize=8, textColor=text_color, alignment=1)))

# #         doc.build(story)
# #         st.download_button(
# #             "💾 Download PDF Report",
# #             data=pdf_buf.getvalue(),
# #             file_name=f"Gemini_Chart_Insights_{today}.pdf",
# #             mime="application/pdf"
# #         )

# #     else:
# #         st.info("⚠️ No structured insights were extracted.")

# import os
# import io
# import base64
# import tempfile
# from typing import List, Dict, Any
# from fpdf import FPDF
# import streamlit as st
# from dotenv import load_dotenv
# from PIL import Image
# from google import genai  # pip install google-genai

# # =========================
# # APP CONFIG
# # =========================
# st.set_page_config(page_title="Gemini Chart Analyzer", page_icon="📊", layout="wide")

# # Sidebar — Theme and Branding
# with st.sidebar:
#     st.image(
#         "https://media.licdn.com/dms/image/v2/D560BAQGaFGbp2Le0_w/company-logo_200_200/company-logo_200_200/0/1715927368675?e=2147483647&v=beta&t=JW6sny_XZqI9n_oF1u3Aec90BDVn4blFVwd2ySTZ80Y",
#         width=150,
#         caption="Acies Global"
#     )
#     theme = st.radio("🎨 Theme", ["Light", "Dark"], horizontal=True)
#     st.markdown("---")

#     st.session_state.setdefault("model_name", "gemini-2.0-flash")
#     st.session_state.model_name = st.selectbox(
#         "Model", ["gemini-2.0-flash", "gemini-2.0-pro"]
#     )

#     st.session_state.setdefault("word_limit", 200)
#     st.session_state.word_limit = st.slider("Word limit", 100, 500, 200, 20)

#     st.session_state.setdefault("output_style", "Structured (bulleted)")
#     st.session_state.output_style = st.selectbox(
#         "Output Format", ["Structured (bulleted)", "Narrative (story)"]
#     )

#     st.session_state.setdefault("audience", "Business Professional")
#     st.session_state.audience = st.selectbox(
#         "Audience", ["Business Professional", "Data Scientist"]
#     )

# # =========================
# # LOAD ENV & CLIENT
# # =========================
# load_dotenv()
# API_KEY = os.getenv("GEMINI_API_KEY")
# if not API_KEY:
#     st.error("⚠️ GEMINI_API_KEY missing in .env")
#     st.stop()

# client = genai.Client(api_key=API_KEY)

# # =========================
# # THEME COLORS
# # =========================
# if theme == "Dark":
#     BG_COLOR = "#121212"
#     TEXT_COLOR = "#ffffff"
#     CARD_BG = "#1E1E1E"
# else:
#     BG_COLOR = "#ffffff"
#     TEXT_COLOR = "#000000"
#     CARD_BG = "#f9f9f9"

# st.markdown(
#     f"""
#     <style>
#     body {{
#         background-color: {BG_COLOR};
#         color: {TEXT_COLOR};
#     }}
#     .stApp {{
#         background-color: {BG_COLOR};
#         color: {TEXT_COLOR};
#     }}
#     div[data-testid="stMarkdownContainer"] p {{
#         color: {TEXT_COLOR};
#     }}
#     .card {{
#         background: {CARD_BG};
#         padding: 20px;
#         border-radius: 15px;
#         box-shadow: 0 0 10px rgba(0,0,0,0.1);
#         margin-bottom: 20px;
#     }}
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

# # =========================
# # UTILITIES
# # =========================
# def pil_to_b64(img: Image.Image) -> str:
#     buf = io.BytesIO()
#     img.save(buf, format="PNG")
#     return base64.b64encode(buf.getvalue()).decode("utf-8")

# def decode_uploaded_files(files):
#     recs = []
#     for f in files:
#         data = f.read()
#         img = Image.open(io.BytesIO(data)).convert("RGB")
#         b64 = pil_to_b64(img)
#         mime = "image/png"
#         recs.append({"name": f.name, "img": img, "b64": b64, "mime": mime})
#     return recs

# def generate_insight(image_rec):
#     tone = "business-friendly" if st.session_state.audience == "Business Professional" else "technically detailed"
#     prompt = f"""
# Analyze the uploaded chart image and provide:
# 1) Short summary (2-3 lines)
# 2) Key findings (3–5 bullet points)
# 3) Keep tone {tone}.
# 4) Max {st.session_state.word_limit} words.
# """
#     contents = [{
#         "role": "user",
#         "parts": [
#             {"text": prompt},
#             {"inline_data": {"mime_type": image_rec["mime"], "data": image_rec["b64"]}},
#         ],
#     }]
#     try:
#         response = client.models.generate_content(
#             model=st.session_state.model_name, contents=contents
#         )
#         return (response.text or "").strip()
#     except Exception as e:
#         return f"⚠️ Error generating insights: {e}"

# def find_relationships(all_summaries):
#     prompt = f"""
# Here are the insights from multiple charts:
# {all_summaries}

# Now, find relationships, trends, and correlations between charts.
# Give a short comparative summary in Markdown.
# """
#     try:
#         response = client.models.generate_content(
#             model=st.session_state.model_name,
#             contents=[{"role": "user", "parts": [{"text": prompt}]}],
#         )
#         return (response.text or "").strip()
#     except Exception as e:
#         return f"⚠️ Could not analyze relationships: {e}"

# # =========================
# # PDF GENERATION
# # =========================
# def export_pdf(charts, insights, relationship_text):
#     pdf = FPDF()
#     pdf.add_page()
#     pdf.set_font("Arial", "B", 18)
#     pdf.cell(0, 10, "Gemini Chart Analyzer Report", ln=True, align="C")
#     pdf.ln(10)

#     for i, rec in enumerate(charts):
#         pdf.set_font("Arial", "B", 14)
#         pdf.cell(0, 10, f"Chart {i+1}: {rec['name']}", ln=True)
#         temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
#         rec["img"].save(temp.name)
#         pdf.image(temp.name, w=150)
#         pdf.set_font("Arial", "", 12)
#         pdf.multi_cell(0, 8, insights[i])
#         pdf.ln(8)

#     pdf.set_font("Arial", "B", 14)
#     pdf.cell(0, 10, "Overall Relationship Insights", ln=True)
#     pdf.set_font("Arial", "", 12)
#     pdf.multi_cell(0, 8, relationship_text)

#     output_path = "chart_analysis_report.pdf"
#     pdf.output(output_path)
#     return output_path

# # =========================
# # MAIN APP
# # =========================
# st.title("📊 Gemini Chart Analyzer")
# st.caption("Analyze charts → extract insights → discover relationships → export as PDF")

# files = st.file_uploader(
#     "Upload chart images (PNG, JPG, JPEG, WEBP)", 
#     type=["png", "jpg", "jpeg", "webp"],
#     accept_multiple_files=True
# )

# if st.button("🔍 Analyze Charts"):
#     if not files:
#         st.warning("Please upload at least one chart.")
#     else:
#         recs = decode_uploaded_files(files)
#         insights = []

#         for i, rec in enumerate(recs, start=1):
#             st.markdown(f"<div class='card'><h4>Chart {i}: {rec['name']}</h4>", unsafe_allow_html=True)
#             st.image(rec["img"], caption=rec["name"], use_container_width=True)
#             with st.spinner(f"Analyzing {rec['name']}..."):
#                 insight = generate_insight(rec)
#             insights.append(insight)
#             st.markdown(insight)
#             st.markdown("</div>", unsafe_allow_html=True)

#         st.success("✅ Individual analyses complete! Finding relationships...")
#         combined_summary = "\n\n".join(insights)
#         with st.spinner("Analyzing relationships across charts..."):
#             relationships = find_relationships(combined_summary)

#         st.markdown("### 🔗 Relationships Between Charts")
#         st.markdown(relationships)

#         pdf_path = export_pdf(recs, insights, relationships)
#         with open(pdf_path, "rb") as f:
#             st.download_button(
#                 label="📥 Download Report as PDF",
#                 data=f,
#                 file_name="Gemini_Chart_Report.pdf",
#                 mime="application/pdf"
#             )


import streamlit as st
import google.generativeai as genai
import time
from PIL import Image
import io
import base64

# ========== CONFIGURATION ==========
st.set_page_config(
    page_title="Chart Insight Analyzer | Acies Global",
    page_icon="💬",
    layout="wide"
)

# Load Acies logo

logo_path = r"C:\Users\Srimukhi\Desktop\Vision_Chatbot\acies-global.webp"


# Custom CSS styling
st.markdown("""
    <style>
    body {
        background-color: black;
        color: #0A2A66;
        font-family: 'Poppins', sans-serif;
    }
    .main {
        padding: 2rem;
    }
    .title {
        text-align: center;
        font-size: 2rem;
        font-weight: 600;
        color: #0A2A66;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .floating-btn {
        position: fixed;
        bottom: 25px;
        right: 25px;
        background-color: #0A2A66;
        color: white;
        border: none;
        border-radius: 50px;
        padding: 15px 25px;
        font-size: 16px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
        cursor: pointer;
        transition: 0.3s;
        z-index: 1000;
    }
    .floating-btn:hover {
        background-color: #133d91;
    }
    </style>
""", unsafe_allow_html=True)

# Floating chat button
#st.markdown('<button class="floating-btn" id="chat-btn">💬 Chat with Data</button>', unsafe_allow_html=True)


# --- CSS for Floating Button and Drawer ---
drawer_css = """
<style>
/* Floating Chat Button */
.floating-chat-btn {
    position: fixed;
    bottom: 25px;
    right: 25px;
    background-color: #002855;
    color: white;
    padding: 14px 24px;
    border-radius: 40px;
    font-weight: 600;
    box-shadow: 0 4px 10px rgba(0,0,0,0.25);
    cursor: pointer;
    text-align: center;
    transition: all 0.3s ease;
    z-index: 9999;
}
.floating-chat-btn:hover {
    background-color: #004080;
    transform: scale(1.05);
}

/* Chat Drawer (hidden by default) */
.chat-drawer {
    position: fixed;
    top: 0;
    right: -450px;
    width: 400px;
    height: 100%;
    background-color: #ffffff;
    box-shadow: -4px 0 10px rgba(0,0,0,0.15);
    border-left: 3px solid #002855;
    transition: right 0.4s ease;
    z-index: 10000;
    padding: 20px;
    overflow-y: auto;
}
.chat-drawer.open {
    right: 0;
}
.chat-header {
    font-size: 20px;
    font-weight: 600;
    color: #002855;
    border-bottom: 2px solid #eee;
    padding-bottom: 10px;
    margin-bottom: 10px;
}
.close-btn {
    float: right;
    font-size: 18px;
    cursor: pointer;
    color: #666;
}
.chat-msg-box {
    margin-top: 20px;
}
</style>
"""

st.markdown(drawer_css, unsafe_allow_html=True)

# --- Initialize chat state ---
if "show_chat_drawer" not in st.session_state:
    st.session_state.show_chat_drawer = False

# --- JavaScript toggle for Drawer ---
chat_button_html = """
<div class="floating-chat-btn" id="openChatBtn">💬 Chat with Data</div>
<div class="chat-drawer" id="chatDrawer">
    <div class="chat-header">
        Chat with Gemini AI
        <span class="close-btn" id="closeDrawer">&times;</span>
    </div>
    <div id="chatContainer">
        <p><i>Hi 👋, ask me about your chart insights!</i></p>
    </div>
</div>

<script>
const chatDrawer = window.parent.document.getElementById('chatDrawer');
const openChatBtn = window.parent.document.getElementById('openChatBtn');
const closeDrawer = window.parent.document.getElementById('closeDrawer');

if (openChatBtn && closeDrawer && chatDrawer) {
    openChatBtn.onclick = () => chatDrawer.classList.add('open');
    closeDrawer.onclick = () => chatDrawer.classList.remove('open');
}
</script>
"""

st.markdown(chat_button_html, unsafe_allow_html=True)

# --- Chat Drawer Logic (Gemini Integration) ---
if st.session_state.show_chat_drawer:
    st.markdown("### 💬 Chat with Gemini AI")
    user_input = st.text_input("Ask your question about the chart:")
    if user_input:
        with st.spinner("Thinking..."):
            try:
                import google.generativeai as genai
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(user_input)
                st.success(response.text)
            except Exception as e:
                st.error(f"Error: {e}")

# Sidebar as chat drawer
st.sidebar.image(logo_path, width=150)
#st.sidebar.title("💬 Chart Insight Assistant")
#st.sidebar.markdown("Upload a chart image to get instant insights from Gemini AI.")



# Gemini configuration
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")


# Upload chart image
uploaded_file = st.file_uploader("📊 Upload a Chart Image (PNG, JPG)", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Chart", use_column_width=True)

    with st.spinner("Analyzing chart with Gemini... 🧠"):
        # Convert image to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_bytes = img_bytes.getvalue()

        # Send to Gemini
        prompt = """
        You are a data visualization expert.
        Analyze this chart image and describe:
        1. The chart type (bar, line, pie, scatter, etc.)
        2. The main trend, comparisons, and insights
        3. Any anomalies, outliers, or interesting findings
        Be concise and professional.
        """
        result = model.generate_content([
            {"mime_type": "image/png", "data": img_bytes},
            prompt
        ])

        # Display insights
        st.subheader("📈 Gemini Insights")
        st.markdown(result.text)

else:
    st.info("👆 Upload a chart image (e.g., bar chart, pie chart) to get started.")

# Footer
st.markdown(
    f"<hr><p style='text-align:center; color:#555;'>© 2025 Acies Global | Powered by Gemini AI</p>",
    unsafe_allow_html=True
)
