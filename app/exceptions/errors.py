from fastapi import status
from fastapi.responses import JSONResponse

class ApplicationException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code

    def to_response(self):
        return JSONResponse(
            status_code=self.status_code,
            content={"error": self.message}
        )