from typing import Union, Optional, Dict, Any


class BaseStorage:
    def __init__(self):
        pass

    async def get_user_language(self, user_id: int) -> Optional[str]:
        return ''

    async def set_user_data(self, user_id: int, data: Optional[Dict[str, Any]] = None,
                            replace: bool = False) -> Dict[str, Any]:
        return dict()

    async def get_user_data(self, user_id: int) -> Union[Dict[str, Any], bool]:
        return False

    async def check_user_exists(self, user_id: int) -> bool:
        return False

    async def create_user(self, user_id: int, language: str):
        pass
