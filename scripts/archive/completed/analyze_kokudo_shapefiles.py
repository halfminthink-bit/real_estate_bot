"""
国土数値情報（地価公示）Shapefile分析スクリプト
2000-2021年のShapefileのフィールド情報を抽出してまとめる
"""

from pathlib import Path
import json
from typing import Dict, List, Any
import sys

try:
    import shapefile
    HAS_SHAPEFILE = True
except ImportError:
    HAS_SHAPEFILE = False
    try:
        import geopandas as gpd
        HAS_GEOPANDAS = True
    except ImportError:
        HAS_GEOPANDAS = False
        print("Error: shapefile or geopandas library is required")
        sys.exit(1)

def find_shapefile_path(year: int, base_dir: Path) -> Path:
    """指定年のShapefileパスを検索"""
    year_dir = base_dir / f"{year}_13"
    
    if not year_dir.exists():
        return None
    
    # 2000-2011年: _LandPriceサフィックス付き
    if 2000 <= year <= 2011:
        shp_path = year_dir / f"L01-{year-2000:02d}_13-g_LandPrice.shp"
        if shp_path.exists():
            return shp_path
    
    # 2012-2014年: 直接配置
    if 2012 <= year <= 2014:
        shp_path = year_dir / f"L01-{year-2000:02d}_13.shp"
        if shp_path.exists():
            return shp_path
    
    # 2015-2021年: GMLフォルダ内
    if 2015 <= year <= 2021:
        gml_dir = year_dir / f"L01-{year-2000:02d}_13_GML"
        if gml_dir.exists():
            shp_path = gml_dir / f"L01-{year-2000:02d}_13.shp"
            if shp_path.exists():
                return shp_path
    
    # フォールバック: 任意の.shpファイルを検索
    shp_files = list(year_dir.rglob("*.shp"))
    if shp_files:
        return shp_files[0]
    
    return None

def analyze_shapefile(year: int, shp_path: Path) -> Dict[str, Any]:
    """Shapefileを分析してフィールド情報を抽出"""
    try:
        if HAS_SHAPEFILE:
            # shapefileライブラリを使用（日本語データのためエンコーディングを指定）
            try:
                sf = shapefile.Reader(str(shp_path), encoding='cp932')
            except:
                try:
                    sf = shapefile.Reader(str(shp_path), encoding='shift_jis')
                except:
                    sf = shapefile.Reader(str(shp_path), encoding='utf-8')
            
            # レコードを一度だけ読み込む（エンコーディングエラーを回避）
            records = None
            total_records = 0
            try:
                records = list(sf.records())
                total_records = len(records)
            except (UnicodeDecodeError, Exception) as e:
                # エンコーディングエラーの場合はレコード数を別の方法で取得
                try:
                    total_records = sf.numRecords if hasattr(sf, 'numRecords') else 0
                except:
                    total_records = 0
            
            # フィールド情報を抽出
            fields = []
            for field_index, field in enumerate(sf.fields[1:]):  # 最初の要素は削除マーカーなのでスキップ
                field_name = field[0]
                field_type = field[1]
                field_length = field[2] if len(field) > 2 else None
                field_decimal = field[3] if len(field) > 3 else None
                
                # サンプル値を取得（最初の5レコード）
                sample_values = []
                null_count = 0
                
                if records is not None:
                    try:
                        for i, record in enumerate(records[:5]):
                            if field_index < len(record):
                                value = record[field_index]
                                if value is not None:
                                    sample_values.append(str(value)[:50])  # 長すぎる場合は切り詰め
                        
                        # 欠損値カウント
                        for record in records:
                            if field_index >= len(record) or record[field_index] is None or record[field_index] == '':
                                null_count += 1
                    except (UnicodeDecodeError, Exception):
                        # エンコーディングエラーの場合はスキップ
                        pass
                
                fields.append({
                    'name': field_name,
                    'type': field_type,
                    'length': field_length,
                    'decimal': field_decimal,
                    'sample_values': sample_values,
                    'null_count': null_count,
                    'total_count': total_records
                })
            
            # ジオメトリタイプを取得
            shape_type = sf.shapeType
            shape_type_names = {
                1: 'Point',
                3: 'Polyline',
                5: 'Polygon',
                8: 'MultiPoint',
                11: 'PointZ',
                13: 'PolylineZ',
                15: 'PolygonZ',
                18: 'MultiPointZ'
            }
            geometry_type = shape_type_names.get(shape_type, f'Unknown({shape_type})')
            
            try:
                rel_path = str(shp_path.relative_to(Path.cwd()))
            except ValueError:
                rel_path = str(shp_path)
            
            return {
                'year': year,
                'file_path': rel_path,
                'total_records': total_records,
                'fields': fields,
                'geometry_type': geometry_type,
                'crs': None  # shapefileライブラリではCRS情報を直接取得できない
            }
        
        elif HAS_GEOPANDAS:
            # geopandasを使用
            gdf = gpd.read_file(shp_path)
            
            # フィールド情報を抽出
            fields = []
            for col in gdf.columns:
                if col == 'geometry':
                    continue
                
                dtype = str(gdf[col].dtype)
                sample_values = gdf[col].dropna().head(5).tolist()
                
                fields.append({
                    'name': col,
                    'dtype': dtype,
                    'sample_values': sample_values,
                    'null_count': int(gdf[col].isna().sum()),
                    'total_count': len(gdf)
                })
            
            try:
                rel_path = str(shp_path.relative_to(Path.cwd()))
            except ValueError:
                rel_path = str(shp_path)
            
            return {
                'year': year,
                'file_path': rel_path,
                'total_records': len(gdf),
                'fields': fields,
                'geometry_type': str(gdf.geometry.type.iloc[0]) if len(gdf) > 0 else None,
                'crs': str(gdf.crs) if gdf.crs else None
            }
    
    except Exception as e:
        try:
            rel_path = str(shp_path.relative_to(Path.cwd()))
        except ValueError:
            rel_path = str(shp_path)
        
        return {
            'year': year,
            'file_path': rel_path,
            'error': str(e)
        }

def main():
    base_dir = Path("data/raw/national/kokudo_suuchi")
    
    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        sys.exit(1)
    
    results = []
    
    print("=" * 80)
    print("国土数値情報（地価公示）Shapefile分析")
    print("=" * 80)
    print()
    
    for year in range(2000, 2022):  # 2000-2021年
        print(f"Processing {year}...", end=" ")
        
        shp_path = find_shapefile_path(year, base_dir)
        
        if shp_path is None:
            print("❌ Shapefile not found")
            results.append({
                'year': year,
                'status': 'not_found'
            })
            continue
        
        if not shp_path.exists():
            print("❌ File does not exist")
            results.append({
                'year': year,
                'status': 'not_found',
                'file_path': str(shp_path)
            })
            continue
        
        try:
            result = analyze_shapefile(year, shp_path)
            results.append(result)
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"✅ {result.get('total_records', 0)} records, {len(result.get('fields', []))} fields")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'year': year,
                'status': 'error',
                'error': str(e),
                'file_path': str(shp_path)
            })
    
    # 結果をテキストファイルに出力
    output_file = Path("kokudo_shapefile_analysis.txt")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("国土数値情報（地価公示）Shapefile分析結果\n")
        f.write("2000-2021年のShapefileフィールド情報まとめ\n")
        f.write("=" * 80 + "\n\n")
        
        for result in results:
            if 'error' in result or result.get('status') == 'not_found':
                f.write(f"\n【{result['year']}年】\n")
                f.write(f"状態: {'見つかりません' if result.get('status') == 'not_found' else 'エラー'}\n")
                if 'error' in result:
                    f.write(f"エラー内容: {result['error']}\n")
                f.write("\n" + "-" * 80 + "\n")
                continue
            
            f.write(f"\n【{result['year']}年】\n")
            f.write(f"ファイルパス: {result['file_path']}\n")
            f.write(f"レコード数: {result['total_records']:,}\n")
            f.write(f"ジオメトリタイプ: {result['geometry_type']}\n")
            f.write(f"座標系: {result['crs']}\n")
            f.write(f"フィールド数: {len(result['fields'])}\n\n")
            
            f.write("フィールド一覧:\n")
            for i, field in enumerate(result['fields'], 1):
                f.write(f"  {i}. {field['name']}\n")
                if 'dtype' in field:
                    f.write(f"     型: {field['dtype']}\n")
                elif 'type' in field:
                    type_info = f"{field['type']}"
                    if field.get('length'):
                        type_info += f" (長さ: {field['length']}"
                        if field.get('decimal'):
                            type_info += f", 小数点: {field['decimal']}"
                        type_info += ")"
                    f.write(f"     型: {type_info}\n")
                f.write(f"     欠損値: {field['null_count']:,} / {field['total_count']:,}\n")
                if field.get('sample_values'):
                    samples = field['sample_values'][:3]
                    f.write(f"     サンプル値: {samples}\n")
                f.write("\n")
            
            f.write("-" * 80 + "\n")
        
        # フィールド名の変遷をまとめ
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("フィールド名の変遷\n")
        f.write("=" * 80 + "\n\n")
        
        # 全フィールド名を収集
        all_field_names = set()
        for result in results:
            if 'fields' in result:
                for field in result['fields']:
                    all_field_names.add(field['name'])
        
        # 各フィールドがどの年に存在するかを確認
        field_years = {}
        for field_name in sorted(all_field_names):
            field_years[field_name] = []
            for result in results:
                if 'fields' in result:
                    field_names = [f['name'] for f in result['fields']]
                    if field_name in field_names:
                        field_years[field_name].append(result['year'])
        
        for field_name in sorted(all_field_names):
            years = sorted(field_years[field_name])
            f.write(f"{field_name}:\n")
            f.write(f"  存在する年: {years[0]}-{years[-1]} ({len(years)}年)\n")
            if len(years) < 22:
                missing = [y for y in range(2000, 2022) if y not in years]
                f.write(f"  欠落している年: {missing}\n")
            f.write("\n")
    
    # JSON形式でも出力
    json_output = Path("kokudo_shapefile_analysis.json")
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print()
    print("=" * 80)
    print(f"✅ 分析完了")
    print(f"   テキストファイル: {output_file}")
    print(f"   JSONファイル: {json_output}")
    print("=" * 80)

if __name__ == "__main__":
    main()

