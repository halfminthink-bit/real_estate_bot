# RealEstateBot - 不動産資産価値証明システム

## 📋 プロジェクト概要

町丁目レベルの**不動産資産価値**を客観的データで証明し、AI記事を自動生成するシステム。

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
4. **無料査定への誘導**: 「知ることの大切さ」を伝え、アクションを促す

---

## 🏗️ システムアーキテクチャ

```
【データソース】
  国土数値情報（地価公示 2000-2025年）
  ✅ 26年分・全国対応
        ↓
  PostgreSQL Database
  （世田谷区 3,907件）
  ✅ 26年分すべて100%完備
        ↓
【AI記事生成パイプライン（modules/）】
  1. データ収集（LandPriceCollector）
  2. スコア計算（AssetValueScorer）
  3. グラフ生成（ChartGenerator）
  4. 記事生成（ContentGenerator + Claude Sonnet 4.5）
  5. HTML出力（HTMLBuilder）
        ↓
【出力】
  Markdown記事 + HTML + 26年間の地価推移グラフ
```

---

## 📊 現在の実装状況

### ✅ Phase 1: データ基盤構築（完了）

| 項目 | 状態 | 詳細 |
|------|------|------|
| PostgreSQLスキーマ | ✅ 完了 | マスタ + 時系列データ |
| 国土数値情報（地価公示） | ✅ 完了 | **3,907件（世田谷区2000-2025年）** |
| 用途地域・建築制限 | ✅ 完了 | 26年分すべて100% |
| choume_code設定 | ✅ 完了 | 世田谷区平均計算可能 |
| データ取得率 | ✅ 100% | 全年度・全項目完備 |

**データ完備状況（2025年11月30日時点）**:
```
2000-2004年: 845件（パブル崩壊後）
2005-2008年: 672件（ミニバブル期）
2009-2012年: 585件（リーマンショック後）
2013-2017年: 672件（長期上昇開始）
2018-2025年: 1,143件（安定成長期）

合計: 3,907件（26年分完璧）
世田谷区平均地価: 550,420円/㎡（2000年）→ 834,716円/㎡（2025年）
26年間で +51.7%上昇
```

### ✅ Phase 1.5: 国土数値情報統合（完了）

| 項目 | 状態 | 内容 |
|------|------|------|
| 用途地域 | ✅ 100% | 1低専、近商、商業など（全年度） |
| 建蔽率・容積率 | ✅ 100% | 建築制限データ（全年度） |
| 前面道路 | ✅ 100% | 方位・幅員（全年度） |
| 地積 | ✅ 100% | 土地面積（全年度） |
| 最寄駅 | ✅ 100% | 駅名・距離（全年度） |
| choume_code | ✅ 100% | 世田谷区内の町丁目コード |

### ✅ Phase 1 MVP: AI記事生成パイプライン（完了）

| モジュール | 状態 | 機能 |
|-----------|------|------|
| LandPriceCollector | ✅ 完了 | PostgreSQLから26年分の地価データ取得 |
| AssetValueScorer | ✅ 完了 | 地価データから資産価値スコア計算（0-100点） |
| ChartGenerator | ✅ 完了 | **26年間の地価推移グラフ生成**（Matplotlib） |
| ContentGenerator | ✅ 完了 | Claude Sonnet 4.5で記事生成 |
| HTMLBuilder | ✅ 完了 | Markdown → HTML変換 |

**記事生成実績**:
- ✅ 141件の記事生成可能（世田谷区全域）
- ✅ 用途地域・建蔽率・容積率の正確な表示
- ✅ 世田谷区平均との比較
- ✅ **26年間の地価推移グラフ**
- ✅ リーマンショック・コロナ禍での底堅さを証明

---

## 🚀 クイックスタート

### 1. 環境構築

```bash
# リポジトリをクローン
git clone <repository-url>
cd real_estate_bot

# Python仮想環境を作成
python -m venv venv
venv\Scripts\activate  # Windows

# 依存パッケージをインストール
pip install -r requirements.txt
```

### 2. 環境変数設定

```bash
# .envファイルを作成
DB_PASSWORD=postgres
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 3. PostgreSQL起動

```bash
docker-compose up -d
```

### 4. データベース初期化（初回のみ）

```bash
# スキーマ作成
python scripts/01_setup_database.py

# 26年分の地価データをインポート
python scripts/import_kokudo_all_years.py
```

**期待される結果**:
```
✅ 成功: 26年分 / 3,907件
✅ 失敗: 0年分
```

### 5. AI記事生成

```bash
# 1件テスト
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --limit 1

# 全件生成（141件）
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --limit 141
```

---

## 🌏 他の地域への展開

### 渋谷区・目黒区など他の区への展開

**ステップ1**: 市区町村コードの確認

| 区 | 市区町村コード | データ件数（推定） |
|---|--------------|-----------------|
| 世田谷区 | 13112 | 3,907件 |
| 渋谷区 | 13113 | 約1,500件 |
| 目黒区 | 13110 | 約1,200件 |
| 大田区 | 13111 | 約2,400件 |

**ステップ2**: データインポート

```bash
# scripts/import_kokudo_all_years.py を編集
# CITY_CODE = '13112' を変更

# 例: 渋谷区
CITY_CODE = '13113'

# 再実行
python scripts/import_kokudo_all_years.py
```

**ステップ3**: プロジェクト設定変更

```bash
# projects/shibuya_real_estate/ を作成
# config.yml を編集
city_code: '13113'
city_name: '渋谷区'
```

**ステップ4**: 記事生成

```bash
python main_orchestrator.py \
  --project projects/shibuya_real_estate/config.yml \
  --limit 100
```

### 全国展開（横浜・川崎・さいたまなど）

地価公示データは**全国対応**のため、市区町村コードを変更するだけで展開可能：

| 都市 | 市区町村コード | 例 |
|-----|--------------|---|
| 横浜市 | 14100-14118 | 14104（中区）など |
| 川崎市 | 14130-14137 | 14133（中原区）など |
| さいたま市 | 11100-11110 | 11102（中央区）など |
| 千葉市 | 12100-12106 | 12101（中央区）など |

---

## 📊 データベーススキーマ

### メインテーブル

```sql
-- 地価公示データ（26年分）
land_prices_kokudo (
    id SERIAL PRIMARY KEY,
    choume_code VARCHAR(11),         -- 町丁目コード
    survey_year INTEGER NOT NULL,    -- 年度（2000-2025）
    official_price INTEGER NOT NULL, -- 地価（円/㎡）
    original_address TEXT,           -- 住所
    land_area INTEGER,               -- 地積（㎡）
    land_use VARCHAR(50),            -- 用途地域
    building_coverage_ratio INTEGER, -- 建蔽率（%）
    floor_area_ratio INTEGER,        -- 容積率（%）
    road_direction VARCHAR(10),      -- 前面道路方位
    road_width NUMERIC(5,1),         -- 前面道路幅員（m）
    nearest_station VARCHAR(100),    -- 最寄駅
    station_distance INTEGER,        -- 駅距離（m）
    UNIQUE(survey_year, original_address)
);

-- マスタテーブル
prefectures      -- 都道府県
cities           -- 市区町村
choume           -- 町丁目
```

---

## 🎯 取得データ詳細

### 三軒茶屋1丁目の実例（2025年）

```
【地価データ】
✅ 最新地価: 1,480,000円/㎡
✅ 26年変動率: +80.3%（2000年比）
✅ 5年変動率: +21.3%（2020年比）
✅ 世田谷区平均: 834,716円/㎡
✅ 区内順位: 上位5%

【国土数値情報】
✅ 用途地域: 近商（近隣商業地域）
✅ 建蔽率: 80%
✅ 容積率: 300%
✅ 前面道路: 南向き 5.3m
✅ 地積: 139㎡
✅ 最寄駅: 三軒茶屋駅 200m

【26年間の推移】
✅ 2000年: 820,000円/㎡
✅ 2008年: 1,100,000円/㎡（ピーク）
✅ 2010年: 900,000円/㎡（リーマン後）
✅ 2020年: 1,220,000円/㎡（コロナ禍）
✅ 2025年: 1,480,000円/㎡（過去最高）
```

---

## 📝 生成される記事の構成

### 記事例

```markdown
# 三軒茶屋1丁目の土地、26年間で証明された資産価値

## あなたの土地の資産価値: 100点

### 1. 26年間で証明された価値上昇
- 2000年: 820,000円/㎡
- 2025年: 1,480,000円/㎡
- **26年間で+80.3%上昇**

### 2. リーマンショックでも底堅い
- 2008年ピーク: 1,100,000円/㎡
- 2010年底: 900,000円/㎡
- わずか-18%の下落（世田谷区平均-25%）

### 3. コロナ禍でも上昇継続
- 2020年: 1,220,000円/㎡
- 2025年: 1,480,000円/㎡
- **5年間で+21.3%上昇**

### 4. 世田谷区内でもトップクラス
- 区平均: 834,716円/㎡
- 三軒茶屋: 1,480,000円/㎡
- **区平均より+77%高い**

### 5. 法的に守られた希少な環境
- 用途地域: 近隣商業地域
- 建蔽率80% / 容積率300%
- 商業施設と住宅が共存する希少エリア

## だからこそ、今の正確な価値を知るべき

[無料査定ボタン]
```

---

## 🛠️ 技術スタック

### データ基盤

- **Database**: PostgreSQL 14+ (Docker)
- **ORM/Query**: psycopg2
- **データ処理**: GeoPandas（Shapefile/GeoJSON）
- **データ検証**: Pydantic

### AI記事生成

- **LLM**: Anthropic Claude Sonnet 4.5
- **プロンプト**: 2段階生成（アウトライン → 本文）
- **グラフ**: Matplotlib（26年間の推移グラフ）
- **HTML**: Markdown + テンプレート

### 開発環境

- **言語**: Python 3.11+
- **パッケージ管理**: pip + venv
- **設定**: YAML + python-dotenv
- **ログ**: logging

---

## 📊 データソース

| データソース | 内容 | 更新頻度 | 件数 | 状態 |
|------------|------|---------|------|------|
| 国土数値情報（地価公示） | 地価データ | 年次 | 3,907件 | ✅ 100% |
| 国土数値情報（2000-2025） | 用途地域・建築制限 | 年次 | 3,907件 | ✅ 100% |

**データの信頼性**:
- 国土交通省の公式データ
- 不動産鑑定士による評価
- 毎年1月1日時点の価格

---

## 🎨 ディレクトリ構成

```
real_estate_bot/
├── db/
│   ├── schema.sql
│   └── migrations/
│
├── modules/                          # AI記事生成パイプライン
│   ├── data_aggregator/
│   │   └── collectors/
│   │       └── land_price_collector.py  ← PostgreSQL接続（26年分）
│   ├── score_calculator/
│   │   └── scorers/
│   │       └── asset_value_scorer.py    ← 地価スコア計算
│   ├── chart_generator/                 ← 26年推移グラフ
│   ├── content_generator/               ← Claude Sonnet 4.5
│   └── html_builder/
│
├── scripts/                          # データ準備
│   ├── 01_setup_database.py          ← スキーマ作成
│   ├── import_kokudo_all_years.py    ← ★26年分インポート（メイン）
│   └── archive/                      ← 旧バージョン・テスト用
│
├── projects/setagaya_real_estate/
│   ├── config.yml                    ← プロジェクト設定
│   ├── data/
│   │   └── areas.csv                 ← 処理対象（141件）
│   ├── prompts/
│   │   ├── persona.txt               ← LLMペルソナ
│   │   ├── outline.txt               ← アウトライン生成
│   │   └── content.txt               ← 本文生成
│   ├── output/                       ← Markdown記事
│   ├── charts/                       ← 26年推移グラフ
│   └── html/                         ← 完成HTML
│
├── main_orchestrator.py              ← メイン実行
├── docker-compose.yml                ← PostgreSQL
└── README.md
```

---

## 📈 実装の進捗

### ✅ Phase 1: データ基盤構築（完了）

- [x] PostgreSQLスキーマ設計
- [x] 国土数値情報（地価公示）取り込み（26年分・3,907件）
- [x] 用途地域・建築制限統合（100%）
- [x] 住所正規化（全角・半角対応）
- [x] データ検証スクリプト

### ✅ Phase 1.5: 26年分データ統合（完了）

- [x] 2000-2011年（Shapefile パターンA）
- [x] 2012-2017年（Shapefile パターンB）
- [x] 2018-2025年（GeoJSON パターンC）
- [x] フィールドマッピング統一
- [x] 全年度100%インポート成功

### ✅ Phase 1 MVP: AI記事生成（完了）

- [x] Claude Sonnet 4.5連携
- [x] 2段階生成（アウトライン → 本文）
- [x] 26年推移グラフ生成
- [x] HTML出力
- [x] 141件一括生成可能

### 🚧 Phase 2: 記事品質向上（次のステップ）

- [ ] プロンプト最適化（26年データ活用）
- [ ] グラフデザイン改善
- [ ] リーマンショック・コロナ禍の解説追加
- [ ] 区内順位の表示

### ⏳ Phase 3: 全国展開（計画中）

- [ ] 渋谷区・目黒区のデータ追加
- [ ] 横浜・川崎・さいたまへの展開
- [ ] マルチ市区町村対応UI

---

## 💻 主要スクリプト

### アクティブ（scripts/ - 現在使用中）

| スクリプト | 用途 | 実行頻度 |
|-----------|------|---------|
| `01_setup_database.py` | PostgreSQLスキーマ作成 | 初回のみ |
| `import_kokudo_all_years.py` | **26年分データインポート（メイン）** | 初回・更新時 |
| `verify_sancha_data.py` | データ検証 | 開発時 |
| `test_graph_generation.py` | グラフ生成テスト | 開発時 |
| `test_article_generation.py` | 記事生成テスト | 開発時 |
| `summary_stats.py` | 統計サマリー | 随時 |
| `quick_check.py` | クイック確認 | 随時 |
| `check_db_data.py` | DB確認 | 随時 |
| `main_orchestrator.py` | AI記事生成（メイン） | 随時 |

### アーカイブ（scripts/archive/）

古いバージョン・テスト用スクリプトは`scripts/archive/`に移動済み：

- **old_versions/** - 旧バージョンのインポートスクリプト（6ファイル）
- **completed/** - 一度実行済み・完了したスクリプト（12ファイル）
- **tests/** - テスト用スクリプト（1ファイル）

詳細は`scripts/archive/README.md`を参照。

---

## 🐛 トラブルシューティング

### エラー: 2024-2025年の価格がおかしい

**原因**: フィールドマッピングが間違っている

**解決**:
```python
# L01_006 ではなく L01_008 を使用
FIELD_MAPPING_C_V2 = {
    'price': 'L01_008',  # ← 正しい
}
```

### エラー: 世田谷区のデータが0件

**原因**: 市区町村コードフィールドが間違っている

**確認方法**:
```bash
python -c "
import geopandas as gpd
gdf = gpd.read_file('path/to/file.shp')
print(gdf.columns)  # フィールド一覧を確認
"
```

### データ確認

```bash
# 年度別件数確認
docker-compose exec postgres psql -U postgres -d real_estate_dev -c "
SELECT survey_year, COUNT(*), 
       MIN(official_price) as 最小価格,
       MAX(official_price) as 最大価格,
       AVG(official_price)::INTEGER as 平均価格
FROM land_prices_kokudo
GROUP BY survey_year
ORDER BY survey_year;
"
```

---

## 📚 参考資料

- [国土数値情報（国土交通省）](https://nlftp.mlit.go.jp/ksj/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [GeoPandas Documentation](https://geopandas.org/)

---

## 📄 ライセンス

MIT License

---

## 🎉 Phase 1完成！

**データ基盤100%完成 + 26年分データ統合完了**

**世田谷区の26年間の地価推移**:
- 2000年: 550,420円/㎡
- 2008年: 684,673円/㎡（ピーク）
- 2010年: 573,607円/㎡（リーマン後）
- 2020年: 724,748円/㎡（コロナ禍）
- 2025年: 834,716円/㎡（過去最高）

**26年間で+51.7%上昇を客観的データで証明！**

次のステップ：記事品質向上 & 全国展開 🚀