"""
不動産情報ライブラリAPI テストスクリプト

テスト内容:
1. PostgreSQLから世田谷区の町丁目リストを取得
2. 各町丁目の取引価格データをAPIから取得
3. レスポンスをJSONファイルに保存
4. データの統計情報を表示
"""
import os
import sys
import json
import psycopg2
from datetime import datetime
from typing import List, Dict, Tuple
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.data_aggregator.collectors.transaction_price_collector import TransactionPriceCollector

# 環境変数を読み込み
load_dotenv()

def get_db_connection():
    """PostgreSQL接続を取得"""
    import yaml
    
    config_path = project_root / 'config' / 'database.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return psycopg2.connect(
        host=os.getenv('DB_HOST', config['postgresql'].get('host', 'localhost')),
        port=os.getenv('DB_PORT', config['postgresql'].get('port', 5432)),
        database=os.getenv('DB_NAME', config['postgresql'].get('database', 'real_estate_dev')),
        user=os.getenv('DB_USER', config['postgresql'].get('user', 'postgres')),
        password=os.getenv('DB_PASSWORD', config['postgresql'].get('password', 'postgres'))
    )

def check_postgresql_connection():
    """PostgreSQL接続とデータの確認"""
    print("\n【デバッグ】PostgreSQL接続確認")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. テーブルの存在確認
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'land_prices_kokudo'
        """)
        table_exists = cursor.fetchone()[0]
        print(f"✅ land_prices_kokudo テーブル存在: {'はい' if table_exists else 'いいえ'}")
        
        # 2. データ件数確認
        cursor.execute("SELECT COUNT(*) FROM land_prices_kokudo")
        total_count = cursor.fetchone()[0]
        print(f"✅ 総データ件数: {total_count:,}件")
        
        # 3. サンプルデータを10件表示（住所形式を確認）
        cursor.execute("""
            SELECT original_address, survey_year
            FROM land_prices_kokudo 
            LIMIT 10
        """)
        samples = cursor.fetchall()
        print(f"\n【重要】サンプル住所（最初の10件）:")
        for i, row in enumerate(samples, 1):
            print(f"  {i}. {row[1]}年: {row[0]}")
        
        # 4. 住所に含まれる文字のパターン確認
        cursor.execute("""
            SELECT 
                original_address,
                CASE 
                    WHEN original_address LIKE '%世田谷区%' THEN '世田谷区を含む'
                    WHEN original_address LIKE '%区%' THEN 'その他の区を含む'
                    WHEN original_address LIKE '%市%' THEN '市を含む'
                    ELSE 'その他'
                END as pattern
            FROM land_prices_kokudo
            LIMIT 5
        """)
        patterns = cursor.fetchall()
        print(f"\n【住所パターン分析】")
        for addr, pattern in patterns:
            print(f"  パターン: {pattern}")
            print(f"  → {addr}")
        
        # 5. 最新年度確認
        cursor.execute("""
            SELECT MAX(survey_year), MIN(survey_year) 
            FROM land_prices_kokudo
        """)
        max_year, min_year = cursor.fetchone()
        print(f"\n✅ 年度範囲: {min_year}年 ～ {max_year}年")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL接続エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_setagaya_choume_list() -> List[str]:
    """
    PostgreSQLから世田谷区の町丁目リストを取得
    
    Returns:
        List[str]: 町丁目名のリスト（例: ["上用賀6丁目", "桜新町1丁目", ...]）
    """
    import re
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 修正版クエリ：もっとシンプルに
    query = """
    SELECT DISTINCT original_address
    FROM land_prices_kokudo
    WHERE original_address LIKE '%世田谷区%'
      AND survey_year = (SELECT MAX(survey_year) FROM land_prices_kokudo)
    ORDER BY original_address;
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Pythonで町丁目を抽出
    choume_set = set()
    
    for row in results:
        address = row[0]
        # 正規表現で町丁目を抽出（例: "上用賀6丁目"）
        match = re.search(r'([^区]+\d+丁目)', address)
        if match:
            choume_set.add(match.group(1))
    
    choume_list = sorted(list(choume_set))
    
    print(f"✅ PostgreSQLから{len(choume_list)}件の町丁目を取得しました")
    
    # デバッグ用：最初の5件の住所も表示
    if results:
        print(f"\n【デバッグ】最初の5件の住所:")
        for i, row in enumerate(results[:5], 1):
            print(f"  {i}. {row[0]}")
    
    return choume_list

def test_api_single_area():
    """
    TEST 1: 世田谷区全体の取引データ取得
    
    テスト内容:
    - 2024年Q3の世田谷区全体データを取得
    - レスポンス件数とサンプルデータを表示
    - JSONファイルに保存
    """
    print("\n" + "=" * 60)
    print("TEST 1: 世田谷区全体の取引データ取得")
    print("=" * 60)
    
    # コレクター初期化
    collector = TransactionPriceCollector()
    
    # 世田谷区の2024年Q3データ取得
    print("\n📡 API呼び出し中...")
    data = collector.get_transaction_data(
        year=2024,
        quarter=3,
        city="13112"  # 世田谷区
    )
    
    # 結果表示
    if data:
        print(f"✅ 取得成功: {len(data)}件")
        print(f"\n【データサンプル（最初の3件）】")
        for i, item in enumerate(data[:3], 1):
            print(f"{i}. {item.get('Type', 'N/A')} | "
                  f"{item.get('DistrictName', 'N/A')} | "
                  f"{item.get('TradePrice', 'N/A')}円 | "
                  f"{item.get('FloorPlan', 'N/A')} | "
                  f"{item.get('BuildingYear', 'N/A')}")
    else:
        print("⚠️  データが取得できませんでした")
        return
    
    # JSONファイルに保存
    output_dir = project_root / "output" / "test_api_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        "metadata": {
            "api": "reinfolib_transaction_prices",
            "endpoint": "XIT001",
            "params": {
                "year": 2024,
                "quarter": 3,
                "city": "13112"
            },
            "fetched_at": datetime.now().isoformat(),
            "total_records": len(data)
        },
        "data": data
    }
    
    output_path = output_dir / "setagaya_2024q3.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 保存完了: {output_path}")

def test_api_specific_choume():
    """
    TEST 2: 特定の町丁目の取引データ取得
    
    テスト内容:
    - DBから上用賀6丁目を確認
    - APIで上用賀エリアの取引データを取得
    - フィルタリング結果を表示
    """
    print("\n" + "=" * 60)
    print("TEST 2: 上用賀6丁目の取引データ取得")
    print("=" * 60)
    
    # コレクター初期化
    collector = TransactionPriceCollector()
    
    # 上用賀6丁目のデータ取得
    print("\n📡 API呼び出し中...")
    data = collector.get_choume_transactions(
        ward="世田谷区",
        choume="上用賀6丁目",
        year=2024,
        quarter=3
    )
    
    # 結果表示
    if data:
        print(f"✅ フィルタリング結果: {len(data)}件")
        print(f"\n【上用賀6丁目周辺の取引事例】")
        for i, item in enumerate(data[:5], 1):
            print(f"{i}. {item.get('Type', 'N/A')} | "
                  f"{item.get('TradePrice', 'N/A')}円 | "
                  f"{item.get('FloorPlan', 'N/A')} | "
                  f"{item.get('BuildingYear', 'N/A')}")
    else:
        print("⚠️  上用賀6丁目のデータが見つかりませんでした")
        return
    
    # JSONファイルに保存
    output_dir = project_root / "output" / "test_api_results"
    output_data = {
        "metadata": {
            "ward": "世田谷区",
            "choume": "上用賀6丁目",
            "year": 2024,
            "quarter": 3,
            "total_records": len(data),
            "fetched_at": datetime.now().isoformat()
        },
        "data": data
    }
    
    output_path = output_dir / "kamiyoga_6chome_2024q3.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 保存完了: {output_path}")

def test_api_multiple_years():
    """
    TEST 3: 複数年度のトレンド確認
    
    テスト内容:
    - 2020-2024年の各年Q3データを取得
    - 年度ごとの統計情報を計算
    - トレンドを表示
    """
    print("\n" + "=" * 60)
    print("TEST 3: 複数年度のトレンド確認（2020-2024年）")
    print("=" * 60)
    
    # コレクター初期化
    collector = TransactionPriceCollector()
    
    # 各年のデータ取得
    years = [2020, 2021, 2022, 2023, 2024]
    results = []
    
    for year in years:
        print(f"\n📡 {year}年Q3のデータ取得中...")
        data = collector.get_transaction_data(
            year=year,
            quarter=3,
            city="13112"
        )
        
        if data:
            # 統計情報を計算
            prices = []
            for item in data:
                price_str = item.get('TradePrice', '0')
                if price_str and price_str != 'N/A':
                    try:
                        prices.append(int(price_str))
                    except (ValueError, TypeError):
                        pass
            
            avg_price = sum(prices) // len(prices) if prices else 0
            
            results.append({
                'year': year,
                'count': len(data),
                'avg_price': avg_price
            })
            print(f"   ✅ {len(data)}件取得（平均価格: {avg_price:,}円）")
        else:
            print(f"   ⚠️  データなし")
    
    # トレンド表示
    print("\n" + "=" * 60)
    print("【年度別トレンド】")
    print("=" * 60)
    print(f"{'年度':<8} | {'取引件数':<10} | {'平均取引価格'}")
    print("-" * 60)
    for r in results:
        print(f"{r['year']:<8} | {r['count']:<10} | {r['avg_price']:>12,}円")
    
    # JSONファイルに保存
    output_dir = project_root / "output" / "test_api_results"
    output_path = output_dir / "trend_2020_2024.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 保存完了: {output_path}")

def analyze_response_structure():
    """
    TEST 4: レスポンスデータ構造の分析
    
    テスト内容:
    - APIレスポンスの全フィールドを抽出
    - 各フィールドのサンプル値を表示
    - データ型と欠損率を確認
    """
    print("\n" + "=" * 60)
    print("TEST 4: レスポンスデータ構造の分析")
    print("=" * 60)
    
    # サンプルデータ取得
    collector = TransactionPriceCollector()
    data = collector.get_transaction_data(
        year=2024,
        quarter=3,
        city="13112"
    )
    
    if not data:
        print("⚠️  データが取得できませんでした")
        return
    
    # 全フィールドを抽出
    all_fields = set()
    for item in data:
        all_fields.update(item.keys())
    
    # フィールド情報を表示
    print(f"\n全フィールド数: {len(all_fields)}")
    print("\n" + "=" * 60)
    print(f"{'フィールド名':<30} | {'サンプル値':<30}")
    print("=" * 60)
    
    for field in sorted(all_fields):
        # 最初のデータからサンプル値を取得
        sample_value = data[0].get(field, "N/A")
        if isinstance(sample_value, str) and len(sample_value) > 25:
            sample_value = sample_value[:25] + "..."
        print(f"{field:<30} | {str(sample_value):<30}")
    
    # 欠損率を計算
    print("\n" + "=" * 60)
    print("【欠損率】")
    print("=" * 60)
    
    for field in sorted(all_fields):
        missing_count = sum(1 for item in data if not item.get(field))
        missing_rate = (missing_count / len(data)) * 100
        if missing_rate > 0:
            print(f"{field:<30} : {missing_rate:.1f}% 欠損")

def main():
    """メイン実行関数"""
    print("\n")
    print("=" * 60)
    print("不動産情報ライブラリAPI テストスクリプト")
    print("=" * 60)
    print("\n")
    
    # PostgreSQL接続確認を追加
    if not check_postgresql_connection():
        print("\n❌ PostgreSQLの問題を解決してから再実行してください")
        return
    
    # 出力ディレクトリ作成
    output_dir = project_root / "output" / "test_api_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # PostgreSQLから町丁目リスト取得（確認用）
        print("\n【準備】PostgreSQLから世田谷区の町丁目を取得")
        choume_list = get_setagaya_choume_list()
        print(f"サンプル（最初の10件）: {choume_list[:10]}")
        
        # TEST 1: 世田谷区全体
        test_api_single_area()
        
        # TEST 2: 特定の町丁目
        test_api_specific_choume()
        
        # TEST 3: 複数年度のトレンド
        test_api_multiple_years()
        
        # TEST 4: レスポンス構造分析
        analyze_response_structure()
        
        print("\n" + "=" * 60)
        print("✅ すべてのテストが完了しました")
        print("=" * 60)
        print("\n📁 出力ファイル:")
        print("   - output/test_api_results/setagaya_2024q3.json")
        print("   - output/test_api_results/kamiyoga_6chome_2024q3.json")
        print("   - output/test_api_results/trend_2020_2024.json")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

