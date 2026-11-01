import os
import io
import time
import base64
import streamlit as st
from pypdf import PdfReader, PdfWriter
from google import genai

MODELS = ["gemini-3.5-flash", "gemini-3.8-flash"]   # tried in this order

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = os.environ.get("GEMINI_API_KEY")

PROMPT = """You are a senior analyst writing a daily briefing for an Indian reader.
The attached PDF contains pages from the newspaper "{paper}".

Task:
1. Pick the {n} most important stories. Prioritise India (policy, economy,
   politics, security) first, then major world events and geopolitics.
2. For each story write:
   ## <Short headline you write>
   **What happened:** 1-2 sentences
   **Why this matters:** ...
   **What's underneath:** deeper causes and context
   **Impacts:** likely consequences, especially for India
   **Bigger picture:** how it connects to larger trends

Rules: use only facts present in the pages plus well-established background.
Do not invent facts, quotes or numbers. If a story is unclear or cut off,
say so briefly.
"""


def slice_pdf(file, start, end):
    reader = PdfReader(file)
    last = min(len(reader.pages), end)
    writer = PdfWriter()
    for i in range(start - 1, last):
        writer.add_page(reader.pages[i])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def ask_gemini(pdf_bytes, prompt):
    client = genai.Client(api_key=API_KEY)
    last_error = None
    for model in MODELS:
        for attempt in range(3):
            try:
                interaction = client.interactions.create(
                    model=model,
                    input=[
                        {
                            "type": "document",
                            "data": base64.b64encode(pdf_bytes).decode("utf-8"),
                            "mime_type": "application/pdf",
                        },
                        {"type": "text", "text": prompt},
                    ],
                )
                return interaction.output_text
            except Exception as e:
                last_error = e
                busy = any(x in str(e) for x in ["503", "429", "UNAVAILABLE"])
                if busy:
                    time.sleep(4 * (attempt + 1))   # wait, then retry
                else:
                    break                            # other error: next model
    raise last_error


st.set_page_config(page_title="Deep News", page_icon="📰")
st.title("📰 Deep News")
st.caption("Upload today's paper, get the analysis.")

file = st.file_uploader("Newspaper PDF", type="pdf")
paper = st.selectbox("Newspaper", ["Indian Express", "Business Standard"])
col1, col2 = st.columns(2)
start = col1.number_input("From page", min_value=1, value=1, step=1)
end = col2.number_input("To page", min_value=1, value=6, step=1)
n = st.slider("Number of stories", 3, 8, 6)

if st.button("Analyse"):
    if not API_KEY:
        st.error("GEMINI_API_KEY secret is missing.")
    elif file is None:
        st.warning("Please upload a PDF first.")
    else:
        with st.spinner("Reading and analysing..."):
            try:
                pdf_bytes = slice_pdf(file, int(start), int(end))
            except Exception:
                st.error("Could not read this PDF.")
                st.stop()

            if len(pdf_bytes) > 18 * 1024 * 1024:
                st.error("These pages are too large. Try fewer pages.")
                st.stop()

            try:
                result = ask_gemini(pdf_bytes, PROMPT.format(paper=paper, n=n))
                st.markdown(result)
            except Exception as e:
                st.error(f"Analysis failed: {type(e).__name__}")
                st.caption(str(e)[:300])
