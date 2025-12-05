from fastapi import Response

def health_check():
    return {"status": "ok"}