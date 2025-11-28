from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
import logging
from aiogram.exceptions import TelegramBadRequest
from database.models import Giveaway, Bots, Sponsors
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.enums.chat_member_status import ChatMemberStatus
from settings import main_bot
from keyboards.inline import checksubscription
from typing import Optional, Union
import json

router = Router()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def viewwinners(message:Message, command:CommandObject, bot_token: Optional[str] = None):

    if command.args:
        args = command.args

        if args.startswith("seegiveawayresults_"):
            id = args.split("_")[1]
            giveaway = await Giveaway.filter(id = id).first()
            if giveaway.status.startswith("ended"):
                winners = json.loads(giveaway.winners)
                winnerslist = []
                i = 1
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
                        i+=1
                        winnerslist.append(link)
                
                links = "\n".join(winnerslist)

                await message.answer(f"🎊 <b>РОЗЫГРЫШ ЗАВЕРШЕН!</b> 🎊\n\n🎁 <b>Розыгрыш:</b> {giveaway.title}\n\n🏆 <b>Победители:</b>\n{links}", parse_mode="HTML")
    
    else:
        bot = await Bots.filter(token=bot_token).first()
        giveaway = await Giveaway.filter(bot=bot.id).first()
        if giveaway.status != "ended":
            fullparticipants = json.loads(giveaway.participants_ended_task)
            participants = json.loads(giveaway.participants)
            ids = []
            for part in fullparticipants:
                ids.append(part["user_id"])
            if not message.from_user.id in ids:
                try:
                    
                    if not bot_token:
                        logger.info("Ошибка: не передан токен бота")
                        return
                        
                    
                    if not bot:
                        logger.info("Ошибка: бот не найден")
                        return
                        
                    
                    #print("Raw participants:", repr(giveaway.participants))
                    
                    # Безопасно парсим participants
                    
                    if giveaway.participants:
                        if isinstance(giveaway.participants, str) and giveaway.participants.strip():
                            try:
                                
                                if not isinstance(participants, list):
                                    participants = []
                            except json.JSONDecodeError as e:
                                logger.error(f"JSON ошибка при парсинге: {e}")
                                participants = []
                        elif isinstance(giveaway.participants, list):
                            participants = giveaway.participants
                    
                    # Создаем данные пользователя
                    user_data = {
                        "user_id": message.from_user.id,
                        "username": message.from_user.username,
                        "name": message.from_user.full_name
                    }
                    
                    # Проверяем наличие пользователя
                    user_exists = False
                    for user in participants:
                        if isinstance(user, dict) and user.get("user_id") == message.from_user.id:
                            user_exists = True
                            break
                    
                    if not user_exists:
                        participants.append(user_data)
                        # ВАЖНО: сохраняем как JSON строку!
                        await Giveaway.filter(id=giveaway.id).update(
                            participants=json.dumps(participants, ensure_ascii=False)
                        )
                        
                    
                    
                    sponstitles = await Sponsors.filter(giveaway=giveaway.id).all()
                    titleslist = []

                    for sponsor in sponstitles:
                        titleslist.append({
                            "title": f"{sponsor.title}", 
                            "invite_link": f"{sponsor.invite_link}"
                        })

                    links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
                    sponstr = "\n✨".join(links)
                    
                    if sponstitles:
                        await message.answer(
                            f"Чтобы участвовать в розыгрыше вам нужно подписаться на спонсоров и нажать кнопку 'ПРОВЕРИТЬ'\n\n✨ {sponstr}", 
                            reply_markup=checksubscription(giveaway),
                            disable_web_page_preview=True
                        )
                    else:
                        await message.answer(
                            f"Чтобы участвовать в розыгрыше вам нужно подписаться на спонсоров и нажать кнопку 'ПРОВЕРИТЬ'\n\nНет действующих спонсоров!", 
                            reply_markup=checksubscription(giveaway),
                            disable_web_page_preview=True
                        )
                
                except Exception as e:
                    logger.error(f"Ошибка в команде /start: {e}")
                    pass
                    
            else:
                sponstitles = await Sponsors.filter(giveaway=giveaway.id).all()
                titleslist = []

                for sponsor in sponstitles:
                    titleslist.append({
                        "title": f"{sponsor.title}", 
                        "invite_link": f"{sponsor.invite_link}"
                    })

                links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
                sponstr = "\n✨ ".join(links)
                await message.answer(f"⭐️ Вы участвуете в розыгрыше! ⭐️\n\n<b>Ваш номер: 👉🏼 #</b> <code>{ids.index(message.from_user.id)+1}</code>\n\nСпонсоры:\n✨ {sponstr}\n\n🎁 Желаем удачи!", disable_web_page_preview=True)
            
        else:
            try:
                    
                # Получаем победителей из базы данных
                winners_data = json.loads(giveaway.winners) if giveaway.winners else []
                
                # Получаем спонсоров из базы данных
                sponstitles = await Sponsors.filter(giveaway=giveaway.id)
                titleslist = []
                for sponsor in sponstitles:
                    titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
                
                links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
                sponsors_text = "\n✨ ".join(links) if links else "Нет спонсоров"
                
                # Формируем список победителей с ссылками
                winners_links = []
                i = 1
                for winner in winners_data:
                    if winner.get("username"):
                        link = f"🏆 Место #{i}: <a href='https://t.me/{winner['username']}'>{winner['name']}</a>"
                    else:
                        link = f"🏆 Место #{i}: <a href='tg://user?id={winner['user_id']}'>{winner['name']}</a>"
                    
                    winners_links.append(link)
                    i += 1
                
                winners_formatted = "\n".join(winners_links) if winners_links else "Победители не определены"
                
                # Формируем финальное сообщение в одну строку
                message_text = f"🎊 <b>РОЗЫГРЫШ ЗАВЕРШЕН!</b> 🎊\n\n🎁 <b>Розыгрыш:</b> {giveaway.title}\n\n🤝 <b>Спонсоры:</b>\n✨ {sponsors_text}\n\n🎉 Поздравляем победителей! 🎉"
                
                await message.answer(
                    text=message_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
            
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение о завершении розыгрыша: {e}")

@router.message(F.text)
async def start(message: Message, bot_token: Optional[str] = None):
    bot = await Bots.filter(token=bot_token).first()
    giveaway = await Giveaway.filter(bot=bot.id).first()
    if giveaway.status != "ended":
        fullparticipants = json.loads(giveaway.participants_ended_task)
        participants = json.loads(giveaway.participants)
        ids = []
        for part in fullparticipants:
            ids.append(part["user_id"])
        if not message.from_user.id in ids:
            try:
                
                if not bot_token:
                    logger.info("Ошибка: не передан токен бота")
                    return
                    
                
                if not bot:
                    logger.info("Ошибка: бот не найден")
                    return
                    
                
                #print("Raw participants:", repr(giveaway.participants))
                
                # Безопасно парсим participants
                
                if giveaway.participants:
                    if isinstance(giveaway.participants, str) and giveaway.participants.strip():
                        try:
                            
                            if not isinstance(participants, list):
                                participants = []
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON ошибка при парсинге: {e}")
                            participants = []
                    elif isinstance(giveaway.participants, list):
                        participants = giveaway.participants
                
                # Создаем данные пользователя
                user_data = {
                    "user_id": message.from_user.id,
                    "username": message.from_user.username,
                    "name": message.from_user.full_name
                }
                
                # Проверяем наличие пользователя
                user_exists = False
                for user in participants:
                    if isinstance(user, dict) and user.get("user_id") == message.from_user.id:
                        user_exists = True
                        break
                
                if not user_exists:
                    participants.append(user_data)
                    # ВАЖНО: сохраняем как JSON строку!
                    await Giveaway.filter(id=giveaway.id).update(
                        participants=json.dumps(participants, ensure_ascii=False)
                    )
                    
                
                
                sponstitles = await Sponsors.filter(giveaway=giveaway.id).all()
                titleslist = []

                for sponsor in sponstitles:
                    titleslist.append({
                        "title": f"{sponsor.title}", 
                        "invite_link": f"{sponsor.invite_link}"
                    })

                links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
                sponstr = "\n✨".join(links)
                
                await message.answer(
                    f"Чтобы участвовать в розыгрыше вам нужно подписаться на спонсоров и нажать кнопку 'ПРОВЕРИТЬ ПОДПИСКИ'\n\n✨ {sponstr}", 
                    reply_markup=checksubscription(giveaway),
                    disable_web_page_preview=True
                )
            
            except Exception as e:
                logger.error(f"Ошибка в команде /start: {e}")
                pass
        else:
            sponstitles = await Sponsors.filter(giveaway=giveaway.id).all()
            titleslist = []

            for sponsor in sponstitles:
                titleslist.append({
                    "title": f"{sponsor.title}", 
                    "invite_link": f"{sponsor.invite_link}"
                })

            links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
            sponstr = "\n✨ ".join(links)
            await message.answer(f"⭐️ Вы участвуете в розыгрыше! ⭐️\n\n<b>Ваш номер: 👉🏼 #</b> <code>{ids.index(message.from_user.id)+1}</code>\n\nСпонсоры:\n✨ {sponstr}\n\n🎁 Желаем удачи!", disable_web_page_preview=True)
        
    else:
        try:
                
            # Получаем победителей из базы данных
            winners_data = json.loads(giveaway.winners) if giveaway.winners else []
            
            # Получаем спонсоров из базы данных
            sponstitles = await Sponsors.filter(giveaway=giveaway.id)
            titleslist = []
            for sponsor in sponstitles:
                titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
            
            links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
            sponsors_text = "\n✨ ".join(links) if links else "Нет спонсоров"
            
            # Формируем список победителей с ссылками
            winners_links = []
            i = 1
            for winner in winners_data:
                if winner.get("username"):
                    link = f"🏆 Место #{i}: <a href='https://t.me/{winner['username']}'>{winner['name']}</a>"
                else:
                    link = f"🏆 Место #{i}: <a href='tg://user?id={winner['user_id']}'>{winner['name']}</a>"
                
                winners_links.append(link)
                i += 1
            
            winners_formatted = "\n".join(winners_links) if winners_links else "Победители не определены"
            
            # Формируем финальное сообщение в одну строку
            message_text = f"🎊 <b>РОЗЫГРЫШ ЗАВЕРШЕН!</b> 🎊\n\n🎁 <b>Розыгрыш:</b> {giveaway.title}\n\n🤝 <b>Спонсоры:</b>\n✨ {sponsors_text}\n\n🎉 Поздравляем победителей! 🎉"
            
            await message.answer(
                text=message_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о завершении розыгрыша: {e}")

async def check_user_in_channels(user_id, sponsors):
    results = {}
    for sponsor in sponsors:
        try:
            
            if sponsor:
                chat_id=sponsor
            member = await main_bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            is_member = member.status not in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
            results[chat_id] = is_member
        except TelegramBadRequest:
            results[chat_id] = False
    return results
   
@router.callback_query(F.data.startswith("checksub_"))
async def checksub(callback: CallbackQuery):
    try:
        id = callback.data.split("_")[1]
        user_id = callback.from_user.id
        giveaway = await Giveaway.filter(id=id).first()
        
        # Правильно парсим JSON из базы данных
        if not giveaway.participants_ended_task or giveaway.participants_ended_task.strip() == "":
            participants_ended_tasks = []
        else:
            try:
                participants_ended_tasks = json.loads(giveaway.participants_ended_task)
            except json.JSONDecodeError:
                participants_ended_tasks = []
        
        # Убедимся, что это список
        if not isinstance(participants_ended_tasks, list):
            participants_ended_tasks = []
        
        if giveaway.status == "started":
            sponsors = json.loads(giveaway.sponsors)
            titleslist = []
            sponstitles = await Sponsors.filter(giveaway=giveaway.id).all()
            for sponsor in sponstitles:
                titleslist.append({
                    "title": f"{sponsor.title}", 
                    "invite_link": f"{sponsor.invite_link}"
                })

            links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
            sponstr = "\n✨ ".join(links)
            subscription_status = await check_user_in_channels(user_id, sponsors)

            not_subscribed = [chan for chan, is_sub in subscription_status.items() if not is_sub]
            notsub = []
            if not_subscribed:
                for chan in not_subscribed:
                    sp = await Sponsors.filter(chat_id = chan).first()
                    notsub.append(f"{sp.title}")
                    
                await callback.answer(f"❌ Вы не подписаны на: {', '.join(notsub)}", show_alert=True)
            else:
                # Создаем словарь для поиска
                user_data = {"user_id": callback.from_user.id, "username": callback.from_user.username, "name": callback.from_user.full_name}
                
                # Проверяем, есть ли пользователь в списке (по user_id)
                user_exists = any(user.get("user_id") == callback.from_user.id for user in participants_ended_tasks)
                
                if not user_exists:
                    participants_ended_tasks.append(user_data)
                    await Giveaway.filter(id=giveaway.id).update(
                        participants_ended_task=json.dumps(participants_ended_tasks, ensure_ascii=False)
                    )
                    number = len(participants_ended_tasks)  # Последний добавленный
                    await callback.answer(f"Вы участвуете в розыгрыше, ваш номерок - #{number}", show_alert=True)
                    await callback.message.edit_text(f"⭐️ Вы участвуете в розыгрыше! ⭐️\n\n<b>Ваш номер:  👉🏼 #</b> <code>{number}</code>\n\n🎁 Ожидайте подведение итогов!\n\nCпонсоры:\n✨ {sponstr}", parse_mode="HTML", disable_web_page_preview=True)
                else:
                    # Находим номер существующего пользователя
                    for i, user in enumerate(participants_ended_tasks):
                        if user.get("user_id") == callback.from_user.id:
                            number = i + 1
                            break
                    await callback.answer(f"Вы уже участвуете в розыгрыше, ваш номерок - #{number}", show_alert=True)
                    
        else:
            await callback.answer("Розыгрыш еще не начался, приходите позже", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка в checksub: {e}")
        logger.info("Произошла ошибка, попробуйте позже")


