import psycopg2
from loguru import logger

config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'real_estate_dev',
    'user': 'postgres',
    'password': 'postgres'
}

logger.info('マスタデータ投入開始')

conn = psycopg2.connect(**config)
cursor = conn.cursor()

# 都道府県マスタ
cursor.execute('''
    INSERT INTO prefectures (prefecture_code, prefecture_name, prefecture_name_en)
    VALUES ('13', '東京都', 'Tokyo')
    ON CONFLICT (prefecture_code) DO NOTHING
''')
logger.info('✅ 都道府県マスタ投入完了')

# 市区町村マスタ（世田谷区）
cursor.execute('''
    INSERT INTO cities (city_code, prefecture_code, city_name, city_name_kana, city_type)
    VALUES ('13112', '13', '世田谷区', 'せたがやく', '区')
    ON CONFLICT (city_code) DO NOTHING
''')
logger.info('✅ 市区町村マスタ投入完了')

conn.commit()

# 確認
cursor.execute('SELECT COUNT(*) FROM prefectures')
pref_count = cursor.fetchone()[0]
logger.info(f'都道府県: {pref_count}件')

cursor.execute('SELECT COUNT(*) FROM cities')
city_count = cursor.fetchone()[0]
logger.info(f'市区町村: {city_count}件')

cursor.close()
conn.close()

logger.info('✅ マスタデータ投入完了')

