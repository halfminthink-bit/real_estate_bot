"""
国土数値情報データ収集モジュール

国土数値情報（国土交通省）から地価公示データをダウンロードします。
GML形式のデータを処理し、GeoPandasで読み込みます。
"""

import requests
import zipfile
from pathlib import Path
from typing import Optional, Dict
import logging
import time

logger = logging.getLogger(__name__)


class KokudoLandPriceCollector:
    """国土数値情報の地価公示データ収集"""

    # 国土数値情報のベースURL
    BASE_URL = "https://nlftp.mlit.go.jp/ksj/gml/datalist"

    # データセットコード（地価公示）
    DATASET_CODE = "L01"

    def __init__(self, download_dir: Path = None):
        """
        Args:
            download_dir: ダウンロード先ディレクトリ
        """
        if download_dir is None:
            download_dir = Path("data/raw/national/kokudo_suuchi")

        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized KokudoLandPriceCollector (download_dir={self.download_dir})")

    def download_land_price(
        self,
        year: int,
        prefecture_code: str = "13",
        force_redownload: bool = False
    ) -> Optional[Path]:
        """
        地価公示データをダウンロード

        Args:
            year: 年度（例: 2024）
            prefecture_code: 都道府県コード（13=東京都）
            force_redownload: 既存ファイルがあっても再ダウンロードする

        Returns:
            解凍先ディレクトリのパス（失敗時はNone）
        """
        # ファイル名とパス
        zip_filename = f"L01-{year}_{prefecture_code}_GML.zip"
        zip_path = self.download_dir / zip_filename
        extract_dir = self.download_dir / f"{year}_{prefecture_code}"

        # 既存ファイルチェック
        if extract_dir.exists() and not force_redownload:
            logger.info(f"Data already exists: {extract_dir}")
            return extract_dir

        # URL構築
        # 実際のURLは年度と都道府県コードによって異なる
        # 例: https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-v3_1.html
        url = self._build_download_url(year, prefecture_code)

        logger.info(f"Downloading: {url}")

        try:
            # ダウンロード
            response = requests.get(url, stream=True, timeout=300)

            if response.status_code != 200:
                logger.error(f"❌ Download failed: HTTP {response.status_code}")
                logger.error(f"URL: {url}")
                return None

            # ZIPファイルに保存
            total_size = int(response.headers.get('content-length', 0))
            logger.info(f"Downloading {total_size / 1024 / 1024:.2f} MB...")

            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"✅ Downloaded to: {zip_path}")

            # 解凍
            logger.info(f"Extracting to: {extract_dir}")
            extract_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            logger.info(f"✅ Extracted {len(list(extract_dir.glob('*')))} files")

            # ZIPファイルを削除（オプション）
            # zip_path.unlink()

            return extract_dir

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Download error: {e}")
            return None
        except zipfile.BadZipFile as e:
            logger.error(f"❌ Invalid ZIP file: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return None

    def _build_download_url(self, year: int, prefecture_code: str) -> str:
        """
        ダウンロードURLを構築

        注意: 実際のURLは国土数値情報サイトで確認する必要があります。
        年度やバージョンによってURLが変わる可能性があります。

        Args:
            year: 年度
            prefecture_code: 都道府県コード

        Returns:
            ダウンロードURL
        """
        # 実際のURL例（要確認）
        # https://nlftp.mlit.go.jp/ksj/gml/data/L01/L01-24/L01-24_13_GML.zip

        # 年度の下2桁
        year_suffix = str(year)[-2:]

        # URL構築
        url = f"{self.BASE_URL}/L01/L01-{year_suffix}/L01-{year_suffix}_{prefecture_code}_GML.zip"

        return url

    def read_gml(self, extract_dir: Path) -> Optional['geopandas.GeoDataFrame']:
        """
        GMLファイルを読み込み

        Args:
            extract_dir: 解凍先ディレクトリ

        Returns:
            GeoDataFrame（失敗時はNone）
        """
        try:
            import geopandas as gpd
        except ImportError:
            logger.error("❌ geopandas is not installed. Run: pip install geopandas")
            return None

        # GMLファイルを検索（.xmlまたは.gml拡張子）
        gml_files = list(extract_dir.glob("*.xml")) + list(extract_dir.glob("*.gml"))

        if not gml_files:
            logger.error(f"❌ No GML file found in {extract_dir}")
            return None

        gml_path = gml_files[0]
        logger.info(f"Reading GML: {gml_path}")

        try:
            gdf = gpd.read_file(gml_path)
            logger.info(f"✅ Loaded {len(gdf)} records")
            logger.info(f"Columns: {list(gdf.columns)}")

            return gdf

        except Exception as e:
            logger.error(f"❌ Failed to read GML: {e}", exc_info=True)
            return None

    def get_available_years(self) -> list[int]:
        """
        利用可能な年度一覧を取得

        注意: これは簡易実装です。実際には国土数値情報のAPIやウェブスクレイピングが必要です。

        Returns:
            年度リスト
        """
        # 簡易実装: 2014年から現在まで
        current_year = 2024
        return list(range(2014, current_year + 1))
