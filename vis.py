
import io, base64, json
from PIL import Image
import streamlit as st
from google import genai   # new SDK

# -----------------------------
# HARD-CODED SETTINGS
# -----------------------------
GEMINI_API_KEY = "AIzaSyAthKAfQTGNNI8s-3oeA2UlcBHOJezBJVQ"
MODEL_NAME = "gemini-2.0-flash"               # free, fast, multimodal

# -----------------------------
# SETUP
# -----------------------------
client = genai.Client(api_key=GEMINI_API_KEY)

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
    st.info("Upload images and click **Analyze with Gemini**.")
