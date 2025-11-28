import asyncio
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from aiogram.exceptions import TelegramServerError, TelegramUnauthorizedError
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery, TelegramObject
from aiogram.client.default import DefaultBotProperties
from typing import Callable, Dict, Any
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from database.main_db import init_db
from settings import config, main_bot as main_bot_instance
from keyboards.inline import gotogiveaway_kb
import logging
import random
from database.models import Bots, Giveaway, Admin, Autopost, Gachannel, Bites, Users
import importlib
from pathlib import Path
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WEBHOOK_HOST = "https://nellumaqwe.online"
WEBHOOK_PATH = "/webhook"

storage_main = MemoryStorage()
storage_baby = MemoryStorage()
main_dp = Dispatcher(storage=storage_main)
baby_dp = Dispatcher(storage=storage_baby)

app = FastAPI()
scheduler = AsyncIOScheduler()

main_handlers_dir = Path(__file__).parent / "mainbothandlers"
baby_handlers_dir = Path(__file__).parent / "babybothandlers"

class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Определяем user_id и username
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        else:
            return await handler(event, data)  # пропускаем другие типы событий

        user_id = user.id
        username = user.username  # может быть None

        logger.info(f"Проверка доступа для: id={user_id}, username={username}")

        # Проверяем, является ли пользователь главным админом
        if user_id == int(config['MAINADMIN']):
            return await handler(event, data)

        # Проверяем, существует ли админ по admin_id или по username
        is_admin = False
        admin_record = None

        if user_id:
            admin_record = await Admin.filter(admin_id=user_id).first()
            if admin_record:
                is_admin = True

        if not is_admin and username:
            admin_record = await Admin.filter(username=username).first()
            if admin_record:
                is_admin = True
                # Если нашли по username, но admin_id ещё не установлен — обновляем
                if not admin_record.admin_id:
                    await Admin.filter(username=username).update(admin_id=user_id)

        # Если не админ — отказываем
        if not is_admin:
            if isinstance(event, Message):
                await event.answer("⛔ Доступ запрещён. Только администраторы могут использовать этого бота.")
                await event.answer("У тебя на выбор две подписки ⬇️\n\n<strong>«Базовая»</strong>\n\n<blockquote><em>В функционал бота входит:\n\n• создание розыгрышей идентичных Tegive\n• удаление/замена спонсоров во время розыгрыша \n• рассылка. поддерживает фото\n\nСтоимость: 37$\nЗа покупкой к @kuniloverbot</em></blockquote>\n\n<strong>«Для ценителей»</strong>\n\n<blockquote><em>В функционал бота входит:\n\n• весь функционал подписки «базовая»\n• авто-байты. бот сам отправляет напоминание на пост, и сам же его удаляет, с любым удобным вам интервалом времени\n• постинг розыгрышей, и любых других постов. больше не нужны сторонние боты\n\nСтоимость: 62$\nЗа покупкой к @kuniloverbot</em></blockquote>", parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ У тебя нет прав для этого действия.", show_alert=True)
                await event.answer("У тебя на выбор две подписки ⬇️\n\n<strong>«Базовая»</strong>\n\n<blockquote><em>В функционал бота входит:\n\n• создание розыгрышей идентичных Tegive\n• удаление/замена спонсоров во время розыгрыша \n• рассылка. поддерживает фото\n\nСтоимость: 37$\nЗа покупкой к @kuniloverbot</em></blockquote>\n\n<strong>«Для ценителей»</strong>\n\n<blockquote><em>В функционал бота входит:\n\n• весь функционал подписки «базовая»\n• авто-байты. бот сам отправляет напоминание на пост, и сам же его удаляет, с любым удобным вам интервалом времени\n• постинг розыгрышей, и любых других постов. больше не нужны сторонние боты\n\nСтоимость: 62$\nЗа покупкой к @kuniloverbot</em></blockquote>", parse_mode="HTML")

            return  # не передаём дальше

        # Синхронизируем данные админа (имя, юзернейм)
        if admin_record:
            update_data = {}
            if admin_record.name != user.full_name:
                update_data['name'] = user.full_name
            if admin_record.username != username:
                update_data['username'] = username

            if update_data:
                await Admin.filter(id=admin_record.id).update(**update_data)

        # Пропускаем событие дальше
        return await handler(event, data)

async def endga(giveaway_id, chat, msg = None):
    from database.models import Sponsors
    giveaway = await Giveaway.filter(id=giveaway_id).first()
    if giveaway.status == "started":
        if msg:
            try:
                colors = ["🟦", "🟧", "⬜"]  # голубой, оранжевый, белый
                # Начальная анимация ленты - распространение от центра
                max_width = 3
                for i in range(max_width):
                    left_part = "".join(colors[(max_width - i + j) % 3] for j in range(i))
                    right_part = "".join(colors[(max_width - i + j) % 3] for j in range(i))
                    center = "🎮" if i > 3 else "🎲"  # Меняем эмодзи в центре
                    rgb_line = f"{left_part}{center}{right_part}"
                    giveaway_info = f"""
    ⠀⠀⠀⠀⠀{rgb_line}

🎮 РОЗЫГРЫШ: {giveaway.title}

👥 УЧАСТНИКОВ: {len(json.loads(giveaway.participants_ended_task))}
🏆 ПОБЕДИТЕЛЕЙ: {giveaway.winners_amount}

🤝 СПОНСОРЫ: {len(await Sponsors.filter(giveaway=giveaway.id))}

    ⠀⠀⠀⠀⠀{rgb_line}
"""
                    if i == 0:
                        animation_msg = await main_bot_instance.edit_message_text(chat_id=chat,message_id=msg, text=giveaway_info) # Замените 123456789 на ID администратора
                    else:
                        await animation_msg.edit_text(giveaway_info)
                    await asyncio.sleep(0.2)
                # Пульсирующая лента во время основной анимации
                pulse_patterns = [
                    "🟦🟧⬜🎮🟧⬜🟦",
                    "⬜🟦🟧🎮🟦🟧⬜",
                    "🟧⬜🟦🎮⬜🟦🟧"
                ]
                # Анимация "вращаю барабан"
                await asyncio.sleep(0.5)
                drum_phrases = [
                    "🎲 Вращаю барабан.",
                    "🎲 Вращаю барабан..",
                    "🎲 Вращаю барабан...",
                    "🎯 Барабан вращается.",
                    "🎯 Барабан вращается..",
                    "🎯 Барабан вращается...",
                    "🎪 Ищу счастливчиков.",
                    "🎪 Ищу счастливчиков..",
                    "🎪 Ищу счастливчиков..."
                ]
                pulse_index = 0
                for phrase in drum_phrases:
                    current_pulse = pulse_patterns[pulse_index % len(pulse_patterns)]
                    giveaway_info = f"""
    ⠀⠀⠀⠀⠀{current_pulse}

🎮 РОЗЫГРЫШ: {giveaway.title}

👥 УЧАСТНИКОВ: {len(json.loads(giveaway.participants_ended_task))}
🏆 ПОБЕДИТЕЛЕЙ: {giveaway.winners_amount}

🤝 СПОНСОРЫ: {len(await Sponsors.filter(giveaway=giveaway.id))}
"""
                    await animation_msg.edit_text(f"{giveaway_info}\n{phrase}\n\n⠀⠀⠀⠀⠀{current_pulse}")
                    await asyncio.sleep(0.2)
                    pulse_index += 1
                # Расширенная анимация прогресс-бара (7 строк)
                progress_lines = [
                    "📊 Подготовка данных...",
                    "🔍 Анализ участников...",
                    "🧮 Подсчет вероятностей...",
                    "🎯 Выбор победителей...",
                    "🎊 Генерация результатов...",
                    "📥 Загрузка финальных данных...",
                    "🏆 Почти готово..."
                ]
                progress = 0
                line_index = 0
                while progress < 100:
                    progress += 5  # Меньший шаг для большей плавности
                    bar = "█" * (progress // 5) + "░" * (20 - progress // 5)
                    # Анимация ленты во время прогресса
                    current_pulse = pulse_patterns[(progress // 5) % len(pulse_patterns)]
                    # Выбираем текущую строку
                    if progress % 15 == 0 and line_index < len(progress_lines):
                        current_line = progress_lines[line_index]
                        line_index += 1
                    elif progress < 15:
                        current_line = "📊 Подготовка данных..."
                    else:
                        current_line = progress_lines[line_index - 1]
                    progress_display = f"""
    ⠀⠀⠀⠀⠀{current_pulse}

🎮 РОЗЫГРЫШ: {giveaway.title}

👥 УЧАСТНИКОВ: {len(json.loads(giveaway.participants_ended_task))}
🏆 ПОБЕДИТЕЛЕЙ: {giveaway.winners_amount}

🤝 СПОНСОРЫ: {len(await Sponsors.filter(giveaway=giveaway.id))}
    {current_line}
    [{bar}] {progress}%

    ⠀⠀⠀⠀⠀{current_pulse}
"""
                    await animation_msg.edit_text(progress_display)
                    await asyncio.sleep(0.15)
                # Анимация "достаю номерки" с пульсирующей лентой
                await asyncio.sleep(0.25)
                pickup_phrases = [
                    "📬 Открываю коробку с номерками.",
                    "📬 Открываю коробку с номерками..",
                    "📬 Открываю коробку с номерками...",
                    "🔍 Проверяю первый счастливый номерок.",
                    "🔍 Проверяю первый счастливый номерок..",
                    "🔍 Проверяю первый счастливый номерок...",
                    "🎉 Вынимаю второй победный билет.",
                    "🎉 Вынимаю второй победный билет..",
                    "🎉 Вынимаю второй победный билет...",
                    "🔮 Заглядываю в хрустальный шар за третьим номерком.",
                    "🔮 Заглядываю в хрустальный шар за третьим номерком..",
                    "🔮 Заглядываю в хрустальный шар за третьим номерком...",
                    "💎 Достаю драгоценные выигрышные номерки.",
                    "💎 Достаю драгоценные выигрышные номерки..",
                    "💎 Достаю драгоценные выигрышные номерки...",
                    "🎪 Вытаскиваю финальные призовые билеты.",
                    "🎪 Вытаскиваю финальные призовые билеты..",
                    "🎪 Вытаскиваю финальные призовые билеты..."
                ]
                pulse_index = 0
                for phrase in pickup_phrases:
                    current_pulse = pulse_patterns[pulse_index % len(pulse_patterns)]
                    giveaway_info = f"""
    ⠀⠀⠀⠀⠀{current_pulse}

🎮 РОЗЫГРЫШ: {giveaway.title}

👥 УЧАСТНИКОВ: {len(json.loads(giveaway.participants_ended_task))}
🏆 ПОБЕДИТЕЛЕЙ: {giveaway.winners_amount}

🤝 СПОНСОРЫ: {len(await Sponsors.filter(giveaway=giveaway.id))}
"""
                    await animation_msg.edit_text(f"{giveaway_info}\n{phrase}\n\n⠀⠀⠀⠀⠀{current_pulse}")
                    await asyncio.sleep(0.2)
                    pulse_index += 1
                # Финальная анимация выбора
                final_phrases = [
                    "👑 Сверяю с золотым списком победителей.",
                    "👑 Сверяю с золотым списком победителей..",
                    "👑 Сверяю с золотым списком победителей...",
                    "🏅 Подтверждаю финальных чемпионов.",
                    "🏅 Подтверждаю финальных чемпионов..",
                    "🏅 Подтверждаю финальных чемпионов...",
                    "✨ Применяю магию случайности.",
                    "✨ Применяю магию случайности..",
                    "✨ Применяю магию случайности...",
                    "🎯 Фиксирую исторические итоги.",
                    "🎯 Фиксирую исторические итоги..",
                    "🎯 Фиксирую исторические итоги...",
                    "🎪 Объявляю имена счастливчиков.",
                    "🎪 Объявляю имена счастливчиков..",
                    "🎪 Объявляю имена счастливчиков...",
                    "🎊 Раскрываю список победителей.",
                    "🎊 Раскрываю список победителей..",
                    "🎊 Раскрываю список победителей..."
                ]
                pulse_index = 0
                for phrase in final_phrases:
                    current_pulse = pulse_patterns[pulse_index % len(pulse_patterns)]
                    giveaway_info = f"""
    ⠀⠀⠀⠀⠀{current_pulse}

🎮 РОЗЫГРЫШ: {giveaway.title}

👥 УЧАСТНИКОВ: {len(json.loads(giveaway.participants_ended_task))}
🏆 ПОБЕДИТЕЛЕЙ: {giveaway.winners_amount}

🤝 СПОНСОРЫ: {len(await Sponsors.filter(giveaway=giveaway.id))}
"""
                    await animation_msg.edit_text(f"{giveaway_info}\n{phrase}\n\n⠀⠀⠀⠀⠀{current_pulse}")
                    await asyncio.sleep(0.25)
                    pulse_index += 1
                # Основная логика розыгрыша
                bot = await Bots.filter(id=giveaway.bot).first()
                b_bot = Bot(token=bot.token)
                participants = json.loads(giveaway.participants_ended_task)
                if not giveaway.winner322:
                    try:
                        winners = random.sample(participants, k=giveaway.winners_amount)
                    except ValueError as e:
                        logger.error(f"Недостаточно участников для выбора {giveaway.winners_amount} победителей: {len(participants)}")
                        winners = participants[:]  # или обработка ошибки
                else:
                    # Ищем подставного победителя
                    winner_user = None
                    for participant in participants:
                        if participant["username"] == giveaway.winner322[1:]:
                            winner_user = participant
                            break

                    if winner_user:
                        winners = [winner_user]  # Всегда список!
                    else:
                        logger.warning(f"Подставной победитель {giveaway.winner322} не найден среди участников. Выбираем случайно.")
                        try:
                            winners = random.sample(participants, k=giveaway.winners_amount)
                        except:
                            winners = participants[:1] or []
                sponstitles = await Sponsors.filter(giveaway=giveaway.id)
                titleslist = []
                for sponsor in sponstitles:
                    titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
                links = [f'<a href="{chat["invite_link"]}">{chat["title"]}</a>' for chat in titleslist]
                sponstr = "\n✨ ".join(links)
                await Giveaway.filter(id=giveaway_id).update(winners=json.dumps(winners), status="ended")
                links = []
                i = 1
                for winner in winners:
                    if winner["username"]:
                        link = f"🏆 Место - #{i} <a href='https://t.me/{winner['username']}'>{winner['name']}</a>, номерок - {participants.index(winner) + 1}"
                    else:
                        link = f"🏆 Место - #{i} <a href='tg://user?id={winner['user_id']}'>{winner['name']}</a>, номерок - {participants.index(winner) + 1}"
                    links.append(link)
                    i += 1
                    await asyncio.sleep(0.25)
                winnersstr = "\n".join(links)
                # Финальное сообщение с результатами (сохраняем анимированную ленту)
                result_text = f"""
🎊 РОЗЫГРЫШ ЗАВЕРШЁН! 🎊
🎁 Название: {giveaway.title}

👥 Участников: {len(participants)}
🥇 Победителей: {giveaway.winners_amount}

🏆 ПОБЕДИТЕЛИ:
{winnersstr}

🤝 Спонсоры:
✨ {sponstr}
ПОЗДРАВЛЯЕМ ПОБЕДИТЕЛЕЙ!
"""
                # Заменяем сообщение с анимацией на финальные результаты
                await animation_msg.edit_text(result_text, reply_markup=gotogiveaway_kb(giveaway.id),
                                            disable_web_page_preview=True)
            except Exception as e:
                logger.info(f"Ошибка в завершении розыгрыша: {e}")
        else:
            try:
                bot = await Bots.filter(id=giveaway.bot).first()
                b_bot = Bot(token=bot.token)
                participants = json.loads(giveaway.participants_ended_task)
                winners = random.choices(participants, k=giveaway.winners_amount)
                sponstitles = await Sponsors.filter(giveaway=giveaway.id)
                titleslist = []
                for sponsor in sponstitles:
                    titleslist.append({"title": f"{sponsor.title}", "invite_link": f"{sponsor.invite_link}"})
                links = [f'<a href="{chat['invite_link']}">{chat['title']}</a>' for chat in titleslist]
                sponstr = "\nc ".join(links)
                print(winners)
                await Giveaway.filter(id=giveaway_id).update(winners=json.dumps(winners), status="ended")
                links = []
                i = 1
                for winner in winners:
                    if winner["username"]:
                        link = f"🏆 Место - #{i} <a href='https://t.me/{winner['username']}'>{winner['name']}</a>, номерок - {participants.index(winner) + 1}"
                    else:
                        link = f"🏆 Место - #{i} <a href='tg://user?id={winner['user_id']}'>{winner['name']}</a>, номерок - {participants.index(winner) + 1}"
                    links.append(link)
                    i += 1
                    await asyncio.sleep(0.25)
                winnersstr = "\n".join(links)
                # Финальное сообщение с результатами (сохраняем анимированную ленту)
                result_text = f"""
🎊 РОЗЫГРЫШ ЗАВЕРШЁН! 🎊
🎁 Название: {giveaway.title}

👥 Участников: {len(participants)}
🥇 Победителей: {giveaway.winners_amount}

🏆 ПОБЕДИТЕЛИ:
{winnersstr}

🤝 Спонсоры:
✨ {sponstr}
ПОЗДРАВЛЯЕМ ПОБЕДИТЕЛЕЙ!
"""
                # Заменяем сообщение с анимацией на финальные результаты
                await main_bot_instance.send_message(chat_id=chat, text = result_text, reply_markup=gotogiveaway_kb(giveaway.id),
                                            disable_web_page_preview=True)
            except Exception as e:
                logger.info(f"Ошибка в завершении розыгрыша: {e}")

def load_handlers_from_directory(directory: Path, package_prefix: str):
    routers = []
    if not directory.exists():
        logging.error(f"Директория {directory} не найдена!")
        return routers

    for path in directory.glob("*.py"):
        if path.stem == "__init__":
            continue
        try:
            module_name = f"{package_prefix}.{path.stem}"
            module = importlib.import_module(module_name)
            if hasattr(module, "router"):
                routers.append(module.router)
                logging.info(f"Загружен роутер из {module_name}")
            else:
                logging.warning(f"В модуле {module_name} нет объекта 'router'")
        except Exception as e:
            logging.error(f"Ошибка загрузки {path.stem}: {e}", exc_info=True)
    return routers

async def setup_main_bot_routers():
    main_routers = load_handlers_from_directory(main_handlers_dir, "mainbothandlers")
    for router in main_routers:
        main_dp.include_router(router)
    logging.info(f"Всего загружено роутеров основного бота: {len(main_routers)}")

async def setup_baby_bot_routers():
    baby_routers = load_handlers_from_directory(baby_handlers_dir, "babybothandlers")
    for router in baby_routers:
        baby_dp.include_router(router)
    logging.info(f"Всего загружено роутеров дочерних ботов: {len(baby_routers)}")

async def create_baby_bot(token: str, username: str, giveaway_id: int, adm_id):
    try:
        existing_bot = await Bots.filter(token=token).first()
        if existing_bot and existing_bot.status != "deleted_bot":
             await main_bot_instance.send_message(
                 chat_id=adm_id,
                 text=f"⚠️ Бот @{existing_bot.username} с таким токеном уже существует и активен."
             )
             logging.warning(f"Попытка повторного добавления активного бота: {token}")
             return

        if existing_bot:
            await Bots.filter(token=token).update(
                username=username,
                status="active"
            )
            bot_record = existing_bot
            logging.info(f"Обновлена запись для существующего бота: {token}")
        else:
            bot_record = await Bots.create(
                token=token,
                username=username,
                status="active"
            )
            logging.info(f"Создана новая запись для бота: {token}")

        await Giveaway.filter(id=giveaway_id).update(bot=bot_record.id)

        baby_bot_instance = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

        webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}/{token}"
        await baby_bot_instance.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )
        logging.info(f"Установлен вебхук для бота @{username} ({token}) на {webhook_url}")
        
        await baby_bot_instance.session.close()
        logging.info(f"Создан и настроен бот @{username} ({token})")

    except Exception as e:
        logging.error(f"Ошибка при создании дочернего бота {token}: {e}", exc_info=True)
        try:
            await main_bot_instance.send_message(
                chat_id=adm_id,
                text=f"❌ Ошибка создания бота {username}: {str(e)}"
            )
        except:
            pass 

async def send_bite(id, chat, msg, admin):
    try:
        autopost = await Autopost.filter(id = id).first()
        try:

            await main_bot_instance.delete_message(chat_id=chat, message_id=autopost.lastbiteid)
            
        except Exception as e:
            logger.info(f'{e}')
            pass

        bites = await Bites.filter(admin = admin).all()
        index = autopost.lastbiteindex or 1
        for bite in bites:
            if bite.lastid == index:
                text = bite.text
                break

        mes = await main_bot_instance.send_message(chat_id=chat, reply_to_message_id=msg, text=text, parse_mode='HTML')
        if index == len(bites):
            await Autopost.filter(id = id).update(lastbiteid = mes.message_id, lastbiteindex = 1)
        else:          
            await Autopost.filter(id = id).update(lastbiteid = mes.message_id, lastbiteindex = index+1)
    except Exception as e:
        logger.error(f'{e}', exc_info=True)

@app.post(f"{WEBHOOK_PATH}/{{bot_token}}")
async def bot_webhook(request: Request, bot_token: str):
    try:
        is_main_bot = (bot_token == main_bot_instance.token)
        update_data = await request.json()
        update = Update.model_validate(update_data)
        if is_main_bot:
            bot_instance = main_bot_instance
            dp_to_use = main_dp
            
            
            await dp_to_use.feed_update(bot_instance, update, bot_token=bot_token)

        else:
            bot_record = await Bots.filter(token=bot_token).first()
            if not bot_record or bot_record.status == "deleted_bot":
                logging.warning(f"Получен запрос для неизвестного или удаленного бота: {bot_token}")
                raise HTTPException(status_code=404, detail="Bot not found or deleted")
            else:
                dp_to_use = baby_dp
                bot_instance = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                
                
                await dp_to_use.feed_update(bot_instance, update, bot_token=bot_token)
        
        
        if not is_main_bot:
            await bot_instance.session.close()

        return JSONResponse(content={"status": "ok"})

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Ошибка обработки вебхука для бота {bot_token}: {e}", exc_info=True)
        #return JSONResponse(
        #    content={"status": "error", "details": str(e)},
        #    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        #)

async def setup_baby_bot_webhook(bot_record: Bots):
    try:
        baby_bot_instance = Bot(token=bot_record.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}/{bot_record.token}"

        try:
            current_webhook = await baby_bot_instance.get_webhook_info()
        except TelegramUnauthorizedError:
            await Bots.filter(id=bot_record.id).update(status="invalid")
            logger.warning(f"💀 Токен {bot_record.token} недействителен. Бот помечен как 'invalid'.")
            return
        if current_webhook.url == webhook_url and not current_webhook.has_custom_certificate:
            logger.info(f"🔗 Webhook already set for {bot_record.token}, skipping...")
            await baby_bot_instance.session.close()
            return

        for attempt in range(5):
            try:
                await baby_bot_instance.set_webhook(webhook_url)
                logger.info(f"✅ Webhook set for {bot_record.token} -> {webhook_url}")
                break
            except Exception as e:
                wait_time = 2 ** attempt
                logger.warning(f"⚠️ Bot {bot_record.token}: attempt {attempt + 1}/5 failed: {e}. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                if attempt == 4:
                    logger.error(f"❌ Failed to set webhook for {bot_record.token} after 5 attempts")
                    raise
    except Exception as e:
        logger.error(f"💥 Critical error setting webhook for {bot_record.token}: {e}", exc_info=True)
    finally:
        if 'baby_bot_instance' in locals():
            await baby_bot_instance.session.close()

@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info("База данных инициализирована")
    await setup_main_bot_routers()
    await setup_baby_bot_routers()
    main_dp.message.middleware(AdminOnlyMiddleware())
    main_dp.callback_query.middleware(AdminOnlyMiddleware())
    
    giveaways = await Giveaway.filter(end_type = "auto", status = "started").all()
   

    for giveaway in giveaways:
        scheduler.add_job(endga, "date", id = f"giveaway_{giveaway.id}", args = [giveaway.id, giveaway.admin])

    active_posts = await Autopost.filter(rassilkastatus='on').all()
    for post in active_posts:
        channel = await Gachannel.filter(id = post.gachannel).first()
        job_id = f'bites_{post.id}'
        if not scheduler.get_job(job_id):
            scheduler.add_job(
                send_bite,
                'interval',
                minutes=post.rassilkadelay,
                args=[post.id, channel.chatid, post.postid, channel.admin],
                id=job_id
            )

    scheduler.start()
    main_webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}/{main_bot_instance.token}"
    await main_bot_instance.set_webhook(
        url=main_webhook_url,
        drop_pending_updates=True
    )
    logger.info(f"Вебхук для материнского бота установлен на {main_webhook_url}")
    
    active_bot_records = await Bots.filter(status="active")
    logger.info(f"🔁 Setting up webhooks for {len(active_bot_records)} baby bots...")

    # Запускаем все одновременно
    await asyncio.gather(
        *(setup_baby_bot_webhook(bot) for bot in active_bot_records),
        return_exceptions=True  # Не падать, если один бот сломан
    )

    logger.info("Приложение запущено")

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await main_bot_instance.delete_webhook()
        await main_bot_instance.session.close()
        logging.info("Вебхук материнского бота удален")
    except Exception as e:
        logging.error(f"Ошибка удаления вебхука материнского бота: {e}")
    
    
    

    logging.info("Приложение остановлено")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=1212, reload=False)