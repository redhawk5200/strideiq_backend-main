import json
from pathlib import Path

STATUS_FILE = Path("upload_status.json")

def _load_status():
    if not STATUS_FILE.exists():
        return {}
    with open(STATUS_FILE, "r") as f:
        return json.load(f)

def _save_status(data):
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def init_status(file_name: str, status: str):
    data = _load_status()
    data[file_name] = status
    _save_status(data)

def update_status(file_name: str, status: str):
    data = _load_status()
    data[file_name] = status
    _save_status(data)

def get_status(file_name: str) -> str:
    data = _load_status()
    return data.get(file_name, "not_found")