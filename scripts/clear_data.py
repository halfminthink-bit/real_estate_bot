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

cursor.execute('DELETE FROM land_prices')
deleted_count = cursor.rowcount
conn.commit()

print(f'✅ 削除完了: {deleted_count} 件')

cursor.close()
conn.close()

