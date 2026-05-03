import sqlite3

def init_db():
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    # Table សម្រាប់រក្សាទុកភាសារបស់អ្នកប្រើប្រាស់
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'km'
        )''')
    # Table សម្រាប់ស្តុក License
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            license_key TEXT,
            price REAL,
            is_sold INTEGER DEFAULT 0,
            buyer_id INTEGER DEFAULT NULL
        )''')
    conn.commit()
    conn.close()

def set_user_lang(user_id, lang):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)', (user_id, lang))
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'km'

def add_multiple_keys(product_name, keys_list, price):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    for key in keys_list:
        if key.strip():
            cursor.execute('INSERT INTO licenses (product_name, license_key, price) VALUES (?, ?, ?)', 
                           (product_name, key.strip(), price))
    conn.commit()
    conn.close()

def get_distinct_products_in_stock():
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute('SELECT product_name, price, COUNT(*) FROM licenses WHERE is_sold = 0 GROUP BY product_name')
    res = cursor.fetchall()
    conn.close()
    return res

def get_available_key(product_name):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, license_key, price FROM licenses WHERE product_name = ? AND is_sold = 0 LIMIT 1', (product_name,))
    result = cursor.fetchone()
    conn.close()
    return result

def mark_as_sold(key_id, buyer_id):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE licenses SET is_sold = 1, buyer_id = ? WHERE id = ?', (buyer_id, key_id))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM licenses WHERE buyer_id = ?', (user_id,))
    res = cursor.fetchone()[0]
    conn.close()
    return res

def get_user_history(user_id):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute('SELECT product_name, license_key FROM licenses WHERE buyer_id = ?', (user_id,))
    res = cursor.fetchall()
    conn.close()
    return res