import asyncio, time, os
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
pc_stats = {}
console_logs = {} # Храним последние 20 строк консоли для каждого юзера

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            :root { --primary: #00f2fe; --bg: #0f0f13; }
            body { background: var(--bg); color: white; font-family: 'Consolas', sans-serif; margin: 0; padding: 15px; }
            .card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 15px; }
            .badge { display: inline-block; padding: 5px 10px; border-radius: 8px; font-size: 10px; margin-bottom: 10px; font-weight: bold; }
            .online { background: #28a745; } .offline { background: #dc3545; }
            
            #console { 
                background: #000; border-radius: 10px; height: 200px; overflow-y: auto; 
                padding: 10px; font-size: 11px; color: #0f0; border: 1px solid #333; margin: 10px 0;
                white-space: pre-wrap;
            }
            
            .input-group { display: flex; gap: 5px; margin-top: 10px; }
            input { flex: 1; background: #1a1a1a; border: 1px solid #333; color: white; padding: 10px; border-radius: 8px; }
            .btn { background: var(--primary); color: #000; border: none; padding: 10px 15px; border-radius: 8px; font-weight: bold; }
            
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
            .stat { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; text-align: center; }
            .btn-red { background: #ff4d4d; color: white; width: 100%; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div class="card">
            <div id="m-status" class="badge offline">OFFLINE</div>
            <div class="grid">
                <div class="stat"><small>CPU</small><br><b id="s-cpu">0%</b></div>
                <div class="stat"><small>RAM</small><br><b id="s-ram">0%</b></div>
            </div>

            <div id="console">Загрузка консоли...</div>
            
            <div class="input-group">
                <input type="text" id="cmd-input" placeholder="Введите команду...">
                <button class="btn" onclick="sendTerminal()">SEND</button>
            </div>

            <div style="margin-top: 15px;">
                <button class="btn" style="width:100%; margin-bottom:5px;" onclick="sendCmd('START')">🚀 ЗАПУСТИТЬ СЕРВЕР</button>
                <button class="btn btn-red" onclick="sendCmd('STOP')">🛑 ВЫКЛЮЧИТЬ</button>
                <button class="btn" style="width:100%; background:#444; color:white; margin-top:5px;" onclick="sendCmd('SCREENSHOT')">📸 СКРИНШОТ</button>
            </div>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            const uid = tg.initDataUnsafe.user.id;

            async function refresh() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let d = await r.json();
                    document.getElementById('m-status').className = "badge " + (d.online ? "online" : "offline");
                    document.getElementById('m-status').innerText = d.online ? "ONLINE" : "OFFLINE";
                    document.getElementById('s-cpu').innerText = d.cpu + "%";
                    document.getElementById('s-ram').innerText = d.ram + "%";
                    document.getElementById('console').innerText = d.logs.join('\\n');
                    let c = document.getElementById('console');
                    c.scrollTop = c.scrollHeight;
                } catch(e) {}
            }

            function sendCmd(name) { fetch(`/send_from_web?user_id=${uid}&cmd=${name}`); }
            
            function sendTerminal() {
                let i = document.getElementById('cmd-input');
                fetch(`/send_from_web?user_id=${uid}&cmd=TERMINAL:${i.value}`);
                i.value = '';
            }

            setInterval(refresh, 2000);
        </script>
    </body>
    </html>
    """

@app.get("/get_pc_stats/{user_id}")
async def get_stats(user_id: str):
    stats = pc_stats.get(user_id, {"last_seen": 0})
    is_online = (time.time() - stats['last_seen']) < 10
    return {
        "online": is_online,
        "cpu": stats.get("cpu", 0),
        "ram": stats.get("ram", 0),
        "logs": console_logs.get(user_id, ["Консоль пуста"])
    }

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    pc_stats[user_id] = {
        "cpu": data.get("cpu", 0), "ram": data.get("ram", 0),
        "last_seen": time.time()
    }
    # Обновляем логи консоли (берем последние 20 строк)
    if "logs" in data:
        console_logs[user_id] = data["logs"][-20:]
    return {"ok": True}

@app.get("/send_from_web")
async def send_from_web(user_id: str, cmd: str):
    commands_storage[user_id] = cmd
    return {"ok": True}

@app.get("/get_cmd/{user_id}")
async def get_cmd(user_id: str):
    cmd = commands_storage.get(user_id, "IDLE")
    commands_storage[user_id] = "IDLE"
    return {"cmd": cmd}

# Бот и загрузка файлов
@app.post("/upload_plugin/{user_id}")
async def upload_plugin(user_id: str, file: UploadFile = File(...)):
    # Логика сохранения плагина в папку plugins на ПК (будет в клиенте)
    return {"status": "plugin_received"}

@app.post("/upload_screen/{user_id}")
async def upload_screen(user_id: str, file: UploadFile = File(...)):
    photo_bytes = await file.read()
    await bot.send_photo(chat_id=int(user_id), photo=BufferedInputFile(photo_bytes, filename="s.png"))
    return {"ok": True}

@dp.message(F.text == "/start")
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 КОНСОЛЬ И УПРАВЛЕНИЕ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]])
    await m.answer("Панель управления сервером готова:", reply_markup=kb)

async def run_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_up(): asyncio.create_task(run_bot())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
