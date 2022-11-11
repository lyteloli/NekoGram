from NekoGram import NekoRouter, Menu, Neko
from aiogram import types

ROUTER: NekoRouter = NekoRouter(name='languages')


@ROUTER.function()
async def widget_languages_set(data: Menu, call: types.CallbackQuery, neko: Neko):
    await neko.storage.set_user_language(language=data.call_data, user_id=call.from_user.id)
    data = await neko.build_menu(name=data.name, obj=call)
    await call.answer(text=data.text)
    data = await neko.build_menu(name=data.next_menu, obj=call)
    await data.build()
    await data.edit_text()
