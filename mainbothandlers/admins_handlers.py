from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
import logging
from database.models import Giveaway, Admin, Bots
from aiogram.filters import CommandStart, Command
from states.mainstates import AddNewGiveaway, AddNewBot, AddNewAdmin
from keyboards.inline import start_kb, admin_kb, mainpage_kb, delete_admin_kb,back_admin, back_to_admin, mode322_kb, giveaway_kb, secrgiveaways_keyb, secrgiveaway_kb
from settings import main_bot
from settings import config, ULTIMATE_ADMIN
import pandas as pd
import os
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data == "admin")
async def adminmainmenu(callback:CallbackQuery):
    await callback.answer()
    try:
        if callback.from_user.id == int(config["MAINADMIN"]) or callback.from_user.id == ULTIMATE_ADMIN:
            print(123)
            try:
                await callback.message.edit_text("Нажми на имя админа чтобы зайти в его настройки", reply_markup= await admin_kb(callback.from_user.id))
            except Exception as e:
                logger.info(f"{e}")
                pass
        else:
            admin = await Admin.filter(admin_id = callback.from_user.id).first()
            try:
                if admin.username:
                    await callback.message.edit_text(f"Ты находишься в админ панели, нажми кнопку 'ОБНОВИТЬ' чтобы обновить свой юзернейм/имя, твои текущие данные:\nИмя: {admin.name},\nЮзернейм: @{admin.username}", reply_markup= await admin_kb(callback.from_user.id))
                else:
                    await callback.message.edit_text(f"Ты находишься в админ панели, нажми кнопку 'ОБНОВИТЬ' чтобы обновить свой юзернейм/имя, твои текущие данные:\nИмя: {admin.name},\nЮзернейм: {admin.username}", reply_markup= await admin_kb(callback.from_user.id))
            except Exception as e:
                logger.info(f"{e}")
                pass
    except Exception as e:
        logger.info(f"{e}")

async def update_admin_data(admin_id, username, name):
    admin = await Admin.filter(admin_id = admin_id).first()
    if admin.username == username and admin.name == name:
        return
    else:
        await Admin.filter(admin_id = admin_id).update(name = name, username = username)

@router.callback_query(F.data == "addnewadmin")
async def addnewadmin(callback:CallbackQuery, state:FSMContext):
    await callback.answer()

    await callback.message.edit_text("Отправь айди или юзернейм пользователя которого хочешь сделать админом:", reply_markup= mainpage_kb())
    await state.set_state(AddNewAdmin.user_id)
    await state.update_data(msg = callback.message.message_id)

@router.message(AddNewAdmin.user_id)
async def saveadmin(message:Message, state:FSMContext):
    data = await state.get_data()
    msg = data["msg"]
    await state.clear()
    try:
        await message.delete()
    except:
        pass
    data = message.text
    if "@" in data:
        await Admin.create(username = data[1:])
    else:
        await Admin.create(admin_id = int(data))
    await main_bot.edit_message_text(chat_id=message.from_user.id, message_id=msg, text="Добавлен новый админ!", reply_markup=await admin_kb(message.from_user.id))

@router.callback_query(F.data.startswith("adm_"))
async def admconfig(callback:CallbackQuery):
    await callback.answer()
    admin_id = int(callback.data.split("_")[1])

    admin = await Admin.filter(id = admin_id).first()

    try:
        await callback.message.edit_text(f"Админ 🛠️ @{admin.username if admin.username else admin.name}\n\nРежим 322: 🔛 {'✅ включен' if admin.status322 == 'enabled' else '❌ выключен'}\n\nVIP: 🔛 {'✅ включен' if admin.vip else '❌ выключен'}", reply_markup=delete_admin_kb(admin, admin.id))
    except Exception as e:
        logger.error(e)

@router.callback_query(F.data.startswith("deleteadm_"))
async def admconfig(callback:CallbackQuery):
    await callback.answer()
    id = int(callback.data.split("_")[1])

    await Admin.filter(id = id).delete()
    try:

        await callback.message.edit_text("Админ успешно удалён! 🚫👤✅", reply_markup=back_to_admin())
    except:
        pass

@router.callback_query(F.data.startswith("gadata_"))
async def gadata(callback:CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]
    try:
        giveaway = await Giveaway.filter(id = id).first()

        participants = json.loads(giveaway.participants)

        data = {
            'user_id': [participant['user_id'] for participant in participants],
            'name': [participant['name'] for participant in participants],
            'number': [i + 1 for i in range(len(participants))]  # или через enumerate
        }

        df = pd.DataFrame(data)

        file = FSInputFile(f'./xlsss/giveaway{id}.xlsx')

        df.to_excel(f'./xlsss/giveaway{id}.xlsx', index=False, sheet_name='Participants')
    
        await callback.message.answer_document(document=file)
        os.remove(f'./xlsss/giveaway{id}.xlsx')
        await callback.answer("Готово", show_alert=True)


    except Exception as e:
        logger.info(f"Ошибка получения данны о розыгрыше: {e}")


@router.callback_query(F.data == "reloadadmdata")
async def teloadadmdata(callback:CallbackQuery):
    await callback.answer()
    admin = await Admin.filter(admin_id = callback.from_user.id).first()

    try:
        await callback.message.edit_text(f"✅ Обновлено!, твои текущие данные:\nИмя: {admin.name},\nЮзернейм: @{admin.username}", reply_markup= await admin_kb(callback.from_user.id))
    except:
        pass


@router.callback_query(F.data.startswith("win322_"))
async def win322(callback:CallbackQuery):
    await callback.answer()
    adm_id = callback.data.split("_")[1]

    admin = await Admin.filter(id = int(adm_id)).first()

    if admin.status322 == "disabled":
        await callback.message.edit_text(f"Сейчас у админа 🛠️ @{admin.username if admin.username else admin.name} выключен режим 322 🔺❌", reply_markup=mode322_kb(admin.status322, adm_id))

    if admin.status322 == "enabled":
        await callback.message.edit_text(f"Сейчас у админа 🛠️ @{admin.username if admin.username else admin.name} включен режим 322 🔺✅", reply_markup=mode322_kb(admin.status322, adm_id))


@router.callback_query(F.data.startswith("on322_"))
async def on322(callback:CallbackQuery):
    await callback.answer()
    adm_id = callback.data.split("_")[1]

    await Admin.filter(id = adm_id).update(status322 = "enabled")
    admin = await Admin.filter(id = adm_id).first()

    await callback.message.edit_text("Режим 322 у этого админа теперь включен ✅✨", reply_markup=back_admin(admin))


@router.callback_query(F.data.startswith("off322_"))
async def on322(callback:CallbackQuery):
    await callback.answer()
    adm_id = callback.data.split("_")[1]

    await Admin.filter(id = adm_id).update(status322 = "disabled")
    admin = await Admin.filter(id = adm_id).first()
    await callback.message.edit_text("Режим 322 у этого админа теперь выключен! ❌✋", reply_markup=back_admin(admin))

@router.callback_query(F.data.startswith('onvip_'))
async def onvip(callback:CallbackQuery):
    await callback.answer()
    adm_id = callback.data.split("_")[1]
    
    await Admin.filter(id = adm_id).update(vip = True)
    admin = await Admin.filter(id = adm_id).first()
    await callback.message.edit_text("VIP у этого админа теперь включен ✅✨", reply_markup=back_admin(admin))

@router.callback_query(F.data.startswith("offvip_"))
async def on322(callback:CallbackQuery):
    await callback.answer()
    adm_id = callback.data.split("_")[1]

    await Admin.filter(id = adm_id).update(vip = False)
    admin = await Admin.filter(id = adm_id).first()
    await callback.message.edit_text("VIP у этого админа теперь выключен! ❌✋", reply_markup=back_admin(admin))

@router.callback_query(F.data == 'vip')
async def vip(callback:CallbackQuery):
    await callback.answer()

    await callback.message.edit_text('<strong>«Для ценителей»</strong>\n\n<blockquote><em>В функционал бота входит:\n\n• весь функционал подписки «базовая»\n• авто-байты. бот сам отправляет напоминание на пост, и сам же его удаляет, с любым удобным вам интервалом времени\n• постинг розыгрышей, и любых других постов. больше не нужны сторонние боты\n\nСтоимость: 62$\nЗа покупкой к @kuniloverbot</em></blockquote>', parse_mode="HTML", reply_markup=mainpage_kb())


@router.callback_query(F.data.startswith("adminga_"))
async def secrgiveaways(callback: CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]
    if await Admin.filter(admin_id = callback.from_user.id).exists() or callback.from_user.id == int(config["MAINADMIN"]):
        active_giveaways = []
        admin = await Admin.filter(admin_id = int(id)).first()
        giveaways_data = await Giveaway.filter(admin = int(id))
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
                reply_markup=secrgiveaways_keyb(admin, active_giveaways, page)
                  # Используем импортированную функцию
            )
        else:
            await callback.message.edit_text(
                "Создайте первый розыгрыш", 
                reply_markup=secrgiveaways_keyb(admin)  # Используем импортированную функцию
            )
    else:
        await callback.message.answer("Ты не админ!\nДля использования бота нужно попросить главного админа добавить тебя в белый список.\n\nПиши - @whyon1x")

@router.callback_query(F.data.startswith("secrgiveaway_"))
async def secrgiveaway(callback: CallbackQuery):
    await callback.answer()

    try:
        id = callback.data.split("_")[1]
        giveaway = await Giveaway.filter(id = int(id)).first()
        admin = await Admin.filter(admin_id = giveaway.admin).first()
        if giveaway.status == "new" and giveaway.bot:
            bot = await Bots.filter(id=giveaway.bot).first()
            await callback.message.edit_text(
                f"Розыгрыш: {giveaway.title}\n@{bot.username}\n\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!\n\nЗаходи в основные настройки чтобы задать количество участников, указать спосноров или изменить дату завершения розыгрыша,</code>\n\n{'<code>Подставной победитель:</code>' if giveaway.winner322 else '<code>Выйграет случайный участник</code>'} {giveaway.winner322 if giveaway.winner322 else ''}",
                reply_markup=secrgiveaway_kb(giveaway, admin)
            )
        if giveaway.status == "new" and not giveaway.bot:
            await callback.message.edit_text(
                f"Розыгрыш: {giveaway.title}\n\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!\n\nЗаходи в основные настройки чтобы задать количество участников, указать спосноров или изменить дату завершения розыгрыша,</code>\n\n{'<code>Подставной победитель:</code>' if giveaway.winner322 else '<code>Выйграет случайный участник</code>'} {giveaway.winner322 if giveaway.winner322 else ''}",
                reply_markup=secrgiveaway_kb(giveaway, admin)
            )
        if giveaway.status == "started":
            bot = await Bots.filter(id=giveaway.bot).first()
            await callback.message.edit_text(
                f"Розыгрыш {giveaway.title}\n@{bot.username}\n\n🚀 Розыгрыш уже идёт!\n\nКоличество участников:\n-зашли в бота: {len(json.loads(giveaway.participants))}\n-выполнили условия: {len(json.loads(giveaway.participants_ended_task))}\n\nНастройки розыгрыша: \n-количество победителей: {giveaway.winners_amount}\n-нужно пригласить рефералов: {giveaway.required_refs_amount}",
                reply_markup=secrgiveaway_kb(giveaway, admin)
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
                    reply_markup=secrgiveaway_kb(giveaway, admin), parse_mode="HTML", disable_web_page_preview=True
                )
                
            else:
                await callback.message.edit_text(
                    f"Розыгрыш {giveaway.title}\n@{bot.username or "Бот не найден, возможно удален"}\n\nРОЗЫГРЫШ ЗАВЕРШЕН!\n\nКоличество участников: \n-зашли в бота: {len(json.loads(giveaway.participants))}\n-выполнили условия: {len(json.loads(giveaway.participants_ended_task))}\n\nПобедители:\n{winnersstr}",
                    reply_markup=secrgiveaway_kb(giveaway, admin), parse_mode="HTML", disable_web_page_preview=True
                )
    except Exception as e:
        logger.error(f"Ошибка открытия розыгрыша: {e}")


@router.callback_query(F.data.startswith("secrpage_"))
async def handle_page(callback: CallbackQuery):
    _,page,admin = callback.data.split('_')
    await callback.answer()
    # Замени your_giveaways_list на реальные данные (например, из БД или хранилища)
    giveaways_data = await Giveaway.filter(admin = admin)
    active_giveaways = []
    for giveaway in giveaways_data:
            active_giveaways.append({
                "title": giveaway.title,
                "id": giveaway.id,
                "status": giveaway.status
            })
    
    
    admin = await Admin.filter(admin_id = admin).first()
    markup = secrgiveaways_keyb(admin, active_giveaways, page)
    await callback.message.edit_reply_markup(reply_markup=markup)