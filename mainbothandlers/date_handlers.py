# handlers/date_handlers.py
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
from database.models import Giveaway, Bots, Admin
from states.mainstates import GiveawayStates
from keyboards.inline import generate_calendar, acceptenddateconfig, giveaway_kb, acceptend
from settings import main_bot
from datetime import datetime
import logging
import asyncio
import json
from settings import config
from main import scheduler, endga

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data.startswith("gaendconfig_"))
async def editenddateaccept(callback: CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    if giveaway.end_date:
        scheduled_datetime = datetime.strptime(giveaway.end_date, "%Y-%m-%d %H:%M:%S")
        formatted_datetime = scheduled_datetime.strftime("%d.%m.%Y %H:%M")
    else:
        formatted_datetime = "<b>Вручную</b>"
    try:
        await callback.message.edit_text(f"Сейчас установлена дата окончания: {formatted_datetime}, выберите новую, если нужно",
                                     reply_markup=acceptenddateconfig(id))
    except:
        pass


@router.callback_query(F.data.startswith("accepteditdate_"))
async def addenddate(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    id = callback.data.split("_")[1]
    await state.clear()
    giveaway = await Giveaway.filter(id=id).first()
    if giveaway.end_date:
        await callback.message.edit_text(f"Выберите новую дату для окончания розыгрыша",
                                         reply_markup=await generate_calendar(giveaway_id=giveaway.id))
    else:
        await callback.message.edit_text(f"установите дату окончания, если нужно, иначе нажмите назад чтобы завершать вручную",
                                         reply_markup=await generate_calendar(giveaway_id=giveaway.id))
    await state.set_state(GiveawayStates.choosing_date)
    await state.update_data(id=id, giveaway_id=giveaway.id)


@router.callback_query(F.data.startswith("prev:") | F.data.startswith("next:"))
async def calendar_nav(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    _, year, month, giveaway_id_str = callback.data.split(":")
    now = datetime.now()
    if int(year) < now.year or (int(year) == now.year and int(month) < now.month):
        await callback.answer("Нельзя выбрать прошедший месяц", show_alert=True)
        return
    try:
        giveaway = await Giveaway.filter(id=int(giveaway_id_str)).first()
        if not giveaway:
            await callback.answer("Розыгрыш не найден", show_alert=True)
            logger.error(f"Розыгрыш с id={giveaway_id_str} не найден для навигации по календарю")
            return
    except ValueError:
        await callback.answer("Ошибка данных календаря", show_alert=True)
        logger.error(f"Неверный ID розыгрыша в callback_data: {giveaway_id_str}")
        return
    await callback.message.edit_reply_markup(
        reply_markup=await generate_calendar(int(year), int(month), giveaway_id=giveaway.id))


@router.callback_query(F.data.startswith("date:"))
async def date_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    _, year, month, day, giveaway_id_str = callback.data.split(":")
    selected_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    await state.update_data(selected_date=selected_date)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    now = datetime.now()
    selected_datetime = datetime(int(year), int(month), int(day))
    try:
        giveaway_id = int(giveaway_id_str)
    except ValueError:
        await callback.answer("Ошибка данных календаря", show_alert=True)
        logger.error(f"Неверный ID розыгрыша в callback_data даты: {giveaway_id_str}")
        return
    available_times = []
    for hour in range(24):
        for minute in [0, 30]:
            time_obj = datetime(int(year), int(month), int(day), hour, minute)
            if selected_datetime.date() > now.date() or (
                    selected_datetime.date() == now.date() and time_obj > now):
                time_str = f"{hour:02d}:{minute:02d}"
                available_times.append(time_str)
    if not available_times:
        await callback.message.edit_text(
            f"❌ На дату {selected_date} больше нет доступного времени.\nПожалуйста, выберите другую дату.",
            reply_markup=await generate_calendar(int(year), int(month), giveaway_id=giveaway_id)
        )
        await state.set_state(GiveawayStates.choosing_date)
        return
    for time_str in available_times:
        builder.button(text=time_str, callback_data=f"time:{time_str}:{giveaway_id}")
    builder.button(text="❌ Отмена", callback_data=f"cancel_time{giveaway_id}")
    builder.adjust(4)
    await callback.message.edit_text(f"Вы выбрали дату: {selected_date}\nТеперь выберите время:",
                                     reply_markup=builder.as_markup())
    await state.set_state(GiveawayStates.choosing_time)
    await state.update_data(giveaway_id=giveaway_id)


@router.callback_query(F.data.startswith("time:"))
async def time_selected(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        print(callback.data)
        _, hour, minute, id = callback.data.split(":")
        data = await state.get_data()
        selected_date = data["selected_date"]
        year, month, day = map(int, selected_date.split("-"))
        scheduled_datetime = datetime(year, month, day, int(hour), int(minute))
        await Giveaway.filter(id=id).update(end_date=scheduled_datetime, end_type="auto")
        formatted_datetime = scheduled_datetime.strftime("%d.%m.%Y %H:%M")
        await callback.message.edit_text(f"Сейчас установлена дата окончания: {formatted_datetime}, выберите новую, если нужно",
                                        reply_markup=await generate_calendar(giveaway_id=id))
        
    except Exception as e:
        logger.error(f"Ошибка установления даты: {e}")


@router.callback_query(F.data.startswith("gaend_"))
async def endgamanual(callback: CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]
    await callback.message.edit_text("Вы точно хотите завершить розыгрыш(процесс не обратим)", reply_markup=acceptend(id))
    

@router.callback_query(F.data.startswith("end_"))
async def acceptending(callback:CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]
    msg = callback.message.message_id
    chat = callback.from_user.id
    giveaway = await Giveaway.filter(id=id).first()
    asyncio.create_task(endga(id, chat, msg))
    logger.info(f"Розыгрыш {giveaway.title} передан в завершение")


@router.callback_query(F.data.startswith("deletedate_"))
async def delete_date(callback: CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]
    await Giveaway.filter(id=id).update(end_date="", end_type="manual")
    
    try:
        scheduler.remove_job(id = f"giveaway_{id}")
        giveaway = await Giveaway.filter(id=id).first()
        admin = await Admin.filter(admin_id = giveaway.admin)
        if giveaway.status == "new" and giveaway.bot:
            bot = await Bots.filter(id=giveaway.bot).first()
            
            await callback.message.edit_text(
                f"Розыгрыш {giveaway.title}\n@{bot.username}\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!</code>",
                reply_markup=giveaway_kb(giveaway, admin)
            )
        else:
            await callback.message.edit_text(
                f"Розыгрыш {giveaway.title}\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!</code>",
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
            await callback.message.edit_text(
                f"Розыгрыш {giveaway.title} завершен\n@{bot.username}\nКоличество участников: {len(json.loads(giveaway.participants))}\n-зашли в бота: {len(json.loads(giveaway.participants))}\n-выполнили задания: {len(json.loads(giveaway.participants_ended_task))}\n\nПобедители:\n{winnersstr}",
                reply_markup=giveaway_kb(giveaway, admin), parse_mode="HTML", disable_web_page_preview=True
            )
    except Exception as e:
        logger.info(f"Ошибка удаления даты: {e}")
