from typing import Annotated
from fastapi import FastAPI, Form, UploadFile
from fastapi.responses import JSONResponse, FileResponse


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/upload/")
def get_lyrics(
    audio: UploadFile,
    lyrics: Annotated[str, Form()],
):
    
    if audio.content_type not in ["audio/mpeg", "audio/wav"]:
        return JSONResponse(content={"error": "Invalid file type. Only MP3 and WAV are supported."}, status_code=400)

    return JSONResponse(content={"message": "File Received"}, status_code=200)