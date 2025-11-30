#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
データベースの現状確認スクリプト
"""

import psycopg2
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'real_estate_bot'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    print("=" * 60)
    print("=== データベース状況確認 ===")
    print("=" * 60)
    
    # 1. 年度確認
    print("\n【1】既存データの年度")
    cursor.execute("SELECT DISTINCT survey_year FROM land_prices ORDER BY survey_year")
    years = [row[0] for row in cursor.fetchall()]
    
    if years:
        print(f"  年度範囲: {min(years)}年 〜 {max(years)}年")
        print(f"  年度一覧: {', '.join(map(str, years))}")
    else:
        print("  データなし")
    
    # 2. 年度別件数
    print("\n【2】年度別データ件数")
    cursor.execute("""
        SELECT survey_year, COUNT(*) as count
        FROM land_prices
        GROUP BY survey_year
        ORDER BY survey_year
    """)
    
    total = 0
    for row in cursor.fetchall():
        print(f"  {row[0]}年: {row[1]:3d}件")
        total += row[1]
    
    print(f"  ─────────────")
    print(f"  合計: {total}件")
    
    # 3. choumeテーブル
    print("\n【3】町丁目マスタ")
    cursor.execute("SELECT COUNT(*) FROM choume")
    choume_count = cursor.fetchone()[0]
    print(f"  登録町丁目数: {choume_count}件")
    
    # 4. サンプルデータ
    print("\n【4】最新データのサンプル（3件）")
    cursor.execute("""
        SELECT survey_year, choume_code, price_per_sqm, land_use, building_coverage_ratio, floor_area_ratio
        FROM land_prices
        ORDER BY survey_year DESC, id DESC
        LIMIT 3
    """)
    
    print("  年度 | choume_code  | 地価(円/㎡) | 用途地域 | 建蔽率 | 容積率")
    print("  " + "-" * 70)
    for row in cursor.fetchall():
        year = row[0]
        choume_code = row[1] or "None"
        price = f"{row[2]:,}" if row[2] else "None"
        land_use = row[3] or "None"
        coverage = row[4] or "None"
        floor = row[5] or "None"
        print(f"  {year} | {choume_code:12s} | {price:>11s} | {land_use:8s} | {coverage:>6s} | {floor:>6s}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("確認完了")
    print("=" * 60)

if __name__ == '__main__':
    main()