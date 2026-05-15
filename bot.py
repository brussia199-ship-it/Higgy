import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
import os

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8750633312:AAEBwJ2dyno_elQFUPNBeogYWSWj43pvCTQ"
ADMIN_ID = 7673683792
IMAGE_PATH = "support.jpg"  # Положите картинку в папку с ботом

# ========== БАЗА ДАННЫХ ==========
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
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            user_id INTEGER,
            message TEXT,
            is_from_helper INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, is_helper) VALUES (?, ?, ?)', 
                   (ADMIN_ID, 'admin', 1))
    
    conn.commit()
    print("База данных готова")

init_db()

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== СОСТОЯНИЯ ==========
class TicketStates(StatesGroup):
    waiting_question = State()
    waiting_answer = State()
    waiting_ticket_id = State()
    waiting_helper_id = State()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def send_with_image(chat_id, text, reply_markup=None):
    if os.path.exists(IMAGE_PATH):
        photo = FSInputFile(IMAGE_PATH)
        await bot.send_photo(chat_id=chat_id, photo=photo, caption=text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)

def is_helper(user_id):
    cursor.execute('SELECT is_helper FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row and row[0] == 1

def user_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♦ Создать тикет", callback_data="create_ticket")],
        [InlineKeyboardButton(text="♦ Мои тикеты", callback_data="my_tickets")],
        [InlineKeyboardButton(text="♦ Статус тикета", callback_data="ticket_status")]
    ])

def helper_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♦ Открытые тикеты", callback_data="open_tickets")],
        [InlineKeyboardButton(text="♦ Мои тикеты", callback_data="my_helper_tickets")],
        [InlineKeyboardButton(text="♦ Закрыть тикет", callback_data="close_ticket")],
        [InlineKeyboardButton(text="♦ Открыть тикет", callback_data="reopen_ticket")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♦ Список хелперов", callback_data="list_helpers")],
        [InlineKeyboardButton(text="♦ Добавить хелпера", callback_data="add_helper")],
        [InlineKeyboardButton(text="♦ Удалить хелпера", callback_data="remove_helper")],
        [InlineKeyboardButton(text="♦ Все тикеты", callback_data="all_tickets")],
        [InlineKeyboardButton(text="♦ Удалить тикет", callback_data="admin_delete_ticket")],
        [InlineKeyboardButton(text="♦ Ответственный", callback_data="ticket_helper")]
    ])

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ ФУНКЦИИ ==========
@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or str(user_id)
    
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    
    await send_with_image(
        msg.chat.id,
        "♦ *Система поддержки* ♦\n\n"
        "• Создайте тикет с вашим вопросом\n"
        "• Хелпер ответит вам в ближайшее время\n"
        "• Отслеживайте статус в разделе «Мои тикеты»",
        reply_markup=user_menu()
    )

@dp.callback_query(F.data == "create_ticket")
async def create_ticket(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("♦ *Опишите вашу проблему:*\n\n(Максимум 500 символов)")
    await state.set_state(TicketStates.waiting_question)

@dp.message(TicketStates.waiting_question)
async def save_ticket(msg: types.Message, state: FSMContext):
    if len(msg.text) > 500:
        await msg.answer("♦ Слишком длинное сообщение! Максимум 500 символов.")
        return
    
    user_id = msg.from_user.id
    username = msg.from_user.username or str(user_id)
    question = msg.text
    now = datetime.now()
    
    cursor.execute('''
        INSERT INTO tickets (user_id, username, question, status, created_at, updated_at)
        VALUES (?, ?, ?, 'open', ?, ?)
    ''', (user_id, username, question, now, now))
    conn.commit()
    
    ticket_id = cursor.lastrowid
    
    await msg.answer(
        f"♦ *Тикет #{ticket_id} создан!*\n\n"
        f"Хелпер ответит вам в ближайшее время.\n"
        f"Вы можете отслеживать статус в разделе «Мои тикеты»",
        reply_markup=user_menu()
    )
    
    # Уведомляем хелперов
    cursor.execute('SELECT user_id FROM users WHERE is_helper = 1')
    helpers = cursor.fetchall()
    for helper in helpers:
        try:
            await bot.send_message(
                helper[0],
                f"♦ *Новый тикет!*\n\n"
                f"▪ ID: #{ticket_id}\n"
                f"▪ От: @{username}\n"
                f"▪ Вопрос: {question[:100]}...",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="♦ Ответить", callback_data=f"answer_ticket_{ticket_id}")]
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
    
    text = "♦ *Ваши тикеты:*\n\n"
    for t in tickets:
        status_icon = "🟢" if t[1] == 'open' else "🔴"
        text += f"{status_icon} #{t[0]} | {t[1]} | {t[2][:16]}\n"
    
    text += "\n♦ Нажмите на ID тикета для просмотра"
    
    buttons = [[InlineKeyboardButton(text=f"▪ Тикет #{t[0]}", callback_data=f"view_ticket_{t[0]}")] for t in tickets]
    buttons.append([InlineKeyboardButton(text="♦ Назад", callback_data="back_to_user")])
    
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "ticket_status")
async def ticket_status_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("♦ *Введите ID тикета:*")
    await state.set_state(TicketStates.waiting_ticket_id)

@dp.message(TicketStates.waiting_ticket_id)
async def show_ticket_status(msg: types.Message, state: FSMContext):
    try:
        ticket_id = int(msg.text)
        user_id = msg.from_user.id
        
        cursor.execute('SELECT * FROM tickets WHERE id = ? AND user_id = ?', (ticket_id, user_id))
        ticket = cursor.fetchone()
        
        if not ticket:
            await msg.answer("♦ Тикет не найден или это не ваш тикет!")
            await state.clear()
            return
        
        text = f"♦ *Тикет #{ticket[0]}*\n\n"
        text += f"▪ Вопрос: {ticket[3]}\n"
        text += f"▪ Статус: {'🟢 Открыт' if ticket[4] == 'open' else '🔴 Закрыт'}\n"
        text += f"▪ Создан: {ticket[6][:16]}\n"
        
        if ticket[5]:
            cursor.execute('SELECT username FROM users WHERE user_id = ?', (ticket[5],))
            helper = cursor.fetchone()
            text += f"▪ Хелпер: @{helper[0] if helper else ticket[5]}\n"
        
        cursor.execute('SELECT message, is_from_helper, created_at FROM messages WHERE ticket_id = ? ORDER BY created_at', (ticket_id,))
        messages = cursor.fetchall()
        
        if messages:
            text += f"\n♦ *Переписка:*\n"
            for m in messages:
                sender = "Хелпер" if m[1] else "Вы"
                text += f"▪ {sender} [{m[2][11:16]}]: {m[0][:100]}\n"
        
        await msg.answer(text, parse_mode="Markdown", reply_markup=user_menu())
        await state.clear()
        
    except ValueError:
        await msg.answer("♦ Введите число (ID тикета)!")
        await state.clear()

@dp.callback_query(F.data.startswith("view_ticket_"))
async def view_ticket(call: types.CallbackQuery):
    ticket_id = int(call.data.split("_")[2])
    user_id = call.from_user.id
    
    cursor.execute('SELECT * FROM tickets WHERE id = ? AND user_id = ?', (ticket_id, user_id))
    ticket = cursor.fetchone()
    
    if not ticket:
        await call.answer("Тикет не найден!", show_alert=True)
        return
    
    text = f"♦ *Тикет #{ticket[0]}*\n\n"
    text += f"▪ Вопрос: {ticket[3]}\n"
    text += f"▪ Статус: {'🟢 Открыт' if ticket[4] == 'open' else '🔴 Закрыт'}\n"
    text += f"▪ Создан: {ticket[6][:16]}\n"
    
    cursor.execute('SELECT message, is_from_helper, created_at FROM messages WHERE ticket_id = ? ORDER BY created_at', (ticket_id,))
    messages = cursor.fetchall()
    
    if messages:
        text += f"\n♦ *Переписка:*\n"
        for m in messages:
            sender = "Хелпер" if m[1] else "Вы"
            text += f"▪ {sender} [{m[2][11:16]}]: {m[0][:150]}\n"
    
    if ticket[4] == 'open':
        buttons = [[InlineKeyboardButton(text="♦ Ответить", callback_data=f"user_answer_{ticket_id}")]]
        buttons.append([InlineKeyboardButton(text="♦ Назад", callback_data="my_tickets")])
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="♦ Назад", callback_data="my_tickets")]
        ]))

@dp.callback_query(F.data.startswith("user_answer_"))
async def user_answer_start(call: types.CallbackQuery, state: FSMContext):
    ticket_id = int(call.data.split("_")[2])
    await state.update_data(ticket_id=ticket_id)
    await call.message.edit_text("♦ *Введите ваш ответ:*")
    await state.set_state(TicketStates.waiting_answer)

@dp.message(TicketStates.waiting_answer)
async def user_send_answer(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data['ticket_id']
    user_id = msg.from_user.id
    message_text = msg.text
    
    cursor.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    
    if not ticket or ticket[4] != 'open':
        await msg.answer("♦ Тикет закрыт! Вы не можете отвечать.")
        await state.clear()
        return
    
    cursor.execute('''
        INSERT INTO messages (ticket_id, user_id, message, is_from_helper, created_at)
        VALUES (?, ?, ?, 0, ?)
    ''', (ticket_id, user_id, message_text, datetime.now()))
    conn.commit()
    
    await msg.answer("♦ Сообщение отправлено хелперу!", reply_markup=user_menu())
    
    helper_id = ticket[5]
    if helper_id:
        try:
            await bot.send_message(
                helper_id,
                f"♦ *Новый ответ в тикете #{ticket_id}*\n\n"
                f"▪ От пользователя @{msg.from_user.username or user_id}\n"
                f"▪ Сообщение: {message_text[:200]}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="♦ Ответить", callback_data=f"answer_ticket_{ticket_id}")]
                ])
            )
        except:
            pass
    
    await state.clear()

# ========== ХЕЛПЕРСКИЕ ФУНКЦИИ ==========
@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    user_id = msg.from_user.id
    if is_helper(user_id) or user_id == ADMIN_ID:
        await send_with_image(msg.chat.id, "♦ *Панель хелпера*", reply_markup=helper_menu())
    else:
        await msg.answer("♦ У вас нет доступа к панели хелпера!")

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
    
    text = "♦ *Открытые тикеты:*\n\n"
    for t in tickets:
        text += f"▪ #{t[0]} | @{t[1]} | {t[3][:16]}\n"
        text += f"   {t[2][:80]}...\n\n"
    
    buttons = [[InlineKeyboardButton(text=f"▪ Ответить на #{t[0]}", callback_data=f"answer_ticket_{t[0]}")] for t in tickets]
    buttons.append([InlineKeyboardButton(text="♦ Назад", callback_data="back_to_helper")])
    
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

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
    
    text = "♦ *Ваши тикеты:*\n\n"
    for t in tickets:
        status = "🟢" if t[3] == 'open' else "🔴"
        text += f"{status} #{t[0]} | @{t[1]} | {t[4][:16]}\n"
    
    buttons = [[InlineKeyboardButton(text=f"▪ Ответить на #{t[0]}", callback_data=f"answer_ticket_{t[0]}")] for t in tickets]
    buttons.append([InlineKeyboardButton(text="♦ Назад", callback_data="back_to_helper")])
    
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

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
    await call.message.edit_text(f"♦ *Отвечаем на тикет #{ticket_id}*\n\nВведите ваш ответ:")
    await state.set_state(TicketStates.waiting_answer)

@dp.message(TicketStates.waiting_answer)
async def helper_send_answer(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data['ticket_id']
    helper_id = msg.from_user.id
    message_text = msg.text
    
    cursor.execute('SELECT user_id, status FROM tickets WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    
    if not ticket or ticket[1] != 'open':
        await msg.answer("♦ Тикет закрыт!")
        await state.clear()
        return
    
    cursor.execute('''
        INSERT INTO messages (ticket_id, user_id, message, is_from_helper, created_at)
        VALUES (?, ?, ?, 1, ?)
    ''', (ticket_id, helper_id, message_text, datetime.now()))
    conn.commit()
    
    cursor.execute('UPDATE tickets SET updated_at = ? WHERE id = ?', (datetime.now(), ticket_id))
    conn.commit()
    
    await msg.answer(f"♦ Ответ отправлен пользователю!", reply_markup=helper_menu())
    
    user_id = ticket[0]
    try:
        await bot.send_message(
            user_id,
            f"♦ *Ответ на ваш тикет #{ticket_id}*\n\n"
            f"▪ Сообщение: {message_text[:200]}\n\n"
            f"Вы можете ответить в разделе «Мои тикеты»",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="♦ Посмотреть тикет", callback_data=f"view_ticket_{ticket_id}")]
            ])
        )
    except:
        pass
    
    await state.clear()

@dp.callback_query(F.data == "close_ticket")
async def close_ticket_start(call: types.CallbackQuery, state: FSMContext):
    if not is_helper(call.from_user.id) and call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    await call.message.edit_text("♦ *Введите ID тикета для закрытия:*")
    await state.set_state(TicketStates.waiting_ticket_id)

@dp.callback_query(F.data == "reopen_ticket")
async def reopen_ticket_start(call: types.CallbackQuery, state: FSMContext):
    if not is_helper(call.from_user.id) and call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    await call.message.edit_text("♦ *Введите ID тикета для открытия:*")
    await state.set_state(TicketStates.waiting_ticket_id)

@dp.message(TicketStates.waiting_ticket_id)
async def process_ticket_action(msg: types.Message, state: FSMContext):
    try:
        ticket_id = int(msg.text)
        
        cursor.execute('SELECT status FROM tickets WHERE id = ?', (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            await msg.answer("♦ Тикет не найден!")
            await state.clear()
            return
        
        new_status = 'closed' if ticket[0] == 'open' else 'open'
        cursor.execute('UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?', (new_status, datetime.now(), ticket_id))
        conn.commit()
        
        action = "закрыт" if new_status == 'closed' else "открыт"
        await msg.answer(f"♦ Тикет #{ticket_id} {action}!", reply_markup=helper_menu())
        
        cursor.execute('SELECT user_id FROM tickets WHERE id = ?', (ticket_id,))
        user = cursor.fetchone()
        if user:
            try:
                await bot.send_message(
                    user[0],
                    f"♦ Ваш тикет #{ticket_id} был {action} хелпером."
                )
            except:
                pass
        
        await state.clear()
        
    except ValueError:
        await msg.answer("♦ Введите число (ID тикета)!")
        await state.clear()

# ========== АДМИНСКИЕ ФУНКЦИИ ==========
@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await send_with_image(msg.chat.id, "♦ *Панель администратора*", reply_markup=admin_menu())
    else:
        await msg.answer("♦ Нет доступа!")

@dp.callback_query(F.data == "list_helpers")
async def list_helpers(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа!", show_alert=True)
        return
    
    cursor.execute('SELECT user_id, username FROM users WHERE is_helper = 1')
    
