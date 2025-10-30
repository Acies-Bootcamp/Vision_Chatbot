# import os
# import io
# import base64
# from typing import List, Dict, Any

# import streamlit as st
# from dotenv import load_dotenv
# from PIL import Image
# from google import genai  # pip install google-genai

# # =========================
# # App Config
# # =========================
# st.set_page_config(page_title="Gemini Chart Analyzer", page_icon="📊", layout="wide")
# st.title("📊 Gemini Chart Analyzer")

# # =========================
# # Session State Defaults
# # =========================
# def _init_state():
#     st.session_state.setdefault("uploads", [])   # [{name, data, img, b64, mime}]
#     st.session_state.setdefault("analysis_summary", "")
#     st.session_state.setdefault("model_name", "gemini-2.0-flash")
#     st.session_state.setdefault("word_limit", 200)
#     st.session_state.setdefault("output_style", "Structured (bulleted)")
#     st.session_state.setdefault("conversation", [])
#     st.session_state.setdefault("audience", "Business Professional")  # only audience

# _init_state()

# # =========================
# # Env & Client
# # =========================
# load_dotenv()
# API_KEY = os.getenv("GEMINI_API_KEY")
# if not API_KEY:
#     st.error("⚠️ GEMINI_API_KEY missing. Create a .env file with GEMINI_API_KEY=your_key")
#     st.stop()

# client = genai.Client(api_key=API_KEY)
# MODEL_CHOICES = ["gemini-2.0-flash", "gemini-2.0-pro"]

# # =========================
# # Small Utilities
# # =========================
# def guess_mime(name: str) -> str:
#     nl = name.lower()
#     if nl.endswith(".png"): return "image/png"
#     if nl.endswith(".webp"): return "image/webp"
#     if nl.endswith(".bmp"): return "image/bmp"
#     return "image/jpeg"

# def decode_uploaded_files(files) -> List[Dict[str, Any]]:
#     out = []
#     if not files:
#         return out
#     for f in files:
#         data = f.getvalue()
#         if not data or len(data) < 10:
#             st.warning(f"⚠️ {f.name} is empty or corrupted. Skipping.")
#             continue
#         try:
#             img = Image.open(io.BytesIO(data)).convert("RGB")
#         except Exception as e:
#             st.warning(f"⚠️ Skipping {f.name}: not a valid image ({e})")
#             continue
#         b64 = base64.b64encode(data).decode("utf-8")
#         out.append({
#             "name": f.name, "data": data, "img": img, "b64": b64, "mime": guess_mime(f.name)
#         })
#     return out

# def _overview_and_bullets(word_limit: int):
#     short = word_limit <= 150
#     overview_lines = "1–2 lines" if short else "2–3 lines"
#     bullet_points = "3–4 bullet points" if short else "5–6 bullet points"
#     length_instruction = "Keep it concise." if short else "Elaborate clearly but stay focused."
#     return overview_lines, bullet_points, length_instruction

# # =========================
# # Gemini Call (per chart)
# # =========================
# def generate_individual_insight_from_rec(
#     rec: Dict[str, Any],
#     audience: str,
#     word_limit: int,
#     model_name: str,
#     output_style: str
# ) -> str:
#     overview_lines, bullet_points, length_instruction = _overview_and_bullets(word_limit)
#     tone_note = "business-friendly" if audience == "Business Professional" else "technically precise"

#     prompt = f"""
# You are a professional data analyst. Analyze the uploaded chart image and provide a structured, professional response.

# Audience: {audience}.
# Instructions:
# 1) Begin with an overview summary ({overview_lines}).
# 2) Follow with key findings and insights ({bullet_points}).
# 3) Keep the tone {tone_note}.
# 4) {length_instruction}
# 5) Keep total length near {word_limit} words.
# 6) {"Use concise bullets." if output_style.startswith("Structured") else "Write it as a short narrative paragraph."}
# """

#     contents = [{
#         "role": "user",
#         "parts": [
#             {"text": prompt},
#             {"inline_data": {"mime_type": rec["mime"], "data": rec["b64"]}},
#         ],
#     }]

#     try:
#         response = client.models.generate_content(model=model_name, contents=contents)
#         return (getattr(response, "text", "") or "").strip() or "No insights generated."
#     except Exception as e:
#         return f"API Error: {e}"

# # =========================
# # Colors and Styles
# # =========================
# PALE_PINK = "#FFDDEE"
# PEACH = "#FFE5B4"

# st.markdown(
#     f"""
#     <style>
#     /* Style Streamlit tabs for Home and Ask */
#     div[data-testid="stHorizontalBlock"] > div:nth-child(1) > div[data-testid="stTab"] {{
#         background-color: {PALE_PINK} !important;
#         border-radius: 5px 5px 0 0 !important;
#         padding: 10px 15px !important;
#     }}
#     div[data-testid="stHorizontalBlock"] > div:nth-child(2) > div[data-testid="stTab"] {{
#         background-color: {PEACH} !important;
#         border-radius: 5px 5px 0 0 !important;
#         padding: 10px 15px !important;
#     }}

#     /* Style for horizontal control row */
#     .control-row > div {{
#         display: inline-block;
#         vertical-align: middle;
#         margin-right: 12px;
#         background: #fff0f5;
#         border-radius: 8px;
#         padding: 8px 12px;
#     }}

#     /* Adjust chat message box colors for clarity */
#     [data-testid="stChatMessage"] {{
#         max-width: 80%;
#     }}
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

# # =========================
# # Controls row with dynamic word limit based on audience
# # =========================
# def render_controls_row():
#     cols = st.columns([1.3, 1.3, 1.3, 1.3], gap="large")
#     with cols[0]:
#         st.session_state.model_name = st.selectbox(
#             "Model",
#             MODEL_CHOICES,
#             index=(MODEL_CHOICES.index(st.session_state.model_name)
#                    if st.session_state.model_name in MODEL_CHOICES else 0),
#             help="Use flash for speed; pro for higher quality."
#         )
#     with cols[1]:
#         max_word_limit = 300 if st.session_state.audience == "Business Professional" else 600
#         # Clamp current word_limit inside max for audience
#         if st.session_state.word_limit > max_word_limit:
#             st.session_state.word_limit = max_word_limit
#         st.session_state.word_limit = st.slider(
#             "Word limit", min_value=80, max_value=max_word_limit,
#             value=st.session_state.word_limit, step=20
#         )
#     with cols[2]:
#         st.session_state.output_style = st.selectbox(
#             "Output format",
#             ["Structured (bulleted)", "Narrative (story)"],
#             index=(0 if st.session_state.output_style.startswith("Structured") else 1)
#         )
#     with cols[3]:
#         st.session_state.audience = st.selectbox(
#             "Audience",
#             ["Business Professional", "Data Scientist"],
#             index=0 if st.session_state.audience == "Business Professional" else 1
#         )

# st.markdown('<div class="control-row">', unsafe_allow_html=True)
# render_controls_row()
# st.markdown('</div>', unsafe_allow_html=True)


# # =========================
# # Main App
# # =========================
# home_tab, ask_tab = st.tabs(["Home", "Ask"])

# with home_tab:
#     files = st.file_uploader(
#         "Upload chart images",
#         type=["png", "jpg", "jpeg", "webp", "bmp", "jfif"],
#         accept_multiple_files=True
#     )
#     if files:
#         st.session_state.uploads = decode_uploaded_files(files)

#     analyze = st.button("🔍 Analyze Charts", type="primary")

#     if analyze:
#         if not st.session_state.uploads:
#             st.error("Please upload at least one chart to analyze.")
#         else:
#             model_name = st.session_state.model_name
#             audience = st.session_state.audience
#             word_limit = st.session_state.word_limit
#             output_style = st.session_state.output_style

#             summary_blocks = []

#             # Individual analysis only
#             for idx, rec in enumerate(st.session_state.uploads, start=1):
#                 st.markdown(f"### Chart {idx} — {rec['name']}")
#                 col_chart, col_insight = st.columns([1, 2], gap="large")
#                 with col_chart:
#                     st.image(rec["img"], caption=rec["name"], use_container_width=True)
#                 with col_insight:
#                     with st.spinner(f"Analyzing {rec['name']} with {model_name}..."):
#                         insight = generate_individual_insight_from_rec(
#                             rec, audience, word_limit, model_name, output_style
#                         )
#                     st.markdown(insight)
#                     summary_blocks.append(f"Chart {idx} ({rec['name']}):\n{insight}")

#             st.session_state.analysis_summary = "\n\n---\n\n".join(summary_blocks)
#             st.success("✅ Analysis complete. Switch to the **Ask** tab to query the results.")

# with ask_tab:
#     st.header("❓ Ask a question about the charts")
#     if not st.session_state.analysis_summary:
#         st.info("No analysis found. Please analyze charts on the Home tab first.")
#     else:
#         user_input = st.chat_input("Type your question about the charts...")
#         if user_input:
#             prompt = (
#                 "Answer based only on the analysis below.\n\n"
#                 f"Context:\n{st.session_state.analysis_summary}\n\n"
#                 "Question: " + user_input
#             )
#             contents = [{"role": "user", "parts": [{"text": prompt}]}]
#             with st.spinner(f"Getting answer from {st.session_state.model_name}..."):
#                 try:
#                     res = client.models.generate_content(
#                         model=st.session_state.model_name,
#                         contents=contents
#                     )
#                     answer = (res.text or "").strip()
#                 except Exception as e:
#                     st.error(f"API Error: {e}")
#                     answer = ""
#             if answer:
#                 st.session_state.conversation.append({"user": user_input, "assistant": answer})

#         for msg in st.session_state.conversation:
#             st.chat_message("user").markdown(msg["user"])
#             st.chat_message("assistant").markdown(msg["assistant"])

#         with st.expander("Analysis Summary", expanded=False):
#             st.markdown(st.session_state.analysis_summary)

import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# -----------------------------------------------------------
# 🧠 CONFIGURATION
# -----------------------------------------------------------
st.set_page_config(page_title="Chart Insight Assistant", page_icon="📊", layout="wide")

# ✅ Gemini API Setup — reads from Streamlit Secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel("gemini-1.5-flash")

# -----------------------------------------------------------
# 💾 SESSION STATE HANDLER
# -----------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "upload"

def go_to_chat():
    st.session_state.page = "chat"

def go_to_upload():
    st.session_state.page = "upload"

# -----------------------------------------------------------
# 🎨 GLOBAL STYLE
# -----------------------------------------------------------
st.markdown(
    """
    <style>
        body {
            background-color: #f6f8fb;
        }
        .main-title {
            text-align: center;
            color: #0c2340;
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .sub-title {
            text-align: center;
            color: #5a5a5a;
            font-size: 18px;
            margin-bottom: 30px;
        }
        .footer {
            text-align: center;
            color: gray;
            font-size: 13px;
            margin-top: 40px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------
# 📤 UPLOAD PAGE
# -----------------------------------------------------------
if st.session_state.page == "upload":
    st.markdown("<h1 class='main-title'>📊 Chart Insight Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>Upload your chart and get instant insights powered by Gemini AI</p>", unsafe_allow_html=True)

    # Logo
    st.image("C:/Users/Srimukhi/Desktop/Vision_Chatbot/Acies_Logo_white.png", width=120)

    st.markdown("### Upload a Chart Image (PNG, JPG)")
    uploaded_file = st.file_uploader("Drag and drop or browse a chart image", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Chart", use_container_width=True)

        # Store uploaded image for chat session
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        st.session_state["uploaded_image"] = img_bytes.getvalue()

        st.success("✅ Chart uploaded successfully!")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💬 Chat with Data", use_container_width=True):
        if "uploaded_image" in st.session_state:
            go_to_chat()
        else:
            st.warning("Please upload a chart before proceeding.")

    st.markdown("<div class='footer'>© 2025 Acies Global | Powered by Gemini AI</div>", unsafe_allow_html=True)

# -----------------------------------------------------------
# 💬 CHAT PAGE
# -----------------------------------------------------------
elif st.session_state.page == "chat":
    st.markdown("<h1 class='main-title'>💬 Chat with Gemini AI</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>Ask questions or discuss insights from your uploaded chart.</p>", unsafe_allow_html=True)

    if "uploaded_image" not in st.session_state:
        st.warning("⚠ Please upload a chart first.")
        if st.button("⬅ Back to Upload Page"):
            go_to_upload()
    else:
        image_data = st.session_state["uploaded_image"]
        st.image(image_data, caption="Your Uploaded Chart", use_container_width=True)

        user_query = st.text_input("Type your message to Gemini:", key="chat_input")

        if st.button("Send"):
            if user_query.strip():
                try:
                    # Send image + text to Gemini model
                    img = Image.open(io.BytesIO(image_data))
                    response = model.generate_content([user_query, img])
                    st.chat_message("user").write(user_query)
                    st.chat_message("assistant").write(response.text)
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter a question or message before sending.")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅ Back to Upload Page"):
            go_to_upload()
