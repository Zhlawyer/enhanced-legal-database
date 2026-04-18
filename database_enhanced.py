#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版数据库架构 - 基于GitHub项目 sublatesublate-design/legal-database
提供完整的数据库表结构和管理功能

特性：
- 扩展字段支持（short_title, document_number, expiry_date等）
- 智能法条拆分和存储
- FTS5全文检索 + 自动触发器
- 连接池优化 + 性能调优
- 批量插入优化
"""

import sqlite3
import logging
import time
from pathlib import Path
from datetime import datetime
import threading
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """数据库操作异常"""
    pass


class EnhancedDatabase:
    """增强版数据库管理类"""

    def __init__(self, db_path="./download_data/legal_database.db", pool_size: int = 5):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 数据库连接池配置
        self.pool_size = pool_size
        self.connections = []
        self.lock = threading.Lock()
        self._init_pool()

        # 初始化数据库
        self.init_database()

    def _init_pool(self):
        """初始化连接池"""
        try:
            for _ in range(self.pool_size):
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                # 配置性能优化
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=-64000")
                conn.execute("PRAGMA temp_store=MEMORY")
                self.connections.append(conn)
            logger.info(f"连接池初始化完成: {self.pool_size} 个连接")
        except Exception as e:
            logger.error(f"连接池初始化失败: {e}")
            raise DatabaseError(f"无法初始化数据库连接池: {e}")

    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. 法律法规主表（扩展字段）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS laws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                short_title TEXT,           -- 短标题
                category TEXT NOT NULL,
                publish_date TEXT,
                effective_date TEXT,
                expiry_date TEXT,           -- 失效日期
                status TEXT,                -- active/repealed/amended/pending
                content TEXT,
                department TEXT,
                file_name TEXT,
                source_url TEXT,
                document_number TEXT,       -- 文号
                is_amendment INTEGER DEFAULT 0,
                base_law_title TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. 全文搜索虚拟表 (FTS5)
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS laws_fts USING fts5(
                title,
                content,
                content='laws',
                content_rowid='id',
                tokenize='trigram'
            )
        ''')

        # 3. 法律别名表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS law_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alias TEXT NOT NULL,
                law_id INTEGER NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (law_id) REFERENCES laws(id) ON DELETE CASCADE,
                UNIQUE(alias, law_id)
            )
        ''')

        # 4. 法律概念同义词表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS concept_synonyms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT NOT NULL,
                canonical_term TEXT NOT NULL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(term, canonical_term)
            )
        ''')

        # 5. 下载记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                law_id INTEGER,
                title TEXT NOT NULL,
                category TEXT,
                download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                file_path TEXT,
                FOREIGN KEY (law_id) REFERENCES laws(id)
            )
        ''')

        # 6. 修订历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS law_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                law_id INTEGER NOT NULL,
                revision_date TEXT NOT NULL,
                revision_type TEXT,           -- amendment/repeal/replace
                description TEXT,
                content_diff TEXT,
                FOREIGN KEY (law_id) REFERENCES laws(id) ON DELETE CASCADE
            )
        ''')

        # 6. 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_laws_category ON laws(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_laws_status ON laws(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_laws_publish_date ON laws(publish_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_laws_title ON laws(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_laws_category ON laws(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_aliases_alias ON law_aliases(alias)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_synonyms_term ON concept_synonyms(term)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_law_id ON articles(law_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_number ON articles(article_number)')

        # 7. 配置FTS5触发器（自动同步）
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS laws_ai AFTER INSERT ON laws BEGIN
                INSERT INTO laws_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
            END;
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS laws_ad AFTER DELETE ON laws BEGIN
                INSERT INTO laws_fts(laws_fts, rowid, title, content) VALUES ('delete', old.id, old.title, old.content);
            END;
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS laws_au AFTER UPDATE ON laws BEGIN
                INSERT INTO laws_fts(laws_fts, rowid, title, content) VALUES ('delete', old.id, old.title, old.content);
                INSERT INTO laws_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
            END;
        ''')

        conn.commit()
        conn.close()

        logger.info(f"数据库初始化完成: {self.db_path}")

    @contextmanager
    def get_connection(self):
        """获取数据库连接（连接池）"""
        with self.lock:
            if self.connections:
                conn = self.connections.pop()
            else:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                # 配置性能优化
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=-64000")
                conn.execute("PRAGMA temp_store=MEMORY")

        try:
            yield conn
        finally:
            with self.lock:
                if len(self.connections) < self.pool_size:
                    self.connections.append(conn)
                else:
                    conn.close()

    def add_law(self, title, category, publish_date=None, effective_date=None,
                status="active", content=None, department=None, source_url=None,
                is_amendment=0, base_law_title=None, short_title=None,
                document_number=None, expiry_date=None):
        """添加法律法规（支持扩展字段）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO laws (
                    title, short_title, category, publish_date, effective_date,
                    expiry_date, status, content, department, source_url,
                    document_number, is_amendment, base_law_title, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, short_title, category, publish_date, effective_date,
                  expiry_date, status, content, department, source_url,
                  document_number, is_amendment, base_law_title, datetime.now()))

            law_id = cursor.lastrowid

            # 同步到FTS5索引
            if content:
                cursor.execute('''
                    INSERT INTO laws_fts(rowid, title, content)
                    VALUES (?, ?, ?)
                ''', (law_id, title, content))

            conn.commit()
            return law_id

    def add_law_with_split(self, auto_split: bool = True, **law_data):
        """
        添加法律法规并可选择自动拆分法条

        Args:
            auto_split: 是否自动拆分法条
            **law_data: 法律数据

        Returns:
            法律ID和拆分结果
        """
        # 添加法律
        law_id = self.add_law(**law_data)

        if auto_split and law_id and law_data.get('content'):
            # 自动拆分法条
            from article_splitter import DatabaseArticleManager
            splitter = DatabaseArticleManager(self.db_path)
            splitter.init_article_tables()

            split_result = splitter.split_and_store(
                law_id,
                law_data.get('title', ''),
                law_data.get('content', '')
            )

            return {
                'law_id': law_id,
                'split_result': split_result
            }

        return {'law_id': law_id, 'split_result': None}

    def batch_add_laws(self, laws_data: list, batch_size: int = 100) -> Dict[str, Any]:
        """
        批量添加法律法规（优化性能）

        Args:
            laws_data: 法律数据列表
            batch_size: 批次大小

        Returns:
            批量插入结果
        """
        import time
        start_time = time.time()

        successful = 0
        failed = 0
        errors = []

        for i in range(0, len(laws_data), batch_size):
            batch = laws_data[i:i + batch_size]

            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    for law_data in batch:
                        try:
                            cursor.execute('''
                                INSERT INTO laws (
                                    title, short_title, category, publish_date, effective_date,
                                    expiry_date, status, content, department, source_url,
                                    document_number, is_amendment, base_law_title, last_updated
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                law_data.get('title'),
                                law_data.get('short_title'),
                                law_data.get('category'),
                                law_data.get('publish_date'),
                                law_data.get('effective_date'),
                                law_data.get('expiry_date'),
                                law_data.get('status', 'active'),
                                law_data.get('content'),
                                law_data.get('department'),
                                law_data.get('source_url'),
                                law_data.get('document_number'),
                                law_data.get('is_amendment', 0),
                                law_data.get('base_law_title'),
                                datetime.now()
                            ))

                            law_id = cursor.lastrowid

                            # 同步到FTS5
                            if law_data.get('content'):
                                cursor.execute('''
                                    INSERT INTO laws_fts(rowid, title, content)
                                    VALUES (?, ?, ?)
                                ''', (law_id, law_data.get('title'), law_data.get('content')))

                            successful += 1

                        except Exception as e:
                            failed += 1
                            errors.append({'title': law_data.get('title'), 'error': str(e)})

                    conn.commit()

            except Exception as e:
                logger.error(f"批量插入批次失败: {e}")
                failed += len(batch)

        elapsed_time = time.time() - start_time

        return {
            'successful': successful,
            'failed': failed,
            'total': len(laws_data),
            'elapsed_time': elapsed_time,
            'errors': errors[:10],  # 只返回前10个错误
            'message': f'批量插入完成: 成功 {successful}, 失败 {failed}, 耗时 {elapsed_time:.2f}秒'
        }

    def add_alias(self, alias, law_title, confidence=1.0):
        """添加法律别名"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 查找法律ID
            cursor.execute('SELECT id FROM laws WHERE title = ?', (law_title,))
            result = cursor.fetchone()
            if not result:
                logger.warning(f"未找到法律: {law_title}")
                return False

            law_id = result[0]

            # 添加别名
            cursor.execute('''
                INSERT OR REPLACE INTO law_aliases (alias, law_id, confidence)
                VALUES (?, ?, ?)
            ''', (alias, law_id, confidence))

            conn.commit()
            return True

    def add_synonym(self, term, canonical_term, category=None):
        """添加概念同义词"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO concept_synonyms (term, canonical_term, category)
                VALUES (?, ?, ?)
            ''', (term, canonical_term, category))

            conn.commit()
            return True

    def search_laws(self, query, category=None, status=None, limit=50):
        """搜索法律法规"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 构建查询
            sql = '''
                SELECT title, category, publish_date, status, department, source_url
                FROM laws
                WHERE (title LIKE ? OR content LIKE ?)
            '''
            params = [f'%{query}%', f'%{query}%']

            if category:
                sql += ' AND category = ?'
                params.append(category)

            if status:
                sql += ' AND status = ?'
                params.append(status)

            sql += ' ORDER BY publish_date DESC LIMIT ?'
            params.append(limit)

            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_law_by_title(self, title):
        """根据标题获取法律"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, title, category, publish_date, status,
                       content, department, source_url, is_amendment, base_law_title
                FROM laws
                WHERE title = ?
            ''', (title,))

            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'title': result[1],
                    'category': result[2],
                    'publish_date': result[3],
                    'status': result[4],
                    'content': result[5],
                    'department': result[6],
                    'source_url': result[7],
                    'is_amendment': result[8],
                    'base_law_title': result[9]
                }
            return None

    def resolve_alias(self, query):
        """解析法律别名"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 查找别名匹配
            cursor.execute('''
                SELECT l.title, l.id, la.confidence
                FROM law_aliases la
                JOIN laws l ON la.alias = ?
                AND la.law_id = l.id
                WHERE l.status = '有效'
                ORDER BY la.confidence DESC
                LIMIT 1
            ''', (query,))

            result = cursor.fetchone()
            if result:
                return result[0]  # 返回标准标题
            return None

    def get_statistics(self):
        """获取数据库统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 总数统计
            cursor.execute('SELECT COUNT(*) FROM laws')
            total = cursor.fetchone()[0]

            # 分类统计
            cursor.execute('''
                SELECT category, COUNT(*) as count
                FROM laws
                GROUP BY category
                ORDER BY count DESC
            ''')
            category_stats = cursor.fetchall()

            # 状态统计
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM laws
                GROUP BY status
            ''')
            status_stats = cursor.fetchall()

            # 最近更新
            cursor.execute('''
                SELECT COUNT(*) FROM laws
                WHERE last_updated >= datetime('now', '-7 days')
            ''')
            recent_count = cursor.fetchone()[0]

            return {
                'total': total,
                'category_stats': category_stats,
                'status_stats': status_stats,
                'recent_7days': recent_count
            }

    def export_to_json(self, output_file=None):
        """导出数据库到JSON"""
        import json

        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.db_path.parent / f"laws_export_{timestamp}.json"

        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT title, category, publish_date, effective_date,
                       status, content, department, source_url,
                       is_amendment, base_law_title
                FROM laws
                ORDER BY category, publish_date DESC
            ''')

            laws = []
            for row in cursor.fetchall():
                law = {
                    'title': row[0],
                    'category': row[1],
                    'publish_date': row[2],
                    'effective_date': row[3],
                    'status': row[4],
                    'content': row[5],
                    'department': row[6],
                    'source_url': row[7],
                    'is_amendment': bool(row[8]),
                    'base_law_title': row[9]
                }
                laws.append(law)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(laws, f, ensure_ascii=False, indent=2)

        logger.info(f"数据已导出到: {output_file}")
        return output_file


def init_sample_data(db):
    """初始化示例数据"""
    # 添加法律法规
    laws = [
        {
            'title': '中华人民共和国民法典',
            'category': '法律',
            'publish_date': '2020-05-28',
            'status': '有效',
            'department': '全国人大常委会',
            'content': '中华人民共和国民法典是为了保护民事主体的合法权益...调整民事关系...'
        },
        {
            'title': '中华人民共和国宪法',
            'category': '宪法',
            'publish_date': '2018-03-11',
            'status': '有效',
            'department': '全国人大',
            'content': '中华人民共和国是工人阶级领导的、以工农联盟为基础的人民民主专政的社会主义国家...'
        }
    ]

    for law in laws:
        law_id = db.add_law(**law)
        logger.info(f"添加法规: {law['title']} (ID: {law_id})")

    # 添加别名
    db.add_alias('民法典', '中华人民共和国民法典')
    db.add_alias('宪法', '中华人民共和国宪法')

    # 添加同义词
    db.add_synonym('债权人撤销权', '撤销权', '民法')
    db.add_synonym('合同撤销权', '撤销权', '民法')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # 创建增强版数据库
    db = EnhancedDatabase('./download_data/enhanced_legal_database.db')

    # 初始化示例数据
    init_sample_data(db)

    # 测试搜索
    results = db.search_laws('民法')
    print(f"搜索'民法'找到 {len(results)} 个结果:")
    for title, category, publish_date, status, department, url in results:
        print(f"  - [{category}] {title}")

    # 测试统计
    stats = db.get_statistics()
    print(f"\n数据库统计:")
    print(f"  总法规数: {stats['total']}")
    print(f"  最近7天更新: {stats['recent_7days']}")

    # 测试别名解析
    resolved = db.resolve_alias('民法典')
    print(f"\n别名解析: 民法典 → {resolved}")