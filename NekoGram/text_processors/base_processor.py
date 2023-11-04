from typing import Union, Dict, Any, TextIO
from abc import ABC, abstractmethod
import os
import io


class BaseProcessor(ABC):
    def __init__(self, validate_start: bool = True):
        """
        Initialize BaseProcessor.
        :param validate_start: Whether to check `start` object exists for each language.
        """
        self.texts: Dict[str, Dict[str, Any]] = dict()
        self._validate_start: bool = validate_start

    @property
    @abstractmethod
    def extensions(self) -> list[str]:
        """
        List of file extensions to accept whe adding texts.
        :return: list of extensions, e.g. `['.ext1', '.ext2']`.
        """

    @abstractmethod
    def from_str(self, texts: str) -> dict[str, Any]:
        """
        Convert `str` texts to `dict`.
        :param texts: `str` texts to convert.
        :return: `dict` texts.
        """

    def add_texts(self, texts: Union[str, TextIO] = 'translations', is_widget: bool = False) -> None:
        """
        Assigns a required piece of texts to use later.
        :param texts: paths to a dir containing translations; path to a file containing translation;
        `typing.TextIO` object containing translation; `str` object containing translation.
        :param is_widget: True if texts is a widget texts, otherwise False.
        :return: None.
        """
        def gather(_texts: Union[str, TextIO] = 'translations', _is_widget: bool = False) -> None:
            if isinstance(_texts, io.TextIOWrapper):  # opened file
                gather(_texts.read(), _is_widget)
            elif os.path.isdir(_texts):  # path to the dir
                for entry in os.listdir(_texts):
                    gather(os.path.abspath(os.path.join(_texts, entry)), _is_widget)
            elif os.path.isfile(_texts):  # path to the file
                if any(_texts.endswith(ext) for ext in self.extensions):  # supported
                    with open(_texts, 'r', encoding='utf-8') as file:
                        gather(file, _is_widget)
            elif isinstance(_texts, str):  # str
                _texts = self.from_str(_texts)
                lang = _texts.get('lang')
                if lang is None:
                    raise ValueError('Some texts do not contain a language definition field "lang".')
                if _is_widget and lang not in self.texts.keys():  # ignore extra langs for widgets
                    return
                self.texts[lang] = self.texts.get(lang, dict()) | _texts
            else:
                raise NotImplementedError(f"Can't parse `texts` of type {type(_texts)} and value {_texts}.")
        gather(texts, is_widget)
        for lang, data in self.texts.items():
            if data.get('start') is None and self._validate_start:
                raise RuntimeError(f'"start" menu is undefined for {lang}! *Nervous paw shaking*')
