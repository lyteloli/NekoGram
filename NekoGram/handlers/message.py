from aiogram import types, exceptions as aiogram_exc
from typing import Union, Dict, Any
from contextlib import suppress
from ..logger import LOGGER
import NekoGram


async def default_start_handler(message: types.Message):
    neko: NekoGram.Neko = message.conf['neko']

    if not await neko.storage.check_user_exists(user_id=message.from_user.id):
        lang = message.from_user.language_code
        await neko.storage.create_user(user_id=message.from_user.id,
                                       language=lang if lang in neko.text_processor.texts.keys() else None)
    else:  # Reset user data on start
        await neko.storage.set_user_data(user_id=message.from_user.id)

    current_menu = await neko.build_menu(name='start', obj=message)
    if current_menu is None:
        raise RuntimeError(f'Start menu formatter should not break execution')

    if neko.functions.get('start'):
        await neko.functions['start'](current_menu, message, neko)
        return
    await current_menu.send_message()
    with suppress(Exception):
        await message.delete()


async def menu_message_handler(message: types.Message):
    neko: NekoGram.Neko = message.conf['neko']
    if message.text == '/start':  # Start case
        await default_start_handler(message)
        return

    user_data: Union[Dict[str, Any], bool] = await neko.storage.get_user_data(user_id=message.from_user.id)
    current_menu = await neko.build_menu(name=user_data['menu'], obj=message)  # Prebuild current menu
    if current_menu is None:
        return

    if message.text and message.text.startswith('⬅️'):  # Back button clicked
        await neko.storage.set_user_menu(menu=current_menu.prev_menu or None, user_id=message.from_user.id)
        last_message_id = await neko.storage.get_last_message_id(user_id=message.from_user.id)
        try:
            await neko.bot.delete_message(chat_id=message.from_user.id, message_id=last_message_id)
        except (aiogram_exc.MessageCantBeDeleted, aiogram_exc.MessageToDeleteNotFound):
            with suppress(Exception):
                await neko.bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=last_message_id)

        if neko.prev_menu_handlers.get(current_menu.name):
            current_menu.prev_menu = await neko.prev_menu_handlers[current_menu.name](current_menu)
        menu = await neko.build_menu(name=current_menu.prev_menu or 'start', obj=message)
        if menu is None:
            return
        await menu.send_message()

        with suppress(Exception):
            await message.delete()
        return

    if current_menu.filters:  # Check filters
        filters_passed: bool = False
        for f in current_menu.filters:
            if await neko.filters[f](message):
                filters_passed = True
                break
    else:
        filters_passed: bool = True

    if not filters_passed:  # Wrong data provided
        current_menu.text = current_menu.validation_error
        await current_menu.send_message()
        return
    else:
        await neko.storage.set_user_data(data={current_menu.name: message.to_python(),
                                               'menu': current_menu.next_menu}, user_id=message.from_user.id)

    if neko.functions.get(current_menu.name):  # Execute a function if present
        await neko.functions[current_menu.name](current_menu, message, neko)
        return

    if neko.next_menu_handlers.get(current_menu.name):
        current_menu.next_menu = await neko.next_menu_handlers[current_menu.name](current_menu)

    if not current_menu.next_menu:  # Next step is undefined
        LOGGER.warning(f'Unhandled user input for {current_menu.name}. *confused meow*')
    next_menu = await neko.build_menu(name=current_menu.next_menu or 'start', obj=message)
    if next_menu is None:
        return

    if neko.functions.get(next_menu.name) and not next_menu.filters:  # Execute a function in next menu if no filters
        await neko.functions[next_menu.name](next_menu, message, neko)

    await next_menu.send_message()
