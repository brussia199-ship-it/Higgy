import sqlite3
from config import ADMIN_IDS

DB_PATH = "shop_bot.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            role TEXT DEFAULT 'user'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            name TEXT,
            description TEXT,
            price REAL,
            contact TEXT,
            is_top INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seller_requests (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            buyer_id INTEGER,
            seller_id INTEGER,
            contact TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            cryptobot_invoice_id TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    conn.commit()
    conn.close()

# === Пользователи ===
def register_user(user_id, username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "username": row[1], "balance": row[2], "role": row[3]}
    return None

def update_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def set_role(user_id, role):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
    conn.commit()
    conn.close()

# === Товары ===
def add_product(seller_id, name, description, price, contact):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (seller_id, name, description, price, contact) VALUES (?, ?, ?, ?, ?)",
        (seller_id, name, description, price, contact)
    )
    conn.commit()
    conn.close()

def get_products(seller_id=None, only_top=False):
    conn = get_connection()
    cursor = conn.cursor()
    if seller_id:
        cursor.execute("SELECT * FROM products WHERE seller_id = ? ORDER BY is_top DESC", (seller_id,))
    elif only_top:
        cursor.execute("SELECT * FROM products WHERE is_top = 1 ORDER BY id DESC")
    else:
        cursor.execute("SELECT * FROM products ORDER BY is_top DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "seller_id": r[1], "name": r[2], "description": r[3], "price": r[4], "contact": r[5], "is_top": r[6]} for r in rows]

def delete_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def promote_to_top(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET is_top = 1 WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def get_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "seller_id": row[1], "name": row[2], "description": row[3], "price": row[4], "contact": row[5], "is_top": row[6]}
    return None

# === Заявки ===
def add_seller_request(user_id, username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO seller_requests (user_id, username, status) VALUES (?, ?, 'pending')", (user_id, username))
    conn.commit()
    conn.close()

def get_pending_requests():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM seller_requests WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return [{"user_id": r[0], "username": r[1], "status": r[2]} for r in rows]

def accept_seller_request(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE seller_requests SET status = 'accepted' WHERE user_id = ?", (user_id,))
    cursor.execute("UPDATE users SET role = 'seller' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# === Сделки ===
def create_deal(product_id, buyer_id, seller_id, contact):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO deals (product_id, buyer_id, seller_id, contact) VALUES (?, ?, ?, ?)",
        (product_id, buyer_id, seller_id, contact)
    )
    deal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return deal_id

def complete_deal(deal_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE deals SET status = 'completed' WHERE id = ?", (deal_id,))
    conn.commit()
    conn.close()

def get_active_deal(buyer_id, product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM deals WHERE buyer_id = ? AND product_id = ? AND status = 'active'",
        (buyer_id, product_id)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "product_id": row[1], "buyer_id": row[2], "seller_id": row[3], "contact": row[4], "status": row[5]}
    return None

# === Инвойсы ===
def save_invoice(user_id, amount, cryptobot_invoice_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO invoices (user_id, amount, cryptobot_invoice_id) VALUES (?, ?, ?)",
        (user_id, amount, cryptobot_invoice_id)
    )
    conn.commit()
    conn.close()

def mark_invoice_paid(cryptobot_invoice_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE invoices SET status = 'paid' WHERE cryptobot_invoice_id = ?",
        (cryptobot_invoice_id,)
    )
    conn.commit()
    conn.close()

def get_pending_invoice(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM invoices WHERE user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "user_id": row[1], "amount": row[2], "cryptobot_invoice_id": row[3], "status": row[4]}
    return None