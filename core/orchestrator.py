from pathlib import Path
import logging
from typing import Optional, List
from datetime import datetime

from core.config import ProjectConfig
from core.data_manager import CSVDataManager
from core.models import Area, ScoreResult
from core.area_loader import AreaLoader

logger = logging.getLogger(__name__)

class Orchestrator:
    """パイプライン全体の制御"""

    def __init__(self, config: ProjectConfig):
        self.config = config
        self.data_manager = CSVDataManager(config.data_dir)
        self.area_loader = AreaLoader()
        self.logger = logging.getLogger(__name__)

        # 処理したarea_idを保持
        self.processed_area_ids = []

        # 各モジュールは後で初期化
        self.data_aggregator = None
        self.score_calculator = None
        self.chart_generator = None
        self.content_generator = None
        self.html_builder = None
        self.article_manager = None

    def set_modules(self, data_aggregator=None, score_calculator=None,
                   chart_generator=None, content_generator=None, html_builder=None,
                   article_manager=None):
        """各モジュールを設定"""
        self.data_aggregator = data_aggregator
        self.score_calculator = score_calculator
        self.chart_generator = chart_generator
        self.content_generator = content_generator
        self.html_builder = html_builder
        self.article_manager = article_manager

    def run(self, mode: str = "full", limit: int = 10):
        """
        パイプライン実行

        mode:
            - full: 全ステップ実行
            - data_only: データ収集のみ
            - generate_only: 記事生成のみ
        """
        self.logger.info(f"Starting pipeline in {mode} mode")

        if mode in ["full", "data_only"]:
            self._run_data_collection(limit)

        if mode in ["full", "generate_only"]:
            self._run_content_generation(limit)

        self.logger.info("Pipeline completed")

    def _run_data_collection(self, limit: int):
        """データ収集パイプライン"""
        self.logger.info("=== Data Collection Phase ===")

        # 処理したarea_idをリセット
        self.processed_area_ids = []

        # PostgreSQLから町丁目リストを取得
        city_name = self.config._config.get('project', {}).get('target_ward', '世田谷区')
        survey_year = self.config._config.get('project', {}).get('survey_year', 2025)
        
        choume_list = self.area_loader.get_choume_list(
            city_name=city_name,
            survey_year=survey_year
        )
        
        self.logger.info(f"Loaded {len(choume_list)} areas from PostgreSQL")
        
        # 未処理のエリアのみをフィルタリング
        if self.article_manager:
            unprocessed = []
            for ward, choume in choume_list:
                # 既に記事が存在するかチェック
                if not self.article_manager.exists(ward, choume):
                    unprocessed.append((ward, choume))
            
            choume_list = unprocessed
            self.logger.info(f"Filtered to {len(choume_list)} unprocessed areas")
        
        # 制限を適用
        if limit:
            choume_list = choume_list[:limit]
            self.logger.info(f"Limited to {limit} areas")
        
        # Areaオブジェクトに変換（area_idは連番で生成）
        areas = []
        for idx, (ward, choume) in enumerate(choume_list, start=1):
            area = Area(
                area_id=idx,
                ward=ward,
                choume=choume,
                priority='medium',
                status='pending'
            )
            areas.append(area)
        
        self.logger.info(f"Found {len(areas)} areas to process")

        for area in areas:
            try:
                self.logger.info(f"Processing area: {area.ward}{area.choume}")
                self.data_manager.update_area_status(area.area_id, "processing")

                # データ収集
                data = {}
                if self.data_aggregator:
                    data = self.data_aggregator.collect(area)
                    self.logger.info(f"Collected data: {data}")
                else:
                    # データアグリゲーターがない場合は直接CSVから読み込み
                    crime_data = self.data_manager.get_crime_data(area.area_id)
                    if crime_data:
                        data.update(crime_data)

                # スコア計算
                if self.score_calculator:
                    score = self.score_calculator.calculate(area, data)
                    self.data_manager.save_score(score)
                    self.logger.info(f"Calculated score: Total={score.total_score}")

                self.data_manager.update_area_status(area.area_id, "completed")
                self.processed_area_ids.append(area.area_id)

            except Exception as e:
                self.logger.error(f"Error processing area {area.area_id}: {e}", exc_info=True)
                self.data_manager.update_area_status(area.area_id, "error")

    def _run_content_generation(self, limit: int):
        """記事生成パイプライン"""
        self.logger.info("=== Content Generation Phase ===")

        # データ収集フェーズで処理したareaを取得
        if not self.processed_area_ids:
            # generate_onlyモードの場合、PostgreSQLから町丁目リストを取得
            self.logger.info("No areas processed in data collection phase, loading from PostgreSQL")
            city_name = self.config._config.get('project', {}).get('target_ward', '世田谷区')
            survey_year = self.config._config.get('project', {}).get('survey_year', 2025)
            
            choume_list = self.area_loader.get_choume_list(
                city_name=city_name,
                survey_year=survey_year
            )
            
            self.logger.info(f"Loaded {len(choume_list)} areas from PostgreSQL")
            
            # 未処理のエリアのみをフィルタリング
            if self.article_manager:
                unprocessed = []
                for ward, choume in choume_list:
                    # 既に記事が存在するかチェック
                    if not self.article_manager.exists(ward, choume):
                        unprocessed.append((ward, choume))
                
                choume_list = unprocessed
                self.logger.info(f"Filtered to {len(choume_list)} unprocessed areas")
            
            # 制限を適用
            if limit:
                choume_list = choume_list[:limit]
            
            # Areaオブジェクトに変換
            areas = []
            for idx, (ward, choume) in enumerate(choume_list, start=1):
                area = Area(
                    area_id=idx,
                    ward=ward,
                    choume=choume,
                    priority='medium',
                    status='pending'
                )
                areas.append(area)
            
            self.logger.info(f"Found {len(areas)} areas to process")
        else:
            # 処理したarea_idからareaを取得（簡易実装：area_idからward/choumeを推測できないため、PostgreSQLから再取得）
            self.logger.info("Loading processed areas from PostgreSQL")
            city_name = self.config._config.get('project', {}).get('target_ward', '世田谷区')
            survey_year = self.config._config.get('project', {}).get('survey_year', 2025)
            
            choume_list = self.area_loader.get_choume_list(
                city_name=city_name,
                survey_year=survey_year
            )
            
            self.logger.info(f"Loaded {len(choume_list)} areas from PostgreSQL")
            
            # 未処理のエリアのみをフィルタリング
            if self.article_manager:
                unprocessed = []
                for ward, choume in choume_list:
                    # 既に記事が存在するかチェック
                    if not self.article_manager.exists(ward, choume):
                        unprocessed.append((ward, choume))
                
                choume_list = unprocessed
                self.logger.info(f"Filtered to {len(choume_list)} unprocessed areas")
            
            # 処理したarea_idの範囲内のみ取得
            if self.processed_area_ids:
                max_id = max(self.processed_area_ids)
                choume_list = choume_list[:max_id]
            
            # Areaオブジェクトに変換
            areas = []
            for idx, (ward, choume) in enumerate(choume_list, start=1):
                if idx in self.processed_area_ids:
                    area = Area(
                        area_id=idx,
                        ward=ward,
                        choume=choume,
                        priority='medium',
                        status='completed'
                    )
                    areas.append(area)
            
            self.logger.info(f"Found {len(areas)} areas with scores")

        for area in areas:
            try:
                self.logger.info(f"Generating content for: {area.ward}{area.choume}")

                # スコアを取得
                score = self.data_manager.get_score(area.area_id)
                if not score:
                    self.logger.warning(f"No score found for area {area.area_id}, skipping")
                    continue

                # データを取得
                data = {}
                if self.data_aggregator:
                    # data_aggregatorから全データを取得（地価データ含む）
                    data = self.data_aggregator.collect(area)
                else:
                    # フォールバック: CSVから犯罪データのみ取得
                    crime_data = self.data_manager.get_crime_data(area.area_id)
                    if crime_data:
                        data.update(crime_data)

                # レーダーチャートは使用しない（固定セクション方式では不要）
                # 価格グラフはContentGenerator内で生成される
                self.logger.info("Skipping radar chart generation (using price graph instead)")

                # 記事生成
                markdown_content = None
                chart_path = None
                if self.content_generator:
                    markdown_content, chart_path = self.content_generator.generate(area, score, data)

                    # Markdownを保存
                    md_filename = f"{area.ward}{area.choume}.md"
                    md_path = self.config.output_dir / md_filename
                    with open(md_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    self.logger.info(f"Generated markdown: {md_path}")

                    # HTML生成（価格グラフはMarkdown内に埋め込まれている）
                    if self.html_builder:
                        html_filename = f"{area.ward}{area.choume}.html"
                        html_path = self.config.html_dir / html_filename
                        
                        # データを準備（HTMLテーブル用）
                        html_data = None
                        if data:
                            # データ年数を計算（land_price_historyから）
                            data_years = 26  # デフォルト
                            if 'land_price_history' in data and isinstance(data['land_price_history'], list):
                                data_years = len(data['land_price_history'])
                            
                            html_data = {
                                'latest_price': data.get('latest_price', 0),
                                'latest_price_min': data.get('latest_price_min', 0),
                                'latest_price_max': data.get('latest_price_max', 0),
                                'latest_point_count': data.get('latest_point_count', 1),
                                'price_change_26y': data.get('price_change_26y'),
                                'price_change_5y': data.get('price_change_5y'),
                                'data_years': data_years
                            }
                        
                        # chart_pathを渡す
                        self.html_builder.build(md_path, chart_path, html_path, data=html_data)
                        self.logger.info(f"Generated HTML: {html_path}")

                    # ArticleManagerに登録
                    if self.article_manager:
                        # タイトル抽出（最初のH1から）
                        title = markdown_content.split('\n')[0].replace('# ', '').strip()
                        if not title:
                            title = f"{area.ward}{area.choume}の資産価値分析"
                        
                        # データ年数を計算
                        data_years = 26  # デフォルト
                        if 'land_price_history' in data and isinstance(data['land_price_history'], list):
                            data_years = len(data['land_price_history'])
                        
                        # 相対パスを計算（project_dirからの相対パス）
                        project_dir = self.config.project_dir
                        markdown_rel = md_path.relative_to(project_dir) if project_dir in md_path.parents else md_path
                        html_rel = html_path.relative_to(project_dir) if project_dir in html_path.parents else html_path
                        
                        # chart_pathの相対パス計算を修正
                        if chart_path and chart_path.exists():
                            chart_rel = chart_path.relative_to(project_dir) if project_dir in chart_path.parents else chart_path
                            chart_path_str = str(chart_rel)
                        else:
                            chart_path_str = ''
                        
                        # パスをPOSIX形式（/）に正規化（Windowsのバックスラッシュを統一）
                        def normalize_path(path_str: str) -> str:
                            """パス区切り文字を / に統一"""
                            return path_str.replace('\\', '/')
                        
                        article_data = {
                            'ward': area.ward,
                            'choume': area.choume,
                            'markdown_path': normalize_path(str(markdown_rel)),
                            'html_path': normalize_path(str(html_rel)),
                            'chart_path': normalize_path(chart_path_str) if chart_path_str else '',
                            'title': title,
                            'word_count': len(markdown_content),
                            'data_years': data_years,
                            'latest_price': data.get('latest_price', 0),
                            'price_min': data.get('latest_price_min', data.get('latest_price', 0)),
                            'price_max': data.get('latest_price_max', data.get('latest_price', 0)),
                            'price_change': data.get('price_change_26y', data.get('price_change_5y', 0)),
                            'prompt_version': 'v2'
                        }
                        
                        article_id = self.article_manager.register_article(article_data)
                        self.logger.info(f"✅ Article registered: ID={article_id}")

            except Exception as e:
                self.logger.error(f"Error generating content for area {area.area_id}: {e}", exc_info=True)
