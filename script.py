import os
import logging
from datetime import datetime, timedelta, time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue
from workalendar.europe import Germany
import pytz
from typing import List, Dict

# Настройки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = "7975152331:AAEAkrFkXCLkSQs-nBev7MBRggkFJwxXW98"
DEBT_FILE = "debt.txt"
cal = Germany()
tz = pytz.timezone('Europe/Berlin')

# Расписание уроков (дни 0-4 = Понедельник - Пятница)
LESSON_SCHEDULE: Dict[int, List[Dict]] = {
    0: [  # Понедельник
        {"start": time(8, 15), "end": time(9, 0), "name": "Mathe: Gruppenarbeit"},
        {"start": time(9, 15), "end": time(10, 0), "name": "Sport"},
        {"start": time(10, 5), "end": time(10, 50), "name": "Sport"},
        {"start": time(11, 10), "end": time(11, 55), "name": "English"}
    ],
    1: [  # Вторник
        {"start": time(8, 15), "end": time(9, 0), "name": "Mathe: Wochenplan"},
        {"start": time(9, 15), "end": time(10, 0), "name": "Englisch"},
        {"start": time(10, 5), "end": time(10, 50), "name": "DaZ: Wochenplan"},
        {"start": time(11, 10), "end": time(11, 55), "name": "DaZ: Wochenplan"},
        {"start": time(12, 0), "end": time(12, 45), "name": "DaZ: Wochenplan"}
    ],
    2: [  # Среда
        {"start": time(8, 15), "end": time(9, 0), "name": "Mathe: Anton/Wochenplan"},
        {"start": time(9, 15), "end": time(10, 0), "name": "Werte"},
        {"start": time(10, 5), "end": time(10, 50), "name": "DaZ: Wochenplan"},
        {"start": time(11, 10), "end": time(11, 55), "name": "Englisch"},
        {"start": time(12, 0), "end": time(12, 45), "name": "DaZ: Lernzeit"}
    ],
    3: [  # Четверг
        {"start": time(8, 15), "end": time(9, 0), "name": "DaZ: Wochenplan"},
        {"start": time(9, 15), "end": time(10, 0), "name": "GRO/Geschichte"},
        {"start": time(10, 5), "end": time(10, 50), "name": "Geo/Geschichte"},
        {"start": time(11, 10), "end": time(11, 55), "name": "Englisch"},
        {"start": time(12, 0), "end": time(12, 45), "name": "DaZ: Wochenplan"}
    ],
    4: [  # Пятница
        {"start": time(8, 15), "end": time(9, 0), "name": "DaZ: Wochenplan"},
        {"start": time(9, 15), "end": time(10, 0), "name": "DaZ: Wochenplan"},
        {"start": time(10, 5), "end": time(10, 50), "name": "Mathe: Wochenplan"},
        {"start": time(11, 10), "end": time(11, 55), "name": "Werte"},
        {"start": time(12, 0), "end": time(12, 45), "name": "DaZ: Lernzeit / Feedback"}
    ]
}


def get_current_lessons(now: datetime) -> List[Dict]:
    """Возвращает список оставшихся уроков на сегодня"""
    weekday = now.weekday()
    if weekday not in LESSON_SCHEDULE:
        return []

    current_time = now.time()
    return [lesson for lesson in LESSON_SCHEDULE[weekday] if lesson["start"] > current_time]


def format_lessons(lessons: List[Dict]) -> str:
    """Форматирует список уроков в текст"""
    return "\n".join(
        f"{lesson['start'].strftime('%H:%M')} - {lesson['end'].strftime('%H:%M')} → {lesson['name']}"
        for lesson in lessons
    )


# Команда /urok
async def urok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает оставшиеся уроки на сегодня.
    Если уроки закончились, выводит расписание следующего учебного дня.
    """
    try:
        now = datetime.now(tz)
        lessons = get_current_lessons(now)

        if not lessons:
            # Если уроки сегодня закончились, выводим расписание следующего учебного дня
            next_date = now.date() + timedelta(days=1)
            # Если следующий день не учебный (выходной), переходим на ближайший учебный день
            while next_date.weekday() not in LESSON_SCHEDULE:
                next_date += timedelta(days=1)
            lessons_next = LESSON_SCHEDULE[next_date.weekday()]
            response = f"Расписание на {next_date.strftime('%d.%m.%Y')}:\n" + format_lessons(lessons_next)
        else:
            response = format_lessons(lessons)

        await update.message.reply_text(response)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


# Уведомление о начале уроков
async def lesson_notification(context: ContextTypes.DEFAULT_TYPE):
    """
    Проверяет и отправляет уведомление об уроках ровно в момент их начала.
    """
    now = datetime.now(tz)
    lessons = get_current_lessons(now)

    if not lessons:
        return

    next_lesson = lessons[0]
    lesson_start = datetime.combine(now.date(), next_lesson["start"]).astimezone(tz)

    # Отправляем уведомление ровно в момент начала урока
    if now.hour == lesson_start.hour and now.minute == lesson_start.minute:
        response = format_lessons(lessons)
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=response
        )


def load_debt() -> float:
    if os.path.exists(DEBT_FILE):
        with open(DEBT_FILE, "r") as f:
            return float(f.read().strip())
    return 335.0


def save_debt(amount: float):
    with open(DEBT_FILE, "w") as f:
        f.write(str(amount))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для учета долга и расписания.\n"
        "Используй:\n"
        "/tato - управление долгом\n"
        "/urok - расписание уроков"
    )


async def tato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        current_debt = load_debt()

        if not args:
            today = datetime.now(tz).strftime("%d.%m.%Y")
            await update.message.reply_text(f"📅 На {today} долг составляет: {current_debt}€")
            return

        operation = args[0]

        if operation.startswith(("+", "-")):
            value = float(operation[1:])
            new_debt = current_debt + value if operation.startswith("+") else current_debt - value
            save_debt(new_debt)
            today = datetime.now(tz).strftime("%d.%m.%Y")
            await update.message.reply_text(
                f"✅ Долг изменен на {operation} ({today})\n"
                f"📅 Новый долг: {new_debt}€"
            )

        elif operation == "stay":
            if len(args) < 2:
                await update.message.reply_text("Используй: /tato stay <сумма>")
                return
            new_debt = float(args[1])
            save_debt(new_debt)
            today = datetime.now(tz).strftime("%d.%m.%Y")
            await update.message.reply_text(
                f"✅ Долг установлен на {new_debt}€ ({today})"
            )
        else:
            await update.message.reply_text("Используй: /tato [+-]<сумма> или /tato stay <сумма>")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


def add_daily_debt():
    now = datetime.now(tz)
    if now.weekday() < 5 and not cal.is_holiday(now.date()):
        debt = load_debt() + 5
        save_debt(debt)
        logging.info(f"Добавлено 5€ за {now.strftime('%d.%m.%Y')}. Новый долг: {debt}€")


async def weekly_notification(context: ContextTypes.DEFAULT_TYPE):
    debt = load_debt()
    today = datetime.now(tz).strftime("%d.%m.%Y")
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"📅 На {today} долг составляет: {debt}€"
    )


def setup_jobs(job_queue: JobQueue, chat_id: int):
    job_queue.run_daily(
        lambda ctx: add_daily_debt(),
        time=time(hour=0, minute=1, tzinfo=tz),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_debt"
    )

    job_queue.run_repeating(
        weekly_notification,
        interval=604800,
        first=datetime.now(tz).replace(
            hour=6, minute=50, second=0, microsecond=0,
            tzinfo=tz
        ) + timedelta(days=(7 - datetime.now(tz).weekday()) % 7),
        chat_id=chat_id,
        name="weekly_notification"
    )

    job_queue.run_repeating(
        lesson_notification,
        interval=60,
        first=datetime.now(tz) + timedelta(seconds=10),
        chat_id=chat_id,
        name="lesson_checker"
    )


async def post_init(application):
    await application.bot.set_my_commands([
        ("start", "Начало работы"),
        ("tato", "Управление долгом"),
        ("urok", "Расписание уроков")
    ])
    setup_jobs(application.job_queue, chat_id=1485636207)


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tato", tato))
    app.add_handler(CommandHandler("urok", urok))
    app.run_polling(drop_pending_updates=True)
