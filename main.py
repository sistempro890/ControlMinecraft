import asyncio, time
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, F
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
    # Эта строка убивает конфликт "terminated by other getUpdates request"
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
            body { background: #000; color: #fff; font-family: sans-serif; margin: 0; padding: 15px; text-align: center; }
            .card { background: #1a1a1a; border: 2px solid #333; border-radius: 20px; padding: 20px; margin-top: 10px; }
            .tag { display: inline-block; padding: 6px 12px; border-radius: 10px; font-size: 12px; font-weight: bold; margin: 5px; border: 1px solid #444; }
            .on { color: #00ff41; border-color: #00ff41; background: rgba(0,255,65,0.1); }
            .off { color: #ff416c; border-color: #ff416c; background: rgba(255,65,108,0.1); }
            
            #console { 
                background: #000; border: 1px solid #00ff41; border-radius: 10px; 
                height: 200px; overflow-y: auto; padding: 10px; font-family: monospace; 
                color: #00ff41; font-size: 11px; text-align: left; margin: 15px 0; white-space: pre-wrap;
            }
            
            .btn { 
                display: block; width: 100%; padding: 15px; border-radius: 12px; border: none; 
                font-weight: bold; color: #fff; margin: 10px 0; font-size: 16px; cursor: pointer;
            }
            .btn-start { background: linear-gradient(135deg, #00b09b, #96c93d); box-shadow: 0 4px 15px rgba(0,255,100,0.2); }
            .btn-stop { background: linear-gradient(135deg, #ff416c, #ff4b2b); }
            
            input { width: 80%; background: #111; border: 1px solid #00ff41; color: #00ff41; padding: 12px; border-radius: 10px; outline: none; }
            button.send-btn { width: 15%; padding: 12px; background: #00ff41; border: none; border-radius: 10px; font-weight: bold; }
        </style>
    </head>
    <body>
        <audio id="notif" src="https://www.myinstants.com/media/sounds/discord-notification.mp3"></audio>
        
        <div class="card">
            <h2 style="margin: 0 0 15px 0; color: #00f2fe;">MC CONTROL</h2>
            <div style="margin-bottom: 10px;">
                <span id="b-t" class="tag off">BAT: OFF</span>
                <span id="p-t" class="tag off">PLAYIT: OFF</span>
            </div>
            
            <div id="console">Ожидание данных от ПК...</div>

            <div style="display:flex; justify-content: space-between; margin-bottom: 10px;">
                <input type="text" id="c-i" placeholder="Команда (say...)">
                <button class="send-btn" onclick="sendT()">></button>
            </div>

            <button class="btn btn-start" onclick="sendC('START')">🚀 ЗАПУСТИТЬ СЕРВЕР</button>
            <button class="btn btn-stop" onclick="sendC('STOP')">🛑 ОСТАНОВИТЬ ВСЁ</button>
        </div>

        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            // Пытаемся получить ID, если не вышло (запуск в браузере) - используем твой ID для теста
            const uid = tg.initDataUnsafe?.user?.id || "8214297039";
            let lastB = false;

            async function refresh() {
                try {
                    let r = await fetch('/get_pc_stats/' + uid);
                    let d = await r.json();

                    if(d.bat_on && !lastB) { document.getElementById('notif').play(); }
                    lastB = d.bat_on;

                    document.getElementById('b-t').className = d.bat_on ? 'tag on' : 'tag off';
                    document.getElementById('b-t').innerText = 'BAT: ' + (d.bat_on ? 'ON' : 'OFF');
                    document.getElementById('p-t').className = d.play_on ? 'tag on' : 'tag off';
                    document.getElementById('p-t').innerText = 'PLAYIT: ' + (d.play_on ? 'ON' : 'OFF');

                    if(d.logs && d.logs.length > 0) {
                        const c = document.getElementById('console');
                        c.innerText = d.logs.join('\\n');
                        c.scrollTop = c.scrollHeight;
                    }
                } catch(e) { console.log("Ошибка обновления"); }
            }

            function sendC(c) { fetch(`/send_from_web?user_id=${uid}&cmd=${c}`); tg.HapticFeedback.impactOccurred('medium'); }
            function sendT() {
                const i = document.getElementById('c-i');
                if(!i.value) return;
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

@dp.message(F.text == "/start")
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 ОТКРЫТЬ ПАНЕЛЬ", web_app=WebAppInfo(url="https://controlminecraft.onrender.com"))
    ]])
    await m.answer("Управление сервером готово!", reply_markup=kb)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
