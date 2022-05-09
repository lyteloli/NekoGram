from typing import Union, Dict, Callable, Awaitable
from aiogram.types import Message, CallbackQuery
import re


async def _to_message(obj: Union[Message, CallbackQuery]) -> Message:
    if isinstance(obj, CallbackQuery):
        obj = obj.message
    return obj


async def is_any(_: Union[Message, CallbackQuery]) -> bool:
    """
    Check if message is of any content types available
    :return: Always True
    """
    return True


async def is_int(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message text can be converted to an integer
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.text and obj.text.isdigit()


async def is_int_neg(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message text can be converted to a negative integer
    :return: True if so
    """
    try:
        return int(obj.text) < 0
    except ValueError:
        return False


async def is_int_pos(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message text can be converted to a positive integer
    :return: True if so
    """
    try:
        return int(obj.text) > 0
    except ValueError:
        return False


async def is_int_smaller_than(obj: Union[Message, CallbackQuery], smaller_than: int = 0) -> bool:
    """
    Checks if message text can be converted to an integer smaller than N
    :return: True if so
    """
    try:
        return int(obj.text) < smaller_than
    except ValueError:
        return False


async def is_int_greater_than(obj: Union[Message, CallbackQuery], greater_than: int = 0) -> bool:
    """
    Checks if message text can be converted to an integer smaller than N
    :return: True if so
    """
    try:
        return int(obj.text) > greater_than
    except ValueError:
        return False


async def is_float(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message text can be converted to a float
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.text and obj.text.isnumeric()


async def is_text(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message content is text
    :return: True if so
    """
    obj = await _to_message(obj)
    return bool(obj.text)


async def is_text_shorter_than(obj: Union[Message, CallbackQuery], shorter_than: int = 0) -> bool:
    """
    Checks if message content is text and is shorter than N characters (inclusive)
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.text and len(obj.text) <= shorter_than


async def is_photo(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message content is a photo
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.content_type == 'photo'


async def is_video(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message content is a video
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.content_type == 'video'


async def is_animation(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message content is a GIF
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.content_type == 'animation'


async def is_http_url(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message text is an HTTP URL
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.text and obj.text.startswith('http://')


async def is_https_url(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message text is an HTTPS URL
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.text and obj.text.startswith('https://')


async def is_tg_url(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message text is a Telegram URL
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.text and obj.text.startswith('tg://')


async def is_url(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message text is an HTTP/HTTPS/Telegram URL
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.text and obj.text.startswith(('http://', 'https://', 'tg://'))


async def is_email(obj: Union[Message, CallbackQuery]) -> bool:
    """
    Checks if message text is an email
    :return: True if so
    """
    obj = await _to_message(obj)
    return obj.text and re.match(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', obj.text)


def _filters_to_dict() -> Dict[str, Callable[[Union[Message, CallbackQuery]], Awaitable[bool]]]:
    """
    Represents all default type filters as a dict
    :return: Type filters dict
    """
    return {'int': is_int, 'int+': is_int_pos, 'int-': is_int_neg, 'int<': is_int_greater_than,
            'int>': is_int_greater_than, 'float': is_float, 'text': is_text, 'photo': is_photo, 'video': is_video,
            'animation': is_animation, 'gif': is_animation, 'http_url': is_http_url, 'https_url': is_https_url,
            'tg_url': is_tg_url, 'url': is_url, 'email': is_email, 'any': is_any}
