from NekoGram import NekoRouter, Neko, Menu
from aiogram import types

ROUTER: NekoRouter = NekoRouter()


@ROUTER.formatter()
async def menu_admins(data: Menu, _: types.User, __: Neko):
    """
    A complete paginated menu example.
    """
    data.skip_media_validation = True
    data.media_type = 'photo'
    data.media = 'EXISTING_FILE_ID_AVAILABLE_FOR_TO_BOT'
    await data.build()
