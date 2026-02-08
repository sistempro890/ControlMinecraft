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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { background: #0a0a0c; color: white; font-family: sans-serif; margin: 0; padding: 15px; }
            .card { background: #121216; border-radius: 20px; padding: 20px; border: 1px solid #333; }
            .status-row { display: flex; gap: 10px; margin-bottom: 15px; }
            .tag { padding: 5px 10px; border-radius: 8px; font-size: 10px; font-weight: bold; border: 1px solid #444; }
            .on { color: #00ff41; border-color: #00ff41; background: rgba(0,255,65,0.1); }
            .off { color: #ff416c; border-color: #ff416c; background: rgba(255,65,108,0.1); }
            
            #console-box { position: relative; background: #000; border: 1px solid #00ff41; border-radius: 10px; margin: 15px 0; }
            #console { height: 250px; overflow-y: auto; padding: 10px; font-family: monospace; color: #00ff41; font-size: 12px; white-space: pre-wrap; }
            .fullscreen { position: fixed !important; top:0; left:0; width:100vw; height:100vh !important; z-index:999; border-radius:0 !important; }
            
            .btn { width: 100%; padding: 15px; border-radius: 12px; border: none; font-weight: bold; color: white; margin-top: 10px; }
            .btn-start { background: linear-gradient(135deg, #00b09b, #96c93d); }
            .btn-stop { background: linear-gradient(135deg, #ff416c, #ff4b2b); }
            .fs-btn { position: absolute; top: 5px; right: 5px; background: #222; font-size: 10px; color: white; border: 1px solid #444; padding: 3px 7px; border-radius: 5px; }
            
            input { width: 100%; background: #000; border: 1px solid #333; color: #00ff41; padding: 12px; border-radius: 10px; box-sizing: border-box; }
        </audio>
    </head>
    <body>
        <audio id="snd" src="https://www.myinstants.com/media/sounds/discord-notification.mp3"></audio>
        <div class="card">
            <div class="status-row">
                <div id="bat-tag" class="tag off">BAT: OFF</div>
                <div id="play-tag" class="tag off">PLAYIT: OFF</div>
            </div>
            
            <div id="console-box">
                <button class="fs-btn" onclick="document.getElementById('console-box').classList.toggle('fullscreen')">FULL</button>
                <div id="console">Ожидание...</div>
            </div>

            <div style="display:flex; gap:10px;">
                <input type="text" id="cmd-in" placeholder="Команда...">
                <button onclick="sendT()" style="background:#00ff41; border:none; border-radius:10px; padding:0 15px;">></button>
            </div>

            <button class="btn btn-start" onclick="sendC('START')">🚀 ЗАПУСТИТЬ</button>
            <button class="btn btn-stop" onclick="sendC('STOP')">🛑 СТОП</button>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            const uid = tg.initDataUnsafe.user.id;
            let lastBat = false;
            let userScroll = false;

            const con = document.getElementById('console');
            con.onscroll = () => { userScroll = con.scrollTop + con.clientHeight < con.scrollHeight - 20; };

            async function update() {
                let r = await fetch('/get_pc_stats/' + uid);
                let d = await r.json();

                if(d.bat_on && !lastBat) { document.getElementById('snd').play(); tg.HapticFeedback.notificationOccurred('success'); }
                lastBat = d.bat_on;

                document.getElementById('bat-tag').className = d.bat_on ? 'tag on' : 'tag off';
                document.getElementById('bat-tag').innerText = 'BAT: ' + (d.bat_on ? 'ON' : 'OFF');
                document.getElementById('play-tag').className = d.play_on ? 'tag on' : 'tag off';
                document.getElementById('play-tag').innerText = 'PLAYIT: ' + (d.play_on ? 'ON' : 'OFF');

                if(d.logs) {
                    con.innerText = d.logs.join('\\n');
                    if(!userScroll) con.scrollTop = con.scrollHeight;
                }
            }
            function sendC(c) { fetch(`/send_from_web?user_id=${uid}&cmd=${c}`); }
            function sendT() { 
                const i = document.getElementById('cmd-in');
                fetch(`/send_from_web?user_id=${uid}&cmd=TERM:`+i.value); 
                i.value=''; 
            }
            setInterval(update, 1000);
        </script>
    </body>
    </html>
    """
# ... (Остальной код API без изменений: get_pc_stats, report_status, get_cmd, send_from_web)
# Добавь эти функции ниже:
@app.get("/get_pc_stats/{user_id}")
async def get_stats(user_id: str):
    s = pc_stats.get(user_id, {"last_seen": 0})
    return {"bat_on": s.get("bat_on", False), "play_on": s.get("play_on", False), "logs": s.get("logs", [])}

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

@dp.message(F.text == "/start")
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 КОНСОЛЬ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))]])
    await m.answer("Панель управления готова.", reply_markup=kb)

if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=10000)
