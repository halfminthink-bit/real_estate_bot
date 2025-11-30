#!/usr/bin/env python3
"""
国土数値情報（GeoJSON）から追加データをインポート

データソース: data/raw/national/kokudo_suuchi/2021_13/L01-21_13_GML/L01-21_13.geojson
対象: 世田谷区のみ
"""
import json
import psycopg2
import yaml
import re
from pathlib import Path
import sys
from dotenv import load_dotenv
import os

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


def load_geojson(file_path):
    """GeoJSONファイルを読み込み"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_setagaya_data(geojson):
    """世田谷区のデータのみ抽出"""
    setagaya_features = []
    for feature in geojson['features']:
        props = feature['properties']
        # L01_022が市区町村名、L01_023が住所
        city_name = props.get('L01_022', '')
        address = props.get('L01_023', '')
        if '世田谷' in city_name or '世田谷' in address:
            setagaya_features.append(feature)
    return setagaya_features


def parse_feature(feature):
    """GeoJSONのfeatureから必要なデータを抽出"""
    props = feature['properties']
    
    # 住所（正規化用）
    address = props.get('L01_023', '')
    # "東京都　世田谷区松原５−４０−１０" → "松原５−４０−１０"
    if '世田谷区' in address:
        address = address.split('世田谷区')[1]
    
    return {
        'address': address.strip(),
        'land_use': props.get('L01_047', ''),           # 用途地域
        'building_coverage': props.get('L01_052', ''),  # 建蔽率
        'floor_area': props.get('L01_053', ''),         # 容積率
        'road_direction': props.get('L01_037', ''),     # 前面道路方位
        'road_width': props.get('L01_038', ''),         # 前面道路幅員
        'land_area': props.get('L01_024', ''),          # 地積
        'nearest_station': props.get('L01_045', ''),    # 最寄駅
        'station_distance': props.get('L01_046', '')    # 駅距離
    }


def normalize_address_for_matching(address):
    """
    住所を正規化してマッチング用の文字列を生成
    
    例: "桜上水５−４０−１０" → "桜上水5丁目"
        "等々力５丁目３３番１５" → "等々力5丁目"
    """
    if not address:
        return ""
    
    # 全角数字を半角に
    address = address.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    
    # 全角ハイフンを半角に
    address = address.replace('−', '-').replace('ー', '-')
    
    # パターン1: "◯◯N丁目" の形式（すでに丁目がある）
    # 例: "等々力5丁目３３番１５" → "等々力5丁目"
    pattern1 = r'^(.+?)(\d+)丁目'
    match = re.search(pattern1, address)
    if match:
        return f"{match.group(1)}{match.group(2)}丁目"
    
    # パターン2: "◯◯N-" の形式（丁目がない）
    # 例: "桜上水5-４０-１０" → "桜上水5丁目"
    pattern2 = r'^(.+?)(\d+)[-−ー]'
    match = re.search(pattern2, address)
    if match:
        return f"{match.group(1)}{match.group(2)}丁目"
    
    # パターン3: "◯◯N番" の形式
    # 例: "上馬1７番１２" → "上馬1丁目"
    pattern3 = r'^(.+?)(\d+)番'
    match = re.search(pattern3, address)
    if match:
        return f"{match.group(1)}{match.group(2)}丁目"
    
    # どれにもマッチしない場合
    return address


def update_database(features, db_config):
    """PostgreSQLにデータを更新"""
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    success_count = 0
    error_count = 0
    no_match_count = 0
    
    # NULL値の処理関数
    def safe_int(value):
        if not value or value == '_' or value == '':
            return None
        try:
            return int(value)
        except:
            return None
    
    def safe_float(value):
        if not value or value == '_' or value == '':
            return None
        try:
            return float(value)
        except:
            return None
    
    for feature in features:
        try:
            data = parse_feature(feature)
            
            # 住所正規化
            normalized_addr = normalize_address_for_matching(data['address'])
            
            if not normalized_addr:
                print(f"  ⚠️  住所抽出失敗: {data['address']}")
                error_count += 1
                continue
            
            # デバッグ用：PostgreSQLの住所を確認（最初の3件のみ）
            if no_match_count + success_count < 3:
                cursor.execute('''
                    SELECT original_address 
                    FROM land_prices 
                    WHERE survey_year = 2021 
                      AND TRANSLATE(original_address, '０１２３４５６７８９', '0123456789') LIKE %s
                    LIMIT 1
                ''', (f"%{normalized_addr}%",))
                
                db_result = cursor.fetchone()
                if db_result:
                    print(f"  🔍 デバッグ: '{normalized_addr}' → DB: '{db_result[0]}'")
                else:
                    print(f"  🔍 デバッグ: '{normalized_addr}' → DB: マッチなし")
                    # 部分マッチを試す
                    search_pattern = normalized_addr.replace('丁目', '')
                    cursor.execute('''
                        SELECT original_address 
                        FROM land_prices 
                        WHERE survey_year = 2021 
                          AND TRANSLATE(original_address, '０１２３４５６７８９', '0123456789') LIKE %s
                        LIMIT 3
                    ''', (f"%{search_pattern}%",))
                    similar = cursor.fetchall()
                    if similar:
                        print(f"        類似住所: {[s[0] for s in similar]}")
            
            building_coverage = safe_int(data['building_coverage'])
            floor_area = safe_int(data['floor_area'])
            road_width = safe_float(data['road_width'])
            land_area = safe_int(data['land_area'])
            station_distance = safe_int(data['station_distance'])
            
            # UPDATEクエリ（PostgreSQL側でも全角→半角変換してマッチング）
            cursor.execute('''
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
                WHERE
                    survey_year = 2021
                    AND TRANSLATE(original_address, '０１２３４５６７８９', '0123456789') LIKE %s
            ''', (
                data['land_use'] or None,
                building_coverage,
                floor_area,
                data['road_direction'] or None,
                road_width,
                land_area,
                data['nearest_station'] or None,
                station_distance,
                f"%{normalized_addr}%"
            ))
            
            if cursor.rowcount > 0:
                success_count += cursor.rowcount
                if success_count <= 5:  # 最初の5件を表示
                    print(f"  ✅ 更新成功: {normalized_addr} ({cursor.rowcount}件)")
            else:
                no_match_count += 1
                if no_match_count <= 10:  # 最初の10件を表示
                    print(f"  ⚠️  マッチなし: {normalized_addr} (元住所: {data['address']})")
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ エラー: {data.get('address', 'unknown')[:30]} - {e}")
            # エラー時はロールバックして次へ
            try:
                conn.rollback()
            except:
                pass
            # 新しいトランザクション開始
            continue
    
    # 最後にコミット
    try:
        conn.commit()
    except Exception as e:
        print(f"  ⚠️  コミットエラー: {e}")
        conn.rollback()
    
    cursor.close()
    conn.close()
    
    return success_count, no_match_count, error_count


def main():
    """メイン処理"""
    print("=" * 60)
    print("国土数値情報インポート開始")
    print("=" * 60)
    
    # GeoJSONファイルパス
    geojson_path = Path('data/raw/national/kokudo_suuchi/2021_13/L01-21_13_GML/L01-21_13.geojson')
    
    if not geojson_path.exists():
        print(f"❌ ファイルが見つかりません: {geojson_path}")
        return
    
    # データ読み込み
    print(f"\n[Step 1] GeoJSON読み込み: {geojson_path}")
    try:
        geojson = load_geojson(geojson_path)
        print(f"✅ 総件数: {len(geojson.get('features', []))} 地点")
    except Exception as e:
        print(f"❌ 読み込み失敗: {e}")
        return
    
    # 世田谷区データ抽出
    print("[Step 2] 世田谷区データ抽出...")
    setagaya_features = extract_setagaya_data(geojson)
    print(f"✅ 世田谷区: {len(setagaya_features)} 地点")
    
    if len(setagaya_features) == 0:
        print("⚠️  世田谷区のデータが見つかりませんでした")
        return
    
    # データベース更新
    print("\n[Step 3] PostgreSQL更新...")
    db_config = load_db_config()
    success, no_match, error = update_database(setagaya_features, db_config)
    
    # 結果表示
    print("\n" + "=" * 60)
    print("インポート完了")
    print("=" * 60)
    print(f"✅ 更新成功: {success} 件")
    if no_match > 0:
        print(f"⚠️  マッチなし: {no_match} 件")
    if error > 0:
        print(f"❌ エラー: {error} 件")
    print("=" * 60)

if __name__ == "__main__":
    main()

