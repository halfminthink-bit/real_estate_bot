#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国土数値情報（地価公示データ）テストインポートスクリプト
Step 1: 3年分（2000年、2016年、2020年）でテスト
"""

import geopandas as gpd
import psycopg2
import yaml
from pathlib import Path
from dotenv import load_dotenv
import os
import sys
import re
from datetime import date

# 環境変数を読み込み
load_dotenv()

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


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
    address = address.replace('－', '-').replace('−', '-').replace('‐', '-')
    
    # ハイフン形式を丁目番形式に変換
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


def create_table(conn):
    """テーブルを作成"""
    cur = conn.cursor()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS land_prices_kokudo (
        id SERIAL PRIMARY KEY,
        choume_code VARCHAR(11),
        survey_year INTEGER NOT NULL,
        official_price INTEGER,  -- NULL許可（2020年以降は価格データなし）
        data_source VARCHAR(50) NOT NULL DEFAULT '地価公示',
        original_address TEXT,
        land_area INTEGER,
        land_use VARCHAR(50),
        building_coverage_ratio INTEGER,
        floor_area_ratio INTEGER,
        road_direction VARCHAR(10),
        road_width NUMERIC(5,1),
        nearest_station VARCHAR(100),
        station_distance INTEGER,
        latitude NUMERIC(10,7),
        longitude NUMERIC(11,7),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(survey_year, original_address)
    );
    
    CREATE INDEX IF NOT EXISTS idx_land_prices_kokudo_year ON land_prices_kokudo(survey_year);
    CREATE INDEX IF NOT EXISTS idx_land_prices_kokudo_choume ON land_prices_kokudo(choume_code);
    """
    
    cur.execute(create_table_sql)
    conn.commit()
    cur.close()
    print("✅ テーブル作成完了: land_prices_kokudo")


def load_shapefile_data(filepath, year, field_mapping):
    """ShapefileまたはGeoJSONを読み込んで世田谷区のデータを抽出"""
    print(f"  📂 ファイル読み込み: {filepath.name}")
    
    # ファイル形式に応じて読み込み
    if filepath.suffix == '.shp':
        gdf = gpd.read_file(filepath, encoding='shift-jis')
    else:
        gdf = gpd.read_file(filepath, encoding='utf-8')
    
    print(f"    総件数: {len(gdf):,}件")
    
    # 世田谷区をフィルタ
    city_code_field = field_mapping['city_code']
    setagaya = gdf[gdf[city_code_field].astype(str) == '13112']
    print(f"    世田谷区: {len(setagaya):,}件")
    
    # データ変換
    records = []
    for idx, row in setagaya.iterrows():
        try:
            # 住所を取得
            address_raw = row.get(field_mapping['address'], '')
            if pd.isna(address_raw) or address_raw == '':
                continue
            
            # 住所を正規化
            normalized_address = normalize_address(str(address_raw))
            
            # 価格を取得
            price = None
            if 'price' in field_mapping:
                price_raw = row.get(field_mapping['price'])
                # GeoJSONは全フィールドが文字列なので、無効値をチェック
                if pd.notna(price_raw) and str(price_raw) not in ['', '_', 'false', 'None']:
                    try:
                        price = int(float(price_raw))
                        # 価格の単位確認: もし小さすぎる場合は×100
                        # 世田谷区の平均地価は50-60万円/㎡程度
                        if price < 10000:  # 1万円/㎡未満は異常（単位が100円単位の可能性）
                            price = price * 100
                    except (ValueError, TypeError):
                        price = None
            
            # 地積を取得
            land_area = None
            if 'land_area' in field_mapping:
                land_area_raw = row.get(field_mapping['land_area'])
                if pd.notna(land_area_raw):
                    try:
                        land_area = int(float(land_area_raw))
                    except (ValueError, TypeError):
                        land_area = None
            
            # ジオメトリから座標を取得
            latitude = None
            longitude = None
            if hasattr(row, 'geometry') and row.geometry is not None:
                try:
                    if row.geometry.geom_type == 'Point':
                        longitude, latitude = row.geometry.x, row.geometry.y
                    else:
                        # Polygon等の場合は重心を取得
                        centroid = row.geometry.centroid
                        longitude, latitude = centroid.x, centroid.y
                except:
                    pass
            
            record = {
                'survey_year': year,
                'original_address': normalized_address,
                'official_price': price,
                'land_area': land_area,
                'data_source': '地価公示',
                'latitude': latitude,
                'longitude': longitude,
                'created_at': date.today()
            }
            
            # 2020年以降の追加フィールド
            if year >= 2020:
                if 'road_direction' in field_mapping:
                    val = row.get(field_mapping['road_direction'])
                    record['road_direction'] = str(val) if pd.notna(val) and val != '_' else None
                
                if 'road_width' in field_mapping:
                    val = row.get(field_mapping['road_width'])
                    if pd.notna(val) and val != '_' and val != 0:
                        try:
                            record['road_width'] = float(val)
                        except:
                            record['road_width'] = None
                    else:
                        record['road_width'] = None
                
                if 'nearest_station' in field_mapping:
                    val = row.get(field_mapping['nearest_station'])
                    record['nearest_station'] = str(val) if pd.notna(val) and val != '_' else None
                
                if 'station_distance' in field_mapping:
                    val = row.get(field_mapping['station_distance'])
                    if pd.notna(val) and val != '_' and val != 0:
                        try:
                            record['station_distance'] = int(float(val))
                        except:
                            record['station_distance'] = None
                    else:
                        record['station_distance'] = None
                
                if 'land_use' in field_mapping:
                    val = row.get(field_mapping['land_use'])
                    record['land_use'] = str(val) if pd.notna(val) and val != '_' else None
                
                if 'building_coverage' in field_mapping:
                    val = row.get(field_mapping['building_coverage'])
                    if pd.notna(val) and val != '_' and val != 0:
                        try:
                            record['building_coverage_ratio'] = int(float(val))
                        except:
                            record['building_coverage_ratio'] = None
                    else:
                        record['building_coverage_ratio'] = None
                
                if 'floor_area_ratio' in field_mapping:
                    val = row.get(field_mapping['floor_area_ratio'])
                    if pd.notna(val) and val != '_' and val != 0:
                        try:
                            record['floor_area_ratio'] = int(float(val))
                        except:
                            record['floor_area_ratio'] = None
                    else:
                        record['floor_area_ratio'] = None
            
            records.append(record)
            
        except Exception as e:
            print(f"    ⚠️  行 {idx} の処理エラー: {e}")
            continue
    
    return records


def import_to_db(conn, records):
    """PostgreSQLにインポート"""
    if not records:
        return 0
    
    cur = conn.cursor()
    
    insert_sql = """
    INSERT INTO land_prices_kokudo (
        survey_year, original_address, official_price, land_area,
        data_source, latitude, longitude, created_at,
        land_use, building_coverage_ratio, floor_area_ratio,
        road_direction, road_width, nearest_station, station_distance
    ) VALUES (
        %(survey_year)s, %(original_address)s, %(official_price)s, %(land_area)s,
        %(data_source)s, %(latitude)s, %(longitude)s, %(created_at)s,
        %(land_use)s, %(building_coverage_ratio)s, %(floor_area_ratio)s,
        %(road_direction)s, %(road_width)s, %(nearest_station)s, %(station_distance)s
    )
    ON CONFLICT (survey_year, original_address) DO UPDATE SET
        official_price = EXCLUDED.official_price,
        land_area = EXCLUDED.land_area,
        land_use = EXCLUDED.land_use,
        building_coverage_ratio = EXCLUDED.building_coverage_ratio,
        floor_area_ratio = EXCLUDED.floor_area_ratio,
        road_direction = EXCLUDED.road_direction,
        road_width = EXCLUDED.road_width,
        nearest_station = EXCLUDED.nearest_station,
        station_distance = EXCLUDED.station_distance
    """
    
    success_count = 0
    error_count = 0
    
    for record in records:
        try:
            # 必須フィールドのデフォルト値設定
            record.setdefault('land_use', None)
            record.setdefault('building_coverage_ratio', None)
            record.setdefault('floor_area_ratio', None)
            record.setdefault('road_direction', None)
            record.setdefault('road_width', None)
            record.setdefault('nearest_station', None)
            record.setdefault('station_distance', None)
            
            cur.execute(insert_sql, record)
            success_count += 1
        except Exception as e:
            print(f"    ❌ インポートエラー: {e}")
            print(f"       データ: {record.get('original_address', 'N/A')}")
            error_count += 1
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    
    return success_count, error_count


def main():
    print("=" * 80)
    print("国土数値情報（地価公示データ）テストインポート")
    print("Step 1: 3年分（2000年、2016年、2020年）")
    print("=" * 80)
    
    # データベース接続
    db_config = load_db_config()
    try:
        conn = psycopg2.connect(**db_config)
        print("\n✅ PostgreSQLに接続しました")
    except Exception as e:
        print(f"\n❌ PostgreSQL接続エラー: {e}")
        return
    
    # テーブル作成
    create_table(conn)
    
    # テスト対象年度の設定
    base_path = project_root / "data" / "raw" / "national" / "kokudo_suuchi"
    
    test_configs = [
        {
            'year': 2000,
            'filepath': base_path / "2000_13" / "L01-00_13-g_LandPrice.shp",
            'field_mapping': {
                'city_code': 'L01_017',
                'city_name': 'L01_018',
                'address': 'L01_019',
                'price': 'L01_006',
                'land_area': 'L01_020',
            }
        },
        {
            'year': 2016,
            'filepath': base_path / "2016_13" / "L01-16_13.shp",
            'field_mapping': {
                'city_code': 'L01_017',
                'city_name': 'L01_018',
                'address': 'L01_019',
                'price': 'L01_006',
                'land_area': 'L01_020',
            }
        },
        {
            'year': 2020,
            'filepath': base_path / "2020_13" / "L01-20_13_GML" / "L01-20_13.geojson",
            'field_mapping': {
                'city_code': 'L01_021',
                'city_name': 'L01_022',
                'address': 'L01_023',
                'price': 'L01_006',  # 価格フィールド追加
                'land_area': 'L01_024',
                'road_direction': 'L01_037',
                'road_width': 'L01_038',
                'nearest_station': 'L01_045',
                'station_distance': 'L01_046',
                'land_use': 'L01_047',
                'building_coverage': 'L01_052',
                'floor_area_ratio': 'L01_053',
            }
        }
    ]
    
    total_success = 0
    total_error = 0
    
    for config in test_configs:
        print(f"\n{'='*80}")
        print(f"📂 {config['year']}年をインポート中...")
        print('='*80)
        
        filepath = config['filepath']
        if not filepath.exists():
            print(f"  ❌ ファイルが見つかりません: {filepath}")
            continue
        
        # データ読み込み
        try:
            records = load_shapefile_data(filepath, config['year'], config['field_mapping'])
            print(f"  ✅ データ抽出完了: {len(records)}件")
        except Exception as e:
            print(f"  ❌ データ読み込みエラー: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # インポート
        success, error = import_to_db(conn, records)
        total_success += success
        total_error += error
        
        print(f"  ✅ インポート完了: 成功 {success}件、エラー {error}件")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print(f"✅ 合計 {total_success}件のレコードをインポートしました")
    if total_error > 0:
        print(f"⚠️  エラー: {total_error}件")
    print("=" * 80)


if __name__ == '__main__':
    import pandas as pd  # geopandasの依存関係で必要
    main()

