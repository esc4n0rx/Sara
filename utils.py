import os
import tempfile

def save_audio_file(audio_data: bytes, extension=".m4a") -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
        temp.write(audio_data)
        return temp.name
