import streamlit as st
import pdfplumber
import re
import random
import string
import json
import os

st.set_page_config(page_title="FairHire Resume Scrubber", layout="centered")
st.markdown("---")
#scrub function
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
#id gen
def generate_candidate_id():
    return "Candidate #" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

#streamlit web ui
st.title("FairHire Resume Scrubber (PDF Prototype)")
st.caption("Prototype that removes race-linked identity markers from resumes.")
st.markdown("---")
uploaded_pdf = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
st.markdown("---")
name = st.text_input("Your full name (as appears on resume)")
city = st.text_input("Your city (as appears on resume)")
st.markdown("---")
if uploaded_pdf:
    st.success("PDF uploaded successfully.")

if st.button("Extract & Scrub Resume"):
    if uploaded_pdf:
        with pdfplumber.open(uploaded_pdf) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        text = clean_extracted_text(text)

        st.subheader("Original Extracted Text")
        st.text_area("Original Resume", text, height=300)

        candidate_id = generate_candidate_id()
        scrubbed = scrub_resume(text, name, city)

        st.subheader(f"Anonymized Resume ({candidate_id})")
        st.text_area("Scrubbed Resume", scrubbed, height=300)

        # JSON
        entry = {
            "candidateId": candidate_id,
            "originalText": text,
            "scrubbedText": scrubbed
        }

        if not os.path.exists("resumes.json"):
            with open("resumes.json", "w") as f:
                json.dump([], f)

        with open("resumes.json", "r") as f:
            data = json.load(f)

        data.append(entry)

        with open("resumes.json", "w") as f:
            json.dump(data, f, indent=2)

        st.success(f"Saved to database as {candidate_id}!")
    else:
        st.error("Please upload a PDF first.")
