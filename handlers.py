import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import aiosqlite

from config import ADMIN_ID
from database import DB_NAME, ensure_user
from keyboards import (
    main_menu, operator_keyboard, deposit_keyboard,
    back_to_menu_keyboard
)
from states import SellAd
from crypto_bot import create_invoice, check_invoice, transfer_money

router = Router()

# ==================== /start и меню ====================

@router.message(CommandStart())
async def cmd_start(message: Message):
    await ensure_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "Добро пожаловать в <b>Gigi Bot</b> — биржу гигабайтов!\n"
        "Здесь ты можешь купить или продать мобильные гигабайты абсолютно безопасно.\n"
        "Выбери действие:",
        reply_markup=main_menu()
    )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu()
    )

# ==================== Профиль и баланс ====================

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT username, balance, rating, deals_count FROM users WHERE user_id=?",
            (user_id,)
        )
        user = await cursor.fetchone()
    if not user:
        await callback.message.edit_text("Сначала нажми /start")
        return
    username, balance, rating, deals = user
    text = (
        f"👤 <b>Профиль</b>\n"
        f"ID: {user_id}\n"
        f"Username: @{username or 'нет'}\n"
        f"Баланс: {balance:.2f} 💎\n"
        f"Рейтинг: {rating:.1f} / 5\n"
        f"Сделок: {deals}\n\n"
        "Действия:"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="deposit"),
        InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

# ==================== Пополнение баланса ====================

@router.callback_query(F.data == "deposit")
async def start_deposit(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите сумму пополнения в USDT (минимум 1):")
    await state.set_state("wait_deposit_amount")

@router.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def process_deposit_amount(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != "wait_deposit_amount":
        return
    amount = float(message.text)
    if amount < 1:
        await message.answer("Минимальная сумма 1 USDT. Попробуйте ещё раз.")
        return
    try:
        pay_url, invoice_id = await create_invoice(message.from_user.id, amount)
    except Exception as e:
        await message.answer(f"Ошибка создания счёта: {e}")
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO transactions (user_id, type, amount, status, external_id) VALUES (?, 'deposit', ?, 'pending', ?)",
            (message.from_user.id, amount, invoice_id)
        )
        await db.commit()
    await message.answer(
        f"Счёт на {amount} USDT создан. Нажмите «Оплатить» и после оплаты нажмите «Я оплатил».",
        reply_markup=deposit_keyboard(pay_url, invoice_id)
    )
    await state.clear()

# ==================== Проверка оплаты ====================

@router.callback_query(F.data.startswith("check_pay_"))
async def check_payment(callback: CallbackQuery):
    invoice_id = callback.data.split("_")[2]
    status = await check_invoice(invoice_id)
    if status == "paid":
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT status, amount FROM transactions WHERE external_id=?", (invoice_id,))
            trans = await cursor.fetchone()
            if trans and trans[0] != 'completed':
                amount = trans[1]
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, callback.from_user.id))
                await db.execute("UPDATE transactions SET status = 'completed' WHERE external_id = ?", (invoice_id,))
                await db.commit()
                await callback.answer("Баланс пополнен! 🎉")
                await callback.message.edit_text(f"Баланс пополнен на {amount} USDT.")
            else:
                await callback.answer("Этот счёт уже обработан.")
    else:
        await callback.answer("Оплата ещё не прошла, попробуйте позже.", show_alert=True)

# ==================== Продажа: создание объявления ====================

@router.callback_query(F.data == "sell")
async def start_sell(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выбери оператора:", reply_markup=operator_keyboard())
    await state.set_state(SellAd.waiting_operator)

@router.callback_query(SellAd.waiting_operator, F.data.startswith("op_"))
async def choose_operator(callback: CallbackQuery, state: FSMContext):
    operator = callback.data.split("_")[1]
    await state.update_data(operator=operator)
    await callback.message.edit_text("Сколько ГБ продаёшь? (целое число)")
    await state.set_state(SellAd.waiting_gb)

@router.message(SellAd.waiting_gb)
async def process_gb(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введи целое число.")
        return
    gb = int(message.text)
    if gb <= 0:
        await message.answer("Должно быть больше 0.")
        return
    await state.update_data(gb=gb)
    await message.answer("Укажи цену за всё (в USDT):")
    await state.set_state(SellAd.waiting_price)

@router.message(SellAd.waiting_price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
    except:
        await message.answer("Введи число (например, 5.5)")
        return
    if price <= 0:
        await message.answer("Цена должна быть положительной.")
        return
    await state.update_data(price=price)
    await message.answer("Регион (например, Москва, или 'Вся Россия'):")
    await state.set_state(SellAd.waiting_region)

@router.message(SellAd.waiting_region)
async def process_region(message: Message, state: FSMContext):
    await state.update_data(region=message.text)
    await message.answer("Способ передачи (например, 'По номеру телефона'):")
    await state.set_state(SellAd.waiting_transfer)

@router.message(SellAd.waiting_transfer)
async def process_transfer(message: Message, state: FSMContext):
    await state.update_data(transfer=message.text)
    await message.answer("Комментарий (или поставь '-', если нет):")
    await state.set_state(SellAd.waiting_comment)

@router.message(SellAd.waiting_comment)
async def process_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    comment = message.text if message.text != '-' else ''
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO ads (seller_id, operator, gb, price, region, transfer_method, comment) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (message.from_user.id, data['operator'], data['gb'], data['price'], data['region'], data['transfer'], comment)
        )
        await db.commit()
    preview = (
        f"✅ <b>Объявление создано!</b>\n\n"
        f"📡 {data['operator']} • {data['gb']} ГБ\n"
        f"📍 {data['region']}\n"
        f"💵 {data['price']:.2f} USDT\n"
        f"Передача: {data['transfer']}\n"
        f"Комментарий: {comment or 'нет'}\n"
        f"Продавец: @{message.from_user.username}\n"
    )
    await message.answer(preview, reply_markup=main_menu())
    await state.clear()

# ==================== Покупка: просмотр и сделка ====================

@router.callback_query(F.data == "buy")
async def start_buy(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔍 Все объявления", callback_data="list_ads"))
    builder.row(InlineKeyboardButton(text="⚙️ Фильтры", callback_data="filters"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    await callback.message.edit_text("Выберите действие:", reply_markup=builder.as_markup())

@router.callback_query(F.data == "list_ads")
async def list_all_ads(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, operator, gb, price, region, seller_id FROM ads WHERE status='active' ORDER BY created_at DESC LIMIT 10"
        )
        ads = await cursor.fetchall()
    if not ads:
        await callback.answer("Нет активных объявлений.")
        return
    text = "<b>📦 Свежие объявления:</b>\n\n"
    builder = InlineKeyboardBuilder()
    for ad in ads:
        ad_id, op, gb, price, region, seller_id = ad
        text += f"#{ad_id} {op} • {gb}ГБ • {region} • {price} USDT\n"
        builder.row(InlineKeyboardButton(text=f"Купить #{ad_id}", callback_data=f"buyad_{ad_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="buy"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("buyad_"))
async def initiate_deal(callback: CallbackQuery):
    ad_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT seller_id, price, operator, gb, region FROM ads WHERE id=? AND status='active'",
            (ad_id,)
        )
        ad = await cursor.fetchone()
    if not ad:
        await callback.answer("Объявление уже неактивно.")
        return
    seller_id, price, operator, gb, region = ad
    buyer_id = callback.from_user.id
    if buyer_id == seller_id:
        await callback.answer("Нельзя купить своё объявление.")
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id=?", (buyer_id,))
        buyer_balance_row = await cursor.fetchone()
    if not buyer_balance_row or buyer_balance_row[0] < price:
        await callback.answer("Недостаточно средств на балансе.", show_alert=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, buyer_id))
        cursor = await db.execute(
            "INSERT INTO deals (ad_id, buyer_id, seller_id, amount, status) VALUES (?, ?, ?, ?, 'paid')",
            (ad_id, buyer_id, seller_id, price)
        )
        deal_id = cursor.lastrowid
        await db.execute("UPDATE ads SET status = 'in_deal' WHERE id=?", (ad_id,))
        await db.execute(
            "INSERT INTO transactions (user_id, type, amount, status) VALUES (?, 'purchase', ?, 'completed')",
            (buyer_id, price)
        )
        await db.commit()
    await callback.bot.send_message(
        seller_id,
        f"🎉 У вас купили гигабайты!\n"
        f"Объявление: {operator} {gb}ГБ за {price} USDT\n"
        f"Покупатель: @{callback.from_user.username}\n\n"
        f"Пожалуйста, переведите гигабайты покупателю и дождитесь подтверждения."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Подтвердить получение", callback_data=f"confirm_{deal_id}"))
    builder.row(InlineKeyboardButton(text="⚠️ Открыть спор", callback_data=f"dispute_{deal_id}"))
    await callback.message.answer(
        f"✅ <b>Сделка создана!</b>\n"
        f"Вы купили {gb}ГБ {operator} за {price} USDT.\n"
        f"Деньги заморожены. Ожидайте перевод гигабайтов от продавца.",
        reply_markup=builder.as_markup()
    )

# ==================== Завершение сделки и спор ====================

@router.callback_query(F.data.startswith("confirm_"))
async def confirm_deal(callback: CallbackQuery):
    deal_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT buyer_id, seller_id, amount, status FROM deals WHERE id=?", (deal_id,))
        deal = await cursor.fetchone()
        if not deal or deal[3] != 'paid':
            await callback.answer("Сделка не найдена или уже завершена.")
            return
        buyer_id, seller_id, amount, _ = deal
        if callback.from_user.id != buyer_id:
            await callback.answer("Только покупатель может подтвердить.", show_alert=True)
            return
        commission = amount * 0.05
        seller_amount = amount - commission
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (seller_amount, seller_id))
        await db.execute("UPDATE deals SET status = 'completed', confirmed_at = CURRENT_TIMESTAMP WHERE id = ?", (deal_id,))
        await db.execute(
            "INSERT INTO transactions (user_id, type, amount, status) VALUES (?, 'sale', ?, 'completed')",
            (seller_id, seller_amount)
        )
        await db.execute("UPDATE users SET deals_count = deals_count + 1 WHERE user_id IN (?, ?)", (buyer_id, seller_id))
        await db.commit()
    await callback.message.edit_text("✅ Сделка успешно завершена! Продавец получил оплату за вычетом комиссии.")
    await callback.bot.send_message(seller_id, f"✅ Покупатель подтвердил получение. Вам начислено {seller_amount} USDT (комиссия 5%).")

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
    reason = message.text
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO disputes (deal_id, initiator_id, reason) VALUES (?, ?, ?)",
            (deal_id, message.from_user.id, reason)
        )
        await db.execute("UPDATE deals SET status = 'disputed' WHERE id = ?", (deal_id,))
        await db.commit()
        await message.bot.send_message(
            ADMIN_ID,
            f"⚠️ Открыт спор по сделке #{deal_id}\nИнициатор: @{message.from_user.username}\nПричина: {reason}"
        )
    await message.answer("Спор открыт. Администратор рассмотрит его в ближайшее время.")
    await state.clear()

# ==================== Остальные кнопки ====================

@router.callback_query(F.data == "my_deals")
async def my_deals(callback: CallbackQuery):
    await callback.answer("Раздел в разработке", show_alert=True)

@router.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    await callback.message.edit_text("По всем вопросам: @support_username", reply_markup=back_to_menu_keyboard())

@router.callback_query(F.data == "rules")
async def rules(callback: CallbackQuery):
    await callback.message.edit_text("Правила пользования биржей...", reply_markup=back_to_menu_keyboard())

@router.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):
    await callback.answer("Реферальная система в разработке", show_alert=True)

@router.callback_query(F.data == "guarantee")
async def guarantee(callback: CallbackQuery):
    await callback.answer("Гарант обеспечивает безопасность сделок.", show_alert=True)