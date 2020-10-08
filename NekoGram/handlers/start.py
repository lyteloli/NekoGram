from aiogram import types
from asyncio import sleep
from typing import Union
import NekoGram


async def default_start_function(message: Union[types.Message, types.CallbackQuery]):
    neko: NekoGram.Neko = message.conf['neko']
    if not await neko.storage.check_user_exists(user_id=message.from_user.id):
        lang = message.from_user.language_code if message.from_user.language_code in neko.texts.keys() \
            else neko.storage.default_language
        await neko.storage.create_user(user_id=message.from_user.id, language=lang)
        await sleep(0.1)  # Sleep a bit to make sure user is added to the database
    else:
        # Completely erase user data
        await neko.storage.set_user_data(user_id=message.from_user.id)

    data = await neko.build_text(text='start', user=message.from_user)
    if isinstance(message, types.Message):
        await message.reply(text=data.data.text, parse_mode=data.data.parse_mode,
                            disable_web_page_preview=data.data.no_preview, reply=False,
                            disable_notification=data.data.silent, reply_markup=data.data.markup)
        await message.delete()
    else:
        await message.message.edit_text(text=data.data.text, disable_web_page_preview=data.data.no_preview,
                                        reply_markup=data.data.markup, parse_mode=data.data.parse_mode)
