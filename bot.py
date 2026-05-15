import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
import os

BOT_TOKEN = "8750633312:AAEBwJ2dyno_elQFUPNBeogYWSWj43pvCTQ"
ADMIN_ID = 7673683792

conn = sqlite3.connect('support_bot.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_helper INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            question TEXT,
            status TEXT DEFAULT 'open',
            helper_id INTEGER DEFAULT NULL,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            user_id INTEGER,
            message TEXT,
            is_from_helper INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (ADMIN_ID,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (user_id, username, is_helper) VALUES (?, ?, ?)', 
                       (ADMIN_ID, 'admin', 1))
    
    conn.commit()
    print("База данных готова")

init_db()

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class TicketStates(StatesGroup):
    waiting_question = State()
    waiting_answer = State()
    waiting_ticket_id = State()
    waiting_helper_id = State()

def is_helper(user_id):
    cursor.execute('SELECT is_helper FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row is not None and row[0] == 1

def user_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать тикет", callback_data="create_ticket")],
        [InlineKeyboardButton(text="📋 Мои тикеты", callback_data="my_tickets")],
        [InlineKeyboardButton(text="ℹ️ Статус тикета", callback_data="ticket_status")]
    ])

def helper_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 Открытые тикеты", callback_data="open_tickets")],
        [InlineKeyboardButton(text="✅ Мои тикеты", callback_data="my_helper_tickets")],
        [InlineKeyboardButton(text="🔒 Закрыть тикет", callback_data="close_ticket")],
        [InlineKeyboardButton(text="🔓 Открыть тикет", callback_data="reopen_ticket")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Список хелперов", callback_data="list_helpers")],
        [InlineKeyboardButton(text="➕ Добавить хелпера", callback_data="add_helper")],
        [InlineKeyboardButton(text="➖ Удалить хелпера", callback_data="remove_helper")],
        [InlineKeyboardButton(text="📋 Все тикеты", callback_data="all_tickets")],
        [InlineKeyboardButton(text="🗑 Удалить тикет", callback_data="admin_delete_ticket")],
        [InlineKeyboardButton(text="👤 Ответственный", callback_data="ticket_helper")]
    ])

@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or str(user_id)
    
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    
    await msg.answer(
        "🤖 *Система поддержки*\n\n"
        "▫️ Создайте тикет с вашим вопросом\n"
        "▫️ Хелпер ответит вам в ближайшее время\n"
        "▫️ Отслеживайте статус в разделе «Мои тикеты»",
        parse_mode="Markdown",
        reply_markup=user_menu()
    )

@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    user_id = msg.from_user.id
    if is_helper(user_id) or user_id == ADMIN_ID:
        await msg.answer("🛠 *Панель хелпера*", parse_mode="Markdown", reply_markup=helper_menu())
    else:
        await msg.answer("❌ У вас нет доступа к панели хелпера!")

@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("👑 *Панель администратора*", parse_mode="Markdown", reply_markup=admin_menu())
    else:
        await msg.answer("❌ Нет доступа!")

@dp.callback_query(F.data == "create_ticket")
async def create_ticket(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📝 *Опишите вашу проблему:*\n\n(Максимум 500 символов)", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_question)

@dp.message(TicketStates.waiting_question)
async def save_ticket(msg: types.Message, state: FSMContext):
    if len(msg.text) > 500:
        await msg.answer("❌ Слишком длинное сообщение! Максимум 500 символов.")
        return
    
    user_id = msg.from_user.id
    username = msg.from_user.username or str(user_id)
    question = msg.text
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO tickets (user_id, username, question, status, created_at, updated_at)
        VALUES (?, ?, ?, 'open', ?, ?)
    ''', (user_id, username, question, now, now))
    conn.commit()
    
    ticket_id = cursor.lastrowid
    
    await msg.answer(
        f"✅ *Тикет #{ticket_id} создан!*\n\n"
        f"Хелпер ответит вам в ближайшее время.\n"
        f"Вы можете отслеживать статус в разделе «Мои тикеты»",
        parse_mode="Markdown",
        reply_markup=user_menu()
    )
    
    cursor.execute('SELECT user_id FROM users WHERE is_helper = 1')
    helpers = cursor.fetchall()
    for helper in helpers:
        try:
            await bot.send_message(
                helper[0],
                f"🆕 *Новый тикет!*\n\n"
                f"ID: #{ticket_id}\n"
                f"От: @{username}\n"
                f"Вопрос: {question[:100]}...",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Ответить", callback_data=f"answer_ticket_{ticket_id}")]
                ])
            )
        except:
            pass
    
    await state.clear()

@dp.callback_query(F.data == "my_tickets")
async def my_tickets(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    cursor.execute('''
        SELECT id, status, created_at FROM tickets 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user_id,))
    tickets = cursor.fetchall()
    
    if not tickets:
        await call.answer("У вас нет тикетов", show_alert=True)
        return
    
    text = "📋 *Ваши тикеты:*\n\n"
    for t in tickets:
        status_icon = "🟢" if t[1] == 'open' else "🔴"
        text += f"{status_icon} #{t[0]} | {t[1]} | {t[2][:16]}\n"
    
    text += "\nНажмите на ID тикета для просмотра"
    
    buttons = [[InlineKeyboardButton(text=f"📌 Тикет #{t[0]}", callback_data=f"view_ticket_{t[0]}")] for t in tickets]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_user")])
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "ticket_status")
async def ticket_status_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("🔢 *Введите ID тикета:*", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_ticket_id)

@dp.callback_query(F.data.startswith("view_ticket_"))
async def view_ticket(call: types.CallbackQuery):
    ticket_id = int(call.data.split("_")[2])
    user_id = call.from_user.id
    
    cursor.execute('SELECT * FROM tickets WHERE id = ? AND user_id = ?', (ticket_id, user_id))
    ticket = cursor.fetchone()
    
    if not ticket:
        await call.answer("Тикет не найден!", show_alert=True)
        return
    
    text = f"📌 *Тикет #{ticket[0]}*\n\n"
    text += f"Вопрос: {ticket[3]}\n"
    text += f"Статус: {'🟢 Открыт' if ticket[4] == 'open' else '🔴 Закрыт'}\n"
    text += f"Создан: {ticket[6][:16]}\n"
    
    cursor.execute('SELECT message, is_from_helper, created_at FROM messages WHERE ticket_id = ? ORDER BY created_at', (ticket_id,))
    messages = cursor.fetchall()
    
    if messages:
        text += f"\n📝 *Переписка:*\n"
        for m in messages:
            sender = "Хелпер" if m[1] else "Вы"
            text += f"▫️ {sender} [{m[2][11:16]}]: {m[0][:150]}\n"
    
    if ticket[4] == 'open':
        buttons = [[InlineKeyboardButton(text="📝 Ответить", callback_data=f"user_answer_{ticket_id}")]]
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="my_tickets")])
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="my_tickets")]
        ]))

@dp.callback_query(F.data.startswith("user_answer_"))
async def user_answer_start(call: types.CallbackQuery, state: FSMContext):
    ticket_id = int(call.data.split("_")[2])
    await state.update_data(ticket_id=ticket_id)
    await call.message.edit_text("📝 *Введите ваш ответ:*", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_answer)

@dp.callback_query(F.data == "open_tickets")
async def open_tickets(call: types.CallbackQuery):
    if not is_helper(call.from_user.id) and call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    cursor.execute('SELECT id, username, question, created_at FROM tickets WHERE status = "open" ORDER BY created_at ASC')
    tickets = cursor.fetchall()
    
    if not tickets:
        await call.answer("Нет открытых тикетов", show_alert=True)
        return
    
    text = "📩 *Открытые тикеты:*\n\n"
    for t in tickets:
        text += f"▫️ #{t[0]} | @{t[1]} | {t[3][:16]}\n"
        text += f"   {t[2][:80]}...\n\n"
    
    buttons = [[InlineKeyboardButton(text=f"📝 Ответить на #{t[0]}", callback_data=f"answer_ticket_{t[0]}")] for t in tickets]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_helper")])
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "my_helper_tickets")
async def my_helper_tickets(call: types.CallbackQuery):
    helper_id = call.from_user.id
    
    cursor.execute('''
        SELECT id, username, question, status, created_at FROM tickets 
        WHERE helper_id = ? 
        ORDER BY created_at DESC
    ''', (helper_id,))
    tickets = cursor.fetchall()
    
    if not tickets:
        await call.answer("У вас нет назначенных тикетов", show_alert=True)
        return
    
    text = "✅ *Ваши тикеты:*\n\n"
    for t in tickets:
        status = "🟢" if t[3] == 'open' else "🔴"
        text += f"{status} #{t[0]} | @{t[1]} | {t[4][:16]}\n"
    
    buttons = [[InlineKeyboardButton(text=f"📝 Ответить на #{t[0]}", callback_data=f"answer_ticket_{t[0]}")] for t in tickets]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_helper")])
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "close_ticket")
async def close_ticket_start(call: types.CallbackQuery, state: FSMContext):
    if not is_helper(call.from_user.id) and call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    await call.message.edit_text("🔢 *Введите ID тикета для закрытия:*", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_ticket_id)

@dp.callback_query(F.data == "reopen_ticket")
async def reopen_ticket_start(call: types.CallbackQuery, state: FSMContext):
    if not is_helper(call.from_user.id) and call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    await call.message.edit_text("🔢 *Введите ID тикета для открытия:*", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_ticket_id)

@dp.callback_query(F.data.startswith("answer_ticket_"))
async def answer_ticket_start(call: types.CallbackQuery, state: FSMContext):
    if not is_helper(call.from_user.id) and call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    ticket_id = int(call.data.split("_")[2])
    helper_id = call.from_user.id
    
    cursor.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    
    if not ticket:
        await call.answer("Тикет не найден!", show_alert=True)
        return
    
    if ticket[4] != 'open':
        await call.answer("Тикет закрыт!", show_alert=True)
        return
    
    if not ticket[5]:
        cursor.execute('UPDATE tickets SET helper_id = ? WHERE id = ?', (helper_id, ticket_id))
        conn.commit()
    
    await state.update_data(ticket_id=ticket_id)
    await call.message.edit_text(f"📝 *Отвечаем на тикет #{ticket_id}*\n\nВведите ваш ответ:", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_answer)

@dp.message(TicketStates.waiting_answer)
async def process_answer(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    
    if not data or 'ticket_id' not in data:
        await msg.answer("❌ Ошибка! Попробуйте снова.")
        await state.clear()
        return
    
    ticket_id = data['ticket_id']
    user_id = msg.from_user.id
    message_text = msg.text
    now = datetime.now().isoformat()
    
    cursor.execute('SELECT user_id, status FROM tickets WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    
    if not ticket or ticket[1] != 'open':
        await msg.answer("❌ Тикет закрыт!")
        await state.clear()
        return
    
    is_helper_answer = is_helper(user_id) or user_id == ADMIN_ID
    
    cursor.execute('''
        INSERT INTO messages (ticket_id, user_id, message, is_from_helper, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (ticket_id, user_id, message_text, 1 if is_helper_answer else 0, now))
    conn.commit()
    
    cursor.execute('UPDATE tickets SET updated_at = ? WHERE id = ?', (now, ticket_id))
    conn.commit()
    
    if is_helper_answer:
        await msg.answer("✅ Ответ отправлен пользователю!", reply_markup=helper_menu())
    else:
        await msg.answer("✅ Сообщение отправлено хелперу!", reply_markup=user_menu())
    
    if is_helper_answer:
        try:
            await bot.send_message(
                ticket[0],
                f"📩 *Новый ответ в тикете #{ticket_id}*\n\n"
                f"Сообщение: {message_text[:200]}\n\n"
                f"Вы можете ответить в разделе «Мои тикеты»",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Посмотреть тикет", callback_data=f"view_ticket_{ticket_id}")]
                ])
            )
        except:
            pass
    else:
        cursor.execute('SELECT user_id FROM users WHERE is_helper = 1')
        helpers = cursor.fetchall()
        for helper in helpers:
            try:
                await bot.send_message(
                    helper[0],
                    f"📩 *Новый ответ в тикете #{ticket_id}*\n\n"
                    f"От пользователя @{msg.from_user.username or msg.from_user.id}\n"
                    f"Сообщение: {message_text[:200]}",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📝 Ответить", callback_data=f"answer_ticket_{ticket_id}")]
                    ])
                )
            except:
                pass
    
    await state.clear()

@dp.callback_query(F.data == "list_helpers")
async def list_helpers(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    cursor.execute('SELECT user_id, username FROM users WHERE is_helper = 1')
    helpers = cursor.fetchall()
    
    text = "👥 *Список хелперов:*\n\n"
    for h in helpers:
        text += f"▫️ @{h[1] or h[0]} (ID: {h[0]})\n"
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_menu())

@dp.callback_query(F.data == "add_helper")
async def add_helper_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    await call.message.edit_text("➕ *Введите ID пользователя для добавления в хелперы:*", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_helper_id)
    await state.update_data(action="add")

@dp.callback_query(F.data == "remove_helper")
async def remove_helper_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    await call.message.edit_text("➖ *Введите ID хелпера для удаления:*", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_helper_id)
    await state.update_data(action="remove")

@dp.callback_query(F.data == "all_tickets")
async def all_tickets_admin(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    cursor.execute('SELECT id, username, status, created_at FROM tickets ORDER BY created_at DESC')
    tickets = cursor.fetchall()
    
    if not tickets:
        await call.answer("Нет тикетов", show_alert=True)
        return
    
    text = "📋 *Все тикеты:*\n\n"
    for t in tickets:
        status = "🟢" if t[2] == 'open' else "🔴"
        text += f"{status} #{t[0]} | @{t[1]} | {t[2]} | {t[3][:16]}\n"
    
    buttons = [[InlineKeyboardButton(text=f"📌 Тикет #{t[0]}", callback_data=f"admin_view_ticket_{t[0]}")] for t in tickets[:20]]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")])
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "admin_delete_ticket")
async def admin_delete_ticket_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    await call.message.edit_text("🗑 *Введите ID тикета для удаления:*", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_ticket_id)
    await state.update_data(action="admin_delete")

@dp.callback_query(F.data == "ticket_helper")
async def ticket_helper_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    await call.message.edit_text("👤 *Введите ID тикета для просмотра ответственного:*", parse_mode="Markdown")
    await state.set_state(TicketStates.waiting_ticket_id)
    await state.update_data(action="ticket_helper")

@dp.callback_query(F.data.startswith("admin_view_ticket_"))
async def admin_view_ticket(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    ticket_id = int(call.data.split("_")[3])
    
    cursor.execute('SELECT * FROM tickets WHERE id = 
