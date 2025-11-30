#!/usr/bin/env python3
"""
Data Download Script

国土数値情報から地価データをダウンロードし、CSVとして保存します。

Usage:
    python scripts/02_download_data.py --year 2024 --prefecture 13
"""

import sys
from pathlib import Path
import argparse
import logging
from dotenv import load_dotenv

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.kokudo_collector import KokudoLandPriceCollector

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
    parser = argparse.ArgumentParser(description="Download land price data from Kokudo Suuchi")
    parser.add_argument('--year', type=int, default=2024, help='Year to download (default: 2024)')
    parser.add_argument('--prefecture', type=str, default='13', help='Prefecture code (default: 13 for Tokyo)')
    parser.add_argument('--force', action='store_true', help='Force re-download even if file exists')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Data Download Script")
    logger.info("=" * 60)
    logger.info(f"Year: {args.year}")
    logger.info(f"Prefecture: {args.prefecture}")
    logger.info(f"Force re-download: {args.force}")
    logger.info("=" * 60)

    try:
        # コレクター初期化
        collector = KokudoLandPriceCollector()

        # データダウンロード
        extract_dir = collector.download_land_price(
            year=args.year,
            prefecture_code=args.prefecture,
            force_redownload=args.force
        )

        if not extract_dir:
            logger.error("❌ Download failed")
            sys.exit(1)

        # GMLファイルを読み込み
        gdf = collector.read_gml(extract_dir)

        if gdf is None:
            logger.error("❌ Failed to read GML file")
            sys.exit(1)

        # CSVとして保存
        output_dir = project_root / 'data' / 'processed' / 'master'
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"kokudo_land_price_{args.year}_{args.prefecture}.csv"

        logger.info(f"Saving to CSV: {output_path}")
        gdf.to_csv(output_path, index=False)

        logger.info(f"✅ Saved {len(gdf)} records to {output_path}")

        # データサマリーを表示
        logger.info("=" * 60)
        logger.info("Data Summary:")
        logger.info(f"  Total records: {len(gdf)}")
        logger.info(f"  Columns: {len(gdf.columns)}")
        logger.info(f"  Column names: {list(gdf.columns[:10])}...")  # 最初の10列のみ

        # サンプルデータを表示
        logger.info("=" * 60)
        logger.info("Sample data (first 5 rows):")
        print(gdf.head())

        logger.info("=" * 60)
        logger.info("✅ Download completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
