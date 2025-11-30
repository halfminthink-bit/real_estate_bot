#!/usr/bin/env python3
"""
資産価値訴求に使えるe-Statデータの完全調査

正しい検索方法：
- statsCode（政府統計コード）を指定
- searchKind=1（通常統計）と searchKind=2（小地域）を両方検索
"""

import os
import sys
import requests
import json
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List

# プロジェクトルートを取得
project_root = Path(__file__).parent.parent

# .envファイルを読み込み
load_dotenv(project_root / '.env')

class AssetValueDataInvestigator:
    """資産価値訴求データの詳細調査"""
    
    def __init__(self):
        self.api_key = os.getenv('ESTAT_API_KEY')
        if not self.api_key:
            raise ValueError("ESTAT_API_KEY が設定されていません。.envファイルに追加してください。")
        
        self.base_url = "https://api.e-stat.go.jp/rest/3.0/app"
        self.timeout = 60
    
    def investigate_all(self):
        """全ての重要統計を調査"""
        
        # 📊 調査対象の政府統計
        stats_to_check = [
            {
                "name": "国勢調査（従業地・通学地）",
                "stats_code": "00200521",
                "survey_years": "2020",
                "purpose": "🎯 昼夜間人口比率（商業活発性）",
                "message": "昼間人口が多く、商業が活発なエリアです",
                "priority": "⭐⭐⭐"
            },
            {
                "name": "経済センサス-活動調査",
                "stats_code": "00200553",
                "survey_years": "2021",
                "purpose": "📈 事業所数・従業者数（地域発展）",
                "message": "事業所が増加しており、今後も発展が見込まれます",
                "priority": "⭐⭐⭐"
            },
            {
                "name": "住宅・土地統計調査",
                "stats_code": "00200522",
                "survey_years": "2018",
                "purpose": "🏠 空き家率・持ち家率",
                "message": "空き家率が低く、需要が高いエリアです",
                "priority": "⭐⭐"
            },
            {
                "name": "人口推計",
                "stats_code": "00200524",
                "survey_years": "2020-2025",
                "purpose": "📊 人口動態",
                "message": "人口が維持・増加傾向のエリアです",
                "priority": "⭐⭐"
            }
        ]
        
        all_results = {}
        
        for stat in stats_to_check:
            print("\n" + "="*80)
            print(f"📊 {stat['name']} （政府統計コード: {stat['stats_code']}）")
            print(f"目的: {stat['purpose']}")
            print(f"訴求: {stat['message']}")
            print(f"優先度: {stat['priority']}")
            print("="*80)
            
            # 通常統計を検索
            print("\n【通常統計】")
            normal_results = self._search_by_stats_code(
                stat['stats_code'], 
                stat['survey_years'],
                searchKind="1"
            )
            
            # 小地域統計を検索
            print("\n【小地域統計】")
            small_area_results = self._search_by_stats_code(
                stat['stats_code'], 
                stat['survey_years'],
                searchKind="2"
            )
            
            all_results[stat['name']] = {
                'stats_code': stat['stats_code'],
                'purpose': stat['purpose'],
                'message': stat['message'],
                'priority': stat['priority'],
                'normal': normal_results,
                'small_area': small_area_results
            }
        
        # 結果を保存
        output_file = project_root / 'asset_value_investigation.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*80)
        print(f"💾 調査結果を保存: {output_file}")
        print("="*80)
        
        # サマリーを表示
        self._print_summary(all_results)
        
        return all_results
    
    def _search_by_stats_code(self, stats_code: str, survey_years: str, searchKind: str = "1") -> List[Dict]:
        """政府統計コードで検索"""
        
        url = f"{self.base_url}/json/getStatsList"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "statsCode": stats_code,
            "surveyYears": survey_years,
            "searchKind": searchKind,
            "limit": 20
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'GET_STATS_LIST' in data and 'DATALIST_INF' in data['GET_STATS_LIST']:
                datalist = data['GET_STATS_LIST']['DATALIST_INF']
                
                if datalist.get('NUMBER', 0) == 0:
                    print(f"   見つかりません（0件）")
                    return []
                
                tables = datalist.get('TABLE_INF', [])
                if not isinstance(tables, list):
                    tables = [tables]
                
                print(f"   見つかりました: {len(tables)}件\n")
                
                results = []
                for i, table in enumerate(tables[:10], 1):  # 最初の10件だけ表示
                    title = table.get('TITLE', {})
                    if isinstance(title, dict):
                        title = title.get('$', 'N/A')
                    else:
                        title = title or 'N/A'
                    
                    info = {
                        'id': table.get('@id', 'N/A'),
                        'title': title,
                        'survey_date': table.get('SURVEY_DATE', 'N/A'),
                        'total_number': table.get('OVERALL_TOTAL_NUMBER', 'N/A')
                    }
                    results.append(info)
                    
                    print(f"   {i}. {info['title']}")
                    print(f"      統計表ID: {info['id']}, 件数: {info['total_number']}")
                
                if len(tables) > 10:
                    print(f"   ... 他 {len(tables) - 10}件")
                
                return results
            
            return []
            
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  リクエストエラー: {e}")
            return []
        except Exception as e:
            print(f"   ⚠️  エラー: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _print_summary(self, results: Dict):
        """調査結果のサマリーを表示"""
        
        print("\n" + "="*80)
        print("📋 調査結果サマリー")
        print("="*80)
        
        for stat_name, data in results.items():
            normal_count = len(data['normal'])
            small_area_count = len(data['small_area'])
            
            status = "✅ 使える" if (normal_count > 0 or small_area_count > 0) else "❌ データなし"
            
            print(f"\n{status} {stat_name} {data['priority']}")
            print(f"   目的: {data['purpose']}")
            print(f"   通常統計: {normal_count}件 / 小地域: {small_area_count}件")
            
            if normal_count == 0 and small_area_count == 0:
                print(f"   → 政府統計コード {data['stats_code']} ではデータが見つかりませんでした")
        
        print("\n" + "="*80)
        print("✅ 次のステップ:")
        print("1. asset_value_investigation.json を確認")
        print("2. 使える統計表IDをリストアップ")
        print("3. 実際にデータ取得テスト")
        print("="*80)


def main():
    print("\n🔍 資産価値訴求データの完全調査")
    print("="*80)
    print("方法: 政府統計コード（statsCode）で検索")
    print("="*80)
    
    try:
        investigator = AssetValueDataInvestigator()
        results = investigator.investigate_all()
        
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


