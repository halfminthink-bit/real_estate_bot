from abc import ABC, abstractmethod
from typing import Dict, Any
from core.models import Area

class BaseCollector(ABC):
    """データ収集の抽象基底クラス"""

    @abstractmethod
    def is_relevant(self, area: Area) -> bool:
        """このコレクターが対象エリアに適用可能か"""
        pass

    @abstractmethod
    def fetch(self, area: Area) -> Dict[str, Any]:
        """データを収集"""
        pass
