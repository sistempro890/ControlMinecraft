import asyncio, time
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
import uvicorn
from contextlib import asynccontextmanager

API_TOKEN = '8504711791:AAG6jdtS_iC0ujhrFBwkPyshqFDqpi6JAdY'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

commands_storage = {}
pc_stats = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    polling_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { 
                background: #0a0a0c; color: white; font-family: 'Segoe UI', sans-serif; 
                display: flex; flex-direction: column; align-items: center; margin: 0; padding: 20px;
            }
            .container { width: 100%; max-width: 400px; }
            .card {
                background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 25px; padding: 25px; backdrop-filter: blur(15px);
                box-shadow: 0 20px 50px rgba(0,0,0,0.5);
            }
            .status-line { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; font-weight: bold; }
            .dot { width: 10px; height: 10px; border-radius: 50%; box-shadow: 0 0 10px currentColor; }
            
            .btn {
                width: 100%; padding: 16px; margin: 10px 0; border: none; border-radius: 15px;
                font-size: 16px; font-weight: bold; color: white; cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
                display: flex; align-items: center; justify-content: center; gap: 10px;
            }
            .btn:active { transform: scale(0.97); }
            
            .btn-start { background: linear-gradient(135deg, #00b09b, #96c93d); box-shadow: 0 4px 15px rgba(0, 176, 155, 0.3); }
            .btn-stop { background: linear-gradient(135deg, #ff416c, #ff4b2b); box-shadow: 0 4px 15px rgba(255, 65, 108, 0.3); }
            .btn-screen { background: linear-gradient(135deg, #4facfe, #00f2fe); box-shadow: 0 4px 15px rgba(79, 172, 254, 0.3); }
            
            .btn:disabled { background: #333 !important; box-shadow: none !important; opacity: 0.5; }
            
            .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
            .stat-box { background: rgba(0,0,0,0.3); padding: 12px; border-radius: 12px; text-align: center; }
            .stat-val { color: #00f2fe; font-weight: bold; font-size: 18px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <div class="status-line" id="st-line" style="color: #ff4d4d;">
                    <div class="dot" id="st-dot"></div> <span id="st-text">OFFLINE</span>
                </div>
                
                <div class="stat-grid">
                    <div class="stat-box"><div class="stat-val" id="cpu">0%</div><div style="font-size:10px">CPU</div></div>
                    <div class="stat-box"><div class="stat-val" id="ram">0%</div><div style="font-size:10px">RAM</div></div>
                </div>

                <div style="margin-top: 25px;">
                    <button id="b1" class="btn btn-start" onclick="sendCmd('START')">🚀 ЗАПУСТИТЬ</button>
                    <button id="b2" class="btn btn-stop" onclick="sendCmd('STOP')">🛑 ВЫКЛЮЧИТЬ</button>
                    <button id="b3" class="btn btn-screen" onclick="sendCmd('SCREENSHOT')">📸 СКРИНШОТ</button>
                </div>
            </div>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            const uid = tg.initDataUnsafe.user.id;

            async function update() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let d = await r.json();
                    
                    const line = document.getElementById('st-line');
                    const text = document.getElementById('st-text');
                    const btns = [document.getElementById('b1'), document.getElementById('b2'), document.getElementById('b3')];

                    if(d.online) {
                        line.style.color = "#28a745"; text.innerText = "ONLINE";
                        btns.forEach(b => b.disabled = false);
                    } else {
                        line.style.color = "#ff4d4d"; text.innerText = "OFFLINE";
                        btns.forEach(b => b.disabled = true);
                    }
                    document.getElementById('cpu').innerText = d.cpu + "%";
                    document.getElementById('ram').innerText = d.ram + "%";
                } catch(e) {}
            }

            function sendCmd(c) { fetch(`/send_from_web?user_id=${uid}&cmd=${c}`); tg.HapticFeedback.notificationOccurred('success'); }
            setInterval(update, 2000);
        </script>
    </body>
    </html>
    """

@app.get("/get_pc_stats/{user_id}")
async def get_stats(user_id: str):
    stats = pc_stats.get(user_id, {"last_seen": 0})
    is_online = (time.time() - stats['last_seen']) < 10
    return {"online": is_online, "cpu": stats.get("cpu", 0), "ram": stats.get("ram", 0)}

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    pc_stats[user_id] = {"cpu": data.get("cpu", 0), "ram": data.get("ram", 0), "last_seen": time.time()}
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

@app.post("/upload_screen/{user_id}")
async def upload_screen(user_id: str, file: UploadFile = File(...)):
    photo_bytes = await file.read()
    await bot.send_photo(chat_id=int(user_id), photo=BufferedInputFile(photo_bytes, filename="s.png"))
    return {"ok": True}

@dp.message(F.text == "/start")
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 КОНТРОЛЬ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))]])
    await m.answer("Панель управления активирована.", reply_markup=kb)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
