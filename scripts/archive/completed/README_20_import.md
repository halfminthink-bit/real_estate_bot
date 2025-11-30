# 国土数値情報（地価公示）インポートスクリプト

## 📋 概要

2000-2025年の26年分の国土数値情報（地価公示）Shapefile/GeoJSONデータをPostgreSQLの`land_prices`テーブルにインポートします。

## 🔧 セットアップ

### 1. 仮想環境の有効化

**PowerShellの場合:**
```powershell
.\venv\Scripts\Activate.ps1
```

**コマンドプロンプトの場合:**
```cmd
venv\Scripts\activate.bat
```

### 2. 依存関係のインストール

仮想環境を有効化した後、必要なパッケージをインストール:

```bash
pip install -r requirements.txt
```

または、不足しているパッケージのみ:

```bash
pip install tqdm geopandas pandas psycopg2-binary pyyaml python-dotenv
```

## 🚀 使用方法

### 全年度処理（2000-2025年）

```bash
python scripts/20_import_historical_kokudo_data.py
```

### 単年度処理

```bash
python scripts/20_import_historical_kokudo_data.py --year 2000
```

### 範囲指定

```bash
python scripts/20_import_historical_kokudo_data.py --start 2018 --end 2025
```

## ⚠️ 注意事項

- **仮想環境を有効化**してからスクリプトを実行してください
- データベース接続設定（`.env`または`config/database.yml`）を確認してください
- 処理時間は約5分以内を想定しています（26年分）

## 📊 処理内容

1. **ファイルパス解決**: 年度ごとのファイル形式に対応
   - 2000-2011年: Shapefile（古い形式）
   - 2012-2014年: Shapefile（中間形式）
   - 2015年以降: ShapefileまたはGeoJSON

2. **データ読み込み**: 世田谷区のデータのみフィルタ

3. **住所マッチング**: `choume`テーブルと照合

4. **データベース投入**: UPSERT処理で重複を自動更新

## 📝 ログ

ログは以下の場所に出力されます:
- コンソール出力
- `logs/real_estate_bot.log`

## 🔍 トラブルシューティング

### ModuleNotFoundError: No module named 'tqdm'

仮想環境を有効化してください:
```powershell
.\venv\Scripts\Activate.ps1
```

### データベース接続エラー

`.env`ファイルまたは`config/database.yml`でデータベース設定を確認してください。

