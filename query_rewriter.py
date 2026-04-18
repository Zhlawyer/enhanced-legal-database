#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询扩展和重写模块 - 基于GitHub项目 sublatesublate-design/legal-database
提供智能查询扩展、别名解析、同义词扩展等功能
"""

import sqlite3
import re
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


class QueryRewriter:
    """查询重写和扩展类"""

    def __init__(self, db_path="./download_data/legal_database.db"):
        self.db_path = Path(db_path)

    @lru_cache(maxsize=1024)
    def expand_query(self, query: str) -> str:
        """扩展查询词，包含别名和同义词"""
        if not query.strip():
            return query

        expanded_terms = {query}

        # 1. 别名扩展
        aliases = self._get_aliases(query)
        expanded_terms.update(aliases)

        # 2. 同义词扩展
        synonyms = self._get_synonyms(query)
        expanded_terms.update(synonyms)

        # 3. 构建OR查询
        if len(expanded_terms) > 1:
            safe_terms = [f'"{term}"' for term in expanded_terms]
            expanded_query = " OR ".join(safe_terms)
            logger.info(f"查询扩展: '{query}' → '{expanded_query}'")
            return expanded_query

        return query

    def _get_aliases(self, query: str) -> set:
        """获取查询词的别名"""
        aliases = set()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 查找该查询词作为别名的所有法律
                cursor.execute('''
                    SELECT l.title
                    FROM law_aliases la
                    JOIN laws l ON la.law_id = l.id
                    WHERE la.alias = ? AND l.status = '有效'
                ''', (query,))

                for row in cursor.fetchall():
                    aliases.add(row[0])

                # 反向查找：如果查询是完整标题，查找其别名
                cursor.execute('''
                    SELECT alias
                    FROM law_aliases la
                    JOIN laws l ON la.law_id = l.id
                    WHERE l.title = ? AND l.status = '有效'
                ''', (query,))

                for row in cursor.fetchall():
                    aliases.add(row[0])

        except sqlite3.Error as e:
            logger.warning(f"别名查询失败: {e}")

        return aliases

    def _get_synonyms(self, query: str) -> set:
        """获取查询词的同义词"""
        synonyms = set()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 查找同义词（query作为标准词）
                cursor.execute('''
                    SELECT term FROM concept_synonyms
                    WHERE canonical_term = ?
                ''', (query,))

                for row in cursor.fetchall():
                    synonyms.add(row[0])

                # 查找标准词（query作为同义词）
                cursor.execute('''
                    SELECT canonical_term FROM concept_synonyms
                    WHERE term = ?
                ''', (query,))

                for row in cursor.fetchall():
                    synonyms.add(row[0])

        except sqlite3.Error as e:
            logger.warning(f"同义词查询失败: {e}")

        return synonyms

    def resolve_law_alias(self, query: str) -> str:
        """解析法律别名，返回标准标题"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 查找别名匹配
                cursor.execute('''
                    SELECT l.title, la.confidence
                    FROM law_aliases la
                    JOIN laws l ON la.law_id = l.id
                    WHERE la.alias = ? AND l.status = '有效'
                    ORDER BY la.confidence DESC
                    LIMIT 1
                ''', (query,))

                result = cursor.fetchone()
                if result:
                    logger.info(f"别名解析: '{query}' → '{result[0]}' (置信度: {result[1]})")
                    return result[0]

        except sqlite3.Error as e:
            logger.warning(f"别名解析失败: {e}")

        return query

    def build_search_query(self, base_query: str, filters: dict = None) -> tuple:
        """构建完整的搜索查询语句"""
        # 扩展查询
        expanded_query = self.expand_query(base_query)

        # 构建SQL
        sql = '''
            SELECT title, category, publish_date, status, department, source_url,
                   is_amendment, base_law_title,
                   highlight(laws_fts, 1, '<mark>', '</mark>') as highlighted_title,
                   highlight(laws_fts, 2, '<mark>', '</mark>') as highlighted_content
            FROM laws
            JOIN laws_fts ON laws.id = laws_fts.rowid
            WHERE laws_fts MATCH ?
        '''

        params = [expanded_query]

        # 添加过滤条件
        if filters:
            if filters.get('category'):
                sql += ' AND category = ?'
                params.append(filters['category'])

            if filters.get('status'):
                sql += ' AND status = ?'
                params.append(filters['status'])

            if filters.get('start_date'):
                sql += ' AND publish_date >= ?'
                params.append(filters['start_date'])

            if filters.get('end_date'):
                sql += ' AND publish_date <= ?'
                params.append(filters['end_date'])

        sql += ' ORDER BY rank LIMIT ?'
        params.append(filters.get('limit', 50))

        return sql, params

    def extract_keywords(self, text: str) -> list:
        """从文本中提取关键词"""
        # 简单的关键词提取（可扩展为更复杂的NLP处理）
        keywords = []

        # 提取法律名称模式
        law_patterns = [
            r'《([^》]+)》',
            r'“([^”]+)”',
            r'中华人民共和国[\u4e00-\u9fa5]+法',
        ]

        for pattern in law_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)

        # 去重
        keywords = list(set(keywords))
        return keywords

    def validate_citation(self, citation: str) -> dict:
        """验证法律引用的有效性"""
        # 提取法律名称
        law_name = self._extract_law_name(citation)
        if not law_name:
            return {'valid': False, 'error': '无法提取法律名称'}

        # 解析别名
        resolved_name = self.resolve_law_alias(law_name)

        # 查找法律
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, title, status, publish_date
                    FROM laws
                    WHERE title = ? OR title LIKE ?
                ''', (resolved_name, f'%{resolved_name}%'))

                result = cursor.fetchone()
                if result:
                    return {
                        'valid': True,
                        'law_id': result[0],
                        'title': result[1],
                        'status': result[2],
                        'publish_date': result[3],
                        'resolved_name': resolved_name
                    }
                else:
                    return {'valid': False, 'error': f'未找到法律: {resolved_name}'}

        except sqlite3.Error as e:
            return {'valid': False, 'error': f'数据库查询失败: {e}'}

    def _extract_law_name(self, citation: str) -> str:
        """从引用中提取法律名称"""
        patterns = [
            r'《([^》]+)》',
            r'“([^”]+)”',
            r'《中华人民共和国[\u4e00-\u9fa5]+法》',
        ]

        for pattern in patterns:
            match = re.search(pattern, citation)
            if match:
                return match.group(1)

        return ''


class AdvancedSearch:
    """高级搜索功能"""

    def __init__(self, db_path="./download_data/legal_database.db"):
        self.db_path = Path(db_path)
        self.rewriter = QueryRewriter(db_path)

    def search(self, query: str, filters: dict = None) -> dict:
        """执行搜索"""
        if not filters:
            filters = {}

        try:
            sql, params = self.rewriter.build_search_query(query, filters)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)

                results = []
                for row in cursor.fetchall():
                    result = {
                        'title': row[0],
                        'category': row[1],
                        'publish_date': row[2],
                        'status': row[3],
                        'department': row[4],
                        'source_url': row[5],
                        'is_amendment': bool(row[6]),
                        'base_law_title': row[7],
                        'highlighted_title': row[8] or row[0],
                        'highlighted_content': row[9] or (row[0][:200] + '...' if row[0] else '')
                    }
                    results.append(result)

                return {
                    'success': True,
                    'query': query,
                    'expanded_query': self.rewriter.expand_query(query),
                    'results': results,
                    'count': len(results)
                }

        except sqlite3.Error as e:
            return {
                'success': False,
                'error': f'搜索失败: {e}',
                'query': query,
                'results': [],
                'count': 0
            }

    def batch_validate_citations(self, text: str) -> dict:
        """批量验证文本中的法律引用"""
        keywords = self.rewriter.extract_keywords(text)
        validations = {}

        for keyword in keywords:
            validations[keyword] = self.rewriter.validate_citation(keyword)

        return {
            'text': text,
            'extracted_keywords': keywords,
            'validations': validations,
            'valid_count': sum(1 for v in validations.values() if v.get('valid')),
            'invalid_count': sum(1 for v in validations.values() if not v.get('valid'))
        }

    def get_law_structure(self, law_title: str) -> dict:
        """获取法律的章节结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 查找法律
                cursor.execute('''
                    SELECT id, title, content
                    FROM laws
                    WHERE title = ? OR title LIKE ?
                ''', (law_title, f'%{law_title}%'))

                result = cursor.fetchone()
                if not result:
                    return {'success': False, 'error': f'未找到法律: {law_title}'}

                law_id, title, content = result

                # 简单的章节提取（基于常见模式）
                chapters = []
                if content:
                    # 提取章节标题
                    chapter_patterns = [
                        r'^第[一二三四五六七八九十百千\d]+章\s+(.+)$',
                        r'^第[一二三四五六七八九十百千\d]+节\s+(.+)$',
                    ]

                    for line in content.split('\n'):
                        for pattern in chapter_patterns:
                            match = re.match(pattern, line.strip())
                            if match:
                                chapters.append({
                                    'title': match.group(0),
                                    'level': 'chapter' if '章' in match.group(0) else 'section'
                                })

                return {
                    'success': True,
                    'law_id': law_id,
                    'title': title,
                    'chapters': chapters,
                    'chapter_count': len(chapters)
                }

        except sqlite3.Error as e:
            return {'success': False, 'error': f'查询失败: {e}'}


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    # 测试查询重写
    rewriter = QueryRewriter('./download_data/enhanced_legal_database.db')

    # 测试查询扩展
    expanded = rewriter.expand_query('民法典')
    print(f"查询扩展: 民法典 → {expanded}")

    # 测试别名解析
    resolved = rewriter.resolve_law_alias('民法典')
    print(f"别名解析: 民法典 → {resolved}")

    # 测试高级搜索
    search = AdvancedSearch('./download_data/enhanced_legal_database.db')

    result = search.search('民法', filters={'category': '法律'})
    print(f"\n搜索结果: 找到 {result['count']} 个结果")
    if result['success'] and result['results']:
        for r in result['results'][:3]:
            print(f"  - {r['title']}")

    # 测试引用验证
    citation_text = "根据《中华人民共和国民法典》第1024条的规定"
    validation = search.batch_validate_citations(citation_text)
    print(f"\n引用验证: {validation['valid_count']} 个有效, {validation['invalid_count']} 个无效")