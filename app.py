
import streamlit as st
import pdfplumber
import re
import random
import string
import json
import os

# -------------------
# JSON helpers
# -------------------
def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# -------------------
# Resume functions
# -------------------
def scrub_resume(text, name=None, city=None):
    result = text
    markers_removed = 0

    def replace(pattern, repl, flags=0):
        nonlocal result, markers_removed
        new_result = re.sub(pattern, repl, result, flags=flags)
        if new_result != result:
            markers_removed += len(re.findall(pattern, result, flags))
        result = new_result

    if name:
        replace(re.escape(name), "[hidden name]", flags=re.IGNORECASE)
    if city:
        replace(re.escape(city), "[hidden location]", flags=re.IGNORECASE)

    replace(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[hidden email]", flags=re.IGNORECASE)
    replace(r"(\+?\d{1,2}[\s.-]?)?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})", "[hidden phone]")
    replace(r"\b\d{1,5}\s+\w+(?:\s+\w+){0,3}\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b",
            "[hidden address]", flags=re.IGNORECASE)

    school_terms = ["High School", "Middle School", "Elementary School",
                    "University", "College", "Academy", "Institute"]
    for term in school_terms:
        replace(term, "[hidden school]", flags=re.IGNORECASE)

    replace(r"https?:\/\/\S*linkedin\.com\S*", "[hidden profile link]", flags=re.IGNORECASE)
    replace(r"\b\d{5}(?:-\d{4})?\b", "[hidden zipcode]")

    return result, markers_removed

def clean_extracted_text(text):
    text = re.sub(r"\(cid:\d+\)", "• ", text)
    text = re.sub(r"(\d)n(\d)", r"\1-\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

def generate_candidate_id():
    return "Candidate #" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

# -------------------
# Streamlit UI
# -------------------
st.set_page_config(page_title="FairHire Resume Scrubber", layout="centered")
st.title("FairHire Resume Scrubber (PDF Prototype)")
st.caption("Prototype that removes race-linked identity markers from resumes.")
st.markdown("---")

uploaded_pdf = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
name = st.text_input("Your full name (as appears on resume)")
city = st.text_input("Your city (as appears on resume)")

if uploaded_pdf:
    st.success("PDF uploaded successfully.")

if st.button("Extract & Scrub Resume"):
    if uploaded_pdf:
        progress = st.progress(0)
        progress.progress(20)

        with pdfplumber.open(uploaded_pdf) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        progress.progress(50)
        text = clean_extracted_text(text)
        st.subheader("Original Extracted Text")
        st.text_area("Original Resume", text, height=300)

        candidate_id = generate_candidate_id()
        scrubbed, markers_removed = scrub_resume(text, name, city)

        progress.progress(80)
        st.subheader(f"Anonymized Resume ({candidate_id})")
        st.text_area("Scrubbed Resume", scrubbed, height=300)

        # Download button for anonymized resume
        st.download_button(
            label="Download Anonymized Resume",
            data=scrubbed,
            file_name=f"{candidate_id}_scrubbed.txt",
            mime="text/plain"
        )

        # Save to resumes.json
        entry = {
            "candidateId": candidate_id,
            "originalText": text,
            "scrubbedText": scrubbed,
            "markersRemoved": markers_removed
        }

        resumes_JSON = "resumes.json"
        data = load_json(resumes_JSON)
        data.append(entry)
        save_json(resumes_JSON, data)

        progress.progress(100)
        st.success(f"Saved to database as {candidate_id}!")
    else:
        st.error("Please upload a PDF first.")

# -------------------
# Employer Portal
# -------------------
st.markdown("---")
st.title("Employer Portal")

resumes_JSON = "resumes.json"
hired_JSON = "hired.json"

candidates = load_json(resumes_JSON)

if "hired" not in st.session_state:
    st.session_state.hired = load_json(hired_JSON)

def save_hired():
    save_json(hired_JSON, st.session_state.hired)

# Candidate list
for candidate in candidates:
    cid = candidate["candidateId"]
    original = clean_extracted_text(candidate["originalText"])
    scrubbed = clean_extracted_text(candidate["scrubbedText"])

    with st.expander(f"{cid} - View Resume"):
        st.subheader("Scrubbed Resume (Anonymous)")
        st.text(scrubbed)

        st.markdown("---")

        if st.button(f"Hire {cid}", key=f"hire_{cid}"):
            if not any(h["candidateId"] == cid for h in st.session_state.hired):
                st.session_state.hired.append(candidate)
                save_hired()
                st.success(f"{cid} has been hired!")
            else:
                st.warning(f"{cid} is already hired.")

st.markdown("---")
# Shows hired candidates
st.subheader("Hired Candidates")
if st.session_state.hired:
    for h in st.session_state.hired:
        with st.expander(f"{cid} - View Resume"):
            st.subheader("Original Resume")
            st.text(original)
else:
    st.info("No candidates hired yet.")

if st.button("Wipe Hired Candidates"):
    st.session_state.hired = []
    save_json("hired.json", st.session_state.hired)


# -------------------
# Fairness Metrics Dashboard
# -------------------
st.markdown("---")
st.header("Fairness Metrics Dashboard")

total_resumes = len(candidates)
total_markers = sumtotal_markers = sum(c.get("markersRemoved", 0) for c in candidates)
avg_markers = total_markers / total_resumes if total_resumes > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Resumes Processed", total_resumes)
col2.metric("Total Identity Markers Removed", total_markers)
