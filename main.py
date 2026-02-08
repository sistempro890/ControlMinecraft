import asyncio
from fastapi import FastAPI, UploadFile, File
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
import uvicorn

API_TOKEN = '8504711791:AAG6jdtS_iC0ujhrFBwkPyshqFDqpi6JAdY'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = FastAPI()

commands_storage = {} # {user_id: cmd}
status_storage = {}   # {user_id: text}

def get_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚀 Запустить всё"), KeyboardButton(text="🛑 Остановить всё")],
        [KeyboardButton(text="📸 Скриншот"), KeyboardButton(text="📊 Статус")]
    ], resize_keyboard=True)

@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    await m.answer(f"Твой ID: `{m.from_user.id}`\nВведи его в программе!", reply_markup=get_kb(), parse_mode="Markdown")

@dp.message()
async def handle_buttons(m: Message):
    uid = str(m.from_user.id)
    if m.text == "🚀 Запустить всё": commands_storage[uid] = "START"
    elif m.text == "🛑 Остановить всё": commands_storage[uid] = "STOP"
    elif m.text == "📸 Скриншот": commands_storage[uid] = "SCREENSHOT"
    elif m.text == "📊 Статус": commands_storage[uid] = "STATUS"
    await m.answer(f"Запрос {m.text} отправлен на ПК...")

# --- API ДЛЯ КЛИЕНТА ---
@app.get("/get_cmd/{user_id}")
async def get_cmd(user_id: str):
    cmd = commands_storage.get(user_id, "IDLE")
    commands_storage[user_id] = "IDLE"
    return {"cmd": cmd}

@app.post("/upload_screen/{user_id}")
async def upload_screen(user_id: str, file: UploadFile = File(...)):
    photo_bytes = await file.read()
    await bot.send_photo(chat_id=int(user_id), photo=BufferedInputFile(photo_bytes, filename="screen.png"), caption="📸 Скриншот с твоего ПК")
    return {"status": "ok"}

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    text = f"📊 Статус ПК:\nJava (Minecraft): {data['java']}\nPlayit: {data['playit']}"
    await bot.send_message(chat_id=int(user_id), text=text)
    return {"status": "ok"}

@app.on_event("startup")
async def startup(): asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
