import asyncio
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import json
import os
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, ChatPermissions

TOKEN = "8718538050:AAFF5vaaWS8Eg2J8PAcW4dgMfQP3rorRN9s"
ADMIN_IDS = [8671380166, 7115269048]
OWNER_ID = 8671380166

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== БАЗА ДАННЫХ ==========
DATA_FILE = "sonara_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"balance": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ========== ВАЛЮТА ==========
def get_balance(user_id):
    uid = str(user_id)
    if uid not in data["balance"]:
        data["balance"][uid] = 0
        save_data(data)
    return data["balance"][uid]

def add_balance(user_id, amount):
    uid = str(user_id)
    if uid not in data["balance"]:
        data["balance"][uid] = 0
    data["balance"][uid] += amount
    save_data(data)
    return data["balance"][uid]

def remove_balance(user_id, amount):
    uid = str(user_id)
    if uid not in data["balance"]:
        return False
    if data["balance"][uid] < amount:
        return False
    data["balance"][uid] -= amount
    save_data(data)
    return True

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@dp.message(F.text.lower() == "/start")
async def start(m: types.Message):
    await m.answer(
        "🤖 *SONARA BOT*\n\n"
        "💰 `/баланс` — баланс\n"
        "💱 `/курс` — курс SNC\n"
        "⭐ `/buy` — купить SNC за Stars\n"
        "🛒 `/buyt` — купить VIP/Premium\n"
        "💸 `/перевести 100` (ответом) — перевод\n"
        "👑 `/мут 1 час` (ответом) — замутить\n"
        "👑 `/бан` (ответом) — забанить\n"
        "👑 `/кик` (ответом) — кикнуть\n"
        "👑 `/варн` (ответом) — предупреждение\n"
        "💰 `/начислить` — начислить SNC (только владелец)\n"
        "📌 `тик` → так\n"
        "📌 `/ид` — показать ID",
        parse_mode="Markdown"
    )

@dp.message(F.text.lower() == "/баланс")
async def balance(m: types.Message):
    await m.answer(f"💰 Ваш баланс: {get_balance(m.from_user.id)} SNC")

@dp.message(F.text.lower() == "/курс")
async def kurs(m: types.Message):
    await m.answer("💱 1 SNC = 14 ₽ = 25 Stars")

@dp.message(F.text.lower() == "тик")
async def tik(m: types.Message):
    await m.reply("Так")

@dp.message(F.text.lower() == "/ид")
async def user_id(m: types.Message):
    if m.reply_to_message:
        await m.answer(f"🆔 ID: {m.reply_to_message.from_user.id}")
    else:
        await m.answer(f"🆔 Ваш ID: {m.from_user.id}")

# ========== КОМАНДА ДЛЯ ВЛАДЕЛЬЦА ==========
@dp.message(F.text.lower() == "/начислить")
async def add_money(m: types.Message):
    if m.from_user.id != OWNER_ID:
        await m.answer("⛔ Только для владельца!")
        return
    
    amount = 1000000
    new_balance = add_balance(m.from_user.id, amount)
    await m.answer(f"✅ Начислено {amount} SNC!\n💰 Ваш баланс: {new_balance} SNC")

# ========== ПОКУПКА SNC ЗА ЗВЁЗДЫ ==========
STARS_PACKS = {25: 1, 250: 10, 2500: 100, 25000: 1000}

@dp.message(F.text.lower() == "/buy")
async def buy_menu(m: types.Message):
    btns = [[InlineKeyboardButton(text=f"⭐ {stars} Stars → {snc} SNC", callback_data=f"buy_stars_{stars}")] for stars, snc in STARS_PACKS.items()]
    btns.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close")])
    await m.answer("🛒 *Купить SNC*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(lambda c: c.data.startswith("buy_stars_"))
async def buy_stars_cb(cb: types.CallbackQuery):
    stars = int(cb.data.split("_")[2])
    snc = STARS_PACKS.get(stars, 0)
    if snc == 0:
        await cb.answer("Ошибка", show_alert=True)
        return
    try:
        await cb.message.answer_invoice(
            title=f"Покупка {snc} SNC",
            description=f"⭐ {stars} Stars → {snc} SNC",
            prices=[LabeledPrice(label=f"{stars} Stars", amount=stars)],
            provider_token="", payload=f"{stars}_{snc}", currency="XTR"
        )
    except Exception as e:
        await cb.message.answer(f"❌ {e}")
    await cb.answer()

@dp.pre_checkout_query()
async def pre_checkout(q: types.PreCheckoutQuery):
    await q.answer(ok=True)

@dp.message(F.successful_payment)
async def payment_ok(m: types.Message):
    stars, snc = map(int, m.successful_payment.invoice_payload.split("_"))
    new_balance = add_balance(m.from_user.id, snc)
    await m.answer(f"✅ +{snc} SNC!\n💰 Баланс: {new_balance} SNC")

# ========== ПЕРЕВОД ==========
@dp.message(F.text.lower().startswith("/перевести"))
async def transfer(m: types.Message):
    if not m.reply_to_message:
        await m.answer("❌ Ответь на сообщение пользователя и напиши `/перевести 100`")
        return
    
    parts = m.text.split()
    if len(parts) < 2:
        await m.answer("❌ Пример: `/перевести 100`")
        return
    
    try:
        amount = int(parts[1])
    except:
        await m.answer("❌ Сумма должна быть числом!")
        return
    
    if amount <= 0:
        await m.answer("❌ Сумма должна быть положительной!")
        return
    
    from_id = m.from_user.id
    to_id = m.reply_to_message.from_user.id
    
    if to_id == from_id:
        await m.answer("❌ Нельзя перевести самому себе!")
        return
    
    if get_balance(from_id) < amount:
        await m.answer(f"❌ Недостаточно SNC! У вас {get_balance(from_id)} SNC")
        return
    
    remove_balance(from_id, amount)
    add_balance(to_id, amount)
    await m.answer(f"✅ Переведено {amount} SNC пользователю {m.reply_to_message.from_user.full_name}")

# ========== МОДЕРАЦИЯ ==========
def parse_time(duration: str):
    dur = duration.lower()
    if "час" in dur or "ч" in dur:
        hours = int(''.join(filter(str.isdigit, dur)) or 1)
        return hours * 60
    elif "день" in dur or "дн" in dur:
        days = int(''.join(filter(str.isdigit, dur)) or 1)
        return days * 24 * 60
    elif "минут" in dur or "мин" in dur:
        return int(''.join(filter(str.isdigit, dur)) or 1)
    return 60

@dp.message(F.text.lower().startswith(("/мут", "/mute")))
async def mute_user(m: types.Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("⛔ Нет прав! Только для админов")
        return
    if not m.reply_to_message:
        await m.answer("❌ Ответьте на сообщение пользователя")
        return
    
    parts = m.text.split()
    if len(parts) < 2:
        await m.answer("❌ Пример: `/мут 1 час`")
        return
    
    duration_str = parts[1]
    reason = " ".join(parts[2:]) if len(parts) > 2 else "Нарушение правил"
    minutes = parse_time(duration_str)
    until = datetime.now() + timedelta(minutes=minutes)
    user = m.reply_to_message.from_user
    
    if user.id in ADMIN_IDS:
        await m.answer("❌ Нельзя замутить админа!")
        return
    
    try:
        await bot.restrict_chat_member(m.chat.id, user.id, permissions=ChatPermissions(can_send_messages=False), until_date=until)
        await m.answer(f"✅ Замучен {user.full_name} на {duration_str}\nПричина: {reason}")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {e}")

@dp.message(F.text.lower().startswith(("/бан", "/ban")))
async def ban_user(m: types.Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("⛔ Нет прав! Только для админов")
        return
    if not m.reply_to_message:
        await m.answer("❌ Ответьте на сообщение пользователя")
        return
    
    parts = m.text.split()
    reason = " ".join(parts[1:]) if len(parts) > 1 else "Нарушение правил"
    user = m.reply_to_message.from_user
    
    if user.id in ADMIN_IDS:
        await m.answer("❌ Нельзя забанить админа!")
        return
    
    try:
        await bot.ban_chat_member(m.chat.id, user.id)
        await m.answer(f"✅ Забанен {user.full_name}\nПричина: {reason}")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {e}")

@dp.message(F.text.lower().startswith(("/кик", "/kick")))
async def kick_user(m: types.Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("⛔ Нет прав! Только для админов")
        return
    if not m.reply_to_message:
        await m.answer("❌ Ответьте на сообщение пользователя")
        return
    
    parts = m.text.split()
    reason = " ".join(parts[1:]) if len(parts) > 1 else "Нарушение правил"
    user = m.reply_to_message.from_user
    
    if user.id in ADMIN_IDS:
        await m.answer("❌ Нельзя кикнуть админа!")
        return
    
    try:
        await bot.ban_chat_member(m.chat.id, user.id)
        await bot.unban_chat_member(m.chat.id, user.id)
        await m.answer(f"✅ Кикнут {user.full_name}\nПричина: {reason}")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {e}")

@dp.message(F.text.lower().startswith(("/варн", "/warn")))
async def warn_user(m: types.Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("⛔ Нет прав! Только для админов")
        return
    if not m.reply_to_message:
        await m.answer("❌ Ответьте на сообщение пользователя")
        return
    
    parts = m.text.split()
    reason = " ".join(parts[1:]) if len(parts) > 1 else "Нарушение правил"
    user = m.reply_to_message.from_user
    
    await m.answer(f"⚠️ Выдано предупреждение {user.full_name}\nПричина: {reason}")

# ========== МАГАЗИН VIP/PREMIUM (УПРОЩЁННЫЙ) ==========
@dp.message(F.text.lower() == "/buyt")
async def buyt_menu(m: types.Message):
    btns = [
        [InlineKeyboardButton(text="👑 VIP 1 месяц — 5000 SNC", callback_data="buy_vip_1")],
        [InlineKeyboardButton(text="👑 VIP 3 месяца — 14000 SNC", callback_data="buy_vip_3")],
        [InlineKeyboardButton(text="👑 VIP 12 месяцев — 45000 SNC", callback_data="buy_vip_12")],
        [InlineKeyboardButton(text="💎 VIP НАВСЕГДА — 100000 SNC", callback_data="buy_vip_forever")],
        [InlineKeyboardButton(text="⭐ Premium 1 месяц — 800 SNC", callback_data="buy_premium_month")],
        [InlineKeyboardButton(text="⭐ Premium 3 месяца — 4000 SNC", callback_data="buy_premium_3months")],
        [InlineKeyboardButton(text="⭐ Premium НАВСЕГДА — 50000 SNC", callback_data="buy_premium_forever")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ]
    await m.answer(
        "🛒 *МАГАЗИН VIP И PREMIUM* 🛒\n\n"
        "👑 VIP даёт права модерации\n"
        "⭐ Premium даёт бонусы к работе",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )

@dp.callback_query(lambda c: c.data.startswith("buy_vip_"))
async def buy_vip(cb: types.CallbackQuery):
    level = cb.data.split("_")[2]
    if level == "forever":
        price = 100000
        name = "💎 VIP НАВСЕГДА"
    else:
        level = int(level)
        prices = {1: 5000, 3: 14000, 12: 45000}
        price = prices[level]
        name = f"👑 VIP {level} месяца"
    
    bal = get_balance(cb.from_user.id)
    
    if bal < price:
        await cb.answer(f"❌ Недостаточно SNC! Нужно {price}, у вас {bal}", show_alert=True)
        return
    
    remove_balance(cb.from_user.id, price)
    await cb.message.answer(f"✅ {name} куплен за {price} SNC!")
    await cb.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_premium_"))
async def buy_premium(cb: types.CallbackQuery):
    level = cb.data.split("_")[2]
    prices = {"month": 800, "3months": 4000, "forever": 50000}
    names = {"month": "⭐ Premium 1 месяц", "3months": "⭐ Premium 3 месяца", "forever": "⭐ Premium НАВСЕГДА"}
    
    price = prices[level]
    name = names[level]
    
    bal = get_balance(cb.from_user.id)
    
    if bal < price:
        await cb.answer(f"❌ Недостаточно SNC! Нужно {price}, у вас {bal}", show_alert=True)
        return
    
    remove_balance(cb.from_user.id, price)
    await cb.message.answer(f"✅ {name} куплен за {price} SNC!")
    await cb.answer()

@dp.callback_query(lambda c: c.data == "close")
async def close_cb(cb: types.CallbackQuery):
    await cb.message.delete()
    await cb.answer()

# ========== ЗАПУСК ==========
async def main():
    print("=" * 50)
    print("🤖 SONARA BOT ЗАПУЩЕН")
    print("✅ /начислить — начислить себе SNC (только владелец)")
    print("✅ /buyt — магазин VIP/Premium")
    print("=" * 50)
    
    while True:
        try:
            await dp.start_polling(bot, skip_updates=True)
        except Exception as e:
            print(f"Ошибка: {e}. Перезапуск через 5 секунд...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())