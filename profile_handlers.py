from telebot import types
import database
from datetime import datetime


def setup_profile_handlers(bot):
    @bot.message_handler(commands=['start'])
    def welcome(message):
        user_id = message.from_user.id
        username = message.from_user.username or "нет"
        first_name = message.from_user.first_name or "Пользователь"

        conn = database.connect_db()
        cursor = conn.cursor()

        # Добавляем нового пользователя
        cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
        if cursor.fetchone() is None:
            cursor.execute(
                'INSERT INTO users (id, username, first_name) VALUES (?, ?, ?)',
                (user_id, username, first_name)
            )
            conn.commit()

        cursor.close()
        conn.close()

        # Создаем главное меню
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        profile_button = types.KeyboardButton("👤 Профиль")
        products_button = types.KeyboardButton("🛍️ Товары")
        info_button = types.KeyboardButton("ℹ️ Информация")
        support_button = types.KeyboardButton("💬 Поддержка")
        terms_button = types.KeyboardButton("📄 Соглашение")
        privacy_button = types.KeyboardButton("🔒 Конфиденциальность")

        markup.add(profile_button, products_button)
        markup.add(info_button, support_button)
        markup.add(terms_button, privacy_button)

        welcome_text = f"""
👋 Добро пожаловать, {first_name}!

Добро пожаловать в RaveProxy — ваш надежный партнер в мире прокси-серверов!

🔹 *Быстрые и стабильные прокси*
🔹 *Серверы по всему миру*
🔹 *Мгновенная активация*
🔹 *Круглосуточная поддержка*

✨ *Начните с покупки прокси прямо сейчас!*

📋 *Меню:*
• 👤 Профиль — ваш баланс и покупки
• 🛍️ Товары — доступные прокси
• ℹ️ Информация — о сервисе
• 💬 Поддержка — помощь и консультации
• 📄 Соглашение — правила использования
• 🔒 Конфиденциальность — защита данных
        """

        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.message_handler(commands=['cancel'])
    def cancel(message):
        # Возвращаем в главное меню при команде /cancel
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        profile_button = types.KeyboardButton("👤 Профиль")
        products_button = types.KeyboardButton("🛍️ Товары")
        info_button = types.KeyboardButton("ℹ️ Информация")
        support_button = types.KeyboardButton("💬 Поддержка")
        terms_button = types.KeyboardButton("📄 Соглашение")
        privacy_button = types.KeyboardButton("🔒 Конфиденциальность")

        markup.add(profile_button, products_button)
        markup.add(info_button, support_button)
        markup.add(terms_button, privacy_button)

        bot.send_message(message.chat.id, "Операция отменена. Вы в главном меню.", reply_markup=markup)

    @bot.message_handler(regexp="👤 Профиль")
    def profile(message):
        user_id = message.from_user.id

        conn = database.connect_db()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            markup = types.InlineKeyboardMarkup(row_width=2)
            top_up_button = types.InlineKeyboardButton(text="💸 Пополнить баланс", callback_data='top_up')
            gift_balance_button = types.InlineKeyboardButton(text="🎁 Подарить баланс", callback_data='gift_balance')
            my_keys_button = types.InlineKeyboardButton(text="🔑 Мои ключи", callback_data='my_keys')
            markup.add(top_up_button, gift_balance_button, my_keys_button)

            bot.send_message(
                message.chat.id,
                f"📋 *Ваш профиль*\n\n"
                f"🆔 ID: `{user[0]}`\n"
                f"👤 Юзернейм: @{user[1] or 'нет'}\n"
                f"📛 Имя: {user[2] or 'не указано'}\n"
                f"💰 Баланс: {user[3]:.2f} руб\n"
                f"💸 Всего пополнено: {user[4]:.2f} руб\n"
                f"🛒 Покупок: {user[6]}",
                reply_markup=markup,
                parse_mode='Markdown'
            )

    @bot.message_handler(regexp="📄 Соглашение")
    def user_agreement(message):
        agreement_text = """
📄 *Пользовательское соглашение*

🔹 *1. Общие положения*
Настоящее соглашение регулирует отношения между пользователем и RaveProxy при использовании сервиса продажи прокси-серверов.

🔹 *2. Предмет соглашения*
Сервис предоставляет доступ к прокси-серверам различных типов для обеспечения анонимности и безопасности в сети Интернет.

🔹 *3. Права и обязанности пользователя*
• Использовать прокси только в законных целях
• Не нарушать работу сервиса
• Соблюдать законодательство РФ
• Не передавать данные третьим лицам

🔹 *4. Ограничения использования*
Запрещается использование для:
• Незаконной деятельности
• Атак на информационные системы
• Нарушения авторских прав
• Распространения вредоносного ПО

🔹 *5. Ответственность*
Пользователь несет полную ответственность за свои действия при использовании сервиса.

🔹 *6. Изменения в соглашении*
Администрация оставляет за собой право изменять условия без предварительного уведомления.

📅 *Дата последнего обновления: 01.01.2026*
        """

        markup = types.InlineKeyboardMarkup()
        back_button = types.InlineKeyboardButton(
            text="🔙 Вернуться в меню",
            callback_data='back_to_main_menu'
        )
        markup.add(back_button)

        bot.send_message(
            message.chat.id,
            agreement_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.message_handler(regexp="🔒 Конфиденциальность")
    def privacy_policy(message):
        privacy_text = """
🔒 *Политика конфиденциальности*

🛡️ *1. Сбор информации*
Мы собираем только необходимую информацию:
• Telegram ID пользователя
• Имя пользователя (если указано)
• Данные о заказах и платежах
• Время использования сервиса

🔐 *2. Использование данных*
Собранная информация используется для:
• Предоставления услуг
• Обработки платежей
• Технической поддержки
• Улучшения сервиса

🔒 *3. Защита данных*
• Все данные шифруются
• Доступ ограничен
• Регулярные проверки безопасности
• Соответствие GDPR

📤 *4. Передача данных*
Мы *НЕ* передаем ваши данные третьим лицам, за исключением:
• Требований законодательства
• Платежных систем (для обработки платежей)

🗑️ *5. Удаление данных*
Вы можете запросить удаление ваших данных, обратившись в поддержку.

📞 *6. Контакты*
По вопросам конфиденциальности обращайтесь в поддержку.

📅 *Дата последнего обновления: 01.01.2026*
        """

        markup = types.InlineKeyboardMarkup()
        back_button = types.InlineKeyboardButton(
            text="🔙 Вернуться в меню",
            callback_data='back_to_main_menu'
        )
        markup.add(back_button)

        bot.send_message(
            message.chat.id,
            privacy_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.message_handler(regexp="ℹ️ Информация")
    def service_info(message):
        info_text = """
ℹ️ *Информация о RaveProxy:*

🌐 *Что мы предлагаем:*
• Быстрые и надежные прокси
• Серверы в разных странах
• Различные типы подключения
• Автоматическая выдача

💳 *Способы оплаты:*
• Банковские карты
• СБП (Система быстрых платежей)
• ЮMoney

⚡️ *Преимущества:*
• Мгновенная активация
• 24/7 техподдержка
• Стабильная работа
• Конкурентные цены

🔒 *Безопасность:*
• Защищенные платежи
• Конфиденциальность данных
• Надежная инфраструктура

🚀 *Начните использовать наши прокси уже сегодня!*
        """

        markup = types.InlineKeyboardMarkup(row_width=2)
        products_button = types.InlineKeyboardButton(
            text="🛍️ Посмотреть товары",
            callback_data='view_products_from_info'
        )
        profile_button = types.InlineKeyboardButton(
            text="👤 Мой профиль",
            callback_data='view_profile_from_info'
        )
        support_button = types.InlineKeyboardButton(
            text="💬 Поддержка",
            callback_data='view_support_from_info'
        )
        back_button = types.InlineKeyboardButton(
            text="🔙 Вернуться",
            callback_data='back_to_main_menu'
        )
        markup.add(products_button, profile_button, support_button, back_button)

        bot.send_message(
            message.chat.id,
            info_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.message_handler(regexp="💬 Поддержка")
    def support_info(message):
        support_text = """
💬 *Поддержка*

👨‍💻 *Контакты для связи:*
• Саппорт - @rozetkagamer228
• Время работы: 12:00-18:00 (МСК)

🕒 *Часы работы поддержки:*
Понедельник - Пятница: 12:00-18:00
Суббота - Воскресенье: 14:00-16:00

📋 *Что мы можем помочь:*
• Консультации по товарам
• Помощь с оплатой
• Технические вопросы
• Возвраты и отмены

⚡️ *Перед обращением в поддержку:*
1. Проверьте баланс в профиле
2. Убедитесь в правильности платежа
3. Сохраните чек об оплате

⚠️ *Важно:*
• Не передавайте свои данные третьим лицам
• Официальный канал поддержки — @rozetkagamer228
        """

        markup = types.InlineKeyboardMarkup(row_width=2)
        contact_button = types.InlineKeyboardButton(
            text="📨 Написать в поддержку",
            url="https://t.me/rozetkagamer228"
        )
        faq_button = types.InlineKeyboardButton(
            text="❓ Частые вопросы",
            callback_data='faq_info'
        )
        back_button = types.InlineKeyboardButton(
            text="🔙 Вернуться в меню",
            callback_data='back_to_main_menu'
        )
        markup.add(contact_button, faq_button, back_button)

        bot.send_message(
            message.chat.id,
            support_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'back_to_main_menu')
    def back_to_main_menu(call):
        # Создаем главное меню
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        profile_button = types.KeyboardButton("👤 Профиль")
        products_button = types.KeyboardButton("🛍️ Товары")
        info_button = types.KeyboardButton("ℹ️ Информация")
        support_button = types.KeyboardButton("💬 Поддержка")
        terms_button = types.KeyboardButton("📄 Соглашение")
        privacy_button = types.KeyboardButton("🔒 Конфиденциальность")

        markup.add(profile_button, products_button)
        markup.add(info_button, support_button)
        markup.add(terms_button, privacy_button)

        bot.send_message(
            call.message.chat.id,
            "Вы вернулись в главное меню. Что вас интересует?",
            reply_markup=markup
        )

        # Удаляем предыдущее сообщение
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

    @bot.callback_query_handler(func=lambda call: call.data == 'view_products_from_info')
    def view_products_from_info(call):
        # Создаем фиктивное сообщение для вызова функции products
        class FakeMessage:
            def __init__(self, chat_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.text = "🛍️ Товары"

        fake_msg = FakeMessage(call.message.chat.id)
        products(fake_msg)

        # Удаляем предыдущее сообщение
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

    @bot.callback_query_handler(func=lambda call: call.data == 'view_profile_from_info')
    def view_profile_from_info(call):
        # Создаем фиктивное сообщение для вызова функции profile
        class FakeMessage:
            def __init__(self, chat_id, from_user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': from_user_id})
                self.text = "👤 Профиль"

        fake_msg = FakeMessage(call.message.chat.id, call.from_user.id)
        profile(fake_msg)

        # Удаляем предыдущее сообщение
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

    @bot.callback_query_handler(func=lambda call: call.data == 'view_support_from_info')
    def view_support_from_info(call):
        # Создаем фиктивное сообщение для вызова функции support_info
        class FakeMessage:
            def __init__(self, chat_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.text = "💬 Поддержка"

        fake_msg = FakeMessage(call.message.chat.id)
        support_info(fake_msg)

        # Удаляем предыдущее сообщение
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

    @bot.callback_query_handler(func=lambda call: call.data == 'faq_info')
    def faq_info(call):
        faq_text = """
❓ *Часто задаваемые вопросы*

1️⃣ *Как купить прокси?*
• Зайдите в 🛍️ Товары
• Выберите нужный товар
• Оплатите с баланса
• Получите ключ мгновенно

2️⃣ *Как пополнить баланс?*
• Зайдите в 👤 Профиль
• Нажмите 💸 Пополнить баланс
• Выберите способ оплаты
• Следуйте инструкциям

3️⃣ *Где взять ключ после покупки?*
• Ключ придет в личные сообщения
• Также можно посмотреть в 👤 Профиль → 🔑 Мои ключи

4️⃣ *Не приходит ключ после оплаты?*
• Проверьте баланс в профиле
• Нажмите кнопку "Проверить оплату"
• Если проблема не решена — обратитесь в поддержку

5️⃣ *Как получить помощь?*
• Напишите в поддержку @rozetkagamer228
• Укажите ваш ID и проблему
• Приложите скриншоты если нужно
        """

        markup = types.InlineKeyboardMarkup()
        support_button = types.InlineKeyboardButton(
            text="💬 Написать в поддержку",
            url="https://t.me/rozetkagamer228"
        )
        back_button = types.InlineKeyboardButton(
            text="🔙 Назад к поддержке",
            callback_data='back_to_support'
        )
        markup.add(support_button, back_button)

        bot.edit_message_text(
            faq_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'back_to_support')
    def back_to_support(call):
        # Создаем фиктивное сообщение для вызова функции support_info
        class FakeMessage:
            def __init__(self, chat_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.text = "💬 Поддержка"

        fake_msg = FakeMessage(call.message.chat.id)
        support_info(fake_msg)

        # Удаляем предыдущее сообщение
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

    @bot.message_handler(regexp="🛍️ Товары")
    def products(message):
            conn = database.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, name, price, description, total_keys, sold_keys FROM products WHERE is_active = 1')
            product_list = cursor.fetchall()

            cursor.close()
            conn.close()

            if not product_list:
                bot.send_message(message.chat.id, "🛒 Пока нет доступных товаров.")
                return

            # Создаем сообщение с рамкой
            products_text = """
    ╔════════════════════════════╗
         Rave ПРОКСИ — ВЫБОР СЕРВЕРА
    ╚════════════════════════════╝

    *FunTime* — работают только на этом сервере
    *HolyWorld* — работают только на этом сервере
    *Universal* — совместимы с большинством проектов
    Не функционируют на FunTime и HolyWorld

    ────────────────────────────
    Гарантия корректной работы распространяется только на указанные сервера
    ────────────────────────────

    Выберите нужный сервер, чтобы получить подходящий прокси:
            """

            # Создаем кнопки для всех товаров
            markup = types.InlineKeyboardMarkup(row_width=1)  # row_width=1 чтобы кнопки шли вертикально

            for product in product_list:
                available = product[4] - product[5]
                button_text = f"{product[1]} - {product[2]:.2f} руб (📦 {available})"
                markup.add(types.InlineKeyboardButton(
                    text=button_text,
                    callback_data=f'view_product_{product[0]}'
                ))

            # Отправляем ОДНО сообщение со всеми кнопками
            bot.send_message(
                message.chat.id,
                products_text,
                reply_markup=markup,
                parse_mode='Markdown'
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('view_product_'))
    def view_product(call):
        product_id = int(call.data.split('_')[2])

        conn = database.connect_db()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, price, description, total_keys, sold_keys 
            FROM products 
            WHERE id = ? AND is_active = 1
        ''', (product_id,))
        product = cursor.fetchone()

        cursor.close()
        conn.close()

        if not product:
            bot.send_message(call.message.chat.id, "❌ Товар не найден или неактивен.")
            return

        product_id = product[0]
        product_name = product[1]
        price = product[2]
        description = product[3]
        total_keys = product[4]
        sold_keys = product[5]
        available = total_keys - sold_keys

        if available <= 0:
            bot.answer_callback_query(call.id, "❌ Товар временно отсутствует", show_alert=True)
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            text=f"✅ Купить за {price:.2f} руб",
            callback_data=f'buy_product_{product_id}'
        ))
        markup.add(types.InlineKeyboardButton(
            text="🔙 Назад к товарам",
            callback_data='back_to_products'
        ))

        bot.send_message(
            call.message.chat.id,
            f"🛍️ *{product_name}*\n\n"
            f"📝 Описание: {description}\n"
            f"💰 Цена: {price:.2f} руб\n"
            f"📦 Доступно: {available} шт\n"
            f"📈 Продано: {sold_keys} шт\n\n"
            f"Для покупки нажмите кнопку ниже:",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'back_to_products')
    def back_to_products(call):
        products(call.message)

    @bot.callback_query_handler(func=lambda call: call.data == 'my_keys')
    def my_keys(call):
        user_id = call.from_user.id

        conn = database.connect_db()
        cursor = conn.cursor()

        # Получаем все купленные ключи пользователя с пагинацией
        cursor.execute('''
            SELECT COUNT(*) 
            FROM purchases p
            JOIN product_keys pk ON p.key_id = pk.id
            JOIN products pr ON p.product_id = pr.id
            WHERE p.user_id = ?
        ''', (user_id,))

        total_keys = cursor.fetchone()[0]

        if total_keys == 0:
            bot.send_message(call.message.chat.id, "📭 У вас пока нет купленных ключей.")
            return

        # Показываем первую страницу
        show_keys_page(bot, call.message.chat.id, user_id, 1)

        bot.answer_callback_query(call.id)

    def show_keys_page(bot, chat_id, user_id, page_number, message_id=None):
        conn = database.connect_db()
        cursor = conn.cursor()

        # Количество ключей на странице
        per_page = 5

        # Получаем ключи для текущей страницы
        cursor.execute('''
            SELECT 
                pr.name,
                pk.key_value,
                p.purchase_date,
                p.price
            FROM purchases p
            JOIN product_keys pk ON p.key_id = pk.id
            JOIN products pr ON p.product_id = pr.id
            WHERE p.user_id = ?
            ORDER BY p.purchase_date DESC
            LIMIT ? OFFSET ?
        ''', (user_id, per_page, (page_number - 1) * per_page))

        keys = cursor.fetchall()

        # Формируем сообщение
        keys_text = f"🔑 *Ваши купленные ключи*\n\n"

        if not keys:
            keys_text += "На этой странице нет ключей."
        else:
            for i, key in enumerate(keys, 1):
                product_name = key[0]
                key_value = key[1]
                purchase_date = datetime.strptime(key[2], '%Y-%m-%d %H:%M:%S') if key[2] else "Дата неизвестна"
                price = key[3]

                if isinstance(purchase_date, datetime):
                    date_str = purchase_date.strftime('%d.%m.%Y %H:%M')
                else:
                    date_str = str(purchase_date)

                keys_text += f"*{i + (page_number - 1) * per_page}. {product_name}*\n"
                keys_text += f"   🔑 Ключ: `{key_value}`\n"
                keys_text += f"   💰 Цена: {price:.2f} руб\n"
                keys_text += f"   📅 Дата: {date_str}\n\n"
                keys_text += f"   🔑 Активировать можно в @raveproxyactivationbot\n\n"

        # Получаем общее количество ключей
        cursor.execute('''
            SELECT COUNT(*) 
            FROM purchases 
            WHERE user_id = ?
        ''', (user_id,))
        total_keys = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # Создаем клавиатуру с пагинацией
        markup = types.InlineKeyboardMarkup(row_width=3)

        # Кнопки пагинации
        if page_number > 1:
            markup.add(types.InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f'keys_page_{user_id}_{page_number - 1}'
            ))

        markup.add(types.InlineKeyboardButton(
            text=f"{page_number}/{(total_keys + per_page - 1) // per_page}",
            callback_data='no_action'
        ))

        if page_number * per_page < total_keys:
            markup.add(types.InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f'keys_page_{user_id}_{page_number + 1}'
            ))

        # Кнопка "Назад в профиль"
        markup.add(types.InlineKeyboardButton(
            text="🔙 Назад в профиль",
            callback_data='back_to_profile'
        ))

        # Кнопка "Экспортировать ключи"
        markup.add(types.InlineKeyboardButton(
            text="📤 Экспорт ключей",
            callback_data=f'export_my_keys_{user_id}'
        ))

        if message_id:
            # Редактируем существующее сообщение
            bot.edit_message_text(
                keys_text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        else:
            # Отправляем новое сообщение
            bot.send_message(
                chat_id,
                keys_text,
                reply_markup=markup,
                parse_mode='Markdown'
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('keys_page_'))
    def change_keys_page(call):
        data = call.data.split('_')
        user_id = int(data[2])
        page_number = int(data[3])

        # Проверяем, что пользователь смотрит свои ключи
        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "❌ Вы не можете просматривать чужие ключи.", show_alert=True)
            return

        show_keys_page(bot, call.message.chat.id, user_id, page_number, call.message.message_id)
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'back_to_profile')
    def back_to_profile(call):
        # Создаем фиктивное сообщение для вызова профиля
        class FakeMessage:
            def __init__(self, chat_id, from_user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': from_user_id})
                self.text = "👤 Профиль"

        fake_msg = FakeMessage(call.message.chat.id, call.from_user.id)
        profile(fake_msg)

        # Удаляем сообщение с ключами
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('export_my_keys_'))
    def export_my_keys(call):
        user_id = int(call.data.split('_')[3])

        # Проверяем, что пользователь экспортирует свои ключи
        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "❌ Вы не можете экспортировать чужие ключи.", show_alert=True)
            return

        conn = database.connect_db()
        cursor = conn.cursor()

        # Получаем все ключи пользователя
        cursor.execute('''
            SELECT 
                pr.name,
                pk.key_value,
                p.purchase_date
            FROM purchases p
            JOIN product_keys pk ON p.key_id = pk.id
            JOIN products pr ON p.product_id = pr.id
            WHERE p.user_id = ?
            ORDER BY p.purchase_date DESC
        ''', (user_id,))

        keys = cursor.fetchall()

        if not keys:
            bot.answer_callback_query(call.id, "❌ У вас нет купленных ключей для экспорта.", show_alert=True)
            cursor.close()
            conn.close()
            return

        # Формируем текстовый файл
        import io
        export_text = "Ваши купленные ключи:\n\n"

        for i, key in enumerate(keys, 1):
            product_name = key[0]
            key_value = key[1]
            purchase_date = key[2]

            export_text += f"{i}. {product_name}\n"
            export_text += f"   Ключ: {key_value}\n"
            export_text += f"   Дата покупки: {purchase_date}\n\n"
            export_text += f"   🔑 Активировать можно в @raveproxyactivationbot\n\n"

        export_text += f"\nВсего ключей: {len(keys)}\nЭкспортировано: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"

        # Создаем файл
        bio = io.BytesIO(export_text.encode('utf-8'))
        bio.name = f'my_keys_{user_id}.txt'

        cursor.close()
        conn.close()

        # Отправляем файл
        bot.send_document(
            call.message.chat.id,
            bio,
            caption=f"📤 Ваши купленные ключи ({len(keys)} шт.)"
        )

        bot.answer_callback_query(call.id, "✅ Ключи экспортированы в файл!")

    @bot.callback_query_handler(func=lambda call: call.data == 'no_action')
    def no_action(call):
        # Пустая функция для кнопки, которая ничего не делает
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('buy_product_'))
    def buy_product(call):
        product_id = int(call.data.split('_')[2])
        user_id = call.message.chat.id

        conn = database.connect_db()
        cursor = conn.cursor()

        # Проверяем доступность товара
        cursor.execute('''
            SELECT name, price, total_keys, sold_keys 
            FROM products 
            WHERE id = ? AND is_active = 1
        ''', (product_id,))
        product = cursor.fetchone()

        if not product:
            bot.answer_callback_query(call.id, "❌ Товар не найден", show_alert=True)
            return

        product_name = product[0]
        price = product[1]
        total_keys = product[2]
        sold_keys = product[3]
        available = total_keys - sold_keys

        if available <= 0:
            bot.answer_callback_query(call.id, "❌ Товар закончился", show_alert=True)
            return

        # Проверяем баланс пользователя
        cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        user_balance = cursor.fetchone()[0]

        if user_balance < price:
            bot.answer_callback_query(
                call.id,
                f"❌ Недостаточно средств. Нужно: {price:.2f} руб, у вас: {user_balance:.2f} руб",
                show_alert=True
            )
            cursor.close()
            conn.close()
            return

        # Находим доступный ключ
        cursor.execute('''
            SELECT id, key_value 
            FROM product_keys 
            WHERE product_id = ? AND is_sold = 0 
            LIMIT 1
        ''', (product_id,))
        key_data = cursor.fetchone()

        if not key_data:
            bot.answer_callback_query(call.id, "❌ Ошибка: ключи отсутствуют", show_alert=True)
            cursor.close()
            conn.close()
            return

        key_id = key_data[0]
        key_value = key_data[1]

        # Обновляем баланс пользователя
        cursor.execute(
            'UPDATE users SET balance = balance - ?, total_purchases = total_purchases + 1 WHERE id = ?',
            (price, user_id)
        )

        # Помечаем ключ как проданный
        cursor.execute(
            'UPDATE product_keys SET is_sold = 1, sold_to = ?, sold_date = CURRENT_TIMESTAMP WHERE id = ?',
            (user_id, key_id)
        )

        # Обновляем счетчики товара
        cursor.execute(
            'UPDATE products SET sold_keys = sold_keys + 1 WHERE id = ?',
            (product_id,)
        )

        # Записываем покупку
        cursor.execute('''
            INSERT INTO purchases (user_id, product_id, key_id, price)
            VALUES (?, ?, ?, ?)
        ''', (user_id, product_id, key_id, price))

        conn.commit()

        # Получаем обновленный баланс
        cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        new_balance = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # Отправляем ключ пользователю
        markup = types.InlineKeyboardMarkup(row_width=2)
        menu_button = types.InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data='back_to_main_menu'
        )
        my_keys_button = types.InlineKeyboardButton(
            text="🔑 Мои ключи",
            callback_data='my_keys'
        )
        markup.add(menu_button, my_keys_button)

        bot.send_message(
            user_id,
            f"🎉 *Покупка успешно завершена!*\n\n"
            f"🛍️ Товар: {product_name}\n"
            f"💰 Стоимость: {price:.2f} руб\n"
            f"💳 Новый баланс: {new_balance:.2f} руб\n\n"
            f"🔑 *Ваш ключ:*\n`{key_value}`\n\n"
            "🔑 Активировать можно в @raveproxyactivationbot\n\n"
            f"⚠️ Сохраните этот ключ в надежном месте!\n"
            f"📋 Все купленные ключи можно посмотреть в профиле (кнопка '🔑 Мои ключи')",
            reply_markup=markup,
            parse_mode='Markdown'
        )

        # Обновляем сообщение
        bot.edit_message_text(
            f"✅ *Покупка завершена!*\n\n"
            f"Ключ вам был выслан ранее.\n\n"
            f"Проверьте его и сохраните в надежном месте.\n\n"
            f"Все купленные ключи можно посмотреть в профиле.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )