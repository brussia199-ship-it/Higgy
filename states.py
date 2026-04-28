from aiogram.fsm.state import StatesGroup, State

class CreateProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    contact = State()

class WithdrawMoney(StatesGroup):
    amount = State()

class AdminAddBalance(StatesGroup):
    user_id = State()
    amount = State()

class AdminAddSeller(StatesGroup):
    user_id = State()

class AdminDeleteProduct(StatesGroup):
    product_id = State()