import sqlite3
import config


def connect_db():
    return sqlite3.connect(config.DATABASE_NAME, check_same_thread=False)


def create_tables(conn):
    cursor = conn.cursor()

    # Создание таблицы пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance REAL DEFAULT 0,
        total_topups REAL DEFAULT 0,
        total_topup_count INTEGER DEFAULT 0,
        total_purchases INTEGER DEFAULT 0
    )
    ''')

    # Создание таблицы товаров (основная информация)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price REAL,
        description TEXT,
        total_keys INTEGER DEFAULT 0,
        sold_keys INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT 1
    )
    ''')

    # Создание таблицы ключей (уникальные ключи)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        key_value TEXT UNIQUE,
        is_sold BOOLEAN DEFAULT 0,
        sold_to INTEGER,
        sold_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')

    # Создание таблицы покупок
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        key_id INTEGER,
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        price REAL,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (product_id) REFERENCES products (id),
        FOREIGN KEY (key_id) REFERENCES product_keys (id)
    )
    ''')

    conn.commit()


def initialize_prebuilt_products(conn):
    cursor = conn.cursor()

    for product in config.PREBUILT_PRODUCTS:
        # Проверяем, существует ли товар
        cursor.execute('SELECT id FROM products WHERE name = ?', (product['name'],))
        existing = cursor.fetchone()

        if not existing:
            # Добавляем товар
            cursor.execute('''
                INSERT INTO products (name, price, description, total_keys, sold_keys, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                product['name'],
                product['price'],
                product['description'],
                product['initial_quantity'],
                0,
                1
            ))
            product_id = cursor.lastrowid

            # Добавляем заглушки для ключей
            for i in range(product['initial_quantity']):
                cursor.execute('''
                    INSERT INTO product_keys (product_id, key_value)
                    VALUES (?, ?)
                ''', (product_id, f"KEY_{product['name']}_{i + 1:03d}"))

    conn.commit()


def update_tables(conn):
    cursor = conn.cursor()

    # Добавление недостающих столбцов в таблицу пользователей
    cursor.execute('PRAGMA table_info(users)')
    columns = [info[1] for info in cursor.fetchall()]
    if 'total_topups' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN total_topups REAL DEFAULT 0')
    if 'total_topup_count' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN total_topup_count INTEGER DEFAULT 0')
    if 'total_purchases' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN total_purchases INTEGER DEFAULT 0')

    conn.commit()


# Инициализация базы данных
conn = connect_db()
create_tables(conn)
update_tables(conn)
initialize_prebuilt_products(conn)