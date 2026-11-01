import os
import streamlit as st
from pypdf import PdfReader
from huggingface_hub import InferenceClient

MODEL = "Qwen/Qwen2.5-72B-Instruct"
MAX_CHARS = 24000

try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
except Exception:
    HF_TOKEN = os.environ.get("HF_TOKEN")

PROMPT = """You are a senior analyst writing a daily briefing for an Indian reader.
Below is raw text extracted from pages of the newspaper "{paper}". The text is
messy (columns, ads, captions may be mixed together).

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

Rules: use only facts present in the text plus well-established background.
Do not invent facts, quotes or numbers. If the text for a story is unclear
or cut off, say so briefly.

NEWSPAPER TEXT:
{text}
"""

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
    if not HF_TOKEN:
        st.error("HF_TOKEN secret is missing.")
    elif file is None:
        st.warning("Please upload a PDF first.")
    else:
        with st.spinner("Reading and analysing..."):
            try:
                reader = PdfReader(file)
                last = min(len(reader.pages), int(end))
                parts = []
                for i in range(int(start) - 1, last):
                    parts.append(f"[Page {i + 1}]\n" + (reader.pages[i].extract_text() or ""))
                text = "\n\n".join(parts)
            except Exception:
                st.error("Could not read this PDF.")
                st.stop()

            if len(text.strip()) < 500:
                st.error("Almost no text found. This PDF may be scanned images.")
                st.stop()

            try:
                client = InferenceClient(token=HF_TOKEN)
                resp = client.chat_completion(
                    model=MODEL,
                    messages=[{"role": "user", "content": PROMPT.format(
                        paper=paper, n=n, text=text[:MAX_CHARS])}],
                    max_tokens=3000,
                    temperature=0.4,
                )
                st.markdown(resp.choices[0].message.content)
            except Exception as e:
                st.error(f"Analysis failed: {type(e).__name__}")
