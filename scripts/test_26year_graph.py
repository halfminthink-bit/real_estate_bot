#!/usr/bin/env python3
"""
26年推移グラフのテスト
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_aggregator.collectors.land_price_collector import LandPriceCollector
from modules.chart_generator.price_graph_generator import PriceGraphGenerator
from core.models import Area

def main():
    print("="*80)
    print("26年推移グラフ テスト")
    print("="*80)
    
    # テスト対象エリア（三軒茶屋1丁目）
    # choume_codeは実際のデータベースから取得する必要がある
    # ここではNoneにして、住所検索で動作確認
    area = Area(
        area_id=2,
        ward='世田谷区',
        choume='三軒茶屋1丁目',
        priority='high',
        choume_code=None  # 住所検索で動作確認
    )
    
    print(f"\n対象エリア: {area.ward}{area.choume}")
    
    # データ取得
    print("\n1. データ取得中...")
    collector = LandPriceCollector()
    data = collector.fetch(area)
    
    if not data:
        print("❌ データ取得失敗")
        return
    
    history = data.get('land_price_history', [])
    print(f"✅ {len(history)}年分のデータを取得")
    
    # 統計表示
    if history:
        print(f"\n【データ概要】")
        print(f"  期間: {history[0]['year']}-{history[-1]['year']}年")
        print(f"  最古: {history[0]['price']:,}円/㎡ ({history[0]['year']}年)")
        print(f"  最新: {history[-1]['price']:,}円/㎡ ({history[-1]['year']}年)")
        
        # 価格帯
        latest = history[-1]
        if 'price_min' in latest and 'price_max' in latest:
            print(f"  価格帯: {latest['price_min']:,}〜{latest['price_max']:,}円/㎡")
            print(f"  地点数: {latest.get('point_count', 1)}地点")
        
        if 'price_change_26y' in data:
            print(f"  26年変動: {data['price_change_26y']:+.1f}%")
        if 'price_change_5y' in data:
            print(f"  5年変動: {data['price_change_5y']:+.1f}%")
        if 'price_change_1y' in data:
            print(f"  1年変動: {data['price_change_1y']:+.1f}%")
    
    # グラフ生成
    print("\n2. グラフ生成中...")
    output_dir = Path(__file__).parent.parent / 'test_output'
    output_dir.mkdir(exist_ok=True)
    
    generator = PriceGraphGenerator(str(output_dir))
    filename = generator.generate_price_graph(history, area.choume)
    
    if filename:
        print(f"✅ グラフ生成成功: {output_dir / filename}")
    else:
        print("❌ グラフ生成失敗")
    
    print("\n" + "="*80)
    print("テスト完了")
    print("="*80)

if __name__ == '__main__':
    main()

