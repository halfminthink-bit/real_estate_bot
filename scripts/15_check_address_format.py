#!/usr/bin/env python3
"""
PostgreSQLとGeoJSONの住所形式を比較
"""
import psycopg2
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv
import os

# 環境変数を読み込み
load_dotenv()

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent


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


def main():
    # PostgreSQLの住所サンプル
    db_config = load_db_config()
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ データベース接続失敗: {e}")
        return
    
    print("=" * 60)
    print("住所形式の比較")
    print("=" * 60)
    
    print("\n【PostgreSQL側の住所（サンプル10件）】")
    cursor.execute('''
        SELECT DISTINCT original_address
        FROM land_prices
        WHERE survey_year = 2021
        ORDER BY original_address
        LIMIT 10
    ''')
    
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. {row[0]}")
    
    cursor.close()
    conn.close()
    
    # GeoJSONの住所サンプル
    geojson_path = Path('data/raw/national/kokudo_suuchi/2021_13/L01-21_13_GML/L01-21_13.geojson')
    
    if not geojson_path.exists():
        print(f"\n⚠️  GeoJSONファイルが見つかりません: {geojson_path}")
        return
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
    
    print("\n【GeoJSON側の住所（世田谷区サンプル10件）】")
    setagaya_count = 0
    for feature in geojson['features']:
        props = feature['properties']
        city_name = props.get('L01_022', '')
        address = props.get('L01_023', '')
        
        if '世田谷' in city_name or '世田谷' in address:
            if '世田谷区' in address:
                address = address.split('世田谷区')[1].strip()
            setagaya_count += 1
            print(f"  {setagaya_count}. {address}")
            if setagaya_count >= 10:
                break
    
    if setagaya_count == 0:
        print("  （世田谷区のデータが見つかりませんでした）")

if __name__ == "__main__":
    main()

