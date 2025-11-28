from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Router, F, Bot
from database.models import Giveaway, Bots, Sponsors, Admin, Autopost
from states.mainstates import AddNewGiveaway
from keyboards.inline import giveaway_kb, giveaways_keyb, addnewbotcancel_kb, configgabot_kb, sponsors_kb, gotogiveaway_kb, mainpage_kb, mainsettings_kb, start_kb
from main import create_baby_bot, scheduler
from settings import main_bot, config, ULTIMATE_ADMIN
from mainbothandlers import admins_handlers
import re
import json
import logging
from main import endga
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()



@router.callback_query(F.data == "add_new")
async def add_new_giveaway(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id != int(config["MAINADMIN"]):
        await admins_handlers.update_admin_data(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    await state.set_state(AddNewGiveaway.title)
    try:
        await callback.message.edit_text("Введите название розыгрыша", reply_markup=mainpage_kb())
    except:
        pass
    await state.update_data(msg=callback.message.message_id)


@router.message(AddNewGiveaway.title)
async def save_new_giveaway(message: Message, state: FSMContext):
    try:
        giveaway = await Giveaway.create(title=message.text, admin=message.from_user.id)
        admin = await Admin.filter(admin_id = giveaway.admin).first()
        data = await state.get_data()
        msg = data.get("msg")
        chat_id = message.chat.id
        await main_bot.edit_message_text(
            chat_id=chat_id, message_id=msg,
    text=f"Розыгрыш: {giveaway.title}\n\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!\n\nЗаходи в основные настройки чтобы задать количество участников, указать спосноров или изменить дату завершения розыгрыша, \n\n {'Подставной победитель:' if giveaway.winner322 else 'Выйграет случайный участник'} {giveaway.winner322 if giveaway.winner322 else ''}</code>",
            reply_markup=giveaway_kb(giveaway, admin)
        )
        await message.delete()
    except Exception as e:
        logger.error(f"Failed to create giveaway: {e}")


@router.callback_query(F.data.startswith("giveaway_"))
async def seegiveaway(callback: CallbackQuery):
    await callback.answer()

    try:
        id = callback.data.split("_")[1]
        giveaway = await Giveaway.filter(id=id).first()
        admin = await Admin.filter(admin_id = giveaway.admin).first()
        if giveaway.status == "new" and giveaway.bot:
            bot = await Bots.filter(id=giveaway.bot).first()
            await callback.message.edit_text(
                f"Розыгрыш: {giveaway.title}\n@{bot.username}\n\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!\n\nЗаходи в основные настройки чтобы задать количество участников, указать спосноров или изменить дату завершения розыгрыша,</code>\n\n{'<code>Подставной победитель:</code>' if giveaway.winner322 else '<code>Выйграет случайный участник</code>'} {giveaway.winner322 if giveaway.winner322 else ''}",
                reply_markup=giveaway_kb(giveaway, admin)
            )
        if giveaway.status == "new" and not giveaway.bot:
            await callback.message.edit_text(
                f"Розыгрыш: {giveaway.title}\n\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!\n\nЗаходи в основные настройки чтобы задать количество участников, указать спосноров или изменить дату завершения розыгрыша,</code>\n\n{'<code>Подставной победитель:</code>' if giveaway.winner322 else '<code>Выйграет случайный участник</code>'} {giveaway.winner322 if giveaway.winner322 else ''}",
                reply_markup=giveaway_kb(giveaway, admin)
            )
        if giveaway.status == "started":
            bot = await Bots.filter(id=giveaway.bot).first()
            await callback.message.edit_text(
                f"Розыгрыш {giveaway.title}\n@{bot.username}\n\n🚀 Розыгрыш уже идёт!\n\nКоличество участников:\n-зашли в бота: {len(json.loads(giveaway.participants))}\n-выполнили условия: {len(json.loads(giveaway.participants_ended_task))}\n\nНастройки розыгрыша: \n-количество победителей: {giveaway.winners_amount}\n-нужно пригласить рефералов: {giveaway.required_refs_amount}",
                reply_markup=giveaway_kb(giveaway, admin)
            )
        
        if giveaway.status == "ended":
            i = 1
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
                    reply_markup=giveaway_kb(giveaway, admin), disable_web_page_preview=True, parse_mode="HTML"
                )
                
            else:
                await callback.message.edit_text(
                    f"Розыгрыш {giveaway.title}\n@{bot.username or "Бот не найден, возможно удален"}\n\nРОЗЫГРЫШ ЗАВЕРШЕН!\n\nКоличество участников: \n-зашли в бота: {len(json.loads(giveaway.participants))}\n-выполнили условия: {len(json.loads(giveaway.participants_ended_task))}\n\nПобедители:\n{winnersstr}",
                    reply_markup=giveaway_kb(giveaway, admin), disable_web_page_preview=True, parse_mode="HTML"
                )

    except Exception as e:
        logger.error(f"Ошибка открытия розыгрыша: {e}", exc_info=True)


@router.callback_query(F.data == "mainpage")
async def mainpage(callback: CallbackQuery, state:FSMContext):
    await callback.answer()
    await state.clear()
    from keyboards.inline import start_kb
    
    giveaways = await Giveaway.filter(admin = callback.from_user.id, status = 'started').order_by('-id').all()
    admin = await Admin.filter(admin_id = callback.from_user.id).first()
    bites = await Autopost.filter(admin = callback.from_user.id, rassilkastatus='on').all()
    giveaways_titles = [f"{ga.title} ({len(json.loads(ga.participants_ended_task))} участников)" for ga in giveaways]
    displayed_giveaways = giveaways_titles[:7]
    remaining_count = len(giveaways_titles) - 7
    bites_titles = [bite.title for bite in bites]
    giveaways_str = '\n· '.join(displayed_giveaways) if giveaways_titles else "Нет активных розыгрышей, нажми на кнопку 'РОЗЫГРЫШИ' и создай первый"
    if remaining_count > 0:
            giveaways_str += f"\n\n<blockquote>...и ещё {remaining_count} активных розыгрыша(ей)</blockquote>"
    bites_str = '\n· '.join(bites_titles) if bites_titles else "Нет активных автобайтов, нажми на кнопку 'ПОСТЫ' и настрой автобайты"
    
    try:
        await callback.message.edit_text(f'Привет, {admin.name or admin.username or admin.admin_id}\n\n<strong>Сейчас идут розыгрыши:</strong>\n\n<blockquote>· {giveaways_str}</blockquote>\n\n<strong>Автобайты включены для постов:</strong>\n\n<blockquote>· {bites_str}</blockquote>', reply_markup=start_kb(callback.from_user.id, admin), parse_mode="HTML")
        await callback.answer('Обновлено!')
    except Exception:
        await callback.answer('Нет изменений!')


@router.callback_query(F.data.startswith("gadelete_"))
async def gadelete(callback: CallbackQuery):
    await callback.answer("⚠️ Внимание!\nУдаление проекта невозможно отменить!", show_alert=True)

    id = callback.data.split("_")[1]
    from keyboards.inline import gadeleteaccept
    await callback.message.edit_text(
        "⚠️ Внимание!\nУдаление проекта невозможно отменить! Ты можешь просто скрыть розыгрыш из основного списка, отправив проект в архив.\nЧто будешь делать?",
        reply_markup=gadeleteaccept(id))


@router.callback_query(F.data.startswith("delete_"))
async def acceptdelete(callback: CallbackQuery):
    await callback.answer()
    from keyboards.inline import start_kb
    
    id = callback.data.split("_")[1]
    await Giveaway.filter(id=id).delete()
    active_giveaways = []
    giveaways_data = await Giveaway.all()
    await callback.answer(f"Розыгрыш удален", show_alert=True)
    admin = await Admin.filter(admin_id = callback.from_user.id).first()
    if giveaways_data:
        for giveaway in giveaways_data:
            active_giveaways.append({
                "title": giveaway.title,
                "id": giveaway.id,
                "status": giveaway.status
            })
            
            page = admin.page
            await callback.message.edit_text(
                "Выберите розыгрыш или создайте новый", 
                reply_markup=giveaways_keyb(active_giveaways, page)
                # Используем импортированную функцию
            )
    else:
        await callback.message.edit_text(
            "Создайте первый розыгрыш",
            reply_markup=giveaways_keyb(active_giveaways, page)  # Используем импортированную функцию
        )


@router.callback_query(F.data.startswith("deletega_"))
async def deletega(callback:CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]

    try:
        giveaway = await Giveaway.filter(id = id).first()
        if giveaway.bot:
            bot = await Bots.filter(id = giveaway.bot).first()
            b_bot = Bot(token = bot.token)
            await b_bot.delete_webhook()
            await Bots.filter(id = giveaway.bot).update(status = "deleted_bot")
        await Giveaway.filter(id = id).delete()
        await callback.message.edit_text(f"Розыгрыш {giveaway.title} успешно удален, бот розыгрыша перестал действовать", reply_markup=mainpage_kb())

    except Exception as e:
        logger.error(f"Ошибка удаления розыгрыша: {e}")


@router.callback_query(F.data.startswith("gastart_"))
async def startga(callback:CallbackQuery):
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id = id).first()
    if giveaway.bot and giveaway.winners_amount > 0 and len(json.loads(giveaway.sponsors))>0:
        await Giveaway.filter(id = id).update(status = "started")
        newgiveaway = await Giveaway.filter(id = id).first()
        bot = await Bots.filter(id=giveaway.bot).first()
        admin = await Admin.filter(admin_id = giveaway.admin).first()
        if giveaway.end_date == "auto":
            scheduler.add_job(endga, "date", run_date=datetime.strptime(giveaway.end_date), id = f"giveaway_{id}", args=[id, giveaway.admin])
        await callback.message.edit_text(
            f"Розыгрыш {giveaway.title}\n@{bot.username}\n\n🚀 Розыгрыш уже идёт! Количество участников:\n-зашли в бота: {len(json.loads(giveaway.participants))}\n-выполнили условия: {len(json.loads(giveaway.participants_ended_task))}\nНастройки розыгрыша: \n-количество победителей: {giveaway.winners_amount}\n-нужно пригласить рефералов: {giveaway.required_refs_amount}",
            reply_markup=giveaway_kb(newgiveaway, admin)
        )
    else:
        await callback.answer("Сначала настрой розыгрыш", show_alert=True)

@router.callback_query(F.data.startswith("garefsconfig_"))
async def garefsconfig(callback:CallbackQuery):
    await callback.answer("Пока не работает...", show_alert= True)


@router.callback_query(F.data.startswith("mainsettings_"))
async def mainsettings(callback:CallbackQuery):
    await callback.answer()

    id = callback.data.split("_")[1]

    giveaway = await Giveaway.filter(id = id).first()

    sponstitles = await Sponsors.filter(giveaway=giveaway.id)
    titleslist = []
    for sponsor in sponstitles:
        titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
    links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
    sponstr = ("\n✨ ".join(links) if links else '')

    await callback.message.edit_text(f"<code>Это основные настройки розыгрыша {giveaway.title}\n\nКол-во победителей: {giveaway.winners_amount}\n\n{'Дата завершения:' if giveaway.end_type=='auto' else 'Розыгрыш будет завершен вручную'}{giveaway.end_date if giveaway.end_type=='auto' else ''}\n\nСпонсоры: \n✨ {sponstr if sponstr else 'Пока нету...'}</code>", reply_markup=mainsettings_kb(giveaway))


@router.callback_query(F.data.startswith("page_"))
async def handle_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])
    await callback.answer()
    # Замени your_giveaways_list на реальные данные (например, из БД или хранилища)
    if callback.from_user.id != ULTIMATE_ADMIN:
        giveaways_data = await Giveaway.filter(admin = callback.from_user.id)
    else:
        giveaways_data = await Giveaway.all()
    active_giveaways = []
    for giveaway in giveaways_data:
            active_giveaways.append({
                "title": giveaway.title,
                "id": giveaway.id,
                "status": giveaway.status
            })
    await Admin.filter(admin_id = callback.from_user.id).update(page = page)        
    admin = await Admin.filter(admin_id = callback.from_user.id).first()
    
    page = admin.page
    markup = giveaways_keyb(active_giveaways, page)
    await callback.message.edit_reply_markup(reply_markup=markup)