#!/usr/bin/env python3
"""
三軒茶屋2丁目のデータを確認するスクリプト
記事の数字とDBの数字が一致しているかチェック
"""

import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path

# .envファイル読み込み
load_dotenv()

def check_sancha_data():
    """三軒茶屋2丁目のデータ確認"""
    
    # PostgreSQL接続
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="real_estate_dev",
        user="postgres",
        password=os.getenv("DB_PASSWORD", "postgres")
    )
    
    cur = conn.cursor()
    
    print("=" * 60)
    print("三軒茶屋2丁目のデータ確認")
    print("=" * 60)
    
    # 1. 全年度のデータを取得
    cur.execute("""
        SELECT 
            survey_year as 年度,
            official_price as 地価,
            year_on_year_change as 変動率,
            land_use as 用途地域,
            building_coverage_ratio as 建蔽率,
            floor_area_ratio as 容積率,
            road_direction as 前面道路方位,
            road_width as 前面道路幅員,
            land_area as 地積,
            original_address as 住所
        FROM land_prices
        WHERE original_address LIKE '%三軒茶屋２%'
           OR original_address LIKE '%三軒茶屋2%'
        ORDER BY survey_year DESC
    """)
    
    rows = cur.fetchall()
    
    if not rows:
        print("❌ データが見つかりません")
        print("住所マッチングに問題がある可能性があります")
        cur.close()
        conn.close()
        return
    
    print(f"\n【取得件数】: {len(rows)}件\n")
    
    # 2. 各年度のデータを表示
    print("【年度別データ】")
    print("-" * 60)
    for row in rows:
        print(f"年度: {row[0]}")
        print(f"  地価: {row[1]:,}円/㎡")
        print(f"  変動率: {row[2]}%")
        print(f"  用途地域: {row[3]}")
        print(f"  建蔽率: {row[4]}%")
        print(f"  容積率: {row[5]}%")
        print(f"  前面道路: {row[6]} {row[7]}m")
        print(f"  地積: {row[8]}㎡")
        print(f"  住所: {row[9]}")
        print("-" * 60)
    
    # 3. 5年変動率を計算
    cur.execute("""
        WITH prices AS (
            SELECT 
                survey_year,
                official_price
            FROM land_prices
            WHERE original_address LIKE '%三軒茶屋２%'
               OR original_address LIKE '%三軒茶屋2%'
        )
        SELECT 
            MAX(CASE WHEN survey_year = 2025 THEN official_price END) as 地価_2025,
            MAX(CASE WHEN survey_year = 2021 THEN official_price END) as 地価_2021,
            ROUND(
                (MAX(CASE WHEN survey_year = 2025 THEN official_price END) - 
                 MAX(CASE WHEN survey_year = 2021 THEN official_price END)) * 100.0 / 
                 MAX(CASE WHEN survey_year = 2021 THEN official_price END),
                1
            ) as 変動率_5年
        FROM prices
    """)
    
    result = cur.fetchone()
    print("\n【5年変動率の計算】")
    print(f"  2025年: {result[0]:,}円/㎡")
    print(f"  2021年: {result[1]:,}円/㎡")
    print(f"  変動率: +{result[2]}%")
    
    # 4. 世田谷区平均を計算
    cur.execute("""
        SELECT 
            ROUND(AVG(official_price)) as 世田谷区平均
        FROM land_prices
        WHERE survey_year = 2025
          AND choume_code LIKE '13112%'
    """)
    
    avg_price = cur.fetchone()[0]
    print("\n【世田谷区平均（2025年）】")
    print(f"  平均地価: {avg_price:,}円/㎡")
    
    # 5. 記事の数字と比較
    print("\n" + "=" * 60)
    print("【記事との照合】")
    print("=" * 60)
    
    article_data = {
        "地価": 1440000,
        "5年変動率": 25.2,
        "用途地域": "1住居",
        "建蔽率": 60,
        "容積率": 300,
        "前面道路方位": "西",
        "前面道路幅員": 8.0,
        "地積": 1698,
        "世田谷区平均": 719776
    }
    
    # 最新データ（2025年）を取得
    latest = rows[0]
    
    print("\n項目               記事        DB         一致?")
    print("-" * 60)
    print(f"地価           {article_data['地価']:>10,} {latest[1]:>10,}    {'✅' if article_data['地価'] == latest[1] else '❌'}")
    print(f"5年変動率      {article_data['5年変動率']:>10} {result[2]:>10}    {'✅' if abs(article_data['5年変動率'] - result[2]) < 0.1 else '❌'}")
    print(f"用途地域       {article_data['用途地域']:>10} {latest[3]:>10}    {'✅' if article_data['用途地域'] == latest[3] else '❌'}")
    print(f"建蔽率         {article_data['建蔽率']:>10} {latest[4]:>10}    {'✅' if article_data['建蔽率'] == latest[4] else '❌'}")
    print(f"容積率         {article_data['容積率']:>10} {latest[5]:>10}    {'✅' if article_data['容積率'] == latest[5] else '❌'}")
    print(f"前面道路方位   {article_data['前面道路方位']:>10} {latest[6]:>10}    {'✅' if article_data['前面道路方位'] == latest[6] else '❌'}")
    print(f"前面道路幅員   {article_data['前面道路幅員']:>10} {latest[7]:>10}    {'✅' if abs(article_data['前面道路幅員'] - float(latest[7])) < 0.1 else '❌'}")
    print(f"地積           {article_data['地積']:>10} {latest[8]:>10}    {'✅' if article_data['地積'] == latest[8] else '❌'}")
    print(f"世田谷区平均   {article_data['世田谷区平均']:>10,} {avg_price:>10,}    {'✅' if abs(article_data['世田谷区平均'] - avg_price) < 1000 else '❌'}")
    
    print("\n" + "=" * 60)
    
    # すべて一致しているかチェック
    all_match = (
        article_data['地価'] == latest[1] and
        abs(article_data['5年変動率'] - result[2]) < 0.1 and
        article_data['用途地域'] == latest[3] and
        article_data['建蔽率'] == latest[4] and
        article_data['容積率'] == latest[5] and
        article_data['前面道路方位'] == latest[6] and
        abs(article_data['前面道路幅員'] - float(latest[7])) < 0.1 and
        article_data['地積'] == latest[8] and
        abs(article_data['世田谷区平均'] - avg_price) < 1000
    )
    
    if all_match:
        print("✅ すべてのデータが一致しています！")
        print("記事の数字は正しくDBから取得されています。")
    else:
        print("❌ 一部のデータが一致していません")
        print("LandPriceCollectorまたはContentGeneratorに問題がある可能性があります")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    try:
        check_sancha_data()
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()