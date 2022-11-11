from ...base_neko import BaseNeko
from typing import Dict, List
try:
    import ujson as json
except ImportError:
    import json

replacements: Dict[str, str]
languages: List[str]


async def startup(neko: BaseNeko):
    global replacements
    global languages
    with open('NekoGram/widgets/languages/replacements.json', 'r') as f:
        replacements = json.load(f)
    languages = list(neko.text_processor.texts.keys())
