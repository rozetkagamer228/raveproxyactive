import logging
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from telebot import TeleBot, types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from telebot.custom_filters import StateFilter

BOT_TOKEN = "8479897989:AAFpiVVVjgOKJQpp_CIqnz6QJQNNqVIuE5E"
ADMIN_ID = 5182413789  # Замените на ваш ID в Telegramegram


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота с хранилищем состояний
storage = StateMemoryStorage()
bot = TeleBot(BOT_TOKEN, state_storage=storage)


# Класс для работы с базой данных
class Database:
    def __init__(self, db_name: str = 'rave_proxy.db'):
        self.db_name = db_name
        self.lock = threading.Lock()  # Для потокобезопасности
        self.init_database()

    def get_connection(self):
        """Создает соединение с базой данных"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
        return conn

    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Таблица ключей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS keys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key_value TEXT UNIQUE NOT NULL,
                        key_type TEXT,
                        wexside_address TEXT NOT NULL,
                        address TEXT NOT NULL,
                        login TEXT NOT NULL,
                        password TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 0,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        activated_date TIMESTAMP,
                        activated_by INTEGER,
                        FOREIGN KEY (activated_by) REFERENCES users(user_id)
                    )
                ''')

                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Таблица активаций (для истории)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        key_id INTEGER NOT NULL,
                        activation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (key_id) REFERENCES keys(id),
                        UNIQUE(key_id, user_id)
                    )
                ''')

                conn.commit()

    # Методы для работы с ключами
    def add_key(self, key_value: str, wexside_address: str, address: str,
                login: str, password: str) -> bool:
        """Добавление нового ключа"""
        try:
            key_type = key_value.split('_')[0] if '_' in key_value else "Базовый"
            with self.lock:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO keys (key_value, key_type, wexside_address, address, login, password)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (key_value, key_type, wexside_address, address, login, password))
                    conn.commit()
                    return True
        except sqlite3.IntegrityError:
            return False  # Ключ уже существует
        except Exception as e:
            logger.error(f"Ошибка добавления ключа: {e}")
            return False

    def get_key(self, key_value: str) -> Optional[dict]:
        """Получение данных ключа"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM keys WHERE key_value = ?', (key_value,))
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_all_keys(self) -> List[dict]:
        """Получение всех ключей"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT k.*, u.username as activated_by_username 
                    FROM keys k 
                    LEFT JOIN users u ON k.activated_by = u.user_id
                    ORDER BY k.added_date DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]

    def activate_key(self, key_value: str, user_id: int) -> Tuple[bool, Optional[dict], str]:
        """Активация ключа пользователем"""
        try:
            with self.lock:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    # Проверяем существование ключа
                    key_data = self.get_key(key_value)
                    if not key_data:
                        return False, None, "Ключ не найден"

                    # Проверяем, не активирован ли уже ключ
                    if key_data['is_active']:
                        # Проверяем, этот ли пользователь активировал ключ
                        if key_data['activated_by'] == user_id:
                            return True, key_data, "Ключ уже активирован вами ранее"
                        else:
                            return False, None, "Ключ уже активирован другим пользователем"

                    # Проверяем, есть ли уже активация у этого пользователя для этого ключа
                    cursor.execute('''
                        SELECT 1 FROM activations 
                        WHERE user_id = ? AND key_id = ?
                    ''', (user_id, key_data['id']))

                    if cursor.fetchone():
                        return False, None, "Вы уже активировали этот ключ"

                    # Обновляем информацию о ключе
                    activation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute('''
                        UPDATE keys 
                        SET is_active = 1, activated_date = ?, activated_by = ?
                        WHERE key_value = ?
                    ''', (activation_date, user_id, key_value))

                    # Добавляем запись в историю активаций
                    cursor.execute('''
                        INSERT INTO activations (user_id, key_id)
                        VALUES (?, ?)
                    ''', (user_id, key_data['id']))

                    conn.commit()

                    # Получаем обновленные данные ключа
                    key_data = self.get_key(key_value)
                    return True, key_data, "Ключ успешно активирован"

        except Exception as e:
            logger.error(f"Ошибка активации ключа: {e}")
            return False, None, f"Ошибка активации: {str(e)}"

    # Методы для работы с пользователями
    def get_or_create_user(self, user_id: int, username: str,
                           first_name: str, last_name: str) -> dict:
        """Получение или создание пользователя"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем существование пользователя
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()

                if user:
                    # Обновляем последнюю активность
                    cursor.execute('''
                        UPDATE users 
                        SET username = ?, first_name = ?, last_name = ?, last_activity = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    ''', (username, first_name, last_name, user_id))
                    conn.commit()
                    return dict(user)
                else:
                    # Создаем нового пользователя
                    cursor.execute('''
                        INSERT INTO users (user_id, username, first_name, last_name)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, username, first_name, last_name))
                    conn.commit()

                    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                    return dict(cursor.fetchone())

    def get_user_activations(self, user_id: int) -> List[dict]:
        """Получение истории активаций пользователя"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT k.key_value, k.key_type, k.wexside_address, k.address, 
                           k.login, k.password, a.activation_date,
                           CASE 
                             WHEN k.activated_by = ? THEN 1 
                             ELSE 0 
                           END as is_owned_by_user
                    FROM activations a
                    JOIN keys k ON a.key_id = k.id
                    WHERE a.user_id = ?
                    ORDER BY a.activation_date DESC
                ''', (user_id, user_id))
                return [dict(row) for row in cursor.fetchall()]

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Получение пользователя по ID"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_all_users(self) -> List[dict]:
        """Получение всех пользователей"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.*, 
                           COUNT(DISTINCT a.id) as total_activations,
                           MAX(a.activation_date) as last_activation
                    FROM users u
                    LEFT JOIN activations a ON u.user_id = a.user_id
                    GROUP BY u.user_id
                    ORDER BY u.registration_date DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]

    # Статистика
    def get_statistics(self) -> dict:
        """Получение статистики"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('SELECT COUNT(*) as total FROM keys')
                total_keys = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) as active FROM keys WHERE is_active = 1')
                active_keys = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(DISTINCT user_id) as total FROM users')
                total_users = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) as total FROM activations')
                total_activations = cursor.fetchone()[0]

                return {
                    'total_keys': total_keys,
                    'active_keys': active_keys,
                    'inactive_keys': total_keys - active_keys,
                    'total_users': total_users,
                    'total_activations': total_activations
                }

    # Админ методы
    def broadcast_to_users(self) -> List[int]:
        """Получение списка всех user_id для рассылки"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users')
                return [row[0] for row in cursor.fetchall()]


# Инициализация базы данных
db = Database()


# Состояния для FSM
class UserStates:
    waiting_for_key = "waiting_for_key"
    viewing_history = "viewing_history"


class AdminStates:
    waiting_for_broadcast = "waiting_for_broadcast"
    waiting_for_new_key = "waiting_for_new_key"
    waiting_for_wexside = "waiting_for_wexside"
    waiting_for_address = "waiting_for_address"
    waiting_for_login = "waiting_for_login"
    waiting_for_password = "waiting_for_password"


# Вспомогательные функции
def create_main_menu() -> types.InlineKeyboardMarkup:
    """Создает главное меню"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Активировать ключ", callback_data="activate_key"),
        types.InlineKeyboardButton("📋 История активаций", callback_data="view_history"),
        types.InlineKeyboardButton("Купить ключ", callback_data="buy_key"),
        types.InlineKeyboardButton("Поддержка", callback_data="support")
    )
    return markup


def create_back_menu() -> types.InlineKeyboardMarkup:
    """Создает меню с кнопкой Назад"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu"))
    return markup


def create_admin_menu() -> types.InlineKeyboardMarkup:
    """Создает меню администратора"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 Все ключи", callback_data="admin_all_keys"),
        types.InlineKeyboardButton("👥 Все пользователи", callback_data="admin_all_users"),
        types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("➕ Добавить ключ", callback_data="admin_add_key"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    )
    return markup


def format_proxy_data(key_data: dict, username: str, user_id: int) -> str:
    """Форматирует данные прокси для отображения"""
    if 'activated_date' in key_data and key_data['activated_date']:
        try:
            activation_date = datetime.strptime(key_data['activated_date'], "%Y-%m-%d %H:%M:%S")
            formatted_date = activation_date.strftime("%d.%m.%Y %H:%M")
        except:
            formatted_date = key_data.get('activation_date', 'Неизвестно')
    else:
        formatted_date = key_data.get('activation_date', 'Неизвестно')

    proxy_info = f"""
👤 Пользователь: {username} (ID: {user_id})
🛡️ Тип: 🌙 {key_data.get('key_type', 'Базовый')}

📋 Ваши прокси:

🔹 Прокси 
🌐 Адрес для WexSide: `{key_data.get('wexside_address', 'Не указан')}`
🌐 Адрес: `{key_data.get('address', 'Не указан')}`
👤 Логин: `{key_data.get('login', 'Не указан')}`
🔐 Пароль: `{key_data.get('password', 'Не указан')}`
📅 Выдано: {formatted_date}
────────────────────

💡 Сохраните эту информацию!
"""
    return proxy_info


# Команда /start
@bot.message_handler(commands=['start'])
def cmd_start(message: types.Message):
    # Регистрируем/обновляем пользователя
    user = db.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    welcome_text = """👋 Привет! Добро пожаловать в Rave Proxy

💠 Вы находитесь в главном меню"""

    if message.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👤 Пользователь", callback_data="user_menu"),
            types.InlineKeyboardButton("⚙️ Админ", callback_data="admin_menu")
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_menu())

    # Сбрасываем состояние
    bot.delete_state(message.from_user.id, message.chat.id)


# Обработчики главного меню
@bot.callback_query_handler(func=lambda call: call.data == "user_menu")
def user_menu(call: types.CallbackQuery):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👋 Привет! Добро пожаловать в Rave Proxy\n\n💠 Вы находитесь в главном меню",
        reply_markup=create_main_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_menu")
def admin_menu(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
        return

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="⚙️ Панель администратора",
        reply_markup=create_admin_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call: types.CallbackQuery):
    # Сбрасываем состояние
    bot.delete_state(call.from_user.id, call.message.chat.id)

    if call.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👤 Пользователь", callback_data="user_menu"),
            types.InlineKeyboardButton("⚙️ Админ", callback_data="admin_menu")
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="👋 Привет! Добро пожаловать в Rave Proxy\n\n💠 Вы находитесь в главном меню",
            reply_markup=markup
        )
    else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="👋 Привет! Добро пожаловать в Rave Proxy\n\n💠 Вы находитесь в главном меню",
            reply_markup=create_main_menu()
        )


# Обработка кнопки "Купить ключ"
@bot.callback_query_handler(func=lambda call: call.data == "buy_key")
def buy_key(call: types.CallbackQuery):
    bot.send_message(call.message.chat.id, "Купить ключ можно в боте @raveproxybot")
    bot.answer_callback_query(call.id)


# Обработка кнопки "Поддержка"
@bot.callback_query_handler(func=lambda call: call.data == "support")
def support(call: types.CallbackQuery):
    support_text = """💬 Поддержка

• Саппорт - @rozetkagamer228
• Время работы: 12:00-18:00"""
    bot.send_message(call.message.chat.id, support_text)
    bot.answer_callback_query(call.id)


# Обработка кнопки "Активировать ключ"
@bot.callback_query_handler(func=lambda call: call.data == "activate_key")
def activate_key_start(call: types.CallbackQuery):
    bot.send_message(call.message.chat.id, "Введите ключ для активации:")
    bot.set_state(call.from_user.id, UserStates.waiting_for_key, call.message.chat.id)
    bot.answer_callback_query(call.id)


# Обработка ввода ключа
@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == UserStates.waiting_for_key)
def process_key_activation(message: types.Message):
    key = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.full_name

    # Активируем ключ через базу данных
    success, key_data, message_text = db.activate_key(key, user_id)

    if success and key_data:
        await_msg = bot.send_message(message.chat.id, "⏳ Активирую ключ...")

        # Форматируем дату для отображения
        if key_data.get('activated_date'):
            try:
                activation_date = datetime.strptime(key_data['activated_date'], "%Y-%m-%d %H:%M:%S")
                key_data['activated_date'] = activation_date.strftime("%d.%m.%Y %H:%M")
            except:
                pass

        proxy_info = format_proxy_data(key_data, username, user_id)

        # Удаляем сообщение "Активирую ключ..."
        bot.delete_message(message.chat.id, await_msg.message_id)

        bot.send_message(
            message.chat.id,
            proxy_info,
            reply_markup=create_back_menu(),
            parse_mode="Markdown"
        )
    else:
        error_message = f"❌ {message_text}\n\n"
        if "не найден" in message_text.lower():
            error_message += "Купите ключ в боте @raveproxybot или если произошла ошибка обратитесь в поддержку."

        bot.send_message(
            message.chat.id,
            error_message,
            reply_markup=create_back_menu()
        )

    # Сбрасываем состояние
    bot.delete_state(user_id, message.chat.id)


# История активации - просмотр списка
@bot.callback_query_handler(func=lambda call: call.data == "view_history")
def view_history_list(call: types.CallbackQuery):
    user_id = call.from_user.id
    username = call.from_user.full_name

    # Получаем историю активаций пользователя
    activations = db.get_user_activations(user_id)

    if not activations:
        bot.send_message(
            call.message.chat.id,
            "У вас пока нет активированных ключей.",
            reply_markup=create_back_menu()
        )
        bot.answer_callback_query(call.id)
        return

    if len(activations) == 1:
        # Если только один ключ, сразу показываем его данные
        key_data = activations[0]
        if key_data.get('activation_date'):
            try:
                activation_date = datetime.strptime(key_data['activation_date'], "%Y-%m-%d %H:%M:%S")
                key_data['activated_date'] = activation_date.strftime("%d.%m.%Y %H:%M")
            except:
                pass

        bot.send_message(
            call.message.chat.id,
            format_proxy_data(key_data, username, user_id),
            reply_markup=create_back_menu(),
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)
        return

    # Создаем клавиатуру со списком ключей
    markup = types.InlineKeyboardMarkup(row_width=1)

    for activation in activations:
        key_type = activation['key_type']
        key_value = activation['key_value']
        display_name = f"🔑 {key_type} ({key_value[:10]}...)"
        markup.add(types.InlineKeyboardButton(display_name, callback_data=f"view_key_{key_value}"))

    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu"))

    bot.send_message(
        call.message.chat.id,
        "📋 Ваши активированные ключи. Выберите ключ для просмотра данных:",
        reply_markup=markup
    )

    # Устанавливаем состояние
    bot.set_state(user_id, UserStates.viewing_history, call.message.chat.id)
    bot.answer_callback_query(call.id)


# Просмотр конкретного ключа из истории
@bot.callback_query_handler(func=lambda call: call.data.startswith("view_key_"))
def view_specific_key(call: types.CallbackQuery):
    user_id = call.from_user.id
    username = call.from_user.full_name
    key_value = call.data.replace("view_key_", "")

    # Получаем историю активаций пользователя
    activations = db.get_user_activations(user_id)

    # Ищем нужный ключ
    key_data = None
    for activation in activations:
        if activation['key_value'] == key_value:
            key_data = activation
            break

    if not key_data:
        bot.answer_callback_query(call.id, "Ключ не найден", show_alert=True)
        return

    # Форматируем дату
    if key_data.get('activation_date'):
        try:
            activation_date = datetime.strptime(key_data['activation_date'], "%Y-%m-%d %H:%M:%S")
            key_data['activated_date'] = activation_date.strftime("%d.%m.%Y %H:%M")
        except:
            pass

    bot.send_message(
        call.message.chat.id,
        format_proxy_data(key_data, username, user_id),
        reply_markup=create_back_menu(),
        parse_mode="Markdown"
    )

    # Сбрасываем состояние
    bot.delete_state(user_id, call.message.chat.id)
    bot.answer_callback_query(call.id)


# Админка: все ключи
@bot.callback_query_handler(func=lambda call: call.data == "admin_all_keys")
def admin_all_keys(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
        return

    keys = db.get_all_keys()

    if not keys:
        bot.send_message(call.message.chat.id, "Нет добавленных ключей.")
        bot.answer_callback_query(call.id)
        return

    keys_text = "📋 Все ключи:\n\n"
    for key in keys:
        status = "✅ Активен" if key['is_active'] else "❌ Не активирован"
        keys_text += f"🔑 {key['key_value']}\n"
        keys_text += f"🛡️ Тип: {key['key_type']}\n"
        keys_text += f"📊 Статус: {status}\n"
        keys_text += f"📅 Добавлен: {key['added_date'][:10]}\n"

        if key['is_active'] and key.get('activated_date'):
            try:
                activation_date = datetime.strptime(key['activated_date'], "%Y-%m-%d %H:%M:%S")
                formatted_date = activation_date.strftime("%d.%m.%Y %H:%M")
                keys_text += f"📅 Активирован: {formatted_date}\n"
            except:
                keys_text += f"📅 Активирован: {key['activated_date']}\n"

            if key.get('activated_by_username'):
                keys_text += f"👤 Активировал: {key['activated_by_username']} (ID: {key['activated_by']})\n"

        keys_text += "────────────────────\n"

    # Разбиваем сообщение если слишком длинное
    if len(keys_text) > 4000:
        parts = [keys_text[i:i + 4000] for i in range(0, len(keys_text), 4000)]
        for part in parts:
            bot.send_message(call.message.chat.id, part)
    else:
        bot.send_message(call.message.chat.id, keys_text)

    bot.answer_callback_query(call.id)


# Админка: все пользователи
@bot.callback_query_handler(func=lambda call: call.data == "admin_all_users")
def admin_all_users(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
        return

    users = db.get_all_users()

    if not users:
        bot.send_message(call.message.chat.id, "Нет зарегистрированных пользователей.")
        bot.answer_callback_query(call.id)
        return

    users_text = "👥 Все пользователи:\n\n"
    for user in users:
        try:
            reg_date = datetime.strptime(user['registration_date'], "%Y-%m-%d %H:%M:%S")
            formatted_reg_date = reg_date.strftime("%d.%m.%Y")
        except:
            formatted_reg_date = user['registration_date']

        users_text += f"👤 {user.get('username', 'Без username')}\n"
        users_text += f"📛 Имя: {user.get('first_name', '')} {user.get('last_name', '')}\n"
        users_text += f"🆔 ID: {user['user_id']}\n"
        users_text += f"📅 Регистрация: {formatted_reg_date}\n"
        users_text += f"🔑 Активаций: {user['total_activations']}\n"

        if user.get('last_activation'):
            try:
                last_act = datetime.strptime(user['last_activation'], "%Y-%m-%d %H:%M:%S")
                formatted_last_act = last_act.strftime("%d.%m.%Y %H:%M")
                users_text += f"🕒 Последняя активация: {formatted_last_act}\n"
            except:
                pass

        users_text += "────────────────────\n"

    # Разбиваем сообщение если слишком длинное
    if len(users_text) > 4000:
        parts = [users_text[i:i + 4000] for i in range(0, len(users_text), 4000)]
        for part in parts:
            bot.send_message(call.message.chat.id, part)
    else:
        bot.send_message(call.message.chat.id, users_text)

    bot.answer_callback_query(call.id)


# Админка: статистика
@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
        return

    stats = db.get_statistics()

    stats_text = f"""📊 Статистика:

🔑 Всего ключей: {stats['total_keys']}
✅ Активировано: {stats['active_keys']}
❌ Не активировано: {stats['inactive_keys']}

👥 Всего пользователей: {stats['total_users']}
🔄 Всего активаций: {stats['total_activations']}"""

    bot.send_message(call.message.chat.id, stats_text)
    bot.answer_callback_query(call.id)


# Админка: рассылка
@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_start(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
        return

    bot.send_message(call.message.chat.id, "Введите сообщение для рассылки всем пользователям:")
    bot.set_state(call.from_user.id, AdminStates.waiting_for_broadcast, call.message.chat.id)
    bot.answer_callback_query(call.id)


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == AdminStates.waiting_for_broadcast)
def admin_broadcast_send(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    broadcast_text = message.text
    sent_count = 0
    failed_count = 0

    status_msg = bot.send_message(message.chat.id, "⏳ Начинаю рассылку...")

    # Получаем список всех пользователей для рассылки
    user_ids = db.broadcast_to_users()
    total_users = len(user_ids)

    # Обновляем статус
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        text=f"⏳ Рассылка начата...\nВсего пользователей: {total_users}\nОтправлено: 0\nОшибок: 0"
    )

    # Отправка всем пользователям
    for i, user_id in enumerate(user_ids, 1):
        try:
            bot.send_message(user_id, f"📢 Рассылка от администратора:\n\n{broadcast_text}")
            sent_count += 1

            # Обновляем статус каждые 10 пользователей
            if i % 10 == 0 or i == total_users:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_msg.message_id,
                    text=f"⏳ Рассылка...\nВсего пользователей: {total_users}\nОтправлено: {sent_count}\nОшибок: {failed_count}"
                )

        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
            failed_count += 1

        # Задержка для избежания лимитов
        import time
        time.sleep(0.05)

    # Финальное сообщение
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        text=f"✅ Рассылка завершена!\nОтправлено: {sent_count}\nНе удалось отправить: {failed_count}"
    )

    # Сбрасываем состояние
    bot.delete_state(message.from_user.id, message.chat.id)


# Админка: добавление ключа
@bot.callback_query_handler(func=lambda call: call.data == "admin_add_key")
def admin_add_key_start(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Доступ запрещен", show_alert=True)
        return

    bot.send_message(call.message.chat.id, "Введите ключ (например: FunTime_40B59A3D5C6E):")
    bot.set_state(call.from_user.id, AdminStates.waiting_for_new_key, call.message.chat.id)
    bot.answer_callback_query(call.id)


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == AdminStates.waiting_for_new_key)
def admin_add_key_process(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    key = message.text.strip()

    # Проверяем, существует ли уже ключ
    existing_key = db.get_key(key)
    if existing_key:
        bot.send_message(message.chat.id, "❌ Этот ключ уже существует. Введите другой ключ:")
        return

    bot.send_message(message.chat.id, "Введите адрес для WexSide:")
    bot.set_state(message.from_user.id, AdminStates.waiting_for_wexside, message.chat.id)

    # Сохраняем ключ в данных состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_key'] = key


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == AdminStates.waiting_for_wexside)
def admin_add_wexside(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    wexside = message.text.strip()
    bot.send_message(message.chat.id, "Введите обычный адрес прокси:")
    bot.set_state(message.from_user.id, AdminStates.waiting_for_address, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['wexside'] = wexside


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == AdminStates.waiting_for_address)
def admin_add_address(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    address = message.text.strip()
    bot.send_message(message.chat.id, "Введите логин:")
    bot.set_state(message.from_user.id, AdminStates.waiting_for_login, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['address'] = address


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == AdminStates.waiting_for_login)
def admin_add_login(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    login = message.text.strip()
    bot.send_message(message.chat.id, "Введите пароль:")
    bot.set_state(message.from_user.id, AdminStates.waiting_for_password, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['login'] = login


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == AdminStates.waiting_for_password)
def admin_add_password(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        bot.delete_state(message.from_user.id, message.chat.id)
        return

    password = message.text.strip()

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if not all(k in data for k in ['new_key', 'wexside', 'address', 'login']):
            bot.send_message(message.chat.id, "❌ Ошибка: данные потеряны. Начните заново.")
            bot.delete_state(message.from_user.id, message.chat.id)
            return

        # Добавляем ключ в базу данных
        success = db.add_key(
            key_value=data['new_key'],
            wexside_address=data['wexside'],
            address=data['address'],
            login=data['login'],
            password=password
        )

        if success:
            bot.send_message(message.chat.id, f"✅ Ключ {data['new_key']} успешно добавлен!")
        else:
            bot.send_message(message.chat.id, f"❌ Ошибка добавления ключа. Возможно, ключ уже существует.")

    # Сбрасываем состояние
    bot.delete_state(message.from_user.id, message.chat.id)


# Обработчик для сброса состояния при команде /cancel
@bot.message_handler(commands=['cancel'])
def cancel_handler(message: types.Message):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, "Действие отменено.", reply_markup=create_main_menu())


# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    print(f"База данных: rave_proxy.db")

    # Добавляем кастомный фильтр для состояний
    bot.add_custom_filter(StateFilter(bot))

    # Запускаем бота
    bot.infinity_polling()