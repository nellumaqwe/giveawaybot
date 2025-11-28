from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram import Router, F
from database.models import Giveaway, Sponsors, Bots, Admin
from aiogram.filters import StateFilter
from states.mainstates import AddSponsor
from keyboards.inline import sponsors_kb, back_sponsor_kb, select_sponsor_type_kb, sponsor_kb, giveaway_kb, secrsponsors_kb, secrsponsor_kb
from settings import main_bot
import json
import logging
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("gasponsorsconfig_"))
async def gasponsorsconfig(callback: CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    sponstitles = await Sponsors.filter(giveaway=id).all()
    titleslist = []
    sponsors = []
    for sponsor in sponstitles:
        titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
        sponsors.append({"title": f"{sponsor.title}", "id": f"{sponsor.id}"})
    links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
    sponstr = "\n".join(links)
    if sponstitles:
        await callback.message.edit_text(f"Список спонсоров розыгрыша\n{sponstr}", reply_markup=sponsors_kb(giveaway, sponsors),
                                         disable_web_page_preview=True)
    else:
        await callback.message.edit_text("Добавьте первого спонсора, на которого нужно будет подписаться для участия в розыгрыше:",
                                         reply_markup=sponsors_kb(giveaway, sponsors))


@router.callback_query(F.data.startswith("gamainpage_"))
async def gamainpage(callback: CallbackQuery):
    
    await callback.answer()
    try:
        id = callback.data.split("_")[1]
        # Используем существующую функцию для отображения информации о розыгрыше
        
        giveaway = await Giveaway.filter(id=id).first()
        admin = await Admin.filter(admin_id = giveaway.admin).first()
        if giveaway.status == "new" and giveaway.bot:
            bot = await Bots.filter(id=giveaway.bot).first()
            await callback.message.edit_text(
                f"Розыгрыш {giveaway.title}\n@{bot.username}\n<code>Что дальше:\n1. Привяжи и настрой внешний вид лендинг-бота, с которым будут взаимодействовать участники розыгрыша\n2. Добавь всех спонсоров\n3. Укажи, нужно ли для участия в розыгрыше пригласить рефералов\n4. Выбери количество победителей\n5. Выбери дату подведения итогов (или вручную запустишь?)\n6. Когда всё будет готово - запускай розыгрыш!\n6. И когда придёт время - бот выберет победителей!</code>",
                reply_markup=giveaway_kb(giveaway, admin)
            )
        if giveaway.status == "new" and not giveaway.bot:
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


@router.callback_query(F.data.startswith("addgasponsor_"))
async def addgasponsor(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    try:
        await callback.message.edit_text("Выбери что добавить в спонсоры:", reply_markup=select_sponsor_type_kb(giveaway))
    except:
        pass


@router.callback_query(F.data.startswith("channel_"))
async def addchannel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    await callback.message.edit_text(
        "1. Добавь меня @contestUCbot в администраторы подключаемого канала \n2. Необходимо разрешение Добавление участников/Пригласительные ссылки\n3. Перешли мне любое сообщение из канала (прямо в этот чат).\nЯ жду..",
        reply_markup=back_sponsor_kb(giveaway))
    await state.set_state(AddSponsor.message)
    await state.update_data(id=id)
    await state.update_data(msg=callback.message.message_id)


@router.message(AddSponsor.message)
async def resendedmessage(message: Message, state: FSMContext):
    data = await state.get_data()
    gaid = data.get("id")
    msg = data["msg"]
    giveaway = await Giveaway.filter(id=gaid).first()
    if not message.forward_from_chat:
        try:
            await message.delete()
        except:
            pass
        await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg,
                                         text="Это сообщение не переслано с другого канала!",
                                         reply_markup=back_sponsor_kb(giveaway))
        await state.set_state(AddSponsor.message)
        return
    chat_id = message.forward_from_chat.id
    title = message.forward_from_chat.title
    if await Sponsors.filter(chat_id=message.forward_from_chat.id, giveaway=gaid).exists():
        await main_bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
        await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg,
                                         text="⚠️ Этот канал/группа уже добавлен как спонсор для этого розыгрыша. Попробуй заново",
                                         reply_markup=back_sponsor_kb(giveaway))
        await state.set_state(AddSponsor.message)
    else:
        try:
            invite_link = await main_bot.create_chat_invite_link(chat_id=chat_id)
            await Sponsors.create(invite_link=invite_link.invite_link, chat_id=chat_id, title=title, giveaway=gaid)
            sponsors = giveaway.sponsors
            splist = json.loads(sponsors) if sponsors else []
            splist.append(chat_id)
            updated_list = json.dumps(splist)
            await Giveaway.filter(id=gaid).update(sponsors=updated_list)
            newpsonsponsors = await Sponsors.filter(giveaway=gaid).all()
            newsponsorslist = []
            newtitlelist = []
            for newsponsor in newpsonsponsors:
                newsponsorslist.append({"title": f"{newsponsor.title}", "id": f"{newsponsor.id}"})
                newtitlelist.append({"title": f"{newsponsor.title}", "invite_link": f"{newsponsor.invite_link}"})
            newlinks = [f'<a href="{newchat["invite_link"]}">{newchat["title"]}</a>' for newchat in newtitlelist]
            newsponstr = "\n ".join(newlinks)
            try:
                await main_bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
            except Exception as e:
                logger.error(f"{e}")
                pass
            await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg,
                                             text=f"✅ ОБНОВЛЕНО \n\nСписок спонсоров:\n {newsponstr}",
                                             reply_markup=sponsors_kb(giveaway, newsponsorslist),
                                             disable_web_page_preview=True)
        except (TelegramBadRequest, TelegramForbiddenError):
            try:
                await main_bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id) 
            except:
                pass
            await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg,
                                             text="⚠️ Ошибка с правами! Проверь, что ты добавил меня в администраторы этого сообщества и включил нужные права.\nИ попробуй ещё раз:",
                                             reply_markup=back_sponsor_kb(giveaway))
            await state.set_state(AddSponsor.message)


@router.callback_query(F.data.startswith("backtosponsors_"))
async def back_to_sponsors(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    sponstitles = await Sponsors.filter(giveaway=id).all()
    titleslist = []
    sponsors = []
    for sponsor in sponstitles:
        sponsors.append({"title": f"{sponsor.title}", "id": f"{sponsor.id}"})
        titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
    links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
    sponstr = "\n".join(links)
    try:
        if sponstitles:
            await callback.message.edit_text(f"Список спонсоров розыгрыша\n{sponstr}",
                                            reply_markup=sponsors_kb(giveaway, sponsors),
                                            disable_web_page_preview=True)
        else:
            await callback.message.edit_text(
                "Добавьте первого спонсора, на которого нужно будет подписаться для участия в розыгрыше:",
                reply_markup=sponsors_kb(giveaway, sponsors))
    except:
        pass


@router.callback_query(F.data.startswith("group_"))
async def addgr(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    await state.set_state(AddSponsor.tag)
    await state.update_data(id=id, user_id = callback.from_user.id, msg = callback.message.message_id)
    await callback.message.edit_text(
        "1. Добавь меня @contestUCbot в администраторы подключаемой группы \n2. Необходимо разрешение Добавление участников/Пригласительные ссылки\n3. Отправь сообщение в группе с моим именем (одним словом): @contestUCbot\nЯ жду..",
        reply_markup=back_sponsor_kb(giveaway))


@router.message(F.text.lower().contains("@contestucbot"))
async def addgroup(message: Message, state: FSMContext):
    if message.chat.type not in ["group", "supergroup"]:
        return 
    
    bot_mentioned = False
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mention_text = message.text[entity.offset : entity.offset + entity.length]
                if "@contestucbot" in mention_text.lower(): 
                    bot_mentioned = True
                    break

    if not bot_mentioned:
        return 
    
    user_fsm_context = FSMContext(
        storage=state.storage, 
        key=StorageKey(
            bot_id=state.key.bot_id,
            user_id=message.from_user.id, 
            chat_id=message.from_user.id  
        )
    )

    st = await user_fsm_context.get_state()
    if st == AddSponsor.tag.state:
        user_state_data = await user_fsm_context.get_data()

        giveaway_id = user_state_data.get("id")
        initiator_user_id = user_state_data.get("user_id")
        msg = user_state_data.get("msg")

        chat_id = message.chat.id
        title = message.chat.title

        giveaway = await Giveaway.filter(id = giveaway_id).first()
        if await Sponsors.filter(chat_id=chat_id, giveaway=giveaway_id).exists():
            await main_bot.edit_message_text(message_id= msg, chat_id=initiator_user_id, text="⚠️ Эта группа уже добавлена как спонсор для этого розыгрыша.", reply_markup=back_sponsor_kb(giveaway))

            await user_fsm_context.clear() 
        try:
        # Создаем пригласительную ссылку
            invite_link_obj = await main_bot.create_chat_invite_link(chat_id=chat_id)
            invite_link = invite_link_obj.invite_link

                # Сохраняем спонсора
            await Sponsors.create(invite_link=invite_link, chat_id=chat_id, title=title, giveaway=giveaway_id)

                # Обновляем список спонсоров в розыгрыше 
            giveaway_obj = await Giveaway.filter(id=giveaway_id).first()

            sponsors = json.loads(giveaway_obj.sponsors)

            sponsors.append(chat_id)
            await Giveaway.filter(id = giveaway_id).update(sponsors = sponsors)

            newpsonsponsors = await Sponsors.filter(giveaway=giveaway_id).all()
            newsponsorslist = []
            newtitlelist = []
            for newsponsor in newpsonsponsors:
                newsponsorslist.append({"title": f"{newsponsor.title}", "id": f"{newsponsor.id}"})
                newtitlelist.append({"title": f"{newsponsor.title}", "invite_link": f"{newsponsor.invite_link}"})
            newlinks = [f'<a href="{newchat["invite_link"]}">{newchat["title"]}</a>' for newchat in newtitlelist]
            newsponstr = "\n".join(newlinks)
                
            await main_bot.edit_message_text(chat_id=initiator_user_id, message_id=msg,
                                            text=f"Обновлен список спонсоров:\n{newsponstr}",
                                            reply_markup=sponsors_kb(giveaway, newsponsorslist),
                                            disable_web_page_preview=True)

        except (TelegramBadRequest, TelegramForbiddenError) as e:
            await main_bot.edit_message_text(chat_id=initiator_user_id, message_id=msg,
                                            text="⚠️ Ошибка с правами! Проверь, что ты добавил меня в администраторы этого сообщества и включил нужные права.\nИ попробуй ещё раз:",
                                            reply_markup=back_sponsor_kb(giveaway))
            await user_fsm_context.set_state(AddSponsor.message)

        finally:
            # ВАЖНО: Очищаем состояние пользователя, чтобы он мог снова начать процесс
            await user_fsm_context.clear()
    else:
        return  


@router.callback_query(F.data.startswith("sponsor_"))
async def gasponsor(callback: CallbackQuery):
    await callback.answer()
    print(callback.data)
    _, sponsor_id, gaid = callback.data.split("_")
    sponsor = await Sponsors.filter(id=sponsor_id).first()
    await callback.message.edit_text(f"Спонсор <a href = '{sponsor.invite_link}'>{sponsor.title}</a>",
                                     reply_markup=sponsor_kb(sponsor_id, gaid))


@router.callback_query(F.data.startswith("deletesp_"))
async def deletesp(callback: CallbackQuery):
    await callback.answer()
    _, spid, gaid = callback.data.split("_")
    print(callback.data)
    print(spid)
    delsponsor = await Sponsors.filter(id=spid).first()
    print(delsponsor)
    giveaway = await Giveaway.filter(id=gaid).first()
    splist = json.loads(giveaway.sponsors)
    splist.remove(delsponsor.chat_id)
    if splist:
        await Giveaway.filter(id=gaid).update(sponsors=splist)
    else:
        await Giveaway.filter(id=gaid).update(sponsors=[])
    await Sponsors.filter(id=spid).delete()
    sponstitles = await Sponsors.filter(giveaway=gaid).all()
    titleslist = []
    sponsors = []
    for sponsor in sponstitles:
        sponsors.append({"title": f"{sponsor.title}", "id": f"{sponsor.id}"})
        titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
    links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
    sponstr = "\n".join(links)
    if sponstitles:
        await callback.message.edit_text(f"Список спонсоров розыгрыша\n{sponstr}",
                                         reply_markup=sponsors_kb(giveaway, sponsors),
                                         disable_web_page_preview=True)
    else:
        await callback.message.edit_text(
            "Добавьте первого спонсора, на которого нужно будет подписаться для участия в розыгрыше:",
            reply_markup=sponsors_kb(giveaway, sponsors))


@router.callback_query(F.data.startswith("updatesponsor_"))
async def udatespdata(callback:CallbackQuery):
    await callback.answer()

    _,id, gaid = callback.data.split("_")

    sponsor = await Sponsors.filter(id = id).first()

    await callback.message.edit_text(f"✅ Обновлено!\n\nСпонсор <a href = '{sponsor.invite_link}'>{sponsor.title}</a>",
                                     reply_markup=sponsor_kb(id, gaid))
    

@router.callback_query(F.data.startswith("secrgasponsorsconfig_"))
async def gasponsorsconfig(callback: CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    sponstitles = await Sponsors.filter(giveaway=id).all()
    titleslist = []
    sponsors = []
    for sponsor in sponstitles:
        titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
        sponsors.append({"title": f"{sponsor.title}", "id": f"{sponsor.id}"})
    links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
    sponstr = "\n".join(links)
    if sponstitles:
        await callback.message.edit_text(f"Список спонсоров розыгрыша\n{sponstr}", reply_markup=secrsponsors_kb(giveaway, sponsors),
                                         disable_web_page_preview=True)
    else:
        await callback.message.edit_text("Добавьте первого спонсора, на которого нужно будет подписаться для участия в розыгрыше:",
                                         reply_markup=secrsponsors_kb(giveaway, sponsors))
        

@router.callback_query(F.data.startswith("backtosecrsponsors_"))
async def back_to_sponsors(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    id = callback.data.split("_")[1]
    giveaway = await Giveaway.filter(id=id).first()
    sponstitles = await Sponsors.filter(giveaway=id).all()
    titleslist = []
    sponsors = []
    for sponsor in sponstitles:
        sponsors.append({"title": f"{sponsor.title}", "id": f"{sponsor.id}"})
        titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
    links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
    sponstr = "\n".join(links)
    try:
        if sponstitles:
            await callback.message.edit_text(f"Список спонсоров розыгрыша\n{sponstr}",
                                            reply_markup=secrsponsors_kb(giveaway, sponsors),
                                            disable_web_page_preview=True)
        else:
            await callback.message.edit_text(
                "Добавьте первого спонсора, на которого нужно будет подписаться для участия в розыгрыше:",
                reply_markup=secrsponsors_kb(giveaway, sponsors))
    except:
        pass


@router.callback_query(F.data.startswith("secrsponsor_"))
async def secrgasponsor(callback: CallbackQuery):
    await callback.answer()
    _, sponsor_id, gaid = callback.data.split("_")
    sponsor = await Sponsors.filter(id=sponsor_id).first()
    await callback.message.edit_text(f"Спонсор <a href = '{sponsor.invite_link}'>{sponsor.title}</a>",
                                     reply_markup=secrsponsor_kb(sponsor_id, gaid))
    
