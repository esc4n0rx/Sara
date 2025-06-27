import os
from groq import Groq

def transcribe_audio(audio_path: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    with open(audio_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(audio_path, file.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json"
        )
    return transcription.text
