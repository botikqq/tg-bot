# language: Python 3.11, file: bot.py, target: Linux/Windows
# pip install aiogram aiohttp
import asyncio
import sqlite3
import re
import json
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# ВСТАВЬ СЮДА СВОЙ ТОКЕН ОТ BOTFATHER
BOT_TOKEN = "9077882574:AAGfl3zErjgqe7JzNPk8z35oDFYReJTqDyU"

dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
db = sqlite3.connect("probiv.db")
db.execute("""CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, target TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
db.commit()

# --- УТИЛИТЫ ---
def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] in "78":
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    if 10 <= len(digits) <= 15:
        return "+" + digits
    return None

async def get_telegram_info(session: aiohttp.ClientSession, target: str) -> dict:
    """Публичные данные через t.me — username/канал."""
    name = target.lstrip("@")
    url = f"https://t.me/{name}"
    try:
        async with session.get(url, timeout=10) as r:
            if r.status == 404:
                return {"error": "Не найден"}
            html = await r.text()
    except Exception as e:
        return {"error": str(e)}

    out = {"username": name}
    for key, pat in [
        ("title", r'property="og:title"\s+content="([^"]*)"'),
        ("description", r'property="og:description"\s+content="([^"]*)"'),
    ]:
        m = re.search(pat, html)
        if m: out[key] = m.group(1)
    
    m = re.search(r'([\d\s]+)\s*(subscribers|members|подписчик)', html)
    if m: out["subscribers"] = m.group(1).strip()
    return out

async def check_leaks(session: aiohttp.ClientSession, query: str) -> list:
    """Заглушка под API утечек (intelx, leaked и т.п.)."""
    return [{"status": "API ключ не подключен"}]

# --- ХЕНДЛЕРЫ ---
@dp.message(CommandStart())
async def start(msg: types.Message):
    await msg.answer(
        "Бот на связи.\n"
        "Отправь /check +79001234567 или /check @username"
    )

@dp.message(lambda m: m.text and m.text.startswith("/check"))
async def check(msg: types.Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return await msg.answer("Формат: /check <номер|@username>")
    target = parts[1].strip()

    async with aiohttp.ClientSession() as session:
        report = {"target": target}
        
        phone = normalize_phone(target)
        if phone:
            report["phone"] = phone
            report["leaks"] = await check_leaks(session, phone)
        elif target.startswith("@") or re.match(r"^[A-Za-z0-9_]{5,}$", target):
            report["telegram"] = await get_telegram_info(session, target)
        else:
            return await msg.answer("Не распознал цель. Номер или @username.")

        db.execute("INSERT INTO queries (user_id, target) VALUES (?, ?)", (msg.from_user.id, target))
        db.commit()

    text = "🔎 <b>Отчёт</b>\n<pre>" + json.dumps(report, ensure_ascii=False, indent=2) + "</pre>"
    await msg.answer(text, parse_mode="HTML")

async def main():
    bot = Bot(token=BOT_TOKEN)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
