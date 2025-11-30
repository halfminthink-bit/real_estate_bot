#!/usr/bin/env python3
"""
Database Setup Script

データベースの初期化とマスタデータ投入を行います。

Usage:
    python scripts/01_setup_database.py
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import get_db_connection
import logging
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def execute_schema(cursor, schema_path: Path):
    """スキーマファイルを実行"""
    logger.info(f"Executing schema: {schema_path}")

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    try:
        cursor.execute(schema_sql)
        logger.info("✅ Schema executed successfully")
    except Exception as e:
        logger.error(f"❌ Schema execution failed: {e}")
        raise


def insert_master_data(cursor):
    """マスタデータを投入"""
    logger.info("Inserting master data...")

    # 都道府県マスタ
    prefectures = [
        ('13', '東京都', 'Tokyo'),
        ('14', '神奈川県', 'Kanagawa'),
        ('11', '埼玉県', 'Saitama'),
        ('12', '千葉県', 'Chiba')
    ]

    for code, name, name_en in prefectures:
        cursor.execute("""
            INSERT INTO prefectures (prefecture_code, prefecture_name, prefecture_name_en)
            VALUES (%s, %s, %s)
            ON CONFLICT (prefecture_code) DO UPDATE SET
                prefecture_name = EXCLUDED.prefecture_name,
                prefecture_name_en = EXCLUDED.prefecture_name_en
        """, (code, name, name_en))

    logger.info(f"✅ Inserted {len(prefectures)} prefectures")

    # 市区町村マスタ（世田谷区のみ Phase 1）
    cities = [
        ('13112', '13', '世田谷区', 'せたがやく', '区')
    ]

    for city_code, pref_code, city_name, city_kana, city_type in cities:
        cursor.execute("""
            INSERT INTO cities (city_code, prefecture_code, city_name, city_name_kana, city_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (city_code) DO UPDATE SET
                city_name = EXCLUDED.city_name,
                city_name_kana = EXCLUDED.city_name_kana,
                city_type = EXCLUDED.city_type
        """, (city_code, pref_code, city_name, city_kana, city_type))

    logger.info(f"✅ Inserted {len(cities)} cities")

    # 町丁目マスタ（サンプルデータ）
    choume_samples = [
        ('13112001001', '13112', '二子玉川1丁目', 'ふたこたまがわいっちょうめ', 35.6113, 139.6286),
        ('13112001002', '13112', '二子玉川2丁目', 'ふたこたまがわにちょうめ', 35.6130, 139.6295),
        ('13112002001', '13112', '三軒茶屋1丁目', 'さんげんぢゃやいっちょうめ', 35.6438, 139.6691),
        ('13112002002', '13112', '三軒茶屋2丁目', 'さんげんぢゃやにちょうめ', 35.6425, 139.6705),
        ('13112003001', '13112', '下北沢1丁目', 'しもきたざわいっちょうめ', 35.6611, 139.6683),
        ('13112003002', '13112', '下北沢2丁目', 'しもきたざわにちょうめ', 35.6598, 139.6695)
    ]

    for choume_code, city_code, choume_name, choume_kana, lat, lon in choume_samples:
        cursor.execute("""
            INSERT INTO choume (choume_code, city_code, choume_name, choume_name_kana, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (choume_code) DO UPDATE SET
                choume_name = EXCLUDED.choume_name,
                choume_name_kana = EXCLUDED.choume_name_kana,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude
        """, (choume_code, city_code, choume_name, choume_kana, lat, lon))

    logger.info(f"✅ Inserted {len(choume_samples)} choume (sample data)")


def verify_setup(cursor):
    """セットアップを検証"""
    logger.info("Verifying database setup...")

    # テーブル存在確認
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()

    logger.info(f"✅ Found {len(tables)} tables:")
    for table in tables:
        logger.info(f"  - {table[0]}")

    # データ件数確認
    cursor.execute("SELECT COUNT(*) FROM prefectures")
    pref_count = cursor.fetchone()[0]
    logger.info(f"✅ Prefectures: {pref_count} records")

    cursor.execute("SELECT COUNT(*) FROM cities")
    city_count = cursor.fetchone()[0]
    logger.info(f"✅ Cities: {city_count} records")

    cursor.execute("SELECT COUNT(*) FROM choume")
    choume_count = cursor.fetchone()[0]
    logger.info(f"✅ Choume: {choume_count} records")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("RealEstateBot Database Setup")
    logger.info("=" * 60)

    try:
        # データベース接続
        db = get_db_connection()

        with db.get_cursor() as cursor:
            # スキーマ実行
            schema_path = project_root / 'db' / 'schema.sql'
            execute_schema(cursor, schema_path)

            # マスタデータ投入
            insert_master_data(cursor)

            # 検証
            verify_setup(cursor)

        logger.info("=" * 60)
        logger.info("✅ Database setup completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
