#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
choumeテーブルにareas.csvからデータを投入するスクリプト

実装仕様:
- areas.csvから町丁目データを読み込み
- choumeテーブルに投入
- choume_codeは自動生成（city_code + 連番）
"""

import pandas as pd
import psycopg2
import os
import sys
import hashlib
from pathlib import Path
from dotenv import load_dotenv
import logging
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/real_estate_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_db_config():
    """データベース設定を読み込み"""
    config_path = project_root / 'config' / 'database.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return {
        'host': os.getenv('DB_HOST', config['postgresql'].get('host', 'localhost')),
        'port': int(os.getenv('DB_PORT', config['postgresql'].get('port', 5432))),
        'database': os.getenv('DB_NAME', config['postgresql'].get('database', 'real_estate_dev')),
        'user': os.getenv('DB_USER', config['postgresql'].get('user', 'postgres')),
        'password': os.getenv('DB_PASSWORD', config['postgresql'].get('password', 'postgres'))
    }


def normalize_choume_name(choume_with_suffix):
    """
    「三軒茶屋1丁目」→「三軒茶屋1」に変換
    
    Args:
        choume_with_suffix: 丁目付きの町丁目名
    
    Returns:
        str: 丁目なしの町丁目名
    """
    if not choume_with_suffix or not isinstance(choume_with_suffix, str):
        return ""
    
    # 「丁目」を削除
    normalized = choume_with_suffix.replace('丁目', '')
    
    # 全角数字を半角に変換
    trans_table = str.maketrans('０１２３４５６７８９', '0123456789')
    normalized = normalized.translate(trans_table)
    
    return normalized.strip()


def generate_choume_code(city_code, choume_name, index):
    """
    choume_codeを生成（11桁）
    フォーマット: {city_code(5桁)}{連番(6桁)}
    
    Args:
        city_code: 市区町村コード（5桁）
        choume_name: 町丁目名
        index: 連番（0から開始）
    
    Returns:
        str: 11桁のchoume_code
    """
    # city_codeは5桁、残り6桁で連番を生成
    # 連番は1から開始して6桁ゼロ埋め
    seq_num = str(index + 1).zfill(6)
    choume_code = f"{city_code}{seq_num}"
    
    return choume_code


def main():
    """メイン処理"""
    # 1. 環境変数読み込み
    load_dotenv()
    
    # 2. PostgreSQL接続
    db_config = load_db_config()
    conn = psycopg2.connect(**db_config)
    
    try:
        cursor = conn.cursor()
        
        # 3. areas.csv読み込み
        csv_path = project_root / 'projects' / 'setagaya_real_estate' / 'data' / 'areas.csv'
        logger.info("=" * 60)
        logger.info("=== CSV読み込み ===")
        logger.info(f"ファイル: {csv_path}")
        
        if not csv_path.exists():
            logger.error(f"❌ CSVファイルが見つかりません: {csv_path}")
            return
        
        df = pd.read_csv(csv_path, encoding='utf-8')
        logger.info(f"総行数: {len(df)}件")
        logger.info(f"列名: {df.columns.tolist()}")
        
        # 4. 世田谷区のcity_codeを取得
        logger.info(f"\n=== 世田谷区の確認 ===")
        cursor.execute("""
            SELECT city_code, city_name
            FROM cities
            WHERE city_name = '世田谷区' OR city_name LIKE '%世田谷%'
            LIMIT 1
        """)
        
        city_result = cursor.fetchone()
        
        if not city_result:
            logger.warning("⚠️ citiesテーブルに世田谷区が見つかりません")
            logger.info("世田谷区をcitiesテーブルに追加します...")
            
            # 東京都のprefecture_codeを取得
            cursor.execute("""
                SELECT prefecture_code FROM prefectures 
                WHERE prefecture_name = '東京都' OR prefecture_name = 'Tokyo'
                LIMIT 1
            """)
            prefecture_result = cursor.fetchone()
            
            if not prefecture_result:
                logger.error("❌ prefecturesテーブルに東京都がありません")
                logger.info("まず東京都をprefecturesテーブルに追加してください")
                return
            
            prefecture_code = prefecture_result[0]
            city_code = '13112'  # 世田谷区のコード
            
            # 世田谷区を追加
            cursor.execute("""
                INSERT INTO cities (city_code, prefecture_code, city_name, city_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (city_code) DO NOTHING
                RETURNING city_code, city_name
            """, (city_code, prefecture_code, '世田谷区', '区'))
            
            result = cursor.fetchone()
            if result:
                conn.commit()
                logger.info(f"✅ 世田谷区を追加しました（city_code: {result[0]}, name: {result[1]}）")
                city_code = result[0]
                city_name = result[1]
            else:
                # 既に存在していた場合
                cursor.execute("SELECT city_code, city_name FROM cities WHERE city_code = %s", (city_code,))
                city_result = cursor.fetchone()
                city_code = city_result[0]
                city_name = city_result[1]
        else:
            city_code = city_result[0]
            city_name = city_result[1]
            logger.info(f"✅ 世田谷区が見つかりました（city_code: {city_code}, name: {city_name}）")
        
        # 5. 町丁目名を正規化
        logger.info(f"\n=== 町丁目名の正規化 ===")
        logger.info(f"元の列名: choume")
        logger.info(f"サンプル（元）: {df['choume'].head(5).tolist()}")
        
        # 正規化（丁目を削除）
        df['choume_normalized'] = df['choume'].apply(normalize_choume_name)
        
        logger.info(f"サンプル（変換後）: {df['choume_normalized'].head(5).tolist()}")
        
        # 重複を削除
        df_unique = df.drop_duplicates(subset=['choume_normalized'])
        logger.info(f"重複削除後: {len(df_unique)}件（元: {len(df)}件）")
        
        # 6. 既存データを確認（削除はしない）
        logger.info(f"\n=== 既存データの確認 ===")
        cursor.execute("""
            SELECT COUNT(*) FROM choume WHERE city_code = %s
        """, (city_code,))
        existing_count = cursor.fetchone()[0]
        logger.info(f"既存の町丁目データ: {existing_count}件")
        
        if existing_count > 0:
            # サンプル表示のみ
            cursor.execute("""
                SELECT choume_code, choume_name FROM choume 
                WHERE city_code = %s
                ORDER BY choume_code
                LIMIT 5
            """, (city_code,))
            logger.info(f"既存データサンプル:")
            for row in cursor.fetchall():
                logger.info(f"  {row[0]} -> {row[1]}")
        
        logger.info(f"\n⚠️ 既存データは削除せず、新規データのみ追加します")
        logger.info(f"   理由: land_pricesテーブルとの外部キー制約があるため")
        
        # 7. データ投入
        logger.info(f"\n=== データ投入開始 ===")
        inserted_count = 0
        skipped_count = 0
        updated_count = 0
        
        # choume_nameでソートして一貫性のある連番を生成
        df_unique_sorted = df_unique.sort_values('choume_normalized').reset_index(drop=True)
        
        for idx, row in df_unique_sorted.iterrows():
            choume_name = row['choume_normalized']
            
            if not choume_name or choume_name.strip() == '':
                skipped_count += 1
                continue
            
            # choume_codeを生成
            choume_code = generate_choume_code(city_code, choume_name, idx)
            
            try:
                cursor.execute("""
                    INSERT INTO choume (choume_code, city_code, choume_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (choume_code) DO UPDATE SET
                        choume_name = EXCLUDED.choume_name,
                        city_code = EXCLUDED.city_code
                """, (choume_code, city_code, choume_name))
                
                if cursor.rowcount > 0:
                    if cursor.rowcount == 1:
                        inserted_count += 1
                    else:
                        updated_count += 1
                    
                    if inserted_count <= 10:
                        logger.info(f"  ✅ {inserted_count:3d}. {choume_code} -> {choume_name}")
                else:
                    skipped_count += 1
                    
            except Exception as e:
                logger.warning(f"⚠️ {choume_name} の投入に失敗: {e}")
                skipped_count += 1
        
        conn.commit()
        
        if inserted_count > 10:
            logger.info(f"  ... 他 {inserted_count - 10} 件")
        
        # 8. 投入結果の確認
        logger.info(f"\n=== 投入完了 ===")
        logger.info(f"新規投入: {inserted_count}件")
        if updated_count > 0:
            logger.info(f"更新: {updated_count}件")
        logger.info(f"スキップ: {skipped_count}件")
        
        cursor.execute("""
            SELECT COUNT(*) FROM choume WHERE city_code = %s
        """, (city_code,))
        final_count = cursor.fetchone()[0]
        logger.info(f"最終件数: {final_count}件（既存{existing_count}件 + 新規{inserted_count}件）")
        
        # サンプル表示
        logger.info(f"\n投入データ（最初の20件）:")
        cursor.execute("""
            SELECT choume_code, choume_name FROM choume 
            WHERE city_code = %s
            ORDER BY choume_name
            LIMIT 20
        """, (city_code,))
        
        for row in cursor.fetchall():
            logger.info(f"  {row[0]} -> {row[1]}")
        
        # 9. UNIQUE制約の確認
        logger.info(f"\n=== UNIQUE制約の確認 ===")
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'choume' AND constraint_type = 'UNIQUE'
        """)
        constraints = cursor.fetchall()
        
        if constraints:
            logger.info(f"✅ UNIQUE制約が設定されています:")
            for c in constraints:
                logger.info(f"  - {c[0]} ({c[1]})")
        else:
            logger.warning("⚠️ UNIQUE制約が設定されていません")
        
        # 10. 「丁目」が残っていないか確認
        try:
            if not city_code:
                logger.warning("⚠️ city_codeが定義されていません。スキップします。")
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM choume 
                    WHERE city_code = %s AND choume_name LIKE '%%丁目%%'
                """, (city_code,))
                result = cursor.fetchone()
                with_choume_count = result[0] if result and len(result) > 0 else 0
            
                if with_choume_count > 0:
                    logger.warning(f"⚠️ 「丁目」を含むレコードが{with_choume_count}件あります")
                    cursor.execute("""
                        SELECT choume_code, choume_name FROM choume 
                        WHERE city_code = %s AND choume_name LIKE '%%丁目%%'
                        LIMIT 5
                    """, (city_code,))
                    logger.info("該当レコード:")
                    for row in cursor.fetchall():
                        logger.info(f"  {row[0]} -> {row[1]}")
                else:
                    logger.info("✅ 「丁目」を含むレコードはありません")
        except Exception as e:
            logger.warning(f"⚠️ 「丁目」チェック中にエラーが発生しました: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        logger.info("\n" + "=" * 60)
        logger.info("=== 処理完了 ===")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {e}", exc_info=True)
        conn.rollback()
        
    finally:
        conn.close()


if __name__ == '__main__':
    main()

