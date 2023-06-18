from typing import Optional
import os

try:
    import ujson as json
except ImportError:
    import json

from ...base_neko import BaseNeko


async def startup(_: BaseNeko) -> Optional[dict]:
    with open(os.path.abspath(__file__).replace('util.py', 'replacements.json'), 'r') as f:
        replacements = json.load(f)
    return dict(languages_replacements=replacements)
