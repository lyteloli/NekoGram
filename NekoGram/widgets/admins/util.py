import os

try:
    import ujson as json
except ImportError:
    import json

from ...base_neko import BaseNeko


async def startup(neko: BaseNeko):
    sql_path = os.path.abspath(__file__).rstrip('util.py')
    with open(os.path.join(f'{sql_path}sql', 'tables.json'), 'r') as f:
        structure = json.load(f)
    await neko.storage.add_tables(structure, required_by='admins')
