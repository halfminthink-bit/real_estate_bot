#!/usr/bin/env python3
"""
スキーマ更新を適用
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
    print("=" * 60)
    print("スキーマ更新を適用")
    print("=" * 60)
    
    # SQLファイル読み込み
    sql_path = project_root / 'db' / 'migrations' / '002_add_kokudo_fields.sql'
    
    if not sql_path.exists():
        print(f"❌ SQLファイルが見つかりません: {sql_path}")
        return
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # データベース接続
    db_config = load_db_config()
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ データベース接続失敗: {e}")
        print("→ PostgreSQLが起動しているか確認してください: docker-compose ps")
        return
    
    try:
        # SQLを実行（複数のステートメントに対応）
        cursor.execute(sql)
        conn.commit()
        print("✅ スキーマ更新完了")
        
        # 確認
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'land_prices' 
              AND column_name IN ('land_use', 'building_coverage_ratio', 'floor_area_ratio', 
                                  'road_direction', 'road_width', 'land_area', 
                                  'nearest_station', 'station_distance')
            ORDER BY column_name
        """)
        
        results = cursor.fetchall()
        if results:
            print("\n【追加されたカラム】")
            for row in results:
                print(f"  {row[0]}: {row[1]}")
        else:
            print("\n⚠️  カラムが見つかりませんでした")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()

