import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ArticleManager:
    """
    記事管理システム
    
    機能:
    - 記事情報の登録・更新
    - WordPress投稿状況の管理
    - 履歴の記録
    - 統計情報の取得
    """
    
    def __init__(self, db_path: Path):
        """
        初期化
        
        Args:
            db_path: SQLiteデータベースのパス（例: articles.db）
        """
        self.db_path = Path(db_path)
        logger.info(f"Initializing ArticleManager: {self.db_path}")
        self._init_db()
    
    def _init_db(self):
        """データベース初期化（テーブル作成）"""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # articlesテーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ward TEXT NOT NULL,
                    choume TEXT NOT NULL,
                    markdown_path TEXT NOT NULL,
                    html_path TEXT NOT NULL,
                    chart_path TEXT NOT NULL,
                    title TEXT NOT NULL,
                    word_count INTEGER,
                    data_years INTEGER,
                    latest_price INTEGER,
                    price_min INTEGER,
                    price_max INTEGER,
                    price_change REAL,
                    asset_value_score INTEGER,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    prompt_version TEXT,
                    wp_post_id INTEGER,
                    wp_url TEXT,
                    wp_posted_at TIMESTAMP,
                    wp_status TEXT,
                    UNIQUE(ward, choume)
                )
            """)
            
            # post_historyテーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS post_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles(id)
                )
            """)
            
            conn.commit()
            logger.info("Database initialized")
    
    def register_article(self, article_data: Dict) -> int:
        """
        記事を登録（既存の場合は更新）
        
        Args:
            article_data: 記事情報
                {
                    'ward': str,              # 区
                    'choume': str,            # 町丁目
                    'markdown_path': str,     # Markdownパス
                    'html_path': str,         # HTMLパス
                    'chart_path': str,        # グラフパス
                    'title': str,             # タイトル
                    'word_count': int,        # 文字数
                    'data_years': int,        # データ年数
                    'latest_price': int,      # 平均地価
                    'price_min': int,         # 最低地価
                    'price_max': int,         # 最高地価
                    'price_change': float,    # 変動率
                    'asset_value_score': int, # スコア（オプショナル、デフォルト: 0）
                    'prompt_version': str     # プロンプトバージョン
                }
        
        Returns:
            int: 記事ID
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # 既存チェック
            cursor = conn.execute(
                "SELECT id FROM articles WHERE ward = ? AND choume = ?",
                (article_data['ward'], article_data['choume'])
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                article_id = existing[0]
                conn.execute("""
                    UPDATE articles SET
                        markdown_path = ?,
                        html_path = ?,
                        chart_path = ?,
                        title = ?,
                        word_count = ?,
                        data_years = ?,
                        latest_price = ?,
                        price_min = ?,
                        price_max = ?,
                        price_change = ?,
                        asset_value_score = ?,
                        generated_at = ?,
                        prompt_version = ?
                    WHERE id = ?
                """, (
                    article_data['markdown_path'],
                    article_data['html_path'],
                    article_data['chart_path'],
                    article_data['title'],
                    article_data['word_count'],
                    article_data['data_years'],
                    article_data['latest_price'],
                    article_data['price_min'],
                    article_data['price_max'],
                    article_data['price_change'],
                    article_data.get('asset_value_score', 0),  # オプショナル（デフォルト: 0）
                    datetime.now(),
                    article_data.get('prompt_version', 'v2'),
                    article_id
                ))
                action = 'updated'
            else:
                # 新規登録
                cursor = conn.execute("""
                    INSERT INTO articles 
                    (ward, choume, markdown_path, html_path, chart_path, 
                     title, word_count, data_years, latest_price, price_min, price_max,
                     price_change, asset_value_score, generated_at, prompt_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_data['ward'],
                    article_data['choume'],
                    article_data['markdown_path'],
                    article_data['html_path'],
                    article_data['chart_path'],
                    article_data['title'],
                    article_data['word_count'],
                    article_data['data_years'],
                    article_data['latest_price'],
                    article_data['price_min'],
                    article_data['price_max'],
                    article_data['price_change'],
                    article_data.get('asset_value_score', 0),  # オプショナル（デフォルト: 0）
                    datetime.now(),
                    article_data.get('prompt_version', 'v2')
                ))
                article_id = cursor.lastrowid
                action = 'generated'
            
            # 履歴追加（同じトランザクション内）
            conn.execute("""
                INSERT INTO post_history (article_id, action, status, message)
                VALUES (?, ?, ?, ?)
            """, (article_id, action, 'success', '記事生成完了'))
            
            # 1回のCOMMITで両方の操作を確定
            conn.commit()
            
            logger.info(f"Article registered: {article_data['choume']} (ID: {article_id})")
            return article_id
    
    def update_wp_post(
        self, 
        ward: str, 
        choume: str, 
        wp_post_id: int, 
        wp_url: str,
        status: str
    ):
        """
        WordPress投稿情報を更新
        
        Args:
            ward: 区
            choume: 町丁目
            wp_post_id: WordPress記事ID
            wp_url: WordPress記事URL
            status: 投稿ステータス（'draft', 'published', 'future'）
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # 記事を更新
            conn.execute("""
                UPDATE articles 
                SET wp_post_id = ?, wp_url = ?, wp_posted_at = ?, wp_status = ?
                WHERE ward = ? AND choume = ?
            """, (wp_post_id, wp_url, datetime.now(), status, ward, choume))
            
            # 記事IDを取得
            cursor = conn.execute(
                "SELECT id FROM articles WHERE ward = ? AND choume = ?",
                (ward, choume)
            )
            result = cursor.fetchone()
            
            if result:
                article_id = result[0]
                
                # 履歴を追加（同じトランザクション内）
                conn.execute("""
                    INSERT INTO post_history (article_id, action, status, message)
                    VALUES (?, ?, ?, ?)
                """, (
                    article_id, 
                    'posted', 
                    'success', 
                    f'WordPress投稿: ID={wp_post_id}, Status={status}'
                ))
            
            # 1回のCOMMITで両方の操作を確定
            conn.commit()
            logger.info(f"WordPress post updated: {choume} (WP ID: {wp_post_id})")
    
    def add_history(self, article_id: int, action: str, status: str, message: str):
        """
        履歴を追加
        
        Args:
            article_id: 記事ID
            action: アクション（'generated', 'posted', 'updated', 'failed'）
            status: ステータス（'success', 'failed'）
            message: メッセージ
        
        Note:
            update_wp_post()とregister_article()では直接SQL実行するため、
            このメソッドは外部から単独で呼ばれる場合のみ使用
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute("""
                INSERT INTO post_history (article_id, action, status, message)
                VALUES (?, ?, ?, ?)
            """, (article_id, action, status, message))
            conn.commit()
    
    def get_article(self, ward: str, choume: str) -> Optional[Dict]:
        """
        記事情報を取得
        
        Args:
            ward: 区
            choume: 町丁目
        
        Returns:
            Dict: 記事情報（存在しない場合はNone）
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM articles WHERE ward = ? AND choume = ?",
                (ward, choume)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def exists(self, ward: str, choume: str) -> bool:
        """
        記事が存在するかチェック
        
        Args:
            ward: 区
            choume: 町丁目
        
        Returns:
            bool: 記事が存在する場合True
        """
        article = self.get_article(ward, choume)
        return article is not None
    
    def get_all_articles(self) -> List[Dict]:
        """
        全記事を取得
        
        Returns:
            List[Dict]: 記事情報のリスト（生成日時降順）
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM articles ORDER BY generated_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_unpublished(self) -> List[Dict]:
        """
        未投稿記事を取得
        
        Returns:
            List[Dict]: 未投稿記事のリスト
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM articles WHERE wp_post_id IS NULL ORDER BY generated_at"
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_by_status(self, status: str) -> List[Dict]:
        """
        ステータスで記事を取得
        
        Args:
            status: WordPress投稿ステータス（'draft', 'published', 'future'）
        
        Returns:
            List[Dict]: 記事リスト
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM articles WHERE wp_status = ? ORDER BY wp_posted_at DESC",
                (status,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """
        統計情報を取得
        
        Returns:
            Dict: 統計情報
                {
                    'total': int,          # 総記事数
                    'published': int,      # 公開済み
                    'draft': int,          # 下書き
                    'unpublished': int     # 未投稿
                }
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            published = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE wp_status = 'published'"
            ).fetchone()[0]
            draft = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE wp_status = 'draft'"
            ).fetchone()[0]
            unpublished = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE wp_post_id IS NULL"
            ).fetchone()[0]
            
            return {
                'total': total,
                'published': published,
                'draft': draft,
                'unpublished': unpublished
            }
    
    def get_history(self, article_id: int) -> List[Dict]:
        """
        記事の履歴を取得
        
        Args:
            article_id: 記事ID
        
        Returns:
            List[Dict]: 履歴のリスト
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM post_history WHERE article_id = ? ORDER BY created_at DESC",
                (article_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def reset_wp_post(self, ward: str, choume: str) -> bool:
        """
        WordPress投稿情報をリセット（再投稿用）
        
        Args:
            ward: 区
            choume: 町丁目
        
        Returns:
            bool: リセット成功したかどうか
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # 記事を取得
            cursor = conn.execute(
                "SELECT id FROM articles WHERE ward = ? AND choume = ?",
                (ward, choume)
            )
            result = cursor.fetchone()
            
            if not result:
                logger.warning(f"Article not found: {ward} {choume}")
                return False
            
            article_id = result[0]
            
            # WordPress情報をリセット
            conn.execute("""
                UPDATE articles 
                SET wp_post_id = NULL, wp_url = NULL, wp_posted_at = NULL, wp_status = NULL
                WHERE ward = ? AND choume = ?
            """, (ward, choume))
            
            # 履歴を追加
            conn.execute("""
                INSERT INTO post_history (article_id, action, status, message)
                VALUES (?, ?, ?, ?)
            """, (article_id, 'reset', 'success', 'WordPress投稿情報をリセット（再投稿準備）'))
            
            conn.commit()
            logger.info(f"WordPress post reset: {choume}")
            return True
    
    def reset_all_wp_posts(self) -> int:
        """
        全記事のWordPress投稿情報をリセット（再投稿用）
        
        Returns:
            int: リセットした記事数
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # リセット対象の記事IDを取得
            cursor = conn.execute(
                "SELECT id, ward, choume FROM articles WHERE wp_post_id IS NOT NULL"
            )
            articles = cursor.fetchall()
            
            if not articles:
                logger.info("No articles to reset")
                return 0
            
            # 各記事をリセット
            reset_count = 0
            for article_id, ward, choume in articles:
                conn.execute("""
                    UPDATE articles 
                    SET wp_post_id = NULL, wp_url = NULL, wp_posted_at = NULL, wp_status = NULL
                    WHERE id = ?
                """, (article_id,))
                
                # 履歴を追加
                conn.execute("""
                    INSERT INTO post_history (article_id, action, status, message)
                    VALUES (?, ?, ?, ?)
                """, (article_id, 'reset', 'success', 'WordPress投稿情報をリセット（再投稿準備）'))
                
                reset_count += 1
            
            conn.commit()
            logger.info(f"Reset {reset_count} articles for republishing")
            return reset_count
    
    def get_all_for_republish(self) -> List[Dict]:
        """
        再投稿用に全記事を取得（投稿済みも含む）
        
        Returns:
            List[Dict]: 全記事のリスト（生成日時順）
        """
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM articles ORDER BY generated_at"
            )
            return [dict(row) for row in cursor.fetchall()]

