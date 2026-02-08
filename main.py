import asyncio, time, os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
import uvicorn

# --- НАСТРОЙКИ ---
API_TOKEN = '8504711791:AAG6jdtS_iC0ujhrFBwkPyshqFDqpi6JAdY'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = FastAPI()

commands_storage = {}
pc_stats = {} # {"user_id": {"java": "❌", "playit": "❌", "cpu": 0, "ram": 0, "last_seen": 0}}

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
            :root { --primary: #00f2fe; --secondary: #4facfe; }
            body { 
                background: #0f0f13; color: white; font-family: 'Segoe UI', sans-serif; 
                margin: 0; display: flex; flex-direction: column; align-items: center;
            }
            .header {
                width: 100%; padding: 20px; background: linear-gradient(180deg, rgba(79,172,254,0.1) 0%, transparent 100%);
                text-align: center; border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            .status-card {
                width: 85%; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1);
                border-radius: 24px; padding: 20px; margin-top: 20px; backdrop-filter: blur(10px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }
            .badge {
                display: inline-block; padding: 6px 12px; border-radius: 12px; font-size: 10px; font-weight: bold;
                letter-spacing: 1px; margin-bottom: 15px;
            }
            .online { background: #28a745; color: white; box-shadow: 0 0 15px rgba(40,167,69,0.4); }
            .offline { background: #dc3545; color: white; }

            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }
            .stat-box { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 16px; text-align: center; }
            .stat-val { display: block; font-size: 18px; font-weight: bold; color: var(--primary); }
            .stat-lab { font-size: 10px; color: #888; text-transform: uppercase; }

            .btn {
                width: 100%; padding: 18px; margin: 8px 0; border: none; border-radius: 16px;
                font-size: 15px; font-weight: bold; cursor: pointer; transition: 0.2s;
                display: flex; align-items: center; justify-content: center; gap: 10px;
            }
            .btn-main { background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); color: #000; }
            .btn-danger { background: rgba(220, 53, 69, 0.1); color: #ff4d4d; border: 1px solid rgba(220, 53, 69, 0.2); }
            .btn:active { transform: scale(0.96); }
            .btn:disabled { opacity: 0.3; filter: grayscale(1); }

            .loader { width: 20px; height: 20px; border: 3px solid #fff; border-bottom-color: transparent; border-radius: 50%; display: none; animation: rotation 1s linear infinite; }
            @keyframes rotation { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div class="header">
            <h1 style="margin:0; font-size: 20px;">MC REMOTE <span id="ver" style="font-size:10px; opacity:0.5;">v2.0</span></h1>
        </div>

        <div class="status-card">
            <div id="m-status" class="badge offline">OFFLINE</div>
            
            <div class="grid">
                <div class="stat-box"><span class="stat-val" id="s-java">❌</span><span class="stat-lab">Server</span></div>
                <div class="stat-box"><span class="stat-val" id="s-net">❌</span><span class="stat-lab">Network</span></div>
                <div class="stat-box"><span class="stat-val" id="s-cpu">0%</span><span class="stat-lab">CPU Load</span></div>
                <div class="stat-box"><span class="stat-val" id="s-ram">0%</span><span class="stat-lab">RAM Use</span></div>
            </div>

            <button id="b1" class="btn btn-main" onclick="sendCmd('START')">🚀 ЗАПУСТИТЬ</button>
            <button id="b2" class="btn btn-danger" onclick="sendCmd('STOP')">🛑 ОСТАНОВИТЬ</button>
            <button id="b3" class="btn btn" style="background: #222; color: #fff;" onclick="sendCmd('SCREENSHOT')">📸 СКРИНШОТ</button>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            const uid = tg.initDataUnsafe.user.id;

            async function refresh() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let d = await r.json();
                    
                    const marker = document.getElementById('m-status');
                    const btns = [document.getElementById('b1'), document.getElementById('b2'), document.getElementById('b3')];
                    
                    if (d.online) {
                        marker.innerText = "ONLINE"; marker.className = "badge online";
                        btns.forEach(b => b.disabled = false);
                        document.getElementById('s-java').innerText = d.java;
                        document.getElementById('s-net').innerText = d.playit;
                        document.getElementById('s-cpu').innerText = d.cpu + "%";
                        document.getElementById('s-ram').innerText = d.ram + "%";
                    } else {
                        marker.innerText = "OFFLINE"; marker.className = "badge offline";
                        btns.forEach(b => b.disabled = true);
                    }
                } catch(e) {}
            }

            function sendCmd(name) {
                fetch(`/send_from_web?user_id=${uid}&cmd=${name}`);
                tg.HapticFeedback.impactOccurred('heavy');
            }

            setInterval(refresh, 2000);
            refresh();
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
        "playit": stats.get("playit", "❌"),
        "cpu": stats.get("cpu", 0),
        "ram": stats.get("ram", 0)
    }

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    pc_stats[user_id] = {
        "java": data['java'], "playit": data['playit'],
        "cpu": data.get("cpu", 0), "ram": data.get("ram", 0),
        "last_seen": time.time()
    }
    return {"ok": True}

@app.get("/send_from_web")
async def send_from_web(user_id: str, cmd: str):
    commands_storage[user_id] = cmd
    return {"ok": True}

@app.get("/get_cmd/{user_id}")
async def get_cmd(user_id: str):
    if user_id in pc_stats: pc_stats[user_id]["last_seen"] = time.time()
    else: pc_stats[user_id] = {"last_seen": time.time(), "java":"❌", "playit":"❌"}
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
        InlineKeyboardButton(text="🎮 ПАНЕЛЬ УПРАВЛЕНИЯ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]])
    await m.answer("Добро пожаловать в будущее! Твой сервер на ладони:", reply_markup=kb)

async def run_bot():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e: print(f"Bot error: {e}")

@app.on_event("startup")
async def on_up(): asyncio.create_task(run_bot())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
