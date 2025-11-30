import psycopg2
import json
from pathlib import Path

config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'real_estate_dev',
    'user': 'postgres',
    'password': 'postgres'
}

conn = psycopg2.connect(**config)
cursor = conn.cursor()

# サンプル：1つの住所の5年推移を取得
sample_address = '松原５丁目１６８番４０'

cursor.execute('''
    SELECT survey_year, official_price, year_on_year_change
    FROM land_prices
    WHERE original_address LIKE %s
    ORDER BY survey_year
''', (f'{sample_address}%',))

data = cursor.fetchall()

print(f'📊 {sample_address} の推移')
print('=' * 50)
for year, price, change in data:
    print(f'{year}年: {price:,}円 (前年比: {change}%)')

# グラフデータJSON生成
graph_data = {
    'type': 'line',
    'data': {
        'labels': [str(row[0]) for row in data],
        'datasets': [{
            'label': sample_address,
            'data': [row[1] for row in data],
            'borderColor': '#4CAF50',
            'tension': 0.1
        }]
    },
    'options': {
        'responsive': True,
        'plugins': {
            'title': {
                'display': True,
                'text': '地価推移（5年間）'
            }
        }
    }
}

print('\n✅ グラフデータJSON:')
print(json.dumps(graph_data, indent=2, ensure_ascii=False))

cursor.close()
conn.close()

