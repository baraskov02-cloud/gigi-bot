from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu() -> InlineKeyboardMarkup:
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
    builder.adjust(2)
    return builder.as_markup()

def back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu"))
    return builder.as_markup()

def operator_choice() -> InlineKeyboardMarkup:
    operators = ["Yota", "Tele2", "MTS", "Билайн", "Мегафон", "Другой"]
    builder = InlineKeyboardBuilder()
    for op in operators:
        builder.add(InlineKeyboardButton(text=op, callback_data=f"op_{op}"))
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_menu"))
    return builder.as_markup()

def confirm_ad() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Опубликовать", callback_data="publish_ad"))
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_menu"))
    return builder.as_markup()

def deposit_menu(pay_url: str, invoice_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Оплатить", url=pay_url))
    builder.row(InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_pay_{invoice_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="profile"))
    return builder.as_markup()

def profile_actions() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit"),
        InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals")
    )
    builder.row(InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu"))
    return builder.as_markup()

def buy_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔍 Все объявления", callback_data="list_ads"))
    builder.row(InlineKeyboardButton(text="⚙️ Фильтры (скоро)", callback_data="filters"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    return builder.as_markup()

def deal_actions(deal_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить получение", callback_data=f"confirm_{deal_id}"),
        InlineKeyboardButton(text="⚠️ Спор", callback_data=f"dispute_{deal_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu"))
    return builder.as_markup()

def my_deals_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📥 Покупки", callback_data="my_purchases"),
        InlineKeyboardButton(text="📤 Продажи", callback_data="my_sales")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    return builder.as_markup()
