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

# UNKNOWNレコードを追加
cursor.execute('''
    INSERT INTO choume (choume_code, city_code, choume_name, latitude, longitude)
    VALUES ('UNKNOWN', '13112', '住所未確定', NULL, NULL)
    ON CONFLICT (choume_code) DO NOTHING
''')

conn.commit()
cursor.close()
conn.close()

print('✅ UNKNOWNレコード追加完了')

