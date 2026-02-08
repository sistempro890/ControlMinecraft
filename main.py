import asyncio, time
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
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
    polling_task = asyncio.create_task(dp.start_polling(bot, skip_updates=True))
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { background: #000; color: #fff; font-family: sans-serif; margin: 0; padding: 10px; }
            .card { background: #111; border: 1px solid #333; border-radius: 15px; padding: 15px; }
            .status-row { display: flex; justify-content: space-around; margin-bottom: 10px; }
            .tag { padding: 5px 10px; border-radius: 5px; font-size: 10px; font-weight: bold; border: 1px solid #444; }
            .on { color: #0f0; border-color: #0f0; background: rgba(0,255,0,0.1); }
            .off { color: #f00; border-color: #f00; background: rgba(255,0,0,0.1); }
            
            #console-wrap { position: relative; margin: 10px 0; border: 1px solid #333; border-radius: 8px; overflow: hidden; }
            #console { height: 250px; overflow-y: auto; padding: 10px; font-family: monospace; color: #ccc; font-size: 11px; background: #050505; white-space: pre-wrap; }
            
            /* КНОПКА НА ВЕСЬ ЭКРАН */
            .fullscreen-mode { position: fixed !important; top:0; left:0; width:100vw !important; height:100vh !important; z-index:9999; }
            .fs-btn { position: absolute; top: 5px; right: 5px; background: #222; color: #fff; border: 1px solid #444; padding: 5px; font-size: 10px; border-radius: 4px; z-index: 10000; }

            .btn { width: 100%; padding: 15px; border-radius: 10px; border: none; font-weight: bold; color: #fff; margin: 5px 0; font-size: 14px; }
            .btn-start { background: #28a745; }
            .btn-stop { background: #dc3545; }
            
            .input-group { display: flex; gap: 5px; margin-top: 10px; }
            input { flex: 1; background: #000; border: 1px solid #333; color: #0f0; padding: 10px; border-radius: 8px; }
            .send-v { background: #0f0; color: #000; border: none; padding: 0 15px; border-radius: 8px; font-weight: bold; }
        </style>
    </head>
    <body>
        <audio id="beep" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>
        
        <div class="card">
            <div class="status-row">
                <span id="b-t" class="tag off">BAT: OFF</span>
                <span id="p-t" class="tag off">PLAYIT: OFF</span>
            </div>

            <div id="console-wrap">
                <button class="fs-btn" onclick="toggleFS()">РАЗВЕРНУТЬ</button>
                <div id="console">Ожидание...</div>
            </div>

            <div class="input-group">
                <input type="text" id="cmd-in" placeholder="Команда (say...)">
                <button class="send-v" onclick="sendT()">OK</button>
            </div>

            <button class="btn btn-start" onclick="sendC('START')">ЗАПУСТИТЬ</button>
            <button class="btn btn-stop" onclick="sendC('STOP')">ВЫКЛЮЧИТЬ ВСЁ</button>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            const uid = tg.initDataUnsafe?.user?.id || "8214297039";
            let lastBat = false;
            let autoScroll = true;

            const con = document.getElementById('console');
            con.onscroll = () => { 
                autoScroll = con.scrollTop + con.clientHeight >= con.scrollHeight - 20; 
            };

            function toggleFS() {
                document.getElementById('console-wrap').classList.toggle('fullscreen-mode');
                document.getElementById('console').style.height = document.getElementById('console-wrap').classList.contains('fullscreen-mode') ? '100vh' : '250px';
            }

            async function update() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let d = await r.json();

                    if(d.bat_on && !lastBat) { document.getElementById('beep').play(); }
                    lastBat = d.bat_on;

                    document.getElementById('b-t').className = d.bat_on ? 'tag on' : 'tag off';
                    document.getElementById('b-t').innerText = 'BAT: ' + (d.bat_on ? 'ON' : 'OFF');
                    document.getElementById('p-t').className = d.play_on ? 'tag on' : 'tag off';
                    document.getElementById('p-t').innerText = 'PLAYIT: ' + (d.play_on ? 'ON' : 'OFF');

                    if(d.logs) {
                        con.innerText = d.logs.join('\\n');
                        if(autoScroll) con.scrollTop = con.scrollHeight;
                    }
                } catch(e) {}
            }
            function sendC(c) { fetch(`/send_from_web?user_id=${uid}&cmd=${c}`); }
            function sendT() {
                const i = document.getElementById('cmd-in');
                fetch(`/send_from_web?user_id=${uid}&cmd=TERM:` + i.value);
                i.value = '';
            }
            setInterval(update, 1000);
        </script>
    </body>
    </html>
    """

@app.get("/get_pc_stats/{user_id}")
async def get_stats(user_id: str):
    s = pc_stats.get(user_id, {})
    return {"bat_on": s.get("bat_on", False), "play_on": s.get("play_on", False), "logs": s.get("logs", [])}

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    pc_stats[user_id] = data
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

@dp.message(F.text == "/start")
async def start(m: Message):
    await m.answer("Панель готова.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 ОТКРЫТЬ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]]))

if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=10000)
