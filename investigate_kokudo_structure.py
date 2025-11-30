#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
国土数値情報（地価公示データ）2000-2025年 構造調査スクリプト
"""

from pathlib import Path
import json

def investigate_file_structure():
    """全年度のファイル構造を調査"""
    base_path = Path('data/raw/national/kokudo_suuchi')
    
    print("=" * 80)
    print("Phase 1: ファイル構造の調査")
    print("=" * 80)
    
    results = {}
    
    for year in range(2000, 2026):
        year_short = f"{year % 100:02d}"
        year_dir = base_path / f"{year}_13"
        
        if not year_dir.exists():
            continue
        
        print(f"\n{'='*80}")
        print(f"📂 {year}年 ({year_short})")
        print(f"{'='*80}")
        print(f"ディレクトリ: {year_dir}")
        
        # ディレクトリ内のファイルを確認
        files = list(year_dir.iterdir())
        
        # Shapefile関連
        shp_files = [f for f in files if f.suffix == '.shp']
        geojson_files = [f for f in files if f.suffix == '.geojson']
        
        # サブディレクトリを確認
        subdirs = [d for d in files if d.is_dir()]
        
        result = {
            'year': year,
            'directory': str(year_dir),
            'shp_files': [f.name for f in shp_files],
            'geojson_files': [f.name for f in geojson_files],
            'subdirs': [d.name for d in subdirs],
            'pattern': None
        }
        
        # サブディレクトリ内のGeoJSONを優先的に確認
        if subdirs:
            print(f"  📁 サブディレクトリ: {', '.join([d.name for d in subdirs])}")
            for subdir in subdirs:
                subdir_path = year_dir / subdir
                sub_geojson = list(subdir_path.glob('*.geojson'))
                if sub_geojson:
                    print(f"     → GeoJSON: {sub_geojson[0].name}")
                    result['format'] = 'geojson'
                    result['main_file'] = str(sub_geojson[0])
                    result['pattern'] = 'pattern_C'
                    break
        
        # ファイルパターンを特定（サブディレクトリにGeoJSONがない場合）
        if result.get('pattern') is None:
            if shp_files:
                print(f"  ✅ Shapefile: {shp_files[0].name}")
                result['format'] = 'shapefile'
                result['main_file'] = str(shp_files[0])
                
                # パターンを判定
                if '-g_LandPrice' in shp_files[0].name:
                    result['pattern'] = 'pattern_A'  # 2000-2011年
                else:
                    result['pattern'] = 'pattern_B'  # 2012-2017年
                    
            elif geojson_files:
                print(f"  ✅ GeoJSON: {geojson_files[0].name}")
                result['format'] = 'geojson'
                result['main_file'] = str(geojson_files[0])
                result['pattern'] = 'pattern_C'  # 2018-2025年
        
        # パターンが未設定の場合はunknown
        if result.get('pattern') is None:
            result['pattern'] = 'unknown'
        
        results[year] = result
    
    # パターン別に分類
    print("\n" + "=" * 80)
    print("📊 パターン別分類")
    print("=" * 80)
    
    pattern_groups = {}
    for year, result in results.items():
        pattern = result.get('pattern', 'unknown')
        if pattern not in pattern_groups:
            pattern_groups[pattern] = []
        pattern_groups[pattern].append(year)
    
    for pattern in sorted(pattern_groups.keys(), key=lambda x: (x == 'unknown', x)):
        years = pattern_groups[pattern]
        print(f"\n{pattern}: {min(years)}-{max(years)}年 ({len(years)}年分)")
        print(f"  年度: {sorted(years)}")
        if years:
            sample_year = min(years)
            sample_result = results[sample_year]
            print(f"  フォーマット: {sample_result.get('format', 'unknown')}")
            if sample_result.get('main_file'):
                print(f"  ファイル例: {Path(sample_result['main_file']).name}")
    
    return results

if __name__ == '__main__':
    results = investigate_file_structure()
    
    # 結果をJSONに保存
    output_file = Path('kokudo_structure_investigation.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 調査結果を保存: {output_file}")

