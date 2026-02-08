import asyncio, time, os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
import uvicorn
from contextlib import asynccontextmanager

# --- НАСТРОЙКИ ---
API_TOKEN = '8504711791:AAG6jdtS_iC0ujhrFBwkPyshqFDqpi6JAdY'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

commands_storage = {}
pc_stats = {}
console_logs = {}

# Используем современный Lifespan вместо on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot))
    print("Бот запущен!")
    yield
    # Shutdown: остановка
    polling_task.cancel()
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

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
            body { background: var(--bg); color: white; font-family: sans-serif; margin: 0; padding: 15px; text-align: center; }
            .card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 20px; }
            #console { 
                background: #000; border-radius: 10px; height: 180px; overflow-y: auto; 
                padding: 10px; font-size: 11px; color: #0f0; text-align: left;
                border: 1px solid #333; margin: 15px 0; font-family: monospace;
            }
            .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
            .stat-item { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; }
            .btn { 
                width: 100%; padding: 15px; margin: 5px 0; border: none; border-radius: 12px; 
                font-weight: bold; font-size: 14px; cursor: pointer; transition: 0.2s;
            }
            .btn-main { background: var(--primary); color: black; }
            .btn-danger { background: #ff4d4d; color: white; }
            .btn:disabled { opacity: 0.3; }
            input { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #333; background: #1a1a1a; color: white; box-sizing: border-box; }
        </style>
    </head>
    <body>
        <div class="card">
            <div id="status" style="color: #ff4d4d; font-weight: bold; margin-bottom: 10px;">● PC OFFLINE</div>
            
            <div class="stat-grid">
                <div class="stat-item"><small>CPU</small><br><b id="cpu">0%</b></div>
                <div class="stat-item"><small>RAM</small><br><b id="ram">0%</b></div>
            </div>

            <div id="console">Консоль ожидает подключения...</div>
            
            <input type="text" id="cmd-in" placeholder="Введите команду в консоль...">
            <button class="btn btn-main" style="margin-top:10px;" onclick="sendTerm()">ОТПРАВИТЬ КОМАНДУ</button>
            
            <hr style="opacity: 0.1; margin: 20px 0;">
            
            <button id="b-start" class="btn btn-main" onclick="sendCmd('START')">🚀 ЗАПУСТИТЬ СЕРВЕР</button>
            <button id="b-stop" class="btn btn-danger" onclick="sendCmd('STOP')">🛑 ОСТАНОВИТЬ</button>
            <button id="b-screen" class="btn" style="background:#333; color:white;" onclick="sendCmd('SCREENSHOT')">📸 СКРИНШОТ</button>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            const uid = tg.initDataUnsafe.user.id;

            async function refresh() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let d = await r.json();
                    
                    document.getElementById('status').innerText = d.online ? "● PC ONLINE" : "● PC OFFLINE";
                    document.getElementById('status').style.color = d.online ? "#28a745" : "#ff4d4d";
                    document.getElementById('cpu').innerText = d.cpu + "%";
                    document.getElementById('ram').innerText = d.ram + "%";
                    
                    if(d.logs.length > 0) {
                        document.getElementById('console').innerText = d.logs.join('\\n');
                        let c = document.getElementById('console');
                        c.scrollTop = c.scrollHeight;
                    }

                    const btns = [document.getElementById('b-start'), document.getElementById('b-stop'), document.getElementById('b-screen')];
                    btns.forEach(b => b.disabled = !d.online);
                } catch(e) {}
            }

            function sendCmd(c) { fetch(`/send_from_web?user_id=${uid}&cmd=${c}`); tg.HapticFeedback.impactOccurred('medium'); }
            function sendTerm() {
                let i = document.getElementById('cmd-in');
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
        "logs": console_logs.get(user_id, ["Ожидание данных..."])
    }

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    pc_stats[user_id] = {
        "cpu": data.get("cpu", 0),
        "ram": data.get("ram", 0),
        "last_seen": time.time()
    }
    if "logs" in data:
        console_logs[user_id] = data["logs"]
    return {"ok": True}

@app.get("/send_from_web")
async def send_from_web(user_id: str, cmd: str):
    commands_storage[user_id] = cmd
    return {"ok": True}

@app.get("/get_cmd/{user_id}")
async def get_cmd(user_id: str):
    if user_id in pc_stats: pc_stats[user_id]["last_seen"] = time.time()
    cmd = commands_storage.get(user_id, "IDLE")
    commands_storage[user_id] = "IDLE"
    return {"cmd": cmd}

@app.post("/upload_screen/{user_id}")
async def upload_screen(user_id: str, file: UploadFile = File(...)):
    photo_bytes = await file.read()
    await bot.send_photo(chat_id=int(user_id), photo=BufferedInputFile(photo_bytes, filename="s.png"))
    return {"ok": True}

@dp.message(F.text == "/start")
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 ОТКРЫТЬ КОНСОЛЬ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]])
    await m.answer("Панель управления готова:", reply_markup=kb)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
