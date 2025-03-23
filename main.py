import config
import sqlite3
from datetime import datetime
from enum import IntEnum, auto
from telegram import Update
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
    GET_MEME_COMMENTS_MEME_ID = auto()



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
    await update.message.reply_text("Мемы какого пользователя показать? Введите Username или ID пользователя:")
    return UserStates.GET_USER_MEMES_BY_USERNAME_OR_ID

async def get_user_memes_by_username_or_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

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
async def add_comment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Введите ID мема, которую хотите прокомментировать:')
    return UserStates.ADD_COMMENT_MEME_ID

async def add_comment_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if not user_message.isdigit():
        await update.message.reply_text('ID мема должен быть числом. Попробуйте снова.')
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




async def get_meme_comments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Введите ID мема, комментарии которого хотите увидеть:')
    return UserStates.GET_MEME_COMMENTS_MEME_ID

async def get_meme_comments_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if not user_message.isdigit():
        await update.message.reply_text('ID мема должно быть числом. Попробуйте снова.')
        return UserStates.GET_MEME_COMMENTS_MEME_ID
    meme_id = int(user_message)
    
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


    
    
    
# ERROR
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'SOME ERROR HAPPENED\nUPDATE:\n{update}\nCAUSED ERROR:\n{context.error}')




def main():
    print('Starting bot...')
    app = Application.builder().token(config.TOKEN).build()
    
    # Conversations
    add_meme_conversation = ConversationHandler(
        entry_points=[CommandHandler('add_meme', add_meme_command)],
        states={
            UserStates.ADD_MEME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_meme_handler)],
        },
        fallbacks=[],
    )
    get_user_memes_conversation = ConversationHandler(
        entry_points=[CommandHandler('get_user_memes', get_user_memes_command)],
        states={
            UserStates.GET_USER_MEMES_BY_USERNAME_OR_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_memes_by_username_or_id_handler),
            ],
        },
        fallbacks=[],
    )
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
    get_comments_conversation = ConversationHandler(
        entry_points=[CommandHandler('get_meme_comments', get_meme_comments_command)],
        states={
            UserStates.GET_MEME_COMMENTS_MEME_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_meme_comments_id_handler),
            ],
        },
        fallbacks=[],
    )
    
    # Добавляем обработчики
    app.add_handler(add_meme_conversation)
    app.add_handler(get_user_memes_conversation)
    app.add_handler(add_comment_conversation)
    app.add_handler(get_comments_conversation)
    

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('get_my_memes', get_my_memes_command))


    # Errors
    app.add_error_handler(error)

    print('Polling...')
    app.run_polling(poll_interval=3)
    
    # close database connection
    connection.close()


if __name__ == '__main__':
    main()
    


