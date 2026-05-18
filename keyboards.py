from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Купить ГБ", callback_data="buy"),
        InlineKeyboardButton(text="💰 Продать ГБ", callback_data="sell")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals"),
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Поддержка", callback_data="support"),
        InlineKeyboardButton(text="📜 Правила", callback_data="rules")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Рефералы", callback_data="referral"),
        InlineKeyboardButton(text="🛡 Гарант", callback_data="guarantee")
    )
    builder.adjust(2)  # по 2 кнопки в ряд
    return builder.as_markup()

def operator_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора оператора при создании объявления"""
    operators = ["Yota", "Tele2", "MTS", "Билайн", "Мегафон", "Другой"]
    builder = InlineKeyboardBuilder()
    for op in operators:
        builder.add(InlineKeyboardButton(text=op, callback_data=f"op_{op}"))
    builder.adjust(3)  # по 3 кнопки в ряд
    return builder.as_markup()

def deposit_keyboard(pay_url: str, invoice_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для пополнения баланса (ссылка на оплату + проверка)"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Оплатить", url=pay_url))
    builder.row(InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_pay_{invoice_id}"))
    return builder.as_markup()

def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Простая кнопка 'Назад' в меню"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    return builder.as_markup()