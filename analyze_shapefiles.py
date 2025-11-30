#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shapefile構造分析スクリプト
アップロードされた6つのShapefileの構造を分析
"""

import geopandas as gpd
import pandas as pd
import json
from pathlib import Path

# 分析対象のShapefile
shapefiles = {
    '2000': 'data/raw/national/kokudo_suuchi/2000_13/L01-00_13-g_LandPrice.shp',
    '2001': 'data/raw/national/kokudo_suuchi/2001_13/L01-01_13-g_LandPrice.shp',
    '2007': 'data/raw/national/kokudo_suuchi/2007_13/L01-07_13-g_LandPrice.shp',
    '2010': 'data/raw/national/kokudo_suuchi/2010_13/L01-10_13-g_LandPrice.shp',
    '2013': 'data/raw/national/kokudo_suuchi/2013_13/L01-13_13.shp',
    '2017': 'data/raw/national/kokudo_suuchi/2017_13/L01-17_13.shp'
}

def analyze_shapefile(filepath, year):
    """Shapefileを分析"""
    print(f"\n{'='*70}")
    print(f"【{year}年】 {Path(filepath).name}")
    print('='*70)
    
    try:
        gdf = gpd.read_file(filepath)
        
        # 基本情報
        print(f"\n総件数: {len(gdf)}件")
        print(f"列数: {len(gdf.columns)}個")
        
        # 列名表示（5個ずつ）
        print(f"\n【列名一覧】")
        cols = gdf.columns.tolist()
        for i in range(0, len(cols), 5):
            print(f"  {', '.join(cols[i:i+5])}")
        
        # 市区町村コードの実際の値を確認
        print(f"\n【市区町村コードの確認】")
        if 'L01_001' in gdf.columns:
            print(f"  L01_001のユニーク値（最初の10個）: {gdf['L01_001'].unique()[:10].tolist()}")
            print(f"  L01_001のデータ型: {gdf['L01_001'].dtype}")
        if 'L01_017' in gdf.columns:
            print(f"  L01_017のユニーク値（最初の10個）: {gdf['L01_017'].unique()[:10].tolist()}")
            print(f"  L01_017のデータ型: {gdf['L01_017'].dtype}")
        
        # 世田谷区フィルタ（複数パターン試行）
        setagaya = pd.DataFrame()
        
        # パターン1: L01_001 == 13112 (数値)
        if 'L01_001' in gdf.columns:
            setagaya = gdf[gdf['L01_001'] == 13112]
            if len(setagaya) > 0:
                print(f"\n✅ L01_001 == 13112 でマッチ")
        
        # パターン2: L01_017 == '13112' (文字列)
        if len(setagaya) == 0 and 'L01_017' in gdf.columns:
            setagaya = gdf[gdf['L01_017'] == '13112']
            if len(setagaya) > 0:
                print(f"\n✅ L01_017 == '13112' でマッチ")
        
        # パターン3: L01_017の最初の5文字が '13112'
        if len(setagaya) == 0 and 'L01_017' in gdf.columns:
            setagaya = gdf[gdf['L01_017'].astype(str).str.startswith('13112')]
            if len(setagaya) > 0:
                print(f"\n✅ L01_017が '13112' で始まる")
        
        # パターン4: 住所に「世田谷」が含まれる
        if len(setagaya) == 0:
            if 'L01_019' in gdf.columns:
                setagaya = gdf[gdf['L01_019'].astype(str).str.contains('世田谷', na=False)]
                if len(setagaya) > 0:
                    print(f"\n✅ L01_019に「世田谷」が含まれる")
            elif 'L01_023' in gdf.columns:
                setagaya = gdf[gdf['L01_023'].astype(str).str.contains('世田谷', na=False)]
                if len(setagaya) > 0:
                    print(f"\n✅ L01_023に「世田谷」が含まれる")
        
        if len(setagaya) == 0:
            print(f"\n❌ 世田谷区のデータが見つかりません")
        
        print(f"\n世田谷区フィルタ後: {len(setagaya)}件")
        
        if len(setagaya) > 0:
            # サンプルデータ表示
            sample = setagaya.iloc[0]
            
            print(f"\n【サンプルデータ（1件目）】")
            important_fields = {
                'L01_001': '市区町村コード（数値）',
                'L01_005': '調査年',
                'L01_006': '地価（円/㎡）',
                'L01_007': '変動率',
                'L01_017': '市区町村コード（文字列）',
                'L01_019': '住所（候補1）',
                'L01_020': '地積（候補1）',
                'L01_023': '住所（候補2）',
                'L01_024': '地積（候補2）',
                'L01_037': '前面道路方位',
                'L01_038': '前面道路幅員',
                'L01_045': '最寄駅',
                'L01_046': '駅距離',
                'L01_047': '用途地域',
                'L01_052': '建蔽率',
                'L01_053': '容積率'
            }
            
            for field, desc in important_fields.items():
                value = sample.get(field, 'フィールドなし')
                print(f"  {field} ({desc}): {value}")
            
            # データ存在率
            print(f"\n【データ存在率】")
            for field, desc in important_fields.items():
                if field in gdf.columns:
                    count = gdf[field].notna().sum()
                    rate = (count / len(gdf)) * 100
                    print(f"  {field} ({desc}): {count}/{len(gdf)}件 ({rate:.1f}%)")
                else:
                    print(f"  {field} ({desc}): ❌ フィールドなし")
        
        # 結果を返す
        return {
            'year': year,
            'total_count': len(gdf),
            'setagaya_count': len(setagaya),
            'columns': cols,
            'has_price': 'L01_006' in gdf.columns,
            'has_address_019': 'L01_019' in gdf.columns,
            'has_address_023': 'L01_023' in gdf.columns,
            'has_land_use': 'L01_047' in gdf.columns,
            'has_coverage': 'L01_052' in gdf.columns,
            'has_floor_area': 'L01_053' in gdf.columns
        }
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return {'year': year, 'error': str(e)}

def main():
    """メイン処理"""
    print("="*70)
    print("Shapefile構造分析")
    print("="*70)
    
    results = []
    
    for year, filepath in sorted(shapefiles.items()):
        if not Path(filepath).exists():
            print(f"\n⚠️ {year}年: ファイルが見つかりません")
            print(f"   {filepath}")
            continue
        
        result = analyze_shapefile(filepath, year)
        results.append(result)
    
    # サマリー表示
    print("\n\n" + "="*70)
    print("【分析サマリー】")
    print("="*70)
    
    print("\n年度 | 総件数 | 世田谷区 | 地価 | 住所 | 用途 | 建蔽率 | 容積率")
    print("-" * 70)
    
    for result in sorted(results, key=lambda x: x['year']):
        if 'error' not in result:
            year = result['year']
            total = result['total_count']
            setagaya = result['setagaya_count']
            price = '✅' if result['has_price'] else '❌'
            address = '✅' if (result['has_address_019'] or result['has_address_023']) else '❌'
            land_use = '✅' if result['has_land_use'] else '❌'
            coverage = '✅' if result['has_coverage'] else '❌'
            floor = '✅' if result['has_floor_area'] else '❌'
            
            print(f"{year} | {total:6d} | {setagaya:8d} | {price:^4} | {address:^4} | {land_use:^4} | {coverage:^6} | {floor:^6}")
        else:
            print(f"{result['year']} | エラー")
    
    # 結論
    print("\n【結論】")
    success_count = len([r for r in results if 'error' not in r])
    has_price_count = len([r for r in results if r.get('has_price', False)])
    
    if has_price_count == success_count and success_count > 0:
        print("✅ すべてのShapefileに地価データあり")
        print("   → 東京都オープンデータ不要、直接INSERTできます")
    elif has_price_count > 0:
        print(f"⚠️ {has_price_count}/{success_count}個のShapefileに地価データあり")
        print("   → 部分的に利用可能")
    else:
        print("❌ 地価データがありません")
        print("   → 東京都オープンデータが必要")
    
    # JSON出力
    output_file = Path('shapefile_analysis_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 分析結果を保存: {output_file}")
    print("="*70)

if __name__ == '__main__':
    main()