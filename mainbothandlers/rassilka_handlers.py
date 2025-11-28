# handlers/rassilka_handlers.py
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram import Router, F, Bot
from database.models import Giveaway, Bots, Autopost, Gachannel, Bites
from states.mainstates import Rassilka, AutoRassilka, Posts
from keyboards.inline import addnewbotcancel_kb,posts_kb, canceldelay, newpostcancel, deletebite_kb, delay_kb, bites_kb, addphoto, pickparts_kb, rassilka_kb,channel_kb, autorassilka_kb, backtauto, post_kb, backtopost, postbutton_kb, channels_kb, publish_kb
from settings import main_bot
from main import scheduler, send_bite
import os
import uuid
import json
import logging
import asyncio
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()



PHOTO_DIR = './photos'
os.makedirs(PHOTO_DIR, exist_ok=True)

ZYAN_SIZE = 30
DELAY_BETWEEN_BATCHES = 1


async def send_with_retry(gaid: int, chat_id: int, text: str, photo, retries=2):
    attempt = 0
    while attempt <= retries:
        try:
            giveaway = await Giveaway.filter(id=gaid).first()
            bot = await Bots.filter(id=giveaway.bot).first()
            b_bot = Bot(token=bot.token)
            if photo:
                await b_bot.send_photo(chat_id=chat_id, photo=FSInputFile(photo), caption=text, parse_mode="HTML")
            else:
                await b_bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            logger.info(f"Сообщение отправлено пользователю {chat_id}")
            await b_bot.session.close()
            return True
        except Exception as e:
            logger.error(f"[Ошибка при отправке {chat_id}] {e}")
            if "Too Many Requests" in str(e):
                wait_time = int(str(e).split("after ")[1].strip()) + 1
                logger.warning(f"[RATE LIMIT] Ждём {wait_time} секунд...")
                await asyncio.sleep(wait_time)
                attempt += 1
            elif "Forbidden" in str(e):
                logger.warning(f"[Заблокирован] Пользователь {chat_id}")
                return False
            else:
                logger.warning(f"[Повторная попытка {attempt + 1}/{retries}] Ошибка: {e}")
                await asyncio.sleep(2 ** attempt)
                attempt += 1
            await b_bot.session.close()
    logger.error(f"[Неудача] Не удалось отправить пользователю {chat_id} после {retries} попыток")
    return False


async def send_bulk_message_background(adm_id: int, msg: int, gaid: int, user_ids: list, text: str, photo):
    """
    Фоновая рассылка — не блокирует бота
    """
    total = len(user_ids)
    logger.info(f"Начинаем фоновую рассылку для {total} пользователей")

    if not user_ids:
        try:
            await main_bot.edit_message_text(
                chat_id=adm_id,
                message_id=msg,
                text="📭 Нет участников для рассылки."
            )
        except Exception as e:
            logger.warning(f"Не удалось обновить статус: {e}")
        return

    totalsum = 0
    totaler = 0

    for i in range(0, total, ZYAN_SIZE):
        batch = user_ids[i:i + ZYAN_SIZE]
        tasks = [send_with_retry(gaid=gaid, chat_id=u, text=text, photo=photo) for u in batch]
        results = await asyncio.gather(*tasks)
        success = sum(results)
        totalsum += success
        failed = len(results) - success
        totaler += failed

        # Обновляем прогресс (каждые ZYAN_SIZE)
        try:
            await main_bot.edit_message_text(
                chat_id=adm_id,
                message_id=msg,
                text=f"📤 Рассылка... Отправлено: {i + ZYAN_SIZE if i + ZYAN_SIZE < total else total}/{total}"
            )
        except Exception as e:
            logger.warning(f"Ошибка обновления прогресса: {e} (возможно, сообщение устарело)")

        if i + ZYAN_SIZE < total:
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    # Удаляем фото
    if photo and os.path.exists(photo):
        try:
            os.remove(photo)
            logger.info(f"Фото удалено: {photo}")
        except Exception as e:
            logger.warning(f"Не удалось удалить фото {photo}: {e}")

    # Финальное сообщение
    try:
        giveaway = await Giveaway.filter(id=gaid).first()
        await main_bot.edit_message_text(
            chat_id=adm_id,
            message_id=msg,
            text=f"✅ Рассылка завершена!\n"
                 f"📬 Успешно: {totalsum}\n"
                 f"❌ Не отправлено: {totaler}",
            reply_markup=addnewbotcancel_kb(giveaway)
        )
    except Exception as e:
        logger.error(f"Финальное редактирование не удалось: {e}")
        try:
            # Если не можем отредактировать — отправим новое
            await main_bot.send_message(
                chat_id=adm_id,
                text=f"✅ Рассылка завершена!\n"
                     f"📬 Успешно: {totalsum}\n"
                     f"❌ Не отправлено: {totaler}",
                reply_markup=addnewbotcancel_kb(giveaway)
            )
        except:
            pass


@router.callback_query(F.data.startswith("gabotrassilka_"))
async def rassilka(callback: CallbackQuery, state: FSMContext):
    try:    
        id = callback.data.split("_")[1]
        giveaway = await Giveaway.filter(id=id).first()
        if len(json.loads(giveaway.participants)) > 0 or len(json.loads(giveaway.participants_ended_task)) > 0:
            
            await callback.message.edit_text("Введите текст рассылки:", reply_markup=addnewbotcancel_kb(giveaway))
            await state.set_state(Rassilka.text)
            await state.update_data(msg=callback.message.message_id, id=id)
        else:
            await callback.answer("Нет пользователей для рассылки!", show_alert= True)
    except Exception as e:
        logger.error(f"{e}")
        pass

@router.callback_query(F.data.startswith("edit_text_"))
async def rassilka(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        id = callback.data.split("_")[2]
        giveaway = await Giveaway.filter(id=id).first()
        await callback.message.edit_text("Введите текст рассылки:", reply_markup=addnewbotcancel_kb(giveaway))
        await state.set_state(Rassilka.text)
        await state.update_data(msg=callback.message.message_id, id=id)
    except Exception as e:
        logger.error(f"{e}")
        pass

@router.message(Rassilka.text)
async def rassilkamain(message: Message, state: FSMContext):
    data = await state.get_data()
    giveaway_id = data["id"]
    msg = data["msg"]

    # ✅ Правильный способ: получить HTML-текст с ссылками
    if message.entities:
        result_text = message.html_text
    else:
        result_text = message.html_text  # или message.text, но html_text безопаснее

    # Если нужно — добавить скрытую ссылку (для фото)
    # result_text += hide_link("https://t.me/tegivebot")

    try:
        await message.delete()
    except:
        pass

    await state.update_data(text=result_text)
    try:
        await main_bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg,
            text=f"Отлично, текст рассылки:\n{result_text}",
            reply_markup=addphoto(giveaway_id),
            parse_mode="HTML"
        )
    except:
        pass
    


@router.callback_query(F.data == "add_photo")
async def acceptaddphoto(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        data = await state.get_data()
        id = data["id"]
        msg = data["msg"]
        text = data["text"]
        await state.set_state(Rassilka.photo)
        await state.update_data(id=id, msg=msg, text=text)
        await callback.message.edit_text("Отправь фото для рассылки")
    except Exception as e:
        logger.error(f"{e}")
        pass

@router.message(Rassilka.photo)
async def pickphoto(message: Message, state: FSMContext):
    try:
        await message.delete()
    except:
        pass
    data = await state.get_data()
    id = data["id"]
    msg = data["msg"]
    giveaway = await Giveaway.filter(id=id).first()
    if message.photo:
        photo = message.photo[-1]
        file_info = await main_bot.get_file(photo.file_id)
        file_path = file_info.file_path
        ext = file_path.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{ext}"
        local_path = os.path.join(PHOTO_DIR, unique_filename)
        await main_bot.download_file(file_path, local_path)
        await state.update_data(photo=local_path)
        await main_bot.edit_message_text(chat_id=message.from_user.id, message_id=msg,
                                         text="Отлично, теперь выбери цели рассылки",
                                         reply_markup=pickparts_kb(giveaway))
    else:
        from keyboards.inline import addnewbotcancel_kb
        await main_bot.edit_message_text(chat_id=message.from_user.id, message_id=msg,
                                         text="Это не фото, попробуй отправить еще раз:",
                                         reply_markup=addnewbotcancel_kb(giveaway))


@router.callback_query(F.data == "skip_photo")
async def skipphoto(callback: CallbackQuery, state: FSMContext):
    
    data = await state.get_data()
    if "id" not in data:
        await callback.answer("❌ Ошибка: данные рассылки утеряны. Начните заново.", show_alert=True)
        await state.clear()
        return
    id = data["id"]
    await callback.answer()
    await state.update_data(photo="")
    giveaway = await Giveaway.filter(id=id).first()
    await callback.message.edit_text("Отлично, теперь выбери цели рассылки", reply_markup=pickparts_kb(giveaway))


@router.callback_query(F.data == "allparts")
async def sendtoall(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    text = data["text"]
    id = data["id"]
    photo = data["photo"]
    msg = callback.message.message_id

    giveaway = await Giveaway.filter(id=id).first()
    ids = [participant["user_id"] for participant in json.loads(giveaway.participants)]

    # Показываем, что рассылка запущена
    try:
        sent_msg = await callback.message.edit_text("🔄 Рассылка запущена, обработка участников...")
    except Exception as e:
        logger.warning(f"Не удалось обновить сообщение: {e}")
        await callback.message.answer("🔄 Рассылка запущена...")
        return

    # Запускаем в фоне
    asyncio.create_task(
        send_bulk_message_background(
            adm_id=callback.from_user.id,
            msg=sent_msg.message_id,
            gaid=id,
            user_ids=ids,
            text=text,
            photo=photo
        )
    )

    # Сбрасываем состояние
    await state.clear()


@router.callback_query(F.data == "endedtaskparts")
async def sendtoended(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    text = data["text"]
    id = data["id"]
    photo = data["photo"]
    msg = callback.message.message_id

    giveaway = await Giveaway.filter(id=id).first()
    ids = [participant["user_id"] for participant in json.loads(giveaway.participants_ended_task)]

    try:
        sent_msg = await callback.message.edit_text("🔄 Рассылка запущена для выполнивших задание...")
    except Exception as e:
        logger.warning(f"Не удалось обновить сообщение: {e}")
        await callback.message.answer("🔄 Рассылка запущена...")
        return

    asyncio.create_task(
        send_bulk_message_background(
            adm_id=callback.from_user.id,
            msg=sent_msg.message_id,
            gaid=id,
            user_ids=ids,
            text=text,
            photo=photo
        )
    )

    await state.clear()



@router.callback_query(F.data.startswith("rassilka_"))
async def rassilkasettings(callback:CallbackQuery):
    await callback.answer()

    id = callback.data.split('_')[1]
    
    autopost = await Autopost.filter(id = id).first()

    await callback.answer()
    if not autopost.postphoto:
        await callback.message.edit_text(f"<code>Настройки постов/байтов\n\n{'Авто байты выключены\n' if autopost.rassilkastatus == "off" else 'Авто байты включены\n'}Текст поста с розыгрышем:\n</code>{autopost.chatmsgtext if autopost.chatmsgtext else '\nпока нету...'}<code>\n\n {'Задержка авто байтов:' if autopost.rassilkastatus == 'on' else ''}{autopost.rassilkadelay if autopost.rassilkastatus == 'on' else ''} {'мин' if autopost.rassilkastatus == 'on' else ''}</code>", reply_markup=rassilka_kb(autopost))
    else:
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(f"<code>Настройки постов/байтов\n\n{'Авто байты выключены\n' if autopost.rassilkastatus == "off" else 'Авто байты включены\n'}Текст поста с розыгрышем:\n</code>{autopost.chatmsgtext if autopost.chatmsgtext else '\nпока нету...'}<code>\n\n{'Задержка авто байтов:' if autopost.rassilkastatus == 'on' else ''}{autopost.rassilkadelay if autopost.rassilkastatus == 'on' else ''} {'мин' if autopost.rassilkastatus == 'on' else ''}</code>", reply_markup=rassilka_kb(autopost))


@router.callback_query(F.data.startswith("autorassilka_"))
async def autorassilka(callback:CallbackQuery, state:FSMContext):
    await callback.answer()
    await state.clear()

    id = callback.data.split("_")[1]
    
    autopost = await Autopost.filter(id = id).first()
    await callback.message.edit_text(f"<code>{'Авто байты включены' if autopost.rassilkastatus == 'on' else 'Авто байты выключены'}\n\nЗадержка авто байтов: {autopost.rassilkadelay} мин</code>", reply_markup=autorassilka_kb(autopost), parse_mode="HTML")
    
@router.callback_query(F.data.startswith("autorassilkatext_"))
async def configautorassilkatext(callback:CallbackQuery, state:FSMContext):
    await callback.answer()

    id = callback.data.split("_")[1]
    giveaway = await Autopost.filter(id = id).first()

    await callback.message.edit_text("Введите текст байта:", reply_markup=backtauto(giveaway))

    await state.set_state(AutoRassilka.text)
    await state.update_data(msg=callback.message.message_id, id=id)


@router.message(AutoRassilka.text)
async def rassilkamain(message: Message, state: FSMContext):
    data = await state.get_data()
    id = data["id"]
    msg = data["msg"]

    # ✅ Правильный способ: получить HTML-текст с ссылками
    if message.entities:
        result_text = message.html_text
    else:
        result_text = message.html_text  # или message.text, но html_text безопаснее

    # Если нужно — добавить скрытую ссылку (для фото)
    # result_text += hide_link("https://t.me/tegivebot")

    try:
        await message.delete()
    except:
        pass

    autopost = await Autopost.filter(id = id).first()

    lastbite = await Bites.filter(admin = message.from_user.id).last()
    if lastbite:
        await Bites.create(admin = message.from_user.id, text = message.html_text, lastid = lastbite.lastid+1)
    else:
        await Bites.create(admin = message.from_user.id, text = message.html_text)

    bites = await Bites.filter(admin = message.from_user.id).all()

    try:
        await main_bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg,
            text=f"Отлично, текст авто байта:\n{result_text}\n\nВсего байтов: {len(bites)}",
            reply_markup=backtauto(autopost),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(e)

@router.callback_query(F.data.startswith('posttext_'))
async def posttext(callback:CallbackQuery, state:FSMContext):
    await callback.answer()
    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()
    
    await state.set_state(Posts.text)
    await state.update_data(msg = callback.message.message_id, id = id)
    if not autopost.postphoto:
        await callback.message.edit_text(f"<code>Текст поста:</code> {'нет' if not autopost.chatmsgtext else autopost.chatmsgtext}\n\n<code>Введи текст для поста в канал с розыгрышем</code>", reply_markup=backtopost(autopost), parse_mode="HTML")
    else:
        await callback.message.edit_caption(caption=f"Фото поста ☝️\n\n<code>Текст поста:</code> {'нету...' if not autopost.chatmsgtext else autopost.chatmsgtext}\n\n<code>Введи текст для поста в канал с розыгрышем</code>", reply_markup=backtopost(autopost), parse_mode="HTML")  

@router.message(Posts.text)
async def changeposttext(message:Message, state:FSMContext):
    data = await state.get_data()
    try:
        await message.delete()
    except:
        pass
    text = message.html_text
    await Autopost.filter(id = data['id']).update(chatmsgtext = text)
    autopost = await Autopost.filter(id = data['id']).first()
    if not autopost.postphoto:
        await main_bot.edit_message_text(message_id=data['msg'], chat_id=message.from_user.id, text=f"<code>{'Текст поста:' if autopost.chatmsgtext else 'Текста поста пока нет...'}</code>{autopost.chatmsgtext if autopost.chatmsgtext else ''}\n\n<code>{'Текст кнопки поста:' if autopost.chatmsgbuttontext else 'Текста кнопки поста пока нет...'}</code> {autopost.chatmsgbuttontext if autopost.chatmsgbuttontext else ''}\n\n<code>{'Ссылка кнопки поста:' if autopost.buttonlink else 'Ccылки кнопки поста пока нет...'}</code> {autopost.buttonlink if autopost.buttonlink else ''} <code>Нажимай на кнопки чтобы поменять настройки поста:</code>", reply_markup=post_kb(autopost), parse_mode="HTML")
    else:
        await main_bot.edit_message_caption(message_id=data['msg'], chat_id=message.from_user.id, caption=f"<code>{'Текст поста:' if autopost.chatmsgtext else 'Текста поста пока нет...'}</code>{autopost.chatmsgtext if autopost.chatmsgtext else ''}\n\n<code>{'Текст кнопки поста:' if autopost.chatmsgbuttontext else 'Текста кнопки поста пока нет...'}</code> {autopost.chatmsgbuttontext if autopost.chatmsgbuttontext else ''}\n\n<code>{'Ссылка кнопки поста:' if autopost.buttonlink else 'Ccылки кнопки поста пока нет...'}</code> {autopost.buttonlink if autopost.buttonlink else ''} <code>Нажимай на кнопки чтобы поменять настройки поста:</code>", reply_markup=post_kb(autopost), parse_mode="HTML")


@router.callback_query(F.data.startswith('channelpost_'))
async def cahnnelpost(callback:CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()
    if not autopost.postphoto:
        await callback.message.edit_text(f"<code>{'Текст поста:' if autopost.chatmsgtext else 'Текста поста пока нет...'}</code>{autopost.chatmsgtext if autopost.chatmsgtext else ''}\n\n<code>{'Текст кнопки поста:' if autopost.chatmsgbuttontext else 'Текста кнопки поста пока нет...'}</code> {autopost.chatmsgbuttontext if autopost.chatmsgbuttontext else ''}\n\n<code>{'Ссылка кнопки поста:' if autopost.buttonlink else 'Ccылки кнопки поста пока нет...'}</code> {autopost.buttonlink if autopost.buttonlink else ''} <code>\nНажимай на кнопки чтобы поменять настройки поста:</code>", reply_markup=post_kb(autopost), parse_mode="HTML")
    else:
        photo = FSInputFile(autopost.postphoto)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer_photo(photo = photo, caption=f"<code>Фото поста ☝️\n\n{'Текст поста:' if autopost.chatmsgtext else 'Текста поста пока нет...'}</code>{autopost.chatmsgtext if autopost.chatmsgtext else ''}\n\n<code>{'Текст кнопки поста:' if autopost.chatmsgbuttontext else 'Текста кнопки поста пока нет...'}</code> {autopost.chatmsgbuttontext if autopost.chatmsgbuttontext else ''}\n\n<code>{'Ссылка кнопки поста:' if autopost.buttonlink else 'Ccылки кнопки поста пока нет...'}</code> {autopost.buttonlink if autopost.buttonlink else ''} <code>\nНажимай на кнопки чтобы поменять настройки поста:</code>", reply_markup=post_kb(autopost), parse_mode="HTML")

@router.callback_query(F.data.startswith('postbuttontext_'))
async def posttext(callback:CallbackQuery, state:FSMContext):
    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()
    
    await state.set_state(Posts.buttontext)
    await state.update_data(msg = callback.message.message_id, id = id)
    await callback.message.edit_text(f"<code>Текст кнопки поста:</code> {'нет' if not autopost.chatmsgbuttontext else autopost.chatmsgbuttontext}\n\n<code>Введи текст для кнопки поста в канал с розыгрышем</code>", reply_markup=backtopost(autopost), parse_mode="HTML")


@router.message(Posts.buttontext)
async def changeposttext(message:Message, state:FSMContext):
    data = await state.get_data()
    try:
        await message.delete()
    except:
        pass
    text = message.html_text
    await Autopost.filter(id = data['id']).update(chatmsgbuttontext = text)
    autopost = await Autopost.filter(id = data['id']).first()
    msg = data['msg']
    await main_bot.edit_message_text(
    chat_id=message.chat.id,  # Добавлен chat_id
    message_id=msg,  # Добавлен message_id
    text=f"<code>Текст кнопки поста:</code> {'нет' if not autopost.chatmsgbuttontext else autopost.chatmsgbuttontext}\n\n<code>Введи текст для кнопки поста в канал с розыгрышем</code>", 
    reply_markup=backtopost(autopost), 
    parse_mode="HTML"
)
@router.callback_query(F.data.startswith('postbuttonlink_'))
async def postbuttonlink(callback:CallbackQuery, state:FSMContext):
    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()
    
    await state.set_state(Posts.link)
    await state.update_data(msg = callback.message.message_id, id = id)
    await callback.message.edit_text(f"<code>Ссылка кнопки поста:</code> {'нет' if not autopost.buttonlink else autopost.buttonlink}\n\n<code>Введи ссылку для кнопки поста в канал с розыгрышем</code>\n\n<code>Пример ссылки:</code> https://t.me/channel", reply_markup=backtopost(autopost), parse_mode="HTML", disable_web_page_preview=True)

@router.message(Posts.link)
async def changeposttext(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.delete()
    except:
        pass

    text = message.text.strip()

    # Проверка, что ссылка начинается с t.me/ или https://t.me/
    

    
    autopost = await Autopost.filter(id=data['id']).first()
    
    
    if not re.match(r"^https?://t\.me/([a-zA-Z][a-zA-Z0-9_]{4,31})/?$", text):
        await main_bot.edit_message_text(message_id=data['msg'], chat_id=message.from_user.id, text="❌ Ссылка должна быть в формате:\n<code>t.me/username</code> или <code>https://t.me/username</code>", parse_mode="HTML", reply_markup=backtopost(autopost))
        return
    await Autopost.filter(id=data['id']).update(buttonlink=text)
    newautopost = await Autopost.filter(id=data['id']).first()

    await main_bot.edit_message_text(
        message_id=data['msg'],
        chat_id=message.from_user.id,
        text=f"<code>Текст кнопки:</code> {newautopost.chatmsgbuttontext}\n\n<code>Ccылка кнопки:</code> {newautopost.buttonlink if newautopost.buttonlink else 'нет...'}",
        reply_markup=postbutton_kb(newautopost),
        parse_mode="HTML"
    )
@router.callback_query(F.data.startswith('postbutton_'))
async def postbutton(callback:CallbackQuery):
    await callback.answer()
    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(f"<code>Текст кнопки:</code> {autopost.chatmsgbuttontext}\n\n<code>Ccылка кнопки:</code> {autopost.buttonlink if autopost.buttonlink else 'нет...'}", reply_markup=postbutton_kb(autopost), parse_mode="HTML")


@router.callback_query(F.data.startswith('postphoto_'))
async def addpostphoto(callback:CallbackQuery, state:FSMContext):
    await callback.answer()
    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()

    await state.set_state(Posts.photo)
    await state.update_data(msg = callback.message.message_id, id = id)
    
    if autopost.postphoto:
        await callback.message.edit_caption(caption="Отправь фото которое будет в посте", reply_markup=backtopost(autopost))
    else:
        await callback.message.edit_text("Отправь фото которое будет в посте", reply_markup=backtopost(autopost))


@router.message(Posts.photo)
async def postphoto(message:Message, state:FSMContext):
    data = await state.get_data()
    id = data['id']
    msg = data['msg']
    try:
        await message.delete()
    except:
        pass
    autopost = await Autopost.filter(id = id).first()
    
    if not message.photo:
        await main_bot.edit_message_text(chat_id=message.from_user.id, message_id=msg, text="Это не фото!", reply_markup=backtopost(autopost))
    else:
        try:
            photo = message.photo[-1]
            file_info = await main_bot.get_file(photo.file_id)
            file_path = file_info.file_path
            ext = file_path.split('.')[-1]
            unique_filename = f"post_{autopost.id}.{ext}"
            local_path = os.path.join(PHOTO_DIR, unique_filename)
            await Autopost.filter(id=id).update(postphoto = local_path)
            await main_bot.download_file(file_path, local_path)
            try:
                await main_bot.delete_message(chat_id=message.from_user.id, message_id=msg)
            except:
                pass
            newpost = await Autopost.filter(id=id).first()
            newphoto = FSInputFile(newpost.postphoto)
            await main_bot.send_photo(chat_id=message.from_user.id, photo = newphoto, caption=f"<code>Фото поста ☝️\n\n{'Текст поста:' if autopost.chatmsgtext else 'Текста поста пока нет...'}</code>{autopost.chatmsgtext if autopost.chatmsgtext else ''}\n\n<code>{'Текст кнопки поста:' if autopost.chatmsgbuttontext else 'Текста кнопки поста пока нет...'}</code> {autopost.chatmsgbuttontext if autopost.chatmsgbuttontext else ''}\n\n<code>{'Ссылка кнопки поста:' if autopost.buttonlink else 'Ccылки кнопки поста пока нет...'}</code> {autopost.buttonlink if autopost.buttonlink else ''} <code>\nНажимай на кнопки чтобы поменять настройки поста:</code>", reply_markup=post_kb(autopost), parse_mode="HTML")
 
        except Exception as e:
            logger.error(f"{e}")


@router.callback_query(F.data.startswith('postchannel_'))
async def postcahnnel(callback:CallbackQuery):
    await callback.answer()

    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()
    

    channels = await Gachannel.filter(admin = callback.from_user.id).all()

    try:
        await callback.message.delete()
    except:
        pass
    if not autopost.gachannel:
        await callback.message.answer(f"Выберите канал снизу или добавьте новый", reply_markup=channels_kb(channels, autopost))
    else:
        channel = await Gachannel.filter(id = autopost.gachannel).first()
        chat = await main_bot.get_chat(chat_id=channel.chatid)
        await callback.message.answer(f"Текущий канал: {'@'+chat.username if chat.username else chat.invite_link}\n\nВыберите канал снизу или добавьте новый", reply_markup=channels_kb(channels, autopost), parse_mode="HTML")

@router.callback_query(F.data.startswith('addnewchannel_'))
async def addnewchannelpost(callback:CallbackQuery, state:FSMContext):
    await callback.answer()
    id = callback.data.split("_")[1]
    autopost = await Autopost.filter(id = id).first()
   
    await callback.message.edit_text("1. Добавь меня @contestUCbot в администраторы подключаемого канала \n2. Необходимо разрешение Добавление участников/Пригласительные ссылки\n3. Перешли мне любое сообщение из канала (прямо в этот чат).\nЯ жду..", reply_markup=backtopost(autopost), parse_mode="HTML")

    await state.set_state(Posts.channel)
    await state.update_data(id = id, msg = callback.message.message_id)


@router.message(Posts.channel)
async def resendedmessage(message: Message, state: FSMContext):
    data = await state.get_data()
    gaid = data.get("id")
    msg = data["msg"]
    try:
        await message.delete()
    except:
        pass
    autopost = await Autopost.filter(id=gaid).first()
    
    if not message.forward_from_chat:
        try:
            await message.delete()
        except:
            pass
        await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg,
                                         text="Это сообщение не переслано с другого канала!",
                                         reply_markup=backtopost(autopost))
        await state.set_state(Posts.channel)
        return
    chat_id = message.forward_from_chat.id
    title = message.forward_from_chat.title
    channel = await Gachannel.create(admin = message.from_user.id, chatid = chat_id, name = title)
    channels = await Gachannel.filter(admin = message.from_user.id).all()
    await Autopost.filter(id = gaid).update(gachannel = channel.id)
    chat = await main_bot.get_chat(chat_id=channel.chatid)
    await main_bot.edit_message_text(chat_id=message.chat.id, message_id=msg, text=f"Текущий канал: {'@'+chat.username if chat.username else chat.invite_link}\n\nВыберите канал снизу или добавьте новый", reply_markup=channels_kb(channels, autopost))


@router.callback_query(F.data.startswith('publish_'))
async def publishpost(callback:CallbackQuery):
    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()

    if not autopost.chatmsgtext or not autopost.buttonlink or not autopost.gachannel:
        await callback.answer("Для начала настрой пост, введи текст, вставь ссылку в кнопку поста, выбери канал в котором будет опубликован пост:", show_alert=True)
        return

    await callback.answer("Проверь всю информацию о посте:", show_alert=True)
    channel = await Gachannel.filter(id = autopost.gachannel).first()
    chat = await main_bot.get_chat(chat_id=channel.chatid)
    if not autopost.postphoto:
        await callback.message.edit_text(f"<code>Текущий канал:</code> {'@'+chat.username if chat.username else chat.invite_link}\n\n<code>{'Текст поста:' if autopost.chatmsgtext else 'Текста поста пока нет...'}</code>{autopost.chatmsgtext if autopost.chatmsgtext else ''}\n\n<code>{'Текст кнопки поста:' if autopost.chatmsgbuttontext else 'Текста кнопки поста пока нет...'}</code> {autopost.chatmsgbuttontext if autopost.chatmsgbuttontext else ''}\n\n<code>{'Ссылка кнопки поста:' if autopost.buttonlink else 'Ccылки кнопки поста пока нет...'}</code> {autopost.buttonlink if autopost.buttonlink else ''}", parse_mode="HTML", reply_markup=publish_kb(autopost))
    else:
        await callback.message.edit_caption(caption=f"<code>Текущий канал:</code> {'@'+chat.username if chat.username else chat.invite_link}\n\n<code>{'Текст поста:' if autopost.chatmsgtext else 'Текста поста пока нет...'}</code>{autopost.chatmsgtext if autopost.chatmsgtext else ''}\n\n<code>{'Текст кнопки поста:' if autopost.chatmsgbuttontext else 'Текста кнопки поста пока нет...'}</code> {autopost.chatmsgbuttontext if autopost.chatmsgbuttontext else ''}\n\n<code>{'Ссылка кнопки поста:' if autopost.buttonlink else 'Ccылки кнопки поста пока нет...'}</code> {autopost.buttonlink if autopost.buttonlink else ''}", parse_mode="HTML", reply_markup=publish_kb(autopost))

@router.callback_query(F.data.startswith('acceptpublish_'))
async def acceptpublish(callback:CallbackQuery):
    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()
    channel = await Gachannel.filter(id = autopost.gachannel).first()
    try:
        if autopost.postphoto:
            photo = FSInputFile(autopost.postphoto)
            post = await main_bot.send_photo(chat_id=channel.chatid, photo=photo, caption=autopost.chatmsgtext, reply_markup=channel_kb(autopost))
            
        else:
            post = await main_bot.send_message(chat_id=channel.chatid, text=autopost.chatmsgtext, reply_markup=channel_kb(autopost))
        await Autopost.filter(id = id).update(postid = post.message_id)
        await callback.answer("Успешно опубликовано!\n\nНажми 'НАЗАД' чтобы вернуться", show_alert=True)
        
    except Exception as e:
        await callback.answer()
        logger.error(f'{e}')

@router.callback_query(F.data.startswith('bitetext_'))
async def bitetext(callback:CallbackQuery):
    await callback.answer()

    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()

    bites = await Bites.filter(admin = callback.from_user.id).all()
    await callback.message.edit_text(f'<code>Всего байтов: {len(bites)}</code>', reply_markup=bites_kb(bites, autopost))



@router.callback_query(F.data.startswith('autopostbite_'))
async def bite(callback:CallbackQuery):
    await callback.answer()

    _,postid,biteid = callback.data.split('_')
    
    autopost = await Autopost.filter(id = postid).first()

    bite = await Bites.filter(id = biteid).first()
            
    await callback.message.edit_text(f'Текст байта:\n\n{bite.text}', reply_markup=deletebite_kb(biteid, autopost))


@router.callback_query(F.data.startswith('deletebite_'))
async def deletebite(callback:CallbackQuery):
    await callback.answer('Удалено!', show_alert=True)

    _,postid,biteid = callback.data.split('_')

    bites = await Bites.filter(admin = callback.from_user.id).all()

    await Bites.filter(id = biteid).delete()

    newautopost = await Autopost.filter(id = postid).first()

    await callback.message.edit_text(f'<code>Всего байтов: {len(bites)}</code>', reply_markup=bites_kb(bites, newautopost))


@router.callback_query(F.data.startswith('autorassilkadelay_'))
async def delay(callback:CallbackQuery):
    await callback.answer()

    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()

    delay = autopost.rassilkadelay

    await callback.message.edit_text(f'<code>Задержка байтов: {delay}, чтобы поменять нажимай на кнопки</code>', reply_markup=delay_kb(autopost))


@router.callback_query(F.data.startswith('delay_'))
async def setdelay(callback:CallbackQuery):
    await callback.answer('Изменено!')

    _,delay,postid = callback.data.split("_")

    autopost = await Autopost.filter(id = postid).first()
    channel = await Gachannel.filter(id = autopost.gachannel).first()
    #if autopost.rassilkastatus == 'on':
        
    await Autopost.filter(id = postid).update(rassilkadelay = delay)
    if autopost.rassilkastatus == 'on':
        scheduler.remove_job(f'bites_{autopost.id}')
        newautopost = await Autopost.filter(id = postid).first()
        scheduler.add_job(send_bite, 'interval', minutes = newautopost.rassilkadelay, args=[autopost.id, channel.chatid, autopost.postid, callback.from_user.id], id=f'bites_{autopost.id}')

    await callback.message.edit_text(f'<code>Задержка байтов: {delay}, чтобы поменять нажимай на кнопки</code>', reply_markup=delay_kb(autopost))

@router.callback_query(F.data.startswith('autorassilkaon_'))
async def onbites(callback:CallbackQuery):
    

    id = callback.data.split("_")[1]

    autopost = await Autopost.filter(id = id).first()
    
    channel = await Gachannel.filter(id = autopost.gachannel).first()
    bites = await Bites.filter(admin = callback.from_user.id).all()

    if len(bites) > 0 and autopost.rassilkadelay>0 and autopost.postid:
        await callback.answer(f'Включены авто-байты c задержкой в {autopost.rassilkadelay} минут', show_alert=True)
        await Autopost.filter(id = id).update(rassilkastatus = 'on')
        newautopost = await Autopost.filter(id = id).first()
        await callback.message.edit_text(f"<code>{'Авто байты включены' if newautopost.rassilkastatus == 'on' else 'Авто байты выключены'}\n\nЗадержка авто байтов: {autopost.rassilkadelay} мин</code>", reply_markup=autorassilka_kb(newautopost), parse_mode="HTML")
        if scheduler.get_job(f'bites_{newautopost.id}'):
            scheduler.remove_job(f'bites_{newautopost.id}')
        scheduler.add_job(send_bite, 'interval', minutes = autopost.rassilkadelay, args=[autopost.id, channel.chatid, autopost.postid, callback.from_user.id], id=f'bites_{autopost.id}')
    else:
        await callback.answer(f'Сначала надо настроить задержку, добавить хотя бы один байт и запостить в канал основной пост с розыгрышем!', show_alert=True)

@router.callback_query(F.data.startswith('autorassilkaoff_'))
async def offbites(callback:CallbackQuery):
    id = callback.data.split("_")[1]
    await callback.answer('Выключено!', show_alert=True)
    await Autopost.filter(id = id).update(rassilkastatus = 'off')
    
    autopost = await Autopost.filter(id = id).first()
    
    
    await callback.message.edit_text(f"<code>{'Авто байты включены' if autopost.rassilkastatus == 'on' else 'Авто байты выключены'}\n\nЗадержка авто байтов: {autopost.rassilkadelay} мин</code>", reply_markup=autorassilka_kb(autopost), parse_mode="HTML")


    scheduler.remove_job(f'bites_{id}')


@router.callback_query(F.data == 'posts')
async def posts(callback:CallbackQuery):
    await callback.answer()
    posts = await Autopost.filter(admin = callback.from_user.id).all()

    await callback.message.edit_text(f'Всего постов: {len(posts)}\n\nНажмите "СОЗДАТЬ ПОСТ" чтобы создать новый', reply_markup=posts_kb(posts))

@router.callback_query(F.data == 'newpost')
async def newpost(callback:CallbackQuery, state:FSMContext):
    await callback.answer()

    await callback.message.edit_text('Введите название нового поста:', reply_markup=newpostcancel())

    await state.set_state(Posts.newpost)

    await state.update_data(msg = callback.message.message_id)

@router.message(Posts.newpost)
async def newposttwo(message:Message, state:FSMContext):
    data = await state.get_data()

    msg = data['msg']

    try:
        await message.delete()
    except:
        pass

    autopost = await Autopost.create(title = message.text, admin = message.from_user.id)    
    await main_bot.edit_message_text(message_id=msg, chat_id=message.from_user.id, text=f"<code>Настройки постов/байтов\n\n{'Авто байты выключены\n' if autopost.rassilkastatus == "off" else 'Авто байты включены\n'}Текст поста с розыгрышем:\n</code>{autopost.chatmsgtext if autopost.chatmsgtext else '\nпока нету...'}<code>\n\n {'Задержка авто байтов:' if autopost.rassilkastatus == 'on' else ''}{autopost.rassilkadelay if autopost.rassilkastatus == 'on' else ''} {'мин' if autopost.rassilkastatus == 'on' else ''}</code>", reply_markup=rassilka_kb(autopost))


@router.callback_query(F.data.startswith('oldchannel_'))
async def pickchannel(callback:CallbackQuery):
    await callback.answer()

    _,chid,aid = callback.data.split('_')

    channel = await Gachannel.filter(id = chid).first()
    autopost = await Autopost.filter(id = aid).first()
    channels = await Gachannel.filter(admin = callback.from_user.id).all()
    await Autopost.filter(id = aid).update(gachannel = channel.id)
    chat = await main_bot.get_chat(chat_id=channel.chatid)
    await callback.message.edit_text(f"Текущий канал: {'@'+chat.username if chat.username else chat.invite_link}\n\nВыберите канал снизу или добавьте новый", reply_markup=channels_kb(channels, autopost))



@router.callback_query(F.data.startswith('adddelay_'))
async def adddelay(callback:CallbackQuery, state:FSMContext):
    id = callback.data.split("_")[1]
    await callback.answer()
    autopost = await Autopost.filter(id = id).first()

    await state.set_state(Posts.delay)
    await state.update_data(id = id, msg = callback.message.message_id)

    await callback.message.edit_text('Введите свою задержку (в минутах, больше 15):', reply_markup=canceldelay(autopost))

@router.message(Posts.delay)
async def setdelay(message:Message, state:FSMContext):

    data = await state.get_data()

    id = data['id']
    try:
        await message.delete()
    except:
        pass
    msg = data['msg']
    text = message.text
    autopost = await Autopost.filter(id = id).first()
    channel = await Gachannel.filter(id = autopost.gachannel).first()
    #if autopost.rassilkastatus == 'on':
    if int(text)>15:    
        await Autopost.filter(id = id).update(rassilkadelay = int(text))
    else:
        await main_bot.edit_message_text(chat_id=message.from_user.id, message_id=msg, text='Это не число или оно не больше 15', reply_markup=canceldelay(autopost))
        await state.set_state(Posts.delay)
    if autopost.rassilkastatus == 'on':
        scheduler.remove_job(f'bites_{autopost.id}')
        newautopost = await Autopost.filter(id = id).first()
        scheduler.add_job(send_bite, 'interval', minutes = newautopost.rassilkadelay, args=[autopost.id, channel.chatid, autopost.postid, message.from_user.id], id=f'bites_{autopost.id}')

    await main_bot.edit_message_text(chat_id=message.from_user.id, message_id=msg, text= f'<code>Задержка байтов: {int(text)}, чтобы поменять нажимай на кнопки</code>', reply_markup=delay_kb(autopost))