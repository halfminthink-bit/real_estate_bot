import pandas as pd
import psycopg2
from pathlib import Path
from loguru import logger
from datetime import date, datetime
import re

# DB接続設定
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'real_estate_dev',
    'user': 'postgres',
    'password': 'postgres'
}

def clean_price(price_str):
    """
    価格文字列をintに変換
    例: '1,234,567' -> 1234567
    """
    if pd.isna(price_str):
        return None
    # カンマを除去して数値に変換
    price_str = str(price_str).replace(',', '').replace('円', '').strip()
    try:
        return int(float(price_str))
    except:
        return None

def convert_wareki_to_year(wareki):
    """
    和暦を西暦に変換
    例: 7 (令和7年) -> 2025
    """
    if pd.isna(wareki):
        return None
    wareki = int(wareki)
    # 令和は2019年から
    return 2018 + wareki

def load_tokyo_csv(csv_path: Path, year: int):
    """
    東京都オープンデータのCSVを読み込む
    
    Args:
        csv_path: CSVファイルパス
        year: 対象年（西暦）
    """
    logger.info(f'📂 読み込み: {csv_path}')
    
    # エンコーディングを試す
    encodings = ['cp932', 'shift-jis', 'utf-8']
    df = None
    
    # 2021-2023年はタイトル行なし、それ以外はタイトル行あり
    skiprows = 0 if 2021 <= year <= 2023 else 1
    
    for enc in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=enc, skiprows=skiprows)
            logger.info(f'✅ 読み込み成功（{enc}）: {len(df)} 件')
            logger.info(f'   年度: {year}, skiprows: {skiprows}')
            break
        except Exception as e:
            continue
    
    if df is None:
        logger.error('❌ CSVの読み込みに失敗')
        return None
    
    logger.info(f'カラム: {df.columns.tolist()[:10]}...')
    
    return df

def parse_tokyo_data(df: pd.DataFrame, year: int):
    """
    東京都CSVを統一フォーマットに変換
    """
    records = []
    
    # カラム名のマッピング（年度によって微妙に違う）
    col_mapping = {
        '都道府県市区町村コード': 'city_code',
        '区市町村名': 'city_name',
        '地番': 'address',
        '住居表示': 'residential_address',
        '当年価格（円）': 'current_price',
        '当年価格': 'current_price',
        '対前年変動率（％）': 'yoy_change',
        '対前年変動率（％）': 'yoy_change',
        '用途区分': 'land_type',
        '法規制・用途区分': 'land_type',
    }
    
    # 世田谷区のみ抽出（13112）
    if '都道府県市区町村コード' in df.columns:
        df = df[df['都道府県市区町村コード'] == 13112].copy()
    elif '標準地番号（都道府県市区町村コード）' in df.columns:
        df = df[df['標準地番号（都道府県市区町村コード）'] == 13112].copy()
    
    logger.info(f'世田谷区のデータ: {len(df)} 件')
    
    for idx, row in df.iterrows():
        try:
            # 価格
            if '当年価格（円）' in df.columns:
                price = clean_price(row['当年価格（円）'])
            elif '当年価格' in df.columns:
                price = clean_price(row['当年価格'])
            else:
                logger.warning(f'価格カラムが見つかりません')
                continue
            
            if price is None or price == 0:
                continue
            
            # 変動率
            if '対前年変動率（％）' in df.columns:
                yoy_change = row['対前年変動率（％）']
            elif '対前年変動率' in df.columns:
                yoy_change = row['対前年変動率']
            else:
                yoy_change = None
            
            # 住所
            if '地番' in df.columns:
                address = row['地番']
            elif '所在並びに地番' in df.columns:
                address = row['所在並びに地番']
            else:
                address = ''
            
            # 用途
            if '用途区分' in df.columns:
                land_type_raw = row['用途区分']
            elif '法規制・用途区分' in df.columns:
                land_type_raw = row['法規制・用途区分']
            else:
                land_type_raw = ''
            
            # 用途区分を標準化
            land_type = '不明'
            if pd.notna(land_type_raw):
                land_type_str = str(land_type_raw)
                if '住宅' in land_type_str or '低層' in land_type_str:
                    land_type = '住宅地'
                elif '商業' in land_type_str:
                    land_type = '商業地'
                elif '工業' in land_type_str:
                    land_type = '工業地'
            
            record = {
                'choume_code': 'UNKNOWN',  # 後で住所から抽出
                'survey_year': year,
                'land_type': land_type,
                'official_price': price,
                'year_on_year_change': yoy_change if pd.notna(yoy_change) else None,
                'data_source': 'tokyo_opendata',
                'original_address': str(address) if pd.notna(address) else '',
                'latitude': None,
                'longitude': None,
                'created_at': date.today()
            }
            
            records.append(record)
            
        except Exception as e:
            logger.warning(f'行 {idx} の処理エラー: {e}')
            continue
    
    logger.info(f'✅ 変換完了: {len(records)} 件')
    return records

def insert_to_db(records: list):
    """
    データベースにインポート
    """
    if not records:
        logger.warning('インポートするデータがありません')
        return
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    insert_query = """
        INSERT INTO land_prices (
            choume_code, survey_year, land_type, official_price,
            year_on_year_change, data_source, original_address,
            latitude, longitude, created_at
        ) VALUES (
            %(choume_code)s, %(survey_year)s, %(land_type)s, %(official_price)s,
            %(year_on_year_change)s, %(data_source)s, %(original_address)s,
            %(latitude)s, %(longitude)s, %(created_at)s
        )
        ON CONFLICT (choume_code, survey_year, land_type, data_source, original_address)
        DO UPDATE SET
            official_price = EXCLUDED.official_price,
            year_on_year_change = EXCLUDED.year_on_year_change,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude
    """
    
    success_count = 0
    error_count = 0
    
    for record in records:
        try:
            cursor.execute(insert_query, record)
            success_count += 1
        except Exception as e:
            logger.error(f'インポートエラー: {e}')
            logger.error(f'データ: {record}')
            error_count += 1
            conn.rollback()
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    logger.info(f'✅ インポート完了: 成功 {success_count} 件、エラー {error_count} 件')

def main():
    # ログファイルの設定
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f'import_tokyo_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # 既存のハンドラーを削除してから新しいハンドラーを追加
    logger.remove()
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO",
        encoding="utf-8"
    )
    logger.add(
        lambda msg: print(msg, end=""),  # コンソールにも出力
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO"
    )
    
    logger.info('=' * 60)
    logger.info('東京都オープンデータ インポート')
    logger.info(f'ログファイル: {log_file}')
    logger.info('=' * 60)
    
    # 8年分をインポート
    years = [
        (2025, 'tokyo_land_price_2025.csv'),
        (2024, 'tokyo_land_price_2024.csv'),
        (2023, 'tokyo_land_price_2023.csv'),
        (2022, 'tokyo_land_price_2022.csv'),
        (2021, 'tokyo_land_price_2021.csv'),
        (2020, 'tokyo_land_price_2020.csv'),
        (2019, 'tokyo_land_price_2019.csv'),
        (2018, 'tokyo_land_price_2018.csv'),
    ]
    
    base_dir = Path('data/raw/prefecture/tokyo')
    
    for year, filename in years:
        logger.info(f'\n--- {year}年 ---')
        csv_path = base_dir / filename
        
        if not csv_path.exists():
            logger.warning(f'⚠️  ファイルが見つかりません: {csv_path}')
            continue
        
        # CSVを読み込み
        df = load_tokyo_csv(csv_path, year)
        if df is None:
            continue
        
        # データをパース
        records = parse_tokyo_data(df, year)
        
        # DBに投入
        insert_to_db(records)
    
    logger.info('\n' + '=' * 60)
    logger.info('すべての処理が完了しました')
    logger.info('=' * 60)

if __name__ == '__main__':
    main()