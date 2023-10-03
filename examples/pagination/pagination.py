from NekoGram import NekoRouter, Neko, Menu
from aiogram import types

ROUTER: NekoRouter = NekoRouter()


@ROUTER.formatter()
async def menu_admins(data: Menu, user: types.User, neko: Neko):
    """
    A complete paginated menu example.
    """
    # A nice way to keep track of user's current page in case they come back after switching to a different menu
    user_data = await neko.storage.get_user_data(user_id=user.id, bot_token=data.bot_token)
    if data.call_data is not None:
        user_data['menu_admins_offset'] = data.call_data
        offset = data.call_data
    else:
        offset = user_data.get('menu_admins_offset', 0)

    await neko.storage.set_user_data(data=user_data, user_id=user.id, replace=True, bot_token=data.bot_token)

    # Pagination implementation starts here
    found: int = 0  # Number of found items by specific query
    limit: int = 0  # Limit of items to display on a single page
    markup: types.InlineKeyboardMarkup = types.InlineKeyboardMarkup()
    async for item in neko.storage.select(  # MySQL query example
            'SELECT id, full_name FROM nekogram_users ORDER BY id DESC LIMIT %s OFFSET %s',
            (limit + 1, offset)
    ):
        found += 1
        if found == limit + 1:  # We break on limit + 1 to know whether we reached the end of distribution
            break

        markup.add(types.InlineKeyboardButton(
            text=f'{item.full_name} ({item.id})',
            callback_data=f'menu_admin_item#{item.id}'
        ))

    await data.add_pagination(
        offset=offset,
        found=found,
        limit=limit,
        shift_last=2  # Number of buttons to shift (from bottom to top)
    )
    await data.build(markup=markup)
