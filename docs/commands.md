# 📋 コマンド集

RealEstateBotの主要コマンドをまとめたクイックリファレンスです。

---

## 🚀 基本コマンド

### 記事生成

```bash
# 1件テスト生成
python main_orchestrator.py --project projects/setagaya_real_estate/config.yml --limit 1

# 複数件生成（例: 10件）
python main_orchestrator.py --project projects/setagaya_real_estate/config.yml --limit 10

# 全件生成（世田谷区全128町丁目）
python main_orchestrator.py --project projects/setagaya_real_estate/config.yml --limit 128
```

**オプション**:
- `--project`: プロジェクト設定ファイルのパス（必須）
- `--limit`: 生成件数の制限（省略時は全件）
- `--mode`: 実行モード（`full`, `data_only`, `generate_only`）
- `--debug`: デバッグモード

---

### WordPress投稿

```bash
# 1件テスト投稿
python scripts/post_to_wordpress.py --limit 1

# 未投稿記事を全件投稿
python scripts/post_to_wordpress.py

# 指定件数投稿
python scripts/post_to_wordpress.py --limit 10

# 再投稿モード（投稿済み記事も含む）
python scripts/post_to_wordpress.py --republish --limit 5

# 全記事のWordPress情報をリセット（再投稿準備）
python scripts/post_to_wordpress.py --reset-all
```

**オプション**:
- `--limit`: 投稿件数制限
- `--republish`: 投稿済み記事も再投稿
- `--reset-all`: 全記事のWordPress情報をリセット
- `--project`: プロジェクトディレクトリ（デフォルト: `projects/setagaya_real_estate`）

---

## 🗄️ データベース操作

### PostgreSQL

```bash
# PostgreSQL接続
docker exec -it real_estate_db psql -U postgres -d real_estate_dev

# データ確認
SELECT COUNT(*) FROM land_prices_kokudo;

# 町丁目の地価確認
SELECT survey_year, AVG(official_price)::INTEGER
FROM land_prices_kokudo
WHERE original_address LIKE '%上用賀6丁目%'
GROUP BY survey_year
ORDER BY survey_year DESC;

# 町丁目マスタ確認
SELECT ward, COUNT(*) as count 
FROM choume_master 
WHERE active = TRUE
GROUP BY ward;

# 終了
\q
```

### SQLite（記事管理）

```bash
# SQLite接続
sqlite3 projects/setagaya_real_estate/articles.db

# 記事一覧
SELECT choume, wp_status, wp_posted_at FROM articles;

# 未投稿記事
SELECT COUNT(*) FROM articles WHERE wp_post_id IS NULL;

# 投稿履歴
SELECT * FROM post_history ORDER BY created_at DESC LIMIT 10;

# 終了
.quit
```

---

## 🔧 データインポート・メンテナンス

### 地価データインポート

```bash
# 26年分（2000-2025年）を一括インポート
python scripts/import_kokudo_all_years.py
```

**期待される結果**:
```
✅ 成功: 26年分 / 3,907件
✅ 失敗: 0年分
```

### データベースパス修正

```bash
# 既存データベースのパスを修正（Windowsのバックスラッシュを / に統一）
python scripts/fix_db_paths.py --yes
```

**用途**: 既存の記事データベース内のパスを正規化（Windows環境で必要）

---

## 🐳 Docker操作

### PostgreSQL

```bash
# PostgreSQL起動
docker-compose up -d

# PostgreSQL停止
docker-compose down

# PostgreSQL再起動
docker-compose restart

# PostgreSQLログ確認
docker logs real_estate_db

# PostgreSQL接続
docker exec -it real_estate_db psql -U postgres -d real_estate_dev
```

---

## 📊 データ確認・デバッグ

### データベース状態確認

```bash
# PostgreSQLデータ確認
python scripts/check_db_data.py

# 記事統計確認
python scripts/show_article_stats.py
```

### APIテスト

```bash
# 不動産情報ライブラリAPIテスト
python scripts/test_reinfolib_api.py

# WordPress認証テスト
python scripts/test_wp_auth.py
```

---

## 🔍 トラブルシューティング

### 記事再生成

```bash
# 既存記事を上書きして再生成（処理済みフラグを無視）
# 注意: 現在は --force オプションは存在しないため、
# データベースから該当記事を削除してから再生成する必要があります
python main_orchestrator.py --project projects/setagaya_real_estate/config.yml --limit 1
```

### データベース再構築

```bash
# PostgreSQLを完全に再構築
docker-compose down -v
docker-compose up -d
python scripts/import_kokudo_all_years.py
```

### ログ確認

```bash
# アプリケーションログ確認
cat logs/real_estate_bot.log

# 最新のログのみ確認
tail -n 100 logs/real_estate_bot.log
```

---

## 📁 ファイル確認

### 生成されたファイル

```bash
# Markdown記事
ls projects/setagaya_real_estate/output/

# HTML記事
ls projects/setagaya_real_estate/html/

# グラフ画像
ls projects/setagaya_real_estate/charts/
```

---

## 🎯 よく使うコマンド組み合わせ

### 新規記事生成から投稿まで

```bash
# 1. 記事を10件生成
python main_orchestrator.py --project projects/setagaya_real_estate/config.yml --limit 10

# 2. 生成された記事を確認
ls projects/setagaya_real_estate/html/

# 3. 1件テスト投稿
python scripts/post_to_wordpress.py --limit 1

# 4. 問題なければ残りを投稿
python scripts/post_to_wordpress.py --limit 9
```

### メンテナンス作業

```bash
# 1. データベースパス修正（Windows環境）
python scripts/fix_db_paths.py --yes

# 2. 記事統計確認
python scripts/show_article_stats.py

# 3. 必要に応じて再投稿
python scripts/post_to_wordpress.py --republish --limit 5
```

---

## 📝 環境変数設定

`.env`ファイルに以下を設定：

```env
# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=real_estate_dev
DB_USER=postgres
DB_PASSWORD=postgres

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# WordPress
WP_SITE_URL=https://totiwobunseki.com
WP_USERNAME=kyota.3557
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx
WP_DEFAULT_STATUS=future
WP_DEFAULT_CATEGORY=不動産

# 不動産情報ライブラリAPI（国土交通省）
REINFOLIB_API_KEY=your_api_key_here
REINFOLIB_API_ENDPOINT=https://www.reinfolib.mlit.go.jp/ex-api/external
REINFOLIB_API_TIMEOUT=30
```

---

## 🔗 関連ドキュメント

- [README.md](../README.md) - プロジェクト全体の説明
- [データベース設計](../README.md#データベース設計) - テーブル構造の詳細

---

## 💡 ヒント

### Windows環境での注意点

- PowerShellでは `&&` が使えないため、コマンドを分けて実行
- パス区切り文字は自動的に `/` に正規化される（`fix_db_paths.py`で修正可能）

### エラーが発生した場合

1. ログファイルを確認: `logs/real_estate_bot.log`
2. データベース接続を確認: `docker ps`
3. 環境変数を確認: `.env`ファイルの設定

---

**最終更新**: 2025年12月2日


