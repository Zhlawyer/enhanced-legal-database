#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法条拆分模块 - 基于GitHub项目 sublatesublate-design/legal-database
智能识别和拆分法律条文，支持条款、项、目的层级结构
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """法条数据类"""
    law_title: str
    article_number: str
    content: str
    level: str  # article/paragraph/item/subitem
    parent_number: Optional[str] = None
    order: int = 0


class ArticleSplitter:
    """法条拆分器"""

    def __init__(self):
        # 法条层级模式
        self.patterns = {
            'article': r'^第[一二三四五六七八九十百千\d]+条\s*(.*)$',
            'paragraph': r'^第[一二三四五六七八九十百千\d]+款\s*(.*)$',
            'item': r'^\([一二三四五六七八九十\d]+\)\s*(.*)$',
            'subitem': r'^[一二三四五六七八九十\d]、\s*(.*)$',
            'point': r'^\([1-9]\d*\)\s*(.*)$'
        }

        # 法律名称提取模式
        self.law_title_patterns = [
            r'《([^》]+)》',
            r'“([^”]+)”',
            r'中华人民共和国[\u4e00-\u9fa5]+法'
        ]

    def extract_law_title(self, text: str) -> str:
        """从文本中提取法律名称"""
        for pattern in self.law_title_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return "未知法律"

    def split_article(self, text: str, law_title: str = None) -> List[Article]:
        """
        拆分法律文本为独立法条

        Args:
            text: 法律文本内容
            law_title: 法律名称（可选）

        Returns:
            法条列表
        """
        if not law_title:
            law_title = self.extract_law_title(text)

        articles = []
        lines = text.split('\n')
        current_article = None
        current_content = []
        order = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否是新的法条
            article_match = re.match(self.patterns['article'], line)
            if article_match:
                # 保存之前的法条
                if current_article:
                    articles.append(Article(
                        law_title=law_title,
                        article_number=current_article,
                        content='\n'.join(current_content).strip(),
                        level='article',
                        order=order
                    ))
                    order += 1

                # 开始新的法条
                current_article = article_match.group(1)
                current_content = [article_match.group(0)]
                continue

            # 如果是其他层级的内容
            if current_article:
                current_content.append(line)

        # 保存最后一个法条
        if current_article and current_content:
            articles.append(Article(
                law_title=law_title,
                article_number=current_article,
                content='\n'.join(current_content).strip(),
                level='article',
                order=order
            ))

        return articles

    def split_detailed(self, text: str, law_title: str = None) -> List[Article]:
        """
        详细拆分（包含条款、项、目）

        Args:
            text: 法律文本内容
            law_title: 法律名称

        Returns:
            详细法条列表
        """
        if not law_title:
            law_title = self.extract_law_title(text)

        articles = []
        lines = text.split('\n')

        current_level = {
            'article': None,  # 第XX条
            'paragraph': None,  # 第XX款
            'item': None,  # (X)
            'subitem': None  # X、
        }

        current_content = []
        order = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查层级
            level_detected = False

            # 检查是否是新法条
            article_match = re.match(self.patterns['article'], line)
            if article_match:
                # 保存之前的内容
                if current_level['article'] and current_content:
                    articles.append(Article(
                        law_title=law_title,
                        article_number=current_level['article'],
                        content='\n'.join(current_content).strip(),
                        level='article',
                        order=order
                    ))
                    order += 1

                current_level['article'] = article_match.group(1)
                current_level['paragraph'] = None
                current_level['item'] = None
                current_level['subitem'] = None
                current_content = [line]
                level_detected = True

            # 检查条款
            elif re.match(self.patterns['paragraph'], line):
                if current_level['article']:
                    current_level['paragraph'] = line
                    current_content.append(line)
                    level_detected = True

            # 检查项
            elif re.match(self.patterns['item'], line):
                if current_level['article']:
                    current_level['item'] = line
                    current_content.append(line)
                    level_detected = True

            # 检查目
            elif re.match(self.patterns['subitem'], line):
                if current_level['article']:
                    current_level['subitem'] = line
                    current_content.append(line)
                    level_detected = True

            # 如果没有检测到层级，作为内容添加
            if not level_detected and current_level['article']:
                current_content.append(line)

        # 保存最后一个法条
        if current_level['article'] and current_content:
            articles.append(Article(
                law_title=law_title,
                article_number=current_level['article'],
                content='\n'.join(current_content).strip(),
                level='article',
                order=order
            ))

        return articles

    def get_article_structure(self, articles: List[Article]) -> Dict[str, Any]:
        """获取法条结构信息"""
        structure = {
            'total_articles': len(articles),
            'article_numbers': [a.article_number for a in articles],
            'word_count': sum(len(a.content) for a in articles),
            'by_level': {}
        }

        # 按层级统计
        for article in articles:
            level = article.level
            if level not in structure['by_level']:
                structure['by_level'][level] = 0
            structure['by_level'][level] += 1

        return structure

    def validate_article_number(self, article_number: str) -> bool:
        """验证法条编号格式"""
        patterns = [
            r'^第[一二三四五六七八九十百千\d]+条$',
            r'^第[一二三四五六七八九十百千\d]+款$',
            r'^\([一二三四五六七八九十\d]+\)$',
            r'^[一二三四五六七八九十\d]、$'
        ]

        for pattern in patterns:
            if re.match(pattern, article_number):
                return True
        return False


class DatabaseArticleManager:
    """数据库法条管理器"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.splitter = ArticleSplitter()

    def init_article_tables(self):
        """初始化法条相关表结构"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 法条表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                law_id INTEGER NOT NULL,
                law_title TEXT NOT NULL,
                article_number TEXT NOT NULL,
                content TEXT NOT NULL,
                level TEXT NOT NULL,
                parent_number TEXT,
                order_num INTEGER,
                word_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (law_id) REFERENCES laws(id) ON DELETE CASCADE,
                UNIQUE(law_id, article_number)
            )
        ''')

        # 法条索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_law_id ON articles(law_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_number ON articles(article_number)')

        conn.commit()
        conn.close()

    def split_and_store(self, law_id: int, law_title: str, content: str) -> Dict[str, Any]:
        """
        拆分法律内容并存储到数据库

        Args:
            law_id: 法律ID
            law_title: 法律标题
            content: 法律内容

        Returns:
            拆分结果统计
        """
        import sqlite3

        try:
            # 拆分法条
            articles = self.splitter.split_detailed(content, law_title)

            if not articles:
                return {'success': False, 'error': '未识别到法条'}

            # 存储到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            stored_count = 0
            for article in articles:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO articles
                        (law_id, law_title, article_number, content, level, parent_number, order_num, word_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        law_id,
                        article.law_title,
                        article.article_number,
                        article.content,
                        article.level,
                        article.parent_number,
                        article.order,
                        len(article.content)
                    ))
                    stored_count += 1
                except sqlite3.Error as e:
                    logger.warning(f"存储法条失败 {article.article_number}: {e}")

            conn.commit()
            conn.close()

            # 获取结构信息
            structure = self.splitter.get_article_structure(articles)

            return {
                'success': True,
                'total_articles': len(articles),
                'stored_count': stored_count,
                'structure': structure,
                'message': f'成功拆分并存储 {stored_count} 个法条'
            }

        except Exception as e:
            logger.error(f"法条拆分失败: {e}")
            return {'success': False, 'error': str(e)}

    def get_law_articles(self, law_id: int) -> List[Dict[str, Any]]:
        """获取法律的所有法条"""
        import sqlite3

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT article_number, content, level, order_num, word_count
                FROM articles
                WHERE law_id = ?
                ORDER BY order_num
            ''', (law_id,))

            articles = []
            for row in cursor.fetchall():
                articles.append({
                    'article_number': row[0],
                    'content': row[1],
                    'level': row[2],
                    'order': row[3],
                    'word_count': row[4]
                })

            conn.close()
            return articles

        except Exception as e:
            logger.error(f"获取法条失败: {e}")
            return []

    def search_articles(self, query: str, law_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """搜索法条内容"""
        import sqlite3

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if law_id:
                cursor.execute('''
                    SELECT law_title, article_number, content, level, word_count
                    FROM articles
                    WHERE law_id = ? AND content LIKE ?
                    ORDER BY order_num
                    LIMIT 50
                ''', (law_id, f'%{query}%'))
            else:
                cursor.execute('''
                    SELECT law_title, article_number, content, level, word_count
                    FROM articles
                    WHERE content LIKE ?
                    ORDER BY law_title, order_num
                    LIMIT 50
                ''', (f'%{query}%',))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'law_title': row[0],
                    'article_number': row[1],
                    'content': row[2][:200] + '...' if len(row[2]) > 200 else row[2],
                    'level': row[3],
                    'word_count': row[4]
                })

            conn.close()
            return results

        except Exception as e:
            logger.error(f"搜索法条失败: {e}")
            return []


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    # 测试法条拆分
    splitter = ArticleSplitter()

    sample_text = """
《中华人民共和国民法典》

第一条
为了保护民事主体的合法权益，调整民事关系，维护社会和经济秩序，适应中国特色社会主义发展要求，弘扬社会主义核心价值观，根据宪法，制定本法。

第二条
民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。

第三条
民事主体的人身权利、财产权利以及其他合法权益受法律保护，任何组织或者个人不得侵犯。
"""

    print("=== 法条拆分测试 ===")
    articles = splitter.split_detailed(sample_text)
    print(f"拆分结果: {len(articles)} 个法条")

    for article in articles:
        print(f"\n【{article.article_number}】")
        print(f"内容: {article.content[:100]}...")

    # 测试数据库管理
    print("\n=== 数据库管理测试 ===")
    db_manager = DatabaseArticleManager('./download_data/enhanced_legal_database.db')
    db_manager.init_article_tables()
    print("✅ 法条表结构初始化完成")