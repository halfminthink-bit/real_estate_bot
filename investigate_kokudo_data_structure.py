#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
国土数値情報（地価公示データ）2000-2025年 データ構造調査スクリプト
Phase 2: データ構造の調査
"""

import geopandas as gpd
import json
from pathlib import Path

def get_file_path(year):
    """指定年度のファイルパスを取得"""
    base_path = Path('data/raw/national/kokudo_suuchi')
    year_short = f"{year % 100:02d}"
    year_dir = base_path / f"{year}_13"
    
    if not year_dir.exists():
        return None
    
    # パターンA: 2000-2011年
    if 2000 <= year <= 2011:
        shp_file = year_dir / f"L01-{year_short}_13-g_LandPrice.shp"
        if shp_file.exists():
            return shp_file
    
    # パターンB: 2012-2014, 2016-2017, 2019, 2022年
    if year in [2012, 2013, 2014, 2016, 2017, 2019, 2022]:
        shp_file = year_dir / f"L01-{year_short}_13.shp"
        if shp_file.exists():
            return shp_file
    
    # パターンC: 2015, 2018, 2020-2021, 2023-2025年（サブディレクトリ内）
    if year in [2015, 2018, 2020, 2021, 2023, 2024, 2025]:
        subdir = year_dir / f"L01-{year_short}_13_GML"
        if subdir.exists():
            # GeoJSONを優先
            geojson_file = subdir / f"L01-{year_short}_13.geojson"
            if geojson_file.exists():
                return geojson_file
            # Shapefile
            shp_file = subdir / f"L01-{year_short}_13.shp"
            if shp_file.exists():
                return shp_file
    
    # 2019年は直接GeoJSONがある可能性
    if year == 2019:
        geojson_file = year_dir / f"L01-{year_short}_13.geojson"
        if geojson_file.exists():
            return geojson_file
    
    return None

def investigate_year(year):
    """指定年度のデータ構造を調査"""
    filepath = get_file_path(year)
    
    if not filepath or not filepath.exists():
        print(f"\n{'='*70}")
        print(f"❌ {year}年: ファイルが見つかりません")
        return None
    
    print(f"\n{'='*70}")
    print(f"📂 {year}年: {filepath.name}")
    print('='*70)
    
    try:
        # ShapefileまたはGeoJSONを読み込み
        if filepath.suffix == '.shp':
            gdf = gpd.read_file(filepath, encoding='shift-jis')
        else:
            gdf = gpd.read_file(filepath, encoding='utf-8')
        
        print(f"\n✅ 読み込み成功")
        print(f"   総件数: {len(gdf):,}件")
        print(f"   カラム数: {len(gdf.columns)}個")
        
        # カラム一覧（最初の30個）
        print(f"\n📋 カラム一覧（最初の30個）:")
        for i, col in enumerate(gdf.columns[:30], 1):
            sample_value = gdf[col].iloc[0] if len(gdf) > 0 else None
            if sample_value is not None:
                val_str = str(sample_value)[:50]
            else:
                val_str = 'None'
            print(f"   {i:2d}. {col:20s} : {val_str}")
        
        if len(gdf.columns) > 30:
            print(f"   ... (残り{len(gdf.columns) - 30}個のカラム)")
        
        # 世田谷区のデータを探す
        setagaya_cols = []
        for col in gdf.columns:
            try:
                # 最初の1000件をチェック
                sample_values = gdf[col].head(1000).astype(str)
                if any('13112' in str(val) for val in sample_values):
                    setagaya_cols.append(col)
            except:
                pass
        
        if setagaya_cols:
            print(f"\n🔍 市区町村コード候補: {setagaya_cols}")
            
            # 世田谷区のデータを抽出
            code_col = setagaya_cols[0]
            setagaya = gdf[gdf[code_col].astype(str) == '13112']
            print(f"   世田谷区: {len(setagaya):,}件")
            
            if len(setagaya) > 0:
                # 住所・価格のカラムを特定
                print(f"\n📍 世田谷区サンプル（1件）:")
                sample = setagaya.iloc[0]
                for col in gdf.columns[:40]:
                    val = str(sample[col])
                    if '東京' in val or '世田谷' in val or (len(val) > 15 and not val.startswith('0')):
                        print(f"   {col:20s}: {val[:70]}")
        
        # 重要フィールドの特定
        print(f"\n🎯 重要フィールドの特定:")
        important_fields = {}
        
        # 市区町村コード
        for col in gdf.columns:
            try:
                sample_values = gdf[col].head(100).astype(str)
                if any('13112' in str(val) for val in sample_values):
                    important_fields['city_code'] = col
                    break
            except:
                pass
        
        # 住所（東京都を含む長い文字列）
        for col in gdf.columns:
            try:
                val = str(gdf[col].iloc[0] if len(gdf) > 0 else '')
                if '東京都' in val and len(val) > 10:
                    important_fields['address'] = col
                    break
            except:
                pass
        
        # 価格（大きな数値）
        for col in gdf.columns:
            try:
                if gdf[col].dtype in ['int64', 'float64']:
                    val = gdf[col].iloc[0] if len(gdf) > 0 else 0
                    if 10000 < val < 10000000:  # 価格の範囲（円/㎡）
                        important_fields['price'] = col
                        break
            except:
                pass
        
        print(f"   市区町村コード: {important_fields.get('city_code', '不明')}")
        print(f"   住所:          {important_fields.get('address', '不明')}")
        print(f"   価格:          {important_fields.get('price', '不明')}")
        
        return {
            'year': year,
            'total_count': len(gdf),
            'column_count': len(gdf.columns),
            'setagaya_count': len(setagaya) if setagaya_cols else 0,
            'important_fields': important_fields,
            'columns': list(gdf.columns)
        }
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    print("=" * 80)
    print("Phase 2: データ構造の調査")
    print("=" * 80)
    
    # 代表的な年度を調査
    years_to_check = [2000, 2005, 2010, 2012, 2015, 2016, 2017, 2018, 2020, 2021, 2022, 2025]
    
    results = []
    for year in years_to_check:
        result = investigate_year(year)
        if result:
            results.append(result)
    
    # 結果をJSONに保存
    output_file = Path('kokudo_data_structure_investigation.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 調査結果を保存: {output_file}")
    
    # フィールドマッピングの要約
    print("\n" + "=" * 80)
    print("📊 フィールドマッピング要約")
    print("=" * 80)
    
    for result in results:
        year = result['year']
        fields = result['important_fields']
        print(f"\n{year}年:")
        print(f"  市区町村コード: {fields.get('city_code', '不明')}")
        print(f"  住所:          {fields.get('address', '不明')}")
        print(f"  価格:          {fields.get('price', '不明')}")
        print(f"  カラム数:      {result['column_count']}個")
        print(f"  世田谷区:      {result['setagaya_count']}件")

