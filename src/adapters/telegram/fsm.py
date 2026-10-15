"""FSM states for multi-step dialogs."""

from aiogram.fsm.state import State, StatesGroup


class PriceStates(StatesGroup):
    """Waiting for executor to type the item price. State data: {"item_id": int}."""

    waiting_price = State()


class QtyStates(StatesGroup):
    """Waiting for executor to type the item quantity. State data: {"item_id": int}."""

    waiting_qty = State()


class RepaymentStates(StatesGroup):
    """Executor records a repayment. State data: {"amount_kop": int}."""

    waiting_amount = State()
    waiting_note = State()
