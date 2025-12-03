"""
不動産情報ライブラリAPI - 取引価格情報コレクター

既存のLandPriceCollectorと同じ設計思想で実装：
- PostgreSQLからデータを取得するのと同じインターフェース
- 取引価格データをAPIから取得して返す
"""
import os
import requests
import gzip
import json
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 環境変数を読み込み
load_dotenv()


class TransactionPriceCollector:
    """
    不動産取引価格情報を取得するコレクター
    
    使用方法:
        # .envファイルから自動読み込み
        collector = TransactionPriceCollector()
        
        # またはパラメータで直接指定（.envをオーバーライド）
        collector = TransactionPriceCollector(
            api_key="your_api_key",
            endpoint="https://custom-endpoint.com",
            timeout=60
        )
        
        data = collector.get_transaction_data(
            year=2024,
            quarter=3,
            city="13112"  # 世田谷区
        )
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """
        初期化
        
        Args:
            api_key: APIキー（Noneの場合は環境変数REINFOLIB_API_KEYから取得）
            endpoint: APIエンドポイント（Noneの場合は環境変数REINFOLIB_API_ENDPOINTから取得）
            timeout: タイムアウト秒数（Noneの場合は環境変数REINFOLIB_API_TIMEOUTから取得）
        """
        # パラメータで直接指定された場合は優先、なければ環境変数から取得
        self.api_key = api_key or os.getenv('REINFOLIB_API_KEY')
        self.endpoint = endpoint or os.getenv('REINFOLIB_API_ENDPOINT', 'https://www.reinfolib.mlit.go.jp/ex-api/external')
        self.timeout = timeout or int(os.getenv('REINFOLIB_API_TIMEOUT', '60'))  # デフォルト60秒に延長
        
        if not self.api_key:
            logger.warning("REINFOLIB_API_KEY が.envに設定されていません")
            logger.warning("テストモードで実行します（APIキー申請後に設定してください）")
    
    def get_transaction_data(
        self,
        year: int,
        quarter: Optional[int] = None,
        area: Optional[str] = None,
        city: Optional[str] = None,
        price_classification: Optional[str] = None
    ) -> List[Dict]:
        """
        取引価格情報を取得
        
        Args:
            year: 取引年（2005～）
            quarter: 四半期（1-4）
            area: 都道府県コード（2桁）例: "13"
            city: 市区町村コード（5桁）例: "13112"
            price_classification: 価格区分（"01", "02"）
        
        Returns:
            List[Dict]: 取引価格データのリスト
            
        Examples:
            # 世田谷区の2024年Q3データ取得
            data = collector.get_transaction_data(
                year=2024,
                quarter=3,
                city="13112"
            )
        """
        # パラメータ検証
        if year < 2005:
            raise ValueError("year は2005年以降を指定してください")
        
        # リクエストパラメータ構築
        params = {"year": year}
        if quarter:
            params["quarter"] = quarter
        if area:
            params["area"] = area
        if city:
            params["city"] = city
        if price_classification:
            params["priceClassification"] = price_classification
        
        # APIリクエスト送信
        try:
            response = self._send_request(params)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"API取得エラー: {e}", exc_info=True)
            return []
    
    def get_choume_transactions(
        self,
        ward: str,
        choume: str,
        year: int,
        quarter: Optional[int] = None
    ) -> List[Dict]:
        """
        特定の町丁目の取引データを取得
        
        Args:
            ward: 区名（例: "世田谷区"）
            choume: 町丁目名（例: "上用賀6丁目"）
            year: 取引年
            quarter: 四半期
        
        Returns:
            List[Dict]: 該当する取引データ
            
        Examples:
            # 上用賀6丁目の取引データ取得
            data = collector.get_choume_transactions(
                ward="世田谷区",
                choume="上用賀6丁目",
                year=2024,
                quarter=3
            )
        """
        # 世田谷区の市区町村コードは "13112"
        city_code = "13112" if ward == "世田谷区" else None
        
        if not city_code:
            logger.warning(f"{ward}の市区町村コードが不明です")
            return []
        
        # 市区町村全体のデータを取得
        all_data = self.get_transaction_data(
            year=year,
            quarter=quarter,
            city=city_code
        )
        
        # 町丁目でフィルタリング
        # DistrictNameから町丁目部分を抽出して比較
        choume_base = choume.replace("丁目", "")  # "上用賀6" に変換
        
        filtered_data = [
            item for item in all_data
            if choume_base in item.get("DistrictName", "")
        ]
        
        return filtered_data
    
    def get_area_transactions(
        self,
        ward: str,
        choume: str,
        years: int = 3
    ) -> Dict[str, Any]:
        """
        特定の町丁目の取引データを取得（エリア全体、過去N年分）
        
        Args:
            ward: 区名（例: "世田谷区"）
            choume: 町丁目名（例: "上用賀6丁目"）
            years: 取得する年数（デフォルト: 3）
                  例: years=3 → 2022年〜2024年の全四半期を取得
        
        Returns:
            Dict: {
                'area_name': str,           # 正規化後の地域名
                'choume_full': str,         # 元の町丁目名
                'transaction_period': str,  # 期間文字列（例: '2022年〜2024年'）
                'transaction_years': int,   # 取得年数
                'transaction_count': int,    # 取引件数
                'transaction_avg': int,      # 平均取引価格
                'transaction_min': int,      # 最小取引価格
                'transaction_max': int,      # 最大取引価格
                'has_transaction_data': bool, # データ有無
                'transaction_samples': List[Dict]  # 代表例（最大10件）
            }
        
        Note:
            - 現在は2025年12月なので、最新データは2024年第4四半期まで
            - 過去N年分の全四半期（N × 4四半期）を取得
            - 各四半期ごとにAPI呼び出しを行い、結果を統合
        """
        import time
        
        # 1. 町丁目を正規化（"上用賀6丁目" → "上用賀"）
        area_name = self._normalize_choume(choume)
        
        # 2. 世田谷区のコードを取得
        city_code = "13112" if ward == "世田谷区" else None
        
        if not city_code:
            logger.warning(f"⚠️  {ward}の市区町村コードが不明です")
            return self._empty_result_with_period(area_name, choume, years)
        
        # 3. 現在の年と四半期を設定
        # 注意: 2025年12月時点で、最新の取引データは2024年第4四半期まで
        latest_year = 2024
        latest_quarter = 4
        
        # 4. 過去N年分の全四半期データを取得
        all_transactions = []
        
        for year_offset in range(years):
            target_year = latest_year - year_offset
            
            # 各年の全四半期を取得（1〜4）
            for quarter in range(1, 5):
                # 最新年度の場合、latest_quarterより先の四半期はスキップ
                if target_year == latest_year and quarter > latest_quarter:
                    continue
                
                try:
                    # API呼び出し（各四半期ごと）
                    quarter_data = self.get_transaction_data(
                        year=target_year,
                        quarter=quarter,
                        city=city_code
                    )
                    
                    if quarter_data:
                        # 該当エリアでフィルタリング
                        filtered_quarter_data = [
                            item for item in quarter_data
                            if area_name in item.get('DistrictName', '')
                        ]
                        
                        # 各取引に年・四半期情報を追加
                        for transaction in filtered_quarter_data:
                            transaction['year'] = target_year
                            transaction['quarter'] = quarter
                        
                        all_transactions.extend(filtered_quarter_data)
                        
                        logger.debug(f"Fetched {target_year}Q{quarter}: {len(filtered_quarter_data)} transactions for {area_name}")
                        
                        # レート制限対策: APIコールの間隔を空ける（5秒待機）
                        time.sleep(5.0)
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch data for {target_year}Q{quarter}: {e}")
                    continue
        
        # 5. データが取得できなかった場合
        if not all_transactions:
            logger.info(f"No transaction data for {area_name} (past {years} years)")
            return self._empty_result_with_period(area_name, choume, years)
        
        # 6. 価格データを抽出して統計を計算
        prices = []
        for item in all_transactions:
            price_str = item.get('TradePrice', '0')
            if price_str and price_str != 'N/A':
                try:
                    # 文字列の場合は数値に変換を試みる
                    if isinstance(price_str, str):
                        # カンマや空白を除去
                        price_str = price_str.replace(',', '').replace(' ', '')
                    price = int(price_str)
                    if price > 0:  # 有効な価格のみ
                        prices.append(price)
                except (ValueError, TypeError):
                    pass
        
        if not prices:
            return self._empty_result_with_period(area_name, choume, years)
        
        # 7. 期間の文字列を生成
        start_year = latest_year - years + 1
        period = f'{start_year}年〜{latest_year}年'
        
        # 8. 返り値を構築
        return {
            'area_name': area_name,
            'choume_full': choume,
            'transaction_period': period,
            'transaction_years': years,
            'transaction_count': len(all_transactions),
            'transaction_avg': int(sum(prices) / len(prices)),
            'transaction_min': min(prices),
            'transaction_max': max(prices),
            'has_transaction_data': True,
            'transaction_samples': all_transactions[:10]  # 代表例を10件まで
        }
    
    def _normalize_choume(self, choume: str) -> str:
        """
        町丁目を正規化
        
        Args:
            choume: 町丁目名（例: "上用賀6丁目"）
        
        Returns:
            str: 正規化後（例: "上用賀"）
        """
        import re
        # "上用賀6丁目" → "上用賀"
        match = re.search(r'^([^0-9]+)', choume)
        return match.group(1) if match else choume
    
    def _empty_result(self, area_name: str, choume: str) -> Dict:
        """
        空の結果を返す（旧形式、後方互換性のため残す）
        """
        return {
            'area_name': area_name,
            'choume_full': choume,
            'data_count': 0,
            'transactions': [],
            'statistics': {
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'median_price': 0
            }
        }
    
    def _empty_result_with_period(self, area_name: str, choume: str, years: int) -> Dict:
        """
        空の結果を返す（期間情報付き）
        
        Args:
            area_name: 正規化後の地域名
            choume: 町丁目名
            years: 取得年数
        
        Returns:
            Dict: 空の取引データ（期間情報付き）
        """
        latest_year = 2024
        start_year = latest_year - years + 1
        period = f'{start_year}年〜{latest_year}年'
        
        return {
            'area_name': area_name,
            'choume_full': choume,
            'transaction_period': period,
            'transaction_years': years,
            'transaction_count': 0,
            'transaction_avg': 0,
            'transaction_min': 0,
            'transaction_max': 0,
            'has_transaction_data': False,
            'transaction_samples': []
        }
    
    def _send_request(self, params: Dict, max_retries: int = 3) -> requests.Response:
        """
        APIリクエストを送信（リトライ処理付き）
        
        Args:
            params: クエリパラメータ
            max_retries: 最大リトライ回数（デフォルト: 3回）
        
        Returns:
            requests.Response: レスポンスオブジェクト
        
        Raises:
            ValueError: APIキーが無効、パラメータが不正、またはAPIエラー
            requests.exceptions.RequestException: 接続エラー（リトライ後も失敗）
        """
        import time
        
        # リクエストヘッダー設定
        headers = {
            'Ocp-Apim-Subscription-Key': self.api_key or ''
        }
        
        # HTTPリクエスト送信
        url = f"{self.endpoint}/XIT001"
        
        last_exception = None
        
        # リトライ処理（指数バックオフ）
        for attempt in range(max_retries):
            try:
                logger.debug(f"APIリクエスト送信 (試行 {attempt + 1}/{max_retries}): {url}, params={params}")
                
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout
                )
                
                # ステータスコード確認
                if response.status_code == 401:
                    raise ValueError("❌ APIキーが無効です。.envのREINFOLIB_API_KEYを確認してください")
                elif response.status_code == 400:
                    raise ValueError(f"❌ パラメータが不正です: {params}")
                elif response.status_code != 200:
                    raise ValueError(f"❌ APIエラー: ステータスコード {response.status_code}, レスポンス: {response.text[:200]}")
                
                # 成功した場合はレスポンスを返す
                if attempt > 0:
                    logger.info(f"✅ APIリクエスト成功 (試行 {attempt + 1}/{max_retries})")
                return response
                
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException) as e:
                last_exception = e
                
                # 最後の試行でない場合は待機してリトライ
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # 指数バックオフ: 1秒, 2秒, 4秒...
                    logger.warning(f"⚠️ API接続エラー (試行 {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"⏳ {wait_time}秒待機してリトライします...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ APIリクエスト失敗 (全{max_retries}回試行): {e}")
                    raise
        
        # ここには到達しないはずだが、念のため
        if last_exception:
            raise last_exception
        raise requests.exceptions.RequestException("APIリクエストが失敗しました")
    
    def _parse_response(self, response: requests.Response) -> List[Dict]:
        """
        レスポンスをデコードしてJSONに変換
        
        Args:
            response: requestsのレスポンスオブジェクト
        
        Returns:
            List[Dict]: デコード済みJSONデータ
        """
        try:
            # まず普通のJSONとして試す（実際のAPIはgzipじゃないようだ）
            response_data = response.json()
            
            # レスポンス構造を確認: {'status': 'OK', 'data': [...]}
            if isinstance(response_data, dict):
                status = response_data.get('status', '')
                if status != 'OK':
                    error_msg = response_data.get('message', 'エラーが発生しました')
                    logger.error(f"❌ APIエラー: status={status}, message={error_msg}")
                    return []
                
                # dataキーから配列を取得
                data = response_data.get('data', [])
                if isinstance(data, list):
                    return data
                else:
                    logger.warning(f"予期しないデータ構造: dataキーの型が{type(data)}")
                    return []
            elif isinstance(response_data, list):
                # 直接リストの場合はそのまま返す（後方互換性）
                return response_data
            else:
                logger.warning(f"予期しないデータ構造: {type(response_data)}")
                return []
                
        except json.JSONDecodeError:
            # 普通のJSONでなければgzipを試す
            try:
                decoded = gzip.decompress(response.content)
                response_data = json.loads(decoded)
                
                # gzipデコード後も同じ構造を確認
                if isinstance(response_data, dict):
                    status = response_data.get('status', '')
                    if status != 'OK':
                        error_msg = response_data.get('message', 'エラーが発生しました')
                        logger.error(f"❌ APIエラー: status={status}, message={error_msg}")
                        return []
                    data = response_data.get('data', [])
                    return data if isinstance(data, list) else []
                elif isinstance(response_data, list):
                    return response_data
                else:
                    return []
            except Exception as e:
                logger.error(f"gzipデコードも失敗: {e}")
                # デバッグ用：最初の100文字を表示
                logger.debug(f"レスポンス先頭: {response.content[:100]}")
                return []
        except Exception as e:
            logger.error(f"パースエラー: {e}", exc_info=True)
            return []

