import asyncio, time
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
pc_stats = {} # Храним статус: {"user_id": {"java": "❌", "playit": "❌", "last_seen": 0}}

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { 
                background: linear-gradient(135deg, #1e1e2f 0%, #111119 100%); 
                color: white; font-family: 'Segoe UI', sans-serif; 
                display: flex; flex-direction: column; align-items: center; 
                min-height: 100vh; margin: 0; overflow: hidden;
            }
            .card {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border-radius: 20px; padding: 25px; margin-top: 30px;
                width: 85%; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.1);
                animation: fadeIn 0.8s ease;
            }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
            
            .status-badge {
                padding: 8px 15px; border-radius: 50px; font-size: 12px; font-weight: bold;
                text-transform: uppercase; margin-bottom: 20px; display: inline-block;
            }
            .online { background: rgba(40, 167, 69, 0.2); color: #28a745; border: 1px solid #28a745; }
            .offline { background: rgba(220, 53, 69, 0.2); color: #dc3545; border: 1px solid #dc3545; }

            .btn {
                width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 12px;
                font-size: 16px; font-weight: 600; cursor: pointer; transition: 0.3s;
                display: flex; align-items: center; justify-content: center; gap: 10px;
            }
            .btn:active { transform: scale(0.95); }
            .btn:disabled { opacity: 0.5; cursor: not-allowed; filter: grayscale(1); }
            
            .btn-start { background: linear-gradient(90deg, #28a745, #85d03a); color: white; }
            .btn-stop { background: linear-gradient(90deg, #cb2d3e, #ef473a); color: white; }
            .btn-action { background: rgba(255,255,255,0.1); color: white; }
            
            .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
            .stat-item { background: rgba(0,0,0,0.2); padding: 10px; border-radius: 10px; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="card">
            <div id="status-marker" class="status-badge offline">Checking...</div>
            <h2 style="margin: 0; font-size: 24px;">Server Panel</h2>
            <p style="color: #aaa; font-size: 14px;">Remote Cloud Control</p>
            
            <div class="stats-grid">
                <div class="stat-item">Minecraft: <span id="stat-java">❓</span></div>
                <div class="stat-item">Network: <span id="stat-net">❓</span></div>
            </div>

            <div style="margin-top: 25px;">
                <button id="b1" class="btn btn-start" onclick="sendCmd('START')">🚀 START SERVER</button>
                <button id="b2" class="btn btn-stop" onclick="sendCmd('STOP')">🛑 TERMINATE</button>
                <button id="b3" class="btn btn-action" onclick="sendCmd('SCREENSHOT')">📸 TAKE SCREENSHOT</button>
            </div>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            const uid = tg.initDataUnsafe.user.id;

            async function updateStatus() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let data = await r.json();
                    
                    const marker = document.getElementById('status-marker');
                    const btns = [document.getElementById('b1'), document.getElementById('b2'), document.getElementById('b3')];
                    
                    if (data.online) {
                        marker.innerText = "● PC CONNECTED";
                        marker.className = "status-badge online";
                        btns.forEach(b => b.disabled = false);
                        document.getElementById('stat-java').innerText = data.java;
                        document.getElementById('stat-net').innerText = data.playit;
                    } else {
                        marker.innerText = "● PC OFFLINE";
                        marker.className = "status-badge offline";
                        btns.forEach(b => b.disabled = true);
                    }
                } catch(e) {}
            }

            function sendCmd(name) {
                fetch(`/send_from_web?user_id=${uid}&cmd=${name}`);
                tg.HapticFeedback.impactOccurred('medium');
            }

            setInterval(updateStatus, 2000);
            updateStatus();
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
        "java": stats.get("java", "❌"),
        "playit": stats.get("playit", "❌")
    }

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    pc_stats[user_id] = {
        "java": data['java'],
        "playit": data['playit'],
        "last_seen": time.time()
    }
    return {"ok": True}

@app.get("/get_cmd/{user_id}")
async def get_cmd(user_id: str):
    # Обновляем last_seen при каждом запросе от ПК
    if user_id in pc_stats: pc_stats[user_id]["last_seen"] = time.time()
    else: pc_stats[user_id] = {"last_seen": time.time(), "java":"❌", "playit":"❌"}
    
    cmd = commands_storage.get(user_id, "IDLE")
    commands_storage[user_id] = "IDLE"
    return {"cmd": cmd}

# Остальной код бота (upload_screen, /start) оставляем из предыдущей версии
@app.post("/upload_screen/{user_id}")
async def upload_screen(user_id: str, file: UploadFile = File(...)):
    photo_bytes = await file.read()
    await bot.send_photo(chat_id=int(user_id), photo=BufferedInputFile(photo_bytes, filename="s.png"), caption="📸 Screenshot")
    return {"ok": True}

@dp.message(F.text == "/start")
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 OPEN DASHBOARD", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]])
    await m.answer("Добро пожаловать в панель управления!", reply_markup=kb)

async def run_bot(): await dp.start_polling(bot)
@app.on_event("startup")
async def on_up(): asyncio.create_task(run_bot())
if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=10000)
