from aiogram.fsm.state import State, StatesGroup

class SellAd(StatesGroup):
    waiting_operator = State()      # выбор оператора
    waiting_gb = State()            # сколько ГБ
    waiting_price = State()         # цена
    waiting_region = State()        # выбор региона (из кнопок)
    waiting_custom_region = State() # свой регион текстом
    waiting_transfer = State()      # выбор способа передачи (из кнопок)
    waiting_custom_transfer = State() # свой способ текстом
    waiting_comment = State()       # комментарий
