"""
WordPress投稿モジュール

ArticleManagerから記事を取得し、WordPress REST APIに投稿する。
"""
from .publisher import WordPressPublisher

__all__ = ['WordPressPublisher']




