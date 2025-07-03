import os
import time
import requests
from bs4 import BeautifulSoup
from edge_tts import Communicate
from requests_toolbelt.multipart.encoder import MultipartEncoder
import subprocess
import urllib.request
import tarfile
import re
import asyncio
from datetime import datetime
import pytz

# ⚙️ פרטי התחברות למערכת ימות המשיח
USERNAME = "0733181201"
PASSWORD = "6714453"
TOKEN = f"{USERNAME}:{PASSWORD}"
UPLOAD_PATH_PREFIX = "ivr2:/*/" # השלוחה *

# 🧾 שמות קבצים
MP3_FILE = "news.mp3"
WAV_FILE_TEMPLATE = "{:03}.wav"  # מספור בלבד: 000.wav, 001.wav וכו'
FFMPEG_PATH = "./bin/ffmpeg"

# ✅ הורדת ffmpeg אם לא קיים
def ensure_ffmpeg():
    if not os.path.exists(FFMPEG_PATH):
        print("⬇️ מוריד ffmpeg...")
        os.makedirs("bin", exist_ok=True)
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        archive_path = "bin/ffmpeg.tar.xz"
        urllib.request.urlretrieve(url, archive_path)
        with tarfile.open(archive_path) as tar:
            for member in tar.getmembers():
                if os.path.basename(member.name) == "ffmpeg":
                    member.name = "ffmpeg"
                    tar.extract(member, path="bin")
        os.chmod(FFMPEG_PATH, 0o755)

# ⏰ השגת השעה לפי שעון השרת
def get_server_time():
    now = datetime.now()
    return now.strftime("%H:%M")

# 🌐 שליפת ההודעה האחרונה מהערוץ
def get_last_telegram_message(channel_username):
    url = f"https://t.me/s/{channel_username}"
    response = requests.get(url, verify=False)
    if response.status_code != 200:
        print("❌ שגיאה בגישה לערוץ.")
        return None
    soup = BeautifulSoup(response.text, 'html.parser')
    messages = soup.find_all('div', class_='tgme_widget_message_text')
    if not messages:
        print("❌ לא נמצאו הודעות.")
        return None
    return messages[-1].get_text(strip=True)

# 🧠 הפקת קול
async def create_voice(text):
    communicate = Communicate(text=text, voice="he-IL-AvriNeural")
    await communicate.save(MP3_FILE)

# 🔄 המרה ל־WAV
def convert_to_wav(wav_filename):
    subprocess.run([FFMPEG_PATH, "-y", "-i", MP3_FILE, "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le", wav_filename])

# ⬆️ העלאה לימות המשיח
def upload_to_yemot(wav_filename):
    with open(wav_filename, 'rb') as f:
        m = MultipartEncoder(
            fields={
                'token': TOKEN,
                'path': UPLOAD_PATH_PREFIX + os.path.basename(wav_filename),
                'message': 'uploading',
                'file': (os.path.basename(wav_filename), f, 'audio/wav')
            }
        )
        response = requests.post('https://www.call2all.co.il/ym/api/UploadFile', data=m, headers={'Content-Type': m.content_type})
        print("📤 הועלה לימות המשיח:", response.json())

# 🧮 מציאת מספר קובץ פנוי
def get_next_filename():
    i = 0
    while True:
        filename = WAV_FILE_TEMPLATE.format(i)
        if not os.path.exists(filename):
            return filename
        i += 1

# 🚀 פונקציה ראשית לביצוע חד פעמי
def run_once():
    ensure_ffmpeg()
    print("\n🕒 בודק הודעות חדשות...")
    try:
        current = get_last_telegram_message("bullstreets_calcalist")
        if current:
            print("🆕 הודעה נמצאה!")
            print("📄 תוכן:", current)

            # הוספת שעה וטקסט פתיחה
            time_prefix = f"בורסה פון השעה {get_server_time()}. "
            full_text = time_prefix + current

            asyncio.run(create_voice(full_text))
            wav_file = get_next_filename()
            convert_to_wav(wav_file)
            upload_to_yemot(wav_file)
        else:
            print("ℹ️ לא נמצאו הודעות חדשות או שהערוץ ריק.")
    except Exception as e:
        print("❌ שגיאה:", e)

if __name__ == "__main__":
    run_once()
