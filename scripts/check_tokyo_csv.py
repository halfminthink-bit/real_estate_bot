import pandas as pd
from pathlib import Path
import sys

def check_csv(csv_path: Path):
    """CSVファイルの構造を確認"""
    if not csv_path.exists():
        print(f'❌ ファイルが見つかりません: {csv_path}')
        return False
    
    # エンコーディングを試す
    encodings = ['utf-8', 'shift-jis', 'cp932']
    
    for enc in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=enc, nrows=5)
            print(f'✅ 読み込み成功（エンコーディング: {enc}）')
            print(f'\n件数: {len(df)} 件（最初の5件のみ）')
            print(f'\nカラム一覧:')
            for i, col in enumerate(df.columns, 1):
                print(f'  {i}. {col}')
            print(f'\n【先頭3件】')
            print(df.head(3))
            return True
        except Exception as e:
            continue
    
    print(f'❌ すべてのエンコーディングで読み込み失敗')
    return False

if __name__ == '__main__':
    # 指定されたファイルまたは全ファイルを確認
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
        check_csv(csv_path)
    else:
        # 5年分を確認
        base_dir = Path('data/raw/prefecture/tokyo')
        years = [2025, 2024, 2023, 2022, 2021]
        
        print('=' * 60)
        print('Tokyo Land Price CSV Check')
        print('=' * 60)
        
        for year in years:
            csv_path = base_dir / f'tokyo_land_price_{year}.csv'
            print(f'\n--- {year}年 ---')
            if check_csv(csv_path):
                print(f'✅ {year}年の確認完了')
            else:
                print(f'⚠️  {year}年のファイルが見つかりません')
        
        print('\n' + '=' * 60)
        print('確認完了')
        print('=' * 60)

