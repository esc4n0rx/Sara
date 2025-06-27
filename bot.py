import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from whisper_handler import transcribe_audio
from llm_handler import interpret_command
from utils import save_audio_file

load_dotenv()

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.voice.file_id)
    audio_data = await file.download_as_bytearray()
    audio_path = save_audio_file(audio_data, ".m4a")

    await update.message.reply_text("🎙 Transcrevendo seu áudio...")

    text = transcribe_audio(audio_path)
    await update.message.reply_text(f"📝 Transcrição: {text}")

    await update.message.reply_text("🤔 Interpretando comando com Sara...")

    url = interpret_command(text)

    await update.message.reply_text(f"🔗 Toque no link para criar o lembrete:\n{url}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling()

if __name__ == "__main__":
    main()
