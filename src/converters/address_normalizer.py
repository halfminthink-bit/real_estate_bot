"""
住所正規化モジュール

住所文字列から町丁目コードを抽出します。

Phase 1: 簡易実装（世田谷区のみ、マッピングテーブル使用）
Phase 2: jageocoder等のライブラリ使用
"""

import re
import logging
from typing import Optional, Dict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


# 世田谷区の町丁目コードマッピング（Phase 1用サンプル）
SETAGAYA_CHOUME_MAP = {
    "二子玉川1丁目": "13112001001",
    "二子玉川2丁目": "13112001002",
    "二子玉川3丁目": "13112001003",
    "二子玉川4丁目": "13112001004",
    "三軒茶屋1丁目": "13112002001",
    "三軒茶屋2丁目": "13112002002",
    "下北沢1丁目": "13112003001",
    "下北沢2丁目": "13112003002",
    "下北沢3丁目": "13112003003",
    "下北沢4丁目": "13112003004",
    "下北沢5丁目": "13112003005",
    # 他の町丁目も追加可能
}


class AddressNormalizer:
    """住所正規化クラス"""

    def __init__(self, mapping_file: Optional[Path] = None):
        """
        Args:
            mapping_file: 町丁目コードマッピングファイル（JSON形式）
        """
        self.choume_map = SETAGAYA_CHOUME_MAP.copy()

        # 外部マッピングファイルがあれば読み込み
        if mapping_file and mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                external_map = json.load(f)
                self.choume_map.update(external_map)
            logger.info(f"Loaded {len(external_map)} mappings from {mapping_file}")

    def normalize(self, address: str) -> str:
        """
        住所から町丁目コードを抽出

        Args:
            address: 住所文字列（例: "東京都世田谷区二子玉川1丁目"）

        Returns:
            町丁目コード（例: "13112001001"）
        """
        if not address:
            logger.warning("Empty address provided")
            return "UNKNOWN"

        # 町丁目名を抽出
        choume_name = self._extract_choume_name(address)

        if choume_name is None:
            logger.warning(f"Could not extract choume name from: {address}")
            return "UNKNOWN"

        # マッピングテーブルから検索
        code = self.choume_map.get(choume_name)

        if code:
            logger.debug(f"Matched: {address} -> {choume_name} -> {code}")
            return code
        else:
            logger.warning(f"No mapping found for: {choume_name} (from: {address})")
            return "UNKNOWN"

    def _extract_choume_name(self, address: str) -> Optional[str]:
        """
        住所から町丁目名を抽出

        Args:
            address: 住所文字列

        Returns:
            町丁目名（例: "二子玉川1丁目"）
        """
        # パターン1: 「○○区△△1丁目」形式
        match = re.search(r'([^区]+区)?(.+?)(\d+丁目)', address)

        if match:
            # 町丁目名 + 丁目番号
            choume_name = match.group(2) + match.group(3)
            return choume_name

        # パターン2: 「△△1-2-3」形式（番地がある場合）
        match = re.search(r'([^区]+区)?(.+?)(\d+-\d+)', address)

        if match:
            # 町丁目名のみ（丁目が明示されていない場合）
            base_name = match.group(2).strip()
            # 「1丁目」を補完（仮）
            return base_name + "1丁目"

        return None

    def get_all_mappings(self) -> Dict[str, str]:
        """全マッピングを取得"""
        return self.choume_map.copy()

    def add_mapping(self, choume_name: str, choume_code: str):
        """
        新しいマッピングを追加

        Args:
            choume_name: 町丁目名
            choume_code: 町丁目コード
        """
        self.choume_map[choume_name] = choume_code
        logger.info(f"Added mapping: {choume_name} -> {choume_code}")

    def save_mappings(self, output_path: Path):
        """
        現在のマッピングをファイルに保存

        Args:
            output_path: 出力先JSONファイル
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.choume_map, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(self.choume_map)} mappings to {output_path}")


# 簡易関数（モジュールレベル）
def normalize_address(address: str) -> str:
    """
    住所を正規化（簡易版）

    Args:
        address: 住所文字列

    Returns:
        町丁目コード
    """
    normalizer = AddressNormalizer()
    return normalizer.normalize(address)
