#!/usr/bin/env python3
"""
拡張されたLandPriceCollectorのテスト
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.models import Area
from modules.data_aggregator.collectors.land_price_collector import LandPriceCollector

def main():
    print("=" * 60)
    print("LandPriceCollector 拡張テスト")
    print("=" * 60)
    
    # テスト用のエリア
    test_area = Area(
        area_id=1,
        ward="世田谷区",
        choume="三宿2丁目",
        priority=1,
        status="pending"
    )
    
    # Collector初期化
    collector = LandPriceCollector()
    
    # データ取得
    print(f"\n[テスト対象] {test_area.ward}{test_area.choume}")
    data = collector.fetch(test_area)
    
    if not data:
        print("❌ データ取得失敗")
        return
    
    # 結果表示
    print("\n【取得データ】")
    print(f"✅ 最新地価: {data.get('latest_price', 0):,}円/㎡")
    print(f"✅ 5年変動率: {data.get('price_change_5y', 0):+.2f}%")
    print(f"✅ 1年変動率: {data.get('price_change_1y', 0):+.2f}%")
    print(f"✅ 用途地域: {data.get('land_use', 'なし')}")
    print(f"✅ 建蔽率: {data.get('building_coverage_ratio', 'なし')}%")
    print(f"✅ 容積率: {data.get('floor_area_ratio', 'なし')}%")
    print(f"✅ 前面道路: {data.get('road_direction', 'なし')} {data.get('road_width', 'なし')}m")
    print(f"✅ 地積: {data.get('land_area', 'なし')}㎡")
    if data.get('nearest_station'):
        print(f"✅ 最寄駅: {data.get('nearest_station', 'なし')} ({data.get('station_distance', 'なし')}m)")
    
    print("\n【地価推移】")
    history = data.get('land_price_history', [])
    if history:
        for item in history[-5:]:  # 最新5年分
            change_str = f"({item['change']:+.1f}%)" if item.get('change') is not None else ""
            print(f"  {item['year']}年: {item['price']:,}円/㎡ {change_str}")
    else:
        print("  （データなし）")
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)

if __name__ == "__main__":
    main()

