from pathlib import Path
import logging
from typing import Optional
from datetime import datetime

from core.config import ProjectConfig
from core.data_manager import CSVDataManager
from core.models import Area, ScoreResult

logger = logging.getLogger(__name__)

class Orchestrator:
    """パイプライン全体の制御"""

    def __init__(self, config: ProjectConfig):
        self.config = config
        self.data_manager = CSVDataManager(config.data_dir)
        self.logger = logging.getLogger(__name__)

        # 処理したarea_idを保持
        self.processed_area_ids = []

        # 各モジュールは後で初期化
        self.data_aggregator = None
        self.score_calculator = None
        self.chart_generator = None
        self.content_generator = None
        self.html_builder = None

    def set_modules(self, data_aggregator=None, score_calculator=None,
                   chart_generator=None, content_generator=None, html_builder=None):
        """各モジュールを設定"""
        self.data_aggregator = data_aggregator
        self.score_calculator = score_calculator
        self.chart_generator = chart_generator
        self.content_generator = content_generator
        self.html_builder = html_builder

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

        # 未処理の町丁目を取得
        areas = self.data_manager.get_pending_areas(limit)
        self.logger.info(f"Found {len(areas)} pending areas")

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
            # generate_onlyモードの場合、スコアが存在するareaを取得
            self.logger.info("No areas processed in data collection phase, looking for areas with scores")
            areas = self.data_manager.get_pending_areas(limit)
        else:
            # 処理したarea_idからareaを取得
            areas = []
            for area_id in self.processed_area_ids:
                area = self.data_manager.get_area_by_id(area_id)
                if area:
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
                if self.content_generator:
                    markdown_content = self.content_generator.generate(area, score, data)

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
                        # chart_pathは不要（Markdown内に画像が埋め込まれている）
                        self.html_builder.build(md_path, None, html_path)
                        self.logger.info(f"Generated HTML: {html_path}")

            except Exception as e:
                self.logger.error(f"Error generating content for area {area.area_id}: {e}", exc_info=True)
