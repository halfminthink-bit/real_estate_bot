"""
APIデータのデバッグスクリプト

目的:
1. 世田谷区全体のデータを取得
2. DistrictNameにどんな値が入っているか確認
3. 「上用賀」が含まれているか確認
"""
import os
import sys
import json
from collections import Counter
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.data_aggregator.collectors.transaction_price_collector import TransactionPriceCollector

# 環境変数を読み込み
load_dotenv()


def main():
    print("=" * 60)
    print("APIデータのデバッグ")
    print("=" * 60)
    
    collector = TransactionPriceCollector()
    
    # 世田谷区全体のデータを取得
    print("\n📡 世田谷区全体のデータ取得中...")
    try:
        all_data = collector.get_transaction_data(
            year=2024,
            quarter=3,
            city="13112"
        )
    except Exception as e:
        print(f"❌ データ取得エラー: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"✅ 取得件数: {len(all_data)}件")
    
    if not all_data:
        print("⚠️  データが取得できませんでした")
        return
    
    # DistrictNameの一覧を確認
    print("\n【DistrictNameの一覧】")
    district_names = [item.get('DistrictName', '') for item in all_data]
    district_counter = Counter(district_names)
    
    # 上位20件を表示
    print("\n上位20件:")
    for district, count in district_counter.most_common(20):
        print(f"  {district}: {count}件")
    
    # 「上用賀」を含むデータを探す
    print("\n" + "=" * 60)
    print("【「上用賀」を含むデータ】")
    kamiyoga_data = [
        item for item in all_data
        if '上用賀' in item.get('DistrictName', '')
    ]
    
    if kamiyoga_data:
        print(f"✅ 見つかりました: {len(kamiyoga_data)}件")
        print("\n最初の3件:")
        for i, item in enumerate(kamiyoga_data[:3], 1):
            print(f"\n{i}. DistrictName: {item.get('DistrictName')}")
            print(f"   Type: {item.get('Type')}")
            print(f"   TradePrice: {item.get('TradePrice')}")
            print(f"   BuildingYear: {item.get('BuildingYear')}")
    else:
        print("❌ 見つかりませんでした")
        
        # 似た名前を探す
        print("\n【参考】「用賀」を含むデータ:")
        youga_data = [
            item for item in all_data
            if '用賀' in item.get('DistrictName', '')
        ]
        if youga_data:
            print(f"✅ {len(youga_data)}件")
            print("\n最初の3件:")
            for i, item in enumerate(youga_data[:3], 1):
                print(f"  {i}. DistrictName: {item.get('DistrictName')}")
        else:
            print("❌ 「用賀」も見つかりませんでした")
    
    # さらに詳しく：DistrictNameのパターンを分析
    print("\n" + "=" * 60)
    print("【DistrictNameのパターン分析】")
    print("=" * 60)
    
    # 「丁目」を含むもの
    choume_count = sum(1 for name in district_names if '丁目' in name)
    print(f"「丁目」を含む: {choume_count}件")
    
    # 数字を含むもの
    import re
    number_count = sum(1 for name in district_names if re.search(r'\d', name))
    print(f"数字を含む: {number_count}件")
    
    # サンプルデータを表示（最初の5件のDistrictName）
    print("\n【サンプルDistrictName（最初の5件）】")
    for i, item in enumerate(all_data[:5], 1):
        print(f"  {i}. {item.get('DistrictName', 'N/A')}")
    
    # 出力ディレクトリ作成
    output_dir = project_root / "output" / "debug_api"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # DistrictNameの一覧を保存
    district_names_file = output_dir / "district_names.json"
    with open(district_names_file, 'w', encoding='utf-8') as f:
        json.dump(dict(district_counter), f, ensure_ascii=False, indent=2)
    print(f"\n✅ DistrictName一覧を保存: {district_names_file}")
    
    # 全データの最初の10件を保存
    sample_data_file = output_dir / "sample_data.json"
    with open(sample_data_file, 'w', encoding='utf-8') as f:
        json.dump(all_data[:10], f, ensure_ascii=False, indent=2)
    print(f"✅ サンプルデータを保存: {sample_data_file}")
    
    # 「上用賀」または「用賀」を含むデータがあれば保存
    if kamiyoga_data:
        kamiyoga_file = output_dir / "kamiyoga_data.json"
        with open(kamiyoga_file, 'w', encoding='utf-8') as f:
            json.dump(kamiyoga_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 上用賀データを保存: {kamiyoga_file}")
    elif youga_data:
        youga_file = output_dir / "youga_data.json"
        with open(youga_file, 'w', encoding='utf-8') as f:
            json.dump(youga_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 用賀データを保存: {youga_file}")
    
    print("\n" + "=" * 60)
    print("✅ デバッグ完了")
    print(f"出力先: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

