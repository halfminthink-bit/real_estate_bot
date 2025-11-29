import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from core.models import Area
from .base_collector import BaseCollector
import logging

logger = logging.getLogger(__name__)

class CrimeCollector(BaseCollector):
    """警視庁 犯罪統計データ収集"""

    TOKYO_23_WARDS = [
        "千代田区", "中央区", "港区", "新宿区", "文京区",
        "台東区", "墨田区", "江東区", "品川区", "目黒区",
        "大田区", "世田谷区", "渋谷区", "中野区", "杉並区",
        "豊島区", "北区", "荒川区", "板橋区", "練馬区",
        "足立区", "葛飾区", "江戸川区"
    ]

    def __init__(self, data_path: Path):
        """
        Args:
            data_path: 警視庁データのCSVファイルパス
                      （手動でExcel→CSV変換したもの）
        """
        self.data_path = data_path
        self.crime_df = None

        if data_path.exists():
            try:
                self.crime_df = pd.read_csv(data_path)
                logger.info(f"Loaded crime data from {data_path}")
            except Exception as e:
                logger.error(f"Failed to load crime data: {e}")
        else:
            logger.warning(f"Crime data file not found at {data_path}")

    def is_relevant(self, area: Area) -> bool:
        return area.ward in self.TOKYO_23_WARDS

    def fetch(self, area: Area) -> Dict[str, Any]:
        """
        町丁目の犯罪データを取得

        Returns:
            {
                'crime_count': int,
                'year': int,
                'month': int,
                'crime_type': str,
                'source': str
            }
        """
        if self.crime_df is None:
            logger.warning("Crime data not loaded")
            return {
                'crime_count': 0,
                'error': 'Data not loaded'
            }

        # CSVから該当町丁目のデータを検索
        try:
            data = self.crime_df[self.crime_df['area_id'] == area.area_id]

            if data.empty:
                logger.warning(f"No crime data found for area {area.area_id}")
                return {
                    'crime_count': 0,
                    'error': 'No data found'
                }

            row = data.iloc[0]
            return {
                'crime_count': int(row['crime_count']),
                'year': int(row['year']),
                'month': int(row['month']),
                'crime_type': str(row['crime_type']),
                'source': str(row['data_source'])
            }

        except Exception as e:
            logger.error(f"Error fetching crime data: {e}")
            return {
                'crime_count': 0,
                'error': str(e)
            }
