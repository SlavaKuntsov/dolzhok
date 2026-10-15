"""FSM states for multi-step dialogs."""

from aiogram.fsm.state import State, StatesGroup


class PriceStates(StatesGroup):
    """Waiting for son to type the item price. State data: {"item_id": int}."""

    waiting_price = State()
