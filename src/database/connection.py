"""
Database Connection Manager

PostgreSQLへの接続を管理します。
環境変数から設定を読み込み、接続プールを提供します。
"""

import psycopg2
from psycopg2 import pool
import yaml
import os
from pathlib import Path
from typing import Optional
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """データベース接続マネージャー"""

    def __init__(self, config_path: str = "config/database.yml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.connection_pool: Optional[pool.SimpleConnectionPool] = None

    def _load_config(self) -> dict:
        """設定ファイルを読み込み、環境変数を展開"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 環境変数を展開
        db_config = config['postgresql']
        resolved_config = {}

        for key, value in db_config.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                # ${VAR_NAME:-default} 形式の解析
                var_spec = value[2:-1]  # ${} を削除

                if ':-' in var_spec:
                    var_name, default = var_spec.split(':-')
                    resolved_config[key] = os.getenv(var_name, default)
                else:
                    var_name = var_spec
                    env_value = os.getenv(var_name)
                    if env_value is None:
                        raise ValueError(f"Environment variable {var_name} is not set")
                    resolved_config[key] = env_value
            else:
                resolved_config[key] = value

        return resolved_config

    def get_connection(self):
        """単一接続を取得"""
        try:
            conn = psycopg2.connect(**self.config)
            logger.info("Database connection established")
            return conn
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def create_pool(self, min_conn: int = 2, max_conn: int = 10):
        """コネクションプールを作成"""
        try:
            self.connection_pool = pool.SimpleConnectionPool(
                min_conn,
                max_conn,
                **self.config
            )
            logger.info(f"Connection pool created (min={min_conn}, max={max_conn})")
        except psycopg2.Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    def get_connection_from_pool(self):
        """プールから接続を取得"""
        if self.connection_pool is None:
            raise RuntimeError("Connection pool is not initialized. Call create_pool() first.")

        conn = self.connection_pool.getconn()
        logger.debug("Connection acquired from pool")
        return conn

    def return_connection_to_pool(self, conn):
        """プールに接続を返却"""
        if self.connection_pool is None:
            raise RuntimeError("Connection pool is not initialized.")

        self.connection_pool.putconn(conn)
        logger.debug("Connection returned to pool")

    def close_pool(self):
        """コネクションプールを閉じる"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Connection pool closed")

    @contextmanager
    def get_cursor(self):
        """
        コンテキストマネージャーでカーソルを取得

        Usage:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM prefectures")
                results = cursor.fetchall()
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            cursor.close()
            conn.close()


# Singleton instance
_db_connection: Optional[DatabaseConnection] = None


def get_db_connection() -> DatabaseConnection:
    """シングルトンのDB接続インスタンスを取得"""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection
