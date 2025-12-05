from io import BytesIO
from pdfminer.high_level import extract_text
import os
import json
from app.core.logger import get_logger
logger = get_logger("file_upload_util")

DOCUMENTS_METADATA_FILE = "uploaded_documents.json"

def extract_text_from_pdf(file_bytes: bytes) -> str:
    with BytesIO(file_bytes) as pdf_stream:
        return extract_text(pdf_stream)
    
def load_documents_metadata():
    if not os.path.exists(DOCUMENTS_METADATA_FILE):
        return []
    try:
        with open(DOCUMENTS_METADATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in uploaded_documents.json — resetting file.")
        save_documents_metadata([])  # clear and reset
        return []


def save_documents_metadata(docs):
    with open(DOCUMENTS_METADATA_FILE, "w") as f:
        json.dump(docs, f, indent=2)


def flush_documents_metadata():
    try:
        save_documents_metadata([])
        logger.info("✅ uploaded_documents.json has been flushed.")
        return {"status": "success", "message": "Metadata file cleared."}
    except Exception as e:
        logger.error(f"❌ Failed to flush metadata file: {e}")
        return {"status": "error", "message": "Failed to clear metadata file."}