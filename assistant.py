import sqlite3
import os
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

TOKEN = os.getenv("BOT_TOKEN")

conn = sqlite3.connect("tasks.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS tasks(
id INTEGER PRIMARY KEY,
task TEXT,
date TEXT,
time TEXT,
status TEXT
)
""")
conn.commit()

main_keyboard = [
["➕ Add Task","📋 Today Tasks"],
["📅 All Tasks","✅ Complete Task"]
]

main_markup = ReplyKeyboardMarkup(main_keyboard,resize_keyboard=True)

date_keyboard = [
["📅 Today","📅 Tomorrow"],
["✏ Custom Date"]
]

date_markup = ReplyKeyboardMarkup(date_keyboard,resize_keyboard=True)

time_keyboard = [
["🕕 6:00 PM","🕖 7:00 PM"],
["🕗 8:00 PM","🕘 9:00 PM"],
["✏ Custom Time"]
]

time_markup = ReplyKeyboardMarkup(time_keyboard,resize_keyboard=True)

TASK, DATE, TIME = range(3)

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello Rohith! Task Manager Ready.",
        reply_markup=main_markup
    )

async def add_task_start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Task name enter pannunga:")
    return TASK

async def task_name(update:Update,context:ContextTypes.DEFAULT_TYPE):
    context.user_data["task"]=update.message.text

    await update.message.reply_text(
        "Date select pannunga:",
        reply_markup=date_markup
    )

    return DATE

async def task_date(update:Update,context:ContextTypes.DEFAULT_TYPE):

    text=update.message.text

    if text=="📅 Today":
        date=datetime.now().strftime("%Y-%m-%d")

    elif text=="📅 Tomorrow":
        date=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")

    else:
        date=text

    context.user_data["date"]=date

    await update.message.reply_text(
        "Time select pannunga:",
        reply_markup=time_markup
    )

    return TIME

async def task_time(update:Update,context:ContextTypes.DEFAULT_TYPE):

    task=context.user_data["task"]
    date=context.user_data["date"]
    time=update.message.text

    c.execute(
        "INSERT INTO tasks(task,date,time,status) VALUES(?,?,?,?)",
        (task,date,time,"pending")
    )

    conn.commit()

    await update.message.reply_text(
        "Task added successfully!",
        reply_markup=main_markup
    )

    return ConversationHandler.END

async def today_tasks(update:Update,context:ContextTypes.DEFAULT_TYPE):

    today=datetime.now().strftime("%Y-%m-%d")

    rows=c.execute(
        "SELECT task,time FROM tasks WHERE date=? AND status='pending'",
        (today,)
    ).fetchall()

    if not rows:
        await update.message.reply_text("No tasks for today")
        return

    msg="Today's Tasks\n\n"

    for i,r in enumerate(rows,1):
        msg+=f"{i}. {r[0]} - {r[1]}\n"

    await update.message.reply_text(msg)

async def all_tasks(update:Update,context:ContextTypes.DEFAULT_TYPE):

    rows=c.execute(
        "SELECT id,task,date,time,status FROM tasks"
    ).fetchall()

    msg="All Tasks\n\n"

    for r in rows:
        msg+=f"{r[0]}. {r[1]} | {r[2]} | {r[3]} ({r[4]})\n"

    await update.message.reply_text(msg)

async def complete_task(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Task ID send pannunga complete panna")

async def mark_done(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.message.text.isdigit():

        task_id=update.message.text

        c.execute(
            "UPDATE tasks SET status='done' WHERE id=?",
            (task_id,)
        )

        conn.commit()

        await update.message.reply_text("Task completed!")

async def router(update:Update,context:ContextTypes.DEFAULT_TYPE):

    text=update.message.text

    if text=="📋 Today Tasks":
        await today_tasks(update,context)

    elif text=="📅 All Tasks":
        await all_tasks(update,context)

    elif text=="✅ Complete Task":
        await complete_task(update,context)

    else:
        await mark_done(update,context)

conv_handler=ConversationHandler(

entry_points=[MessageHandler(filters.TEXT & filters.Regex("➕ Add Task"),add_task_start)],

states={

TASK:[MessageHandler(filters.TEXT,task_name)],

DATE:[MessageHandler(filters.TEXT,task_date)],

TIME:[MessageHandler(filters.TEXT,task_time)]

},

fallbacks=[]
)

app=ApplicationBuilder().token("8602038532:AAFgGowucCDiM6MTawht2pu8xuCoDjUylFY").build()

app.add_handler(CommandHandler("start",start))
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT,router))

app.run_polling()