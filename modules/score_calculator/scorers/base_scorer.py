from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseScorer(ABC):
    """スコア計算の抽象基底クラス"""

    @abstractmethod
    def calculate(self, data: Dict[str, Any]) -> int:
        """
        データからスコアを計算

        Returns:
            0-100のスコア
        """
        pass
