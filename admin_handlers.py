from telebot import types
import config
import database
import telebot

conn = database.connect_db()
cursor = conn.cursor()

admin_mode = {}
product_step = {}
users_page = {}


def escape_markdown(text):
    escape_chars = r'\*_`['
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)


def send_main_menu(bot, chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    profile_button = types.KeyboardButton("👤 Профиль")
    products_button = types.KeyboardButton("🛍️ Товары")
    markup.add(profile_button, products_button)
    bot.send_message(chat_id, "Вы в главном меню.", reply_markup=markup)


def show_users_page(bot, chat_id, page_number):
    conn = database.connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    if total_users == 0:
        bot.send_message(chat_id, "Пользователей нет.")
        return

    cursor.execute(
        'SELECT id, username, first_name, balance, total_topups, total_purchases FROM users LIMIT 10 OFFSET ?',
        ((page_number - 1) * 10,))
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    users_info = "\n\n".join([
        f"🆔ID: `{escape_markdown(str(user[0]))}`\n👤 Юзернейм: @{escape_markdown(str(user[1]))}\n📛 Имя: {escape_markdown(str(user[2]))}\n💰 Баланс: {user[3]:.2f} руб\n💸 Сумма пополнений: {user[4]:.2f} руб\n🛒 Количество покупок: {user[5]}"
        for user in users
    ])

    markup = types.InlineKeyboardMarkup()
    if page_number > 1:
        markup.add(types.InlineKeyboardButton(text="⏪ Влево", callback_data=f'users_page_{page_number - 1}'))
    if (page_number * 10) < total_users:
        markup.add(types.InlineKeyboardButton(text="⏩ Вправо", callback_data=f'users_page_{page_number + 1}'))

    bot.send_message(chat_id, f"Количество пользователей: {total_users}\n\n{users_info}", reply_markup=markup,
                     parse_mode='Markdown')


def setup_admin_handlers(bot):
    @bot.message_handler(commands=['admin'])
    def admin_panel(message):
        if message.from_user.id == config.ADMIN_ID:
            admin_mode[message.from_user.id] = True
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            broadcast_button = types.KeyboardButton("📢 Рассылка")
            change_balance_button = types.KeyboardButton("💰 Изменить баланс")
            user_count_button = types.KeyboardButton("👥 Пользователи")
            manage_keys_button = types.KeyboardButton("🔑 Управление ключами")
            add_product_button = types.KeyboardButton("➕ Новый товар")
            stats_button = types.KeyboardButton("📊 Статистика")
            exit_button = types.KeyboardButton("❌ Выйти")
            markup.add(broadcast_button, change_balance_button, user_count_button, manage_keys_button)
            markup.add(add_product_button, stats_button, exit_button)
            bot.send_message(message.chat.id, "Админ панель:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")

    @bot.message_handler(commands=['off'])
    def exit_admin_panel(message):
        if message.from_user.id in admin_mode:
            del admin_mode[message.from_user.id]
        send_main_menu(bot, message.chat.id)
        bot.send_message(message.chat.id, "Вы вышли из админ панели.")

    @bot.message_handler(func=lambda message: message.from_user.id in admin_mode)
    def admin_actions(message):
        chat_id = message.chat.id

        if message.text == "📢 Рассылка":
            bot.send_message(chat_id, "Введите текст для рассылки:")
            bot.register_next_step_handler(message, broadcast_message)

        elif message.text == "💰 Изменить баланс":
            bot.send_message(chat_id, "Введите ID пользователя, чей баланс вы хотите изменить:")
            bot.register_next_step_handler(message, get_user_balance)

        elif message.text == "👥 Пользователи":
            users_page[chat_id] = 1
            show_users_page(bot, chat_id, users_page[chat_id])

        elif message.text == "🔑 Управление ключами":
            show_products_for_management(bot, chat_id)

        elif message.text == "➕ Новый товар":
            bot.send_message(chat_id, "Введите имя нового товара:")
            bot.register_next_step_handler(message, process_new_product_name)

        elif message.text == "📊 Статистика":
            show_statistics(bot, chat_id)

        elif message.text == "❌ Выйти":
            exit_admin_panel(message)

        else:
            bot.send_message(message.chat.id, "Неизвестная команда. Пожалуйста, выберите одну из опций.")

    def show_products_for_management(bot, chat_id):
        conn = database.connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, total_keys, sold_keys FROM products WHERE is_active = 1')
        products = cursor.fetchall()
        cursor.close()
        conn.close()

        if not products:
            bot.send_message(chat_id, "Товаров нет.")
            return

        markup = types.InlineKeyboardMarkup()
        for product in products:
            available = product[2] - product[3]
            markup.add(types.InlineKeyboardButton(
                text=f"{product[1]} (Доступно: {available})",
                callback_data=f'manage_product_{product[0]}'
            ))

        markup.add(types.InlineKeyboardButton(text="🔙 Назад", callback_data='back_to_admin'))
        bot.send_message(chat_id, "Выберите товар для управления ключами:", reply_markup=markup)

    def show_statistics(bot, chat_id):
        conn = database.connect_db()
        cursor = conn.cursor()

        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        cursor.execute('SELECT SUM(balance) FROM users')
        total_balance = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(total_topups) FROM users')
        total_topups = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(price) FROM purchases')
        total_sales = cursor.fetchone()[0] or 0

        # Статистика по товарам
        cursor.execute('''
            SELECT p.name, COUNT(pk.id) as total, 
                   SUM(CASE WHEN pk.is_sold = 1 THEN 1 ELSE 0 END) as sold,
                   SUM(CASE WHEN pk.is_sold = 0 THEN 1 ELSE 0 END) as available
            FROM products p
            LEFT JOIN product_keys pk ON p.id = pk.product_id
            GROUP BY p.id
        ''')
        products_stats = cursor.fetchall()

        cursor.close()
        conn.close()

        stats_text = f"""📊 *Общая статистика*
👥 Пользователей: {total_users}
💰 Общий баланс: {total_balance:.2f} руб
💸 Общие пополнения: {total_topups:.2f} руб
🛒 Общие продажи: {total_sales:.2f} руб

*Статистика по товарам:*
"""
        for product in products_stats:
            stats_text += f"\n{product[0]}:"
            stats_text += f"\n  Всего ключей: {product[1]}"
            stats_text += f"\n  Продано: {product[2]}"
            stats_text += f"\n  Доступно: {product[3]}"

        bot.send_message(chat_id, stats_text, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'back_to_admin')
    def back_to_admin(call):
        admin_actions(call.message)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('manage_product_'))
    def manage_product(call):
        product_id = int(call.data.split('_')[2])
        conn = database.connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT name, total_keys, sold_keys FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        cursor.close()
        conn.close()

        if product:
            available = product[1] - product[2]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                text="📥 Добавить ключи",
                callback_data=f'add_keys_{product_id}'
            ))
            markup.add(types.InlineKeyboardButton(
                text="📝 Добавить ключи списком",
                callback_data=f'add_keys_list_{product_id}'
            ))
            markup.add(types.InlineKeyboardButton(
                text="📤 Экспортировать ключи",
                callback_data=f'export_keys_{product_id}'
            ))
            markup.add(types.InlineKeyboardButton(
                text="🔙 Назад к товарам",
                callback_data='back_to_products_manage'
            ))

            bot.send_message(
                call.message.chat.id,
                f"Управление товаром: *{product[0]}*\n\n"
                f"Всего ключей: {product[1]}\n"
                f"Продано: {product[2]}\n"
                f"Доступно: {available}",
                reply_markup=markup,
                parse_mode='Markdown'
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('back_to_products_manage'))
    def back_to_products_manage(call):
        show_products_for_management(bot, call.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('add_keys_'))
    def add_keys(call):
        product_id = int(call.data.split('_')[2])
        bot.send_message(call.message.chat.id,
                         "Введите количество ключей для добавления (будут сгенерированы автоматически):")
        bot.register_next_step_handler(call.message, process_add_keys, product_id)

    def process_add_keys(message, product_id):
        try:
            count = int(message.text)
            if count <= 0 or count > 1000:
                bot.send_message(message.chat.id, "Введите число от 1 до 1000.")
                return

            conn = database.connect_db()
            cursor = conn.cursor()

            # Получаем информацию о товаре
            cursor.execute('SELECT name FROM products WHERE id = ?', (product_id,))
            product_name = cursor.fetchone()[0]

            # Добавляем ключи
            added = 0
            for i in range(count):
                try:
                    # Генерируем уникальный ключ
                    import uuid
                    key_value = f"{product_name}_{uuid.uuid4().hex[:12].upper()}"

                    cursor.execute(
                        'INSERT INTO product_keys (product_id, key_value) VALUES (?, ?)',
                        (product_id, key_value)
                    )
                    added += 1
                except sqlite3.IntegrityError:
                    # Если ключ неуникальный, пропускаем
                    continue

            # Обновляем общее количество ключей
            cursor.execute(
                'UPDATE products SET total_keys = total_keys + ? WHERE id = ?',
                (added, product_id)
            )

            conn.commit()
            cursor.close()
            conn.close()

            bot.send_message(message.chat.id, f"✅ Добавлено {added} ключей для товара.")

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректное число.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('add_keys_list_'))
    def add_keys_list(call):
        product_id = int(call.data.split('_')[3])
        bot.send_message(call.message.chat.id,
                         "Отправьте список ключей (каждый ключ с новой строки):")
        bot.register_next_step_handler(call.message, process_keys_list, product_id)

    def process_keys_list(message, product_id):
        if not message.text:
            bot.send_message(message.chat.id, "❌ Отправьте текстовое сообщение с ключами.")
            return

        keys = [key.strip() for key in message.text.split('\n') if key.strip()]

        conn = database.connect_db()
        cursor = conn.cursor()

        # Получаем информацию о товаре
        cursor.execute('SELECT name FROM products WHERE id = ?', (product_id,))
        product_name = cursor.fetchone()[0]

        added = 0
        duplicates = 0

        for key in keys:
            try:
                cursor.execute(
                    'INSERT INTO product_keys (product_id, key_value) VALUES (?, ?)',
                    (product_id, key)
                )
                added += 1
            except sqlite3.IntegrityError:
                duplicates += 1

        # Обновляем общее количество ключей
        if added > 0:
            cursor.execute(
                'UPDATE products SET total_keys = total_keys + ? WHERE id = ?',
                (added, product_id)
            )

        conn.commit()
        cursor.close()
        conn.close()

        bot.send_message(
            message.chat.id,
            f"✅ Добавлено ключей: {added}\n"
            f"❌ Дубликатов: {duplicates}"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('export_keys_'))
    def export_keys(call):
        product_id = int(call.data.split('_')[2])
        conn = database.connect_db()
        cursor = conn.cursor()

        # Получаем непроданные ключи
        cursor.execute('''
            SELECT key_value FROM product_keys 
            WHERE product_id = ? AND is_sold = 0 
            ORDER BY id
        ''', (product_id,))

        keys = cursor.fetchall()
        cursor.close()
        conn.close()

        if not keys:
            bot.send_message(call.message.chat.id, "❌ Нет доступных ключей для экспорта.")
            return

        # Формируем текст с ключами
        keys_text = "\n".join([key[0] for key in keys])

        # Если слишком длинное сообщение, отправляем файлом
        if len(keys_text) > 4000:
            import io
            bio = io.BytesIO(keys_text.encode('utf-8'))
            bio.name = f'keys_{product_id}.txt'
            bot.send_document(call.message.chat.id, bio)
        else:
            bot.send_message(call.message.chat.id, f"Ключи:\n\n{keys_text}")

    def process_new_product_name(message):
        name = message.text.strip()
        if not name:
            bot.send_message(message.chat.id, "❌ Имя товара не может быть пустым.")
            return

        conn = database.connect_db()
        cursor = conn.cursor()

        # Проверяем, существует ли товар
        cursor.execute('SELECT id FROM products WHERE name = ?', (name,))
        if cursor.fetchone():
            bot.send_message(message.chat.id, "❌ Товар с таким именем уже существует.")
            cursor.close()
            conn.close()
            return

        cursor.close()
        conn.close()

        # Сохраняем имя и запрашиваем цену
        product_step[message.chat.id] = {'name': name}
        bot.send_message(message.chat.id, "Введите цену товара (в рублях):")
        bot.register_next_step_handler(message, process_new_product_price)

    def process_new_product_price(message):
        try:
            price = float(message.text)
            if price <= 0:
                bot.send_message(message.chat.id, "❌ Цена должна быть больше 0.")
                return

            product_step[message.chat.id]['price'] = price
            bot.send_message(message.chat.id, "Введите описание товара:")
            bot.register_next_step_handler(message, process_new_product_description)

        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректную цену.")
            bot.register_next_step_handler(message, process_new_product_price)

    def process_new_product_description(message):
        description = message.text.strip()
        if not description:
            description = "Без описания"

        product_step[message.chat.id]['description'] = description

        # Создаем товар в базе данных
        conn = database.connect_db()
        cursor = conn.cursor()

        product_data = product_step[message.chat.id]
        cursor.execute('''
            INSERT INTO products (name, price, description, total_keys, sold_keys, is_active)
            VALUES (?, ?, ?, 0, 0, 1)
        ''', (
            product_data['name'],
            product_data['price'],
            product_data['description']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        # Очищаем временные данные
        if message.chat.id in product_step:
            del product_step[message.chat.id]

        bot.send_message(message.chat.id, f"✅ Товар '{product_data['name']}' успешно добавлен!")

    def broadcast_message(message):
        if message.text.startswith('/'):
            bot.send_message(message.chat.id, "Рассылка отменена.")
            return

        broadcast_text = message.text
        conn = database.connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users')
        user_ids = cursor.fetchall()
        cursor.close()
        conn.close()

        sent = 0
        failed = 0

        for user_id in user_ids:
            try:
                bot.send_message(user_id[0], f"📢 Сообщение от администратора:\n\n{broadcast_text}")
                sent += 1
            except telebot.apihelper.ApiTelegramException as e:
                if e.error_code == 403:
                    failed += 1
                else:
                    raise e

        bot.send_message(message.chat.id, f"✅ Рассылка завершена.\nДоставлено: {sent}\nНе доставлено: {failed}")

    def get_user_balance(message):
        if message.text.startswith('/'):
            bot.send_message(message.chat.id, "Изменение баланса отменено.")
            return

        try:
            user_id = int(message.text)
            conn = database.connect_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                markup = types.InlineKeyboardMarkup()
                change_balance_button = types.InlineKeyboardButton(
                    text="Изменить баланс",
                    callback_data=f'change_balance_{user_id}'
                )
                markup.add(change_balance_button)

                bot.send_message(
                    message.chat.id,
                    f"Профиль пользователя:\nID: `{escape_markdown(str(user[0]))}`\n"
                    f"👤 Юзернейм: @{escape_markdown(str(user[1]))}\n"
                    f"📛 Имя: {escape_markdown(str(user[2]))}\n"
                    f"💰 Баланс: {user[3]:.2f} руб",
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
            else:
                bot.send_message(message.chat.id, "❌ Пользователь с таким ID не найден.")

        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверный формат ID.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('change_balance_'))
    def change_balance(call):
        user_id = int(call.data.split('_')[2])
        bot.send_message(call.message.chat.id, "Введите новый баланс для пользователя:")
        bot.register_next_step_handler(call.message, update_user_balance, user_id)

    def update_user_balance(message, user_id):
        try:
            new_balance = float(message.text)
            conn = database.connect_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user_id))
            conn.commit()
            cursor.close()
            conn.close()

            bot.send_message(message.chat.id, "✅ Баланс успешно обновлен.")
            try:
                bot.send_message(user_id, f"💰 Администратор изменил ваш баланс.\nНовый баланс: {new_balance:.2f} руб")
            except:
                pass
        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверный формат суммы.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('users_page_'))
    def change_users_page(call):
        page_number = int(call.data.split('_')[2])
        users_page[call.message.chat.id] = page_number
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_users_page(bot, call.message.chat.id, page_number)