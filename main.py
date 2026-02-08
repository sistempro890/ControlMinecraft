import asyncio, time
from fastapi import FastAPI
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
            body { background: #000; color: #fff; font-family: sans-serif; margin: 0; padding: 10px; overflow: hidden; }
            .card { background: #111; border: 1px solid #333; border-radius: 15px; padding: 15px; height: 92vh; display: flex; flex-direction: column; }
            #console { flex-grow: 1; overflow-y: auto; padding: 10px; font-family: 'Courier New', monospace; color: #0f0; font-size: 11px; background: #050505; border-radius: 8px; white-space: pre-wrap; margin: 10px 0; border: 1px solid #222; scroll-behavior: smooth; }
            .btn { width: 100%; padding: 12px; border-radius: 8px; border: none; font-weight: bold; color: #fff; margin: 3px 0; font-size: 13px; cursor: pointer; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
            .input-group { display: flex; gap: 5px; }
            input { flex: 1; background: #000; border: 1px solid #333; color: #0f0; padding: 10px; border-radius: 8px; outline: none; }
            .status-bar { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 10px; font-weight: bold; }
            .on { color: #0f0; } .off { color: #f00; }
        </style>
    </head>
    <body>
        <audio id="snd" src="https://assets.mixkit.co/active_storage/sfx/1435/1435-preview.mp3"></audio>
        <div class="card">
            <div class="status-bar">
                <span id="st-bat">BAT: <span class="off">OFF</span></span>
                <span id="st-play">PLAYIT: <span class="off">OFF</span></span>
            </div>
            <div id="console">Загрузка данных с ПК...</div>
            <div class="input-group">
                <input type="text" id="cmd-in" placeholder="Введите команду...">
                <button onclick="sendT()" style="background:#0f0; border:none; padding:0 15px; border-radius:8px; font-weight:bold;">></button>
            </div>
            <div class="grid">
                <button class="btn" style="background:#333;" onclick="sendC('SYS_INFO')">📊 СИСТЕМА</button>
                <button class="btn" style="background:#333;" onclick="sendC('RESTART')">🔄 РЕСТАРТ</button>
            </div>
            <button class="btn" style="background:#28a745;" onclick="sendC('START')">🚀 ЗАПУСТИТЬ ВСЁ</button>
            <button class="btn" style="background:#dc3545;" onclick="sendC('STOP')">🛑 ОСТАНОВИТЬ</button>
        </div>
        <script>
            let tg = window.Telegram.WebApp;
            const uid = tg.initDataUnsafe?.user?.id || "8214297039";
            let lastLogs = "";
            let wasDone = false;

            async function update() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let d = await r.json();
                    
                    // Звук
                    if(d.is_done && !wasDone) { document.getElementById('snd').play(); wasDone = true; }
                    if(!d.bat_on) wasDone = false;

                    // Статусы
                    document.getElementById('st-bat').innerHTML = `BAT: <span class="${d.bat_on?'on':'off'}">${d.bat_on?'ON':'OFF'}</span>`;
                    document.getElementById('st-play').innerHTML = `PLAYIT: <span class="${d.play_on?'on':'off'}">${d.play_on?'ON':'OFF'}</span>`;

                    // Обновление логов БЕЗ мерцания
                    if(d.logs) {
                        let newLogs = d.logs.join('\\n');
                        if(newLogs !== lastLogs) {
                            const c = document.getElementById('console');
                            c.innerText = newLogs;
                            c.scrollTop = c.scrollHeight;
                            lastLogs = newLogs;
                        }
                    }
                } catch(e) {}
            }
            function sendC(c) { fetch(`/send_from_web?user_id=${uid}&cmd=${c}`); tg.HapticFeedback.impactOccurred('medium'); }
            function sendT() { 
                const i = document.getElementById('cmd-in'); 
                if(i.value) { fetch(`/send_from_web?user_id=${uid}&cmd=TERM:` + i.value); i.value = ''; }
            }
            setInterval(update, 1000);
            tg.expand();
        </script>
    </body>
    </html>
    """

@app.get("/get_pc_stats/{user_id}")
async def get_stats(user_id: str):
    return pc_stats.get(user_id, {})

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    msg = data.get("alert")
    if msg: asyncio.create_task(bot.send_message(int(user_id), msg))
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
    await m.answer("Управление Minecraft VPS", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📱 ОТКРЫТЬ ПУЛЬТ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]]))

if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=10000)
