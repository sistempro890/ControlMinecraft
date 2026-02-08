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
            #console { height: 250px; overflow-y: auto; padding: 10px; font-family: monospace; color: #ccc; font-size: 11px; background: #050505; border-radius: 8px; white-space: pre-wrap; margin: 10px 0; border: 1px solid #222; }
            .fullscreen-mode { position: fixed !important; top:0; left:0; width:100vw !important; height:100vh !important; z-index:9999; border-radius:0 !important; }
            .btn { width: 100%; padding: 12px; border-radius: 8px; border: none; font-weight: bold; color: #fff; margin: 3px 0; cursor: pointer; }
            .btn-vps { background: #222; font-size: 11px; border: 1px solid #444; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-top: 10px; }
            .input-group { display: flex; gap: 5px; }
            input { flex: 1; background: #000; border: 1px solid #333; color: #0f0; padding: 10px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <audio id="snd" src="https://assets.mixkit.co/active_storage/sfx/1435/1435-preview.mp3"></audio>
        <div class="card">
            <div id="console-wrap" style="position:relative;">
                <button onclick="toggleFS()" style="position:absolute; right:5px; top:5px; background:#333; color:#fff; border:none; padding:2px 5px; border-radius:3px; font-size:9px;">FULL</button>
                <div id="console">Ожидание...</div>
            </div>
            <div class="input-group">
                <input type="text" id="cmd-in" placeholder="Команда...">
                <button onclick="sendT()" style="background:#0f0; border:none; padding:0 15px; border-radius:8px; font-weight:bold;">></button>
            </div>
            <div class="grid">
                <button class="btn btn-vps" onclick="sendC('SYS_INFO')">📊 СИСТЕМА</button>
                <button class="btn btn-vps" onclick="sendC('CLEAR_LOGS')">🧹 ОЧИСТИТЬ ЛОГ</button>
                <button class="btn btn-vps" onclick="sendC('RESTART')">🔄 РЕСТАРТ</button>
                <button class="btn btn-vps" onclick="sendC('STOP')">💀 ВЫКЛЮЧИТЬ</button>
            </div>
            <button class="btn" style="background:#28a745; margin-top:10px;" onclick="sendC('START')">🚀 ЗАПУСК СЕРВЕРА</button>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            const uid = tg.initDataUnsafe?.user?.id || "8214297039";
            let wasDone = false;

            async function update() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let d = await r.json();
                    if (d.is_done && !wasDone) { document.getElementById('snd').play(); }
                    wasDone = d.is_done;
                    if(d.logs) {
                        const c = document.getElementById('console');
                        c.innerText = d.logs.join('\\n');
                        c.scrollTop = c.scrollHeight;
                    }
                } catch(e) {}
            }
            function toggleFS() { document.getElementById('console-wrap').classList.toggle('fullscreen-mode'); }
            function sendC(c) { fetch(`/send_from_web?user_id=${uid}&cmd=${c}`); }
            function sendT() { 
                const i = document.getElementById('cmd-in'); 
                fetch(`/send_from_web?user_id=${uid}&cmd=TERM:` + i.value); i.value = ''; 
            }
            setInterval(update, 1000);
        </script>
    </body>
    </html>
    """

@app.get("/get_pc_stats/{user_id}")
async def get_stats(user_id: str):
    return pc_stats.get(user_id, {})

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    # Логика уведомлений в Телеграм
    uid = int(user_id)
    msg = data.get("alert")
    if msg:
        asyncio.create_task(bot.send_message(uid, msg))
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

@dp.message(F.document)
async def handle_plugin(m: Message):
    if m.document.file_name.endswith('.jar'):
        file = await bot.get_file(m.document.file_id)
        url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
        commands_storage[str(m.from_user.id)] = f"INSTALL_PLG:{url}|{m.document.file_name}"
        await m.answer(f"📦 Плагин {m.document.file_name} загружается...")

@dp.message(F.text == "/start")
async def start(m: Message):
    await m.answer("Панель VPS готова.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 КОНСОЛЬ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]]))

if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=10000)
