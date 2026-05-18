import asyncio, re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import aiosqlite

from config import ADMIN_ID
from database import DB_NAME, ensure_user
from keyboards import *
from states import SellAd
from crypto_bot import create_invoice, check_invoice, transfer_money

router = Router()

# ---------- Функция для безопасного вывода в Markdown ----------
def escape_md(text: str) -> str:
    if not text:
        return text
    return re.sub(r'([_*`\[\]()~\\])', r'\\\1', text)

# ---------- Проверка адекватности текста ----------
def is_valid_text(text: str, min_len=2, max_len=50) -> bool:
    """Текст должен содержать буквы, не быть только цифрами/спецсимволами"""
    if len(text) < min_len or len(text) > max_len:
        return False
    # Хотя бы одна буква (русская или латиница) и нет запрещённых символов вроде <> (для безопасности)
    if re.search(r'[<>]', text):
        return False
    # Должна быть хотя бы одна буква или пробел (чтобы отсеять #### или 12345)
    if not re.search(r'[а-яА-ЯёЁa-zA-Z]', text):
        return False
    return True

# ==================== /start ====================
@router.message(CommandStart())
async def cmd_start(message: Message):
    await ensure_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "👋 Добро пожаловать в **Gigi Bot** — безопасную биржу гигабайтов!\n"
        "Выберите действие:",
        reply_markup=main_menu()
    )

@router.callback_query(F.data == "back_to_menu")
async def go_back(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())

# ==================== Профиль ====================
@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    uid = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        row = await db.execute("SELECT username, balance, rating, deals_count FROM users WHERE user_id=?", (uid,))
        user = await row.fetchone()
    if not user:
        await callback.answer("Сначала нажмите /start")
        return
    uname, bal, rating, deals = user
    uname_safe = escape_md(uname) if uname else "нет"
    text = (
        f"👤 **Профиль**\n"
        f"🆔 ID: `{uid}`\n"
        f"👤 Username: @{uname_safe}\n"
        f"💰 Баланс: **{bal:.2f} USDT**\n"
        f"⭐ Рейтинг: {rating:.1f}/5\n"
        f"📊 Сделок: {deals}\n"
    )
    await callback.message.edit_text(text, reply_markup=profile_actions())

# ==================== Пополнение ====================
@router.callback_query(F.data == "deposit")
async def start_deposit(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите сумму пополнения в USDT (минимум 1):")
    await state.set_state("wait_deposit_amount")

@router.message(F.text.regexp(r"^\d+(\.\d+)?$"), StateFilter("wait_deposit_amount"))
async def process_deposit_amount(message: Message, state: FSMContext):
    amount = float(message.text)
    if amount < 1:
        await message.answer("Минимальная сумма 1 USDT.")
        return
    try:
        pay_url, invoice_id = await create_invoice(message.from_user.id, amount)
    except Exception as e:
        await message.answer(f"Ошибка создания счёта: {e}")
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO transactions (user_id, type, amount, status, external_id) VALUES (?, 'deposit', ?, 'pending', ?)",
                         (message.from_user.id, amount, invoice_id))
        await db.commit()
    await message.answer(
        f"Счёт на {amount} USDT создан. После оплаты нажмите «Я оплатил».",
        reply_markup=deposit_menu(pay_url, invoice_id)
    )
    await state.clear()

@router.callback_query(F.data.startswith("check_pay_"))
async def check_payment(callback: CallbackQuery):
    invoice_id = callback.data.split("_")[2]
    status = await check_invoice(invoice_id)
    if status == "paid":
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("SELECT status, amount FROM transactions WHERE external_id=?", (invoice_id,))
            trans = await cur.fetchone()
            if trans and trans[0] != 'completed':
                amount = trans[1]
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, callback.from_user.id))
                await db.execute("UPDATE transactions SET status = 'completed' WHERE external_id = ?", (invoice_id,))
                await db.commit()
                await callback.answer("Баланс пополнен! 🎉")
                await callback.message.edit_text(f"Баланс пополнен на {amount} USDT.")
            else:
                await callback.answer("Счёт уже обработан.")
    else:
        await callback.answer("Оплата ещё не прошла. Попробуйте позже.", show_alert=True)

# ==================== Продажа (Tele2 + умный ввод) ====================
@router.callback_query(F.data == "sell")
async def start_sell(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите оператора:", reply_markup=operator_choice())
    await state.set_state(SellAd.waiting_operator)

@router.callback_query(SellAd.waiting_operator, F.data.startswith("op_"))
async def choose_operator(callback: CallbackQuery, state: FSMContext):
    operator = callback.data.split("_")[1]  # Tele2
    await state.update_data(operator=operator)
    await callback.message.edit_text("Сколько ГБ продаёте? (целое число)")
    await state.set_state(SellAd.waiting_gb)

@router.message(SellAd.waiting_gb)
async def process_gb(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите целое число.")
        return
    gb = int(message.text)
    if gb <= 0:
        await message.answer("Число должно быть больше 0.")
        return
    await state.update_data(gb=gb)
    await message.answer("Укажите цену за всё в USDT:")
    await state.set_state(SellAd.waiting_price)

@router.message(SellAd.waiting_price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
    except:
        await message.answer("Введите число, например 5.5")
        return
    if price <= 0:
        await message.answer("Цена должна быть положительной.")
        return
    await state.update_data(price=price)
    await message.answer("Выберите регион:", reply_markup=region_choice())
    await state.set_state(SellAd.waiting_region)

# Регион: выбор из кнопок
@router.callback_query(SellAd.waiting_region, F.data.startswith("region_"))
async def choose_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split("_", 1)[1]  # "Москва" и т.д.
    if region == "Другой":
        await callback.message.edit_text("Напишите ваш регион (город, область). Только буквы, пробелы и дефис (2-50 символов):")
        await state.set_state(SellAd.waiting_custom_region)
        return
    await state.update_data(region=region)
    await callback.message.edit_text("Выберите способ передачи:", reply_markup=transfer_choice())
    await state.set_state(SellAd.waiting_transfer)

# Обработчик своего региона
@router.message(SellAd.waiting_custom_region)
async def custom_region(message: Message, state: FSMContext):
    region = message.text.strip()
    if not is_valid_text(region, min_len=2, max_len=50):
        await message.answer("Некорректный регион. Используйте только буквы, пробелы, дефис (2-50 символов). Попробуйте ещё раз:")
        return
    await state.update_data(region=escape_md(region))
    await message.answer("Выберите способ передачи:", reply_markup=transfer_choice())
    await state.set_state(SellAd.waiting_transfer)

# Способ передачи: выбор из кнопок
@router.callback_query(SellAd.waiting_transfer, F.data.startswith("transfer_"))
async def choose_transfer(callback: CallbackQuery, state: FSMContext):
    method = callback.data.split("_", 1)[1]
    if method == "Другой":
        await callback.message.edit_text("Опишите способ передачи (2-50 символов, только буквы, цифры, пробелы, дефис):")
        await state.set_state(SellAd.waiting_custom_transfer)
        return
    await state.update_data(transfer=method)
    await callback.message.edit_text("Добавьте комментарий (или поставьте «-», если не нужно):")
    await state.set_state(SellAd.waiting_comment)

# Обработчик своего способа передачи
@router.message(SellAd.waiting_custom_transfer)
async def custom_transfer(message: Message, state: FSMContext):
    method = message.text.strip()
    if not is_valid_text(method, min_len=2, max_len=50):
        await message.answer("Некорректное описание. Используйте буквы, цифры, пробелы, дефис (2-50 символов). Попробуйте ещё раз:")
        return
    await state.update_data(transfer=escape_md(method))
    await message.answer("Добавьте комментарий (или поставьте «-», если не нужно):")
    await state.set_state(SellAd.waiting_comment)

# Комментарий
@router.message(SellAd.waiting_comment)
async def process_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    raw_comment = message.text.strip()
    if raw_comment == '-':
        comment = ''
    else:
        # Проверка на адекватность (длина до 200, и чтобы был смысл)
        if len(raw_comment) > 200:
            await message.answer("Слишком длинный комментарий (макс 200 символов). Сократите:")
            return
        # Проверка на бессмысленный набор символов: должна быть хотя бы одна буква, или это могут быть цифры с буквами
        if not re.search(r'[а-яА-ЯёЁa-zA-Z0-9]', raw_comment):
            await message.answer("Комментарий должен содержать осмысленный текст. Попробуйте ещё раз:")
            return
        comment = escape_md(raw_comment)
    await state.update_data(comment=comment)
    preview = (
        f"📡 **Проверьте объявление**\n\n"
        f"Оператор: {data['operator']}\n"
        f"ГБ: {data['gb']}\n"
        f"Цена: {data['price']:.2f} USDT\n"
        f"Регион: {data['region']}\n"
        f"Способ: {data['transfer']}\n"
        f"Комментарий: {comment or 'нет'}\n\n"
        "Всё верно?"
    )
    await message.answer(preview, reply_markup=confirm_ad())
    await state.set_state("confirm_ad")

@router.callback_query(F.data == "publish_ad")
async def publish_ad(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO ads (seller_id, operator, gb, price, region, transfer_method, comment) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (callback.from_user.id, data['operator'], data['gb'], data['price'],
             data['region'], data['transfer'], data.get('comment', ''))
        )
        await db.commit()
    await callback.message.edit_text("✅ Объявление успешно опубликовано!", reply_markup=main_menu())
    await state.clear()

# ==================== Покупка ====================
@router.callback_query(F.data == "buy")
async def show_buy_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выберите действие:", reply_markup=buy_menu())

@router.callback_query(F.data == "list_ads")
async def list_ads(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("""
            SELECT a.id, a.operator, a.gb, a.price, a.region, a.seller_id,
                   u.username, u.rating, u.deals_count
            FROM ads a JOIN users u ON a.seller_id = u.user_id
            WHERE a.status='active'
            ORDER BY a.created_at DESC LIMIT 5
        """)
        ads = await cur.fetchall()
    if not ads:
        await callback.answer("Нет активных объявлений.")
        return
    lines = ["📦 **Актуальные лоты:**\n"]
    builder = InlineKeyboardBuilder()
    for ad in ads:
        ad_id, op, gb, price, region, seller_id, uname, rating, deals = ad
        uname_safe = escape_md(uname) if uname else "нет"
        region_safe = escape_md(region)
        lines.append(
            f"#{ad_id} {op} · {gb}ГБ · {price:.2f} USDT\n"
            f"📍 {region_safe} | 👤 @{uname_safe}\n"
            f"⭐ {rating:.1f} · {deals} сделок\n"
        )
        builder.row(InlineKeyboardButton(text=f"Купить #{ad_id}", callback_data=f"buyad_{ad_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="buy"))
    await callback.message.edit_text("\n".join(lines), reply_markup=builder.as_markup(), disable_web_page_preview=True)

@router.callback_query(F.data.startswith("buyad_"))
async def initiate_deal(callback: CallbackQuery):
    ad_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT seller_id, price, operator, gb, region FROM ads WHERE id=? AND status='active'", (ad_id,))
        ad = await cur.fetchone()
    if not ad:
        await callback.answer("Объявление уже неактивно.")
        return
    seller_id, price, operator, gb, region = ad
    buyer_id = callback.from_user.id
    if buyer_id == seller_id:
        await callback.answer("Нельзя купить свой же лот.")
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (buyer_id,))
        bal = await cur.fetchone()
    if not bal or bal[0] < price:
        await callback.answer("Недостаточно средств на балансе. Пополните счёт.", show_alert=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, buyer_id))
        cur = await db.execute("INSERT INTO deals (ad_id, buyer_id, seller_id, amount, status) VALUES (?, ?, ?, ?, 'paid')",
                              (ad_id, buyer_id, seller_id, price))
        deal_id = cur.lastrowid
        await db.execute("UPDATE ads SET status = 'in_deal' WHERE id=?", (ad_id,))
        await db.execute("INSERT INTO transactions (user_id, type, amount, status) VALUES (?, 'purchase', ?, 'completed')",
                         (buyer_id, price))
        await db.commit()
    buyer_uname = escape_md(callback.from_user.username) if callback.from_user.username else "нет"
    await callback.bot.send_message(
        seller_id,
        f"🎉 Ваш лот #{ad_id} ({operator} {gb}ГБ) купили за {price} USDT.\n"
        f"Покупатель: @{buyer_uname}\n"
        f"Переведите гигабайты и ожидайте подтверждения."
    )
    await callback.message.edit_text(
        f"✅ Сделка создана! Вы купили {gb}ГБ {operator} за {price} USDT.\n"
        "Ожидайте перевод от продавца. После получения нажмите «Подтвердить получение».",
        reply_markup=deal_actions(deal_id)
    )

# ==================== Подтверждение и спор ====================
@router.callback_query(F.data.startswith("confirm_"))
async def confirm_deal(callback: CallbackQuery):
    deal_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT buyer_id, seller_id, amount, status FROM deals WHERE id=?", (deal_id,))
        deal = await cur.fetchone()
        if not deal or deal[3] != 'paid':
            await callback.answer("Сделка не найдена или уже завершена.")
            return
        buyer_id, seller_id, amount, _ = deal
        if callback.from_user.id != buyer_id:
            await callback.answer("Только покупатель может подтвердить.")
            return
        commission = amount * 0.05
        seller_amount = amount - commission
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (seller_amount, seller_id))
        await db.execute("UPDATE deals SET status = 'completed', confirmed_at = CURRENT_TIMESTAMP WHERE id = ?", (deal_id,))
        await db.execute("INSERT INTO transactions (user_id, type, amount, status) VALUES (?, 'sale', ?, 'completed')",
                         (seller_id, seller_amount))
        await db.execute("UPDATE users SET deals_count = deals_count + 1 WHERE user_id IN (?, ?)", (buyer_id, seller_id))
        await db.commit()
    await callback.message.edit_text("✅ Сделка успешно завершена! Продавец получил оплату за вычетом комиссии 5%.")
    await callback.bot.send_message(seller_id, f"✅ Покупатель подтвердил получение. Вам начислено {seller_amount:.2f} USDT.")

@router.callback_query(F.data.startswith("dispute_"))
async def open_dispute(callback: CallbackQuery, state: FSMContext):
    deal_id = int(callback.data.split("_")[1])
    await callback.message.edit_text("Опишите причину спора:")
    await state.set_state("dispute_reason")
    await state.update_data(deal_id=deal_id)

@router.message(F.state == "dispute_reason")
async def submit_dispute(message: Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data['deal_id']
    reason = escape_md(message.text)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO disputes (deal_id, initiator_id, reason) VALUES (?, ?, ?)",
                         (deal_id, message.from_user.id, reason))
        await db.execute("UPDATE deals SET status = 'disputed' WHERE id = ?", (deal_id,))
        await db.commit()
        initiator_uname = escape_md(message.from_user.username) if message.from_user.username else "нет"
        await message.bot.send_message(ADMIN_ID, f"⚠️ Спор по сделке #{deal_id}\nИнициатор: @{initiator_uname}\nПричина: {reason}")
    await message.answer("Спор открыт. Администратор свяжется с вами.", reply_markup=main_menu())
    await state.clear()

# ==================== Мои сделки ====================
@router.callback_query(F.data == "my_deals")
async def my_deals_menu_handler(callback: CallbackQuery):
    await callback.message.edit_text("Выберите категорию сделок:", reply_markup=my_deals_menu())

@router.callback_query(F.data == "my_purchases")
async def my_purchases(callback: CallbackQuery):
    uid = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("""
            SELECT d.id, a.operator, a.gb, d.amount, d.status, a.seller_id, u.username
            FROM deals d
            JOIN ads a ON d.ad_id = a.id
            JOIN users u ON a.seller_id = u.user_id
            WHERE d.buyer_id=? AND d.status IN ('paid','completed','disputed')
            ORDER BY d.created_at DESC LIMIT 5
        """, (uid,))
        rows = await cur.fetchall()
    if not rows:
        await callback.answer("У вас пока нет покупок.")
        return
    lines = ["📥 **Ваши покупки:**\n"]
    for deal_id, op, gb, amount, status, seller_id, uname in rows:
        status_text = {"paid": "⏳ Ожидает", "completed": "✅ Завершено", "disputed": "⚠️ Спор"}.get(status, status)
        uname_safe = escape_md(uname) if uname else "нет"
        lines.append(f"#{deal_id} {op} {gb}ГБ — {amount} USDT | {status_text}\nПродавец: @{uname_safe}")
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="my_deals"))
    await callback.message.edit_text("\n".join(lines), reply_markup=builder.as_markup())

@router.callback_query(F.data == "my_sales")
async def my_sales(callback: CallbackQuery):
    uid = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("""
            SELECT d.id, a.operator, a.gb, d.amount, d.status, d.buyer_id, u.username
            FROM deals d
            JOIN ads a ON d.ad_id = a.id
            JOIN users u ON d.buyer_id = u.user_id
            WHERE d.seller_id=? AND d.status IN ('paid','completed','disputed')
            ORDER BY d.created_at DESC LIMIT 5
        """, (uid,))
        rows = await cur.fetchall()
    if not rows:
        await callback.answer("У вас пока нет продаж.")
        return
    lines = ["📤 **Ваши продажи:**\n"]
    for deal_id, op, gb, amount, status, buyer_id, uname in rows:
        status_text = {"paid": "⏳ Ожидает", "completed": "✅ Завершено", "disputed": "⚠️ Спор"}.get(status, status)
        uname_safe = escape_md(uname) if uname else "нет"
        lines.append(f"#{deal_id} {op} {gb}ГБ — {amount} USDT | {status_text}\nПокупатель: @{uname_safe}")
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="my_deals"))
    await callback.message.edit_text("\n".join(lines), reply_markup=builder.as_markup())

# ==================== Остальные кнопки ====================
@router.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    await callback.message.edit_text(
        "📧 По всем вопросам обращайтесь: **@bapawko8**\n\n"
        "Опишите проблему, и мы поможем.",
        reply_markup=back_to_menu()
    )

@router.callback_query(F.data == "rules")
async def rules(callback: CallbackQuery):
    await callback.message.edit_text(
        "📜 **Правила сервиса:**\n"
        "1. Запрещено мошенничество.\n"
        "2. Соблюдайте условия сделок.\n"
        "3. При спорах обращайтесь к гаранту.",
        reply_markup=back_to_menu()
    )

@router.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):
    await callback.answer("Реферальная система будет запущена позже.", show_alert=True)

@router.callback_query(F.data == "guarantee")
async def guarantee(callback: CallbackQuery):
    await callback.answer("Гарант обеспечивает безопасность сделок и разрешает споры.", show_alert=True)
