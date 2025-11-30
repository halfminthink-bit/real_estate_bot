#!/usr/bin/env python3
"""
PostgreSQLから町丁目リストを取得してareas.csvを生成

使い方:
    python scripts/11_create_areas_csv.py
"""
import psycopg2
import csv
import yaml
from pathlib import Path
import sys
from dotenv import load_dotenv
import os

# 環境変数を読み込み
load_dotenv()

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.utils.address_normalizer import AddressNormalizer

# DB接続設定
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
    """メイン処理"""
    print("=" * 60)
    print("areas.csv 生成開始")
    print("=" * 60)
    
    # 1. PostgreSQL接続
    print("\n[Step 1] PostgreSQLに接続...")
    db_config = load_db_config()
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print("✅ 接続成功")
    except Exception as e:
        print(f"❌ 接続失敗: {e}")
        print("→ PostgreSQLが起動しているか確認してください: docker-compose ps")
        sys.exit(1)
    
    # 2. ユニークな町丁目を取得
    print("[Step 2] 町丁目リスト取得...")
    cursor.execute('''
        SELECT DISTINCT original_address
        FROM land_prices
        WHERE survey_year = 2025
        ORDER BY original_address
    ''')
    
    addresses = [row[0] for row in cursor.fetchall()]
    print(f"✅ {len(addresses)} 件の住所を取得")
    
    cursor.close()
    conn.close()
    
    # 3. areas.csv 作成
    print("[Step 3] areas.csv 生成...")
    
    output_dir = Path('projects/setagaya_real_estate/data')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = output_dir / 'areas.csv'
    
    success_count = 0
    error_count = 0
    normalizer = AddressNormalizer()
    
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # ヘッダー
        writer.writerow(['area_id', 'ward', 'choume', 'priority', 'status'])
        
        # データ行
        for idx, address in enumerate(addresses, start=1):
            try:
                # 住所正規化
                choume, _ = AddressNormalizer.extract_choume(address)
                
                if not choume:
                    print(f"  ⚠️  正規化失敗: {address}")
                    error_count += 1
                    continue
                
                # area_id生成（連番を使用）
                area_id = idx
                
                # CSV書き込み
                writer.writerow([area_id, '世田谷区', choume, 1, 'pending'])
                
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ エラー: {address} - {e}")
                error_count += 1
    
    # 4. 結果表示
    print("\n" + "=" * 60)
    print("areas.csv 生成完了")
    print("=" * 60)
    print(f"✅ 成功: {success_count} 件")
    if error_count > 0:
        print(f"❌ エラー: {error_count} 件")
    print(f"📁 出力先: {csv_path.absolute()}")
    print("=" * 60)
    
    # 5. サンプル表示
    print("\n【先頭5件のサンプル】")
    with open(csv_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 6:  # ヘッダー + 5件
                break
            print(f"  {line.rstrip()}")

if __name__ == "__main__":
    main()

