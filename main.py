import asyncio
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import uvicorn

# --- НАСТРОЙКИ ---
API_TOKEN = '8504711791:AAG6jdtS_iC0ujhrFBwkPyshqFDqpi6JAdY'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = FastAPI()

# База данных в памяти: { "ID_пользователя": "команда" }
commands_storage = {}

def get_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚀 Запустить всё"), KeyboardButton(text="🛑 Остановить всё")],
        [KeyboardButton(text="📸 Скриншот"), KeyboardButton(text="📊 Статус")]
    ], resize_keyboard=True)

@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    await m.answer(f"Привет! Твой ID: `{m.from_user.id}`\nВведи его в программе на ПК.", 
                   parse_mode="Markdown", reply_markup=get_kb())

@dp.message()
async def handle_buttons(m: Message):
    user_id = str(m.from_user.id)
    if m.text == "🚀 Запустить всё":
        commands_storage[user_id] = "START"
        await m.answer("Сигнал запуска отправлен!")
    elif m.text == "🛑 Остановить всё":
        commands_storage[user_id] = "STOP"
        await m.answer("Сигнал остановки отправлен!")
    elif m.text == "📸 Скриншот":
        commands_storage[user_id] = "SCREENSHOT"
        await m.answer("Запрос скриншота отправлен...")

# API для программы на ПК
@app.get("/get_cmd/{user_id}")
async def get_cmd(user_id: str):
    cmd = commands_storage.get(user_id, "IDLE")
    commands_storage[user_id] = "IDLE" # Сбрасываем после прочтения
    return {"cmd": cmd}

# Запуск бота и API одновременно
async def run_bot():
    await dp.start_polling(bot)

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
