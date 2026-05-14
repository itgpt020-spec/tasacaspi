import asyncio
import requests
API_URL = "https://tazakaspiyy.onrender.com"
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ContentType,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from config import BOT_TOKEN, TRASH_TYPES
from database import (
    init_db, add_user, add_cleanup, add_cleanup_item,
    add_trash_spot, update_user_stats
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === КЛАВИАТУРЫ ===
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='🧹 Я убрал мусор')],
        [KeyboardButton(text='📍 Здесь свалка'), KeyboardButton(text='📊 Статистика')],
        [KeyboardButton(text='🏆 Рейтинг')],
    ],
    resize_keyboard=True
)

type_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='♻️ Пластик'), KeyboardButton(text='🍾 Стекло')],
        [KeyboardButton(text='🔩 Металл'), KeyboardButton(text='📄 Бумага')],
        [KeyboardButton(text='🗑 Бытовой'), KeyboardButton(text='🧱 Строительный')],
        [KeyboardButton(text='⚪ Другое'), KeyboardButton(text='✅ Готово')],
    ],
    resize_keyboard=True
)

# === FSM ===
class CleanupForm(StatesGroup):
    waiting_photo = State()
    waiting_location = State()
    waiting_location_name = State()
    waiting_trash_type = State()
    waiting_weight = State()
    waiting_bags = State()
    waiting_more = State()
    waiting_notes = State()


class SpotForm(StatesGroup):
    waiting_photo = State()
    waiting_location = State()
    waiting_description = State()


# === ХЕЛПЕРЫ ===
def get_type_key(display_text):
    for key, val in TRASH_TYPES.items():
        if val == display_text or val in display_text or display_text in val:
            return key
    return 'other'


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user = message.from_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    requests.post(f"{API_URL}/api/user", json={     # ← 4 пробела отступа!
        "telegram_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    })
    await message.answer(                            # ← тоже 4 пробела
        f'Привет, {user.first_name}! 🌊\n\n'
        'Ты в проекте <b>ТазаКаспий</b> — экотрекере Атырау.\n\n'
        'Что можно сделать:\n'
        '• 🧹 Отметить уборку мусора\n'
        '• 📍 Показать новую свалку\n'
        '• 📊 Посмотреть общую статистику\n'
        '• 🏆 Посмотреть рейтинг активистов',
        parse_mode='HTML',
        reply_markup=main_kb
    )


# === УБОРКА МУСОРА ===
@dp.message(F.text == '🧹 Я убрал мусор')
async def start_cleanup(message: types.Message, state: FSMContext):
    await state.set_state(CleanupForm.waiting_photo)
    await message.answer(
        'Отлично! Давай зафиксируем результат.\n'
        'Сначала пришли <b>фото</b> собранного мусора (или места после уборки).',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='❌ Отмена')]],
            resize_keyboard=True
        )
    )


@dp.message(CleanupForm.waiting_photo, F.content_type == ContentType.PHOTO)
async def cleanup_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await state.set_state(CleanupForm.waiting_location)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📍 Отправить геолокацию', request_location=True)],
            [KeyboardButton(text='❌ Отмена')]
        ],
        resize_keyboard=True
    )
    await message.answer('Теперь отправь геолокацию, где убирал:', reply_markup=kb)


@dp.message(CleanupForm.waiting_location, F.content_type == ContentType.LOCATION)
async def cleanup_location(message: types.Message, state: FSMContext):
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    await state.set_state(CleanupForm.waiting_location_name)
    await message.answer(
        'Напиши название места (например: <i>пляж Сайгалык, пляж Жумыскер, набережная</i>):',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='❌ Отмена')]],
            resize_keyboard=True
        )
    )


@dp.message(CleanupForm.waiting_location_name)
async def cleanup_location_name(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.clear()
        return await message.answer('Отменено.', reply_markup=main_kb)
    await state.update_data(location_name=message.text)
    await state.set_state(CleanupForm.waiting_trash_type)
    await message.answer(
        'Выбери тип мусора, который собрал. Можно добавить несколько — жми ✅ Готово, когда закончишь.',
        reply_markup=type_kb
    )


@dp.message(CleanupForm.waiting_trash_type)
async def cleanup_trash_type(message: types.Message, state: FSMContext):
    text = message.text
    if text == '❌ Отмена':
        await state.clear()
        return await message.answer('Отменено.', reply_markup=main_kb)

    if text == '✅ Готово':
        data = await state.get_data()
        items = data.get('items', [])
        if not items:
            return await message.answer('Добавь хотя бы один тип мусора.')
        await state.set_state(CleanupForm.waiting_notes)
        return await message.answer(
            'Добавь комментарий (или напиши "нет"):',
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text='❌ Отмена')]],
                resize_keyboard=True
            )
        )

    type_key = get_type_key(text)
    await state.update_data(current_type=type_key)
    await state.set_state(CleanupForm.waiting_weight)
    await message.answer(
        f'Сколько килограммов <b>{TRASH_TYPES.get(type_key, text)}</b> собрал? (можно примерно, цифрой)',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='❌ Отмена')]],
            resize_keyboard=True
        )
    )


@dp.message(CleanupForm.waiting_weight)
async def cleanup_weight(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.clear()
        return await message.answer('Отменено.', reply_markup=main_kb)
    try:
        weight = float(message.text.replace(',', '.'))
    except ValueError:
        return await message.answer('Введи число, например: 2.5')

    await state.update_data(current_weight=weight)
    await state.set_state(CleanupForm.waiting_bags)
    await message.answer(
        'Сколько мешков заполнил? (число)',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='❌ Отмена')]],
            resize_keyboard=True
        )
    )


@dp.message(CleanupForm.waiting_bags)
async def cleanup_bags(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.clear()
        return await message.answer('Отменено.', reply_markup=main_kb)
    try:
        bags = int(message.text)
    except ValueError:
        return await message.answer('Введи целое число, например: 3')

    data = await state.get_data()
    items = data.get('items', [])
    items.append({
        'type': data['current_type'],
        'weight': data['current_weight'],
        'bags': bags
    })
    await state.update_data(items=items)
    await state.set_state(CleanupForm.waiting_trash_type)

    summary = '\n'.join([f'• {TRASH_TYPES.get(i["type"], i["type"])} — {i["weight"]} кг ({i["bags"]} мешков)' for i in items])
    await message.answer(
        f'Добавлено!\n\n<b>Текущий список:</b>\n{summary}\n\n'
        'Добавь ещё или нажми ✅ Готово',
        parse_mode='HTML',
        reply_markup=type_kb
    )


@dp.message(CleanupForm.waiting_notes)
async def cleanup_notes(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.clear()
        return await message.answer('Отменено.', reply_markup=main_kb)

    data = await state.get_data()
    notes = message.text if message.text.lower() != 'нет' else None

    cleanup_id = add_cleanup(
        user_id=message.from_user.id,
        lat=data['lat'],
        lon=data['lon'],
        location_name=data['location_name'],
        photo_file_id=data['photo_id'],
        notes=notes
    )

    total_kg = 0
    for item in data.get('items', []):
        add_cleanup_item(cleanup_id, item['type'], item['weight'], item['bags'])
        total_kg += item['weight']

    update_user_stats(message.from_user.id)
    requests.post(f"{API_URL}/api/cleanup", json={
        "user_id": message.from_user.id,
        "lat": data['lat'],
        "lon": data['lon'],
        "location_name": data['location_name'],
        "photo_file_id": data.get('photo_id'),
        "notes": notes,
        "items": data.get('items', [])
    })

    await state.clear()
    await message.answer(
        f'🎉 <b>Уборка зафиксирована!</b>\n\n'
        f'📍 Место: {data["location_name"]}\n'
        f'♻️ Всего собрано: <b>{total_kg} кг</b>\n'
        f'🙏 Спасибо за чистый Каспий!',
        parse_mode='HTML',
        reply_markup=main_kb
    )


# === СВАЛКА (ГДЕ МУСОР ОСТАЛСЯ) ===
@dp.message(F.text == '📍 Здесь свалка')
async def start_spot(message: types.Message, state: FSMContext):
    await state.set_state(SpotForm.waiting_photo)
    await message.answer(
        'Пришли фото свалки (или нажми "Пропустить"):',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='⏭ Пропустить')],
                [KeyboardButton(text='❌ Отмена')]
            ],
            resize_keyboard=True
        )
    )


@dp.message(SpotForm.waiting_photo, F.content_type == ContentType.PHOTO)
async def spot_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await spot_ask_location(message, state)


@dp.message(SpotForm.waiting_photo, F.text == '⏭ Пропустить')
async def spot_skip_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=None)
    await spot_ask_location(message, state)


async def spot_ask_location(message, state):
    await state.set_state(SpotForm.waiting_location)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📍 Отправить геолокацию', request_location=True)],
            [KeyboardButton(text='❌ Отмена')]
        ],
        resize_keyboard=True
    )
    await message.answer('Отправь геолокацию свалки:', reply_markup=kb)


@dp.message(SpotForm.waiting_location, F.content_type == ContentType.LOCATION)
async def spot_location(message: types.Message, state: FSMContext):
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    await state.set_state(SpotForm.waiting_description)
    await message.answer(
        'Опиши ситуацию (например: <i>бытовой мусор, размер ~5 м², воняет</i>):',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='❌ Отмена')]],
            resize_keyboard=True
        )
    )


@dp.message(SpotForm.waiting_description)
async def spot_description(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.clear()
        return await message.answer('Отменено.', reply_markup=main_kb)

    data = await state.get_data()
    add_trash_spot(
        user_id=message.from_user.id,
        lat=data['lat'],
        lon=data['lon'],
        description=message.text,
        photo_file_id=data.get('photo_id')
    )
    requests.post(f"{API_URL}/api/spot", json={
        "user_id": message.from_user.id,
        "lat": data['lat'],
        "lon": data['lon'],
        "description": message.text,
        "photo_file_id": data.get('photo_id')
    })
    await state.clear()
    await message.answer(
        '📍 <b>Свалка отмечена на карте!</b>\n'
        'Волонтёры увидят её и смогут убрать.',
        parse_mode='HTML',
        reply_markup=main_kb
    )


# === СТАТИСТИКА И РЕЙТИНГ В БОТЕ ===
@dp.message(F.text == '📊 Статистика')
async def show_stats(message: types.Message):
    from database import get_stats_by_type, get_monthly_stats
    by_type = get_stats_by_type()
    monthly = get_monthly_stats()

    text = '<b>📊 Общая статистика проекта</b>\n\n'
    if by_type:
        text += '<b>По типам мусора:</b>\n'
        for t, w, b in by_type:
            name = TRASH_TYPES.get(t, t)
            text += f'{name}: {w or 0:.1f} кг\n'
    else:
        text += 'Пока нет данных. Стань первым!\n'

    if monthly:
        text += '\n<b>По месяцам:</b>\n'
        for m, w, c in monthly[:6]:
            text += f'{m}: {w or 0:.1f} кг ({c} уборок)\n'

    await message.answer(text, parse_mode='HTML', reply_markup=main_kb)


@dp.message(F.text == '🏆 Рейтинг')
async def show_rating(message: types.Message):
    from database import get_leaderboard
    leaders = get_leaderboard(10)
    if not leaders:
        return await message.answer('Пока нет участников. Будь первым! 🏆', reply_markup=main_kb)

    text = '<b>🏆 Топ волонтёров</b>\n\n'
    for i, (name, username, kg, count, group) in enumerate(leaders, 1):
        medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}.')
        uname = f' (@{username})' if username else ''
        text += f'{medal} {name}{uname} — <b>{kg:.1f} кг</b> ({count} уборок)\n'

    await message.answer(text, parse_mode='HTML', reply_markup=main_kb)


@dp.message(F.text == '❌ Отмена')
async def cancel_any(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer('Отменено.', reply_markup=main_kb)


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
