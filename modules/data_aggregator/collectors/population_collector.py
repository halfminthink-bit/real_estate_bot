from typing import Dict, Any
from core.models import Area
from .base_collector import BaseCollector
import logging

logger = logging.getLogger(__name__)

class PopulationCollector(BaseCollector):
    """e-Stat API - 人口データ収集（Phase 1はダミー）"""

    def is_relevant(self, area: Area) -> bool:
        return True

    def fetch(self, area: Area) -> Dict[str, Any]:
        """
        Phase 1ではダミーデータを返す
        Phase 2でe-Stat API実装
        """
        logger.info(f"Fetching population data for {area.ward}{area.choume} (dummy)")

        return {
            'population': 5000,  # ダミー
            'households': 2500,  # ダミー
            'population_source': 'dummy'
        }
