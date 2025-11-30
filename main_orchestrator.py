#!/usr/bin/env python3
"""
RealEstateBot Phase 1 MVP - Main Orchestrator

世田谷区5町丁目の住みやすさ記事を生成します
"""

import argparse
import logging
from pathlib import Path
import sys

from core.config import ProjectConfig
from core.orchestrator import Orchestrator
from modules.data_aggregator.aggregator import DataAggregator
from modules.data_aggregator.collectors.crime_collector import CrimeCollector
from modules.data_aggregator.collectors.population_collector import PopulationCollector
from modules.data_aggregator.collectors.resas_collector import RESASCollector
from modules.score_calculator.calculator import ScoreCalculator
from modules.chart_generator.generator import ChartGenerator
from modules.content_generator.generator import ContentGenerator
from modules.content_generator.llm.anthropic_client import AnthropicClient
from modules.html_builder.builder import HTMLBuilder


def setup_logging(log_level=logging.INFO):
    """ログ設定"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'real_estate_bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description='RealEstateBot Phase 1 MVP - Real estate article generator'
    )
    parser.add_argument(
        '--project',
        required=True,
        help='プロジェクト設定ファイルパス (例: projects/setagaya_real_estate/config.yml)'
    )
    parser.add_argument(
        '--mode',
        default='full',
        choices=['full', 'data_only', 'generate_only'],
        help='実行モード: full=全実行, data_only=データ収集のみ, generate_only=記事生成のみ'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='処理する町丁目の最大数（デフォルト: 10）'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='デバッグモードで実行'
    )
    args = parser.parse_args()

    # ログ設定
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("RealEstateBot Phase 1 MVP")
    logger.info("=" * 60)
    logger.info(f"Project: {args.project}")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Limit: {args.limit}")
    logger.info(f"Debug: {args.debug}")
    logger.info("=" * 60)

    try:
        # 設定読み込み
        logger.info("Loading project configuration...")
        config = ProjectConfig(args.project)
        logger.info(f"Project name: {config.project_name}")

        # 各モジュールを初期化
        logger.info("Initializing modules...")

        # データ収集モジュール
        crime_collector = CrimeCollector(config.data_dir / 'crime_data.csv')
        population_collector = PopulationCollector()
        resas_collector = RESASCollector()
        data_aggregator = DataAggregator([crime_collector, population_collector, resas_collector])

        # スコア計算モジュール
        score_calculator = ScoreCalculator(config.get_scoring_rules_path())

        # レーダーチャート生成モジュール
        chart_generator = ChartGenerator(config.charts_dir)

        # AI記事生成モジュール
        llm_config = config.get_llm_config()
        api_key = config.get_api_key('anthropic')

        if not api_key and args.mode in ['full', 'generate_only']:
            logger.error("ANTHROPIC_API_KEY is not set. Please set it in .env file.")
            logger.error("Copy .env.example to .env and add your API key.")
            sys.exit(1)

        content_generator = None
        if api_key:
            llm_client = AnthropicClient(
                api_key=api_key,
                model=llm_config.get('model', 'claude-sonnet-4-5-20250929')
            )
            content_generator = ContentGenerator(config, llm_client)

        # HTML生成モジュール
        html_builder = HTMLBuilder(config)

        # Orchestratorにモジュールを設定
        logger.info("Setting up orchestrator...")
        orchestrator = Orchestrator(config)
        orchestrator.set_modules(
            data_aggregator=data_aggregator,
            score_calculator=score_calculator,
            chart_generator=chart_generator,
            content_generator=content_generator,
            html_builder=html_builder
        )

        # パイプライン実行
        logger.info("Starting pipeline execution...")
        orchestrator.run(mode=args.mode, limit=args.limit)

        logger.info("=" * 60)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 60)
        logger.info(f"Output directory: {config.output_dir}")
        logger.info(f"Charts directory: {config.charts_dir}")
        logger.info(f"HTML directory: {config.html_dir}")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        logger.error("Please make sure all required files exist.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
