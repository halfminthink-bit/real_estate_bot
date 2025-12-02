# RealEstateBot - 不動産資産価値証明システム

## 📋 プロジェクト概要

町丁目レベルの**不動産資産価値**を客観的データで証明し、AI記事を自動生成してWordPressに投稿するシステム。

**コンセプト**: 
- ❌ 「これから住む人」向けの物件探し
- ✅ 「すでに住んでいる人」向けの資産価値証明

**ターゲット**: 
自分の土地・建物の価値を知らないオーナーに、客観的データで資産価値を伝え、無料査定へ誘導する。

---

## 🎯 プロジェクトの目的

1. **資産価値の可視化**: 26年間の地価推移、用途地域、建築制限から価値を証明
2. **客観的データの提示**: 国土数値情報（地価公示データ）2000-2025年
3. **AI記事自動生成**: Claude Sonnet 4.5による説得力のある記事
4. **WordPress自動投稿**: 予約投稿で安定的なコンテンツ配信
5. **無料査定への誘導**: 「知ることの大切さ」を伝え、アクションを促す

---

## 🏗️ システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    【データソース】                          │
│  国土数値情報（地価公示 2000-2025年）26年分・全国対応      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                 【PostgreSQL Database】                      │
│  land_prices_kokudo テーブル                                │
│  - 世田谷区: 3,907件（26年分）                              │
│  - 地価、用途地域、建蔽率、容積率、前面道路、駅距離など     │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│          【AI記事生成パイプライン】(modules/)               │
│                                                              │
│  1. データ収集                                              │
│     └─ LandPriceCollector                                  │
│        └─ PostgreSQLから26年分×複数地点のデータ取得        │
│                                                              │
│  2. スコア計算                                              │
│     └─ AssetValueScorer                                    │
│        └─ 地価データから資産価値スコア算出（0-100点）       │
│                                                              │
│  3. グラフ生成                                              │
│     └─ PriceGraphGenerator                                 │
│        └─ 26年間の地価推移グラフ（価格帯レンジ付き）       │
│                                                              │
│  4. 記事生成                                                │
│     └─ ContentGenerator + Claude Sonnet 4.5                │
│        └─ 2段階生成（アウトライン → 本文）                 │
│                                                              │
│  5. HTML出力                                                │
│     └─ HTMLBuilder                                         │
│        └─ Markdown → HTML（インラインCSS）                 │
│                                                              │
│  6. 記事管理                                                │
│     └─ ArticleManager (SQLite)                             │
│        └─ 記事メタデータ、投稿履歴を管理                   │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   【WordPress投稿】                          │
│  WordPressPublisher (modules/wordpress_publisher/)          │
│                                                              │
│  1. 画像アップロード                                         │
│     └─ WordPress Media Library                             │
│     └─ ローカル画像 → WordPressサーバー                    │
│                                                              │
│  2. 記事投稿                                                │
│     └─ WordPress REST API                                  │
│     └─ 予約投稿（1日5件ずつ、18:00）                       │
│                                                              │
│  3. 投稿履歴記録                                            │
│     └─ ArticleManager（SQLite）に記録                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                      【出力】                                │
│  - Markdown記事（output/）                                  │
│  - HTML記事（html/）                                         │
│  - 地価推移グラフ（charts/）                                │
│  - WordPress投稿（自動）                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 現在の実装状況

### ✅ Phase 1: データ基盤構築（完了）

| 項目 | 状態 | 詳細 |
|------|------|------|
| PostgreSQLスキーマ | ✅ 完了 | land_prices_kokudo テーブル |
| 国土数値情報（地価公示） | ✅ 完了 | **3,907件（世田谷区2000-2025年）** |
| 用途地域・建築制限 | ✅ 100% | 26年分すべて完備 |
| データ取得率 | ✅ 100% | 全年度・全項目完備 |

**データ完備状況**:
```
2000-2004年: 845件（バブル崩壊後）
2005-2008年: 672件（ミニバブル期）
2009-2012年: 585件（リーマンショック後）
2013-2017年: 672件（長期上昇開始）
2018-2025年: 1,143件（安定成長期）

合計: 3,907件（26年分完璧）
世田谷区平均地価: 550,420円/㎡（2000年）→ 834,716円/㎡（2025年）
26年間で +51.7%上昇
```

### ✅ Phase 1.5: AI記事生成パイプライン（完了）

| モジュール | 状態 | 機能 |
|-----------|------|------|
| LandPriceCollector | ✅ 完了 | PostgreSQLから26年分×複数地点データ取得 |
| AssetValueScorer | ✅ 完了 | 資産価値スコア計算（0-100点） |
| PriceGraphGenerator | ✅ 完了 | 地価推移グラフ生成（価格帯レンジ付き） |
| ContentGenerator | ✅ 完了 | Claude Sonnet 4.5で記事生成 |
| HTMLBuilder | ✅ 完了 | Markdown → HTML変換（インラインCSS） |
| ArticleManager | ✅ 完了 | 記事メタデータ・投稿履歴管理（SQLite） |

**記事生成実績**:
- ✅ 141件の記事生成可能（世田谷区全域）
- ✅ 26年間の地価推移グラフ
- ✅ リーマンショック・コロナ禍の注釈
- ✅ 用途地域・建蔽率・容積率の表示
- ✅ インラインCSS（WordPress対応）

### ✅ Phase 2: WordPress自動投稿（完了）

| 項目 | 状態 | 詳細 |
|------|------|------|
| 画像アップロード | ✅ 完了 | Media Libraryに自動アップロード |
| 記事投稿 | ✅ 完了 | REST API経由で予約投稿 |
| 予約投稿 | ✅ 完了 | 1日5件ずつ、18:00 |
| カテゴリ自動作成 | ✅ 完了 | 存在しない場合は自動作成 |
| 投稿履歴管理 | ✅ 完了 | ArticleManagerに記録 |
| スラッグ生成 | ✅ 完了 | 日本語→ローマ字変換 |

**WordPress連携**:
- ✅ Application Password認証
- ✅ Xserver対応（.htaccess設定済み）
- ✅ 画像パス自動置き換え
- ✅ h1タグ自動削除

---

## 📂 ディレクトリ構成

```
real_estate_bot/
├── config/
│   └── database.yml                    # PostgreSQL設定
│
├── db/
│   ├── schema.sql                      # PostgreSQLスキーマ
│   └── migrations/
│
├── modules/                            # コアモジュール
│   ├── data_aggregator/
│   │   └── collectors/
│   │       ├── land_price_collector.py # 地価データ取得
│   │       └── transaction_price_collector.py # 取引価格データ取得（不動産情報ライブラリAPI）
│   ├── score_calculator/
│   │   └── scorers/
│   │       └── asset_value_scorer.py   # スコア計算
│   ├── chart_generator/
│   │   └── price_graph_generator.py    # グラフ生成
│   ├── content_generator/
│   │   └── generator.py                # AI記事生成
│   ├── html_builder/
│   │   └── builder.py                  # HTML変換
│   ├── article_manager/
│   │   └── manager.py                  # 記事管理（SQLite）
│   └── wordpress_publisher/            # WordPress投稿
│       └── publisher.py                # 投稿処理
│
├── scripts/                            # ユーティリティ
│   ├── import_kokudo_all_years.py      # 地価データインポート
│   ├── post_to_wordpress.py            # WordPress投稿実行
│   └── test_reinfolib_api.py           # 不動産情報ライブラリAPIテスト
│
├── projects/setagaya_real_estate/      # プロジェクトディレクトリ
│   ├── config.yml                      # プロジェクト設定（target_ward, survey_year）
│   ├── data/
│   │   └── (areas.csvは不要 - PostgreSQLから直接取得)
│   ├── prompts/
│   │   ├── persona.txt                 # LLMペルソナ
│   │   ├── outline.txt                 # アウトライン生成
│   │   └── content.txt                 # 本文生成
│   ├── output/                         # Markdown記事
│   ├── html/                           # HTML記事
│   ├── charts/                         # グラフ画像
│   └── articles.db                     # 記事管理DB（SQLite）
│
├── main_orchestrator.py                # メイン実行
├── docker-compose.yml                  # PostgreSQL
├── .env                                # 環境変数
└── README.md
```

---

## 📊 データベース設計

### PostgreSQL: land_prices_kokudo テーブル

```sql
-- 地価公示データ（26年分×複数地点）
CREATE TABLE land_prices_kokudo (
    id SERIAL PRIMARY KEY,
    
    -- 基本情報
    survey_year INTEGER NOT NULL,              -- 調査年度（2000-2025）
    original_address TEXT NOT NULL,            -- 住所（例: 上用賀6丁目103番7）
    choume_code VARCHAR(11),                   -- 町丁目コード（任意）
    
    -- 地価データ
    official_price INTEGER NOT NULL,           -- 地価（円/㎡）
    
    -- 土地情報
    land_area INTEGER,                         -- 地積（㎡）
    land_use VARCHAR(50),                      -- 用途地域（1低専、近商、商業など）
    building_coverage_ratio INTEGER,           -- 建蔽率（%）
    floor_area_ratio INTEGER,                  -- 容積率（%）
    
    -- 前面道路
    road_direction VARCHAR(10),                -- 方位（北、南、東、西など）
    road_width NUMERIC(5,1),                   -- 幅員（m）
    
    -- アクセス
    nearest_station VARCHAR(100),              -- 最寄駅
    station_distance INTEGER,                  -- 駅距離（m）
    
    -- ユニーク制約
    UNIQUE(survey_year, original_address)
);

-- インデックス
CREATE INDEX idx_address ON land_prices_kokudo(original_address);
CREATE INDEX idx_survey_year ON land_prices_kokudo(survey_year);
```

**検索方法**:
```sql
-- 町丁目で検索（LIKE検索）
SELECT * FROM land_prices_kokudo
WHERE original_address LIKE '%上用賀6丁目%';

-- 年度別の平均・最小・最大
SELECT 
    survey_year,
    COUNT(*) as point_count,
    AVG(official_price)::INTEGER as avg_price,
    MIN(official_price) as min_price,
    MAX(official_price) as max_price
FROM land_prices_kokudo
WHERE original_address LIKE '%上用賀6丁目%'
GROUP BY survey_year
ORDER BY survey_year;
```

---

### SQLite: articles テーブル（ArticleManager）

```sql
-- 記事管理データベース
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 地域情報
    ward TEXT NOT NULL,                        -- 区（世田谷区）
    choume TEXT NOT NULL,                      -- 町丁目（上用賀6丁目）
    
    -- ファイルパス（プロジェクトディレクトリからの相対パス）
    markdown_path TEXT,                        -- output/世田谷区上用賀6丁目.md
    html_path TEXT,                            -- html/世田谷区上用賀6丁目.html
    chart_path TEXT,                           -- charts/世田谷_上用賀6_price_graph.png
    
    -- 記事情報
    title TEXT,                                -- タイトル
    word_count INTEGER,                        -- 文字数
    
    -- WordPress情報
    wp_post_id INTEGER,                        -- WordPress投稿ID
    wp_url TEXT,                               -- WordPress URL
    wp_status TEXT,                            -- 投稿ステータス（future, publish）
    wp_posted_at TIMESTAMP,                    -- 投稿日時
    
    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- ユニーク制約
    UNIQUE(ward, choume)
);

-- 投稿履歴テーブル
CREATE TABLE post_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    action TEXT NOT NULL,                      -- posted, updated, deleted
    status TEXT NOT NULL,                      -- success, failed
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
```

---

## 🚀 実行方法

### 1. 環境構築（初回のみ）

```bash
# リポジトリをクローン
git clone <repository-url>
cd real_estate_bot

# Python仮想環境を作成
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 依存パッケージをインストール
pip install -r requirements.txt
```

### 2. 環境変数設定

**.envファイルを作成**:
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
REINFOLIB_API_KEY=your_api_key_here_after_application
REINFOLIB_API_ENDPOINT=https://www.reinfolib.mlit.go.jp/ex-api/external
REINFOLIB_API_TIMEOUT=30
```

### 3. データベース起動

```bash
# PostgreSQLをDockerで起動
docker-compose up -d

# 接続確認
docker exec -it real_estate_db psql -U postgres -d real_estate_dev
```

### 4. 地価データインポート（初回のみ）

```bash
# 26年分（2000-2025年）を一括インポート
python scripts/import_kokudo_all_years.py
```

**期待される結果**:
```
✅ 成功: 26年分 / 3,907件
✅ 失敗: 0年分
```

### 5. AI記事生成

**重要**: 町丁目リストはPostgreSQLから自動取得されます。`areas.csv`ファイルは不要です。

```bash
# 1件テスト
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --limit 1

# 全件生成（PostgreSQLから取得した全町丁目）
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --limit 141
```

**町丁目リストの取得**:
- `core/area_loader.py`がPostgreSQLから直接取得
- `config.yml`の`target_ward`と`survey_year`で対象を指定
- CSVファイルへの依存を排除し、常に最新データを使用

**生成されるファイル**:
```
projects/setagaya_real_estate/
├── output/世田谷区上用賀6丁目.md           # Markdown
├── html/世田谷区上用賀6丁目.html           # HTML
├── charts/世田谷_上用賀6_price_graph.png  # グラフ
└── articles.db                            # 記事管理DB（自動更新）
```

### 6. WordPress投稿

```bash
# 1件テスト投稿
python scripts/post_to_wordpress.py --limit 1

# 全件投稿（予約投稿）
python scripts/post_to_wordpress.py --limit 141
```

**投稿ルール**:
- 1日5件ずつ
- 毎日18:00に予約投稿
- 画像は自動アップロード
- カテゴリは自動作成

---

## 🔧 主要コマンド一覧

### データベース操作

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

# 終了
\q
```

### 記事管理（ArticleManager）

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

### 不動産情報ライブラリAPIテスト

```bash
# APIキーを.envに設定（申請後）
# REINFOLIB_API_KEY=your_api_key_here

# テストスクリプト実行
python scripts/test_reinfolib_api.py

# 出力結果確認
ls -lh output/test_api_results/
cat output/test_api_results/setagaya_2024q3.json | head -50
```

**テスト内容**:
- TEST 1: 世田谷区全体の取引データ取得（2024年Q3）
- TEST 2: 特定の町丁目（上用賀6丁目）の取引データ取得
- TEST 3: 複数年度のトレンド確認（2020-2024年）
- TEST 4: レスポンスデータ構造の分析

### トラブルシューティング

```bash
# PostgreSQLログ確認
docker logs real_estate_db

# PostgreSQL再起動
docker-compose restart

# 記事再生成（強制）
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --force \
  --limit 1
```

---

## 🎯 取得データ詳細

### 上用賀6丁目の実例

```
【26年間の地価推移】
2000年: 500,000円/㎡
2008年: 588,000円/㎡（リーマンショック前ピーク）
2009年: 521,000円/㎡（リーマン後）
2020年: 570,000円/㎡（コロナ禍）
2025年: 649,000円/㎡（+29.8% / 26年間）

【最新データ（2025年）】
✅ 地価: 649,000円/㎡
✅ 用途地域: 1低専（第一種低層住居専用地域）
✅ 建蔽率: 50%
✅ 容積率: 100%
✅ 前面道路: 西向き 6.0m
✅ 地積: 151㎡
✅ 最寄駅: 用賀駅 1,500m

【資産価値スコア】
✅ 85/100点
```

---

## 🌐 WordPress連携

### WordPress REST API設定

1. **Application Password作成**
   ```
   WordPress管理画面 → ユーザー → プロフィール
   → アプリケーションパスワード → 新規追加
   ```

2. **Xserver用 .htaccess設定**
   ```apache
   # WordPress/.htaccess に追加
   SetEnvIf Authorization "(.*)" HTTP_AUTHORIZATION=$1
   RewriteCond %{HTTP:Authorization} ^(.+)$
   RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
   ```

3. **パーマリンク設定**
   ```
   設定 → パーマリンク → 投稿名
   ```

### 投稿ステータス

| ステータス | 説明 |
|----------|------|
| future | 予約投稿（指定日時に自動公開） |
| publish | 即時公開 |
| draft | 下書き |

---

## 🔄 ワークフロー

### 通常運用フロー

```bash
# 1. 新しい記事を生成（週1回など）
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --limit 10

# 2. 生成された記事を確認
ls projects/setagaya_real_estate/html/

# 3. WordPress投稿（予約投稿）
python scripts/post_to_wordpress.py --limit 10

# 4. WordPress管理画面で確認
# → 投稿 → 予約投稿
```

### メンテナンスフロー

```bash
# 記事再生成（既存ファイルを上書き）
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --force \
  --limit 1

# 投稿済み記事の更新
python scripts/post_to_wordpress.py --republish --limit 1

# データベース再構築
docker-compose down -v
docker-compose up -d
python scripts/import_kokudo_all_years.py
```

---

## 📈 今後の展開

### Phase 3: 機能拡張（計画中）

- [ ] 他の市区町村への展開（渋谷区、目黒区など）
- [ ] 世田谷区内での相対評価（区内順位）
- [ ] e-Stat人口データ統合
- [ ] 周辺相場との比較機能

### Phase 4: サイト改善（計画中）

- [ ] SEO最適化
- [ ] 内部リンク自動生成
- [ ] サイトマップ自動更新
- [ ] Google Analytics連携

---

## 🚨 重要な注意事項

### データの制約

1. **調査地点数**
   - 1町丁目あたり1-3地点程度
   - 地点が少ない場合、価格の幅（レンジ）は表示されない

2. **調査地点の変更**
   - 年度によって調査地点が変わる場合がある
   - グラフには注記を表示

3. **choume_code**
   - PostgreSQLの`choume_code`は空の場合あり
   - `original_address`でLIKE検索を使用

### WordPress投稿

1. **画像アップロード**
   - `chart_path`が空の記事は画像なしで投稿される
   - 記事生成時に必ず`chart_path`が設定されるよう確認

2. **予約投稿**
   - 1日5件ずつ、18:00に予約
   - 最終投稿日から継続してスケジューリング

3. **認証エラー**
   - Xserverの場合、.htaccess設定が必須
   - Application Passwordのスペースを削除

---

## 📚 参考資料

- [国土数値情報（国土交通省）](https://nlftp.mlit.go.jp/ksj/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [WordPress REST API](https://developer.wordpress.org/rest-api/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

## 📝 データ取得の変更点（v2.0）

### PostgreSQLから直接取得

**変更前（v1.x）**:
- `areas.csv`ファイルに町丁目リストを手動管理
- CSVとPostgreSQLのデータが一致しない可能性
- 新しい町丁目を追加するたびにCSV更新が必要

**変更後（v2.0）**:
- ✅ PostgreSQLから直接町丁目リストを取得（`core/area_loader.py`）
- ✅ 常に最新のデータを使用
- ✅ CSVファイルへの依存を排除
- ✅ データの一元管理

**使用方法**:
```python
from core.area_loader import AreaLoader

loader = AreaLoader()
areas = loader.get_choume_list('世田谷区', 2025)
# [('世田谷区', '上用賀1丁目'), ('世田谷区', '上用賀6丁目'), ...]
```

**設定**:
```yaml
# config.yml
project:
  target_ward: "世田谷区"
  survey_year: 2025  # PostgreSQLから取得する対象年度
```

**メリット**:
1. **データの一元管理**: PostgreSQLが唯一の真実のソース
2. **常に最新**: 新しいデータが追加されれば自動的に反映
3. **整合性保証**: CSVとPostgreSQLの不整合が発生しない
4. **拡張性**: 他の市区町村への展開が容易

---

## 📄 ライセンス

MIT License

---

## 🎉 Phase 2完成！

**データ基盤 + AI記事生成 + WordPress自動投稿が完全稼働中** 🚀

## 📝 データ取得の変更点（v2.0）

### PostgreSQLから直接取得

**変更前（v1.x）**:
- `areas.csv`ファイルに町丁目リストを手動管理
- CSVとPostgreSQLのデータが一致しない可能性
- 新しい町丁目を追加するたびにCSV更新が必要

**変更後（v2.0）**:
- ✅ PostgreSQLから直接町丁目リストを取得（`core/area_loader.py`）
- ✅ 常に最新のデータを使用
- ✅ CSVファイルへの依存を排除
- ✅ データの一元管理

**使用方法**:
```python
from core.area_loader import AreaLoader

loader = AreaLoader()
areas = loader.get_choume_list('世田谷区', 2025)
# [('世田谷区', '上用賀1丁目'), ('世田谷区', '上用賀6丁目'), ...]
```

**設定**:
```yaml
# config.yml
project:
  target_ward: "世田谷区"
  survey_year: 2025  # PostgreSQLから取得する対象年度
```

---

次のステップ：全国展開・機能拡張へ