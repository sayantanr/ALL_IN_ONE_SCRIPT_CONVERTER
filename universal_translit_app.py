import io, os, re, zipfile, tempfile, threading
from typing import List, Dict
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
from flask import Flask, request, send_file, jsonify
import streamlit as st
from PIL import Image
from pdf2image import convert_from_bytes
import pytesseract
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from langdetect import detect as lang_detect

# ---------- SCRIPT DETECTION ----------
SCRIPT_RANGES = [
    ("Devanagari", (0x0900, 0x097F)),
    ("Bengali", (0x0980, 0x09FF)),
    ("Gujarati", (0x0A80, 0x0AFF)),
    ("Oriya", (0x0B00, 0x0B7F)),
    ("Tamil", (0x0B80, 0x0BFF)),
    ("Telugu", (0x0C00, 0x0C7F)),
    ("Kannada", (0x0C80, 0x0CFF)),
    ("Malayalam", (0x0D00, 0x0D7F)),
    ("Latin", (0x0041, 0x007A)),
    ("Arabic", (0x0600, 0x06FF)),
    ("Hebrew", (0x0590, 0x05FF)),
]

SANSCRIPT_MAP = {k: getattr(sanscript, k) for k in dir(sanscript) if k.isupper()}

def detect_script(text: str) -> str:
    counts = {}
    for ch in text:
        cp = ord(ch)
        for name, (lo, hi) in SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[name] = counts.get(name, 0) + 1
    return max(counts, key=counts.get) if counts else "Unknown"

def guess_input_scheme(text: str) -> str:
    iast = re.compile(r"[āīūṛṝṅñṭḍṇśṣḥṃĀĪŪṚṜḶḸ]")
    if iast.search(text):
        return "IAST"
    scr = detect_script(text)
    if scr == "Devanagari": return "DEVANAGARI"
    if scr == "Bengali": return "BENGALI"
    return "ITRANS"

# ---------- OCR ----------
def ocr_image_bytes(img_bytes, lang="eng"):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return pytesseract.image_to_string(img, lang=lang)

def ocr_pdf_bytes(pdf_bytes, lang="eng"):
    images = convert_from_bytes(pdf_bytes)
    return "\n".join([pytesseract.image_to_string(img, lang=lang) for img in images])

# ---------- TRANSLITERATION ----------
def transliterate_text(text, src, tgt):
    try:
        return transliterate(text, SANSCRIPT_MAP[src], SANSCRIPT_MAP[tgt])
    except Exception as e:
        return f"[ERROR] {e}"

# ---------- ZIP BATCH ----------
def make_zip(file_map, src, tgts):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in file_map.items():
            for tgt in tgts:
                out = transliterate_text(text, src, tgt)
                z.writestr(f"{os.path.splitext(name)[0]}__{tgt}.txt", out.encode("utf-8"))
    mem.seek(0)
    return mem

# ---------- FASTAPI ----------
fastapi_app = FastAPI(title="Universal Transliteration API")

@fastapi_app.post("/transliterate")
async def transliterate_api(
    file: UploadFile = File(...),
    tgt: List[str] = Form(...),
    src: str = Form("Auto"),
    tess_lang: str = Form("eng"),
):
    data = await file.read()
    name = file.filename
    if name.endswith(".txt"):
        try: text = data.decode("utf-8")
        except: text = data.decode("latin-1")
    elif name.endswith(".pdf"):
        text = ocr_pdf_bytes(data, tess_lang)
    else:
        text = ocr_image_bytes(data, tess_lang)
    src_scheme = src if src != "Auto" else guess_input_scheme(text)
    results = {t: transliterate_text(text, src_scheme, t) for t in tgt}
    if len(tgt) == 1:
        return PlainTextResponse(results[tgt[0]])
    z = make_zip({name: text}, src_scheme, tgt)
    return StreamingResponse(z, media_type="application/zip")

# ---------- FLASK ----------
flask_app = Flask(__name__)

@flask_app.route("/transliterate", methods=["POST"])
def transliterate_flask():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    tgt = request.form.getlist("tgt")
    src = request.form.get("src", "Auto")
    tess_lang = request.form.get("tess_lang", "eng")
    data = f.read()
    name = f.filename
    if name.endswith(".txt"):
        try: text = data.decode("utf-8")
        except: text = data.decode("latin-1")
    elif name.endswith(".pdf"):
        text = ocr_pdf_bytes(data, tess_lang)
    else:
        text = ocr_image_bytes(data, tess_lang)
    src_scheme = src if src != "Auto" else guess_input_scheme(text)
    results = {t: transliterate_text(text, src_scheme, t) for t in tgt}
    if len(tgt) == 1:
        return results[tgt[0]]
    z = make_zip({name: text}, src_scheme, tgt)
    return send_file(z, mimetype="application/zip", as_attachment=True, download_name="outputs.zip")

# ---------- STREAMLIT ----------
def run_streamlit():
    st.set_page_config(page_title="Universal Transliteration Suite", layout="wide")
    st.title("🌀 Universal Transliteration Suite")
    st.write("Auto OCR + Transliteration using **indic-transliteration**")

    tess_lang = st.sidebar.text_input("Tesseract language", "eng")
    uploaded_files = st.file_uploader("Upload files (.txt, .pdf, .png, .jpg)", accept_multiple_files=True)
    src_scheme = st.selectbox("Source Scheme", ["Auto"] + sorted(SANSCRIPT_MAP.keys()))
    tgt_schemes = st.multiselect("Target Schemes", ["DEVANAGARI","BENGALI","IAST","ITRANS","SLP1","VELTHUIS"], default=["DEVANAGARI","BENGALI"])
    
    if uploaded_files and st.button("Convert"):
        outputs = {}
        for f in uploaded_files:
            name = f.name
            data = f.read()
            if name.endswith(".txt"):
                try: text = data.decode("utf-8")
                except: text = data.decode("latin-1")
            elif name.endswith(".pdf"):
                st.info(f"OCR on {name}")
                text = ocr_pdf_bytes(data, tess_lang)
            else:
                st.info(f"OCR on {name}")
                text = ocr_image_bytes(data, tess_lang)
            src_used = src_scheme if src_scheme != "Auto" else guess_input_scheme(text)
            outputs[name] = text
            st.write(f"**{name}** detected as {detect_script(text)} ({src_used})")
            for tgt in tgt_schemes:
                result = transliterate_text(text, src_used, tgt)
                st.download_button(f"Download {name}__{tgt}.txt", result.encode("utf-8"), f"{name}__{tgt}.txt")
                st.text_area(f"{name}_{tgt}", result[:1000], height=150)

        if len(uploaded_files) > 1:
            z = make_zip(outputs, src_scheme if src_scheme != "Auto" else "ITRANS", tgt_schemes)
            st.download_button("⬇️ Download All (ZIP)", data=z, file_name="outputs.zip", mime="application/zip")

# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    import argparse, uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["streamlit", "fastapi", "flask"], default="streamlit")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()

    if args.mode == "streamlit":
        import subprocess
        subprocess.run(["streamlit", "run", __file__])
    elif args.mode == "fastapi":
        uvicorn.run(fastapi_app, host="0.0.0.0", port=args.port)
    elif args.mode == "flask":
        flask_app.run(host="0.0.0.0", port=args.port)
