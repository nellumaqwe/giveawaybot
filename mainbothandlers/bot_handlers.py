from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Router, F, Bot
from database.models import Giveaway, Bots, Admin
from states.mainstates import AddNewBot, EditBot
from keyboards.inline import addnewbotcancel_kb, configgabot_kb, giveaway_kb
from main import create_baby_bot
from settings import main_bot
import re
import json
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("addgabot_"))
async def create_new_bot(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    if giveaway.bot:
        await callback.message.edit_text("Отправь мне токен бота от @botfather.\n\nДля этого:\n 1. Открой отца ботов - @BotFather\n 2. Создай нового бота (команда /newbot)\n 3. Отец отправит тебе API token твоего личного бота (формата 123456789:ASDFABC-DEF1234gh) - скопируй этот токен и отправь его мне.\n\nВажно! Не используй бота, которого ты привязывал к другому сервису (или к другим ботам)!\n\nЯ жду токен..", reply_markup=addnewbotcancel_kb(giveaway))
        await state.set_state(EditBot.token)
    else:
        await callback.message.edit_text("Отправь мне токен бота от @botfather.\n\nДля этого:\n 1. Открой отца ботов - @BotFather\n 2. Создай нового бота (команда /newbot)\n 3. Отец отправит тебе API token твоего личного бота (формата 123456789:ASDFABC-DEF1234gh) - скопируй этот токен и отправь его мне.\n\nВажно! Не используй бота, которого ты привязывал к другому сервису (или к другим ботам)!\n\nЯ жду токен..", reply_markup=addnewbotcancel_kb(giveaway))
        await state.set_state(AddNewBot.token)
    await state.update_data(id=id, msg=callback.message.message_id)


@router.message(AddNewBot.token)
async def startnewbot(message: Message, state: FSMContext):
    data = await state.get_data()
    id = data.get("id")
    msg = data.get("msg")
    token = message.text
    pattern = r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$'
    await state.clear()
    bot = Bot(token=token)
    username = await bot.get_me()
    if re.fullmatch(pattern, token):
        asyncio.create_task(create_baby_bot(token, username.username, id, message.from_user.id))
        giveaway = await Giveaway.filter(id=id).first()
        await message.delete()
        for i in range(6):
            if i<=3:    
                await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg, text=f"Проверяю{'.'*i}")
                await asyncio.sleep(1)
            else:
                await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg, text=f"Проверяю{'.'*(i-3)}")
                await asyncio.sleep(1)

        await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg,
                                         text=f"Настройки лендинг-бота:\nБот: @{username.username}",
                                         reply_markup=configgabot_kb(giveaway))
    else:
        await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg, text = "Неправильно введен токен, пример верного: 123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11\nПопробуйте еще раз:")
        await state.set_state(AddNewBot.token)


@router.message(EditBot.token)
async def startnewbot(message: Message, state: FSMContext):
    data = await state.get_data()
    id = data.get("id")
    msg = data.get("msg")
    giveaway = await Giveaway.filter(id=id).first()
    
    
    token = message.text
    pattern = r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$'
    await state.clear()
    bot = Bot(token=token)
    username = await bot.get_me()
    if re.fullmatch(pattern, token):
        await Bots.filter(id=giveaway.bot).update(status="deleted_bot")
        asyncio.create_task(create_baby_bot(token, username.username, id, message.from_user.id))
        giveaway = await Giveaway.filter(id=id).first()
        await message.delete()
        for i in range(6):
            if i<=3:    
                await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg, text=f"Проверяю{'.'*i}")
                await asyncio.sleep(1)
            else:
                await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg, text=f"Проверяю{'.'*(i-3)}")
                await asyncio.sleep(1)

        await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg,
                                         text=f"БОТ УСТАНОВЛЕН\n\nНастройки лендинг-бота:\nБот: @{username.username}",
                                         reply_markup=configgabot_kb(giveaway))
    else:
        await message.answer(
            "Неправильно введен токен, пример верного: 123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11\nПопробуйте еще раз:")
        await state.set_state(EditBot.token)


@router.callback_query(F.data.startswith("gabotconfig_"))
async def configgabot(callback: CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    if giveaway.bot:
        bot = await Bots.filter(id=giveaway.bot).first()
        await callback.message.edit_text(f"Настройки лендинг-бота:\nБот: @{bot.username}",
                                         reply_markup=configgabot_kb(giveaway))
    else:
        await callback.message.edit_text(f"Привяжите бота: ", reply_markup=configgabot_kb(giveaway))


@router.callback_query(F.data.startswith("addnewbotcancel_"))
async def addnewbotcancel(callback: CallbackQuery, state: FSMContext):
    
    await callback.answer()
    await state.clear()
    try:
        id = callback.data.split("_")[1]
        # Используем существующую функцию для отображения информации о розыгрыше
        
        giveaway = await Giveaway.filter(id=id).first()
        admin = await Admin.filter(admin_id = giveaway.admin).first()
        if giveaway.status == "new" and giveaway.bot:
            bot = await Bots.filter(id=giveaway.bot).first()
            await callback.message.edit_text(
                f"Розыгрыш: {giveaway.title}\n{giveaway.bot}\n\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!\n\nЗаходи в основные настройки чтобы задать количество участников, указать спосноров или изменить дату завершения розыгрыша,</code>\n\n{'<code>Подставной победитель:</code>' if giveaway.winner322 else '<code>Выйграет случайный участник</code'} {giveaway.winner322 if giveaway.winner322 else ''}",
                reply_markup=giveaway_kb(giveaway, admin)
            )
        if giveaway.status == "new" and not giveaway.bot:
            await callback.message.edit_text(
                f"Розыгрыш: {giveaway.title}\n\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!\n\nЗаходи в основные настройки чтобы задать количество участников, указать спосноров или изменить дату завершения розыгрыша,</code>\n\n{'<code>Подставной победитель:</code>' if giveaway.winner322 else '<code>Выйграет случайный участник</code'} {giveaway.winner322 if giveaway.winner322 else ''}",
                reply_markup=giveaway_kb(giveaway, admin)
            )
        if giveaway.status == "started":
            bot = await Bots.filter(id=giveaway.bot).first()
            await callback.message.edit_text(
                f"Розыгрыш {giveaway.title}\n@{bot.username}\n\n🚀 Розыгрыш уже идёт!\n\nКоличество участников:\n-зашли в бота: {len(json.loads(giveaway.participants))}\n-выполнили условия: {len(json.loads(giveaway.participants_ended_task))}\n\nНастройки розыгрыша: \n-количество победителей: {giveaway.winners_amount}\n-нужно пригласить рефералов: {giveaway.required_refs_amount}",
                reply_markup=giveaway_kb(giveaway, admin)
            )
        i = 1
        if giveaway.status == "ended":
            bot = await Bots.filter(id=giveaway.bot).first()
            participants = json.loads(giveaway.participants_ended_task)
            winners = json.loads(giveaway.winners)
            links = []
            for winner in winners:
                if '<' in winner['name']:
                    newwinner = 'Участник'
                else:
                    newwinner = winner['name']
                if winner["username"]:
                    link = f"Место {i} - #{participants.index(winner) + 1} - <a href='https://t.me/{winner['username']}'>{newwinner}</a>"
                else:
                    print(winner["user_id"])
                    link = f"Место {i} - #{participants.index(winner) + 1} - <a href='tg://user?id={winner['user_id']}'>{newwinner}</a>"              
                    links.append(link)
                i += 1
            winnersstr = "\n".join(links)
            if giveaway.winners322_amount or giveaway.winners322_amount_tasks:
                await callback.message.edit_text(
                    f"Розыгрыш {giveaway.title}\n@{bot.username or "Бот не найден, возможно удален"}\n\nРОЗЫГРЫШ ЗАВЕРШЕН!\n\nКоличество участников: \n-зашли в бота: {giveaway.winners322_amount or len(json.loads(giveaway.participants))}\n-выполнили условия: {giveaway.winners322_amount_tasks or len(json.loads(giveaway.participants_ended_task))}\n\nПобедители:\n{winnersstr}",
                    reply_markup=giveaway_kb(giveaway, admin), parse_mode="HTML", disable_web_page_preview=True
                )
                
            else:
                await callback.message.edit_text(
                    f"Розыгрыш {giveaway.title}\n@{bot.username or "Бот не найден, возможно удален"}\n\nРОЗЫГРЫШ ЗАВЕРШЕН!\n\nКоличество участников: \n-зашли в бота: {len(json.loads(giveaway.participants))}\n-выполнили условия: {len(json.loads(giveaway.participants_ended_task))}\n\nПобедители:\n{winnersstr}",
                    reply_markup=giveaway_kb(giveaway, admin), parse_mode="HTML", disable_web_page_preview=True
                )
    except Exception as e:
        logger.info(f"Ошибка индекса: {e}")
