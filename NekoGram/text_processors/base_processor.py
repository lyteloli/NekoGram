from typing import Union, Dict, Any, TextIO


class BaseProcessor:
    @staticmethod
    def add_texts(texts: Union[Dict[str, Any], TextIO, str] = 'translations'):
        pass

    @property
    def processor_type(self) -> str:
        return 'base'
