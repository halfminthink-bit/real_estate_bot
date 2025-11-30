#!/usr/bin/env python3
"""
国土数値情報（2018-2025年版）を一括インポート（強力マッチング版）
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
    "1低専": "1低専", "2低専": "2低専",
    "1中専": "1中専", "2中専": "2中専",
    "1住居": "1住居", "2住居": "2住居",
    "準住居": "準住居", "近商": "近商",
    "商業": "商業", "準工": "準工",
    "工業": "工業", "工専": "工専",
}

# 漢数字変換用マップ
KANJI_NUM_MAP = str.maketrans('一二三四五六七八九', '123456789')
REV_KANJI_NUM_MAP = {
    '1': '一', '2': '二', '3': '三', '4': '四', '5': '五',
    '6': '六', '7': '七', '8': '八', '9': '九'
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

def normalize_string(s):
    """文字列を正規化（全角英数→半角、スペース削除）"""
    if not s:
        return ""
    s = s.translate(str.maketrans('０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ', 
                                  '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'))
    s = s.replace(' ', '').replace('　', '')
    return s

def normalize_address(address):
    """住所を正規化"""
    address = normalize_string(address)
    # 世田谷区が含まれていたら削除（突合精度向上のため）
    if '世田谷区' in address:
        parts = address.split('世田谷区')
        if len(parts) > 1:
            address = parts[1].strip()
    # 「字」「大字」を削除
    address = address.replace('大字', '').replace('字', '')
    return address

def num_to_kanji(s):
    """数字が含まれる文字列の数字部分を漢数字に変換（例: 2丁目 -> 二丁目）"""
    res = ""
    for char in s:
        res += REV_KANJI_NUM_MAP.get(char, char)
    return res
def extract_choume_candidates(address):
    """
    住所から町丁目名の候補リストを返す（強化版）
    """
    if not address:
        return []
    
    # 1. 基本正規化（全角英数→半角、スペース削除）
    normalized = normalize_address(address)
    
    # 2. ハイフン正規化（ここを強化）
    # 全角ハイフン(－)、マイナス(−)、長音(ー)、ダッシュ(‐)などを全て半角ハイフン(-)に置換
    normalized = re.sub(r'[－−ー‐]', '-', normalized)
    
    candidates = []

    # パターン1: "◯◯N丁目" の形式
    # 例: "等々力5丁目..."
    match1 = re.search(r'^(.+?\d+)丁目', normalized)
    if match1:
        base = match1.group(1) + "丁目"
        candidates.append(base)
        candidates.append(num_to_kanji(base)) # 漢数字版（等々力五丁目）

    # パターン2: "◯◯N-" の形式（ここが2018-2020年用）
    # 例: "喜多見9-19-6" -> "喜多見9-" にマッチ
    match2 = re.search(r'^(.+?)(\d+)-', normalized)
    if match2:
        area_name = match2.group(1)   # 喜多見
        choume_num = match2.group(2)  # 9
        
        # "喜多見9丁目"
        base = f"{area_name}{choume_num}丁目"
        candidates.append(base)
        
        # "喜多見九丁目" (漢数字変換)
        candidates.append(f"{area_name}{num_to_kanji(choume_num)}丁目")
        
        # "喜多見" (丁目なしの地域用フォールバック)
        candidates.append(area_name)

    # パターン3: 数字が含まれない場合（単なる町名）
    # 例: "大蔵..."
    match3 = re.search(r'^(\D+)', normalized)
    if match3:
        candidates.append(match3.group(1))

    # 重複を除去してリスト化
    return list(set(candidates))
def get_field_mapping(year):
    """年度別のフィールドマッピング"""
    if year <= 2020:
        return {
            'address': 'L01_023',
            'city_name': 'L01_022',
            'land_area': 'L01_024',
            'road_direction': 'L01_037',
            'road_width': 'L01_038',
            'nearest_station': 'L01_045',
            'station_distance': 'L01_046',
            'land_use': 'L01_047',
            'building_coverage': 'L01_052',
            'floor_area_ratio': 'L01_053',
            'official_price': 'L01_006',
        }
    elif year == 2021:
        return {
            'address': 'L01_023',
            'city_name': 'L01_022',
            'land_area': 'L01_024',
            'road_direction': 'L01_037',
            'road_width': 'L01_038',
            'nearest_station': 'L01_045',
            'station_distance': 'L01_046',
            'land_use': 'L01_047',
            'building_coverage': 'L01_052',
            'floor_area_ratio': 'L01_053',
            'official_price': 'L01_006',
        }
    elif year <= 2023:
        return {
            'address': 'L01_024',
            'city_name': 'L01_023',
            'land_area': 'L01_026',
            'road_direction': 'L01_040',
            'road_width': 'L01_041',
            'nearest_station': 'L01_048',
            'station_distance': 'L01_049',
            'land_use': 'L01_050',
            'building_coverage': 'L01_056',
            'floor_area_ratio': 'L01_057',
            'official_price': 'L01_006',
        }
    else:
        return {
            'address': 'L01_025',
            'city_name': 'L01_024',
            'land_area': 'L01_027',
            'road_direction': 'L01_041',
            'road_width': 'L01_042',
            'nearest_station': 'L01_048',
            'station_distance': 'L01_050',
            'land_use': 'L01_051',
            'building_coverage': 'L01_057',
            'floor_area_ratio': 'L01_058',
            'official_price': 'L01_006',
        }

def extract_from_geojson(geojson_path, year=None):
    print(f"\n📂 {geojson_path.name} を読み込み中...")
    if year is None:
        import re
        match = re.search(r'(\d{4})_13', str(geojson_path))
        year = int(match.group(1)) if match else 2021
    
    fields = get_field_mapping(year)
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    
    features = geojson_data.get('features', [])
    print(f"   総件数: {len(features)}件")
    
    result = {}
    for feature in features:
        props = feature['properties']
        
        # 住所取得
        address = props.get(fields['address'], '')
        if not address: address = props.get('L01_023', '')
        if not address: continue
        
        # 世田谷区フィルタ
        city_name = props.get(fields['city_name'], '')
        if '世田谷' not in address and '世田谷' not in city_name:
            continue
        
        # 地価
        price_val = props.get(fields.get('official_price', 'L01_006'), '')
        try:
            official_price = int(price_val)
        except:
            official_price = None

        def safe_val(key, cast=int):
            v = props.get(fields.get(key), '')
            try: return cast(v)
            except: return None

        normalized_addr = normalize_address(address)
        result[normalized_addr] = {
            'land_use': LAND_USE_MAP.get(props.get(fields['land_use'], ''), None),
            'building_coverage_ratio': safe_val('building_coverage'),
            'floor_area_ratio': safe_val('floor_area_ratio'),
            'road_direction': props.get(fields['road_direction'], None),
            'road_width': safe_val('road_width', float),
            'land_area': safe_val('land_area'),
            'nearest_station': props.get(fields['nearest_station'], None),
            'station_distance': safe_val('station_distance'),
            'official_price': official_price,
            'original_address': address
        }
    
    print(f"   抽出完了: {len(result)}件（世田谷区のみ）")
    return result

def import_year_data(conn, year, geojson_data):
    print(f"\n🔄 {year}年度のデータをインポート中...")
    cur = conn.cursor()
    
    # マスタキャッシュ作成 (正規化キー -> コード)
    cur.execute("SELECT choume_name, choume_code FROM choume")
    choume_map = {}
    for row in cur.fetchall():
        choume_map[normalize_string(row[0])] = row[1]
    
    # 既存レコード取得
    cur.execute("SELECT id, original_address FROM land_prices WHERE survey_year = %s", (year,))
    existing_map = {normalize_address(addr): rid for rid, addr in cur.fetchall() if addr}
    
    stats = {'update': 0, 'insert': 0, 'skip': 0, 'error': 0}
    debug_skips = []

    for norm_addr, data in geojson_data.items():
        try:
            # UPDATE
            if norm_addr in existing_map:
                cur.execute("""
                    UPDATE land_prices SET 
                        land_use=%s, building_coverage_ratio=%s, floor_area_ratio=%s,
                        road_direction=%s, road_width=%s, land_area=%s,
                        nearest_station=%s, station_distance=%s,
                        official_price=COALESCE(official_price, %s)
                    WHERE id=%s
                """, (
                    data['land_use'], data['building_coverage_ratio'], data['floor_area_ratio'],
                    data['road_direction'], data['road_width'], data['land_area'],
                    data['nearest_station'], data['station_distance'],
                    data['official_price'], existing_map[norm_addr]
                ))
                stats['update'] += 1
            
            # INSERT
            else:
                # 候補リストからマッチするものを探す
                candidates = extract_choume_candidates(data['original_address'])
                choume_code = None
                matched_name = None
                
                for cand in candidates:
                    # 正規化したキーで検索
                    norm_cand = normalize_string(cand)
                    if norm_cand in choume_map:
                        choume_code = choume_map[norm_cand]
                        matched_name = cand
                        break
                
                if not choume_code:
                    stats['skip'] += 1
                    if len(debug_skips) < 3: # 最初の3件だけ詳細ログ保存
                        debug_skips.append(f"Org: {data['original_address']} -> Cands: {candidates}")
                    continue

                cur.execute("""
                    INSERT INTO land_prices (
                        choume_code, survey_year, official_price,
                        land_use, building_coverage_ratio, floor_area_ratio,
                        road_direction, road_width, land_area,
                        nearest_station, station_distance, original_address, data_source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'kokudo_geojson')
                    ON CONFLICT (choume_code, survey_year, land_type, data_source, original_address)
                    DO UPDATE SET official_price = EXCLUDED.official_price
                """, (
                    choume_code, year, data['official_price'],
                    data['land_use'], data['building_coverage_ratio'], data['floor_area_ratio'],
                    data['road_direction'], data['road_width'], data['land_area'],
                    data['nearest_station'], data['station_distance'], data['original_address']
                ))
                stats['insert'] += 1

        except Exception as e:
            stats['error'] += 1
            print(f"Error: {e}")

    conn.commit()
    cur.close()
    
    print(f"   ✅ UPDATE: {stats['update']} / INSERT: {stats['insert']}")
    print(f"   ⚠️ SKIP: {stats['skip']} / ERROR: {stats['error']}")
    if debug_skips:
        print("   [Skip Sample Debug]")
        for msg in debug_skips:
            print(f"     - {msg}")
    
    return stats['update'] + stats['insert']

def main():
    print("=" * 60 + "\n国土数値情報（2018-2025年版）一括インポート（修正版）\n" + "=" * 60)
    
    base_path = project_root / "data" / "raw" / "national" / "kokudo_suuchi"
    # ※ファイルパスは環境に合わせて調整してください
    geojson_files = {
        y: base_path / f"{y}_13" / (f"L01-{str(y)[2:]}_13_GML" if y!=2022 and y!=2019 else f"L01-{str(y)[2:]}_13") / f"L01-{str(y)[2:]}_13.geojson"
        for y in range(2018, 2026)
    }
    # パス微調整用（実際のフォルダ構成に合わせてフォールバック）
    for y in geojson_files:
        if not geojson_files[y].exists():
             # パターンB: GMLフォルダなし
             alt = base_path / f"{y}_13" / f"L01-{str(y)[2:]}_13.geojson"
             if alt.exists(): geojson_files[y] = alt

    db_config = load_db_config()
    try:
        conn = psycopg2.connect(**db_config)
    except Exception as e:
        print(f"DB接続エラー: {e}")
        return

    total = 0
    for year in range(2018, 2026):
        path = geojson_files.get(year)
        if path and path.exists():
            data = extract_from_geojson(path, year)
            if data:
                total += import_year_data(conn, year, data)
        else:
            print(f"\n⚠️ {year}年ファイルなし: {path}")

    conn.close()
    print(f"\n完了: 合計 {total} 件処理")

if __name__ == "__main__":
    main()