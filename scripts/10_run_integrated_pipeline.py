#!/usr/bin/env python3
"""
完全統合パイプライン実行スクリプト

PostgreSQL → modules/ → LLM → 記事生成
"""
import argparse
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import ProjectConfig
from core.orchestrator import Orchestrator
from modules.data_aggregator.aggregator import DataAggregator
from modules.data_aggregator.collectors.crime_collector import CrimeCollector
from modules.data_aggregator.collectors.land_price_collector import LandPriceCollector
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
            logging.FileHandler(log_dir / 'integrated_pipeline.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description='RealEstateBot Integrated Pipeline - PostgreSQL + LLM Article Generation'
    )
    parser.add_argument(
        '--project',
        default='projects/setagaya_real_estate/config.yml',
        help='プロジェクト設定ファイルパス'
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
        default=5,
        help='処理する町丁目の最大数（デフォルト: 5）'
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
    logger.info("RealEstateBot Integrated Pipeline")
    logger.info("PostgreSQL + LLM Article Generation")
    logger.info("=" * 60)
    logger.info(f"Project: {args.project}")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Limit: {args.limit}")
    logger.info("=" * 60)

    try:
        # 設定読み込み
        logger.info("Loading project configuration...")
        config = ProjectConfig(args.project)
        logger.info(f"Project name: {config.project_name}")

        # 各モジュールを初期化
        logger.info("Initializing modules...")

        # データ収集モジュール
        collectors = []
        
        # 犯罪データCollector
        crime_data_path = config.data_dir / 'crime_data.csv'
        if crime_data_path.exists():
            crime_collector = CrimeCollector(crime_data_path)
            collectors.append(crime_collector)
            logger.info("Added CrimeCollector")
        else:
            logger.warning(f"Crime data file not found: {crime_data_path}")

        # 地価データCollector（PostgreSQL）
        land_price_collector = LandPriceCollector()
        collectors.append(land_price_collector)
        logger.info("Added LandPriceCollector")

        data_aggregator = DataAggregator(collectors)
        logger.info(f"Initialized DataAggregator with {len(collectors)} collectors")

        # スコア計算モジュール
        score_calculator = ScoreCalculator(config.get_scoring_rules_path())
        logger.info("Initialized ScoreCalculator")

        # レーダーチャート生成モジュール
        chart_generator = ChartGenerator(config.charts_dir)
        logger.info("Initialized ChartGenerator")

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
            logger.info("Initialized ContentGenerator")
        else:
            logger.warning("ANTHROPIC_API_KEY not set, content generation will be skipped")

        # HTML生成モジュール
        html_builder = HTMLBuilder(config)
        logger.info("Initialized HTMLBuilder")

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

