#!/usr/bin/env python3
"""
e-Stat API テストスクリプト

取得できるデータの種類を確認し、実際にデータを取得してみる
"""

import os
import sys
import argparse
import requests
import json
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Optional

# プロジェクトルートを取得
project_root = Path(__file__).parent.parent

# .envファイルを読み込み（オーバーライド可能）
load_dotenv(project_root / '.env')

class EStatAPITester:
    """e-Stat APIのテスター"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: APIキー（Noneの場合は環境変数から取得）
        """
        # コマンドライン引数 > 環境変数の順で取得
        self.api_key = api_key or os.getenv('ESTAT_API_KEY')
        if not self.api_key:
            raise ValueError("ESTAT_API_KEY が設定されていません。.envファイルまたは--api-keyオプションで指定してください。")
        
        self.base_url = "https://api.e-stat.go.jp/rest/3.0/app"
        self.timeout = 60  # タイムアウトを60秒に延長
        print(f"✅ APIキー確認OK: {self.api_key[:10]}...")
    
    def test_connection(self) -> bool:
        """API接続テスト"""
        print("\n" + "="*60)
        print("【1】API接続テスト")
        print("="*60)
        
        url = f"{self.base_url}/json/getStatsList"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "surveyYears": "2020"  # 2020年のデータを検索
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('GET_STATS_LIST'):
                print("✅ 接続成功！")
                result = data['GET_STATS_LIST']['RESULT']
                print(f"ステータス: {result.get('STATUS')}")
                print(f"エラーメッセージ: {result.get('ERROR_MSG', 'なし')}")
                return True
            else:
                print("❌ 接続失敗")
                return False
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    
    def search_available_stats(self, keyword: str = "人口") -> List[Dict]:
        """利用可能な統計データを検索"""
        print("\n" + "="*60)
        print(f"【2】統計データ検索: キーワード「{keyword}」")
        print("="*60)
        
        url = f"{self.base_url}/json/getStatsList"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "searchWord": keyword,
            "limit": 10
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            data = response.json()
            
            stats_list = data['GET_STATS_LIST']['DATALIST_INF']['TABLE_INF']
            
            print(f"\n見つかった統計: {len(stats_list)}件\n")
            
            results = []
            for i, stat in enumerate(stats_list, 1):
                info = {
                    'id': stat.get('@id'),
                    'title': stat.get('TITLE', {}).get('$'),
                    'org': stat.get('GOV_ORG', {}).get('$'),
                    'survey_date': stat.get('SURVEY_DATE')
                }
                results.append(info)
                
                print(f"{i}. {info['title']}")
                print(f"   組織: {info['org']}")
                print(f"   調査日: {info['survey_date']}")
                print(f"   統計ID: {info['id']}")
                print()
            
            return results
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            return []
    
    def get_meta_info(self, stats_data_id: str) -> Dict:
        """統計データのメタ情報を取得"""
        print("\n" + "="*60)
        print(f"【3】メタ情報取得: {stats_data_id}")
        print("="*60)
        
        url = f"{self.base_url}/json/getMetaInfo"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "statsDataId": stats_data_id
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            data = response.json()
            
            meta = data['GET_META_INFO']['METADATA_INF']
            
            print(f"\n統計名: {meta.get('TITLE', {}).get('$')}")
            print(f"\n【利用可能な項目】")
            
            class_obj = meta.get('CLASS_INF', {}).get('CLASS_OBJ', [])
            
            for obj in class_obj:
                print(f"\n- {obj.get('@name')}")
                classes = obj.get('CLASS', [])
                if isinstance(classes, dict):
                    classes = [classes]
                
                for cls in classes[:5]:  # 最初の5件だけ表示
                    print(f"  • {cls.get('@name')} (コード: {cls.get('@code')})")
                
                if len(classes) > 5:
                    print(f"  ... 他 {len(classes) - 5}件")
            
            return meta
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            return {}
    
    def get_sample_data(self, stats_data_id: str, limit: int = 10) -> pd.DataFrame:
        """実際のデータを取得（サンプル）"""
        print("\n" + "="*60)
        print(f"【4】データ取得: {stats_data_id}")
        print("="*60)
        
        url = f"{self.base_url}/json/getStatsData"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "statsDataId": stats_data_id,
            "limit": limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            data = response.json()
            
            values = data['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']
            
            # DataFrameに変換
            df = pd.DataFrame(values)
            
            print(f"\n取得件数: {len(df)}件")
            print(f"\nカラム: {list(df.columns)}")
            print(f"\nサンプルデータ（最初の5件）:")
            print(df.head())
            
            # 基本統計
            if '$' in df.columns:
                print(f"\n値の統計:")
                df['$'] = pd.to_numeric(df['$'], errors='coerce')
                print(df['$'].describe())
            
            return df
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            return pd.DataFrame()
    
    def test_population_data(self):
        """人口統計データの取得テスト（令和2年国勢調査・町丁目レベル）"""
        print("\n" + "="*60)
        print("【5】町丁目レベル人口データの実践テスト")
        print("="*60)
        
        # 令和2年国勢調査 小地域集計（町丁目レベル）
        stats_data_id = "0003445068"
        
        url = f"{self.base_url}/json/getStatsData"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "statsDataId": stats_data_id,
            "cdArea": "13112",  # 世田谷区のコード
            "limit": 100
        }
        
        try:
            print(f"\n世田谷区の町丁目別人口データを取得中...")
            print(f"統計ID: {stats_data_id}")
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # デバッグ：レスポンス構造を確認
            print("\n【レスポンス構造の確認】")
            if 'GET_STATS_DATA' in data:
                print("✅ GET_STATS_DATA: あり")
                result = data['GET_STATS_DATA'].get('RESULT', {})
                print(f"   STATUS: {result.get('STATUS')}")
                print(f"   ERROR_MSG: {result.get('ERROR_MSG', 'なし')}")
                
                if 'STATISTICAL_DATA' in data['GET_STATS_DATA']:
                    print("✅ STATISTICAL_DATA: あり")
                    stat_data = data['GET_STATS_DATA']['STATISTICAL_DATA']
                    print(f"   キー: {list(stat_data.keys())}")
                    
                    # データの存在確認
                    if 'DATA_INF' in stat_data:
                        print("✅ DATA_INF: あり")
                        data_inf = stat_data['DATA_INF']
                        
                        if 'VALUE' in data_inf:
                            values = data_inf['VALUE']
                            print(f"✅ VALUE: あり（{len(values)}件）")
                            
                            # DataFrameに変換
                            df = pd.DataFrame(values)
                            
                            print(f"\n【取得データ】")
                            print(f"件数: {len(df)}件")
                            print(f"カラム: {list(df.columns)}")
                            print(f"\nサンプル（最初の10件）:")
                            print(df.head(10))
                            
                            # データの値を確認
                            if '$' in df.columns:
                                df['値'] = pd.to_numeric(df['$'], errors='coerce')
                                print(f"\n【統計情報】")
                                print(df['値'].describe())
                            
                            # CSVに保存
                            output_file = "estat_choume_population.csv"
                            df.to_csv(output_file, index=False, encoding='utf-8-sig')
                            print(f"\n💾 保存完了: {output_file}")
                            
                            return df
                        else:
                            print("❌ VALUE が見つかりません")
                            print(f"   DATA_INFのキー: {list(data_inf.keys())}")
                    else:
                        print("❌ DATA_INF が見つかりません")
                else:
                    print("❌ STATISTICAL_DATA が見つかりません")
            else:
                print("❌ GET_STATS_DATA が見つかりません")
                print(f"レスポンスのキー: {list(data.keys())}")
            
            # 失敗時は全レスポンスを出力
            print("\n【フルレスポンス（最初の2000文字）】")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
            
            return pd.DataFrame()
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTPエラー: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   レスポンス: {e.response.text[:500]}")
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
        
        return pd.DataFrame()
    
    def show_useful_datasets(self):
        """不動産プロジェクトに役立つデータセット一覧（2025年11月時点）"""
        print("\n" + "="*60)
        print("【6】不動産プロジェクトで使えるe-Statデータセット（最新版）")
        print("="*60)
        
        datasets = [
            {
                "name": "令和2年国勢調査 小地域集計",
                "id": "0003445068",
                "level": "🎯 町丁目レベル",
                "description": "人口、世帯数、年齢別人口（町丁目ごと）",
                "use_case": "人口密度、世帯構成の詳細分析",
                "priority": "⭐⭐⭐ 最重要"
            },
            {
                "name": "令和2年国勢調査 人口等基本集計",
                "id": "0003445855",
                "level": "市区町村",
                "description": "総人口、年齢構成、世帯構成",
                "use_case": "エリア全体の人口動態",
                "priority": "⭐⭐"
            },
            {
                "name": "経済センサス 事業所集計（2021年）",
                "id": "0003431555",
                "level": "町丁目可能",
                "description": "事業所数、従業者数、産業分類",
                "use_case": "利便性スコア（商業施設密度）",
                "priority": "⭐⭐⭐"
            },
            {
                "name": "住宅・土地統計調査（2018年）",
                "id": "0003348423",
                "level": "市区町村",
                "description": "住宅種類、建築年、設備",
                "use_case": "住環境スコア算出",
                "priority": "⭐"
            }
        ]
        
        for i, ds in enumerate(datasets, 1):
            print(f"\n{i}. {ds['name']} {ds['priority']}")
            print(f"   統計ID: {ds['id']}")
            print(f"   レベル: {ds['level']}")
            print(f"   内容: {ds['description']}")
            print(f"   活用例: {ds['use_case']}")
    
    def find_tokyo_small_area_stats(self):
        """東京都の小地域（町丁目レベル）統計表IDを検索"""
        print("\n" + "="*60)
        print("【7】東京都の小地域統計表ID検索")
        print("="*60)
        
        url = f"{self.base_url}/json/getStatsList"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "statsCode": "00200521",  # 国勢調査
            "searchKind": "2",  # 小地域・地域メッシュ
            "surveyYears": "2020",  # 令和2年
            "searchWord": "東京"
        }
        
        try:
            print("\n検索中...")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'GET_STATS_LIST' in data and 'DATALIST_INF' in data['GET_STATS_LIST']:
                datalist = data['GET_STATS_LIST']['DATALIST_INF']
                
                if datalist.get('NUMBER', 0) == 0:
                    print("❌ 該当する統計表が見つかりません")
                    return []
                
                tables = datalist.get('TABLE_INF', [])
                if not isinstance(tables, list):
                    tables = [tables]
                
                print(f"\n見つかった統計表: {len(tables)}件\n")
                
                results = []
                for i, table in enumerate(tables, 1):
                    info = {
                        'id': table.get('@id'),
                        'title': table.get('TITLE', {}).get('$', 'N/A') if isinstance(table.get('TITLE'), dict) else table.get('TITLE', 'N/A'),
                        'survey_date': table.get('SURVEY_DATE'),
                        'total_number': table.get('OVERALL_TOTAL_NUMBER')
                    }
                    results.append(info)
                    
                    print(f"{i}. {info['title']}")
                    print(f"   統計表ID: {info['id']}")
                    print(f"   調査日: {info['survey_date']}")
                    print(f"   総件数: {info['total_number']}")
                    print()
                
                # 統計表IDリストを保存
                output_file = "tokyo_small_area_table_ids.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"💾 統計表IDリストを保存: {output_file}")
                
                return results
            else:
                print("❌ 予期しないレスポンス構造")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
                return []
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def test_small_area_data(self, table_id: str):
        """特定の統計表IDで小地域データを取得"""
        print("\n" + "="*60)
        print(f"【8】小地域データ取得テスト: {table_id}")
        print("="*60)
        
        url = f"{self.base_url}/json/getStatsData"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "statsDataId": table_id,
            "limit": 100
        }
        
        try:
            print(f"\nデータ取得中...")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # レスポンス確認
            if 'GET_STATS_DATA' in data:
                result = data['GET_STATS_DATA'].get('RESULT', {})
                print(f"STATUS: {result.get('STATUS')}")
                print(f"ERROR_MSG: {result.get('ERROR_MSG', 'なし')}")
                
                if result.get('STATUS') == 0:  # 成功
                    stat_data = data['GET_STATS_DATA']['STATISTICAL_DATA']
                    
                    if 'DATA_INF' in stat_data and 'VALUE' in stat_data['DATA_INF']:
                        values = stat_data['DATA_INF']['VALUE']
                        df = pd.DataFrame(values)
                        
                        print(f"\n✅ 取得成功！ {len(df)}件")
                        print(f"\nカラム: {list(df.columns)}")
                        print(f"\nサンプル（最初の20件）:")
                        print(df.head(20))
                        
                        # CSVに保存
                        output_file = f"estat_data_{table_id}.csv"
                        df.to_csv(output_file, index=False, encoding='utf-8-sig')
                        print(f"\n💾 保存完了: {output_file}")
                        
                        return df
                    else:
                        print("❌ DATA_INF/VALUE が見つかりません")
                        if 'DATA_INF' in stat_data:
                            print(f"   DATA_INFのキー: {list(stat_data['DATA_INF'].keys())}")
                else:
                    print("❌ APIエラーが発生")
            else:
                print("❌ 予期しないレスポンス")
                print(f"レスポンスのキー: {list(data.keys())}")
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def run_all_tests(self):
        """全テストを実行"""
        print("\n" + "🔍 e-Stat API 完全テスト")
        print("="*60)
        
        # 1. 接続テスト
        if not self.test_connection():
            print("\n❌ API接続に失敗しました。APIキーを確認してください。")
            return
        
        # 2. データ検索（参考用）
        stats = self.search_available_stats("人口")
        
        # 3. メタ情報取得（参考用）
        if stats:
            self.get_meta_info(stats[0]['id'])
        
        # 4. 🎯 東京都の小地域統計表IDを検索（重要！）
        tokyo_tables = self.find_tokyo_small_area_stats()
        
        # 5. 見つかった統計表で実際にデータ取得
        if tokyo_tables:
            print("\n" + "="*60)
            print("【実データ取得テスト】")
            print("="*60)
            
            # 最初の3つの統計表でテスト
            for table in tokyo_tables[:3]:
                self.test_small_area_data(table['id'])
                print("\n" + "-"*60)
        else:
            print("\n⚠️  小地域統計表が見つかりませんでした。従来の方法でテストを続行します。")
            # 4. 実際のデータ取得（フォールバック）
            self.test_population_data()
        
        # 6. 使えるデータセット一覧
        self.show_useful_datasets()
        
        print("\n" + "="*60)
        print("✅ テスト完了！")
        print("="*60)


def main():
    """メイン実行"""
    parser = argparse.ArgumentParser(
        description='e-Stat API テストスクリプト',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/explore_estat.py
  python scripts/explore_estat.py --api-key YOUR_API_KEY
  python scripts/explore_estat.py --api-key YOUR_API_KEY --timeout 120
        """
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='e-Stat APIキー（.envファイルのESTAT_API_KEYより優先されます）'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='リクエストタイムアウト（秒、デフォルト: 60）'
    )
    
    args = parser.parse_args()
    
    try:
        tester = EStatAPITester(api_key=args.api_key)
        if args.timeout != 60:
            tester.timeout = args.timeout
            print(f"⏱️  タイムアウト設定: {args.timeout}秒")
        tester.run_all_tests()
        
    except ValueError as e:
        print(f"\n❌ エラー: {e}")
        print("\n以下のいずれかの方法でAPIキーを設定してください:")
        print("1. .envファイルに以下を追加:")
        print("   ESTAT_API_KEY=your-api-key-here")
        print("2. コマンドライン引数で指定:")
        print("   python scripts/explore_estat.py --api-key YOUR_API_KEY")
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()