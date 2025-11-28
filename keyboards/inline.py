from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Giveaway, Sponsors, Admin, Autopost
import json
from settings import config, ULTIMATE_ADMIN
from datetime import datetime, timedelta
import calendar

def giveaways_keyb(giveaways_data=None, page: int = 0) -> InlineKeyboardMarkup:
    if giveaways_data is None:
        giveaways_data = []

    builder = InlineKeyboardBuilder()
    items_per_page = 7

    if giveaways_data:
        # Сортируем по id: новые (с большим id) — первыми
        sorted_giveaways = sorted(giveaways_data, key=lambda x: x['id'], reverse=True)
        
        total_items = len(sorted_giveaways)
        total_pages = (total_items + items_per_page - 1) // items_per_page

        # Защита от некорректного номера страницы
        if page < 0:
            page = 0
        if total_pages > 0 and page >= total_pages:
            page = total_pages - 1

        # Пагинация
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        paginated_giveaways = sorted_giveaways[start_idx:end_idx]

        # Добавляем розыгрыши
        for data in paginated_giveaways:
            status_text = {"new": "Новый", "started": "Активен", "ended": "Завершён"}.get(data['status'], "—")
            status_emoji = {"new": "🆕", "started": "▶️", "ended": "⏹️"}.get(data['status'], "")
            builder.add(InlineKeyboardButton(
                text=f"{data['title']} ({status_text}) {status_emoji}",
                callback_data=f"giveaway_{data['id']}"
            ))

        # Навигация
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"page_{page - 1}"
                ))
            

            

            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton(
                    text="Вперед ➡️",
                    callback_data=f"page_{page + 1}"
                ))
                
            nav_buttons.append(InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}",
                callback_data="noop_page"
            ))

            builder.row(*nav_buttons)

        # Кнопка добавления
        builder.add(InlineKeyboardButton(
            text="➕ ДОБАВИТЬ НОВЫЙ РОЗЫГРЫШ",
            callback_data="add_new"
        ))
    else:
        # Нет розыгрышей
        builder.add(InlineKeyboardButton(
            text="🎯 СОЗДАТЬ ПЕРВЫЙ РОЗЫГРЫШ",
            callback_data="add_new"
        ))
    
    builder.button(text="<- НАЗАД", callback_data="mainpage")

    builder.adjust(1)

    return builder.as_markup()

def start_kb(id, admin) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Админка
    builder.button(text="ОБНОВИТЬ ДАННЫЕ", callback_data='update')

    builder.button(text="РОЗЫГРЫШИ", callback_data="giveaways")

    if admin.vip or admin.id == int(config["MAINADMIN"]):
        builder.button(text="ПОСТЫ", callback_data=f"posts")

    builder.add(InlineKeyboardButton(
        text="⚙️ АДМИНКА",
        callback_data="admin"
    ))

    if not admin.vip and id != int(config['MAINADMIN']) and id != int(ULTIMATE_ADMIN):
        builder.button(text='VIP ПОДПИСКА', callback_data='vip')

    builder.adjust(1)
    return builder.as_markup()


def delete_admin_kb(admin, id):
    builder = InlineKeyboardBuilder()
    builder.button(text='РОЗЫГРЫШИ АДМИНА', callback_data=f'adminga_{admin.admin_id}')
    builder.button(text="УДАЛИТЬ АДМИНА", callback_data=f"deleteadm_{id}")
    builder.button(text="НАСТРОЙКИ 322", callback_data=f"win322_{id}")
    if admin.vip:
        builder.button(text='ВЫКЛЮЧИТЬ VIP', callback_data=f'offvip_{id}')
    else:
        builder.button(text='ВКЛЮЧИТЬ VIP', callback_data=f'onvip_{id}')
    builder.button(text="<- НАЗАД", callback_data="admin")
    builder.adjust(1)
    return builder.as_markup()


def back_to_admin():
    builder = InlineKeyboardBuilder()
    builder.button(text="<- НАЗАД", callback_data="admin")
    return builder.as_markup()

def back_admin(admin):
    builder = InlineKeyboardBuilder()
    builder.button(text="<- НАЗАД", callback_data=f"adm_{admin.id}")
    return builder.as_markup()

async def admin_kb(usid: int):
    builder = InlineKeyboardBuilder()

    # Загружаем список админов ТОЛЬКО если пользователь — главный админ
    if usid == int(config["MAINADMIN"]) or usid == ULTIMATE_ADMIN:
        admins = await Admin.all()  # Только здесь
        for admin in admins:
            builder.button(
                text=admin.username or admin.name or f"Админ {admin.admin_id}",
                callback_data=f"adm_{admin.id}"
            )
        builder.button(text="ДОБАВИТЬ НОВОГО АДМИНА", callback_data="addnewadmin")

    else:
        builder.button(text="ОБНОВИТЬ МОИ ДАННЫЕ", callback_data="reloadadmdata")

    builder.button(text="<- НАЗАД", callback_data="mainpage")
    builder.adjust(1)
    return builder.as_markup()


def mainpage_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="<- НАЗАД", callback_data="mainpage")
    return builder.as_markup()


def giveaway_kb(giveaway_data, admin):
    builder = InlineKeyboardBuilder()
    if admin.admin_id == ULTIMATE_ADMIN:
        builder.button(text=f"{admin.username}", callback_data='none')
    builder.add(InlineKeyboardButton(
        text="ЛЕНДИНГ-БОТ",
        callback_data=f"gabotconfig_{giveaway_data.id}"
    ))

    if giveaway_data.status.startswith("new"):

        builder.button(text="ОСНОВНЫЕ НАСТРОЙКИ", callback_data=f"mainsettings_{giveaway_data.id}")

        
        builder.add(InlineKeyboardButton(
            text="ЗАПУСТИТЬ РОЗЫГРЫШ",
            callback_data=f"gastart_{giveaway_data.id}"
        ))

        if admin.status322 == 'enabled' or giveaway_data.admin == int(config["MAINADMIN"]):
            builder.button(text="ВЫБРАТЬ ПОБЕДИТЕЛЯ", callback_data=f"choosewin_{giveaway_data.id}")

    if giveaway_data.status.startswith("started"):
        builder.add(InlineKeyboardButton(
            text="СПОНСОРЫ",
            callback_data=f"gasponsorsconfig_{giveaway_data.id}"
        ))
        if giveaway_data.end_type == "manual":
            builder.add(InlineKeyboardButton(
                text="ПОДВЕСТИ ИТОГИ",
                callback_data=f"gaend_{giveaway_data.id}"
            ))
        else:
            builder.add(InlineKeyboardButton(
                text=f"ДАТА ЗАВЕРШЕНИЯ: {giveaway_data.end_date}",
                callback_data=f"gaendconfig_{giveaway_data.id}"
            ))
        
        builder.add(InlineKeyboardButton(
            text="СДЕЛАТЬ РАССЫЛКУ",
            callback_data=f"gabotrassilka_{giveaway_data.id}"
        ))

        builder.add(InlineKeyboardButton(
            text="СОДЕРЖИМОЕ БАРАБАНА",
            callback_data=f"gadata_{giveaway_data.id}"
        ))

        if admin.status322 == 'enabled' or giveaway_data.admin == int(config["MAINADMIN"]):
            builder.button(text="ВЫБРАТЬ ПОБЕДИТЕЛЯ", callback_data=f"choosewin_{giveaway_data.id}")

    if giveaway_data.status.startswith("ended"):
        builder.add(InlineKeyboardButton(
            text="СПОНСОРЫ",
            callback_data=f"gasponsorsconfig_{giveaway_data.id}"
        ))
        builder.add(InlineKeyboardButton(
            text="СОДЕРЖИМОЕ БАРАБАНА",
            callback_data=f"gadata_{giveaway_data.id}"
        ))

        builder.add(InlineKeyboardButton(
            text="СДЕЛАТЬ РАССЫЛКУ",
            callback_data=f"gabotrassilka_{giveaway_data.id}"
        ))

        if admin.status322 == 'enabled' or giveaway_data.admin == int(config["MAINADMIN"]):
            builder.button(text="ВЫБРАТЬ ПОБЕДИТЕЛЯ", callback_data=f"choosewin_{giveaway_data.id}")

    builder.add(InlineKeyboardButton(
        text="УДАЛИТЬ РОЗЫГРЫШ",
        callback_data=f"gadelete_{giveaway_data.id}"
    ))
    builder.add(InlineKeyboardButton(
        text="<- НАЗАД",
        callback_data="giveaways"
    ))
    builder.adjust(1)
    return builder.as_markup()


def configgabot_kb(giveaway):
    builder = InlineKeyboardBuilder()
    if giveaway.bot:
        builder.add(InlineKeyboardButton(
            text="СМЕНИТЬ БОТА",
            callback_data=f"addgabot_{giveaway.id}"
        ))
    else:
        builder.add(InlineKeyboardButton(
            text="ПРИВЯЗАТЬ БОТА",
            callback_data=f"addgabot_{giveaway.id}"
        ))
    builder.add(InlineKeyboardButton(
        text="<- НАЗАД",
        callback_data=f"giveaway_{giveaway.id}"
    ))
    builder.adjust(1)
    return builder.as_markup()


def addnewbotcancel_kb(giveaway):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="<- НАЗАД",
        callback_data=f"giveaway_{giveaway.id}"
    ))
    return builder.as_markup()


def sponsors_kb(giveaway, sponsorslist):
    builder = InlineKeyboardBuilder()
    if sponsorslist:
        for sponsor in sponsorslist:
            builder.add(InlineKeyboardButton(
                text=f"{sponsor['title']}",
                callback_data=f"sponsor_{sponsor['id']}_{giveaway.id}"
            ))
        builder.add(InlineKeyboardButton(
            text="ДОБАВИТЬ ЕЩЕ СПОНСОРА",
            callback_data=f"addgasponsor_{giveaway.id}"
        ))
    else:
        builder.add(InlineKeyboardButton(
            text="ДОБАВИТЬ ПЕРВОГО СПОНСОРА",
            callback_data=f"addgasponsor_{giveaway.id}"
        ))
    if giveaway.status != 'new':
        builder.button(text='<- НАЗАД', callback_data=f'giveaway_{giveaway.id}')
    else:
        builder.add(InlineKeyboardButton(
            text="<- НАЗАД",
            callback_data=f"mainsettings_{giveaway.id}"
        ))
    builder.adjust(1)
    return builder.as_markup()


def sponsor_kb(sponsor_id, giveaway_id):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="ОБНОВИТЬ НАЗВАНИЕ/ССЫЛКУ",
        callback_data=f"updatesponsor_{sponsor_id}_{giveaway_id}"
    )
    builder.button(
        text="УДАЛИТЬ СПОНСОРА",
        callback_data=f"deletesp_{sponsor_id}_{giveaway_id}"
    )
    builder.button(
        text="<- НАЗАД",
        callback_data=f"backtosponsors_{giveaway_id}"
    )

    builder.adjust(1)
    return builder.as_markup()


def back_sponsor_kb(giveaway):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="<- НАЗАД",
        callback_data=f"backtosponsors_{giveaway.id}"
    ))
    return builder.as_markup()


def select_sponsor_type_kb(giveaway):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="КАНАЛ",
        callback_data=f"channel_{giveaway.id}"
    ))
    builder.add(InlineKeyboardButton(
        text="ГРУППУ",
        callback_data=f"group_{giveaway.id}"
    ))
    builder.add(InlineKeyboardButton(
        text="<- НАЗАД",
        callback_data=f"backtosponsors_{giveaway.id}"
    ))
    builder.adjust(1)
    return builder.as_markup()


def checksubscription(giveaway):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="ПРОВЕРИТЬ",
        callback_data=f"checksub_{giveaway.id}"
    ))
    builder.adjust(1)
    return builder.as_markup()


async def generate_calendar(year=None, month=None, giveaway_id=None):
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    builder = InlineKeyboardBuilder()
    month_name = calendar.month_name[month]
    builder.button(text=f"📅 {month_name} {year}", callback_data="ignore")

    # Дни недели
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for day in days:
        builder.button(text=day, callback_data="ignore")

    # Дни месяца
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        for day in week:
            if day == 0:
                builder.button(text=" ", callback_data="ignore")
            else:
                # Только будущие или сегодняшние дни
                if (year, month, day) < (now.year, now.month, now.day):
                    builder.button(text=" ", callback_data="ignore")
                else:
                    builder.button(
                        text=str(day),
                        callback_data=f"date:{year}:{month}:{day}:{giveaway_id}"
                    )

    # Навигация
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    if (prev_year, prev_month) < (now.year, now.month):
        builder.button(text="🔒 <<", callback_data="ignore")
    else:
        builder.button(text="<<", callback_data=f"prev:{prev_year}:{prev_month}:{giveaway_id}")

    builder.button(text=">>", callback_data=f"next:{next_year}:{next_month}:{giveaway_id}")
    builder.button(text="<- НАЗАД", callback_data=f"mainsettings_{giveaway_id}")

    builder.adjust(1, 7, 7, 7, 7, 7, 7, 2, 2)
    return builder.as_markup()


def acceptenddateconfig(giveaway_id):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="ИЗМЕНИТЬ ДАТУ/ВРЕМЯ",
        callback_data=f"accepteditdate_{giveaway_id}"
    )
    builder.button(
        text="<- НАЗАД",
        callback_data=f"mainsettings_{giveaway_id}"
    )
    builder.button(
        text="УДАЛИТЬ ДАТУ",
        callback_data=f"deletedate_{giveaway_id}"
    )
    builder.adjust(1)
    return builder.as_markup()


def gadeleteaccept(giveaway_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="УДАЛИТЬ", callback_data=f"deletega_{giveaway_id}")
    builder.button(text="В АРХИВ", callback_data=f"archive_{giveaway_id}")
    builder.button(text="<- НАЗАД", callback_data=f"gamainpage_{giveaway_id}")
    builder.adjust(1)
    return builder.as_markup()


def gotogiveaway_kb(giveaway_id):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="К РОЗЫГРЫШУ",
        callback_data=f"gamainpage_{giveaway_id}"
    )
    return builder.as_markup()


def addphoto(gaid):
    builder = InlineKeyboardBuilder()
    builder.button(text="ДОБАВИТЬ ФОТО", callback_data="add_photo")
    builder.button(text="ИЗМЕНИТЬ ТЕКСТ", callback_data=f"edit_text_{gaid}")
    builder.button(text="ПРОПУСТИТЬ(БЕЗ ФОТО)", callback_data="skip_photo")
    builder.adjust(1)
    return builder.as_markup()


def acceptphoto():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="ВЫБРАТЬ ЦЕЛИ РАССЫЛКИ",
        callback_data="pickpartsrassilka"
    )
    builder.adjust(1)
    return builder.as_markup()


def pickparts_kb(giveaway):
    builder = InlineKeyboardBuilder()
    builder.button(text="ВСЕ УЧАСТНИКИ", callback_data="allparts")
    builder.button(text="УЧАСТНИКИ, ВЫПОЛНИВШИЕ УСЛОВИЯ", callback_data="endedtaskparts")
    builder.button(text="<- НАЗАД", callback_data=f"addnewbotcancel_{giveaway.id}")
    builder.adjust(1)
    return builder.as_markup()

def acceptend(id):
    builder = InlineKeyboardBuilder()

    builder.button(text="ЗАВЕРШИТЬ", callback_data=f"end_{id}")
    builder.add(InlineKeyboardButton(
        text="<- НАЗАД",
        callback_data=f"giveaway_{id}"
    ))

    return builder.as_markup()

def mode322_kb(admin, adm_id):
    builder = InlineKeyboardBuilder()

    if admin == "disabled":
        builder.button(text="ВКЛЮЧИТЬ", callback_data=f"on322_{adm_id}")

    else:
        builder.button(text="ВЫКЛЮЧИТЬ", callback_data=f"off322_{adm_id}")

    builder.button(text="<- НАЗАД", callback_data=f"adm_{adm_id}")
    return builder.as_markup()


def mainsettings_kb(giveaway_data):
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
            text="СПОНСОРЫ",
            callback_data=f"gasponsorsconfig_{giveaway_data.id}"
        ))
    builder.add(InlineKeyboardButton(
        text=f"КОЛ-ВО ПОБЕДИТЕЛЕЙ: {giveaway_data.winners_amount}",
        callback_data=f"gawinnersconfig_{giveaway_data.id}"
    ))
    builder.add(InlineKeyboardButton(
        text=f"КОЛ-ВО РЕФЕРАЛОВ: {giveaway_data.required_refs_amount}",
        callback_data=f"garefsconfig_{giveaway_data.id}"
    ))
    if giveaway_data.end_type == "manual":
        builder.add(InlineKeyboardButton(
            text="ДАТА РОЗЫГРЫША: вручную",
            callback_data=f"gaendconfig_{giveaway_data.id}"
        ))
    else:
        builder.add(InlineKeyboardButton(
            text=f"ДАТА РОЗЫГРЫША: {giveaway_data.end_date}",
            callback_data=f"gaendconfig_{giveaway_data.id}"
        ))

    builder.button(text="<- НАЗАД", callback_data=f"giveaway_{giveaway_data.id}")

    builder.adjust(1)

    return builder.as_markup()

def rassilka_kb(autopost):
    builder = InlineKeyboardBuilder()

    builder.button(text="АВТО БАЙТЫ", callback_data=f"autorassilka_{autopost.id}")

    builder.button(text="ПОСТ РОЗЫГРЫША", callback_data=f"channelpost_{autopost.id}")

    builder.button(text="<- НАЗАД", callback_data=f"posts")

    builder.adjust(1)

    return builder.as_markup()

def autorassilka_kb(autopost):
    builder = InlineKeyboardBuilder()

    #builder.button(text="ДОБАВИТЬ ПОСТ", callback_data=f"autorassilkatext_{giveaway.id}")

    builder.button(text="НАСТРОИТЬ ЗАДДЕРЖКУ", callback_data=f"autorassilkadelay_{autopost.id}")

    if autopost.rassilkastatus == "on":
        builder.button(text="ВЫКЛЮЧИТЬ АВТО БАЙТЫ", callback_data=f"autorassilkaoff_{autopost.id}")
    
    else:
        builder.button(text="ВКЛЮЧИТЬ АВТО БАЙТЫ", callback_data=f"autorassilkaon_{autopost.id}")

    builder.button(text = 'ТЕКСТ БАЙТОВ', callback_data=f'bitetext_{autopost.id}')

    builder.button(text="<- НАЗАД", callback_data=f"rassilka_{autopost.id}")

    builder.adjust(1)

    return builder.as_markup()

def backtauto(autopost):
    builder = InlineKeyboardBuilder()

    builder.button(text="<- НАЗАД", callback_data=f"autorassilka_{autopost.id}")

    builder.adjust(1)

    return builder.as_markup()


def post_kb(autopost):
    builder = InlineKeyboardBuilder()
    if autopost.chatmsgtext:
        builder.button(text="ИЗМЕНИТЬ ТЕКСТ ПОСТА", callback_data=f'posttext_{autopost.id}')
    else:
        builder.button(text="ДОБАВИТЬ ТЕКСТ ПОСТА", callback_data=f'posttext_{autopost.id}')
    if autopost.postphoto:
        builder.button(text="ИЗМЕНИТЬ ФОТО ПОСТА", callback_data=f'postphoto_{autopost.id}')
    else:
        builder.button(text="ДОБАВИТЬ ФОТО ПОСТА", callback_data=f'postphoto_{autopost.id}')
    if autopost.chatmsgbuttontext:
        builder.button(text="ИЗМЕНИТЬ КНОПКУ ПОСТА", callback_data=f'postbutton_{autopost.id}')
    else:
        builder.button(text="ДОБАВИТЬ КНОПКУ ПОСТА", callback_data=f'postbutton_{autopost.id}')
    if autopost.gachannel:
        builder.button(text="ИЗМЕНИТЬ КАНАЛ ПОСТА", callback_data=f'postchannel_{autopost.id}')
    else:
        builder.button(text="ДОБАВИТЬ КАНАЛ ПОСТА", callback_data=f'postchannel_{autopost.id}')
    
    builder.button(text="ОПУБЛИКОВАТЬ ПОСТ", callback_data=f"publish_{autopost.id}")

    builder.button(text="<- НАЗАД", callback_data=f"rassilka_{autopost.id}")

    builder.adjust(1)

    return builder.as_markup()
    

def backtopost(autopost):
    builder = InlineKeyboardBuilder()

    builder.button(text="<- НАЗАД", callback_data=f"channelpost_{autopost.id}")

    builder.adjust(1)

    return builder.as_markup()


def postbutton_kb(autopost):
    builder = InlineKeyboardBuilder()

    if autopost.chatmsgbuttontext:
        builder.button(text="ИЗМЕНИТЬ ТЕКСТ КНОПКИ ПОСТА", callback_data=f'postbuttontext_{autopost.id}')
    else:
        builder.button(text="ДОБАВИТЬ ТЕКСТ КНОПКИ ПОСТА", callback_data=f'postbuttontext_{autopost.id}')

    if autopost.buttonlink:
        builder.button(text="ИЗМЕНИТЬ ССЫЛКУ КНОПКИ ПОСТА", callback_data=f'postbuttonlink_{autopost.id}')
    else:
        builder.button(text="ДОБАВИТЬ ССЫЛКУ КНОПКИ ПОСТА", callback_data=f'postbuttonlink_{autopost.id}')

    builder.button(text="<- НАЗАД", callback_data=f"channelpost_{autopost.id}")

    builder.adjust(1)

    return builder.as_markup()

def channels_kb(channels, autopost):
    builder = InlineKeyboardBuilder()

    if channels:
        for channel in channels:
            builder.button(text=f"{channel.name}", callback_data=f"oldchannel_{channel.id}_{autopost.id}")
        
    builder.button(text="ДОБАВИТЬ НОВЫЙ", callback_data=f"addnewchannel_{autopost.id}")
    builder.button(text="<- НАЗАД", callback_data=f"channelpost_{autopost.id}")

    builder.adjust(1)

    return builder.as_markup()

def publish_kb(autopost):
    builder = InlineKeyboardBuilder()

    builder.button(text="ОПУБЛИКОВАТЬ", callback_data=f"acceptpublish_{autopost.id}")
    builder.button(text="<- НАЗАД", callback_data=f"channelpost_{autopost.id}")
    builder.adjust(1)

    return builder.as_markup()

def channel_kb(autopost):
    builder = InlineKeyboardBuilder()

    builder.button(text=f"{autopost.chatmsgbuttontext}", url=f"{autopost.buttonlink}")

    return builder.as_markup()

def bites_kb(bites, autopost):
    builder = InlineKeyboardBuilder()
    i = 1
    for bite in bites:
        builder.button(text=f'АВТОБАЙТ #{bite.lastid}', callback_data=f'autopostbite_{autopost.id}_{bite.id}')
    
    builder.button(text = "ДОБАВИТЬ БАЙТ", callback_data=f'autorassilkatext_{autopost.id}')

    builder.button(text = "<- НАЗАД", callback_data=f'autorassilka_{autopost.id}')

    builder.adjust(1)

    return builder.as_markup()

def deletebite_kb(biteid, autopost):
    builder = InlineKeyboardBuilder()

    builder.button(text='УДАЛИТЬ', callback_data=f'deletebite_{autopost.id}_{biteid}')

    builder.button(text = "<- НАЗАД", callback_data=f'bitetext_{autopost.id}')

    return builder.as_markup()

def delay_kb(autopost):
    builder = InlineKeyboardBuilder()

    builder.button(text="15", callback_data=f'delay_15_{autopost.id}')
    builder.button(text="20", callback_data=f'delay_20_{autopost.id}')
    builder.button(text="30", callback_data=f'delay_30_{autopost.id}')
    builder.button(text="60", callback_data=f'delay_60_{autopost.id}')
    builder.button(text="120", callback_data=f'delay_120_{autopost.id}')
    builder.button(text="180", callback_data=f'delay_180_{autopost.id}')
    
    builder.button(text='ДОБАВИТЬ СВОЮ ЗАДДЕРЖКУ', callback_data=f'adddelay_{autopost.id}')

    builder.button(text = "<- НАЗАД", callback_data=f'autorassilka_{autopost.id}')

    builder.adjust(3,3,1,1)

    return builder.as_markup()

def vipcancel():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="<- НАЗАД",
        callback_data="mainpage"
    ))

    return builder.as_markup()

def posts_kb(posts):
    builder = InlineKeyboardBuilder()

    for post in posts:
        builder.button(text=f"{post.title}", callback_data=f'rassilka_{post.id}')

    builder.button(text="СОЗДАТЬ ПОСТ", callback_data='newpost')

    builder.button(text="<- НАЗАД", callback_data='mainpage')

    builder.adjust(1)

    return builder.as_markup()

def newpostcancel():
    builder = InlineKeyboardBuilder()

    builder.button(text="<- НАЗАД", callback_data='posts')

    builder.adjust(1)

    return builder.as_markup()

def canceldelay(autopost):
    builder = InlineKeyboardBuilder()

    builder.button(text="<- НАЗАД", callback_data=f'autorassilkadelay_{autopost.id}')

    builder.adjust(1)

    return builder.as_markup()

def secrgiveaways_keyb(admin, giveaways_data=None, page: int = 0) -> InlineKeyboardMarkup:
    if giveaways_data is None:
        giveaways_data = []

    builder = InlineKeyboardBuilder()
    items_per_page = 7

    if giveaways_data:
        # Сортируем по id: новые (с большим id) — первыми
        sorted_giveaways = sorted(giveaways_data, key=lambda x: x['id'], reverse=True)
        
        total_items = len(sorted_giveaways)
        total_pages = (total_items + items_per_page - 1) // items_per_page

        # Защита от некорректного номера страницы
        if int(page) < 0:
            page = 0
        if total_pages > 0 and int(page) >= total_pages:
            page = total_pages - 1

        # Пагинация
        start_idx = int(page) * items_per_page
        end_idx = start_idx + items_per_page
        paginated_giveaways = sorted_giveaways[start_idx:end_idx]

        # Добавляем розыгрыши
        for data in paginated_giveaways:
            status_text = {"new": "Новый", "started": "Активен", "ended": "Завершён"}.get(data['status'], "—")
            status_emoji = {"new": "🆕", "started": "▶️", "ended": "⏹️"}.get(data['status'], "")
            builder.add(InlineKeyboardButton(
                text=f"{data['title']} ({status_text}) {status_emoji}",
                callback_data=f"secrgiveaway_{data['id']}"
            ))

        # Навигация
        if total_pages > 1:
            nav_buttons = []
            if int(page) > 0:
                nav_buttons.append(InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"secrpage_{int(page) - 1}_{admin.admin_id}"
                ))
            

            

            if int(page) < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton(
                    text="Вперед ➡️",
                    callback_data=f"secrpage_{int(page) + 1}_{admin.admin_id}"
                ))
                
            nav_buttons.append(InlineKeyboardButton(
                text=f"{int(page) + 1}/{total_pages}",
                callback_data="noop_page"
            ))

            builder.row(*nav_buttons)

        # Кнопка добавления
        
    else:
        # Нет розыгрышей
        builder.add(InlineKeyboardButton(
            text="НЕТ РОЗЫГРЫШЕЙ",
            callback_data="noop"
        ))
    
    builder.button(text="<- НАЗАД", callback_data=f"adm_{admin.id}")

    builder.adjust(1)

    return builder.as_markup()

def secrgiveaway_kb(giveaway_data, admin):
    builder = InlineKeyboardBuilder()
    
    
    builder.add(InlineKeyboardButton(
        text="СПОНСОРЫ",
        callback_data=f"secrgasponsorsconfig_{giveaway_data.id}"
    ))
        
    builder.add(InlineKeyboardButton(
        text="<- НАЗАД",
        callback_data=f"adminga_{admin.admin_id}"
    ))
    builder.adjust(1)
    return builder.as_markup()

def secrsponsors_kb(giveaway, sponsorslist):
    builder = InlineKeyboardBuilder()
    if sponsorslist:
        for sponsor in sponsorslist:
            builder.add(InlineKeyboardButton(
                text=f"{sponsor['title']}",
                callback_data=f"secrsponsor_{sponsor['id']}_{giveaway.id}"
            ))
        builder.add(InlineKeyboardButton(
            text="ДОБАВИТЬ ЕЩЕ СПОНСОРА",
            callback_data=f"addgasponsor_{giveaway.id}"
        ))
    else:
        builder.add(InlineKeyboardButton(
            text="ДОБАВИТЬ ПЕРВОГО СПОНСОРА",
            callback_data=f"addgasponsor_{giveaway.id}"
        ))
    
    builder.button(text='<- НАЗАД', callback_data=f'secrgiveaway_{giveaway.id}')
    
    builder.adjust(1)
    return builder.as_markup()

def secrsponsor_kb(sponsor_id, giveaway_id):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="УДАЛИТЬ СПОНСОРА",
        callback_data=f"deletesp_{sponsor_id}_{giveaway_id}"
    )
    builder.button(
        text="<- НАЗАД",
        callback_data=f"backtosecrsponsors_{giveaway_id}"
    )

    builder.adjust(1)

    return builder.as_markup()