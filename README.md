# RealEstateBot - Phase 1 MVP

## 1. エグゼクティブサマリー

### 1.1. プロジェクトの目的
町丁目レベルの住みやすさ×売却相場という唯一無二のポジションで、不動産売却を検討する人に総合的な判断材料を提供し、アフィリエイト収益月10万円を目指す。

### 1.2. 主要な特徴

| 特徴 | 説明 |
|------|------|
| 唯一無二のポジション | ウチノカチ・LIFULL HOME'Sにない「町丁目×住みやすさ×売却相場」統合 |
| 公的データ基盤 | 警視庁、e-Stat、国土交通省の信頼できるデータのみ使用 |
| スコア化・可視化 | 5軸レーダーチャート（治安・教育・利便性・資産価値・住環境） |
| プログラマティックSEO | 250→1,000ページ自動生成で検索上位独占 |
| CSV→DB移行対応 | 初期はCSV、成長に合わせてDB移行可能な設計 |
| モジュラー設計 | プロンプト・設定を外部化、保守性・拡張性を最大化 |

### 1.3. 技術スタック

- **言語**: Python 3.11+
- **AI**: Claude Sonnet 4.5 (Anthropic)
- **データ管理**: CSV → SQLite → PostgreSQL (段階的移行)
- **外部API**: 警視庁API、e-Stat API、国土数値情報API
- **設定管理**: YAML + python-dotenv
- **可視化**: Matplotlib (レーダーチャート)
- **CMS連携**: WordPress REST API (将来)

---

## 2. クイックスタート

### 2.1. 環境構築

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
# .envファイルを編集してANTHROPIC_API_KEYを設定
```

### 2.2. 最初の記事を生成

```bash
# データ収集のみ実行（APIキー不要）
python main_orchestrator.py 
  --project projects/setagaya_real_estate/config.yml 
  --mode data_only 
  --limit 5

# 全パイプライン実行（記事生成まで）
python main_orchestrator.py 
  --project projects/setagaya_real_estate/config.yml 
  --mode full 
  --limit 1
```

### 2.3. 生成された記事を確認

```bash
# Markdownファイル
ls projects/setagaya_real_estate/output/

# レーダーチャート
ls projects/setagaya_real_estate/charts/

# HTMLファイル
ls projects/setagaya_real_estate/html/
```

---

## 3. プロジェクト構成

```
real_estate_bot/
├── main_orchestrator.py          # メインエントリーポイント
├── requirements.txt               # Python依存パッケージ
├── .env.example                   # 環境変数テンプレート
├── .gitignore                     # Git除外設定
│
├── core/                          # コアモジュール
│   ├── models.py                  # データモデル定義
│   ├── config.py                  # 設定管理
│   ├── data_manager.py            # データ永続化層
│   └── orchestrator.py            # パイプライン制御
│
├── modules/                       # 機能モジュール
│   ├── data_aggregator/           # データ収集
│   │   ├── aggregator.py
│   │   └── collectors/
│   │       ├── base_collector.py
│   │       ├── crime_collector.py
│   │       └── population_collector.py
│   │
│   ├── score_calculator/          # スコア計算
│   │   ├── calculator.py
│   │   └── scorers/
│   │       ├── base_scorer.py
│   │       └── safety_scorer.py
│   │
│   ├── chart_generator/           # レーダーチャート生成
│   │   └── generator.py
│   │
│   ├── content_generator/         # AI記事生成
│   │   ├── generator.py
│   │   └── llm/
│   │       ├── base_client.py
│   │       └── anthropic_client.py
│   │
│   └── html_builder/              # HTML生成
│       └── builder.py
│
├── projects/                      # プロジェクト別設定
│   └── setagaya_real_estate/
│       ├── config.yml             # プロジェクト設定
│       ├── scoring_rules.yml      # スコアリングルール
│       ├── affiliate_config.yml   # アフィリエイト設定
│       ├── data/                  # データファイル
│       │   ├── areas.csv
│       │   └── crime_data.csv
│       ├── prompts/               # AIプロンプト
│       │   ├── persona.txt
│       │   ├── outline.txt
│       │   └── content.txt
│       ├── templates/             # HTMLテンプレート
│       │   └── article_template.html
│       ├── output/                # 生成されたMarkdown
│       ├── charts/                # 生成されたレーダーチャート
│       └── html/                  # 生成されたHTML
│
└── logs/                          # ログファイル
    └── real_estate_bot.log
```

---

## 4. 使い方

### 4.1. コマンドラインオプション

```bash
python main_orchestrator.py [OPTIONS]
```

**必須オプション:**
- `--project`: プロジェクト設定ファイルのパス

**任意オプション:**
- `--mode`: 実行モード（デフォルト: `full`）
  - `full`: データ収集 + 記事生成
  - `data_only`: データ収集のみ
  - `generate_only`: 記事生成のみ（既存データを使用）
- `--limit`: 処理する町丁目の最大数（デフォルト: 10）
- `--debug`: デバッグモードで実行

### 4.2. 使用例

```bash
# 5つの町丁目のデータ収集のみ
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --mode data_only \
  --limit 5

# 全パイプライン実行（記事生成まで）
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --mode full \
  --limit 5

# デバッグモードで実行
python main_orchestrator.py \
  --project projects/setagaya_real_estate/config.yml \
  --mode full \
  --limit 1 \
  --debug
```

---

## 5. 設定ファイルのカスタマイズ

### 5.1. プロジェクト設定（config.yml）

プロジェクト全体の設定を管理します。

```yaml
project:
  name: "setagaya_real_estate"
  version: "1.0"

llm:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"
  temperature: 0.7
  max_tokens: 8000
```

### 5.2. スコアリングルール（scoring_rules.yml）

各スコアの計算ルールを定義します。

```yaml
safety:
  excellent:
    max_crimes: 30
    score_range: [90, 100]
  good:
    max_crimes: 50
    score_range: [70, 89]
```

### 5.3. アフィリエイト設定（affiliate_config.yml）

アフィリエイトリンクの設定を管理します。

```yaml
ieul:
  name: "イエウール"
  url: "https://example.com/ieul"
  text: "無料で複数社に一括査定を依頼する"
  button_color: "#FF6B35"
```

### 5.4. AIプロンプト（prompts/*.txt）

記事生成のプロンプトを外部ファイルで管理します。

- `persona.txt`: ライターのペルソナ定義
- `outline.txt`: アウトライン生成プロンプト
- `content.txt`: 本文生成プロンプト

---

## 6. Phase 1 MVPの制限事項

Phase 1では以下の機能は簡易実装またはダミーデータです：

- **人口データ**: ダミー値（Phase 2でe-Stat API実装予定）
- **施設データ**: ダミー値（Phase 2で実装予定）
- **教育スコア**: ダミー値（Phase 2で実装予定）
- **利便性スコア**: ダミー値（Phase 2で実装予定）
- **資産価値スコア**: ダミー値（Phase 2で実装予定）
- **住環境スコア**: ダミー値（Phase 2で実装予定）

**実装済み機能:**
- ✅ 犯罪データ収集（CSV）
- ✅ 治安スコア計算
- ✅ レーダーチャート生成
- ✅ AI記事生成（2段階: アウトライン→本文）
- ✅ HTML生成

---

## 7. トラブルシューティング

### 7.1. ANTHROPIC_API_KEYが設定されていない

```bash
Error: ANTHROPIC_API_KEY is not set
```

**解決方法:**
```bash
# .envファイルを編集
cp .env.example .env
# .envにANTHROPIC_API_KEY=your-api-keyを追加
```

### 7.2. データファイルが見つからない

```bash
Error: File not found: projects/setagaya_real_estate/data/areas.csv
```

**解決方法:**
データファイルが正しい場所に配置されているか確認してください。

### 7.3. 日本語フォントが表示されない

レーダーチャートで日本語が文字化けする場合、matplotlibのフォント設定を確認してください。

---

## 8. 次のステップ（Phase 2計画）

Phase 2では以下の機能を実装予定：

1. **e-Stat API連携**: 人口統計データの取得
2. **施設データ収集**: 学校、保育園、駅、店舗データ
3. **全スコアの実装**: 教育、利便性、資産価値、住環境
4. **データベース移行**: CSV → SQLite
5. **自動化**: cron/GitHub Actionsでの定期実行
6. **WordPress連携**: 記事の自動投稿

---

## 9. ライセンス

MIT License

---

## 10. お問い合わせ

質問や提案がある場合は、Issueを作成してください。
