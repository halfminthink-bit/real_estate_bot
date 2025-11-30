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

print('=' * 60)
print('地価データ確認')
print('=' * 60)

# 総件数
cursor.execute('SELECT COUNT(*) FROM land_prices')
total = cursor.fetchone()[0]
print(f'\n✅ 総件数: {total} 件')

# 年度別件数
cursor.execute('''
    SELECT survey_year, COUNT(*) as cnt
    FROM land_prices
    GROUP BY survey_year
    ORDER BY survey_year DESC
''')
print(f'\n【年度別件数】')
for row in cursor.fetchall():
    print(f'  {row[0]}年: {row[1]} 件')

# choume_code別件数
cursor.execute('''
    SELECT choume_code, COUNT(*) as cnt
    FROM land_prices
    GROUP BY choume_code
    ORDER BY cnt DESC
    LIMIT 10
''')
print(f'\n【choume_code別件数（上位10件）】')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} 件')

# サンプルデータ（最新5件）
cursor.execute('''
    SELECT id, survey_year, land_type, official_price, 
           year_on_year_change, original_address, choume_code
    FROM land_prices
    ORDER BY survey_year DESC, id DESC
    LIMIT 5
''')
print(f'\n【サンプルデータ（最新5件）】')
for row in cursor.fetchall():
    print(f'  ID:{row[0]} {row[1]}年 {row[2]} {row[3]:,}円 変動率:{row[4]}% choume:{row[6]}')
    print(f'    住所: {row[5][:50]}...')

# UNIQUEな組み合わせを確認
cursor.execute('''
    SELECT COUNT(DISTINCT choume_code || survey_year::text || land_type || data_source)
    FROM land_prices
''')
unique_count = cursor.fetchone()[0]
print(f'\n✅ ユニークな組み合わせ: {unique_count} 件')

cursor.close()
conn.close()

print('\n' + '=' * 60)

