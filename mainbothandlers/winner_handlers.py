from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
from database.models import Giveaway, Bots, Admin, Sponsors
from states.mainstates import EditWinners, Win322
from keyboards.inline import addnewbotcancel_kb, giveaway_kb, mainsettings_kb
from settings import main_bot
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("gawinnersconfig_"))
async def gawinnersconfig(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    await state.set_state(EditWinners.amount)
    await callback.message.edit_text(f"<code>Введите количество победителей в розыгрыше {giveaway.title}</code>",
                                     reply_markup=addnewbotcancel_kb(giveaway))
    await state.update_data(id=id, msg=callback.message.message_id)


@router.message(EditWinners.amount)
async def editwinners(message: Message, state: FSMContext):
    data = await state.get_data()
    id = data.get("id")
    if message.text.isdigit():
        msg = data.get("msg")
        amount = message.text
        await message.delete()
        await Giveaway.filter(id=id).update(winners_amount=amount)
        giveaway = await Giveaway.filter(id=id).first()
        admin = await Admin.filter(admin_id = giveaway.admin).first()

        sponstitles = await Sponsors.filter(giveaway=giveaway.id)
        titleslist = []
        for sponsor in sponstitles:
            titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
        links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
        sponstr = "\n✨ ".join(links)

        await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg, text=f"<code>Это основные настройки розыгрыша {giveaway.title}\n\nКол-во победителей: {giveaway.winners_amount}\n\n{'Дата завершения:' if giveaway.end_type=='auto' else 'Розыгрыш будет завершен вручную'}{giveaway.end_date if giveaway.end_type=='auto' else ''}\n\nСпонсоры: \n✨ {sponstr if sponstr else 'Пока нету...'}</code>", reply_markup=mainsettings_kb(giveaway))

        await state.clear()
    else:
        msg = data.get("msg")
        await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg, text=f"Нужно ввести число!")
        await state.set_state(EditWinners.amount)


@router.callback_query(F.data.startswith("choosewin_"))
async def choosewin(callback:CallbackQuery, state:FSMContext):
    await callback.answer()
    logger.info(f"{callback.data}")
    id = callback.data.split("_")[1]

    giveaway = await Giveaway.filter(id = id).first()

    await callback.message.edit_text("Введи юзернейм пользователя которого хочешь сделать подставным победителем\n\nВАЖНО!!!\nПодставной победитель должен поучаствовать в розыгрыше и выполнить условия", reply_markup= addnewbotcancel_kb(giveaway))

    await state.set_state(Win322.winner)
    await state.update_data(giveaway = giveaway, msg = callback.message.message_id)

@router.message(Win322.winner)
async def selectwin(message: Message, state: FSMContext):
    data = await state.get_data()
    giveaway = data["giveaway"]
    username = message.text.strip()
    msg_id = data["msg"]

    # Проверка на юзернейм
    if not username.startswith("@"):
        await main_bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg_id,
            text="Это не юзернейм, попробуй еще раз",
            reply_markup=addnewbotcancel_kb(giveaway)
        )
        return

    # Обновляем winner322 в любом случае
    await Giveaway.filter(id=giveaway.id).update(winner322=username)

    # Если розыгрыш завершён — пытаемся обновить победителя
    if giveaway.status == 'ended':
        participants = []
        try:
            if giveaway.participants_ended_task:
                participants = json.loads(giveaway.participants_ended_task)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга participants_ended_task: {e}")
            participants = []

        if not participants:
            await main_bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_id,
                text="Нет участников или ошибка в данных.",
                reply_markup=addnewbotcancel_kb(giveaway)
            )
            return

        # Убираем @ из юзернейма
        target_username = username[1:]

        new_winner = None
        for participant in participants:
            if participant["username"] == target_username:
                new_winner = participant
                break

        if not new_winner:
            await main_bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_id,
                text=f"Пользователь {username} не найден среди участников.",
                reply_markup=addnewbotcancel_kb(giveaway)
            )
            return

        # Загружаем текущих победителей
        try:
            current_winners = json.loads(giveaway.winners) if giveaway.winners else []
        except json.JSONDecodeError:
            current_winners = []

        if not current_winners:
            updated_winners = [new_winner]
        else:
            # Заменяем первого победителя
            updated_winners = [new_winner] + current_winners[1:]

        # Сохраняем обновлённый список победителей
        try:
            await Giveaway.filter(id=giveaway.id).update(winners=json.dumps(updated_winners, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Ошибка сохранения winners: {e}")
            await main_bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_id,
                text="Ошибка при сохранении победителя.",
                reply_markup=addnewbotcancel_kb(giveaway)
            )
            return

    # Подтверждение
    await main_bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg_id,
        text="✅ Успешно добавлен подставной победитель",
        reply_markup=addnewbotcancel_kb(giveaway)
    )

    await state.clear()
    

