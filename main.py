import config
import sqlite3
from datetime import datetime
from enum import IntEnum, auto
from telegram import Update
from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)


class UserStates(IntEnum):
    ADD_MEME = auto()
    GET_USER_MEMES_BY_USERNAME_OR_ID = auto()
    ADD_COMMENT_MEME_ID = auto()
    ADD_COMMENT_TEXT = auto()
    RATE_MEME_ID = auto()
    RATE_MEME_VALUE = auto()



# database
connection = sqlite3.connect('MemesDB.db')
cursor = connection.cursor()

# Users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY,
        username VARCHAR(32)
    )
''')
# Memes table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Memes (
        id INTEGER PRIMARY KEY,
        text TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES Users(id)
    )
''')
# Tags table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Tags (
        id INTEGER PRIMARY KEY,
        tag_name VARCHAR(25) NOT NULL UNIQUE
    )
''')
# Meme_Tags table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Meme_Tags (
        meme_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        PRIMARY KEY (meme_id, tag_id),
        FOREIGN KEY (meme_id) REFERENCES Memes(id),
        FOREIGN KEY (tag_id) REFERENCES Tags(id)
    )
''')
# Ratings table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Ratings (
        id INTEGER PRIMARY KEY,
        meme_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        FOREIGN KEY (meme_id) REFERENCES Memes(id),
        FOREIGN KEY (user_id) REFERENCES Users(id)
    )
''')
# Comments table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Comments (
        id INTEGER PRIMARY KEY,
        meme_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        comment_text TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        FOREIGN KEY (meme_id) REFERENCES Memes(id),
        FOREIGN KEY (user_id) REFERENCES Users(id)
    )
''')




async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    
    cursor.execute('SELECT id FROM Users WHERE id = ?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO Users (id, username) VALUES (?, ?)', (user_id, username))
        connection.commit()
        await update.message.reply_text(f"Приятно познакомиться, {username}")
    else:
        await update.message.reply_text("Давно не виделись")
    
    
    
    

# MEME
# ADD
async def add_meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Формат: первая строка "кто придумал", вторая "шутка" (строкой считается текст до \\n).'
    )
    return UserStates.ADD_MEME

async def add_meme_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    lines = user_message.split('\n')
    
    if len(lines) < 2:
        await update.message.reply_text('Неверный формат. Нужно две строки: "кто придумал" и "шутка".')
        return UserStates.ADD_MEME
    
    author = lines[0].strip()
    joke = lines[1].strip()
    
    user_id = update.message.from_user.id
        
    cursor.execute('INSERT INTO Memes (text, created_at, user_id) VALUES (?, ?, ?)', 
                   (joke, datetime.now(), user_id))
    connection.commit()
    
    await update.message.reply_text('Мем успешно добавлена!')
    return ConversationHandler.END


# GET
async def get_all_memes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    cursor.execute('SELECT text, created_at, id FROM Memes')
    memes = cursor.fetchall()
    
    if not memes:
        await update.message.reply_text("Пока нет добавленных мемов.")
        return
    
    memes_list = "Все мемы:\n"
    for meme in memes:
        memes_list += f"Текст: {meme[0]}\nДата создания: {meme[1]}\nID: {meme[2]}\n\n"
    
    await update.message.reply_text(memes_list)
    
    
async def get_my_memes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    cursor.execute('SELECT text, created_at, id FROM Memes WHERE user_id = ?', (user_id,))
    memes = cursor.fetchall()
    
    if not memes:
        await update.message.reply_text("У вас нет добавленных мемов.")
        return
    
    memes_list = "Ваши мемы:\n"
    for meme in memes:
        memes_list += f"Текст: {meme[0]}\nДата создания: {meme[1]}\nID: {meme[2]}\n\n"
    
    await update.message.reply_text(memes_list)


async def get_user_memes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('Укажите username или user_id после команды, например: /get_user_memes 123')
        return
    
    user_input = context.args[0]
    if user_input.isdigit():
        user_id = int(user_input)
        cursor.execute('SELECT text, created_at, id FROM Memes WHERE user_id = ?', (user_id,))
    else:
        cursor.execute('SELECT id FROM Users WHERE username = ?', (user_input,))
        user_data = cursor.fetchone()
        if not user_data:
            await update.message.reply_text("Пользователь с таким username не найден.")
            return ConversationHandler.END
        user_id = user_data[0]
        cursor.execute('SELECT text, created_at, id FROM Memes WHERE user_id = ?', (user_id,))

    memes = cursor.fetchall()

    if not memes:
        await update.message.reply_text("У этого пользователя пока нет добавленных мемов.")
        return ConversationHandler.END

    memes_list = "Мемы этого пользователя:\n"
    for meme in memes:
        memes_list += f"Текст: {meme[0]}\nДата создания: {meme[1]}\nID: {meme[2]}\n\n"

    await update.message.reply_text(memes_list)
    return ConversationHandler.END




# COMMENT
# ADD
async def add_comment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Введите meme_id, который хотите прокомментировать:')
    return UserStates.ADD_COMMENT_MEME_ID

async def add_comment_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if not user_message.isdigit():
        await update.message.reply_text('meme_id должно быть числом. Попробуйте снова.')
        return UserStates.ADD_COMMENT_MEME_ID
    meme_id = int(user_message)
    
    cursor.execute('SELECT id FROM Memes WHERE id = ?', (meme_id,))
    if not cursor.fetchone():
        await update.message.reply_text('Мем с таким ID не найдена. Попробуйте снова.')
        return UserStates.ADD_COMMENT_MEME_ID
    
    context.user_data['meme_id'] = meme_id
    
    await update.message.reply_text('Теперь введите ваш комментарий:')
    return UserStates.ADD_COMMENT_TEXT

async def add_comment_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment_text = update.message.text
    meme_id = context.user_data['meme_id']
    user_id = update.message.from_user.id
        
    cursor.execute('INSERT INTO Comments (meme_id, user_id, comment_text, created_at) VALUES (?, ?, ?, ?)', 
                   (meme_id, user_id, comment_text, datetime.now()))
    connection.commit()
    
    await update.message.reply_text('Комментарий успешно добавлен!')
    return ConversationHandler.END



# GET
async def get_meme_comments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('Укажите meme_id после команды, например: /get_meme_comments 123')
        return
    meme_id = context.args[0]
    if not meme_id.isdigit():
        await update.message.reply_text('meme_id должно быть числом. Попробуйте снова.')
        return
    meme_id = int(meme_id)
    
    cursor.execute('SELECT id FROM Memes WHERE id = ?', (meme_id,))
    if not cursor.fetchone():
        await update.message.reply_text('Мем с таким ID не найдена. Попробуйте снова.')
        return UserStates.GET_MEME_COMMENTS_MEME_ID
    
    cursor.execute('SELECT comment_text, created_at, user_id, id FROM Comments WHERE meme_id = ?', (meme_id,))
    comments = cursor.fetchall()
    if not comments:
        await update.message.reply_text("У этого пользователя пока нет добавленных мемов.")
        return ConversationHandler.END

    comments_list = "Мемы этого пользователя:\n"
    for comment in comments:
        comments_list += f"Текст: {comment[0]}\nДата создания: {comment[1]}\nID пользователя: {comment[2]}\nID комментария: {comment[3]}\n\n"
    
    await update.message.reply_text(comments_list)
    return ConversationHandler.END






# RATING
# ADD
async def rate_meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Введите meme_id, который хотите оценить:')
    return UserStates.RATE_MEME_ID

async def rate_meme_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if not user_message.isdigit():
        await update.message.reply_text('meme_id должно быть числом. Попробуйте снова.')
        return UserStates.RATE_MEME_ID
    
    meme_id = int(user_message)
    
    cursor.execute('SELECT id FROM Memes WHERE id = ?', (meme_id,))
    if not cursor.fetchone():
        await update.message.reply_text('Мем с таким ID не найден. Попробуйте снова.')
        return UserStates.RATE_MEME_ID
    
    user_id = update.message.from_user.id
    cursor.execute('SELECT id FROM Ratings WHERE meme_id = ? AND user_id = ?', (meme_id, user_id))
    if cursor.fetchone():
        await update.message.reply_text('Вы уже оценивали этот мем. Хотите изменить оценку? (да/нет)')
        context.user_data['meme_id'] = meme_id
        context.user_data['update_rating'] = True
        return UserStates.RATE_MEME_VALUE
    
    context.user_data['meme_id'] = meme_id
    context.user_data['update_rating'] = False
    
    await update.message.reply_text('Введите вашу оценку (от 1 до 5):')
    return UserStates.RATE_MEME_VALUE

async def rate_meme_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if not user_message.isdigit() or int(user_message) < 1 or int(user_message) > 5:
        await update.message.reply_text('Оценка должна быть числом от 1 до 5. Попробуйте снова.')
        return UserStates.RATE_MEME_VALUE
    
    rating = int(user_message)
    meme_id = context.user_data['meme_id']
    user_id = update.message.from_user.id
    
    if context.user_data.get('update_rating', False):
        cursor.execute('''
            UPDATE Ratings 
            SET rating = ?
            WHERE meme_id = ? AND user_id = ?
        ''', (rating, meme_id, user_id))
    else:
        cursor.execute('''
            INSERT INTO Ratings (meme_id, user_id, rating)
            VALUES (?, ?, ?)
        ''', (meme_id, user_id, rating))
    
    connection.commit()
    
    await update.message.reply_text('Спасибо за вашу оценку!')
    return ConversationHandler.END

# GET
async def get_meme_rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('Укажите meme_id после команды, например: /get_meme_rating 123')
        return
    
    meme_id = context.args[0]
    
    if not meme_id.isdigit():
        await update.message.reply_text('meme_id должен быть числом.')
        return
    
    cursor.execute('''
        SELECT AVG(rating), COUNT(rating)
        FROM Ratings
        WHERE meme_id = ?
    ''', (int(meme_id),))
    
    result = cursor.fetchone()
    avg_rating, count = result if result else (None, 0)
    
    if avg_rating is None:
        await update.message.reply_text('Этот мем еще не оценивали.')
    else:
        await update.message.reply_text(
            f'Средняя оценка мема: {avg_rating:.1f}\n'
            f'Количество оценок: {count}'
        )

    
    
    
# ERROR
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'SOME ERROR HAPPENED\nUPDATE:\n{update}\nCAUSED ERROR:\n{context.error}')



# HELP
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Доступные команды:
/start - Начать работу с ботом
/help - Показать список всех команд
/add_meme - Добавить новый мем
/get_all_memes - Показать все мемы
/get_my_memes - Показать все ваши мемы
/get_user_memes - Показать мемы другого пользователя $name_or_id
/add_comment - Добавить комментарий к мему
/get_meme_comments - Показать комментарии к мему $meme_id
/rate_meme - Оценить мем (от 1 до 5)
/get_meme_rating - Показать рейтинг мема $meme_id
"""
    await update.message.reply_text(help_text)


# AVAILABLE COMMANDS
async def set_bot_commands(application: Application):
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("help", "Показать список всех команд"),
        BotCommand("add_meme", "Добавить новый мем"),
        BotCommand("get_all_memes", "Показать все мемы"),
        BotCommand("get_my_memes", "Показать все ваши мемы"),
        BotCommand("get_user_memes", "Показать мемы пользователя $name_or_id"),
        BotCommand("add_comment", "Добавить комментарий к мему"),
        BotCommand("get_meme_comments", "Показать комментарии к мему $meme_id"),
        BotCommand("rate_meme", "Оценить мем (от 1 до 5)"),
        BotCommand("get_meme_rating", "Показать рейтинг мема $meme_id"),
    ]
    await application.bot.set_my_commands(commands)




# MAIN
def main():
    print('Starting bot...')
    app = Application.builder().token(config.TOKEN).post_init(set_bot_commands).build()



    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('get_my_memes', get_my_memes_command))
    app.add_handler(CommandHandler('get_user_memes', get_user_memes_command))
    app.add_handler(CommandHandler('get_all_memes', get_all_memes_command))
    app.add_handler(CommandHandler('get_meme_comments', get_meme_comments_command))
    app.add_handler(CommandHandler('get_meme_rating', get_meme_rating_command))
    
    

    # Сonversations
    # memes
    add_meme_conversation = ConversationHandler(
        entry_points=[CommandHandler('add_meme', add_meme_command)],
        states={
            UserStates.ADD_MEME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_meme_handler)],
        },
        fallbacks=[],
    )
    app.add_handler(add_meme_conversation)
    # comments
    add_comment_conversation = ConversationHandler(
        entry_points=[CommandHandler('add_comment', add_comment_command)],
        states={
            UserStates.ADD_COMMENT_MEME_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_comment_id_handler),
            ],
            UserStates.ADD_COMMENT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_comment_text_handler),
            ],
        },
        fallbacks=[],
    )
    app.add_handler(add_comment_conversation)
    # ratings
    rate_meme_conversation = ConversationHandler(
        entry_points=[CommandHandler('rate_meme', rate_meme_command)],
        states={
            UserStates.RATE_MEME_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, rate_meme_id_handler),
            ],
            UserStates.RATE_MEME_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, rate_meme_value_handler),
            ],
        },
        fallbacks=[],
    )
    app.add_handler(rate_meme_conversation)



    # Errors
    app.add_error_handler(error)

    print('Polling...')
    app.run_polling(poll_interval=3)
    
    connection.close()


if __name__ == '__main__':
    main()
    


