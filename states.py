from aiogram.fsm.state import State, StatesGroup

class SellAd(StatesGroup):
    """Состояния для создания объявления о продаже"""
    waiting_operator = State()
    waiting_gb = State()
    waiting_price = State()
    waiting_region = State()
    waiting_transfer = State()
    waiting_comment = State()

class BuyFilter(StatesGroup):
    """Состояния для фильтрации объявлений при покупке (опционально)"""
    waiting_operator = State()
    waiting_region = State()
    waiting_max_price = State()
    waiting_min_gb = State()