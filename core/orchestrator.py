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

            except Exception as e:
                self.logger.error(f"Error processing area {area.area_id}: {e}", exc_info=True)
                self.data_manager.update_area_status(area.area_id, "error")

    def _run_content_generation(self, limit: int):
        """記事生成パイプライン"""
        self.logger.info("=== Content Generation Phase ===")

        # 完了した町丁目を取得
        areas = self.data_manager.get_pending_areas(limit)

        for area in areas:
            try:
                self.logger.info(f"Generating content for: {area.ward}{area.choume}")

                # スコアを取得
                score = self.data_manager.get_score(area.area_id)
                if not score:
                    self.logger.warning(f"No score found for area {area.area_id}, skipping")
                    continue

                # データを取得
                crime_data = self.data_manager.get_crime_data(area.area_id)
                data = crime_data if crime_data else {}

                # レーダーチャート生成
                chart_path = None
                if self.chart_generator:
                    chart_path = self.chart_generator.generate(area, score)
                    self.logger.info(f"Generated chart: {chart_path}")

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

                    # HTML生成
                    if self.html_builder and chart_path:
                        html_filename = f"{area.ward}{area.choume}.html"
                        html_path = self.config.html_dir / html_filename
                        self.html_builder.build(md_path, chart_path, html_path)
                        self.logger.info(f"Generated HTML: {html_path}")

            except Exception as e:
                self.logger.error(f"Error generating content for area {area.area_id}: {e}", exc_info=True)
