from aiogram import exceptions as aiogram_exceptions, types
from typing import List, Optional, Union
from contextlib import suppress
import NekoGram


def _convert_call_data(call_data: List[str]) -> Optional[Union[str, int]]:
    if len(call_data) == 1:
        return None

    call_data = call_data[1]
    return int(call_data) if call_data.isnumeric() else call_data


async def menu_callback_query_handler(call: types.CallbackQuery):
    neko: NekoGram.Neko = call.conf['neko']
    if call.data == 'menu_start':  # Reset user data on start
        await neko.storage.set_user_data(user_id=call.from_user.id)

    call_data = call.data.split(neko.callback_parameters_delimiter)
    current_menu = await neko.build_menu(name=call_data[0], obj=call, callback_data=_convert_call_data(call_data))
    if current_menu is None:
        return

    await neko.storage.set_user_menu(user_id=call.from_user.id, menu=current_menu.name)
    if not current_menu.filters and neko.functions.get(current_menu.name):  # Call function if it doesn't need input
        await neko.functions[current_menu.name](current_menu, call, neko)
        return

    try:
        await current_menu.edit_text()
    except aiogram_exceptions.InlineKeyboardExpected:
        with suppress(Exception):
            await call.message.delete()
        await current_menu.send_message()
    except (aiogram_exceptions.MessageCantBeEdited, aiogram_exceptions.MessageToEditNotFound):
        await current_menu.send_message()
