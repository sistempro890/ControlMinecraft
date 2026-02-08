import asyncio
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
import uvicorn

API_TOKEN = '8504711791:AAG6jdtS_iC0ujhrFBwkPyshqFDqpi6JAdY'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = FastAPI()

commands_storage = {}

# --- HTML ИНТЕРФЕЙС (Web App) ---
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { background: #1a1a1a; color: white; font-family: sans-serif; text-align: center; padding: 20px; }
            button { 
                width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 10px; 
                font-size: 16px; font-weight: bold; cursor: pointer; color: white;
            }
            .btn-start { background: #28a745; }
            .btn-stop { background: #dc3545; }
            .btn-other { background: #007bff; }
        </style>
    </head>
    <body>
        <h2>MC SERVER CONTROL</h2>
        <p id="user-id"></p>
        <button class="btn-start" onclick="sendCmd('START')">🚀 ЗАПУСТИТЬ</button>
        <button class="btn-stop" onclick="sendCmd('STOP')">🛑 ОСТАНОВИТЬ</button>
        <button class="btn-other" onclick="sendCmd('SCREENSHOT')">📸 СКРИНШОТ</button>
        <button class="btn-other" onclick="sendCmd('STATUS')">📊 СТАТУС</button>

        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            document.getElementById('user-id').innerText = "ID: " + tg.initDataUnsafe.user.id;

            function sendCmd(name) {
                fetch(`/send_from_web?user_id=${tg.initDataUnsafe.user.id}&cmd=${name}`);
                tg.HapticFeedback.notificationOccurred('success');
            }
        </script>
    </body>
    </html>
    """

# API для Web App, чтобы он мог передать команду на сервер
@app.get("/send_from_web")
async def send_from_web(user_id: str, cmd: str):
    commands_storage[user_id] = cmd
    return {"ok": True}

# Остальное API (get_cmd, upload_screen и т.д.) остается как было...
@app.get("/get_cmd/{user_id}")
async def get_cmd(user_id: str):
    cmd = commands_storage.get(user_id, "IDLE")
    commands_storage[user_id] = "IDLE"
    return {"cmd": cmd}

@app.post("/upload_screen/{user_id}")
async def upload_screen(user_id: str, file: UploadFile = File(...)):
    photo_bytes = await file.read()
    await bot.send_photo(chat_id=int(user_id), photo=BufferedInputFile(photo_bytes, filename="s.png"))
    return {"ok": True}

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    text = f"📊 СТАТУС:\nJava: {data['java']}\nPlayit: {data['playit']}"
    await bot.send_message(chat_id=int(user_id), text=text)
    return {"ok": True}

@dp.message(F.text == "/start")
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 УПРАВЛЕНИЕ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]])
    await m.answer("Нажми на кнопку ниже, чтобы открыть панель управления:", reply_markup=kb)

async def run_bot():
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_up():
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
