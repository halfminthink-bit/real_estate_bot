"""
データ準備テストスクリプト

取引価格APIから取得したデータを、記事生成プロンプトのプレースホルダに渡せる形式に整形する処理をテストする。
"""
import os
import sys
import json
import re
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.data_aggregator.collectors.transaction_price_collector import TransactionPriceCollector

# 環境変数を読み込み
load_dotenv()


def normalize_choume(choume: str) -> str:
    """
    町丁目を正規化（APIのDistrictNameに合わせる）
    
    Args:
        choume: 町丁目名（例: "上用賀6丁目"）
    
    Returns:
        str: 正規化後（例: "上用賀"）
    
    Examples:
        normalize_choume("上用賀6丁目") → "上用賀"
        normalize_choume("桜新町1丁目") → "桜新町"
        normalize_choume("深沢") → "深沢"
    """
    # 正規表現で数字より前の部分を抽出
    match = re.search(r'^([^0-9]+)', choume)
    return match.group(1) if match else choume


def prepare_transaction_data(
    choume: str,
    year: int = 2024,
    quarter: int = 3
) -> Dict:
    """
    取引価格データを取得してプレースホルダ用に整形
    
    Args:
        choume: 町丁目名（例: "上用賀6丁目"）
        year: 取引年（デフォルト: 2024）
        quarter: 四半期（デフォルト: 3）
    
    Returns:
        Dict: プレースホルダ用データ
        {
            'area_name': str,              # 正規化後の地域名
            'transaction_year': int,        # 取引年
            'transaction_quarter': int,     # 四半期
            'transaction_count': int,       # 取引件数
            'transaction_avg': int,         # 平均取引価格
            'transaction_min': int,         # 最小取引価格
            'transaction_max': int,         # 最大取引価格
            'has_transaction_data': bool,   # データ有無フラグ
            'transaction_samples': List[Dict]  # 取引事例（最大3件）
        }
    """
    # 1. TransactionPriceCollectorを初期化
    collector = TransactionPriceCollector()
    
    # 2. データ取得（get_area_transactions()を使用）
    try:
        raw_data = collector.get_area_transactions(
            ward="世田谷区",
            choume=choume,
            year=year,
            quarter=quarter
        )
    except Exception as e:
        print(f"❌ データ取得エラー: {e}")
        # デフォルト値を返す
        area_name = normalize_choume(choume)
        return {
            'area_name': area_name,
            'transaction_year': year,
            'transaction_quarter': quarter,
            'transaction_count': 0,
            'transaction_avg': 0,
            'transaction_min': 0,
            'transaction_max': 0,
            'has_transaction_data': False,
            'transaction_samples': []
        }
    
    # 3. raw_dataから情報を取得
    area_name = raw_data.get('area_name', normalize_choume(choume))
    data_count = raw_data.get('data_count', 0)
    transactions = raw_data.get('transactions', [])
    statistics = raw_data.get('statistics', {})
    
    # 4. データがない場合
    if data_count == 0:
        return {
            'area_name': area_name,
            'transaction_year': year,
            'transaction_quarter': quarter,
            'transaction_count': 0,
            'transaction_avg': 0,
            'transaction_min': 0,
            'transaction_max': 0,
            'has_transaction_data': False,
            'transaction_samples': []
        }
    
    # 5. データがある場合：統計情報とサンプルを整形
    transaction_avg = statistics.get('avg_price', 0)
    transaction_min = statistics.get('min_price', 0)
    transaction_max = statistics.get('max_price', 0)
    
    # 6. サンプル事例を整形（最大3件）
    transaction_samples = []
    for item in transactions[:3]:
        sample = {
            'type': item.get('Type', ''),
            'price': str(item.get('TradePrice', '')),
            'building_year': item.get('BuildingYear', ''),
            'floor_plan': item.get('FloorPlan', ''),
            'city_planning': item.get('CityPlanning', ''),
            'coverage_ratio': str(item.get('CoverageRatio', '')),
            'floor_area_ratio': str(item.get('FloorAreaRatio', '')),
            'land_shape': item.get('LandShape', ''),
            'frontage': str(item.get('Frontage', ''))
        }
        transaction_samples.append(sample)
    
    return {
        'area_name': area_name,
        'transaction_year': year,
        'transaction_quarter': quarter,
        'transaction_count': data_count,
        'transaction_avg': transaction_avg,
        'transaction_min': transaction_min,
        'transaction_max': transaction_max,
        'has_transaction_data': True,
        'transaction_samples': transaction_samples
    }


def main():
    """メイン実行関数"""
    print("\n" + "=" * 60)
    print("データ準備テスト")
    print("=" * 60)
    
    # 出力ディレクトリ作成
    output_dir = project_root / "output" / "test_data_preparation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # テストケース1: 上用賀6丁目（データあり想定）
    print("\n【テスト1】上用賀6丁目")
    print("-" * 60)
    
    choume1 = "上用賀6丁目"
    area_name1 = normalize_choume(choume1)
    print(f"\n町丁目: {choume1}")
    print(f"正規化後: {area_name1}")
    
    print("\n📡 取引データ取得中...")
    result1 = prepare_transaction_data("上用賀6丁目", year=2024, quarter=3)
    
    if result1['has_transaction_data']:
        print(f"✅ 取引データ取得成功: {result1['transaction_count']}件")
        
        # 取引事例を表示
        for i, sample in enumerate(result1['transaction_samples'], 1):
            print(f"\n取引事例 {i}:")
            print(f"  種類: {sample.get('type', 'N/A')}")
            print(f"  価格: {sample.get('price', 'N/A')}円")
            print(f"  建築年: {sample.get('building_year', 'N/A')}")
            if sample.get('floor_plan'):
                print(f"  間取り: {sample.get('floor_plan', 'N/A')}")
    else:
        print("⚠️  取引データなし")
    
    # 整形後のデータを表示
    print("\n【整形後のデータ】")
    print(f"  area_name: {result1['area_name']}")
    print(f"  transaction_count: {result1['transaction_count']}")
    if result1['has_transaction_data']:
        print(f"  transaction_avg: {result1['transaction_avg']:,}円")
        print(f"  transaction_min: {result1['transaction_min']:,}円")
        print(f"  transaction_max: {result1['transaction_max']:,}円")
    print(f"  has_transaction_data: {result1['has_transaction_data']}")
    
    # JSONファイルに保存
    output_path1 = output_dir / "test1_kamiyoga.json"
    with open(output_path1, 'w', encoding='utf-8') as f:
        json.dump(result1, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 保存完了: {output_path1}")
    
    # テストケース2: データがない町丁目
    print("\n" + "=" * 60)
    print("\n【テスト2】データがない町丁目")
    print("-" * 60)
    
    choume2 = "テスト1丁目"
    area_name2 = normalize_choume(choume2)
    print(f"\n町丁目: {choume2}")
    print(f"正規化後: {area_name2}")
    
    print("\n📡 取引データ取得中...")
    result2 = prepare_transaction_data("テスト1丁目", year=2024, quarter=3)
    
    if result2['has_transaction_data']:
        print(f"✅ 取引データ取得成功: {result2['transaction_count']}件")
    else:
        print("⚠️  取引データなし")
    
    # 整形後のデータを表示
    print("\n【整形後のデータ】")
    print(f"  area_name: {result2['area_name']}")
    print(f"  transaction_count: {result2['transaction_count']}")
    print(f"  has_transaction_data: {result2['has_transaction_data']}")
    
    # JSONファイルに保存
    output_path2 = output_dir / "test2_no_data.json"
    with open(output_path2, 'w', encoding='utf-8') as f:
        json.dump(result2, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 保存完了: {output_path2}")
    
    # 完了メッセージ
    print("\n" + "=" * 60)
    print("✅ テスト完了")
    print(f"出力先: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

