import config
import sqlite3
from telegram import Update
from datetime import datetime
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)


ADD_MEME, ADD_COMMENT, ADD_COMMENT_TEXT = range(3)



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
    
    
    
    

# Обработчик команды /add_meme
async def add_meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Формат: первая строка "кто придумал", вторая "шутка" (строкой считается текст до \\n).'
    )
    return ADD_MEME

# Обработчик текстового сообщения для добавления шутки
async def handle_meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    lines = user_message.split('\n')
    
    if len(lines) < 2:
        await update.message.reply_text('Неверный формат. Нужно две строки: "кто придумал" и "шутка".')
        return ADD_MEME
    
    author = lines[0].strip()
    joke = lines[1].strip()
    
    user_id = update.message.from_user.id
        
    cursor.execute('INSERT INTO Memes (text, created_at, user_id) VALUES (?, ?, ?)', 
                   (joke, datetime.now(), user_id))
    connection.commit()
    
    await update.message.reply_text('Шутка успешно добавлена!')
    return ConversationHandler.END



async def add_comment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Введите ID шутки, которую хотите прокомментировать:')
    return ADD_COMMENT

# Обработчик текстового сообщения для комментария
async def handle_comment_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Проверяем, является ли сообщение числом (ID шутки)
    if not user_message.isdigit():
        await update.message.reply_text('ID шутки должен быть числом. Попробуйте снова.')
        return ADD_COMMENT
    
    meme_id = int(user_message)
    
    # Проверяем, существует ли шутка с таким ID
    cursor.execute('SELECT id FROM Memes WHERE id = ?', (meme_id,))
    if not cursor.fetchone():
        await update.message.reply_text('Шутка с таким ID не найдена. Попробуйте снова.')
        return ADD_COMMENT
    
    # Сохраняем ID шутки в контексте
    context.user_data['meme_id'] = meme_id
    
    await update.message.reply_text('Теперь введите ваш комментарий:')
    return ADD_COMMENT_TEXT

# Обработчик текстового сообщения для текста комментария
async def handle_comment_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment_text = update.message.text
    meme_id = context.user_data['meme_id']
    user_id = update.message.from_user.id
        
    cursor.execute('INSERT INTO Comments (meme_id, user_id, comment_text, created_at) VALUES (?, ?, ?, ?)', 
                   (meme_id, user_id, comment_text, datetime.now()))
    connection.commit()
    
    await update.message.reply_text('Комментарий успешно добавлен!')
    return ConversationHandler.END


async def get_jokes_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute('SELECT * FROM jokes')
    rows = cursor.fetchall()
    print("All jokes in the table:")
    all_rows=""
    for row in rows:
        all_rows += f"ID: {row[0]}, Who: {row[1]}, Joke: {row[2]}, Why: {row[3]}, Created At: {row[4]}\n"
        
    print(all_rows)
    await update.message.reply_text(all_rows)
    
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update:\n{update}\nCaused error:\n{context.error}')




def main():
    print('Starting bot...')
    app = Application.builder().token(config.TOKEN).build()
    
    # Conversations
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_meme', add_meme_command)],
        states={
            ADD_MEME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_meme)],
        },
        fallbacks=[],
    )
    comment_handler = ConversationHandler(
        entry_points=[CommandHandler('add_comment', add_comment_command)],
        states={
            ADD_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_comment_id),
            ],
            ADD_COMMENT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_comment_text),
            ],
        },
        fallbacks=[],
    )
    
    # Добавляем обработчики
    app.add_handler(conv_handler)
    app.add_handler(comment_handler)
    

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('get_jokes_all', get_jokes_all_command))


    # Errors
    app.add_error_handler(error)

    print('Polling...')
    app.run_polling(poll_interval=3)
    
    # close database connection
    connection.close()


if __name__ == '__main__':
    main()
    


