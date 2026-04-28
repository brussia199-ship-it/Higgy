import mysql.connector
from mysql.connector import pooling
from config import MYSQL_CONFIG

db_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=10, **MYSQL_CONFIG)

def get_connection():
    return db_pool.get_connection()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(100),
            balance DECIMAL(10,2) DEFAULT 0,
            role ENUM('user', 'seller', 'admin') DEFAULT 'user'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            seller_id BIGINT,
            name VARCHAR(255),
            description TEXT,
            price DECIMAL(10,2),
            contact VARCHAR(255),
            is_top BOOLEAN DEFAULT FALSE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seller_requests (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(100),
            status ENUM('pending', 'accepted', 'declined') DEFAULT 'pending'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT,
            amount DECIMAL(10,2),
            status ENUM('pending', 'done') DEFAULT 'pending'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT,
            buyer_id BIGINT,
            seller_id BIGINT,
            contact VARCHAR(255),
            status ENUM('active', 'completed') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT,
            amount DECIMAL(10,2),
            cryptobot_invoice_id VARCHAR(100),
            status ENUM('pending', 'paid') DEFAULT 'pending'
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

def register_user(user_id, username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT IGNORE INTO users (user_id, username) VALUES (%s, %s)", (user_id, username))
    conn.commit()
    cursor.close()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def update_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def set_role(user_id, role):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = %s WHERE user_id = %s", (role, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def add_product(seller_id, name, description, price, contact):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (seller_id, name, description, price, contact) VALUES (%s, %s, %s, %s, %s)",
        (seller_id, name, description, price, contact)
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_products(seller_id=None, only_top=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if seller_id:
        cursor.execute("SELECT * FROM products WHERE seller_id = %s ORDER BY is_top DESC", (seller_id,))
    elif only_top:
        cursor.execute("SELECT * FROM products WHERE is_top = 1 ORDER BY id DESC")
    else:
        cursor.execute("SELECT * FROM products ORDER BY is_top DESC")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return products

def delete_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    cursor.close()
    conn.close()

def promote_to_top(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET is_top = 1 WHERE id = %s", (product_id,))
    conn.commit()
    cursor.close()
    conn.close()

def get_product(product_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return product

def add_seller_request(user_id, username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO seller_requests (user_id, username) VALUES (%s, %s) ON DUPLICATE KEY UPDATE status='pending'", (user_id, username))
    conn.commit()
    cursor.close()
    conn.close()

def get_pending_requests():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM seller_requests WHERE status = 'pending'")
    requests = cursor.fetchall()
    cursor.close()
    conn.close()
    return requests

def accept_seller_request(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE seller_requests SET status = 'accepted' WHERE user_id = %s", (user_id,))
    cursor.execute("UPDATE users SET role = 'seller' WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

def create_deal(product_id, buyer_id, seller_id, contact):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO deals (product_id, buyer_id, seller_id, contact) VALUES (%s, %s, %s, %s)",
        (product_id, buyer_id, seller_id, contact)
    )
    deal_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return deal_id

def complete_deal(deal_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE deals SET status = 'completed' WHERE id = %s", (deal_id,))
    conn.commit()
    cursor.close()
    conn.close()

def save_invoice(user_id, amount, cryptobot_invoice_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO invoices (user_id, amount, cryptobot_invoice_id) VALUES (%s, %s, %s)",
        (user_id, amount, cryptobot_invoice_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

def mark_invoice_paid(cryptobot_invoice_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE invoices SET status = 'paid' WHERE cryptobot_invoice_id = %s",
        (cryptobot_invoice_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_pending_invoice(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM invoices WHERE user_id = %s AND status = 'pending' ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    inv = cursor.fetchone()
    cursor.close()
    conn.close()
    return inv