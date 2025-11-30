import psycopg2

config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'real_estate_dev',
    'user': 'postgres',
    'password': 'postgres'
}

conn = psycopg2.connect(**config)
cursor = conn.cursor()

print('ユニーク制約を修正します...')

# 既存の制約を削除
cursor.execute('ALTER TABLE land_prices DROP CONSTRAINT IF EXISTS unique_land_price')
print('✅ 既存の制約を削除')

# 新しい制約を追加（original_addressを含める）
cursor.execute('''
    ALTER TABLE land_prices 
    ADD CONSTRAINT unique_land_price 
    UNIQUE (choume_code, survey_year, land_type, data_source, original_address)
''')
print('✅ 新しい制約を追加（original_addressを含む）')

conn.commit()
cursor.close()
conn.close()

print('✅ 完了')

