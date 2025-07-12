# fitness_bot.py
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import aiosqlite
import datetime

logging.basicConfig(level=logging.INFO)

API_TOKEN = '7945310198:AAEv28Kn-tYPtHPJf7PW3UnVsJUtsfzhHrk'
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# FSM states
class UserData(StatesGroup):
    age = State()
    gender = State()
    height = State()
    weight = State()
    goal = State()
    target_weight = State()
    health_issues = State()
    training_place = State()
    training_frequency = State()

# Exercise database
exercise_db = {
    "дома": [
        {"name": "Приседания", "type": "силовые", "contra": ["колени"]},
        {"name": "Отжимания", "type": "силовые", "contra": []},
        {"name": "Планка", "type": "силовые", "contra": []},
        {"name": "Прыжки на месте", "type": "кардио", "contra": ["суставы"]},
        {"name": "Берпи", "type": "кардио", "contra": ["суставы", "спина"]},
        {"name": "Махи ногами", "type": "силовые", "contra": []}
    ],
    "в зале": [
        {"name": "Жим лежа", "type": "силовые", "contra": []},
        {"name": "Приседания со штангой", "type": "силовые", "contra": ["колени"]},
        {"name": "Тяга блока", "type": "силовые", "contra": []},
        {"name": "Эллипсоид", "type": "кардио", "contra": []},
        {"name": "Беговая дорожка", "type": "кардио", "contra": ["суставы"]}
    ]
}

@dp.message_handler(Command('start'))
async def cmd_start(message: types.Message):
    await message.reply("Привет! Сколько тебе лет?")
    await UserData.age.set()

@dp.message_handler(Command('restart'), state='*')
async def cmd_restart(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply("Анкета сброшена. Введи возраст:")
    await UserData.age.set()

@dp.message_handler(state=UserData.age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if not 10 <= age <= 99:
            raise ValueError
        await state.update_data(age=age)
        await message.reply("Пол? (мужской/женский)")
        await UserData.gender.set()
    except:
        await message.reply("Введите возраст от 10 до 99")

@dp.message_handler(state=UserData.gender)
async def process_gender(message: types.Message, state: FSMContext):
    gender = message.text.lower()
    if gender not in ['мужской', 'женский']:
        await message.reply("Пожалуйста, выбери 'мужской' или 'женский'")
        return
    await state.update_data(gender=gender)
    await message.reply("Рост (см)?")
    await UserData.height.set()

@dp.message_handler(state=UserData.height)
async def process_height(message: types.Message, state: FSMContext):
    try:
        height = int(message.text)
        if not 100 <= height <= 250:
            raise ValueError
        await state.update_data(height=height)
        await message.reply("Вес (кг)?")
        await UserData.weight.set()
    except:
        await message.reply("Введите рост от 100 до 250 см")

@dp.message_handler(state=UserData.weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = int(message.text)
        if not 30 <= weight <= 200:
            raise ValueError
        await state.update_data(weight=weight)
        await message.reply("Цель тренировок? (1 — поддерживать форму, 2 — похудеть, 3 — набрать массу)")
        await UserData.goal.set()
    except:
        await message.reply("Введите вес от 30 до 200 кг")

@dp.message_handler(state=UserData.goal)
async def process_goal(message: types.Message, state: FSMContext):
    goal = message.text
    if goal not in ['1', '2', '3']:
        await message.reply("Выбери 1, 2 или 3")
        return
    await state.update_data(goal=goal)
    if goal in ['2', '3']:
        await message.reply("Желаемый вес?")
        await UserData.target_weight.set()
    else:
        await state.update_data(target_weight=None)
        await message.reply("Проблемы со здоровьем?")
        await UserData.health_issues.set()

@dp.message_handler(state=UserData.target_weight)
async def process_target_weight(message: types.Message, state: FSMContext):
    try:
        tw = int(message.text)
        await state.update_data(target_weight=tw)
        await message.reply("Проблемы со здоровьем?")
        await UserData.health_issues.set()
    except:
        await message.reply("Введите число")

@dp.message_handler(state=UserData.health_issues)
async def process_health(message: types.Message, state: FSMContext):
    await state.update_data(health_issues=message.text.lower())
    await message.reply("Где будешь тренироваться? (дома/в зале)")
    await UserData.training_place.set()

@dp.message_handler(state=UserData.training_place)
async def process_place(message: types.Message, state: FSMContext):
    place = message.text.lower()
    if place not in ['дома', 'в зале']:
        await message.reply("Выбери 'дома' или 'в зале'")
        return
    await state.update_data(training_place=place)
    await message.reply("Сколько тренировок в неделю? (1-7)")
    await UserData.training_frequency.set()

@dp.message_handler(state=UserData.training_frequency)
async def process_freq(message: types.Message, state: FSMContext):
    try:
        freq = int(message.text)
        if not 1 <= freq <= 7:
            raise ValueError
        await state.update_data(training_frequency=freq)
        data = await state.get_data()
        await save_user_data(message.from_user.id, data)
        await message.reply("Данные сохранены. Используй /this_week или /next_week для тренировок.")
        await state.finish()
    except:
        await message.reply("Введите число от 1 до 7")

async def save_user_data(user_id, data):
    async with aiosqlite.connect("fitness_bot.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, age INTEGER, gender TEXT, height INTEGER, weight INTEGER,
            goal TEXT, target_weight INTEGER, health_issues TEXT, training_place TEXT, training_frequency INTEGER
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS workouts (
            user_id INTEGER, week_number INTEGER, plan TEXT,
            PRIMARY KEY(user_id, week_number)
        )""")
        await db.execute("""INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, data['age'], data['gender'], data['height'], data['weight'], data['goal'],
             data.get('target_weight'), data['health_issues'], data['training_place'], data['training_frequency']))
        await db.commit()

async def generate_training_plan(user_id, week_offset=0):
    async with aiosqlite.connect("fitness_bot.db") as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                return "Сначала пройди анкету с помощью /start"
            age, gender, place, goal, freq, health = user[1], user[2], user[8], user[5], user[9], user[7]
            week_number = datetime.date.today().isocalendar()[1] + week_offset

            # Проверка существующего плана
            async with db.execute("SELECT plan FROM workouts WHERE user_id = ? AND week_number = ?",
                                  (user_id, week_number)) as plan_cursor:
                row = await plan_cursor.fetchone()
                if row:
                    return f"План на {'эту' if week_offset == 0 else 'следующую'} неделю уже создан:\n\n{row[0]}"

            available = [e for e in exercise_db[place] if all(contra not in health for contra in e['contra'])]
            random.shuffle(available)
            plan = ""
            for i in range(freq):
                day = f"День {i+1}"
                chosen = random.sample(available, k=min(3, len(available)))
                exercises = "\n".join([f"- {ex['name']} – 3x15" for ex in chosen])
                plan += f"{day}:\n{exercises}\n\n"

            await db.execute("INSERT INTO workouts (user_id, week_number, plan) VALUES (?, ?, ?)",
                             (user_id, week_number, plan))
            await db.commit()
            return plan

@dp.message_handler(Command('this_week'))
async def this_week(message: types.Message):
    user_id = message.from_user.id
    plan = await generate_training_plan(user_id, 0)
    await message.reply(plan)

@dp.message_handler(Command('next_week'))
async def next_week(message: types.Message):
    user_id = message.from_user.id
    plan = await generate_training_plan(user_id, 1)
    await message.reply(plan)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
