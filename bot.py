import asyncio
import json
import logging
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

with open(os.path.join(os.path.dirname(__file__), "questions.json"), encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

TOTAL = len(ALL_QUESTIONS)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# user_id -> session state
sessions: dict[int, dict] = {}


def build_session(count: int) -> dict:
    indices = list(range(TOTAL))
    random.shuffle(indices)
    indices = indices[:count]
    return {
        "order": indices,
        "pos": 0,
        "score": 0,
        "current_options": None,
        "current_correct": None,
        "answered": False,
    }


def make_question_payload(session: dict):
    q_index = session["order"][session["pos"]]
    q = ALL_QUESTIONS[q_index]
    options = q["options"][:]
    random.shuffle(options)
    session["current_options"] = options
    session["current_correct"] = q["correct"]
    session["answered"] = False

    text = f"❓ {session['pos'] + 1}/{len(session['order'])}\n\n{q['question']}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"ans:{i}")]
            for i, opt in enumerate(options)
        ]
    )
    return text, keyboard


async def send_question(chat_id: int, session: dict):
    text, keyboard = make_question_payload(session)
    await bot.send_message(chat_id, text, reply_markup=keyboard)


async def finish_quiz(chat_id: int, session: dict):
    total = len(session["order"])
    score = session["score"]
    percent = round(score / total * 100) if total else 0
    await bot.send_message(
        chat_id,
        f"🏁 Test yakunlandi!\n\n"
        f"✅ To'g'ri javoblar: {score}/{total}\n"
        f"📊 Natija: {percent}%\n\n"
        f"Qayta boshlash uchun /start buyrug'ini yuboring.",
    )
    sessions.pop(chat_id, None)


def main_menu_text() -> str:
    return (
        "🎓 MUM bo'yicha test!\n\n"
        f"Jami savollar bazasi: {TOTAL} ta\n\n"
        "🎲 Tanlang:\n"
        "/quiz10 — 10 ta savol\n"
        "/quiz20 — 20 ta savol\n"
        "/quiz50 — 50 ta savol\n"
        "/quizall — barcha savollar\n\n"
        "/stop — testni to'xtatish"
    )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    sessions.pop(message.chat.id, None)
    await message.answer(main_menu_text())


@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    if message.chat.id in sessions:
        sessions.pop(message.chat.id, None)
        await message.answer("Test to'xtatildi. /start")
    else:
        await message.answer("Hozircha faol test yo'q. /start")


async def start_quiz(message: Message, count: int):
    count = min(count, TOTAL)
    session = build_session(count)
    sessions[message.chat.id] = session
    await message.answer(f"✅ {count} ta savol. Boshlandi! 👇")
    await send_question(message.chat.id, session)


@dp.message(Command("quiz10"))
async def cmd_quiz10(message: Message):
    await start_quiz(message, 10)


@dp.message(Command("quiz20"))
async def cmd_quiz20(message: Message):
    await start_quiz(message, 20)


@dp.message(Command("quiz50"))
async def cmd_quiz50(message: Message):
    await start_quiz(message, 50)


@dp.message(Command("quizall"))
async def cmd_quizall(message: Message):
    await start_quiz(message, TOTAL)


@dp.callback_query(F.data.startswith("ans:"))
async def handle_answer(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    session = sessions.get(chat_id)

    if not session or session.get("answered"):
        await callback.answer()
        return

    chosen_index = int(callback.data.split(":")[1])
    chosen_text = session["current_options"][chosen_index]
    correct_text = session["current_correct"]
    is_correct = chosen_text == correct_text
    session["answered"] = True

    if is_correct:
        session["score"] += 1
        feedback = "✅ To'g'ri!"
    else:
        feedback = f"❌ Noto'g'ri.\nTo'g'ri javob: {correct_text}"

    await callback.message.edit_text(f"{callback.message.text}\n\n{feedback}")
    await callback.answer()

    session["pos"] += 1
    if session["pos"] >= len(session["order"]):
        await finish_quiz(chat_id, session)
    else:
        await send_question(chat_id, session)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
