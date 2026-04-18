#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量检索模块 - 基于GitHub项目 sublatesublate-design/legal-database
支持语义搜索和相似度检索
"""

import sqlite3
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import pickle
import hashlib

logger = logging.getLogger(__name__)


class VectorIndex:
    """向量索引类"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.vectors = None
        self.article_ids = []
        self._initialized = False

    def init_vector_table(self):
        """初始化向量表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 向量表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS article_vectors (
                article_id INTEGER PRIMARY KEY,
                law_id INTEGER NOT NULL,
                vector_blob BLOB,
                embedding_model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
            )
        ''')

        # 向量索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vectors_law_id ON article_vectors(law_id)')

        conn.commit()
        conn.close()

    def generate_embedding(self, text: str, model: str = "trigram") -> np.ndarray:
        """
        生成文本向量（简化版）

        Args:
            text: 输入文本
            model: 嵌入模型

        Returns:
            向量数组
        """
        if model == "trigram":
            # 使用字符三元组作为特征
            chars = list(text)
            trigrams = [''.join(chars[i:i+3]) for i in range(len(chars)-2)]

            # 统计三元组频率
            feature_vector = {}
            for trigram in trigrams:
                feature_vector[trigram] = feature_vector.get(trigram, 0) + 1

            # 转换为固定长度向量（简化处理）
            vector = np.zeros(1000)
            for i, (trigram, count) in enumerate(list(feature_vector.items())[:1000]):
                vector[i] = count

            return vector

        elif model == "hash":
            # 使用哈希作为向量
            text_hash = hashlib.md5(text.encode()).hexdigest()
            vector = np.zeros(256)
            for i, char in enumerate(text_hash[:256]):
                vector[i] = ord(char) % 256
            return vector

        else:
            # 默认使用随机向量（实际应用中应使用真实模型）
            np.random.seed(hash(text) % (2**32))
            return np.random.randn(128)

    def build_index(self, force_rebuild: bool = False):
        """构建向量索引"""
        if self._initialized and not force_rebuild:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取所有法条
            cursor.execute('''
                SELECT a.id, a.law_id, a.content
                FROM articles a
                WHERE a.content IS NOT NULL AND LENGTH(a.content) > 0
            ''')

            articles = cursor.fetchall()
            if not articles:
                logger.warning("没有找到可索引的法条")
                return

            vectors = []
            article_ids = []

            for article_id, law_id, content in articles:
                # 生成向量
                vector = self.generate_embedding(content)
                vectors.append(vector)
                article_ids.append(article_id)

                # 存储到数据库
                vector_blob = pickle.dumps(vector)
                cursor.execute('''
                    INSERT OR REPLACE INTO article_vectors
                    (article_id, law_id, vector_blob, embedding_model)
                    VALUES (?, ?, ?, ?)
                ''', (article_id, law_id, vector_blob, 'trigram'))

            conn.commit()
            conn.close()

            # 保存到内存
            self.vectors = np.array(vectors)
            self.article_ids = article_ids
            self._initialized = True

            logger.info(f"向量索引构建完成: {len(article_ids)} 个法条")

        except Exception as e:
            logger.error(f"构建向量索引失败: {e}")

    def search(self, query: str, top_k: int = 10, min_similarity: float = 0.0) -> List[Dict[str, Any]]:
        """
        语义搜索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            搜索结果列表
        """
        if not self._initialized:
            self.build_index()

        if self.vectors is None or len(self.vectors) == 0:
            return []

        try:
            # 生成查询向量
            query_vector = self.generate_embedding(query)

            # 计算余弦相似度
            similarities = np.dot(self.vectors, query_vector) / (
                np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(query_vector)
            )

            # 获取top-k结果
            top_indices = np.argsort(similarities)[-top_k:][::-1]

            results = []
            for idx in top_indices:
                similarity = similarities[idx]
                if similarity < min_similarity:
                    continue

                article_id = self.article_ids[idx]
                result = self._get_article_info(article_id)
                if result:
                    result['similarity'] = float(similarity)
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []

    def _get_article_info(self, article_id: int) -> Optional[Dict[str, Any]]:
        """获取法条信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT a.law_title, a.article_number, a.content, a.level, l.title
                FROM articles a
                JOIN laws l ON a.law_id = l.id
                WHERE a.id = ?
            ''', (article_id,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'law_title': result[0],
                    'article_number': result[1],
                    'content': result[2][:200] + '...' if len(result[2]) > 200 else result[2],
                    'level': result[3],
                    'parent_law': result[4]
                }
            return None

        except Exception as e:
            logger.error(f"获取法条信息失败: {e}")
            return None

    def get_similar_articles(self, article_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取相似法条"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取当前法条向量
            cursor.execute('SELECT vector_blob FROM article_vectors WHERE article_id = ?', (article_id,))
            result = cursor.fetchone()
            conn.close()

            if not result:
                return []

            current_vector = pickle.loads(result[0])

            # 计算相似度
            similarities = np.dot(self.vectors, current_vector) / (
                np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(current_vector)
            )

            # 排除自己，获取top-k
            top_indices = np.argsort(similarities)[-top_k-1:-1][::-1]

            results = []
            for idx in top_indices:
                similar_article_id = self.article_ids[idx]
                result = self._get_article_info(similar_article_id)
                if result:
                    result['similarity'] = float(similarities[idx])
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"获取相似法条失败: {e}")
            return []


class EnhancedSearch:
    """增强搜索（结合关键词和语义搜索）"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.vector_index = VectorIndex(db_path)

    def search(self, query: str, method: str = "hybrid", top_k: int = 20) -> Dict[str, Any]:
        """
        混合搜索

        Args:
            query: 查询文本
            method: 搜索方法 (keyword/vector/hybrid)
            top_k: 结果数量

        Returns:
            搜索结果
        """
        results = {}

        if method in ["keyword", "hybrid"]:
            # 关键词搜索
            keyword_results = self._keyword_search(query, top_k)
            results['keyword'] = keyword_results

        if method in ["vector", "hybrid"]:
            # 语义搜索
            vector_results = self.vector_index.search(query, top_k)
            results['vector'] = vector_results

        if method == "hybrid":
            # 融合结果
            hybrid_results = self._merge_results(
                results.get('keyword', []),
                results.get('vector', [])
            )
            results['hybrid'] = hybrid_results

        results['method'] = method
        results['query'] = query

        return results

    def _keyword_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """关键词搜索"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT a.law_title, a.article_number, a.content, a.level, l.title
                FROM articles a
                JOIN laws l ON a.law_id = l.id
                WHERE a.content LIKE ? OR a.article_number LIKE ?
                ORDER BY l.title, a.order_num
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'law_title': row[0],
                    'article_number': row[1],
                    'content': row[2][:200] + '...' if len(row[2]) > 200 else row[2],
                    'level': row[3],
                    'parent_law': row[4],
                    'source': 'keyword'
                })

            conn.close()
            return results

        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []

    def _merge_results(self, keyword_results: List[Dict], vector_results: List[Dict]) -> List[Dict]:
        """融合关键词和语义搜索结果"""
        # 创建去重映射
        result_map = {}

        # 添加关键词结果（较高优先级）
        for i, result in enumerate(keyword_results):
            key = f"{result['law_title']}_{result['article_number']}"
            if key not in result_map:
                result['score'] = 1.0 - (i * 0.01)  # 排名得分
                result_map[key] = result

        # 添加语义结果
        for i, result in enumerate(vector_results):
            key = f"{result['law_title']}_{result['article_number']}"
            if key not in result_map:
                result['score'] = result.get('similarity', 0.5)
                result_map[key] = result
            else:
                # 融合得分
                existing = result_map[key]
                existing['score'] = max(existing['score'], result.get('similarity', 0))

        # 按得分排序
        merged = sorted(result_map.values(), key=lambda x: x.get('score', 0), reverse=True)
        return merged[:20]  # 限制结果数量


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    # 测试向量检索
    print("=== 向量检索测试 ===")

    # 创建测试数据
    db_path = './download_data/enhanced_legal_database.db'
    vector_index = VectorIndex(db_path)
    vector_index.init_vector_table()

    print("✅ 向量表结构初始化完成")

    # 测试搜索
    enhanced_search = EnhancedSearch(db_path)

    # 由于数据库为空，这里只测试框架
    print("✅ 增强搜索框架准备就绪")