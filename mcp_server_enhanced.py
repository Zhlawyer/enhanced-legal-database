#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP服务器接口 - 基于GitHub项目 sublatesublate-design/legal-database
为AI助手提供法律数据库查询接口
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from database_enhanced import EnhancedDatabase
from query_rewriter import AdvancedSearch

logger = logging.getLogger(__name__)


class LegalMCPService:
    """MCP服务类 - 提供AI友好的法律数据库接口"""

    def __init__(self, db_path="./download_data/enhanced_legal_database.db"):
        self.db_path = Path(db_path)
        self.database = EnhancedDatabase(db_path)
        self.search_engine = AdvancedSearch(db_path)

    def search_laws(self, query: str, category: Optional[str] = None,
                   status: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """
        智能检索法律法规

        Args:
            query: 搜索关键词
            category: 分类筛选（可选）
            status: 状态筛选（可选）
            limit: 结果数量限制

        Returns:
            搜索结果字典
        """
        try:
            filters = {'limit': limit}
            if category:
                filters['category'] = category
            if status:
                filters['status'] = status

            result = self.search_engine.search(query, filters)

            return {
                'success': True,
                'query': query,
                'expanded_query': result.get('expanded_query', query),
                'results': result.get('results', []),
                'count': result.get('count', 0),
                'message': f"找到 {result.get('count', 0)} 个结果"
            }

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'results': [],
                'count': 0
            }

    def get_article(self, law_title: str, article_number: int) -> Dict[str, Any]:
        """
        获取指定法律的特定条款

        Args:
            law_title: 法律标题
            article_number: 条款编号

        Returns:
            条款内容字典
        """
        try:
            # 解析别名
            resolved_title = self.search_engine.rewriter.resolve_law_alias(law_title)

            # 获取法律全文
            law = self.database.get_law_by_title(resolved_title)
            if not law:
                return {
                    'success': False,
                    'error': f'未找到法律: {law_title}',
                    'law_title': law_title
                }

            content = law.get('content', '')
            if not content:
                return {
                    'success': False,
                    'error': f'法律 {law_title} 暂无内容',
                    'law_title': law_title
                }

            # 提取指定条款（简化版）
            article_patterns = [
                f'第{article_number}条',
                f'第{article_number} 条',
            ]

            article_content = None
            for line in content.split('\n'):
                for pattern in article_patterns:
                    if pattern in line:
                        article_content = line
                        break
                if article_content:
                    break

            if article_content:
                return {
                    'success': True,
                    'law_title': resolved_title,
                    'article_number': article_number,
                    'content': article_content,
                    'message': f'成功获取 {resolved_title} 第{article_number}条'
                }
            else:
                return {
                    'success': False,
                    'error': f'未找到 {law_title} 第{article_number}条',
                    'law_title': law_title,
                    'article_number': article_number
                }

        except Exception as e:
            logger.error(f"获取条款失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'law_title': law_title,
                'article_number': article_number
            }

    def get_law_structure(self, law_title: str) -> Dict[str, Any]:
        """
        获取法律的章节结构

        Args:
            law_title: 法律标题

        Returns:
            法律结构字典
        """
        try:
            result = self.search_engine.get_law_structure(law_title)
            return result

        except Exception as e:
            logger.error(f"获取法律结构失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'law_title': law_title
            }

    def check_law_validity(self, law_title: str) -> Dict[str, Any]:
        """
        检查法律有效性

        Args:
            law_title: 法律标题

        Returns:
            有效性检查结果
        """
        try:
            # 解析别名
            resolved_title = self.search_engine.rewriter.resolve_law_alias(law_title)

            # 获取法律信息
            law = self.database.get_law_by_title(resolved_title)
            if not law:
                return {
                    'success': False,
                    'error': f'未找到法律: {law_title}',
                    'law_title': law_title,
                    'valid': False
                }

            return {
                'success': True,
                'law_title': resolved_title,
                'status': law.get('status'),
                'publish_date': law.get('publish_date'),
                'effective_date': law.get('effective_date'),
                'department': law.get('department'),
                'valid': law.get('status') == '有效',
                'message': f'{resolved_title} 当前状态: {law.get("status")}'
            }

        except Exception as e:
            logger.error(f"检查有效性失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'law_title': law_title,
                'valid': False
            }

    def batch_verify_citations(self, document_text: str) -> Dict[str, Any]:
        """
        批量校验文档中的法律引用

        Args:
            document_text: 包含法律引用的文档文本

        Returns:
            引用校验结果
        """
        try:
            result = self.search_engine.batch_validate_citations(document_text)
            return {
                'success': True,
                'document_text': document_text[:100] + '...' if len(document_text) > 100 else document_text,
                'extracted_keywords': result['extracted_keywords'],
                'validations': result['validations'],
                'valid_count': result['valid_count'],
                'invalid_count': result['invalid_count'],
                'message': f"校验完成: {result['valid_count']} 个有效, {result['invalid_count']} 个无效"
            }

        except Exception as e:
            logger.error(f"批量校验失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'document_text': document_text[:100] + '...' if len(document_text) > 100 else document_text,
                'validations': {},
                'valid_count': 0,
                'invalid_count': 0
            }

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        try:
            stats = self.database.get_statistics()
            return {
                'success': True,
                'total_laws': stats['total'],
                'category_stats': dict(stats['category_stats']),
                'status_stats': dict(stats['status_stats']),
                'recent_7days': stats['recent_7days'],
                'message': f"数据库统计: {stats['total']} 条法规"
            }

        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_laws': 0,
                'category_stats': {},
                'status_stats': {},
                'recent_7days': 0
            }

    def search_by_category(self, category: str, limit: int = 50) -> Dict[str, Any]:
        """
        按分类检索法律法规

        Args:
            category: 法律分类
            limit: 结果数量限制

        Returns:
            分类检索结果
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT title, publish_date, status, department, source_url
                    FROM laws
                    WHERE category = ? AND status = '有效'
                    ORDER BY publish_date DESC
                    LIMIT ?
                ''', (category, limit))

                results = []
                for row in cursor.fetchall():
                    results.append({
                        'title': row[0],
                        'publish_date': row[1],
                        'status': row[2],
                        'department': row[3],
                        'source_url': row[4]
                    })

                return {
                    'success': True,
                    'category': category,
                    'results': results,
                    'count': len(results),
                    'message': f'{category} 共 {len(results)} 条现行有效法规'
                }

        except Exception as e:
            logger.error(f"分类检索失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'category': category,
                'results': [],
                'count': 0
            }

    def split_articles(self, law_title: str, content: str) -> Dict[str, Any]:
        """
        拆分法律条文

        Args:
            law_title: 法律标题
            content: 法律内容

        Returns:
            拆分结果
        """
        try:
            from article_splitter import ArticleSplitter
            splitter = ArticleSplitter()

            articles = splitter.split_detailed(content, law_title)

            return {
                'success': True,
                'law_title': law_title,
                'article_count': len(articles),
                'articles': [
                    {
                        'number': a.article_number,
                        'content': a.content[:200] + '...' if len(a.content) > 200 else a.content,
                        'level': a.level
                    } for a in articles
                ],
                'message': f'成功拆分 {len(articles)} 个法条'
            }

        except Exception as e:
            logger.error(f"法条拆分失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'law_title': law_title,
                'article_count': 0
            }

    def semantic_search(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        语义搜索

        Args:
            query: 查询文本
            top_k: 结果数量

        Returns:
            搜索结果
        """
        try:
            from vector_db import EnhancedSearch
            search = EnhancedSearch(self.db_path)

            results = search.search(query, "vector", top_k)

            return {
                'success': True,
                'query': query,
                'results': results.get('vector', []),
                'count': len(results.get('vector', [])),
                'message': f'找到 {len(results.get("vector", []))} 个语义相似结果'
            }

        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'results': [],
                'count': 0
            }


# MCP工具函数（供AI调用）
def create_mcp_tools(service: LegalMCPService) -> List[Dict[str, Any]]:
    """创建MCP工具定义"""
    return [
        {
            "name": "search_laws",
            "description": "智能检索法律法规，支持关键词搜索和分类筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "category": {"type": "string", "description": "分类筛选（可选）"},
                    "status": {"type": "string", "description": "状态筛选（可选）"},
                    "limit": {"type": "integer", "description": "结果数量限制", "default": 20}
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_article",
            "description": "获取指定法律的特定条款",
            "parameters": {
                "type": "object",
                "properties": {
                    "law_title": {"type": "string", "description": "法律标题"},
                    "article_number": {"type": "integer", "description": "条款编号"}
                },
                "required": ["law_title", "article_number"]
            }
        },
        {
            "name": "get_law_structure",
            "description": "获取法律的章节结构",
            "parameters": {
                "type": "object",
                "properties": {
                    "law_title": {"type": "string", "description": "法律标题"}
                },
                "required": ["law_title"]
            }
        },
        {
            "name": "check_law_validity",
            "description": "检查法律有效性",
            "parameters": {
                "type": "object",
                "properties": {
                    "law_title": {"type": "string", "description": "法律标题"}
                },
                "required": ["law_title"]
            }
        },
        {
            "name": "batch_verify_citations",
            "description": "批量校验文档中的法律引用",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_text": {"type": "string", "description": "包含法律引用的文档文本"}
                },
                "required": ["document_text"]
            }
        },
        {
            "name": "get_statistics",
            "description": "获取数据库统计信息",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "search_by_category",
            "description": "按分类检索法律法规",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "法律分类"},
                    "limit": {"type": "integer", "description": "结果数量限制", "default": 50}
                },
                "required": ["category"]
            }
        },
        {
            "name": "split_articles",
            "description": "拆分法律条文为独立条款",
            "parameters": {
                "type": "object",
                "properties": {
                    "law_title": {"type": "string", "description": "法律标题"},
                    "content": {"type": "string", "description": "法律内容文本"}
                },
                "required": ["law_title", "content"]
            }
        },
        {
            "name": "semantic_search",
            "description": "语义搜索（基于向量相似度）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询文本"},
                    "top_k": {"type": "integer", "description": "结果数量", "default": 10}
                },
                "required": ["query"]
            }
        }
    ]


# 示例使用
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    # 创建服务实例
    service = LegalMCPService('./download_data/enhanced_legal_database.db')

    print("=== MCP服务测试 ===")

    # 测试搜索
    result = service.search_laws("民法", limit=5)
    print(f"\n1. 搜索测试:")
    print(f"   查询: 民法")
    print(f"   结果: {result['count']} 个")
    if result['success'] and result['results']:
        for r in result['results'][:3]:
            print(f"   - {r['title']}")

    # 测试别名解析
    result = service.check_law_validity("民法典")
    print(f"\n2. 有效性检查:")
    print(f"   法律: 民法典")
    print(f"   状态: {result.get('status', '未知')}")

    # 测试统计
    result = service.get_statistics()
    print(f"\n3. 数据库统计:")
    print(f"   总法规数: {result.get('total_laws', 0)}")
    print(f"   最近7天更新: {result.get('recent_7days', 0)}")

    # 测试分类检索
    result = service.search_by_category("法律", limit=10)
    print(f"\n4. 分类检索:")
    print(f"   分类: 法律")
    print(f"   结果: {result['count']} 条现行有效法规")

    print("\n=== MCP工具定义 ===")
    tools = create_mcp_tools(service)
    for tool in tools:
        print(f"- {tool['name']}: {tool['description']}")