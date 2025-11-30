"""
地価データ収集器

PostgreSQLから地価データを取得します。
"""
import psycopg2
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from core.models import Area
from .base_collector import BaseCollector
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

# 環境変数を読み込み
load_dotenv()


class LandPriceCollector(BaseCollector):
    """地価データ収集器"""

    def __init__(self, db_config_path: Optional[Path] = None):
        """
        Args:
            db_config_path: データベース設定ファイルのパス（デフォルト: config/database.yml）
        """
        if db_config_path is None:
            db_config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'database.yml'
        
        self.db_config = self._load_db_config(db_config_path)
        logger.info("Initialized LandPriceCollector")

    def _load_db_config(self, config_path: Path) -> Dict[str, Any]:
        """データベース設定を読み込み"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 環境変数からパスワードを取得（設定ファイルより優先）
        password = os.getenv('DB_PASSWORD', config['postgresql'].get('password', 'postgres'))
        
        return {
            'host': os.getenv('DB_HOST', config['postgresql'].get('host', 'localhost')),
            'port': int(os.getenv('DB_PORT', config['postgresql'].get('port', 5432))),
            'database': os.getenv('DB_NAME', config['postgresql'].get('database', 'real_estate_dev')),
            'user': os.getenv('DB_USER', config['postgresql'].get('user', 'postgres')),
            'password': password
        }

    def is_relevant(self, area: Area) -> bool:
        """このコレクターが対象エリアに適用可能か"""
        # 世田谷区のみ対応（Phase 1）
        return area.ward == '世田谷区'

    def fetch(self, area: Area) -> Dict[str, Any]:
        """
        地価データを取得

        Returns:
            {
                'land_price_history': List[Dict],
                'latest_price': int,
                'price_change_5y': float,
                'price_change_1y': float,
                'data_source': str
            }
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # 住所パターンを作成（例: "松原5丁目" -> "松原5丁目"）
            # 全角・半角対応のため、半角で統一
            choume_normalized = area.choume.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            search_pattern = f"%{choume_normalized}%"

            # 5年分のデータを取得（国土数値情報のフィールドも含む）
            # 全角・半角対応でマッチング
            cursor.execute('''
                SELECT 
                    survey_year, 
                    official_price, 
                    year_on_year_change, 
                    original_address,
                    land_use,
                    building_coverage_ratio,
                    floor_area_ratio,
                    road_direction,
                    road_width,
                    land_area,
                    nearest_station,
                    station_distance
                FROM land_prices
                WHERE TRANSLATE(original_address, '０１２３４５６７８９', '0123456789') LIKE %s
                ORDER BY survey_year
            ''', (search_pattern,))

            rows = cursor.fetchall()

            if not rows:
                logger.warning(f"No land price data found for {area.choume}")
                cursor.close()
                conn.close()
                return {}

            # データを整形
            history = []
            for row in rows:
                history.append({
                    'year': row[0],
                    'price': row[1],
                    'change': row[2],
                    'address': row[3] if len(row) > 3 else None
                })

            latest = rows[-1]
            oldest = rows[0]
            price_change_5y = ((latest[1] - oldest[1]) / oldest[1]) * 100 if oldest[1] > 0 else 0
            price_change_1y = latest[2] if latest[2] else 0

            # 最新年のデータから国土数値情報を取得（2021年データがあれば優先）
            kokudo_data = None
            for row in reversed(rows):  # 最新年から遡って探す
                if len(row) > 4 and row[4] is not None:  # land_useが存在
                    kokudo_data = {
                        'land_use': row[4],
                        'building_coverage_ratio': row[5],
                        'floor_area_ratio': row[6],
                        'road_direction': row[7],
                        'road_width': row[8],
                        'land_area': row[9],
                        'nearest_station': row[10],
                        'station_distance': row[11]
                    }
                    break

            result = {
                'land_price_history': history,
                'latest_price': latest[1],
                'price_change_5y': price_change_5y,
                'price_change_1y': price_change_1y,
                'data_source': 'tokyo_opendata',
                'original_address': latest[3] if len(latest) > 3 else None
            }

            # 国土数値情報を追加
            if kokudo_data:
                result.update(kokudo_data)

            logger.info(f"Fetched land price data for {area.choume}: "
                       f"{len(history)} years, latest={latest[1]:,}円/㎡, 用途地域={kokudo_data.get('land_use', 'なし') if kokudo_data else 'なし'}")

            cursor.close()
            conn.close()

            return result

        except Exception as e:
            logger.error(f"Error fetching land price data for {area.choume}: {e}", exc_info=True)
            return {}

    def _create_search_pattern(self, choume: str) -> str:
        """
        町丁目名から検索パターンを作成

        Args:
            choume: 町丁目名（例: "松原5丁目"）

        Returns:
            検索パターン（例: "松原５丁目%"）
        """
        # 半角数字を全角に変換
        choume_fullwidth = choume.translate(str.maketrans('0123456789', '０１２３４５６７８９'))
        return f"{choume_fullwidth}%"

