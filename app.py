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
# Path is where you want the data to be saved
# Data is what you want to save
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

    def escape(s):
        return re.escape(s)

    if name:
        result = re.sub(escape(name), "[hidden name]", result, flags=re.IGNORECASE)
    if city:
        result = re.sub(escape(city), "[hidden location]", result, flags=re.IGNORECASE)

    result = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
                    "[hidden email]", result, flags=re.IGNORECASE)
    result = re.sub(r"(\+?\d{1,2}[\s.-]?)?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
                    "[hidden phone]", result)
    result = re.sub(r"\b\d{1,5}\s+\w+(?:\s+\w+){0,3}\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b",
                    "[hidden address]", result, flags=re.IGNORECASE)

    school_terms = ["High School", "Middle School", "Elementary School",
                    "University", "College", "Academy", "Institute"]
    for term in school_terms:
        result = re.sub(term, "[hidden school]", result, flags=re.IGNORECASE)

    result = re.sub(r"https?:\/\/\S*linkedin\.com\S*", "[hidden profile link]", result, flags=re.IGNORECASE)
    result = re.sub(r"\b\d{5}(?:-\d{4})?\b", "[hidden zipcode]", result)

    return result

def clean_extracted_text(text):
    text = re.sub(r"\(cid:\d+\)", "• ", text)
    text = re.sub(r"(\d)n(\d)", r"\1-\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

def generate_candidate_id():
    return "Candidate #" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

# -------------------
# Employee Portal
# -------------------
# Remember: All data entered will be saved to the local resumes.json file, not implementing wipe button YET
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
        with pdfplumber.open(uploaded_pdf) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        text = clean_extracted_text(text)
        st.subheader("Original Extracted Text")
        st.text_area("Original Resume", text, height=300)

        candidate_id = generate_candidate_id()
        scrubbed = scrub_resume(text, name, city)

        st.subheader(f"Anonymized Resume ({candidate_id})")
        st.text_area("Scrubbed Resume", scrubbed, height=300)

        # Save to resumes.json
        entry = {
            "candidateId": candidate_id,
            "originalText": text,
            "scrubbedText": scrubbed
        }

        resumes_JSON = "resumes.json"
        data = load_json(resumes_JSON)
        data.append(entry)
        save_json(resumes_JSON, data)

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

# Each dropdown has a candidate to hire and the hire button, only scrubbed text is visible
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

# Wipes all hired candidates, 1st press updates, 2nd press shows new
if st.button("Wipe Hired Candidates"):
    st.session_state.hired = []
    save_json("hired.json", st.session_state.hired)
