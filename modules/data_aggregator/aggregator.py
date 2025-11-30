from typing import Dict, Any, List
from core.models import Area
import logging

logger = logging.getLogger(__name__)

class DataAggregator:
    """データ収集のコーディネーター"""

    def __init__(self, collectors: List):
        self.collectors = collectors
        logger.info(f"Initialized DataAggregator with {len(collectors)} collectors")

    def collect(self, area: Area) -> Dict[str, Any]:
        """全てのコレクターからデータ収集"""
        result = {}

        for collector in self.collectors:
            try:
                if collector.is_relevant(area):
                    data = collector.fetch(area)
                    result.update(data)
                    logger.debug(f"Collected data from {collector.__class__.__name__}: {data}")
            except Exception as e:
                logger.error(f"Error in {collector.__class__.__name__}: {e}", exc_info=True)

        return result
