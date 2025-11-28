from aiogram import F
from aiogram.fsm.state import StatesGroup, State

class AddNewGiveaway(StatesGroup):
    title = State()

class AddNewBot(StatesGroup):
    token = State()

class EditBot(StatesGroup):
    token = State()

class AddSponsor(StatesGroup):
    message = State()
    tag = State()

class EditWinners(StatesGroup):
    amount = State()

class GiveawayStates(StatesGroup):
    choosing_date = State()
    choosing_time = State()

class Rassilka(StatesGroup):
    text = State()
    photo = State()

class AddNewAdmin(StatesGroup):
    user_id = State()

class Win322(StatesGroup):
    winner = State()

class AutoRassilka(StatesGroup):
    text = State()

class Posts(StatesGroup):
    text = State()
    photo = State()
    link = State()
    buttontext = State()
    channel = State()
    photoview = State()
    newpost = State()
    delay = State()