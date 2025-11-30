#!/usr/bin/env python3
"""
Data Import Script

CSVデータをデータベースにインポートします。

Usage:
    python scripts/03_import_data.py --csv data/processed/master/kokudo_land_price_2024_13.csv
"""

import sys
from pathlib import Path
import argparse
import logging
from dotenv import load_dotenv
import pandas as pd

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import get_db_connection
from src.database.repository import LandPriceRepository
from src.converters.kokudo_converter import KokudoLandPriceConverter
from src.converters.address_normalizer import AddressNormalizer

# 環境変数を読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Import CSV data to database")
    parser.add_argument('--csv', type=str, required=True, help='CSV file path to import')
    parser.add_argument('--skip-errors', action='store_true', help='Skip rows with conversion errors')
    args = parser.parse_args()

    csv_path = Path(args.csv)

    logger.info("=" * 60)
    logger.info("Data Import Script")
    logger.info("=" * 60)
    logger.info(f"CSV file: {csv_path}")
    logger.info(f"Skip errors: {args.skip_errors}")
    logger.info("=" * 60)

    if not csv_path.exists():
        logger.error(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)

    try:
        # 1. CSVデータを読み込み
        logger.info("Loading CSV...")
        df = pd.read_csv(csv_path)
        logger.info(f"✅ Loaded {len(df)} rows")

        # 2. データ変換
        logger.info("Converting data to unified format...")
        normalizer = AddressNormalizer()
        converter = KokudoLandPriceConverter(normalizer)

        # カラムマッピングを推測
        column_mapping = converter.create_column_mapping_from_columns(df.columns.tolist())

        # データ変換
        records = converter.convert_dataframe(
            df,
            column_mapping=column_mapping,
            skip_errors=args.skip_errors
        )

        logger.info(f"✅ Converted {len(records)} records")

        if not records:
            logger.warning("No records to import")
            return

        # 3. データベースに接続
        logger.info("Connecting to database...")
        db = get_db_connection()
        conn = db.get_connection()

        # 4. データベースにインポート
        logger.info("Importing data to database...")
        repo = LandPriceRepository(conn)
        insert_count = repo.bulk_insert(records)

        logger.info(f"✅ Imported {insert_count} records")

        # 5. 検証
        logger.info("Verifying imported data...")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM land_prices")
        total_count = cursor.fetchone()[0]
        logger.info(f"Total land_prices records in DB: {total_count}")

        cursor.close()
        conn.close()

        logger.info("=" * 60)
        logger.info("✅ Import completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Import failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
