#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
町丁目リストローダー

PostgreSQLから町丁目リストを動的に取得
"""
import psycopg2
import yaml
from pathlib import Path
from typing import List, Tuple, Optional
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class AreaLoader:
    """PostgreSQLから町丁目リストを取得"""
    
    def __init__(self, db_config_path: Optional[Path] = None):
        """
        Args:
            db_config_path: データベース設定ファイルのパス
        """
        if db_config_path is None:
            db_config_path = Path(__file__).parent.parent / 'config' / 'database.yml'
        
        self.db_config = self._load_db_config(db_config_path)
        logger.info("Initialized AreaLoader")
    
    def _load_db_config(self, config_path: Path) -> dict:
        """データベース設定を読み込み"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        password = os.getenv('DB_PASSWORD', config['postgresql'].get('password', 'postgres'))
        
        return {
            'host': os.getenv('DB_HOST', config['postgresql'].get('host', 'localhost')),
            'port': int(os.getenv('DB_PORT', config['postgresql'].get('port', 5432))),
            'database': os.getenv('DB_NAME', config['postgresql'].get('database', 'real_estate_dev')),
            'user': os.getenv('DB_USER', config['postgresql'].get('user', 'postgres')),
            'password': password
        }
    
    def get_choume_list(
        self, 
        city_name: str = '世田谷区', 
        survey_year: int = 2025
    ) -> List[Tuple[str, str]]:
        """
        PostgreSQLから町丁目リストを取得
        
        Args:
            city_name: 市区町村名（例: 世田谷区）
            survey_year: 対象年度（デフォルト: 2025）
        
        Returns:
            List[Tuple[str, str]]: [(ward, choume), ...]
            例: [('世田谷区', '上用賀1丁目'), ('世田谷区', '上用賀6丁目'), ...]
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 市区町村名から検索パターン作成
            # 「世田谷区」→「世田谷」で検索
            search_pattern = city_name.replace('区', '').replace('市', '')
            
            logger.info(f"Fetching choume list for {city_name} (year={survey_year})")
            
            # 最新年度から町丁目一覧を取得
            # original_addressから「XX丁目」までを抽出
            cursor.execute('''
                SELECT DISTINCT 
                    %s as ward,
                    SUBSTRING(
                        original_address 
                        FROM 1 
                        FOR POSITION('丁目' IN original_address) + 2
                    ) as choume
                FROM land_prices_kokudo
                WHERE original_address LIKE %s
                  AND survey_year = %s
                  AND POSITION('丁目' IN original_address) > 0
                ORDER BY choume
            ''', (city_name, f'%{search_pattern}%', survey_year))
            
            areas = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            logger.info(f"Found {len(areas)} choume in {city_name}")
            
            return areas
        
        except Exception as e:
            logger.error(f"Error fetching choume list: {e}", exc_info=True)
            return []
    
    def get_available_years(self) -> List[int]:
        """
        PostgreSQLから利用可能な年度一覧を取得
        
        Returns:
            List[int]: [2000, 2001, ..., 2025]
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT survey_year
                FROM land_prices_kokudo
                ORDER BY survey_year DESC
            ''')
            
            years = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return years
        
        except Exception as e:
            logger.error(f"Error fetching available years: {e}", exc_info=True)
            return []




