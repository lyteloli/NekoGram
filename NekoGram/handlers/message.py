from typing import Union, Dict, Any
from aiogram import types
import NekoGram


async def menu_message_handler(message: types.Message):
    neko: NekoGram.Neko = message.conf['neko']
    user_data: Union[Dict[str, Any], bool] = await neko.storage.get_user_data(user_id=message.from_user.id)
    current_menu_name: str = user_data.get('menu')
    current_menu = await neko.build_text(text=current_menu_name, user=message.from_user, no_formatting=True)
    current_menu_step: int = int(current_menu_name.split('_step_')[1]) if '_step_' in current_menu_name else 0
    next_menu_name: str = current_menu_name.split('_step_')[0] + '_step_' + str(current_menu_step + 1)

    if message.text and message.text.startswith('⬅️'):  # If BACK button was clicked
        await neko.delete_markup(user_id=message.from_user.id)
        user_data.pop(current_menu_name, None)  # Delete items gathered by the current menu
        if current_menu.back_menu:
            prev_menu_name = current_menu.back_menu
        elif current_menu_step > 1:  # Menu steps start from 1
            prev_menu_name = current_menu_name.split('_step_')[0] + '_step_' + str(current_menu_step - 1)
        else:
            await neko.start_function(message)  # Start function should completely erase all user data
            return

        data = await neko.build_text(text=prev_menu_name, user=message.from_user)
        user_data['menu'] = prev_menu_name if data.function or data.data.allowed_items else None
        await neko.storage.set_user_data(data=user_data, user_id=message.from_user.id, replace=True)
        await message.reply(text=data.data.text, parse_mode=data.data.parse_mode,
                            disable_web_page_preview=data.data.no_preview, reply=False,
                            disable_notification=data.data.silent, reply_markup=data.data.markup)
        return

    if current_menu.data.allowed_items:  # If any item is required to proceed to the next menu step
        ok: bool = False
        for item in current_menu.data.allowed_items:  # Check filters
            callback = await neko.get_content_filter(name=item)
            if callback and await callback(message):
                ok = True
                break

        if not ok and message.content_type not in current_menu.data.allowed_items:
            data = await neko.build_text(text='wrong_content_type', user=message.from_user)
            await message.reply(text=data.data.text, parse_mode=data.data.parse_mode,
                                disable_web_page_preview=data.data.no_preview, reply=False,
                                disable_notification=data.data.silent, reply_markup=data.data.markup)
            return

        # Update user data
        if isinstance(message[message.content_type], list):
            result = message[message.content_type][-1].to_python()
        elif isinstance(message[message.content_type], str):
            result = {'text': message[message.content_type]}
        else:
            result = message[message.content_type].to_python()
        user_data[current_menu_name] = result
        user_data[current_menu_name + '_content_type'] = message.content_type

    if await neko.check_text_exists(next_menu_name):
        user_data['menu'] = next_menu_name
    await neko.storage.set_user_data(data=user_data, user_id=message.from_user.id, replace=True)

    if neko.functions.get(current_menu_name):  # If the current menu has a function, call it
        await neko.delete_markup(user_id=message.from_user.id)
        if await neko.functions[current_menu_name](current_menu, message, neko) is True:
            await neko.start_function(message)  # Start function should completely erase all user data
        return

    if not await neko.check_text_exists(next_menu_name):  # Check if text exists, use start if not
        await neko.start_function(message)  # Start function should completely erase all user data
        return

    next_menu = await neko.build_text(text=next_menu_name, user=message.from_user)

    await message.reply(text=next_menu.data.text, parse_mode=next_menu.data.parse_mode,
                        disable_web_page_preview=next_menu.data.no_preview, reply=False,
                        disable_notification=next_menu.data.silent, reply_markup=next_menu.data.markup)
