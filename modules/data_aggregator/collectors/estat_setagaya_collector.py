#!/usr/bin/env python3
"""
e-Stat API 世田谷区データコレクター

資産価値訴求に必要なデータを町丁目レベルで取得
"""

import os
import sys
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
import time
import logging

# プロジェクトルートを取得
project_root = Path(__file__).parent.parent.parent.parent

# .envファイルを読み込み
load_dotenv(project_root / '.env')

logger = logging.getLogger(__name__)

class EStatSetagayaCollector:
    """e-Stat APIで世田谷区のデータを収集"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: e-Stat APIキー（Noneの場合は環境変数から取得）
        """
        self.api_key = api_key or os.getenv('ESTAT_API_KEY')
        if not self.api_key:
            raise ValueError("ESTAT_API_KEY が設定されていません。.envファイルまたは引数で指定してください。")
        
        self.base_url = "https://api.e-stat.go.jp/rest/3.0/app"
        self.setagaya_code = "13112"  # 世田谷区のコード
        self.timeout = 60
        
        # 東京都の統計表ID（町丁目レベル）
        # 注意: 実際の統計表IDは調査結果に基づいて更新してください
        self.tokyo_table_ids = {
            "population": "8003006724",      # 人口総数・世帯数
            "age_composition": "8003006792",  # 年齢5歳階級別人口
            "household_size": "8003006803",   # 世帯人員別世帯数
            "housing_tenure": "8003006918",   # 住宅所有関係
            "industry": "8003007680",         # 産業別就業者数
        }
        
        # データ保存ディレクトリ
        self.data_dir = project_root / 'data'
        self.data_dir.mkdir(exist_ok=True)
    
    def collect_all_setagaya_data(self) -> Dict[str, pd.DataFrame]:
        """世田谷区の全データを収集"""
        
        results = {}
        
        for data_name, table_id in self.tokyo_table_ids.items():
            print(f"\n{'='*60}")
            print(f"📊 {data_name} を取得中...")
            print(f"統計表ID: {table_id}")
            print('='*60)
            
            df = self._fetch_data(table_id, data_name)
            
            if not df.empty:
                # 世田谷区のデータのみフィルタ
                if '@area' in df.columns:
                    setagaya_df = df[df['@area'].str.startswith(self.setagaya_code)]
                    print(f"✅ 世田谷区データ: {len(setagaya_df)}件（全データ: {len(df)}件）")
                    
                    # 保存
                    output_file = self.data_dir / f"estat_{data_name}_setagaya.csv"
                    setagaya_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    print(f"💾 保存: {output_file}")
                    
                    results[data_name] = setagaya_df
                else:
                    print(f"⚠️  @areaカラムが見つかりません。全データを保存します。")
                    output_file = self.data_dir / f"estat_{data_name}_setagaya.csv"
                    df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    print(f"💾 保存: {output_file}")
                    results[data_name] = df
            else:
                print(f"❌ データ取得失敗")
            
            time.sleep(1)  # API制限対策
        
        return results
    
    def _fetch_data(self, table_id: str, data_name: str, limit: int = 100000) -> pd.DataFrame:
        """統計表IDからデータを取得"""
        
        url = f"{self.base_url}/json/getStatsData"
        params = {
            "appId": self.api_key,
            "lang": "J",
            "statsDataId": table_id,
            "limit": limit
        }
        
        try:
            print(f"リクエスト送信中...")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'GET_STATS_DATA' in data:
                result = data['GET_STATS_DATA'].get('RESULT', {})
                
                if result.get('STATUS') == 0:
                    stat_data = data['GET_STATS_DATA']['STATISTICAL_DATA']
                    
                    if 'DATA_INF' in stat_data and 'VALUE' in stat_data['DATA_INF']:
                        values = stat_data['DATA_INF']['VALUE']
                        df = pd.DataFrame(values)
                        print(f"✅ 取得件数: {len(df)}件")
                        if len(df) > 0:
                            print(f"   カラム: {list(df.columns)}")
                        return df
                    else:
                        print(f"❌ ERROR: DATA_INF/VALUE が見つかりません")
                        if 'DATA_INF' in stat_data:
                            print(f"   DATA_INFのキー: {list(stat_data['DATA_INF'].keys())}")
                else:
                    error_msg = result.get('ERROR_MSG', 'Unknown error')
                    print(f"❌ ERROR: {error_msg}")
                    print(f"   STATUS: {result.get('STATUS')}")
            else:
                print(f"❌ ERROR: GET_STATS_DATA が見つかりません")
                print(f"   レスポンスのキー: {list(data.keys())}")
            
            return pd.DataFrame()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR: リクエストエラー - {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def aggregate_by_choume(self, df: pd.DataFrame) -> pd.DataFrame:
        """町丁目ごとに集計"""
        
        if df.empty:
            return pd.DataFrame()
        
        if '@area' not in df.columns:
            print("⚠️  @areaカラムが見つかりません")
            return df
        
        # @areaカラムで町丁目コードを抽出（最初の11桁）
        df['choume_code'] = df['@area'].str[:11]
        
        # 集計に必要なカラムを確認
        groupby_cols = ['choume_code']
        if '@cat01' in df.columns:
            groupby_cols.append('@cat01')
        if '@cat02' in df.columns:
            groupby_cols.append('@cat02')
        
        # 値のカラムを確認
        value_col = '$' if '$' in df.columns else df.columns[-1]
        
        # グルーピング
        aggregated = df.groupby(groupby_cols).agg({
            value_col: 'sum'
        }).reset_index()
        
        return aggregated


def main():
    """メイン実行"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='e-Stat API 世田谷区データ収集',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python -m modules.data_aggregator.collectors.estat_setagaya_collector
  python -m modules.data_aggregator.collectors.estat_setagaya_collector --api-key YOUR_API_KEY
        """
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='e-Stat APIキー（.envファイルのESTAT_API_KEYより優先されます）'
    )
    
    args = parser.parse_args()
    
    print("\n🚀 e-Stat 世田谷区データ収集開始")
    print("="*60)
    
    try:
        collector = EStatSetagayaCollector(api_key=args.api_key)
        results = collector.collect_all_setagaya_data()
        
        print("\n" + "="*60)
        print("✅ 収集完了！")
        print("="*60)
        
        for data_name, df in results.items():
            print(f"- {data_name}: {len(df)}件")
        
        print("\n💡 次のステップ:")
        print("1. データ構造の解析：@cat01, @cat02の意味を解読")
        print("2. 町丁目マッピング：町丁目コード → 町名の変換テーブル作成")
        print("3. スコア算出：人口密度、年齢構成から「住みやすさスコア」計算")
        print("4. 他APIとの統合：不動産情報ライブラリAPI、犯罪データ、ハザードマップ")
        
    except ValueError as e:
        print(f"\n❌ エラー: {e}")
        print("\n.envファイルに以下を追加してください:")
        print("ESTAT_API_KEY=your-api-key-here")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()











