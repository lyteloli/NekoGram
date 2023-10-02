import asyncio

from NekoGram.storages.sqlite import SQLiteStorage
from NekoGram.storages.mysql import MySQLStorage
from NekoGram.storages.pg import PGStorage


db: SQLiteStorage = SQLiteStorage(':memory:')
# db: SQLiteStorage = SQLiteStorage('local.db')
# db: MySQLStorage = MySQLStorage(database='database', user='root', password='password', host='localhost', port=3306)
# db: PGStorage = PGStorage(database='database', user='postgres', password='password', host='localhost', port=5432)


async def main():
    assert await db.acquire_pool()

    total_apply = 0
    for i in range(10):
        # id, lang, data, last_message_id, full_name, username
        total_apply += await db.apply(
            f"INSERT INTO nekogram_users VALUES ({i}, 'en', '{{}}', 0, 'full_name{i}', 'username{i}');"
        )

    users_select = [user async for user in db.select('SELECT * FROM nekogram_users;')]

    users_get = await db.get('SELECT * FROM nekogram_users;', fetch_all=True)
    assert users_select == users_get

    total_check = await db.check('SELECT * FROM nekogram_users;')
    assert total_check == total_apply

    total_delete = await db.apply('DELETE FROM nekogram_users;')
    assert total_check == total_delete

    assert await db.close_pool()


if __name__ == '__main__':
    asyncio.new_event_loop().run_until_complete(main())
