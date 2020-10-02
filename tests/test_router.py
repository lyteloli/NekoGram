from NekoGram import NekoRouter, Neko, Bot


def test_router():
    router = NekoRouter()
    neko = Neko(bot=Bot(token='0:0', validate_token=False))

    @router.formatter()
    async def test(_, __, ___):
        pass

    @router.function()
    async def test(_, __, ___):
        pass

    router.attach_router(neko)
    assert neko.format_functions == router.format_functions
    assert neko.functions == router.functions
