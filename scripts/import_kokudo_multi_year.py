#!/usr/bin/env python3
"""
国土数値情報（2021-2025年版）を一括インポート

各年度のGeoJSONファイルから用途地域、建蔽率、容積率などを取得し、
対応する年度のland_pricesレコードに設定する
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
    """
    住所を正規化（全角→半角、スペース削除）
    
    Args:
        address: 元の住所文字列
    
    Returns:
        正規化された住所
    """
    if not address:
        return ""
    
    # 全角数字を半角に変換
    address = address.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    
    # スペース削除
    address = address.replace(' ', '').replace('　', '')
    
    # 「丁目」の異なる表記を統一
    address = re.sub(r'(\d+)[-−ー](\d+)[-−ー](\d+)', r'\1丁目\2番\3', address)
    address = re.sub(r'(\d+)[-−ー](\d+)', r'\1丁目\2番', address)
    
    return address


def extract_from_geojson(geojson_path):
    """
    GeoJSONから国土数値情報を抽出
    
    Args:
        geojson_path: GeoJSONファイルのパス
    
    Returns:
        住所をキーとした辞書 {住所: {用途地域, 建蔽率, ...}}
    """
    print(f"\n📂 {geojson_path.name} を読み込み中...")
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    
    features = geojson_data.get('features', [])
    print(f"   総件数: {len(features)}件")
    
    result = {}
    
    for feature in features:
        props = feature['properties']
        
        # 住所を取得（L01_023フィールド）
        address = props.get('L01_023', '')
        if not address:
            continue
        
        # 世田谷区のデータのみ抽出
        if '世田谷' not in address and '世田谷' not in props.get('L01_022', ''):
            continue
        
        # 住所から「世田谷区」を除去
        if '世田谷区' in address:
            address = address.split('世田谷区')[1]
        
        # 住所を正規化
        normalized_addr = normalize_address(address)
        
        # データを抽出
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
        
        data = {
            'land_use': LAND_USE_MAP.get(props.get('L01_047', ''), None),
            'building_coverage_ratio': safe_int(props.get('L01_052')),
            'floor_area_ratio': safe_int(props.get('L01_053')),
            'road_direction': props.get('L01_037', None) if props.get('L01_037') and props.get('L01_037') != '_' else None,
            'road_width': safe_float(props.get('L01_038')),
            'land_area': safe_int(props.get('L01_024')),
            'nearest_station': props.get('L01_045', None) if props.get('L01_045') and props.get('L01_045') != '_' else None,
            'station_distance': safe_int(props.get('L01_046')),
            'original_address': address  # デバッグ用
        }
        
        result[normalized_addr] = data
    
    print(f"   抽出完了: {len(result)}件（世田谷区のみ）")
    return result


def import_year_data(conn, year, geojson_data):
    """
    指定年度のデータをインポート
    
    Args:
        conn: PostgreSQL接続
        year: 年度（2021-2025）
        geojson_data: GeoJSONから抽出したデータ
    
    Returns:
        更新件数
    """
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
    
    updated_count = 0
    matched_addresses = []
    
    for record_id, db_address in records:
        # 住所を正規化
        normalized_db_addr = normalize_address(db_address)
        
        # GeoJSONデータから検索
        matched_data = None
        
        # 完全一致
        if normalized_db_addr in geojson_data:
            matched_data = geojson_data[normalized_db_addr]
            matched_addresses.append(db_address)
        else:
            # 部分一致（前方一致）
            for geojson_addr, data in geojson_data.items():
                # 正規化された住所が含まれているか
                if normalized_db_addr in geojson_addr or geojson_addr in normalized_db_addr:
                    matched_data = data
                    matched_addresses.append(db_address)
                    break
        
        if not matched_data:
            continue
        
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
            matched_data['land_use'],
            matched_data['building_coverage_ratio'],
            matched_data['floor_area_ratio'],
            matched_data['road_direction'],
            matched_data['road_width'],
            matched_data['land_area'],
            matched_data['nearest_station'],
            matched_data['station_distance'],
            record_id
        ))
        
        updated_count += 1
    
    conn.commit()
    
    print(f"   ✅ {updated_count}件を更新しました")
    
    # マッチしなかった住所を表示
    if updated_count < len(records):
        print(f"   ⚠️  {len(records) - updated_count}件がマッチしませんでした")
        
        # マッチしなかった住所を取得
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
    """
    インポート結果を確認
    """
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
    print("国土数値情報（2021-2025年版）一括インポート")
    print("=" * 60)
    
    # GeoJSONファイルのパス
    base_path = project_root / "data" / "raw" / "national" / "kokudo_suuchi"
    
    geojson_files = {
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
    
    for year in [2021, 2022, 2023, 2024, 2025]:
        geojson_path = geojson_files[year]
        
        if not geojson_path.exists():
            print(f"\n⚠️  {year}年版GeoJSONが見つかりません。スキップします。")
            continue
        
        # GeoJSONからデータ抽出
        geojson_data = extract_from_geojson(geojson_path)
        
        if not geojson_data:
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

