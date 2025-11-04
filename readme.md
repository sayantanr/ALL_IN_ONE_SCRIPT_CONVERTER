🔧 Setup

Install required packages:

pip install streamlit fastapi flask uvicorn python-multipart pdf2image pytesseract Pillow indic-transliteration langdetect tqdm
System requirements (for OCR):
# Ubuntu/Debian
sudo apt install tesseract-ocr poppler-utils

# Optional (better OCR for Indian scripts)
sudo apt install tesseract-ocr-hin tesseract-ocr-ben

******how to run **

| Mode              | Command                                                       | Access URL                                                                 |
| ----------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Streamlit GUI** | `python universal_translit_app.py --mode streamlit`           | [http://localhost:8501](http://localhost:8501)                             |
| **FastAPI API**   | `python universal_translit_app.py --mode fastapi --port 8000` | [http://localhost:8000/docs](http://localhost:8000/docs)                   |
| **Flask API**     | `python universal_translit_app.py --mode flask --port 5000`   | [http://localhost:5000/transliterate](http://localhost:5000/transliterate) |

| Feature                   | Description                                                                            |
| ------------------------- | -------------------------------------------------------------------------------------- |
| OCR                       | Auto OCR from image/PDF (Tesseract)                                                    |
| File Types                | `.txt`, `.pdf`, `.png`, `.jpg`, `.jpeg`                                                |
| Auto Script Detection     | Unicode-range heuristics                                                               |
| Auto Input Scheme         | Detects IAST, ITRANS, Devanagari, Bengali                                              |
| Multi-file Batch          | Multiple files, ZIP download                                                           |
| Output                    | `.txt` or ZIP                                                                          |
| Multiple Backends         | Streamlit GUI, FastAPI, Flask                                                          |
| Transliteration           | Using `indic-transliteration` (IAST, ITRANS, SLP1, VELTHUIS, Devanagari, Bengali etc.) |
| Configurable OCR language | via sidebar                                                                            |
