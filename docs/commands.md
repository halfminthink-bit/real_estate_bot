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
python scripts/post_to_wordpress.py --republish --limit 1

# 全記事のWordPress情報をリセット（再投稿準備）
python scripts/post_to_wordpress.py --reset-all
```

**オプション**:
- `--limit`: 投稿件数制限
- `--republish`: 投稿済み記事も再投稿
- `--reset-all`: 全記事のWordPress情報をリセット
- `--project`: プロジェクトディレクトリ（デフォルト: `projects/setagaya_real_estate`）

### HTML再生成

既存のMarkdownファイルからHTMLを再生成する場合：

```bash
# 全記事のHTMLを再生成
python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml

# 指定件数だけ再生成
python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml --limit 10

# 強制再生成（既存HTMLを上書き）
python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml --force
```

**オプション**:
- `--project`: プロジェクト設定ファイルのパス（必須）
- `--limit`: 再生成する記事数（省略時は全件）
- `--force`: 既存HTMLがあっても強制的に上書き

**用途**:
- アフィリエイト設定変更後のHTML再生成
- テンプレート変更後のHTML再生成
- デザイン修正後のHTML再生成

### アフィリエイトリンク更新（再投稿）

ASP承認後、既存の投稿を更新する場合：

```bash
# 全記事を再HTML化してWordPressを更新
python scripts/republish_articles.py --project projects/setagaya_real_estate/config.yml 

# 指定件数だけ更新
python scripts/republish_articles.py --project projects/setagaya_real_estate/config.yml --limit 10
```

**使用手順**:

1. **ASP承認前**: ダミーリンク（`example.com`）で記事を投稿
   ```bash
   python scripts/post_to_wordpress.py --limit 128
   ```

2. **ASP承認後**: `affiliate_config.yml` を更新
   ```yaml
   affiliates:
     primary:
       url: "https://tracking.example.com/click?id=12345"  # ← 本番リンクに変更
   ```

3. **HTML再生成**: アフィリエイト設定を反映したHTMLを再生成
   ```bash
   python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml --force
   ```

4. **WordPress再投稿**: 既存投稿を更新
   ```bash
   python scripts/republish_articles.py --project projects/setagaya_real_estate/config.yml
   ```

**オプション**:
- `--project`: プロジェクト設定ファイルのパス（必須）
- `--limit`: 更新する記事数（省略時は全件）

**注意**: 
- Markdownファイルはそのまま（データが保全される）
- 投稿ID、URLが変わらない（SEO的に安全）
- 画像も自動的にWordPressにアップロードされる
- 完全自動化可能

### 全投稿のリセットと再投稿

投稿済みの記事を全てリセットして、最初から投稿し直す場合：

```bash
# 1. 全記事のWordPress投稿情報をリセット
python scripts/post_to_wordpress.py --reset-all

# 2. 確認メッセージで 'y' を入力

# 3. リセット後、全記事を再投稿
python scripts/post_to_wordpress.py
```

**注意**:
- `--reset-all` は `wp_post_id`, `wp_url`, `wp_status`, `wp_posted_at` を NULL にリセットします
- 記事のMarkdown/HTMLファイルは削除されません
- リセット後は未投稿状態になるため、通常の投稿コマンドで再投稿できます
- WordPress側の既存投稿は削除されません（手動で削除する必要があります）

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

### ASP承認後のアフィリエイトリンク更新

```bash
# 1. affiliate_config.yml を更新（本番リンクに変更）
# ファイル: projects/setagaya_real_estate/affiliate_config.yml

# 2. 全記事のHTMLを再生成（アフィリエイト設定を反映）
python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml --force

# 3. 生成されたHTMLを確認（アフィリエイトセクションが入っているか）
grep -A 10 "市場全体" projects/setagaya_real_estate/html/世田谷区三軒茶屋1丁目.html

# 4. WordPressに再投稿（既存投稿を更新）
python scripts/republish_articles.py --project projects/setagaya_real_estate/config.yml

# 5. 更新結果を確認
python scripts/show_article_stats.py
```

**または、Pythonから直接実行**:
```bash
# WordPressに再投稿（republisherモジュールを直接使用）
python -c "from modules.wordpress_publisher.republisher import republish_articles; republish_articles('projects/setagaya_real_estate/config.yml')"
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

### 全投稿のリセットと再投稿

```bash
# 1. 全記事のWordPress投稿情報をリセット
python scripts/post_to_wordpress.py --reset-all

# 2. リセット後、全記事を再投稿
python scripts/post_to_wordpress.py
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

---

## 📋 アフィリエイト設定ファイル

### `affiliate_config.yml` の構造

**場所**: `projects/setagaya_real_estate/affiliate_config.yml`

```yaml
# アフィリエイトリンク設定
affiliates:
  primary:
    name: "ミライアス"
    url: "https://px.a8.net/svt/ejp?a8mat=45K45A+DDNS9E+4I6M+614CY"
    button_text: "あなたの土地の価値を確認する（無料）"
    color: "#00B900"

# デフォルト設定
default:
  show_secondary: false
```

**ASP承認後の更新例**:
```yaml
affiliates:
  primary:
    url: "https://tracking.example.com/click?id=12345&siteid=xxx"  # ← 変更
```

**テンプレートファイル**: `projects/setagaya_real_estate/templates/affiliate_section.html`
- HTMLデザインを変更する場合はこのファイルを編集
- 変数プレースホルダー: `{{ choume }}`, `{{ url }}`, `{{ button_text }}`, `{{ color }}`, `{{ name }}`

**更新手順**: 
1. `affiliate_config.yml` を編集（URL、テキスト、色など）
2. `python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml --force` でHTML再生成
3. `python scripts/republish_articles.py --project projects/setagaya_real_estate/config.yml` でWordPress再投稿

**注意**: 
- 設定変更は `affiliate_config.yml` のみ編集（Pythonコードは触らない）
- デザイン変更は `templates/affiliate_section.html` のみ編集

---

**最終更新**: 2025年12月2日


