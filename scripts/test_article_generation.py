import psycopg2
from pathlib import Path

config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'real_estate_dev',
    'user': 'postgres',
    'password': 'postgres'
}

# サンプル住所
sample_address = '松原５丁目１６８番４０'

conn = psycopg2.connect(**config)
cursor = conn.cursor()

# 5年分のデータ取得
cursor.execute('''
    SELECT survey_year, official_price, year_on_year_change
    FROM land_prices
    WHERE original_address LIKE %s
    ORDER BY survey_year
''', (f'{sample_address}%',))

data = cursor.fetchall()

if not data:
    print(f'❌ データが見つかりません: {sample_address}')
    cursor.close()
    conn.close()
    exit(1)

# 簡易記事生成
latest = data[-1]
oldest = data[0]
change_5y = ((latest[1] - oldest[1]) / oldest[1]) * 100

article = f'''
# {sample_address.split('丁目')[0]}丁目の資産価値分析

## 📊 地価推移（過去5年）

最新の地価公示データによると、{sample_address}の2025年の公示地価は**{latest[1]:,}円/㎡**です。

### 5年間の変化
- 2021年: {oldest[1]:,}円/㎡
- 2025年: {latest[1]:,}円/㎡
- **5年間の変動率: {change_5y:+.1f}%**

### 最新の動向（2025年）
前年比で**{latest[2]:+.1f}%**の{'上昇' if latest[2] > 0 else '下降'}となっています。

## 💡 資産価値の評価

この地域は過去5年間で{'安定した上昇' if change_5y > 0 else '下降'}トレンドを示しており、
{'資産価値の保全性が高い' if change_5y > 0 else '慎重な検討が必要な'}エリアと言えます。

---
*データ出典: 東京都オープンデータ（地価公示）*
'''

print(article)

# ファイルに保存
output_dir = Path('output/articles')
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / f'{sample_address.replace("丁目", "").replace("番", "")}_report.md'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(article)

print(f'\n✅ 記事を保存: {output_file}')

cursor.close()
conn.close()

