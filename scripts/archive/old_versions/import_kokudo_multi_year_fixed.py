#!/usr/bin/env python3
"""
国土数値情報（2018-2025年版）インポート修正版

各年度のGeoJSONフィールド構造に対応
"""

import json
import psycopg2
import yaml
from pathlib import Path
from dotenv import load_dotenv
import os
import re
import sys

# 環境変数を読み込み
load_dotenv()

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 用途地域コードの変換マップ
LAND_USE_MAP = {
    "1低専": "1低専",
    "2低専": "2低専",
    "1中専": "1中専",
    "2中専": "2中専",
    "1住居": "1住居",
    "2住居": "2住居",
    "準住居": "準住居",
    "近商": "近商",
    "商業": "商業",
    "準工": "準工",
    "工業": "工業",
    "工専": "工専",
}

# 年度別フィールドマッピング
FIELD_MAPPING = {
    # 2018-2021年は同じフィールド構造
    2018: {
        'city_code': 'L01_021',      # 市区町村コード
        'city_name': 'L01_022',      # 市区町村名
        'address': 'L01_023',        # 住所
        'land_area': 'L01_024',      # 地積
        'road_direction': 'L01_037', # 前面道路方位
        'road_width': 'L01_038',     # 前面道路幅員
        'nearest_station': 'L01_045',# 最寄駅
        'station_distance': 'L01_046',# 駅距離
        'land_use': 'L01_047',       # 用途地域
        'building_coverage': 'L01_052', # 建蔽率
        'floor_area_ratio': 'L01_053',  # 容積率
    },
    2019: {
        'city_code': 'L01_021',      # 市区町村コード
        'city_name': 'L01_022',      # 市区町村名
        'address': 'L01_023',        # 住所
        'land_area': 'L01_024',      # 地積
        'road_direction': 'L01_037', # 前面道路方位
        'road_width': 'L01_038',     # 前面道路幅員
        'nearest_station': 'L01_045',# 最寄駅
        'station_distance': 'L01_046',# 駅距離
        'land_use': 'L01_047',       # 用途地域
        'building_coverage': 'L01_052', # 建蔽率
        'floor_area_ratio': 'L01_053',  # 容積率
    },
    2020: {
        'city_code': 'L01_021',      # 市区町村コード
        'city_name': 'L01_022',      # 市区町村名
        'address': 'L01_023',        # 住所
        'land_area': 'L01_024',      # 地積
        'road_direction': 'L01_037', # 前面道路方位
        'road_width': 'L01_038',     # 前面道路幅員
        'nearest_station': 'L01_045',# 最寄駅
        'station_distance': 'L01_046',# 駅距離
        'land_use': 'L01_047',       # 用途地域
        'building_coverage': 'L01_052', # 建蔽率
        'floor_area_ratio': 'L01_053',  # 容積率
    },
    2021: {
        'city_code': 'L01_021',      # 市区町村コード
        'city_name': 'L01_022',      # 市区町村名
        'address': 'L01_023',        # 住所
        'land_area': 'L01_024',      # 地積
        'road_direction': 'L01_037', # 前面道路方位
        'road_width': 'L01_038',     # 前面道路幅員
        'nearest_station': 'L01_045',# 最寄駅
        'station_distance': 'L01_046',# 駅距離
        'land_use': 'L01_047',       # 用途地域
        'building_coverage': 'L01_052', # 建蔽率
        'floor_area_ratio': 'L01_053',  # 容積率
    },
    2022: {
        'city_code': 'L01_022',      # 市区町村コード
        'city_name': 'L01_023',      # 市区町村名
        'address': 'L01_024',        # 住所
        'land_area': 'L01_026',      # 地積
        'road_direction': 'L01_040', # 前面道路方位
        'road_width': 'L01_041',     # 前面道路幅員
        'nearest_station': 'L01_048',# 最寄駅
        'station_distance': 'L01_049',# 駅距離
        'land_use': 'L01_050',       # 用途地域
        'building_coverage': 'L01_056', # 建蔽率
        'floor_area_ratio': 'L01_057',  # 容積率
    },
    2023: {
        'city_code': 'L01_022',      # 市区町村コード
        'city_name': 'L01_023',      # 市区町村名
        'address': 'L01_024',        # 住所
        'land_area': 'L01_026',      # 地積
        'road_direction': 'L01_040', # 前面道路方位
        'road_width': 'L01_041',     # 前面道路幅員
        'nearest_station': 'L01_048',# 最寄駅
        'station_distance': 'L01_049',# 駅距離
        'land_use': 'L01_050',       # 用途地域
        'building_coverage': 'L01_056', # 建蔽率
        'floor_area_ratio': 'L01_057',  # 容積率
    },
    # 2024年版と2025年版はフィールド番号がずれている
    2024: {
        'city_code': 'L01_001',      # 市区町村コード
        'city_name': 'L01_024',      # 市区町村名
        'address': 'L01_025',        # 住所（ずれている）
        'land_area': 'L01_027',      # 地積
        'road_direction': 'L01_041', # 前面道路方位
        'road_width': 'L01_042',     # 前面道路幅員
        'nearest_station': 'L01_048',# 最寄駅
        'station_distance': 'L01_050',# 駅距離
        'land_use': 'L01_051',       # 用途地域
        'building_coverage': 'L01_057', # 建蔽率
        'floor_area_ratio': 'L01_058',  # 容積率
    },
    2025: {
        'city_code': 'L01_001',
        'city_name': 'L01_024',
        'address': 'L01_025',
        'land_area': 'L01_027',
        'road_direction': 'L01_041',
        'road_width': 'L01_042',
        'nearest_station': 'L01_048',
        'station_distance': 'L01_050',
        'land_use': 'L01_051',
        'building_coverage': 'L01_057',
        'floor_area_ratio': 'L01_058',
    },
}


def load_db_config():
    """データベース設定を読み込み"""
    config_path = project_root / 'config' / 'database.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return {
        'host': os.getenv('DB_HOST', config['postgresql'].get('host', 'localhost')),
        'port': int(os.getenv('DB_PORT', config['postgresql'].get('port', 5432))),
        'database': os.getenv('DB_NAME', config['postgresql'].get('database', 'real_estate_dev')),
        'user': os.getenv('DB_USER', config['postgresql'].get('user', 'postgres')),
        'password': os.getenv('DB_PASSWORD', config['postgresql'].get('password', 'postgres'))
    }


def normalize_address(address):
    """住所を正規化"""
    if not address:
        return ""
    
    # 全角数字を半角に
    address = address.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    
    # スペース削除
    address = address.replace(' ', '').replace('　', '')
    
    # 「東京都」を削除
    address = address.replace('東京都', '')
    
    # 「世田谷区」を削除
    if '世田谷区' in address:
        address = address.split('世田谷区')[1]
    
    # 全角ハイフン・マイナスを半角ハイフンに統一
    # 2018-2021年のGeoJSONは「－」（全角ハイフン）や「−」（全角マイナス）を使用
    address = address.replace('－', '-').replace('−', '-').replace('‐', '-')
    
    # ハイフン形式を丁目番形式に変換
    # 例: 「喜多見9-19-6」→「喜多見9丁目19番6」
    parts = re.split(r'[-]', address)
    if len(parts) == 3:
        # 3分割された場合：町名-丁目-番地
        address = f"{parts[0]}丁目{parts[1]}番{parts[2]}"
    elif len(parts) == 2:
        # 2分割された場合：町名-番地
        address = f"{parts[0]}番{parts[1]}"
    
    # 「外」を削除（マッチングのため）
    address = address.replace('外', '')
    
    return address.strip()


def extract_from_geojson(geojson_path, year):
    """GeoJSONから世田谷区のデータを抽出"""
    print(f"\n📂 {geojson_path.name} を読み込み中...")
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    
    features = geojson_data.get('features', [])
    print(f"   総件数: {len(features)}件")
    
    # その年度のフィールドマッピングを取得
    field_map = FIELD_MAPPING.get(year)
    if not field_map:
        print(f"   ❌ {year}年のフィールドマッピングが定義されていません")
        return {}
    
    result = {}
    setagaya_count = 0
    
    for feature in features:
        props = feature['properties']
        
        # 市区町村コードで世田谷区をフィルタ（13112）
        city_code = props.get(field_map['city_code'], '')
        if str(city_code) != '13112':
            continue
        
        setagaya_count += 1
        
        # 住所を取得
        address = props.get(field_map['address'], '')
        if not address or address == 'false' or address == '_':
            continue
        
        # 住所を正規化
        normalized_addr = normalize_address(address)
        
        # データを抽出
        def get_value(key, default=None):
            value = props.get(field_map[key], default)
            # "false"や"_"は無効値として扱う
            if value in ['false', '_', '0.0', 0, '']:
                return None
            return value
        
        # 用途地域を変換
        land_use_raw = get_value('land_use')
        land_use = LAND_USE_MAP.get(land_use_raw) if land_use_raw else None
        
        # 数値変換
        try:
            land_area = int(get_value('land_area', 0)) if get_value('land_area') else None
        except (ValueError, TypeError):
            land_area = None
        
        try:
            building_coverage = int(get_value('building_coverage', 0)) if get_value('building_coverage') else None
        except (ValueError, TypeError):
            building_coverage = None
        
        try:
            floor_area_ratio = int(get_value('floor_area_ratio', 0)) if get_value('floor_area_ratio') else None
        except (ValueError, TypeError):
            floor_area_ratio = None
        
        try:
            road_width = float(get_value('road_width', 0)) if get_value('road_width') else None
            if road_width == 0.0:
                road_width = None
        except (ValueError, TypeError):
            road_width = None
        
        try:
            station_distance = int(get_value('station_distance', 0)) if get_value('station_distance') else None
        except (ValueError, TypeError):
            station_distance = None
        
        data = {
            'land_use': land_use,
            'building_coverage_ratio': building_coverage,
            'floor_area_ratio': floor_area_ratio,
            'road_direction': get_value('road_direction'),
            'road_width': road_width,
            'land_area': land_area,
            'nearest_station': get_value('nearest_station'),
            'station_distance': station_distance,
            'original_address': address
        }
        
        result[normalized_addr] = data
    
    print(f"   世田谷区: {setagaya_count}件")
    print(f"   抽出完了: {len(result)}件（世田谷区のみ）")
    
    return result


def import_year_data(conn, year, geojson_data):
    """指定年度のデータをインポート"""
    print(f"\n🔄 {year}年度のデータをインポート中...")
    
    cur = conn.cursor()
    
    # 対象年度のland_pricesレコードを取得
    cur.execute("""
        SELECT id, original_address
        FROM land_prices
        WHERE survey_year = %s
          AND original_address IS NOT NULL
    """, (year,))
    
    records = cur.fetchall()
    print(f"   対象レコード: {len(records)}件")
    
    if len(records) == 0:
        print(f"   ⚠️  {year}年度のレコードが見つかりません")
        cur.close()
        return 0
    
    updated_count = 0
    
    for record_id, db_address in records:
        # 住所を正規化
        normalized_db_addr = normalize_address(db_address)
        
        # GeoJSONデータから検索（完全一致）
        matched = False
        for geojson_addr, data in geojson_data.items():
            # 部分一致で検索
            if geojson_addr in normalized_db_addr or normalized_db_addr in geojson_addr:
                matched = True
                
                # データを更新
                cur.execute("""
                    UPDATE land_prices
                    SET 
                        land_use = %s,
                        building_coverage_ratio = %s,
                        floor_area_ratio = %s,
                        road_direction = %s,
                        road_width = %s,
                        land_area = %s,
                        nearest_station = %s,
                        station_distance = %s
                    WHERE id = %s
                """, (
                    data['land_use'],
                    data['building_coverage_ratio'],
                    data['floor_area_ratio'],
                    data['road_direction'],
                    data['road_width'],
                    data['land_area'],
                    data['nearest_station'],
                    data['station_distance'],
                    record_id
                ))
                
                updated_count += 1
                break
    
    conn.commit()
    
    print(f"   ✅ {updated_count}件を更新しました")
    
    if updated_count < len(records):
        print(f"   ⚠️  {len(records) - updated_count}件がマッチしませんでした")
        
        # マッチしなかった住所を表示（最大5件）
        cur.execute("""
            SELECT DISTINCT original_address
            FROM land_prices
            WHERE survey_year = %s
              AND land_use IS NULL
              AND original_address IS NOT NULL
            LIMIT 5
        """, (year,))
        
        unmatched = cur.fetchall()
        if unmatched:
            print("\n   【マッチしなかった住所の例】")
            for addr in unmatched:
                print(f"      - {addr[0]}")
    
    cur.close()
    return updated_count


def verify_import():
    """インポート結果を確認"""
    print("\n" + "=" * 60)
    print("📊 インポート結果の確認")
    print("=" * 60)
    
    db_config = load_db_config()
    
    try:
        conn = psycopg2.connect(**db_config)
    except Exception as e:
        print(f"❌ PostgreSQL接続エラー: {e}")
        return
    
    cur = conn.cursor()
    
    # 年度別の統計
    cur.execute("""
        SELECT 
            survey_year,
            COUNT(*) as 総件数,
            COUNT(land_use) as 用途地域あり,
            COUNT(building_coverage_ratio) as 建蔽率あり,
            COUNT(floor_area_ratio) as 容積率あり,
            ROUND(COUNT(land_use) * 100.0 / NULLIF(COUNT(*), 0), 1) as 取得率
        FROM land_prices
        GROUP BY survey_year
        ORDER BY survey_year DESC
    """)
    
    print("\n【年度別データ取得状況】")
    print("年度 | 総件数 | 用途地域 | 建蔽率 | 容積率 | 取得率")
    print("-" * 65)
    
    for row in cur.fetchall():
        print(f"{row[0]} |  {row[1]:3}件 |  {row[2]:3}件 | {row[3]:3}件 | {row[4]:3}件 | {row[5]:5.1f}%")
    
    # 三軒茶屋2丁目のサンプル確認
    cur.execute("""
        SELECT 
            survey_year,
            official_price,
            land_use,
            building_coverage_ratio,
            floor_area_ratio
        FROM land_prices
        WHERE TRANSLATE(original_address, '０１２３４５６７８９', '0123456789') LIKE '%三軒茶屋2%'
           OR TRANSLATE(original_address, '０１２３４５６７８９', '0123456789') LIKE '%三軒茶屋２%'
        ORDER BY survey_year DESC
    """)
    
    print("\n【サンプル: 三軒茶屋2丁目】")
    print("年度 | 地価        | 用途地域 | 建蔽率 | 容積率")
    print("-" * 55)
    
    for row in cur.fetchall():
        year = row[0]
        price = f"{row[1]:,}" if row[1] else "なし"
        land_use = row[2] if row[2] else "❌ NULL"
        coverage = f"{row[3]}%" if row[3] else "❌ NULL"
        floor = f"{row[4]}%" if row[4] else "❌ NULL"
        
        print(f"{year} | {price:11} | {land_use:8} | {coverage:6} | {floor:6}")
    
    cur.close()
    conn.close()


def main():
    """メイン処理"""
    print("=" * 60)
    print("国土数値情報（2018-2025年版）インポート修正版")
    print("=" * 60)
    
    # GeoJSONファイルのパス
    base_path = project_root / "data" / "raw" / "national" / "kokudo_suuchi"
    
    geojson_files = {
        2018: base_path / "2018_13" / "L01-18_13_GML" / "L01-18_13.geojson",
        2019: base_path / "2019_13" / "L01-19_13.geojson",
        2020: base_path / "2020_13" / "L01-20_13_GML" / "L01-20_13.geojson",
        2021: base_path / "2021_13" / "L01-21_13_GML" / "L01-21_13.geojson",
        2022: base_path / "2022_13" / "L01-22_13.geojson",
        2023: base_path / "2023_13" / "L01-23_13_GML" / "L01-23_13.geojson",
        2024: base_path / "2024_13" / "L01-24_13_GML" / "L01-24_13.geojson",
        2025: base_path / "2025_13" / "L01-25_13_GML" / "L01-25_13.geojson",
    }
    
    # ファイル存在確認
    print("\n【ファイル存在確認】")
    for year, path in geojson_files.items():
        if path.exists():
            print(f"✅ {year}年版: {path.name}")
        else:
            print(f"❌ {year}年版: 見つかりません ({path})")
    
    # PostgreSQL接続
    db_config = load_db_config()
    try:
        conn = psycopg2.connect(**db_config)
        print("\n✅ PostgreSQLに接続しました")
    except Exception as e:
        print(f"\n❌ PostgreSQL接続エラー: {e}")
        return
    
    # 各年度のデータをインポート
    total_updated = 0
    
    for year in [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]:
        geojson_path = geojson_files[year]
        
        if not geojson_path.exists():
            print(f"\n⚠️  {year}年版GeoJSONが見つかりません。スキップします。")
            continue
        
        # GeoJSONからデータ抽出
        geojson_data = extract_from_geojson(geojson_path, year)
        
        if len(geojson_data) == 0:
            print(f"   ⚠️  {year}年版のデータが抽出できませんでした。スキップします。")
            continue
        
        # インポート実行
        updated = import_year_data(conn, year, geojson_data)
        total_updated += updated
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ 合計 {total_updated}件のレコードを更新しました")
    print("=" * 60)
    
    # 結果確認
    verify_import()
    
    print("\n" + "=" * 60)
    print("✅ すべての処理が完了しました")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

