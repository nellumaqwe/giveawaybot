from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
import logging
from database.models import Giveaway, Admin, Autopost
from aiogram.filters import CommandStart
from keyboards.inline import start_kb, giveaways_keyb
from settings import config, ULTIMATE_ADMIN
import re
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()

@router.message(CommandStart())
async def start(message:Message):
    giveaways = await Giveaway.filter(admin = message.from_user.id, status = 'started').order_by('-id').all()
    admin = await Admin.filter(admin_id = message.from_user.id).first()
    bites = await Autopost.filter(admin = message.from_user.id, rassilkastatus='on').all()
    giveaways_titles = [f"{ga.title} ({len(json.loads(ga.participants_ended_task))} участников)" for ga in giveaways]
    displayed_giveaways = giveaways_titles[:7]
    remaining_count = len(giveaways_titles) - 7
    bites_titles = [bite.title for bite in bites]
    giveaways_str = '\n· '.join(displayed_giveaways) if giveaways_titles else "Нет активных розыгрышей, нажми на кнопку 'РОЗЫГРЫШИ' и создай первый"
    if remaining_count > 0:
            giveaways_str += f"\n\n<blockquote>...и ещё {remaining_count} активных розыгрыша(ей)</blockquote>"
    bites_str = '\n· '.join(bites_titles) if bites_titles else "Нет активных автобайтов, нажми на кнопку 'ПОСТЫ' и настрой автобайты"
    
    await message.answer(f'Привет, {admin.name or admin.username or admin.admin_id}\n\n<strong>Сейчас идут розыгрыши:</strong>\n\n<blockquote>· {giveaways_str}</blockquote>\n\n<strong>Автобайты включены для постов:</strong>\n\n<blockquote>· {bites_str}</blockquote>', reply_markup=start_kb(message.from_user.id, admin), parse_mode="HTML")

@router.callback_query(F.data=='update')
async def update(callback:CallbackQuery):
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

@router.callback_query(F.data == 'giveaways')
async def giveaways(callback:CallbackQuery):
    await callback.answer()
    if await Admin.filter(admin_id = callback.from_user.id).exists() or callback.from_user.id == int(config["MAINADMIN"]):
        active_giveaways = []
        admin = await Admin.filter(admin_id = callback.from_user.id).first()
        if callback.from_user.id == ULTIMATE_ADMIN:
            giveaways_data = await Giveaway.all()
        else:
            giveaways_data = await Giveaway.filter(admin = callback.from_user.id)
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
            )
        else:
            await callback.message.edit_text(
                "Создайте первый розыгрыш", 
                reply_markup=giveaways_keyb()
            )
    else:
        await callback.message.answer("Ты не админ!\nДля использования бота нужно попросить главного админа добавить тебя в белый список.\n\nПиши - @whyon1x")
