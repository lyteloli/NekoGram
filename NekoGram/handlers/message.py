from aiogram import types, exceptions as aiogram_exc
from typing import Union, Dict, Any, Optional
from contextlib import suppress

from ..logger import LOGGER
import NekoGram


async def _start_handler(message: types.Message):
    neko: NekoGram.Neko = message.conf['neko']

    if not await neko.storage.check_user_exists(user_id=message.from_user.id):
        lang = message.from_user.language_code
        await neko.storage.create_user(
            user_id=message.from_user.id,
            language=lang if lang in neko.text_processor.texts.keys() else neko.storage.default_language,
            name=message.from_user.full_name,
            username=message.from_user.username
        )
    else:  # Reset user data on start
        await neko.storage.set_user_data(user_id=message.from_user.id, bot_token=message.conf.get('request_token'))

    current_menu = await neko.build_menu(name='start', obj=message)
    if current_menu is None:
        raise RuntimeError(f'Start menu formatter should not break execution')

    if neko.functions.get('start'):
        await neko.functions['start'](current_menu, message, neko)
        return
    else:
        await current_menu.send_message()
        if neko.delete_messages:
            with suppress(Exception):
                await message.delete()


async def menu_message_handler(message: types.Message):
    neko: NekoGram.Neko = message.conf['neko']

    bot_token: Optional[str] = message.conf.get('request_token')
    user_data: Union[Dict[str, Any], bool] = await neko.storage.get_user_data(
        user_id=message.from_user.id, bot_token=bot_token
    )
    current_menu = await neko.build_menu(name=user_data['menu'], obj=message)  # Prebuild current menu
    if current_menu is None:
        return

    if message.text and message.text.startswith('⬅️'):  # Back button clicked
        await neko.storage.set_user_menu(
            menu=current_menu.prev_menu or None, user_id=message.from_user.id, bot_token=bot_token
        )
        if neko.delete_messages:
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

        if neko.delete_messages:
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
        user_data = await neko.storage.set_user_data(
            data={current_menu.name: message.to_python(), 'menu': current_menu.next_menu},
            user_id=message.from_user.id,
            bot_token=bot_token
        )

    if neko.functions.get(current_menu.name):  # Execute a function if present
        if current_menu.intermediate_menu:  # Show an intermediate menu
            intermediate_menu = await neko.build_menu(name=current_menu.intermediate_menu, obj=message)
            intermediate_menu.markup = None
            await intermediate_menu.send_message()
        await neko.functions[current_menu.name](current_menu, message, neko)
        if user_data.get('menu') == current_menu.name:
            await neko.storage.set_user_menu(user_id=message.from_user.id, bot_token=bot_token)
        return

    if neko.next_menu_handlers.get(current_menu.name):
        current_menu.next_menu = await neko.next_menu_handlers[current_menu.name](current_menu)

    if not current_menu.next_menu:  # Next step is undefined
        if current_menu.name == 'start':
            return
        LOGGER.warning(f'Unhandled user input for {current_menu.name}. *confused meow*')
        await neko.storage.set_user_menu(menu=current_menu.name, user_id=message.from_user.id, bot_token=bot_token)
    next_menu = await neko.build_menu(name=current_menu.next_menu or 'start', obj=message)
    if next_menu is None:
        return

    if neko.functions.get(next_menu.name) and not next_menu.filters:  # Execute a function in next menu if no filters
        await neko.functions[next_menu.name](next_menu, message, neko)

    await next_menu.send_message()
