import asyncio, time, os
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
console_logs = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    polling_task.cancel()

app = FastAPI(lifespan=lifespan)

# Прием плагинов (.jar)
@dp.message(F.document)
async def handle_docs(m: Message):
    if m.document.file_name.endswith('.jar'):
        f = await bot.get_file(m.document.file_id)
        url = f"https://api.telegram.org/file/bot{API_TOKEN}/{f.file_path}"
        commands_storage[str(m.from_user.id)] = f"INSTALL_PLG:{url}|{m.document.file_name}"
        await m.answer(f"🚀 Плагин {m.document.file_name} отправлен на установку!")

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
            :root { --grad: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%); }
            body { background: #08080a; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 15px; }
            .card { background: #121216; border-radius: 20px; padding: 20px; border: 1px solid #222; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            
            #console { 
                background: #000; border: 1px solid #333; border-radius: 12px; height: 180px; 
                overflow-y: auto; padding: 10px; font-family: 'Consolas', monospace; font-size: 11px; 
                color: #00ff41; margin: 15px 0; white-space: pre-wrap;
            }
            
            .btn { 
                width: 100%; padding: 14px; border-radius: 12px; border: none; color: white; 
                font-weight: bold; cursor: pointer; margin: 5px 0; transition: 0.2s;
            }
            .btn-main { background: var(--grad); color: #000; }
            .btn-danger { background: linear-gradient(135deg, #ff416c, #ff4b2b); }
            
            .input-group { display: flex; gap: 8px; margin-top: 10px; }
            input { flex: 1; background: #1a1a1e; border: 1px solid #333; border-radius: 10px; color: white; padding: 12px; }
            .stat-val { color: #00f2fe; font-size: 18px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span id="st-text" style="color:red; font-weight:bold;">● OFFLINE</span>
                <div style="text-align: right;">
                    <span class="stat-val" id="cpu">0%</span> <small>CPU</small>
                </div>
            </div>

            <div id="console">Ожидание логов...</div>

            <div class="input-group">
                <input type="text" id="term-in" placeholder="Введите команду...">
                <button class="btn btn-main" style="width: 80px; margin:0;" onclick="sendTerm()">SEND</button>
            </div>

            <div style="margin-top: 20px;">
                <button class="btn btn-main" onclick="sendCmd('START')">🚀 ЗАПУСТИТЬ СЕРВЕР</button>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <button class="btn btn-danger" onclick="sendCmd('STOP')">🛑 СТОП</button>
                    <button class="btn" style="background:#333;" onclick="sendCmd('SCREENSHOT')">📸 СКРИН</button>
                </div>
                <button class="btn" style="background: #fbab7e; background-image: linear-gradient(62deg, #fbab7e 0%, #f7ce68 100%); color:black;" 
                        onclick="sendCmd('CLEAN')">🧹 ОЧИСТИТЬ ПАМЯТЬ (TASKKILL)</button>
            </div>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            const uid = tg.initDataUnsafe.user.id;

            async function refresh() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let d = await r.json();
                    document.getElementById('st-text').innerText = d.online ? "● ONLINE" : "● OFFLINE";
                    document.getElementById('st-text').style.color = d.online ? "#00ff41" : "red";
                    document.getElementById('cpu').innerText = d.cpu + "%";
                    
                    if(d.logs) {
                        const c = document.getElementById('console');
                        c.innerText = d.logs.join('\\n');
                        c.scrollTop = c.scrollHeight;
                    }
                } catch(e) {}
            }

            function sendCmd(c) { fetch(`/send_from_web?user_id=${uid}&cmd=${c}`); }
            function sendTerm() {
                const i = document.getElementById('term-in');
                fetch(`/send_from_web?user_id=${uid}&cmd=TERM:` + i.value);
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
    return {"online": is_online, "cpu": stats.get("cpu", 0), "logs": console_logs.get(user_id, [])}

@app.post("/report_status/{user_id}")
async def report_status(user_id: str, data: dict):
    pc_stats[user_id] = {"cpu": data.get("cpu", 0), "last_seen": time.time()}
    if "logs" in data: console_logs[user_id] = data["logs"]
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

@app.post("/upload_screen/{user_id}")
async def upload_screen(user_id: str, file: UploadFile = File(...)):
    await bot.send_photo(chat_id=int(user_id), photo=BufferedInputFile(await file.read(), filename="s.png"))
    return {"ok": True}

@dp.message(F.text == "/start")
async def start(m: Message):
    await m.answer("Панель готова.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 КОНСОЛЬ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]]))

if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=10000)
