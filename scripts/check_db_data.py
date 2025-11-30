import psycopg2
from loguru import logger

config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'real_estate_dev',
    'user': 'postgres',
    'password': 'postgres'
}

logger.info('=' * 60)
logger.info('データベース確認')
logger.info('=' * 60)

try:
    conn = psycopg2.connect(**config)
    cursor = conn.cursor()
    
    # 1. データソース別の件数
    logger.info('\n【データソース別件数】')
    cursor.execute('''
        SELECT data_source, COUNT(*) as count
        FROM land_prices
        GROUP BY data_source
        ORDER BY count DESC
    ''')
    sources = cursor.fetchall()
    for source, count in sources:
        logger.info(f'  {source}: {count:,}件')
    
    # 2. 世田谷区のデータ件数
    logger.info('\n【世田谷区データ】')
    cursor.execute('''
        SELECT COUNT(*) 
        FROM land_prices 
        WHERE choume_code LIKE '13112%' OR city_code = '13112'
    ''')
    setagaya_count = cursor.fetchone()[0]
    logger.info(f'  世田谷区: {setagaya_count:,}件')
    
    # 3. 住所データのサンプル（tokyo_opendata）
    logger.info('\n【住所データサンプル（tokyo_opendata）】')
    cursor.execute('''
        SELECT original_address, choume_code, survey_year, official_price
        FROM land_prices 
        WHERE data_source = 'tokyo_opendata'
        LIMIT 10
    ''')
    addresses = cursor.fetchall()
    for addr, choume, year, price in addresses:
        logger.info(f'  {addr[:50]}... | {choume} | {year}年 | {price:,}円/㎡')
    
    # 4. 世田谷区の町丁目一覧
    logger.info('\n【世田谷区の町丁目一覧】')
    cursor.execute('''
        SELECT DISTINCT choume_code, choume_name
        FROM choume
        WHERE city_code = '13112'
        ORDER BY choume_code
    ''')
    choume_list = cursor.fetchall()
    logger.info(f'  町丁目数: {len(choume_list)}件')
    for code, name in choume_list[:20]:  # 最初の20件
        logger.info(f'  {code}: {name}')
    if len(choume_list) > 20:
        logger.info(f'  ... 他 {len(choume_list) - 20} 件')
    
    # 5. UNKNOWNレコードの使用状況
    logger.info('\n【UNKNOWNレコード使用状況】')
    cursor.execute('''
        SELECT COUNT(*) 
        FROM land_prices 
        WHERE choume_code = 'UNKNOWN'
    ''')
    unknown_count = cursor.fetchone()[0]
    logger.info(f'  UNKNOWNレコード使用: {unknown_count:,}件')
    
    # 6. 年度別データ件数
    logger.info('\n【年度別データ件数】')
    cursor.execute('''
        SELECT survey_year, COUNT(*) as count
        FROM land_prices
        GROUP BY survey_year
        ORDER BY survey_year DESC
    ''')
    years = cursor.fetchall()
    for year, count in years:
        logger.info(f'  {year}年: {count:,}件')
    
    # 7. 地価タイプ別件数
    logger.info('\n【地価タイプ別件数】')
    cursor.execute('''
        SELECT land_type, COUNT(*) as count
        FROM land_prices
        GROUP BY land_type
        ORDER BY count DESC
    ''')
    types = cursor.fetchall()
    for land_type, count in types:
        logger.info(f'  {land_type}: {count:,}件')
    
    cursor.close()
    conn.close()
    
    logger.info('\n' + '=' * 60)
    logger.info('確認完了')
    logger.info('=' * 60)
    
except Exception as e:
    logger.error(f'❌ エラー: {e}')
    import traceback
    traceback.print_exc()

