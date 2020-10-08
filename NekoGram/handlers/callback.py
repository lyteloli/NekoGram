from aiogram import exceptions as aiogram_exceptions, types
from typing import Optional
import NekoGram


async def menu_callback_query_handler(call: types.CallbackQuery):
    neko: NekoGram.Neko = call.conf['neko']
    call_data: Optional[int] = None
    new_call_data: str = call.data

    if '#' in call.data:  # If data is supplied
        call_data: str = call.data.split('#')[1]  # Just the data
        call_data = int(call_data) if call_data.isnumeric() else call_data  # Make data an int if it is numeric
        new_call_data = call.data.split('#')[0]  # Real call

    if new_call_data == 'menu_start':
        await neko.start_function(call)  # Start function should completely erase all user data
        return

    if '_step_' not in new_call_data and not await neko.check_text_exists(new_call_data):
        new_call_data += '_step_1'  # Add a step_1 to the name if such text doesn't exist

    data = await neko.build_text(text=new_call_data, user=call.from_user, formatter_extras={'call_data': call_data})

    if data.data.extras.get('answer_call'):  # If the call should be answered
        await call.answer(text=data.data.text, show_alert=True)
        if data.data.extras.get('answer_only'):  # If only the call answer is required
            return
    # If the current menu has a function, call it
    if not data.data.allowed_items and (data.function or (neko.functions.get(data.data.name))):
        call_or_message = call.message if neko.only_messages_in_functions else call
        if await neko.functions[data.function or new_call_data](data, call_or_message, neko) is True:
            await neko.start_function(call)  # Start function should completely erase all user data
            await call.answer()
        return

    await call.answer()

    if (isinstance(data.data.markup, types.InlineKeyboardMarkup) or data.data.markup is None) and not \
            data.data.extras.get('delete_and_send'):
        await call.message.edit_text(text=data.data.text, parse_mode=data.data.parse_mode,
                                     disable_web_page_preview=data.data.no_preview, reply_markup=data.data.markup)
    else:
        await neko.storage.set_user_data(user_id=call.from_user.id, data={'menu': new_call_data})
        try:
            await call.message.delete()
        except aiogram_exceptions.MessageCantBeDeleted:
            await call.message.edit_reply_markup()
        await call.message.reply(text=data.data.text, parse_mode=data.data.parse_mode,
                                 disable_web_page_preview=data.data.no_preview, reply=False,
                                 disable_notification=data.data.silent, reply_markup=data.data.markup)
