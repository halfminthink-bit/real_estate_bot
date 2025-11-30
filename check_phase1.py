import psycopg2
from pathlib import Path

# Docker接続設定
config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'real_estate_dev',
    'user': 'postgres',
    'password': 'postgres'
}

print("="*60)
print("Phase 1-4 実装確認")
print("="*60)

try:
    # 接続
    conn = psycopg2.connect(**config)
    cursor = conn.cursor()
    print("\n✅ Step 1: PostgreSQL接続成功")
    
    # バージョン確認
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"   {version[:50]}...")
    
    # テーブル一覧
    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
    tables = cursor.fetchall()
    
    print(f"\n✅ Step 2: テーブル確認（{len(tables)}個）")
    expected_tables = ['area_scores', 'choume', 'cities', 'graph_data', 
                      'land_price_summary', 'land_prices', 'population', 
                      'population_summary', 'prefectures']
    
    if len(tables) == 0:
        print("   ❌ テーブルが1つも作成されていません")
        print("   → scripts/01_setup_database.py を実行してください")
    else:
        for table in tables:
            status = "✓" if table[0] in expected_tables else "?"
            print(f"   [{status}] {table[0]}")
    
    # 都道府県マスタ
    cursor.execute("SELECT * FROM prefectures;")
    prefectures = cursor.fetchall()
    print(f"\n✅ Step 3: 都道府県マスタ（{len(prefectures)}件）")
    if len(prefectures) == 0:
        print("   ❌ データが入っていません")
        print("   → scripts/01_setup_database.py を実行してください")
    else:
        for pref in prefectures:
            print(f"   {pref[0]}: {pref[1]}")
    
    # 市区町村マスタ
    cursor.execute("SELECT * FROM cities;")
    cities = cursor.fetchall()
    print(f"\n✅ Step 4: 市区町村マスタ（{len(cities)}件）")
    if len(cities) == 0:
        print("   ❌ データが入っていません")
        print("   → scripts/01_setup_database.py を実行してください")
    else:
        for city in cities:
            print(f"   {city[0]}: {city[2]}")
    
    # ファイル確認
    print(f"\n✅ Step 5: ダウンロードファイル確認")
    raw_dir = Path("data/raw/national/kokudo_suuchi")
    if raw_dir.exists():
        files = list(raw_dir.rglob("*.csv")) + list(raw_dir.rglob("*.xml")) + list(raw_dir.rglob("*.zip"))
        print(f"   ファイル数: {len(files)}")
        for f in files[:5]:  # 最初の5個だけ表示
            print(f"   - {f.relative_to(raw_dir)}")
    else:
        print("   ❌ ディレクトリが存在しません")
        print("   → scripts/02_download_data.py を実行してください")
    
    # 処理済みCSV確認
    print(f"\n✅ Step 6: 処理済みCSV確認")
    csv_path = Path("data/processed/master/kokudo_land_price_2024.csv")
    if csv_path.exists():
        import pandas as pd
        df = pd.read_csv(csv_path)
        print(f"   ✓ {csv_path.name}")
        print(f"   行数: {len(df)}")
        print(f"   カラム数: {len(df.columns)}")
    else:
        print("   ❌ CSVファイルが存在しません")
        print("   → scripts/02_download_data.py を実行してください")
    
    # 地価データ確認
    cursor.execute("SELECT COUNT(*) FROM land_prices;")
    land_price_count = cursor.fetchone()[0]
    print(f"\n✅ Step 7: 地価データ（{land_price_count}件）")
    
    if land_price_count == 0:
        print("   ❌ データが入っていません")
        print("   → scripts/03_import_data.py を実行してください")
    else:
        # データソース別
        cursor.execute("SELECT data_source, COUNT(*) FROM land_prices GROUP BY data_source;")
        sources = cursor.fetchall()
        print("   データソース別:")
        for source, count in sources:
            print(f"     - {source}: {count}件")
        
        # 世田谷区データ
        cursor.execute("SELECT COUNT(*) FROM land_prices WHERE choume_code LIKE '13112%';")
        setagaya_count = cursor.fetchone()[0]
        print(f"   世田谷区: {setagaya_count}件")
        
        # サンプル表示
        cursor.execute("""
            SELECT choume_code, survey_year, land_type, official_price, original_address 
            FROM land_prices 
            WHERE choume_code LIKE '13112%' 
            LIMIT 3
        """)
        samples = cursor.fetchall()
        if samples:
            print("\n   サンプルデータ:")
            for s in samples:
                print(f"     {s[0]} | {s[1]}年 | {s[2]} | {s[3]:,}円/㎡")
                print(f"       住所: {s[4][:40]}...")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("確認完了")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ エラー: {e}")
    import traceback
    traceback.print_exc()

