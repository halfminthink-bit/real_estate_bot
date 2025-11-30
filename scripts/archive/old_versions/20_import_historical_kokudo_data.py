#!/usr/bin/env python3
"""
国土数値情報（地価公示）Shapefile/GeoJSON → PostgreSQL インポートスクリプト

2000-2025年の26年分の国土数値情報（地価公示）データを
PostgreSQLのland_pricesテーブルにインポートします。

Usage:
    python scripts/20_import_historical_kokudo_data.py                    # 全年度処理
    python scripts/20_import_historical_kokudo_data.py --year 2000       # 単年度処理
    python scripts/20_import_historical_kokudo_data.py --start 2018 --end 2025  # 範囲指定
"""

import geopandas as gpd
import pandas as pd
import psycopg2
from pathlib import Path
from tqdm import tqdm
import os
import sys
import re
import logging
import argparse
from typing import Optional, Tuple, List
from dotenv import load_dotenv
import yaml

# 環境変数を読み込み
load_dotenv()

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ログ設定
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


def get_file_path(year: int) -> Optional[str]:
    """
    年度に応じて正しいファイルパスを返す
    
    Args:
        year: 調査年（2000-2025）
    
    Returns:
        str: ファイルパス（.shp または .geojson）、存在しない場合はNone
    
    Raises:
        FileNotFoundError: ファイルが存在しない場合
    """
    base_dir = project_root / 'data' / 'raw' / 'national' / 'kokudo_suuchi'
    year_dir = base_dir / f"{year}_13"
    
    if not year_dir.exists():
        return None
    
    yy = str(year)[-2:]  # 下2桁（例: 2000 -> "00"）
    
    # 2018年以降: GeoJSONを優先的に使用
    if year >= 2018:
        # GMLフォルダ内のGeoJSONを優先
        gml_dir = year_dir / f"L01-{yy}_13_GML"
        if gml_dir.exists():
            geojson_path = gml_dir / f"L01-{yy}_13.geojson"
            if geojson_path.exists():
                return str(geojson_path)
        
        # 直接GeoJSON（GMLフォルダなし、例: 2022年）
        geojson_path = year_dir / f"L01-{yy}_13.geojson"
        if geojson_path.exists():
            return str(geojson_path)
        
        # GMLフォルダ内のShapefile（フォールバック）
        if gml_dir.exists():
            shp_path = gml_dir / f"L01-{yy}_13.shp"
            if shp_path.exists():
                return str(shp_path)
        
        # 直接Shapefile（フォールバック）
        shp_path = year_dir / f"L01-{yy}_13.shp"
        if shp_path.exists():
            return str(shp_path)
    
    # 2015-2017年: GMLフォルダ内のShapefileまたは直接Shapefile
    elif year >= 2015:
        # 2015年はGMLフォルダ内
        if year == 2015:
            gml_dir = year_dir / f"L01-{yy}_13_GML"
            if gml_dir.exists():
                shp_path = gml_dir / f"L01-{yy}_13.shp"
                if shp_path.exists():
                    return str(shp_path)
        else:
            # 2016-2017年は直接Shapefile
            shp_path = year_dir / f"L01-{yy}_13.shp"
            if shp_path.exists():
                return str(shp_path)
    
    # 2012-2014年: 中間形式（直接Shapefile）
    elif year >= 2012:
        shp_path = year_dir / f"L01-{yy}_13.shp"
        if shp_path.exists():
            return str(shp_path)
    
    # 2000-2011年: 古い形式（-g_LandPrice.shp）
    else:
        shp_path = year_dir / f"L01-{yy}_13-g_LandPrice.shp"
        if shp_path.exists():
            return str(shp_path)
    
    return None


def load_land_price_data(year: int, debug: bool = False) -> Optional[gpd.GeoDataFrame]:
    """
    任意の年のデータを統一形式で読み込む
    
    Args:
        year: 調査年（2000-2025）
    
    Returns:
        GeoDataFrame: 地価データ + ジオメトリ、読み込み失敗時はNone
    """
    file_path = get_file_path(year)
    
    if file_path is None:
        logger.warning(f"⚠️ {year}年のファイルが見つかりません")
        return None
    
    if not Path(file_path).exists():
        logger.warning(f"⚠️ ファイルが存在しません: {file_path}")
        return None
    
    try:
        logger.info(f"[{year}年] ファイル読み込み: {file_path}")
        gdf = gpd.read_file(file_path)
        logger.info(f"[{year}年] 総件数: {len(gdf)} 地点")
        
        # デバッグ: データ読み込み直後の詳細出力
        if debug:
            print("\n" + "=" * 60)
            print(f"=== デバッグ: [{year}年] 読み込みデータ ===")
            print(f"列名（最初の30個）: {gdf.columns.tolist()[:30]}")
            print(f"総列数: {len(gdf.columns)}")
            print(f"総件数: {len(gdf)}")
            
            # 市区町村コードの確認
            for col_name in ['L01_001', 'L01_017', 'L01_021']:
                if col_name in gdf.columns:
                    print(f"\n{col_name}（市区町村コード候補）:")
                    sample_values = gdf[col_name].head(10).tolist()
                    print(f"  サンプル値: {sample_values}")
                    
                    # ユニーク値の確認
                    unique_values = gdf[col_name].unique()[:20]
                    print(f"  ユニーク値（最初の20個）: {unique_values.tolist()}")
                    
                    # 世田谷区関連の値を確認
                    if hasattr(gdf[col_name], 'astype'):
                        str_values = gdf[col_name].astype(str)
                        setagaya_count = str_values.str.contains('13112|13', na=False).sum()
                        print(f"  '13'を含む値の件数: {setagaya_count}")
            
            # 住所フィールドの確認
            for col_name in ['L01_019', 'L01_023', 'L01_024', 'L01_025']:
                if col_name in gdf.columns:
                    print(f"\n{col_name}（住所候補）のサンプル:")
                    for i, addr in enumerate(gdf[col_name].head(5), 1):
                        if pd.notna(addr):
                            print(f"  {i}. {str(addr)[:80]}")
        
        # 世田谷区のデータのみフィルタ（市区町村コード: 13112）
        # L01_017が市区町村コード（年度によって位置が異なる可能性があるため、複数パターンを試す）
        city_code_col = None
        
        # まず、各候補列で世田谷区（13112）が存在するか確認
        for col in ['L01_017', 'L01_001', 'L01_021']:
            if col in gdf.columns:
                # 文字列型としてチェック
                str_values = gdf[col].astype(str)
                has_setagaya = (str_values == '13112').any() or (str_values.str.startswith('13112', na=False)).any()
                
                # 数値型としてもチェック
                if not has_setagaya:
                    try:
                        num_values = pd.to_numeric(gdf[col], errors='coerce')
                        has_setagaya = (num_values == 13112).any()
                    except:
                        pass
                
                if has_setagaya:
                    city_code_col = col
                    if debug:
                        print(f"✅ 市区町村コード列として '{col}' を使用")
                    break
        
        if city_code_col:
            # 世田谷区（13112）でフィルタ
            setagaya_gdf = None
            
            # 数値型として処理（13112 = 世田谷区）
            try:
                num_values = pd.to_numeric(gdf[city_code_col], errors='coerce')
                setagaya_gdf = gdf[num_values == 13112]
            except:
                pass
            
            # 文字列として処理（13112または"13112"で始まる）
            if setagaya_gdf is None or len(setagaya_gdf) == 0:
                try:
                    str_values = gdf[city_code_col].astype(str)
                    # 完全一致または前方一致
                    setagaya_gdf = gdf[str_values.str.startswith('13112', na=False)]
                except:
                    pass
            
            # それでも見つからない場合は、'13'で始まるものを試す（デバッグ用）
            if (setagaya_gdf is None or len(setagaya_gdf) == 0) and debug:
                try:
                    str_values = gdf[city_code_col].astype(str)
                    all_13 = gdf[str_values.str.startswith('13', na=False)]
                    print(f"\n⚠️ 世田谷区（13112）が見つかりません。'13'で始まるデータ: {len(all_13)}件")
                    if len(all_13) > 0:
                        unique_codes = all_13[city_code_col].unique()[:10]
                        print(f"  含まれる市区町村コード: {unique_codes.tolist()}")
                except:
                    pass
            
            if debug and city_code_col:
                print(f"\n使用したフィルタ列: {city_code_col}")
                if setagaya_gdf is not None and len(setagaya_gdf) > 0:
                    print(f"フィルタ後の市区町村コード分布:")
                    code_counts = setagaya_gdf[city_code_col].value_counts().head(10)
                    for code, count in code_counts.items():
                        print(f"  {code}: {count}件")
        else:
            # 市区町村コードで絞れない場合は、市区町村名で絞る
            city_name_cols = ['L01_018', 'L01_019', 'L01_022', 'L01_023', 'L01_024']
            setagaya_gdf = None
            used_col = None
            for col in city_name_cols:
                if col in gdf.columns:
                    gdf[col] = gdf[col].astype(str)
                    if '世田谷' in gdf[col].values:
                        setagaya_gdf = gdf[gdf[col].str.contains('世田谷', na=False)]
                        used_col = col
                        break
            
            if setagaya_gdf is None:
                logger.warning(f"[{year}年] 世田谷区のデータが見つかりません")
                if debug:
                    print(f"\n⚠️ 世田谷区のフィルタに失敗しました")
                return None
            
            if debug:
                print(f"\n使用したフィルタ列（市区町村名）: {used_col}")
        
        logger.info(f"[{year}年] 世田谷区フィルタ: {len(setagaya_gdf)} 地点")
        
        # デバッグ: 世田谷区フィルタ後の詳細出力
        if debug:
            print(f"\n=== デバッグ: [{year}年] 世田谷区フィルタ後 ===")
            print(f"フィルタ後件数: {len(setagaya_gdf)}")
            
            if len(setagaya_gdf) > 0:
                # 住所フィールドを探す
                address_field = None
                for col in ['L01_019', 'L01_023', 'L01_024', 'L01_025']:
                    if col in setagaya_gdf.columns:
                        address_field = col
                        break
                
                if address_field:
                    print(f"\n住所フィールド: {address_field}")
                    print(f"住所サンプル（フィルタ後）:")
                    for i, addr in enumerate(setagaya_gdf[address_field].head(5), 1):
                        if pd.notna(addr):
                            print(f"  {i}. {str(addr)[:80]}")
        
        return setagaya_gdf
    
    except Exception as e:
        logger.error(f"[{year}年] データ読み込みエラー: {e}", exc_info=True)
        return None


def extract_choume_name(address: str) -> Optional[str]:
    """
    所在地から町丁目名を抽出（正規化版、丁目付きで返す）
    
    例: "東京都　世田谷区上北沢３丁目２５番１０" → "上北沢3丁目"
        "桜上水５−４０−１０" → "桜上水5丁目"
    
    Args:
        address: 所在地住所
    
    Returns:
        str: 町丁目名（例: "上北沢3丁目"）、抽出失敗時はNone
    """
    if not address or not isinstance(address, str):
        return None
    
    # 全角数字を半角に変換
    address = address.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    
    # 全角ハイフンを半角に
    address = address.replace('−', '-').replace('ー', '-')
    
    # "世田谷区"以降を抽出
    if '世田谷区' in address:
        address = address.split('世田谷区')[1]
    
    # パターン1: "◯◯N丁目" の形式（すでに丁目がある）
    # 例: "等々力5丁目３３番１５" → "等々力5丁目"
    pattern1 = r'^(.+?)(\d+)丁目'
    match = re.search(pattern1, address)
    if match:
        area_name = match.group(1).strip()
        choume_num = match.group(2)
        return f"{area_name}{choume_num}丁目"
    
    # パターン2: "◯◯N-" の形式（丁目がない）
    # 例: "桜上水5-４０-１０" → "桜上水5丁目"
    pattern2 = r'^(.+?)(\d+)[-−ー]'
    match = re.search(pattern2, address)
    if match:
        area_name = match.group(1).strip()
        choume_num = match.group(2)
        return f"{area_name}{choume_num}丁目"
    
    # パターン3: "◯◯N番" の形式
    # 例: "上馬17番１２" → "上馬1丁目"（最初の数字を丁目として扱う）
    pattern3 = r'^(.+?)(\d+)番'
    match = re.search(pattern3, address)
    if match:
        area_name = match.group(1).strip()
        choume_num = match.group(2)
        # 最初の数字を丁目として扱う（簡易版）
        if choume_num:
            return f"{area_name}{choume_num[0]}丁目"
    
    return None


def match_with_choume(gdf: gpd.GeoDataFrame, conn, year: int, debug: bool = False) -> pd.DataFrame:
    """
    国土数値情報の住所をchoumeテーブルとマッチング
    
    Args:
        gdf: GeoDataFrame（国土数値情報）
        conn: PostgreSQL接続オブジェクト
        year: 調査年
    
    Returns:
        DataFrame: choume_code付きデータ
    """
    cursor = conn.cursor()
    
    # デバッグ: choumeテーブルの構造を確認
    if debug:
        print("\n" + "=" * 60)
        print(f"=== デバッグ: [{year}年] 町丁目マスタ取得前 ===")
        cursor.execute("SELECT COUNT(*) FROM choume")
        total_choume_count = cursor.fetchone()[0]
        print(f"全choumeテーブルの件数: {total_choume_count}")
        
        # city_codeの分布を確認
        cursor.execute("""
            SELECT city_code, COUNT(*) as cnt
            FROM choume
            GROUP BY city_code
            ORDER BY cnt DESC
            LIMIT 10
        """)
        city_code_dist = cursor.fetchall()
        print(f"\ncity_codeの分布（上位10件）:")
        for city_code, cnt in city_code_dist:
            print(f"  {city_code}: {cnt}件")
        
        # 世田谷区（13112）のデータを確認
        cursor.execute("""
            SELECT COUNT(*) 
            FROM choume 
            WHERE city_code = '13112'
        """)
        setagaya_count = cursor.fetchone()[0]
        print(f"\n世田谷区（city_code='13112'）の件数: {setagaya_count}")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM choume 
            WHERE city_code LIKE '13%'
        """)
        tokyo_ku_count = cursor.fetchone()[0]
        print(f"東京都の区（city_code LIKE '13%'）の件数: {tokyo_ku_count}")
    
    # 町丁目マスタを取得（世田谷区のみ）
    # city_codeはVARCHAR型なので文字列で比較
    cursor.execute("""
        SELECT choume_code, choume_name, city_code
        FROM choume
        WHERE city_code = '13112' OR city_code LIKE '13112%'
        ORDER BY choume_code
    """)
    choume_records = cursor.fetchall()
    choume_dict = {row[1]: row[0] for row in choume_records}  # name -> code マッピング
    
    logger.info(f"[{year}年] 町丁目マスタ: {len(choume_dict)} 件")
    
    # デバッグ: 町丁目マスタ取得後の詳細出力
    if debug:
        print(f"\n=== デバッグ: [{year}年] 町丁目マスタ取得後 ===")
        print(f"取得件数: {len(choume_dict)} 件")
        
        if len(choume_dict) > 0:
            print(f"\n町丁目マスタ（最初の20件）:")
            for i, (name, code) in enumerate(list(choume_dict.items())[:20], 1):
                print(f"  {i:2d}. {name:20s} -> {code}")
        else:
            print("⚠️ 町丁目マスタが空です！")
            
            # choumeテーブルの内容を確認
            cursor.execute("SELECT COUNT(*) FROM choume")
            total_count = cursor.fetchone()[0]
            print(f"\n全choumeテーブルの件数: {total_count}")
            
            if total_count > 0:
                cursor.execute("""
                    SELECT choume_code, choume_name, city_code
                    FROM choume
                    ORDER BY city_code, choume_name
                    LIMIT 20
                """)
                print(f"\n全choumeテーブルのサンプル（最初の20件）:")
                for row in cursor.fetchall():
                    print(f"  {row[2]:8s} | {row[1]:20s} | {row[0]}")
                
                # city_codeの分布を確認
                cursor.execute("""
                    SELECT city_code, COUNT(*) as cnt
                    FROM choume
                    GROUP BY city_code
                    ORDER BY cnt DESC
                    LIMIT 10
                """)
                print(f"\ncity_codeの分布:")
                for city_code, cnt in cursor.fetchall():
                    print(f"  {city_code}: {cnt}件")
                
                # 世田谷区（13112）のデータを直接確認
                cursor.execute("""
                    SELECT choume_code, choume_name
                    FROM choume
                    WHERE city_code = '13112'
                    ORDER BY choume_name
                    LIMIT 10
                """)
                setagaya_records = cursor.fetchall()
                if setagaya_records:
                    print(f"\n世田谷区（city_code='13112'）のデータ（最初の10件）:")
                    for code, name in setagaya_records:
                        print(f"  {code} | {name}")
                else:
                    print(f"\n⚠️ 世田谷区（city_code='13112'）のデータが存在しません")
            else:
                print("\n⚠️ choumeテーブルが完全に空です。先に21_import_choume_master.pyを実行してください。")
    
    # 住所フィールドを探す（年度によって異なる）
    address_col = None
    for col in ['L01_019', 'L01_023', 'L01_024', 'L01_025']:
        if col in gdf.columns:
            address_col = col
            break
    
    if address_col is None:
        logger.error(f"[{year}年] 住所フィールドが見つかりません")
        return pd.DataFrame()
    
    # 必須フィールドを確認
    survey_year_col = 'L01_005'
    price_col = 'L01_006'
    city_code_col = None
    city_name_col = None
    land_area_col = None
    
    for col in ['L01_017', 'L01_018', 'L01_021', 'L01_001']:
        if col in gdf.columns:
            city_code_col = col
            break
    
    for col in ['L01_018', 'L01_019', 'L01_022', 'L01_023', 'L01_024']:
        if col in gdf.columns:
            city_name_col = col
            break
    
    for col in ['L01_020', 'L01_024', 'L01_026', 'L01_027']:
        if col in gdf.columns:
            land_area_col = col
            break
    
    matched_records = []
    skipped_count = 0
    
    # デバッグ: 町丁目抽出のテスト
    if debug and len(gdf) > 0:
        print(f"\n=== デバッグ: [{year}年] 町丁目抽出・マッチング ===")
        print(f"処理対象件数: {len(gdf)} 件")
        print(f"\n最初の5件の抽出結果:")
        
        for i, (idx, row) in enumerate(gdf.head(5).iterrows(), 1):
            address = str(row.get(address_col, ''))
            choume_name_extracted = extract_choume_name(address) if address and address != 'nan' else None
            
            # マッチング試行
            matched_code = None
            if choume_name_extracted:
                if choume_name_extracted in choume_dict:
                    matched_code = choume_dict[choume_name_extracted]
                else:
                    # 部分一致を試す
                    normalized_extracted = choume_name_extracted.replace('丁目', '').strip()
                    for db_name, db_code in choume_dict.items():
                        normalized_db = db_name.replace('丁目', '').strip()
                        if normalized_extracted == normalized_db:
                            matched_code = db_code
                            break
            
            print(f"\n  {i}. 元住所: {address[:60] if address else '(空)'}")
            print(f"     抽出結果: {choume_name_extracted or '(抽出失敗)'}")
            print(f"     マッチコード: {matched_code or '(マッチなし)'}")
            
            if choume_name_extracted and not matched_code:
                # マッチ失敗時、類似検索
                if len(choume_dict) > 0:
                    normalized_extracted = choume_name_extracted.replace('丁目', '').strip()
                    similar = []
                    for db_name, db_code in choume_dict.items():
                        normalized_db = db_name.replace('丁目', '').strip()
                        # 前方一致または後方一致で類似を検索
                        if normalized_extracted[:2] in normalized_db or normalized_db[:2] in normalized_extracted:
                            similar.append((db_name, db_code))
                        # 部分一致も追加
                        elif normalized_extracted in normalized_db or normalized_db in normalized_extracted:
                            similar.append((db_name, db_code))
                    
                    if similar:
                        print(f"     類似候補（最初の5件）:")
                        for name, code in similar[:5]:
                            print(f"       - {name} ({code})")
                    else:
                        print(f"     類似候補: なし")
    
    for idx, row in gdf.iterrows():
        address = str(row.get(address_col, ''))
        if not address or address == 'nan':
            skipped_count += 1
            continue
        
        # 町丁目名を抽出
        choume_name_extracted = extract_choume_name(address)
        if not choume_name_extracted:
            skipped_count += 1
            if skipped_count <= 10:  # 最初の10件のみログ出力
                logger.debug(f"  ⚠️ 住所抽出失敗: {address[:50]}")
            continue
        
        # マッチング（柔軟な検索）
        matched_code = None
        matched_name = None
        
        # 完全一致
        if choume_name_extracted in choume_dict:
            matched_code = choume_dict[choume_name_extracted]
            matched_name = choume_name_extracted
        else:
            # 丁目の有無を正規化して比較
            normalized_extracted = choume_name_extracted.replace('丁目', '').strip()
            
            for db_name, db_code in choume_dict.items():
                normalized_db = db_name.replace('丁目', '').strip()
                
                # 正規化後の完全一致
                if normalized_extracted == normalized_db:
                    matched_code = db_code
                    matched_name = db_name
                    break
                
                # 前方一致（抽出名がDB名の先頭に含まれる）
                if normalized_extracted and normalized_extracted in normalized_db:
                    # より具体的なマッチを優先（長い名前を優先）
                    if matched_code is None or len(normalized_db) > len(choume_dict.get(matched_code, '').replace('丁目', '')):
                        matched_code = db_code
                        matched_name = db_name
                
                # 後方一致（DB名が抽出名の先頭に含まれる）
                elif normalized_db and normalized_db in normalized_extracted:
                    matched_code = db_code
                    matched_name = db_name
                    break
        
        if not matched_code:
            skipped_count += 1
            if skipped_count <= 10:
                logger.debug(f"  ⚠️ マッチなし: {choume_name_extracted} (元住所: {address[:50]})")
            continue
        
        # データ抽出
        try:
            survey_year = int(row.get(survey_year_col, year))
            price_str = str(row.get(price_col, ''))
            # 空文字や"_"を除去
            price_str = price_str.replace('_', '').strip()
            price_per_sqm = int(price_str) if price_str and price_str.isdigit() else None
            
            if price_per_sqm is None:
                logger.debug(f"  ⚠️ 価格が無効: {price_str}")
                skipped_count += 1
                continue
            
            land_area = None
            if land_area_col and land_area_col in row:
                land_area_str = str(row[land_area_col]).replace('_', '').strip()
                try:
                    land_area = float(land_area_str) if land_area_str else None
                except (ValueError, TypeError):
                    pass
            
            # ジオメトリから座標を取得
            latitude = None
            longitude = None
            if row.geometry and row.geometry.geom_type == 'Point':
                longitude, latitude = row.geometry.x, row.geometry.y
            elif row.geometry:
                # Polygonやその他のジオメトリの場合は重心を取得
                centroid = row.geometry.centroid
                longitude, latitude = centroid.x, centroid.y
            
            matched_records.append({
                'choume_code': matched_code,
                'choume_name': matched_name,
                'survey_year': survey_year,
                'official_price': price_per_sqm,
                'original_address': address,
                'land_area': land_area,
                'latitude': latitude,
                'longitude': longitude
            })
        
        except Exception as e:
            logger.debug(f"  ⚠️ データ抽出エラー: {e}")
            skipped_count += 1
            continue
    
    total_count = len(gdf)
    matched_count = len(matched_records)
    
    logger.info(f"[{year}年] 町丁目マッチング: {matched_count}件成功、{skipped_count}件スキップ")
    
    if matched_count < total_count * 0.5:
        logger.warning(f"⚠️ [{year}年] マッチング率が低すぎます（{matched_count}/{total_count} = {matched_count/total_count*100:.1f}%）")
    
    return pd.DataFrame(matched_records)


def insert_to_database(conn, df: pd.DataFrame, year: int) -> int:
    """
    データベースに挿入
    
    Args:
        conn: PostgreSQL接続
        df: 投入データ（choume_code, official_price含む）
        year: 調査年
    
    Returns:
        int: 挿入件数
    """
    if df.empty:
        logger.warning(f"[{year}年] 投入データがありません")
        return 0
    
    cursor = conn.cursor()
    
    insert_count = 0
    error_count = 0
    
    # INSERT ON CONFLICT UPDATE クエリ
    # UNIQUE制約: (choume_code, survey_year, land_type, data_source, original_address)
    # land_typeはNULLを許容（NULLは他のNULLとは異なる値として扱われるため、複数レコードが可能）
    insert_query = """
        INSERT INTO land_prices (
            choume_code, survey_year, land_type, official_price, data_source,
            original_address, land_area, latitude, longitude, created_at
        ) VALUES (
            %(choume_code)s, %(survey_year)s, NULL, %(official_price)s, 'kokudo_suuchi',
            %(original_address)s, %(land_area)s, %(latitude)s, %(longitude)s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (choume_code, survey_year, land_type, data_source, original_address)
        DO UPDATE SET
            official_price = EXCLUDED.official_price,
            land_area = EXCLUDED.land_area,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude
    """
    
    for _, row in df.iterrows():
        try:
            record = {
                'choume_code': row['choume_code'],
                'survey_year': int(row['survey_year']),
                'official_price': int(row['official_price']),
                'original_address': row['original_address'],
                'land_area': row.get('land_area'),
                'latitude': row.get('latitude'),
                'longitude': row.get('longitude')
            }
            
            cursor.execute(insert_query, record)
            insert_count += 1
            
        except Exception as e:
            error_count += 1
            if error_count <= 10:  # 最初の10件のみログ出力
                logger.error(f"  ❌ 挿入エラー: {e} - {row.get('choume_code', 'unknown')}")
            conn.rollback()
            continue
    
    try:
        conn.commit()
        logger.info(f"[{year}年] DB投入完了: {insert_count}件（エラー: {error_count}件）")
    except Exception as e:
        logger.error(f"[{year}年] コミットエラー: {e}")
        conn.rollback()
        insert_count = 0
    
    return insert_count


def process_year(year: int, db_config: dict, debug: bool = False) -> Tuple[bool, int]:
    """
    単年度の処理を実行
    
    Args:
        year: 調査年
        db_config: データベース設定
        debug: デバッグモード
    
    Returns:
        Tuple[bool, int]: (成功フラグ, 投入件数)
    """
    try:
        # データ読み込み
        gdf = load_land_price_data(year, debug=debug)
        if gdf is None or gdf.empty:
            return False, 0
        
        # PostgreSQL接続
        conn = psycopg2.connect(**db_config)
        
        try:
            # 町丁目マッチング
            df = match_with_choume(gdf, conn, year, debug=debug)
            
            if df.empty:
                logger.warning(f"[{year}年] マッチング結果が空です")
                return False, 0
            
            # DB投入
            insert_count = insert_to_database(conn, df, year)
            
            return True, insert_count
        
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"[{year}年] 処理エラー: {e}", exc_info=True)
        return False, 0


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='国土数値情報（地価公示）インポート')
    parser.add_argument('--year', type=int, help='処理する年度（例: 2000）')
    parser.add_argument('--start', type=int, help='開始年度（例: 2018）')
    parser.add_argument('--end', type=int, help='終了年度（例: 2025）')
    parser.add_argument('--debug', action='store_true', help='デバッグモード（詳細ログ出力）')
    
    args = parser.parse_args()
    
    # デバッグモードの設定
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        print("🔍 デバッグモードが有効になりました")
    
    # 処理年度の決定
    if args.year:
        years = [args.year]
    elif args.start and args.end:
        years = list(range(args.start, args.end + 1))
    else:
        # デフォルト: 2000-2025年
        years = list(range(2000, 2026))
    
    logger.info("=" * 60)
    logger.info("=== 国土数値情報インポート開始 ===")
    logger.info(f"対象期間: {min(years)}-{max(years)}年（{len(years)}年分）")
    if args.debug:
        logger.info("🔍 デバッグモード: ON")
    logger.info("=" * 60)
    
    # データベース設定読み込み
    db_config = load_db_config()
    
    # 各年度を処理
    total_inserted = 0
    success_years = []
    failed_years = []
    
    # デバッグモードの場合はtqdmを使わない（出力が混ざるため）
    year_iter = years if args.debug else tqdm(years, desc="処理中")
    
    for year in year_iter:
        logger.info(f"\n[{year}年] 処理開始")
        success, count = process_year(year, db_config, debug=args.debug)
        
        if success:
            total_inserted += count
            success_years.append(year)
        else:
            failed_years.append(year)
    
    # サマリー出力
    logger.info("\n" + "=" * 60)
    logger.info("=== 完了サマリー ===")
    logger.info(f"総処理年数: {len(years)}年")
    logger.info(f"成功: {len(success_years)}年")
    logger.info(f"失敗: {len(failed_years)}年")
    if failed_years:
        logger.info(f"失敗年度: {failed_years}")
    logger.info(f"総投入件数: {total_inserted}件")
    
    if len(success_years) > 0:
        avg_matched = total_inserted / len(success_years)
        logger.info(f"平均投入件数/年: {avg_matched:.1f}件")
    
    logger.info("=" * 60)
    
    if len(failed_years) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

