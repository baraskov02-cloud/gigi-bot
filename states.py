from aiogram.fsm.state import State, StatesGroup

class SellAd(StatesGroup):
    waiting_operator = State()
    waiting_gb = State()
    waiting_price = State()
    waiting_region = State()
    waiting_transfer = State()
    waiting_comment = State()
