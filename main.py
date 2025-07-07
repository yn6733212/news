import os
import datetime
import asyncio
import base64
import subprocess
import requests
from google.genai import Client
from google.genai.types import (
    GenerateContentConfig,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig
)
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest

# =========== הגדרות קבועות ===========
api_id = 24005590
api_hash = "bb3d1bff42183fe39478ccf98d729cc6"
channel_username = "calcalistcapitalmarkets"
session_name = "session"

YEMOT_USERNAME = "0733181201"
YEMOT_PASSWORD = "6714453"
YEMOT_TOKEN = f"{YEMOT_USERNAME}:{YEMOT_PASSWORD}"
YEMOT_UPLOAD_URL = "https://www.call2all.co.il/ym/api/UploadFile"
TARGET_FOLDER = "ivr2:/4"

GEMINI_KEYS = [
    "AIzaSyCNjsz1g2NPCxsfWyBfTmpD97bpSRA1qPA",
    "AIzaSyBu_hgfv5YR9ZbJ4FK3-XmTPwp4ZkIGk38",
    "AIzaSyD0Yi5Nl3whDBTlaCo-95EJNEertRPX-rA"
]

VOICE_NAME = "Zubenelgenubi"
OUTPUT_FOLDER = "audio"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
FFMPEG = "ffmpeg"

# =========== שליפת הודעה אחרונה ===========
async def get_latest_message():
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise Exception("❌ לא מחובר לטלגרם – הפעל מקומית פעם אחת ליצירת session")
    result = await client(GetHistoryRequest(
        peer=channel_username,
        limit=1,
        offset_date=None,
        offset_id=0,
        max_id=0,
        min_id=0,
        add_offset=0,
        hash=0
    ))
    await client.disconnect()
    return result.messages[0].message.strip()

# =========== יצירת שם קובץ ===========
def get_next_filename():
    existing = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".wav")]
    numbers = [int(f.split(".")[0]) for f in existing if f.split(".")[0].isdigit()]
    next_number = max(numbers) + 1 if numbers else 0
    return os.path.join(OUTPUT_FOLDER, f"{next_number:03}.wav")

# =========== שמירת RAW ===========
def save_raw_pcm(path, data):
    with open(path, "wb") as f:
        f.write(data)

# =========== המרה עם ffmpeg ===========
def convert_raw_to_wav(raw_path, wav_path):
    subprocess.run([
        FFMPEG,
        "-f", "s16le",
        "-ar", "24000",
        "-ac", "1",
        "-i", raw_path,
        "-ar", "8000",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        wav_path
    ], check=True)

# =========== יצירת שמע ===========
def create_audio(text, wav_path):
    for api_key in GEMINI_KEYS:
        try:
            client = Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=text,
                config=GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=SpeechConfig(
                        voice_config=VoiceConfig(
                            prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=VOICE_NAME)
                        )
                    )
                )
            )
            audio_base64 = response.candidates[0].content.parts[0].inline_data.data
            pcm = base64.b64decode(audio_base64)
            raw_path = wav_path.replace(".wav", ".raw")
            save_raw_pcm(raw_path, pcm)
            convert_raw_to_wav(raw_path, wav_path)
            print(f"✅ קובץ נוצר: {wav_path}")
            return True
        except Exception as e:
            print(f"⚠️ שגיאה עם מפתח {api_key[:15]}...: {e}")
    return False

# =========== העלאה לימות ===========
def upload_to_yemot(filepath):
    with open(filepath, "rb") as f:
        files = {
            "token": (None, YEMOT_TOKEN),
            "path": (None, f"{TARGET_FOLDER}/{os.path.basename(filepath)}"),
            "file": (filepath, f, "audio/wav")
        }
        response = requests.post(YEMOT_UPLOAD_URL, files=files)
        print("📤 תגובת ימות:", response.text)

# =========== MAIN ===========
async def main():
    try:
        print("🔍 הודעה מטלגרם...")
        msg = await get_latest_message()

        now = datetime.datetime.now()
        weekday = {
            "Sunday": "יום ראשון", "Monday": "יום שני", "Tuesday": "יום שלישי",
            "Wednesday": "יום רביעי", "Thursday": "יום חמישי",
            "Friday": "יום שישי", "Saturday": "שבת"
        }[now.strftime("%A")]
        time_str = now.strftime("%H:%M").replace(":", " ו")
        intro = f"{weekday}, השעה {time_str}.\n"
        full_text = intro + msg

        filename = get_next_filename()
        print("🎤 יוצר קובץ קול עם Gemini...")
        if create_audio(full_text, filename):
            print("📄 הטקסט שהוקרא:\n" + full_text)
            print("📤 מעלה לימות...")
            upload_to_yemot(filename)
        else:
            print("❌ יצירת קול נכשלה.")
    except Exception as e:
        print("🚨 שגיאה:", e)

# =========== הרצה ===========
if __name__ == "__main__":
    asyncio.run(main())
