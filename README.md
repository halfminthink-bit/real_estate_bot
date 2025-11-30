# RealEstateBot - データ基盤 & 記事生成システム

## 📋 プロジェクト概要

町丁目レベルの住みやすさ×不動産資産価値を分析し、記事を自動生成するシステム。

**現在の状態**:
- ✅ **Phase 1**: データ基盤構築完了（PostgreSQL + 国土数値情報）
- ✅ **Phase 1 MVP**: AI記事生成パイプライン完了（既存実装）
- 🚧 **Phase 2**: データソース統合・分析機能強化（計画中）

---

## 🎯 プロジェクトの目的

1. **データドリブンな不動産分析**: 公的データ（国土数値情報、e-Stat）を活用
2. **町丁目レベルの詳細分析**: 区・市レベルではなく、より細かい町丁目単位
3. **資産価値の可視化**: 地価推移、人口動態を基にしたスコアリング
4. **AI記事自動生成**: Claude Sonnet 4.5による高品質な記事作成

---

## 🏗️ アーキテクチャ

### データフロー

```
[国土数値情報] ───┐
[東京都オープンデータ] ─┤
[e-Stat API]  ───┘
        ↓
   データ収集（collectors）
        ↓
   データ変換（converters）
        ↓
   PostgreSQL Database
        ↓
   データ分析（analysis）
        ↓
   AI記事生成（LLM）
        ↓
   HTML出力
```

### ディレクトリ構成

```
real_estate_bot/
├── config/                # 設定ファイル
│   ├── database.yml      # DB接続設定
│   ├── data_sources.yml  # データソース定義
│   └── project.yml       # プロジェクト設定
│
├── db/                   # データベース
│   ├── schema.sql       # スキーマ定義
│   └── migrations/      # マイグレーション
│
├── src/                  # Phase 1: 新しい実装
│   ├── models/          # データモデル
│   ├── collectors/      # データ収集
│   ├── converters/      # データ変換
│   ├── database/        # データベース操作
│   ├── analysis/        # データ分析
│   ├── llm/             # LLM連携
│   └── utils/           # ユーティリティ
│
├── modules/              # Phase 1 MVP: 既存実装（AI記事生成）
│   ├── data_aggregator/
│   ├── score_calculator/
│   ├── chart_generator/
│   ├── content_generator/
│   └── html_builder/
│
├── scripts/              # 実行スクリプト
│   ├── 01_setup_database.py    # DB初期化
│   ├── 02_download_data.py     # データダウンロード
│   └── 03_import_data.py       # データインポート
│
└── data/                 # データファイル
    ├── raw/             # 生データ
    └── processed/       # 変換後データ
```

---

## 🚀 クイックスタート

### 1. 環境構築

```bash
# リポジトリをクローン
git clone <repository-url>
cd real_estate_bot

# Python仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .envファイルを編集
```

### 2. データベースセットアップ（Phase 1）

```bash
# PostgreSQLを起動（Dockerの場合）
docker run -d \
  --name real_estate_postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=real_estate_dev \
  -p 5432:5432 \
  postgres:14

# 環境変数を設定
export DB_PASSWORD=yourpassword

# データベース初期化
python scripts/01_setup_database.py
```

### 3. データ収集とインポート

```bash
# 国土数値情報から地価データをダウンロード
python scripts/02_download_data.py --year 2024 --prefecture 13

# データベースにインポート
python scripts/03_import_data.py --csv data/processed/master/kokudo_land_price_2024_13.csv
```

### 4. AI記事生成（Phase 1 MVP）

```bash
# 環境変数にANTHROPIC_API_KEYを設定
export ANTHROPIC_API_KEY=sk-ant-xxxx

# 記事生成（既存実装）
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --mode full \
  --limit 5
```

---

## 📊 データベーススキーマ

### マスタテーブル

- `prefectures`: 都道府県マスタ
- `cities`: 市区町村マスタ
- `choume`: 町丁目マスタ

### 時系列データテーブル

- `land_prices`: 地価公示データ（年次）
- `population`: 人口データ（国勢調査、5年ごと）

### 集計・分析テーブル

- `land_price_summary`: 地価推移サマリー
- `population_summary`: 人口推移サマリー
- `area_scores`: エリアスコア計算結果
- `graph_data`: グラフデータ（Chart.js形式）

---

## 📦 データソース

| データソース | 内容 | 更新頻度 | Phase |
|------------|------|---------|-------|
| 国土数値情報 | 地価公示 | 年次 | ✅ Phase 1 |
| 東京都オープンデータ | 地価調査 | 年次 | 🚧 Phase 2 |
| e-Stat | 人口統計 | 5年ごと | 🚧 Phase 2 |
| 警視庁 | 犯罪統計 | 月次 | 🚧 Phase 2 |

---

## 🔧 Phase 1実装状況

### ✅ 完了

- [x] PostgreSQLスキーマ設計
- [x] データベース接続管理（connection.py）
- [x] 国土数値情報コレクター（kokudo_collector.py）
- [x] データ変換モジュール（unified_schema.py, converters）
- [x] 住所正規化（address_normalizer.py）
- [x] リポジトリパターン（repository.py）
- [x] データインポートスクリプト（scripts/01-03）

### 🚧 Phase 2計画

- [ ] e-Stat API連携（人口データ）
- [ ] 東京都オープンデータ連携
- [ ] データ分析モジュール（trend_calculator, score_calculator）
- [ ] グラフ生成（Chart.js形式）
- [ ] 新旧実装の統合

---

## 🛠️ 技術スタック

### データ基盤（Phase 1）

- **Database**: PostgreSQL 14+
- **GIS処理**: GeoPandas
- **データ検証**: Pydantic
- **API**: psycopg2

### AI記事生成（Phase 1 MVP）

- **LLM**: Anthropic Claude Sonnet 4.5
- **データ処理**: Pandas
- **グラフ生成**: Matplotlib
- **HTML生成**: Markdown + Jinja2

### 共通

- **言語**: Python 3.11+
- **設定管理**: YAML + python-dotenv
- **ロギング**: Loguru

---

## 📝 使用例

### データベースクエリ例

```python
from src.database.connection import get_db_connection
from src.database.repository import LandPriceRepository

# 接続
db = get_db_connection()
conn = db.get_connection()

# リポジトリ作成
repo = LandPriceRepository(conn)

# データ取得
data = repo.get_by_choume_and_year(
    choume_code="13112001001",  # 二子玉川1丁目
    survey_year=2024
)

print(data)
```

### データ変換例

```python
from src.converters.kokudo_converter import KokudoLandPriceConverter
import pandas as pd

# CSVデータ読み込み
df = pd.read_csv("data/processed/master/kokudo_land_price_2024_13.csv")

# 変換
converter = KokudoLandPriceConverter()
records = converter.convert_dataframe(df)

print(f"Converted {len(records)} records")
```

---

## 🐛 トラブルシューティング

### データベース接続エラー

```bash
# エラー: psycopg2.OperationalError: could not connect to server
# 解決策: 環境変数を確認
echo $DB_PASSWORD
echo $DB_HOST

# または、.envファイルを確認
cat .env
```

### GMLファイル読み込みエラー

```bash
# エラー: No GML file found
# 解決策: ダウンロードURLを確認（年度によってURLが変わる可能性あり）
# src/collectors/kokudo_collector.py の _build_download_url() を確認
```

---

## 📚 参考資料

- [国土数値情報（国土交通省）](https://nlftp.mlit.go.jp/ksj/)
- [東京都オープンデータ](https://www.opendata.metro.tokyo.lg.jp/)
- [e-Stat（政府統計ポータル）](https://www.e-stat.go.jp/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Anthropic Claude API](https://docs.anthropic.com/)

---

## 📄 ライセンス

MIT License

---

## 👥 コントリビューター

プロジェクト開発者: [Your Name]

---

**Phase 1データ基盤構築完了！次のステップでデータ分析・記事生成機能を統合予定** 🚀
