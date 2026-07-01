import pymysql
from dbutils.pooled_db import PooledDB
from pymysql.cursors import DictCursor

from app.infrastructure.config.settings import settings

_connection_pool: PooledDB | None = None


def init_connection_pool() -> None:
    global _connection_pool
    if _connection_pool is not None:
        return

    _connection_pool = PooledDB(
        creator=pymysql,
        maxconnections=10,
        mincached=1,
        maxcached=5,
        blocking=True,
        ping=1,
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def close_connection_pool() -> None:
    global _connection_pool
    if _connection_pool is None:
        return

    _connection_pool.close()
    _connection_pool = None


def get_connection():
    if _connection_pool is None:
        init_connection_pool()

    return _connection_pool.connection()
