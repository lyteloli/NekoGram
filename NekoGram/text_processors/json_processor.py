from typing import Union, Optional, Any, TextIO, Dict, List
from os.path import isdir, isfile
from io import TextIOWrapper
from os import listdir

try:
    import ujson as json
except ImportError:
    import json


def add_json_texts(required_texts: List[str], texts: Union[Dict[str, Any], TextIO, str] = 'translations',
                   lang: Optional[str] = None, validate_text_names: bool = True):
    """
    Assigns a required piece of texts to use later
    :param required_texts: List of required text names
    :param texts: Dictionary or JSON containing texts, path to a file or path to a directory containing texts
    :param lang: Language of the texts
    :param validate_text_names: True if validate text names
    """
    processed_texts: Dict[str, Dict[str, Any]] = dict()

    if not lang and isinstance(texts, str) and isdir(texts):  # Path to directory containing translations
        text_list = listdir(texts)
        for file in text_list:
            if file.endswith('.json'):
                with open(f'{texts}/{file}', 'r') as text_file:
                    processed_texts[file.replace('.json', '').split('_')[0]] = json.load(text_file)
    elif lang and isinstance(texts, str) and not isfile(texts):  # String JSON
        processed_texts[lang] = json.loads(texts)
    elif isinstance(texts, str) and isfile(texts):  # File path
        with open(texts, 'r') as file:
            processed_texts[lang] = json.load(file)
    elif isinstance(texts, TextIOWrapper):  # IO JSON file
        processed_texts[lang] = json.load(texts)
    else:
        raise ValueError('No valid text path, text or language supplied')

    for lang, text in processed_texts.items():  # Validate texts
        if validate_text_names and not all(elem in text for elem in required_texts):
            raise ValueError(f'The supplied translation for {lang} does not contain some of the required texts: '
                             f'{required_texts}')

    return processed_texts
