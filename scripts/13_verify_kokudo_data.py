#!/usr/bin/env python3
"""
国土数値情報の取得確認
"""
import psycopg2
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
    db_config = load_db_config()
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ データベース接続失敗: {e}")
        return
    
    print("=" * 60)
    print("国土数値情報 取得確認")
    print("=" * 60)
    
    # 用途地域の分布
    print("\n【用途地域の分布】")
    cursor.execute('''
        SELECT land_use, COUNT(*) as count
        FROM land_prices
        WHERE survey_year = 2021 AND land_use IS NOT NULL
        GROUP BY land_use
        ORDER BY count DESC
    ''')
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"  {row[0]}: {row[1]}件")
    else:
        print("  （データなし）")
    
    # 建蔽率・容積率の分布
    print("\n【建蔽率・容積率の組み合わせ（上位5）】")
    cursor.execute('''
        SELECT 
            building_coverage_ratio,
            floor_area_ratio,
            COUNT(*) as count
        FROM land_prices
        WHERE survey_year = 2021 
          AND building_coverage_ratio IS NOT NULL
          AND floor_area_ratio IS NOT NULL
        GROUP BY building_coverage_ratio, floor_area_ratio
        ORDER BY count DESC
        LIMIT 5
    ''')
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"  {row[0]}% / {row[1]}%: {row[2]}件")
    else:
        print("  （データなし）")
    
    # サンプルデータ表示
    print("\n【サンプルデータ（三宿2丁目）】")
    cursor.execute('''
        SELECT 
            original_address,
            official_price,
            land_use,
            building_coverage_ratio,
            floor_area_ratio,
            road_direction,
            road_width
        FROM land_prices
        WHERE survey_year = 2021
          AND original_address LIKE '%三宿２%'
        LIMIT 1
    ''')
    row = cursor.fetchone()
    if row:
        print(f"  住所: {row[0]}")
        print(f"  地価: {row[1]:,}円/㎡")
        print(f"  用途地域: {row[2]}")
        print(f"  建蔽率: {row[3]}%")
        print(f"  容積率: {row[4]}%")
        print(f"  前面道路: {row[5]} {row[6]}m")
    else:
        print("  （データなし）")
    
    # データ取得率
    print("\n【データ取得率】")
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            COUNT(land_use) as has_land_use,
            COUNT(building_coverage_ratio) as has_building_coverage,
            COUNT(floor_area_ratio) as has_floor_area
        FROM land_prices
        WHERE survey_year = 2021
    ''')
    row = cursor.fetchone()
    if row:
        total = row[0]
        print(f"  総件数: {total}件")
        if total > 0:
            print(f"  用途地域: {row[1]}件 ({row[1]*100//total}%)")
            print(f"  建蔽率: {row[2]}件 ({row[2]*100//total}%)")
            print(f"  容積率: {row[3]}件 ({row[3]*100//total}%)")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

