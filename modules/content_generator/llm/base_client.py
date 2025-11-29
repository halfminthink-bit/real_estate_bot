from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    """LLMクライアントの抽象基底クラス"""

    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 8000) -> str:
        """
        プロンプトからコンテンツ生成

        Args:
            prompt: 生成用プロンプト
            temperature: ランダム性（0.0-1.0）
            max_tokens: 最大トークン数

        Returns:
            生成されたテキスト
        """
        pass
