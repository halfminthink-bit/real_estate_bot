import geopandas as gpd
import pandas as pd
from pathlib import Path
from loguru import logger
import sys

def convert_gml_to_csv(year: int, prefecture_code: str = '13'):
    '''
    国土数値情報のGMLファイルをCSVに変換
    '''
    # パス設定
    gml_dir = Path(f'data/raw/national/kokudo_suuchi/{year}_{prefecture_code}')
    output_dir = Path('data/processed/master')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # GMLファイルを探す
    gml_files = list(gml_dir.rglob('L01-*.xml'))
    
    if not gml_files:
        logger.error(f'❌ GMLファイルが見つかりません: {gml_dir}')
        return None
    
    gml_file = gml_files[0]
    logger.info(f'📂 読み込み: {gml_file}')
    
    try:
        # GMLファイルを読み込み
        gdf = gpd.read_file(gml_file)
        logger.info(f'✅ 読み込み成功: {len(gdf)} 件')
        
        # カラム名を表示
        logger.info(f'カラム: {gdf.columns.tolist()}')
        
        # CSVに保存（geometryカラムは除外）
        output_csv = output_dir / f'kokudo_land_price_{year}_{prefecture_code}.csv'
        
        # geometry以外のカラムを抽出
        df = pd.DataFrame(gdf.drop(columns=['geometry']))
        
        # 緯度経度を追加
        df['latitude'] = gdf.geometry.y
        df['longitude'] = gdf.geometry.x
        
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        logger.info(f'✅ CSV保存完了: {output_csv}')
        
        # サンプル表示
        logger.info(f'\n【先頭3件のサンプル】')
        print(df.head(3))
        
        return output_csv
        
    except Exception as e:
        logger.error(f'❌ エラー: {e}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # 5年分を変換
    years = [2025, 2024, 2023, 2022, 2021]
    
    logger.info('=' * 60)
    logger.info('GML → CSV 変換開始')
    logger.info('=' * 60)
    
    for year in years:
        logger.info(f'\n--- {year}年 ---')
        csv_path = convert_gml_to_csv(year)
        
        if csv_path:
            logger.info(f'✅ {year}年の変換完了')
        else:
            logger.warning(f'⚠️  {year}年の変換失敗（ファイルが存在しない可能性）')
    
    logger.info('\n' + '=' * 60)
    logger.info('変換完了')
    logger.info('=' * 60)

