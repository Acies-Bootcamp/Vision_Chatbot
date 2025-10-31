import io, os, base64
from PIL import Image
import streamlit as st
from dotenv import load_dotenv
from google import genai

# -----------------------------
# SETUP
# -----------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ Please set GEMINI_API_KEY in your .env file.")
    st.stop()

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.0-flash"

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="ChartSense AI", layout="wide", page_icon="")

# -----------------------------
# SIDEBAR OPTIONS
# -----------------------------
st.sidebar.header("⚙️ Analysis Configuration")

# User type
person_type = st.sidebar.radio(
    "Your Background",
    ["Business Professional", "Technical Analyst"],
    help="Select the profile that best matches your perspective."
)

# Analysis depth (merged previous Response Depth & Summary Length)
analysis_depth = st.sidebar.radio(
    "Analysis Depth",
    ["Short & Crisp", "Detailed & Elaborate"],
    help="Controls both the length and analytical depth of the generated insights."
)


# Individual or combined analysis
result_type = st.sidebar.radio(
    "Analysis Mode",
    ["Individual", "Combined"],
    help="Whether to generate insights per chart or a single combined report."
)

# -----------------------------
# DYNAMIC CSS
# -----------------------------
max_height = "500px" if result_type == "Combined" else "350px"

st.markdown(f"""
<style>
.stButton>button {{
    background-color: #4CAF50; color: white; height: 40px; width: 150px;
    border-radius: 10px; border: none; font-size: 16px;
}}
.stButton>button:hover {{background-color: #45a049;}}
div.stFileUploader {{border: 2px dashed #4CAF50; border-radius: 10px; padding: 20px;}}
.insight-card {{
    background-color: #f9f9f9;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 15px;
    box-shadow: 1px 1px 5px rgba(0,0,0,0.1);
    max-height: {max_height};
    overflow-y: auto;
}}
[data-testid="stSidebar"] > div:first-child {{
    background-color: #f0f2f6;
    padding: 15px;
}}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# HEADER
# -----------------------------
with st.container():
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("logo.png", width=250)
    with col2:
        st.title("ChartSense AI")

st.markdown("**Get crisp, professional insights from your charts.**")
st.markdown("_Upload charts to get a short overview and key findings — individually or combined._")
st.markdown("💡 **Tip:** Use the sidebar to control analysis depth and analysis mode.")
st.markdown("---")

# -----------------------------
# UPLOAD SECTION
# -----------------------------
st.header("Upload Your Chart(s)")
uploaded_files = st.file_uploader(
    "Upload chart images (PNG/JPG). You can select multiple files.",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

# -----------------------------
# GEMINI FUNCTIONS
# -----------------------------
def generate_individual_insight(file, person_type, analysis_depth):
    """Analyze a single chart based on user preferences."""
    image_bytes = file.read()
    mime_type = "image/png" if file.name.lower().endswith("png") else "image/jpeg"
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Set lines/bullets based on depth
    overview_lines = "1–2 lines" if analysis_depth == "Short & Crisp" else "2–3 lines"
    bullet_points = "3–4 bullet points" if analysis_depth == "Short & Crisp" else "5–6 bullet points"
    length_instruction = "Keep it concise." if analysis_depth == "Short & Crisp" else "Elaborate clearly but stay focused."

    prompt = f"""
You are a professional data analyst.
Analyze the uploaded chart image and provide a structured, professional response.

Audience: {person_type}.
Analysis Depth: {analysis_depth}.

Instructions:
1. Begin with an **overview summary** of the chart ({overview_lines}).  
2. Follow with **key findings and insights** ({bullet_points}).  
3. Keep the tone aligned with the reader type — business-friendly if business professional, technically precise if analyst.  
4. {length_instruction}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[{"role": "user", "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": mime_type, "data": image_b64}}
        ]}]
    )

    return getattr(response, "text", "").strip() or "No insights generated."

def generate_combined_insight(files, person_type, analysis_depth):
    """Analyze multiple charts together and discuss relationships."""
    overview_lines = "1–2 lines" if analysis_depth == "Short & Crisp" else "2–3 lines"
    bullet_points = "3–5 bullet points" if analysis_depth == "Short & Crisp" else "5–7 bullet points"
    length_instruction = "Keep it concise." if analysis_depth == "Short & Crisp" else "Elaborate clearly but stay focused."

    contents = [{"role": "user", "parts": [
        {"text": f"""
You are a senior data analyst. You are given multiple related charts.
Analyze them and provide a structured, professional combined insight report.

Audience: {person_type}.
Analysis Depth: {analysis_depth}.

Instructions:
1. Begin with an **overall overview** summarizing what all charts collectively show ({overview_lines}).  
2. Provide **cross-chart insights** ({bullet_points}), highlighting relationships, correlations, or contrasts.  
3. Avoid repeating similar facts. Keep the response concise and professional, aligned with the selected audience.  
{length_instruction}
"""}
    ]}]

    for file in files:
        image_bytes = file.read()
        mime_type = "image/png" if file.name.lower().endswith("png") else "image/jpeg"
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        contents[0]["parts"].append({"inline_data": {"mime_type": mime_type, "data": image_b64}})

    response = client.models.generate_content(model=MODEL_NAME, contents=contents)
    return getattr(response, "text", "").strip() or "No insights generated."

# -----------------------------
# MAIN LOGIC
# -----------------------------
show_question = False

if st.button("Analyze"):
    if uploaded_files:
        st.info("🔍 Generating insights… please wait.")

        if result_type == "Individual":
            for idx, file in enumerate(uploaded_files, start=1):
                st.markdown(f"### Chart {idx}")
                col_chart, col_insight = st.columns([1, 2], gap="large")
                with col_chart:
                    file.seek(0)
                    st.image(file, caption=file.name, use_container_width=True)
                with col_insight:
                    file.seek(0)
                    insight = generate_individual_insight(file, person_type, analysis_depth)
                    st.markdown(
                        f'<div class="insight-card"><b>Insights:</b><br>{insight}</div>',
                        unsafe_allow_html=True
                    )

        else:  # Combined
            st.markdown("### Combined Analysis Across All Charts")
            col_chart, col_insight = st.columns([1, 2], gap="large")

            with col_chart:
                for file in uploaded_files:
                    st.image(file, caption=file.name, use_container_width=True)

            with col_insight:
                for file in uploaded_files:
                    file.seek(0)
                combined_result = generate_combined_insight(uploaded_files, person_type, analysis_depth)
                st.markdown(
                    f'<div class="insight-card"><b>Combined Insights:</b><br>{combined_result}</div>',
                    unsafe_allow_html=True
                )

        show_question = True
    else:
        st.error("Please upload at least one chart to analyze.")

# -----------------------------
# FOLLOW-UP QUESTION SECTION
# -----------------------------
if show_question:
    st.markdown("---")
    st.header("Have a question about the analysis?")
    user_question = st.text_input("Ask your question here:")

    if st.button("Submit Question"):
        if user_question:
            st.info("🤔 Thinking...")
            followup_prompt = f"Based on the previous analysis, answer this question concisely: {user_question}"
            response = client.models.generate_content(model=MODEL_NAME, contents=followup_prompt)
            st.success(response.text.strip() if response.text else "No response generated.")
        else:
            st.warning("Please enter a question.")
