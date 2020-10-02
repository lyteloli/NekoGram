from NekoGram.storages.mysql.mysql import MySQLStorage
from NekoGram import Neko, Bot, Dispatcher
from aiogram import types
import os
# Don't forget to move NekoGram directory so it is a module.

# Constants
TOKEN: str = os.getenv('bot_token')
DATABASE_USER: str = os.getenv('database_user')
DATABASE_PASSWORD: str = os.getenv('database_password')

# Object constants
DATABASE: MySQLStorage = MySQLStorage(database='nekogram_test', user=DATABASE_USER, password=DATABASE_PASSWORD)
"""
Note: MySQLStorage is used here because it's a storage that's ready out of the box (BaseStorage).
Don't forget to create a database and import tables if you don't have a database already. 
You can find the SQL file in NekoGram/storages/mysql/sql.sql
"""
BOT: Bot = Bot(token=TOKEN)
DP: Dispatcher = Dispatcher(bot=BOT)
NEKO: Neko = Neko(dp=DP, storage=DATABASE)

NEKO.add_texts()  # Pass no parameters so texts will be pulled from translations/ directory


@NEKO.formatter(name='start')  # Start function formatter
async def _(data: Neko.BuildResponse, user: types.User, _: Neko):
    await data.data.assemble_markup(text_format=user.full_name)


NEKO.start_polling()  # Wake the bot and keep it alive
