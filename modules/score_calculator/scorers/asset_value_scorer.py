"""
資産価値スコア計算器

地価データベースから取得したデータを基に資産価値スコアを計算します。
"""
import psycopg2
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

# 環境変数を読み込み
load_dotenv()


class AssetValueScorer:
    """資産価値スコア計算器"""

    def __init__(self, db_config_path: Optional[Path] = None):
        """
        Args:
            db_config_path: データベース設定ファイルのパス（デフォルト: config/database.yml）
        """
        if db_config_path is None:
            db_config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'database.yml'
        
        self.db_config = self._load_db_config(db_config_path)
        logger.info("Initialized AssetValueScorer")

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

    def calculate(self, data: Dict[str, Any]) -> int:
        """
        資産価値スコアを計算（0-100点）

        Args:
            data: データ辞書（land_price_history, latest_price などが含まれる）

        Returns:
            スコア（0-100点）
        """
        # 地価データがない場合はデフォルト値
        if 'land_price_history' not in data or not data['land_price_history']:
            logger.warning("No land price data available, returning default score")
            return 75

        history = data['land_price_history']
        if not history:
            return 75

        # 最新価格を取得
        latest_price = data.get('latest_price', 0)
        if latest_price == 0:
            latest_price = history[-1].get('price', 0) if history else 0

        # 5年変動率を取得
        price_change_5y = data.get('price_change_5y', 0)
        if price_change_5y == 0 and len(history) >= 2:
            oldest_price = history[0].get('price', 0)
            if oldest_price > 0:
                price_change_5y = ((latest_price - oldest_price) / oldest_price) * 100

        # 1年変動率を取得
        price_change_1y = data.get('price_change_1y', 0)
        if price_change_1y == 0 and len(history) >= 2:
            prev_price = history[-2].get('price', 0) if len(history) >= 2 else 0
            if prev_price > 0:
                price_change_1y = ((latest_price - prev_price) / prev_price) * 100

        # スコア計算ロジック
        score = 50  # ベーススコア

        # 1. 最新価格による評価（世田谷区平均を基準）
        # 世田谷区の平均地価を約70万円/㎡と仮定
        avg_price_setagaya = 700000
        if latest_price > 0:
            price_ratio = latest_price / avg_price_setagaya
            if price_ratio >= 1.2:
                score += 20  # 高価格エリア
            elif price_ratio >= 1.0:
                score += 15
            elif price_ratio >= 0.8:
                score += 10
            else:
                score += 5

        # 2. 5年変動率による評価
        if price_change_5y > 15:
            score += 20  # 大幅上昇
        elif price_change_5y > 10:
            score += 15
        elif price_change_5y > 5:
            score += 10
        elif price_change_5y > 0:
            score += 5
        elif price_change_5y < -10:
            score -= 10  # 大幅下降
        elif price_change_5y < -5:
            score -= 5

        # 3. 1年変動率による評価
        if price_change_1y > 5:
            score += 10  # 急上昇
        elif price_change_1y > 0:
            score += 5
        elif price_change_1y < -5:
            score -= 10  # 急下降
        elif price_change_1y < 0:
            score -= 5

        # スコアを0-100の範囲に制限
        score = max(0, min(100, score))

        logger.debug(f"Asset value score calculated: {score} "
                    f"(price={latest_price:,}, 5y_change={price_change_5y:.2f}%, "
                    f"1y_change={price_change_1y:.2f}%)")

        return int(score)

    def fetch_land_price_data(self, area: 'Area') -> Optional[Dict[str, Any]]:
        """
        データベースから地価データを取得

        Args:
            area: エリア情報

        Returns:
            地価データ辞書、またはNone
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # 住所パターンを作成（例: "松原5丁目" -> "松原５丁目%"）
            search_pattern = self._create_search_pattern(area.choume)

            # 5年分のデータを取得
            cursor.execute('''
                SELECT survey_year, official_price, year_on_year_change
                FROM land_prices
                WHERE original_address LIKE %s
                ORDER BY survey_year
            ''', (search_pattern,))

            rows = cursor.fetchall()

            if not rows:
                logger.warning(f"No land price data found for {area.choume}")
                cursor.close()
                conn.close()
                return None

            # データを整形
            history = []
            for year, price, change in rows:
                history.append({
                    'year': year,
                    'price': price,
                    'change': change
                })

            latest = rows[-1]
            oldest = rows[0]
            price_change_5y = ((latest[1] - oldest[1]) / oldest[1]) * 100 if oldest[1] > 0 else 0
            price_change_1y = latest[2] if latest[2] else 0

            result = {
                'land_price_history': history,
                'latest_price': latest[1],
                'price_change_5y': price_change_5y,
                'price_change_1y': price_change_1y,
                'data_source': 'tokyo_opendata'
            }

            cursor.close()
            conn.close()

            return result

        except Exception as e:
            logger.error(f"Error fetching land price data: {e}", exc_info=True)
            return None

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

