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
        地価データを取得（26年分・平均値+価格帯）
        
        Returns:
            {
                'land_price_history': List[Dict],  # 平均値・最小・最大・地点数
                'latest_price': int,               # 最新年の平均
                'latest_price_min': int,           # 最新年の最小
                'latest_price_max': int,           # 最新年の最大
                'latest_point_count': int,         # 最新年の地点数
                'price_change_26y': float,
                'price_change_5y': float,
                'price_change_1y': float,
                'data_source': str,
                ...
            }
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # 町丁目名から検索パターン作成
            # 全角→半角変換
            choume_normalized = area.choume.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            
            # 念のため末尾の数字を削除（例: "世田谷2丁目3" → "世田谷2丁目"）
            import re
            choume_base = re.sub(r'\d+$', '', choume_normalized)
            
            # 検索パターン（例: "世田谷2丁目%"）
            search_pattern = f"{choume_base}%"
            
            # 年度別の平均・最小・最大・地点数を取得
            cursor.execute('''
                SELECT 
                    survey_year,
                    COUNT(*) as point_count,
                    AVG(official_price)::INTEGER as avg_price,
                    MIN(official_price) as min_price,
                    MAX(official_price) as max_price,
                    -- 国土数値情報は最新年から取得
                    MAX(CASE WHEN land_use IS NOT NULL THEN land_use END) as land_use,
                    MAX(CASE WHEN building_coverage_ratio IS NOT NULL THEN building_coverage_ratio END) as building_coverage_ratio,
                    MAX(CASE WHEN floor_area_ratio IS NOT NULL THEN floor_area_ratio END) as floor_area_ratio,
                    MAX(CASE WHEN road_direction IS NOT NULL THEN road_direction END) as road_direction,
                    MAX(CASE WHEN road_width IS NOT NULL THEN road_width END) as road_width,
                    MAX(CASE WHEN land_area IS NOT NULL THEN land_area END) as land_area,
                    MAX(CASE WHEN nearest_station IS NOT NULL THEN nearest_station END) as nearest_station,
                    MAX(CASE WHEN station_distance IS NOT NULL THEN station_distance END) as station_distance,
                    -- 代表的な住所（最初の1件）
                    MIN(original_address) as sample_address
                FROM land_prices_kokudo
                WHERE TRANSLATE(original_address, '０１２３４５６７８９', '0123456789') LIKE %s
                GROUP BY survey_year
                ORDER BY survey_year
            ''', (search_pattern,))

            rows = cursor.fetchall()

            if not rows:
                logger.warning(f"No land price data found for {area.choume}")
                cursor.close()
                conn.close()
                return {}

            # データ整形（変動率を計算）
            history = []
            for i, row in enumerate(rows):
                # 前年比変動率（平均値で計算）
                change = 0.0
                if i > 0:
                    prev_avg = rows[i-1][2]  # 前年の平均
                    curr_avg = row[2]         # 今年の平均
                    if prev_avg and prev_avg > 0:
                        change = ((curr_avg - prev_avg) / prev_avg) * 100

                history.append({
                    'year': row[0],
                    'price': row[2],           # 平均価格
                    'price_min': row[3],       # 最小価格
                    'price_max': row[4],       # 最大価格
                    'point_count': row[1],     # 地点数
                    'change': change,
                    'address': row[13]
                })

            latest = rows[-1]
            oldest = rows[0]

            # 26年間の変動率（平均値で計算）
            price_change_26y = ((latest[2] - oldest[2]) / oldest[2]) * 100 if oldest[2] and oldest[2] > 0 else 0

            # 5年間の変動率
            price_change_5y = 0.0
            if len(rows) >= 5:
                five_years_ago = rows[-5]
                price_change_5y = ((latest[2] - five_years_ago[2]) / five_years_ago[2]) * 100 if five_years_ago[2] and five_years_ago[2] > 0 else 0

            # 1年間の変動率
            price_change_1y = 0.0
            if len(rows) >= 2:
                prev = rows[-2]
                price_change_1y = ((latest[2] - prev[2]) / prev[2]) * 100 if prev[2] and prev[2] > 0 else 0

            # 国土数値情報（最新年）
            kokudo_data = {
                'land_use': latest[5],
                'building_coverage_ratio': latest[6],
                'floor_area_ratio': latest[7],
                'road_direction': latest[8],
                'road_width': latest[9],
                'land_area': latest[10],
                'nearest_station': latest[11],
                'station_distance': latest[12]
            }

            # 価格倍率関連の計算
            price_min = latest[3] if latest[3] else 0
            price_max = latest[4] if latest[4] else 0
            point_count = latest[1] if latest[1] else 0
            
            price_ratio = price_max / price_min if price_min > 0 else 1.0
            price_range_yen = price_max - price_min
            has_wide_range = (price_ratio > 1.5 and point_count > 1) if price_min > 0 else False

            result = {
                'land_price_history': history,
                'latest_price': latest[2],            # 平均価格
                'latest_price_min': latest[3],      # 最小価格
                'latest_price_max': latest[4],      # 最大価格
                'latest_point_count': latest[1],    # 地点数
                'price_change_26y': price_change_26y,
                'price_change_5y': price_change_5y,
                'price_change_1y': price_change_1y,
                'data_source': '地価公示',
                'original_address': latest[13],
                # 【追加】価格倍率関連
                'price_ratio': price_ratio,
                'price_range_yen': price_range_yen,
                'has_wide_range': has_wide_range,
                **kokudo_data
            }

            logger.info(f"Fetched land price data for {area.choume}: "
                       f"{len(history)} years, {latest[1]} points, "
                       f"avg={latest[2]:,}円/㎡ (range: {latest[3]:,}-{latest[4]:,})")

            cursor.close()
            conn.close()

            return result

        except Exception as e:
            logger.error(f"Error fetching land price data for {area.choume}: {e}", exc_info=True)
            return {}

