#!/usr/bin/env python3
"""
資産価値訴求に使えるe-Statデータの調査
"""

import os
import sys
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートを取得
project_root = Path(__file__).parent.parent

# .envファイルを読み込み
load_dotenv(project_root / '.env')

class AssetValueDataFinder:
    """資産価値訴求データの探索"""
    
    def __init__(self):
        self.api_key = os.getenv('ESTAT_API_KEY')
        if not self.api_key:
            raise ValueError("ESTAT_API_KEY が設定されていません。.envファイルに追加してください。")
        
        self.base_url = "https://api.e-stat.go.jp/rest/3.0/app"
        self.timeout = 60
    
    def search_datasets(self):
        """資産価値に関連するデータセットを検索"""
        
        # 検索キーワードリスト
        searches = [
            {
                "keyword": "将来推計人口",
                "purpose": "🎯 人口維持・増加の根拠",
                "message": "この地域は○年後も人口が維持される見込みです"
            },
            {
                "keyword": "昼夜間人口",
                "purpose": "🏢 商業活発性",
                "message": "昼間人口が多く、商業が活発なエリアです"
            },
            {
                "keyword": "従業地 通学地",
                "purpose": "🚃 都心アクセス",
                "message": "都心への通勤者が多い利便性の高いエリアです"
            },
            {
                "keyword": "経済センサス 事業所",
                "purpose": "📈 地域発展",
                "message": "事業所が増加しており、今後も発展が見込まれます"
            },
            {
                "keyword": "空き家",
                "purpose": "🏠 需要の高さ",
                "message": "空き家率が低く、需要が高いエリアです"
            },
            {
                "keyword": "持ち家率",
                "purpose": "🏡 資産形成志向",
                "message": "持ち家率が高く、資産形成に適したエリアです"
            }
        ]
        
        all_results = {}
        
        for search in searches:
            print(f"\n{'='*70}")
            print(f"🔍 検索: {search['keyword']}")
            print(f"目的: {search['purpose']}")
            print(f"訴求: {search['message']}")
            print('='*70)
            
            # 通常の統計表を検索
            results = self._search_api(search['keyword'], searchKind="1")
            
            # 小地域データも検索
            small_area_results = self._search_api(search['keyword'], searchKind="2")
            
            all_results[search['keyword']] = {
                'purpose': search['purpose'],
                'message': search['message'],
                'normal': results,
                'small_area': small_area_results
            }
            
            print(f"\n通常統計: {len(results)}件")
            if results:
                for i, r in enumerate(results[:3], 1):
                    print(f"  {i}. {r['title']}")
                    print(f"     ID: {r['id']}, 年: {r['survey_date']}")
            
            print(f"\n小地域統計: {len(small_area_results)}件")
            if small_area_results:
                for i, r in enumerate(small_area_results[:3], 1):
                    print(f"  {i}. {r['title']}")
                    print(f"     ID: {r['id']}, 年: {r['survey_date']}")
        
        # 結果を保存
        output_file = project_root / 'asset_value_datasets.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*70}")
        print(f"💾 結果を保存: {output_file}")
        print('='*70)
        
        return all_results
    
    def _search_api(self, keyword, searchKind="1"):
        """e-Stat APIで検索"""
        url = f"{self.base_url}/json/getStatsList"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "searchWord": keyword,
            "searchKind": searchKind,
            "surveyYears": "2015-2025",  # 広めに検索
            "limit": 10
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'GET_STATS_LIST' in data and 'DATALIST_INF' in data['GET_STATS_LIST']:
                datalist = data['GET_STATS_LIST']['DATALIST_INF']
                
                if datalist.get('NUMBER', 0) == 0:
                    return []
                
                tables = datalist.get('TABLE_INF', [])
                if not isinstance(tables, list):
                    tables = [tables]
                
                results = []
                for table in tables:
                    title = table.get('TITLE', {})
                    if isinstance(title, dict):
                        title = title.get('$', 'N/A')
                    else:
                        title = title or 'N/A'
                    
                    org = table.get('GOV_ORG', {})
                    if isinstance(org, dict):
                        org = org.get('$', 'N/A')
                    else:
                        org = org or 'N/A'
                    
                    results.append({
                        'id': table.get('@id', 'N/A'),
                        'title': title,
                        'survey_date': table.get('SURVEY_DATE', 'N/A'),
                        'org': org
                    })
                
                return results
            
            return []
            
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  リクエストエラー: {e}")
            return []
        except Exception as e:
            print(f"   ⚠️  エラー: {e}")
            return []


def main():
    print("\n🎯 資産価値訴求データの探索開始")
    print("="*70)
    
    try:
        finder = AssetValueDataFinder()
        results = finder.search_datasets()
        
        print("\n✅ 探索完了！")
        print("\n次のステップ:")
        print("1. asset_value_datasets.json を確認")
        print("2. 使えるデータセットIDをリストアップ")
        print("3. 実際にデータ取得テスト")
        
    except ValueError as e:
        print(f"\n❌ エラー: {e}")
        print("\n.envファイルに以下を追加してください:")
        print("ESTAT_API_KEY=your-api-key-here")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


