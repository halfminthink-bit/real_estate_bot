import requests
import os
import time
from typing import Dict, Any, Optional
from core.models import Area
from .base_collector import BaseCollector
import logging

logger = logging.getLogger(__name__)

class RESASCollector(BaseCollector):
    """RESAS API - 将来人口推計データ収集"""

    # 東京都23区の市区町村コードマッピング
    TOKYO_23_WARDS_CODE = {
        "千代田区": 13101,
        "中央区": 13102,
        "港区": 13103,
        "新宿区": 13104,
        "文京区": 13105,
        "台東区": 13106,
        "墨田区": 13107,
        "江東区": 13108,
        "品川区": 13109,
        "目黒区": 13110,
        "大田区": 13111,
        "世田谷区": 13112,
        "渋谷区": 13113,
        "中野区": 13114,
        "杉並区": 13115,
        "豊島区": 13116,
        "北区": 13117,
        "荒川区": 13118,
        "板橋区": 13119,
        "練馬区": 13120,
        "足立区": 13121,
        "葛飾区": 13122,
        "江戸川区": 13123,
    }

    PREF_CODE_TOKYO = 13  # 東京都の都道府県コード
    API_BASE_URL = "https://opendata.resas-portal.go.jp/api/v1"
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # 秒

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: RESAS APIキー（Noneの場合は環境変数から取得）
        """
        self.api_key = api_key or os.getenv('RESAS_API_KEY')
        if not self.api_key:
            logger.warning("RESAS_API_KEY not found. RESAS data collection will be disabled.")

    def is_relevant(self, area: Area) -> bool:
        """東京都23区のエリアのみ対象"""
        return area.ward in self.TOKYO_23_WARDS_CODE

    def fetch(self, area: Area) -> Dict[str, Any]:
        """
        将来人口推計データを取得

        Returns:
            {
                'current_population': int,  # 現在の人口（直近の年）
                'population_10years': int,  # 10年後の予測人口
                'population_20years': int,  # 20年後の予測人口
                'change_rate_10years': float,  # 10年後の人口増減率（%）
                'change_rate_20years': float,  # 20年後の人口増減率（%）
                'data_year': int,  # データの基準年
                'source': 'RESAS'
            }
        """
        if not self.api_key:
            logger.warning(f"RESAS API key not available for {area.ward}{area.choume}")
            return {
                'error': 'API key not available',
                'source': 'RESAS'
            }

        city_code = self.TOKYO_23_WARDS_CODE.get(area.ward)
        if not city_code:
            logger.warning(f"City code not found for {area.ward}")
            return {
                'error': f'City code not found for {area.ward}',
                'source': 'RESAS'
            }

        try:
            # API呼び出し
            population_data = self._fetch_population_data(city_code)
            if not population_data:
                return {
                    'error': 'Failed to fetch population data',
                    'source': 'RESAS'
                }

            # 人口増減率を計算
            result = self._calculate_population_change(population_data)
            result['source'] = 'RESAS'
            result['city_code'] = city_code

            logger.info(f"RESAS data for {area.ward}{area.choume}: "
                       f"10年後={result.get('change_rate_10years', 0):.2f}%, "
                       f"20年後={result.get('change_rate_20years', 0):.2f}%")

            return result

        except Exception as e:
            logger.error(f"Error fetching RESAS data for {area.ward}{area.choume}: {e}", exc_info=True)
            return {
                'error': str(e),
                'source': 'RESAS'
            }

    def _fetch_population_data(self, city_code: int) -> Optional[Dict]:
        """RESAS APIから人口データを取得"""
        url = f"{self.API_BASE_URL}/population/composition/perYear"
        headers = {
            "X-API-KEY": self.api_key
        }
        params = {
            "prefCode": self.PREF_CODE_TOKYO,
            "cityCode": city_code
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()

                # RESAS APIのエラーレスポンスをチェック
                if 'message' in data and data['message']:
                    logger.error(f"RESAS API error: {data['message']}")
                    return None

                if 'result' not in data:
                    logger.error(f"RESAS API response missing 'result' key: {data}")
                    return None

                return data['result']

            except requests.exceptions.RequestException as e:
                logger.warning(f"RESAS API request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))  # 指数バックオフ
                else:
                    raise

        return None

    def _calculate_population_change(self, population_data: Dict) -> Dict[str, Any]:
        """
        人口データから増減率を計算

        Args:
            population_data: RESAS APIのresultデータ

        Returns:
            人口データと増減率を含む辞書
        """
        # データ構造を確認
        # RESAS APIのレスポンス構造:
        # {
        #   "boundaryYear": 2020,
        #   "data": [
        #     {
        #       "label": "総人口",
        #       "data": [
        #         {"year": 2020, "value": 123456},
        #         {"year": 2025, "value": 125000},
        #         ...
        #       ]
        #     }
        #   ]
        # }

        if 'data' not in population_data or not population_data['data']:
            logger.error("Invalid population data structure")
            return {
                'error': 'Invalid data structure',
                'current_population': 0,
                'population_10years': 0,
                'population_20years': 0,
                'change_rate_10years': 0.0,
                'change_rate_20years': 0.0,
                'data_year': None
            }

        # 「総人口」のデータを取得
        total_population_data = None
        for item in population_data['data']:
            if item.get('label') == '総人口':
                total_population_data = item.get('data', [])
                break

        if not total_population_data:
            logger.warning("Total population data not found")
            return {
                'error': 'Total population data not found',
                'current_population': 0,
                'population_10years': 0,
                'population_20years': 0,
                'change_rate_10years': 0.0,
                'change_rate_20years': 0.0,
                'data_year': None
            }

        # 年と人口のマッピングを作成
        year_population = {item['year']: item['value'] for item in total_population_data if 'year' in item and 'value' in item}

        if not year_population:
            logger.warning("No population data found")
            return {
                'error': 'No population data',
                'current_population': 0,
                'population_10years': 0,
                'population_20years': 0,
                'change_rate_10years': 0.0,
                'change_rate_20years': 0.0,
                'data_year': None
            }

        # 現在の年（最新の実測値）を取得
        # 実測値は過去のデータ、予測値は未来のデータ
        current_year = max([y for y in year_population.keys() if y <= 2024], default=None)
        if current_year is None:
            # 実測値がない場合は最小の年を使用
            current_year = min(year_population.keys())

        current_population = year_population.get(current_year, 0)

        # 10年後、20年後の予測人口を取得
        target_year_10 = current_year + 10
        target_year_20 = current_year + 20

        population_10years = year_population.get(target_year_10, current_population)
        population_20years = year_population.get(target_year_20, current_population)

        # 増減率を計算（%）
        change_rate_10years = 0.0
        change_rate_20years = 0.0

        if current_population > 0:
            change_rate_10years = ((population_10years - current_population) / current_population) * 100
            change_rate_20years = ((population_20years - current_population) / current_population) * 100

        return {
            'current_population': int(current_population),
            'population_10years': int(population_10years),
            'population_20years': int(population_20years),
            'change_rate_10years': round(change_rate_10years, 2),
            'change_rate_20years': round(change_rate_20years, 2),
            'data_year': current_year,
            'error': None
        }


if __name__ == "__main__":
    # テスト実行
    import logging
    logging.basicConfig(level=logging.INFO)

    # 世田谷区のテスト
    from core.models import Area

    test_area = Area(
        area_id=1,
        ward="世田谷区",
        choume="三軒茶屋1丁目",
        priority="high"
    )

    collector = RESASCollector()
    result = collector.fetch(test_area)

    print("\n=== RESAS API Test Result ===")
    print(f"Area: {test_area.ward}{test_area.choume}")
    print(f"Result: {result}")
    print("\n詳細:")
    if 'error' not in result or not result.get('error'):
        print(f"  現在の人口: {result.get('current_population', 0):,}人")
        print(f"  10年後の予測人口: {result.get('population_10years', 0):,}人")
        print(f"  20年後の予測人口: {result.get('population_20years', 0):,}人")
        print(f"  10年後の増減率: {result.get('change_rate_10years', 0):.2f}%")
        print(f"  20年後の増減率: {result.get('change_rate_20years', 0):.2f}%")
        print(f"  データ基準年: {result.get('data_year', 'N/A')}年")
    else:
        print(f"  エラー: {result.get('error')}")


