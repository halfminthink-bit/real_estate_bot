from pathlib import Path
import yaml
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os

class ProjectConfig:
    """プロジェクト設定管理"""

    def __init__(self, config_path: str):
        load_dotenv()
        self.config_path = Path(config_path)
        self.project_dir = self.config_path.parent
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """YAML設定ファイルを読み込み"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @property
    def project_name(self) -> str:
        return self._config['project']['name']

    @property
    def data_dir(self) -> Path:
        return self.project_dir / 'data'

    @property
    def prompts_dir(self) -> Path:
        return self.project_dir / 'prompts'

    @property
    def output_dir(self) -> Path:
        path = self.project_dir / 'output'
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def charts_dir(self) -> Path:
        path = self.project_dir / 'charts'
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def html_dir(self) -> Path:
        path = self.project_dir / 'html'
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def templates_dir(self) -> Path:
        return self.project_dir / 'templates'

    def get_api_key(self, service: str) -> Optional[str]:
        """環境変数からAPIキーを取得"""
        key_map = {
            'anthropic': 'ANTHROPIC_API_KEY',
            'estat': 'ESTAT_API_KEY'
        }
        env_key = key_map.get(service)
        if not env_key:
            raise ValueError(f"Unknown service: {service}")

        key = os.getenv(env_key)
        return key

    def get_llm_config(self) -> Dict[str, Any]:
        """LLM設定を取得"""
        return self._config.get('llm', {})

    def get_scoring_rules_path(self) -> Path:
        """スコアリングルールファイルのパスを取得"""
        rules_file = self._config.get('scoring', {}).get('rules_file')
        if rules_file:
            return Path(rules_file)
        return self.project_dir / 'scoring_rules.yml'

    def get_affiliate_config_path(self) -> Path:
        """アフィリエイト設定ファイルのパスを取得"""
        affiliate_file = self._config.get('html', {}).get('affiliate_config')
        if affiliate_file:
            return Path(affiliate_file)
        return self.project_dir / 'affiliate_config.yml'
