import anthropic
from typing import Optional
from .base_client import BaseLLMClient
import logging

logger = logging.getLogger(__name__)

class AnthropicClient(BaseLLMClient):
    """Claude API クライアント"""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5"):
        if not api_key:
            raise ValueError("API key is required")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"Initialized AnthropicClient with model={model}")

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
        logger.info(f"Generating content with temperature={temperature}, max_tokens={max_tokens}")
        logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            logger.info(f"Generated {len(response_text)} characters")
            return response_text

        except Exception as e:
            logger.error(f"Error generating content: {e}", exc_info=True)
            raise
