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
        self.timeout = timeout or int(os.getenv('REINFOLIB_API_TIMEOUT', '30'))
        
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
        year: int,
        quarter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        特定の町丁目の取引データを取得（エリア全体）
        
        Args:
            ward: 区名（例: "世田谷区"）
            choume: 町丁目名（例: "上用賀6丁目"）
            year: 取引年
            quarter: 四半期
        
        Returns:
            Dict: {
                'area_name': str,           # 正規化後の地域名
                'choume_full': str,         # 元の町丁目名
                'data_count': int,          # 取引件数
                'transactions': List[Dict], # 取引データ
                'statistics': Dict          # 統計情報
            }
        """
        # 1. 町丁目を正規化（"上用賀6丁目" → "上用賀"）
        area_name = self._normalize_choume(choume)
        
        # 2. 世田谷区全体のデータを取得
        # 世田谷区のコードは13112
        city_code = "13112" if ward == "世田谷区" else None
        
        if not city_code:
            logger.warning(f"⚠️  {ward}の市区町村コードが不明です")
            return self._empty_result(area_name, choume)
        
        all_data = self.get_transaction_data(
            year=year,
            quarter=quarter,
            city=city_code
        )
        
        # 3. 該当エリアでフィルタリング
        # DistrictNameに area_name が含まれるデータを抽出
        filtered_data = [
            item for item in all_data
            if area_name in item.get('DistrictName', '')
        ]
        
        # 4. データがない場合
        if not filtered_data:
            return self._empty_result(area_name, choume)
        
        # 5. 統計情報を計算
        prices = []
        for item in filtered_data:
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
            return self._empty_result(area_name, choume)
        
        sorted_prices = sorted(prices)
        statistics = {
            'avg_price': sum(prices) // len(prices),
            'min_price': min(prices),
            'max_price': max(prices),
            'median_price': sorted_prices[len(sorted_prices) // 2]
        }
        
        return {
            'area_name': area_name,
            'choume_full': choume,
            'data_count': len(filtered_data),
            'transactions': filtered_data,
            'statistics': statistics
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
        空の結果を返す
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
    
    def _send_request(self, params: Dict) -> requests.Response:
        """
        APIリクエストを送信
        
        Args:
            params: クエリパラメータ
        
        Returns:
            requests.Response: レスポンスオブジェクト
        """
        # リクエストヘッダー設定
        headers = {
            'Ocp-Apim-Subscription-Key': self.api_key or ''
        }
        
        # HTTPリクエスト送信
        url = f"{self.endpoint}/XIT001"
        
        logger.debug(f"APIリクエスト送信: {url}, params={params}")
        
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
        
        return response
    
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

