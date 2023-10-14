from typing import Any

try:
    import ujson as json
except ImportError:
    import warnings
    from ..utils import NekoGramWarning

    warnings.warn('`ujson` is not installed, `JSONProcessor` may work slowly.', category=NekoGramWarning)
    import json

from .base_processor import BaseProcessor


class JSONProcessor(BaseProcessor):
    def __init__(self, validate_start: bool = True):
        """
        Initialize JSONProcessor.
        :param validate_start: Whether to check `start` object exists for each language.
        """
        super().__init__(validate_start=validate_start)

    @property
    def extensions(self) -> list[str]:
        return ['.json']

    def from_str(self, texts: str) -> dict[str, Any]:
        return json.loads(texts)
