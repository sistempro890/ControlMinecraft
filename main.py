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
            body { background: #0a0a0c; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 15px; overflow-x: hidden; }
            .card { background: #121216; border-radius: 20px; padding: 15px; border: 1px solid #222; }
            
            #console-wrapper { position: relative; transition: 0.3s; }
            #console { 
                background: #000; border: 2px solid #00ff41; border-radius: 10px; 
                height: 200px; overflow-y: auto; padding: 10px; 
                font-family: 'Consolas', monospace; font-size: 12px; color: #00ff41; 
                margin: 10px 0; white-space: pre-wrap;
            }
            #console.fullscreen { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 100; margin: 0; border-radius: 0; }
            
            .btn { width: 100%; padding: 14px; border-radius: 12px; border: none; color: white; font-weight: bold; margin: 5px 0; }
            .btn-start { background: linear-gradient(135deg, #00b09b, #96c93d); }
            .btn-stop { background: linear-gradient(135deg, #ff416c, #ff4b2b); }
            .btn-full { background: #333; font-size: 10px; width: auto; padding: 5px 10px; position: absolute; right: 5px; top: 15px; }
            
            .status-tag { padding: 4px 8px; border-radius: 6px; font-size: 11px; margin-right: 5px; }
            .on { background: rgba(0, 255, 65, 0.2); color: #00ff41; }
            .off { background: rgba(255, 0, 0, 0.2); color: #ff4d4d; }
        </style>
    </head>
    <body>
        <div class="card">
            <div style="margin-bottom: 10px;">
                <span id="st-bat" class="status-tag off">BAT: OFF</span>
                <span id="st-play" class="status-tag off">PLAYIT: OFF</span>
            </div>

            <div id="console-wrapper">
                <button class="btn btn-full" onclick="toggleFull()">FULLSCREEN</button>
                <div id="console">Загрузка логов...</div>
            </div>

            <div style="display: flex; gap: 5px;">
                <input type="text" id="t-in" style="flex:1; background:#000; color:#00ff41; border:1px solid #333; padding:10px; border-radius:10px;">
                <button onclick="sendTerm()" style="background:#00ff41; color:#000; border:none; border-radius:10px; padding:0 15px;">></button>
            </div>

            <button class="btn btn-start" onclick="sendCmd('START')">🚀 ЗАПУСТИТЬ</button>
            <button class="btn btn-stop" onclick="sendCmd('STOP')">🛑 СТОП</button>
        </div>

        <audio id="notifSound" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>

        <script>
            let tg = window.Telegram.WebApp;
            const uid = tg.initDataUnsafe.user.id;
            let isFull = false;
            let userScrolling = false;
            let lastBatState = false;

            const con = document.getElementById('console');
            con.onscroll = () => {
                userScrolling = con.scrollTop + con.clientHeight < con.scrollHeight - 20;
            };

            async function refresh() {
                let r = await fetch('/get_pc_stats/' + uid);
                let d = await r.json();
                
                // Звук при запуске
                if (d.bat_on && !lastBatState) {
                    document.getElementById('notifSound').play();
                    tg.HapticFeedback.notificationOccurred('success');
                }
                lastBatState = d.bat_on;

                document.getElementById('st-bat').className = d.bat_on ? 'status-tag on' : 'status-tag off';
                document.getElementById('st-bat').innerText = 'BAT: ' + (d.bat_on ? 'ON' : 'OFF');
                document.getElementById('st-play').className = d.play_on ? 'status-tag on' : 'status-tag off';
                document.getElementById('st-play').innerText = 'PLAYIT: ' + (d.play_on ? 'ON' : 'OFF');

                if (d.logs) {
                    con.innerText = d.logs.join('\\n');
                    if (!userScrolling) con.scrollTop = con.scrollHeight;
                }
            }

            function toggleFull() {
                isFull = !isFull;
                con.classList.toggle('fullscreen');
            }

            function sendCmd(c) { fetch(`/send_from_web?user_id=${uid}&cmd=${c}`); }
            function sendTerm() {
                const i = document.getElementById('t-in');
                fetch(`/send_from_web?user_id=${uid}&cmd=TERM:` + i.value);
                i.value = '';
            }
            setInterval(refresh, 1000);
        </script>
    </body>
    </html>
    """

@app.get("/get_pc_stats/{user_id}")
async def get_stats(user_id: str):
    s = pc_stats.get(user_id, {"last_seen": 0})
    return {
        "online": (time.time() - s['last_seen']) < 10,
        "bat_on": s.get("bat_on", False),
        "play_on": s.get("play_on", False),
        "logs": s.get("logs", [])
    }

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    pc_stats[user_id] = data
    pc_stats[user_id]['last_seen'] = time.time()
    return {"ok": True}

@app.get("/get_cmd/{user_id}")
async def get_cmd(user_id: str):
    cmd = commands_storage.get(user_id, "IDLE")
    commands_storage[user_id] = "IDLE"
    return {"cmd": cmd}

@app.get("/send_from_web")
async def send_from_web(user_id: str, cmd: str):
    commands_storage[user_id] = cmd
    return {"ok": True}

if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=10000)
