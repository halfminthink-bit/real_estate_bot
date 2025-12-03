# 不動産情報ライブラリAPI テストスクリプト実行方法

## 📋 前提条件

1. **PostgreSQLが起動している**
   - Docker Composeで起動している場合: `docker-compose up -d`
   - または、ローカルのPostgreSQLが起動していること

2. **Python仮想環境が有効化されている**
   ```powershell
   # プロジェクトルートで実行
   .\venv\Scripts\Activate.ps1
   ```

3. **必要なパッケージがインストールされている**
   ```powershell
   pip install -r requirements.txt
   ```

4. **環境変数ファイル（.env）が設定されている（オプション）**
   - APIキーが必要な場合のみ
   - プロジェクトルートに `.env` ファイルを作成
   - 以下の内容を記述:
     ```
     REINFOLIB_API_KEY=your_api_key_here
     REINFOLIB_API_ENDPOINT=https://www.reinfolib.mlit.go.jp/ex-api/external
     REINFOLIB_API_TIMEOUT=30
     ```

## 🚀 実行方法

### 方法1: 仮想環境を有効化してから実行

```powershell
# 1. プロジェクトルートに移動
cd C:\Users\hyokaimen\kyota\real_estate_bot

# 2. 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# 3. スクリプトを実行
python scripts\test_reinfolib_api.py
```

### 方法2: 仮想環境のPythonを直接指定

```powershell
# プロジェクトルートで実行
.\venv\Scripts\python.exe scripts\test_reinfolib_api.py
```

## 📊 実行結果

スクリプトは以下のテストを実行します:

1. **PostgreSQL接続確認**
   - テーブル存在確認
   - データ件数確認
   - サンプル住所表示（10件）
   - 住所パターン分析

2. **TEST 1: 世田谷区全体の取引データ取得**
   - 2024年Q3の世田谷区全体データを取得
   - 結果を `output/test_api_results/setagaya_2024q3.json` に保存

3. **TEST 2: 特定の町丁目の取引データ取得**
   - 上用賀6丁目の取引データを取得
   - 結果を `output/test_api_results/kamiyoga_6chome_2024q3.json` に保存

4. **TEST 3: 複数年度のトレンド確認**
   - 2020-2024年の各年Q3データを取得
   - 結果を `output/test_api_results/trend_2020_2024.json` に保存

5. **TEST 4: レスポンス構造分析**
   - APIレスポンスの全フィールドを抽出
   - 各フィールドのサンプル値と欠損率を表示

## ⚠️ トラブルシューティング

### PostgreSQL接続エラーが発生する場合

1. PostgreSQLが起動しているか確認
   ```powershell
   # Docker Composeの場合
   docker-compose ps
   ```

2. 接続情報を確認
   - `config/database.yml` の設定を確認
   - 環境変数 `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` を確認

### APIキーエラーが発生する場合

- `.env` ファイルに `REINFOLIB_API_KEY` が設定されているか確認
- APIキーが有効か確認（不動産情報ライブラリのサイトで確認）

### モジュールインポートエラーが発生する場合

```powershell
# 仮想環境が正しく有効化されているか確認
python -c "import sys; print(sys.executable)"

# 必要なパッケージを再インストール
pip install -r requirements.txt
```

