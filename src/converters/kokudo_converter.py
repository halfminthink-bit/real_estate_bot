"""
国土数値情報データ変換モジュール

国土数値情報（GML形式）のデータを統一フォーマットに変換します。
"""

import pandas as pd
from typing import List, Dict, Any
import logging

from src.models.unified_schema import LandPriceRecord
from src.converters.address_normalizer import AddressNormalizer

logger = logging.getLogger(__name__)


class KokudoLandPriceConverter:
    """国土数値情報の地価データを統一フォーマットに変換"""

    # 用途区分マッピング
    LAND_TYPE_MAP = {
        '住宅': '住宅地',
        '宅地': '住宅地',
        '商業': '商業地',
        '工業': '工業地',
        '林地': 'その他'
    }

    def __init__(self, address_normalizer: AddressNormalizer = None):
        """
        Args:
            address_normalizer: 住所正規化インスタンス
        """
        if address_normalizer is None:
            address_normalizer = AddressNormalizer()

        self.normalizer = address_normalizer

    def convert(self, row: Dict[str, Any], column_mapping: Dict[str, str] = None) -> LandPriceRecord:
        """
        1行のデータを統一フォーマットに変換

        Args:
            row: GeoDataFrameの1行（辞書形式）
            column_mapping: カラム名マッピング（GMLのカラム名 -> 内部カラム名）

        Returns:
            統一フォーマットのレコード
        """
        if column_mapping is None:
            # デフォルトのカラムマッピング（国土数値情報地価公示データ用）
            column_mapping = self._get_default_column_mapping()

        try:
            # 住所から町丁目コードを抽出
            address = str(row.get(column_mapping['address'], ''))
            choume_code = self.normalizer.normalize(address)

            # 調査年
            survey_year = int(row.get(column_mapping['year'], 0))

            # 用途区分
            land_type_raw = str(row.get(column_mapping['land_type'], ''))
            land_type = self.LAND_TYPE_MAP.get(land_type_raw, land_type_raw)

            # 公示価格
            price = int(row.get(column_mapping['price'], 0))

            # 前年比
            yoy_change = row.get(column_mapping['yoy_change'])
            if pd.notna(yoy_change):
                yoy_change = float(yoy_change)
            else:
                yoy_change = None

            # 緯度経度
            latitude = row.get(column_mapping.get('latitude'))
            longitude = row.get(column_mapping.get('longitude'))

            if pd.notna(latitude):
                latitude = float(latitude)
            else:
                latitude = None

            if pd.notna(longitude):
                longitude = float(longitude)
            else:
                longitude = None

            # 統一レコード作成
            record = LandPriceRecord(
                choume_code=choume_code,
                survey_year=survey_year,
                land_type=land_type,
                official_price=price,
                year_on_year_change=yoy_change,
                data_source='kokudo_suuchi',
                original_address=address,
                latitude=latitude,
                longitude=longitude
            )

            return record

        except Exception as e:
            logger.error(f"Conversion error: {e}")
            logger.error(f"Row data: {row}")
            raise

    def convert_dataframe(
        self,
        df: pd.DataFrame,
        column_mapping: Dict[str, str] = None,
        skip_errors: bool = True
    ) -> List[LandPriceRecord]:
        """
        DataFrame全体を変換

        Args:
            df: 変換対象のDataFrame
            column_mapping: カラム名マッピング
            skip_errors: エラーが発生した行をスキップするか

        Returns:
            統一フォーマットのレコードリスト
        """
        records = []
        error_count = 0

        logger.info(f"Converting {len(df)} rows...")

        for idx, row in df.iterrows():
            try:
                record = self.convert(row.to_dict(), column_mapping)
                records.append(record)

            except Exception as e:
                error_count += 1
                if skip_errors:
                    logger.warning(f"⚠️  Skipped row {idx}: {e}")
                    continue
                else:
                    raise

        logger.info(f"✅ Converted {len(records)} records ({error_count} errors)")

        return records

    def _get_default_column_mapping(self) -> Dict[str, str]:
        """
        デフォルトのカラムマッピングを取得

        国土数値情報のGMLデータのカラム名は年度によって異なる場合があります。
        実際のデータを確認してマッピングを調整してください。

        Returns:
            カラムマッピング辞書
        """
        # 例: 地価公示データ（L01）のカラム名（要確認）
        return {
            'year': 'L01_001',       # 調査年
            'land_type': 'L01_006',  # 用途区分
            'price': 'L01_011',      # 公示価格
            'yoy_change': 'L01_012', # 前年比
            'address': 'L01_024',    # 住所
            'latitude': 'latitude',  # 緯度（geometry から抽出される場合もあり）
            'longitude': 'longitude' # 経度
        }

    def create_column_mapping_from_columns(self, columns: List[str]) -> Dict[str, str]:
        """
        実際のカラム名からマッピングを推測

        Args:
            columns: DataFrameのカラムリスト

        Returns:
            推測されたカラムマッピング
        """
        mapping = {}

        # パターンマッチングでカラム名を推測
        for col in columns:
            col_lower = col.lower()

            if '年' in col or 'year' in col_lower:
                mapping['year'] = col
            elif '用途' in col or '地目' in col:
                mapping['land_type'] = col
            elif '価格' in col or 'price' in col_lower:
                mapping['price'] = col
            elif '変化' in col or '前年' in col or 'change' in col_lower:
                mapping['yoy_change'] = col
            elif '住所' in col or 'address' in col_lower:
                mapping['address'] = col
            elif 'lat' in col_lower:
                mapping['latitude'] = col
            elif 'lon' in col_lower or 'lng' in col_lower:
                mapping['longitude'] = col

        logger.info(f"Inferred column mapping: {mapping}")

        return mapping
