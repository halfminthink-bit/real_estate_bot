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
print('世田谷区 地価統計サマリー')
print('=' * 60)

# 2025年の平均価格
cursor.execute('''
    SELECT 
        COUNT(*) as cnt,
        AVG(official_price) as avg_price,
        MIN(official_price) as min_price,
        MAX(official_price) as max_price
    FROM land_prices
    WHERE survey_year = 2025
''')
row = cursor.fetchone()
print(f'\n【2025年】')
print(f'  地点数: {row[0]} 件')
print(f'  平均価格: {int(row[1]):,} 円/㎡')
print(f'  最低価格: {int(row[2]):,} 円/㎡')
print(f'  最高価格: {int(row[3]):,} 円/㎡')

# 5年間の平均変動率
cursor.execute('''
    SELECT AVG(year_on_year_change)
    FROM land_prices
    WHERE year_on_year_change IS NOT NULL
''')
avg_change = cursor.fetchone()[0]
print(f'\n【5年平均変動率】')
print(f'  {float(avg_change):.2f}%')

# 上昇トレンドの地点数 vs 下降トレンドの地点数
cursor.execute('''
    SELECT 
        CASE 
            WHEN year_on_year_change > 0 THEN '上昇'
            WHEN year_on_year_change < 0 THEN '下降'
            ELSE '横ばい'
        END as trend,
        COUNT(*) as cnt
    FROM land_prices
    WHERE survey_year = 2025 AND year_on_year_change IS NOT NULL
    GROUP BY trend
''')
print(f'\n【2025年のトレンド】')
for trend, cnt in cursor.fetchall():
    print(f'  {trend}: {cnt} 件')

cursor.close()
conn.close()

print('\n' + '=' * 60)

