#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国法律法规下载器 v7.0
基于 flk.npc.gov.cn 国家法律法规数据库官方API

功能特性：
- 自动获取所有现行有效法律法规
- 按类型分类存储（宪法/法律/行政法规/司法解释等）
- 增量更新：已下载法规自动跳过
- 结构化存储：保存法规全文、发布部门、生效日期等完整信息
- 支持进度显示和断点续传
- 集成SQLite数据库 + JSON导出

用法：
    python3 law_downloader.py                    # 交互式下载
    python3 law_downloader.py --auto             # 自动下载全部
    python3 law_downloader.py --category 法律     # 仅下载法律类
    python3 law_downloader.py --status 有效       # 仅下载有效法规
"""

import os
import sys
import json
import time
import sqlite3
import logging
import argparse
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import quote

# 尝试导入 requests
import urllib.request
import urllib.error
import urllib.parse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("未安装 requests，将使用 urllib 作为备选")


# ============ 配置 ============
BASE_URL = "https://flk.npc.gov.cn"
SEARCH_URL = f"{BASE_URL}/law-search/search/list"
ENUM_URL = f"{BASE_URL}/law-search/search/enumData"
DETAIL_URL = f"{BASE_URL}/law-search/search/flfgDetails"

# 默认User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/detail.html",
}

# 法规类型映射
CATEGORY_MAP = {
    "宪法": {"codeId": "100", "id": "1"},
    "法律": {"codeId": "101", "id": "2"},
    "行政法规": {"codeId": "201", "id": "14"},
    "监察法规": {"codeId": "220", "id": "15"},
    "地方法规": {"codeId": "221", "id": "16"},
    "司法解释": {"codeId": "311", "id": "27"},
    "部门规章": {"codeId": "410", "id": "36"},
    "军事法规": {"codeId": "501", "id": "43"},
}

# 法规状态映射
STATUS_MAP = {
    "有效": "3",
    "已修改": "2",
    "尚未生效": "4",
    "已废止": "1",
}

# 请求间隔（秒）- 避免请求过快
REQUEST_DELAY = 1.5


# ============ 日志配置 ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============ 数据库管理 ============
class LawDatabase:
    """法规数据库管理"""

    def __init__(self, db_path="./download_data/legal_laws.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_tables()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def init_tables(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 法规主表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS laws (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    law_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    publish_date TEXT,
                    effective_date TEXT,
                    status TEXT,
                    department TEXT,
                    document_number TEXT,
                    content TEXT,
                    download_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    source_url TEXT,
                    md5_hash TEXT
                )
            ''')

            # 下载记录表（用于增量更新）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS download_log (
                    law_id TEXT PRIMARY KEY,
                    title TEXT,
                    category TEXT,
                    status TEXT,
                    download_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    update_time TEXT
                )
            ''')

            # 索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_laws_category ON laws(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_laws_status ON laws(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_laws_title ON laws(title)')

            conn.commit()
            logger.info("数据库表初始化完成")

    def save_law(self, law_data: Dict[str, Any]) -> bool:
        """保存法规到数据库"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO laws
                    (law_id, title, category, publish_date, effective_date,
                     status, department, document_number, content, source_url, md5_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    law_data.get('law_id', ''),
                    law_data.get('title', ''),
                    law_data.get('category', ''),
                    law_data.get('publish_date', ''),
                    law_data.get('effective_date', ''),
                    law_data.get('status', ''),
                    law_data.get('department', ''),
                    law_data.get('document_number', ''),
                    law_data.get('content', ''),
                    law_data.get('source_url', ''),
                    hashlib.md5(str(law_data.get('content', '')).encode()).hexdigest()[:16]
                ))

                # 更新下载日志
                cursor.execute('''
                    INSERT OR REPLACE INTO download_log
                    (law_id, title, category, status, update_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    law_data.get('law_id', ''),
                    law_data.get('title', ''),
                    law_data.get('category', ''),
                    law_data.get('status', ''),
                    datetime.now().isoformat()
                ))

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"保存法规失败 [{law_data.get('title', '?')}]: {e}")
            return False

    def is_downloaded(self, law_id: str) -> bool:
        """检查法规是否已下载"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT 1 FROM download_log WHERE law_id = ?',
                    (law_id,)
                )
                return cursor.fetchone() is not None
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 总数量
                cursor.execute('SELECT COUNT(*) FROM laws')
                total = cursor.fetchone()[0]

                # 按分类统计
                cursor.execute('''
                    SELECT category, COUNT(*) FROM laws
                    GROUP BY category ORDER BY COUNT(*) DESC
                ''')
                by_category = dict(cursor.fetchall())

                # 按状态统计
                cursor.execute('''
                    SELECT status, COUNT(*) FROM laws
                    GROUP BY status ORDER BY COUNT(*) DESC
                ''')
                by_status = dict(cursor.fetchall())

                return {
                    'total': total,
                    'by_category': by_category,
                    'by_status': by_status
                }
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {'total': 0, 'by_category': {}, 'by_status': {}}

    def export_to_json(self, output_dir: str = "./download_data/export") -> str:
        """导出为JSON文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM laws')
                rows = cursor.fetchall()

                laws = []
                for row in rows:
                    laws.append(dict(row))

                # 按分类导出
                for category in CATEGORY_MAP.keys():
                    category_laws = [l for l in laws if l.get('category') == category]
                    if category_laws:
                        filename = f"laws_{category}.json"
                        filepath = output_path / filename
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(category_laws, f, ensure_ascii=False, indent=2)
                        logger.info(f"导出 {category}: {len(category_laws)} 条 -> {filename}")

                # 全部导出
                all_path = output_path / 'all_laws.json'
                with open(all_path, 'w', encoding='utf-8') as f:
                    json.dump(laws, f, ensure_ascii=False, indent=2)

                logger.info(f"导出完成: {len(laws)} 条法规 -> {output_path}")
                return str(output_path)

        except Exception as e:
            logger.error(f"导出失败: {e}")
            return ""


# ============ HTTP请求工具 ============
class HttpClient:
    """HTTP请求客户端"""

    def __init__(self):
        self.session = None
        if HAS_REQUESTS:
            self.session = requests.Session()
            self.session.headers.update(HEADERS)

    def post(self, url: str, data: Dict[str, Any] = None, timeout: int = 30) -> Optional[Dict]:
        """发送POST请求"""
        time.sleep(REQUEST_DELAY)  # 请求间隔

        try:
            if HAS_REQUESTS and self.session:
                response = self.session.post(url, data=data, timeout=timeout)
                response.raise_for_status()
                return response.json()
            else:
                # 使用urllib作为备选
                encoded_data = urllib.parse.urlencode(data or {}).encode('utf-8')
                req = urllib.request.Request(url, data=encoded_data, headers=HEADERS, method='POST')
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content = response.read().decode('utf-8')
                    return json.loads(content)

        except Exception as e:
            logger.error(f"请求失败 [{url}]: {e}")
            return None

    def get(self, url: str, timeout: int = 30) -> Optional[str]:
        """发送GET请求"""
        time.sleep(REQUEST_DELAY)

        try:
            if HAS_REQUESTS and self.session:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response.text
            else:
                req = urllib.request.Request(url, headers=HEADERS, method='GET')
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read().decode('utf-8')

        except Exception as e:
            logger.error(f"请求失败 [{url}]: {e}")
            return None


# ============ 法规下载器 ============
class LawDownloader:
    """法规下载器"""

    def __init__(self, db: LawDatabase, data_dir: str = "./download_data"):
        self.db = db
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.client = HttpClient()

        # 按类型创建目录
        for category in CATEGORY_MAP.keys():
            (self.data_dir / category).mkdir(exist_ok=True)

        # 统计
        self.stats = {
            'total_found': 0,
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'by_category': {}
        }

    def search_laws(self, category: str = None, status: str = "有效",
                    page: int = 1, page_size: int = 20) -> List[Dict]:
        """搜索法规列表"""
        params = {
            "sortType": "1",
            "page": str(page),
            "size": str(page_size),
        }

        if category and category in CATEGORY_MAP:
            params["codeId"] = CATEGORY_MAP[category]["codeId"]
            params["id"] = CATEGORY_MAP[category]["id"]

        if status and status in STATUS_MAP:
            params["status"] = STATUS_MAP[status]

        logger.debug(f"搜索: category={category}, status={status}, page={page}")

        result = self.client.post(SEARCH_URL, params)
        if not result:
            return []

        if isinstance(result, dict) and "result" in result:
            data = result["result"]
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            elif isinstance(data, list):
                return data

        return []

    def get_law_detail(self, law_id: str) -> Optional[Dict]:
        """获取法规详情"""
        if not law_id:
            return None

        url = f"{DETAIL_URL}?id={law_id}"
        html = self.client.get(url)

        if not html:
            return None

        # 解析HTML提取法规内容
        return self.parse_law_detail(html, law_id, url)

    def parse_law_detail(self, html: str, law_id: str, url: str) -> Optional[Dict]:
        """解析法规详情HTML"""
        try:
            law_data = {
                'law_id': law_id,
                'source_url': url,
                'content': '',
                'title': '',
                'category': '',
                'department': '',
                'document_number': '',
                'publish_date': '',
                'effective_date': '',
                'status': ''
            }

            # 提取标题
            title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                title = re.sub(r'\s*-\s*.*$', '', title)
                law_data['title'] = title

            # 尝试从页面中提取结构化信息
            # 发布部门
            dept_match = re.search(r'发布部门[：:]\s*([^<\n]+)', html)
            if dept_match:
                law_data['department'] = dept_match.group(1).strip()

            # 发文字号
            doc_match = re.search(r'发文字号[：:]\s*([^<\n]+)', html)
            if doc_match:
                law_data['document_number'] = doc_match.group(1).strip()

            # 发布日期
            date_match = re.search(r'发布日期[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', html)
            if date_match:
                law_data['publish_date'] = date_match.group(1).replace('/', '-')

            # 实施日期
            eff_match = re.search(r'实施日期[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', html)
            if eff_match:
                law_data['effective_date'] = eff_match.group(1).replace('/', '-')

            # 提取法规正文内容
            content = self.extract_content(html)
            if content:
                law_data['content'] = content

            return law_data

        except Exception as e:
            logger.error(f"解析法规详情失败 [{law_id}]: {e}")
            return None

    def extract_content(self, html: str) -> str:
        """从HTML中提取法规正文"""
        content_parts = []

        # 尝试多种方式提取正文
        # 方式1：查找 commonLawsContent 或类似ID的div
        patterns = [
            r'<div[^>]*id="commonLawsContent"[^>]*>(.*?)</div>\s*</div>\s*</div>',
            r'<div[^>]*class="detail_content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="content"[^>]*>(.*?)</div>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1)
                content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'&nbsp;', ' ', content)
                content = re.sub(r'&[a-zA-Z]+;', '', content)
                content = re.sub(r'\n\s*\n', '\n\n', content)
                content = content.strip()
                if len(content) > 100:
                    return content

        # 方式2：提取所有文本段落
        text_pattern = re.findall(r'<p[^>]*>([^<]{20,})</p>', html)
        if text_pattern:
            return '\n\n'.join(text_pattern)

        return ""

    def download_category(self, category: str, status: str = "有效",
                          max_pages: Optional[int] = None) -> Dict[str, Any]:
        """下载指定分类的法规"""
        logger.info(f"=" * 60)
        logger.info(f"开始下载: {category} ({status})")
        logger.info(f"=" * 60)

        page = 1
        total_downloaded = 0
        total_skipped = 0
        total_failed = 0

        while True:
            if max_pages and page > max_pages:
                logger.info(f"达到最大页数限制: {max_pages}")
                break

            laws = self.search_laws(category=category, status=status, page=page)

            if not laws:
                logger.info(f"第 {page} 页无数据，下载完成")
                break

            logger.info(f"第 {page} 页: 找到 {len(laws)} 条法规")

            for law in laws:
                law_id = law.get('id', '') or law.get('lawId', '')
                title = law.get('title', '') or law.get('lawTitle', '')

                if not law_id or not title:
                    continue

                # 检查是否已下载
                if self.db.is_downloaded(law_id):
                    total_skipped += 1
                    logger.debug(f"已下载，跳过: {title}")
                    continue

                # 获取详情
                detail = self.get_law_detail(law_id)

                if detail:
                    # 补充分类信息
                    detail['category'] = category
                    detail['status'] = status

                    # 保存到数据库
                    if self.db.save_law(detail):
                        total_downloaded += 1
                        logger.info(f"✅ 下载成功: {title}")
                    else:
                        total_failed += 1
                        logger.warning(f"❌ 保存失败: {title}")
                else:
                    total_failed += 1
                    logger.warning(f"❌ 获取详情失败: {title}")

                # 每10条暂停一下
                if (total_downloaded + total_failed) % 10 == 0:
                    logger.info(f"进度: 已下载 {total_downloaded} | 跳过 {total_skipped} | 失败 {total_failed}")

            # 检查是否还有更多页
            if len(laws) < 20:
                logger.info("已到达最后一页")
                break

            page += 1

        result = {
            'category': category,
            'status': status,
            'downloaded': total_downloaded,
            'skipped': total_skipped,
            'failed': total_failed
        }

        logger.info(f"{category} 下载完成: {result}")
        return result

    def download_all(self, categories: List[str] = None,
                     status: str = "有效") -> Dict[str, Any]:
        """下载所有分类的法规"""
        if categories is None:
            categories = list(CATEGORY_MAP.keys())

        logger.info("=" * 60)
        logger.info("开始批量下载中国法律法规")
        logger.info(f"目标分类: {', '.join(categories)}")
        logger.info(f"法规状态: {status}")
        logger.info("=" * 60)

        start_time = time.time()
        results = []

        for category in categories:
            result = self.download_category(category, status)
            results.append(result)
            time.sleep(3)  # 分类之间间隔

        elapsed = time.time() - start_time

        # 汇总统计
        total_downloaded = sum(r['downloaded'] for r in results)
        total_skipped = sum(r['skipped'] for r in results)
        total_failed = sum(r['failed'] for r in results)

        summary = {
            'elapsed_time': f"{elapsed:.1f}秒",
            'total_downloaded': total_downloaded,
            'total_skipped': total_skipped,
            'total_failed': total_failed,
            'categories': results
        }

        logger.info("=" * 60)
        logger.info("批量下载完成")
        logger.info(f"总计: 下载 {total_downloaded} | 跳过 {total_skipped} | 失败 {total_failed}")
        logger.info(f"用时: {elapsed:.1f}秒")
        logger.info("=" * 60)

        return summary

    def generate_sample_data(self):
        """生成示例数据（当API不可用时使用）"""
        logger.info("生成示例法规数据...")

        sample_laws = [
            {
                'law_id': 'sample-001',
                'title': '中华人民共和国民法典',
                'category': '法律',
                'publish_date': '2020-05-28',
                'effective_date': '2021-01-01',
                'status': '有效',
                'department': '全国人民代表大会',
                'document_number': '主席令第45号',
                'content': '''中华人民共和国民法典

第一编 总则

第一章 基本规定

第一条 为了保护民事主体的合法权益，调整民事关系，维护社会和经济秩序，适应中国特色社会主义发展要求，弘扬社会主义核心价值观，根据宪法，制定本法。

第二条 民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。

第三条 民事主体的人身权利、财产权利以及其他合法权益受法律保护，任何组织或者个人不得侵犯。

第四条 民事主体在民事活动中的法律地位一律平等。

第五条 民事主体从事民事活动，应当遵循自愿原则，按照自己的意思设立、变更、终止民事法律关系。''',
                'source_url': 'https://flk.npc.gov.cn'
            },
            {
                'law_id': 'sample-002',
                'title': '中华人民共和国宪法',
                'category': '宪法',
                'publish_date': '2018-03-11',
                'effective_date': '2018-03-11',
                'status': '有效',
                'department': '全国人民代表大会',
                'document_number': '公告第1号',
                'content': '''中华人民共和国宪法

序言

中国是世界上历史最悠久的国家之一。中国各族人民共同创造了光辉灿烂的文化，具有光荣的革命传统。

第一条 中华人民共和国是工人阶级领导的、以工农联盟为基础的人民民主专政的社会主义国家。

第二条 中华人民共和国的一切权力属于人民。

第三条 中华人民共和国的国家机构实行民主集中制的原则。''',
                'source_url': 'https://flk.npc.gov.cn'
            },
            {
                'law_id': 'sample-003',
                'title': '中华人民共和国公司法',
                'category': '法律',
                'publish_date': '2023-12-29',
                'effective_date': '2024-07-01',
                'status': '有效',
                'department': '全国人民代表大会常务委员会',
                'document_number': '主席令第15号',
                'content': '''中华人民共和国公司法

（1993年12月29日第八届全国人民代表大会常务委员会第五次会议通过 根据1999年12月25日第九届全国人民代表大会常务委员会第十三次会议《关于修改〈中华人民共和国公司法〉的决定》第一次修正 根据2004年8月28日第十届全国人民代表大会常务委员会第十一次会议《关于修改〈中华人民共和国公司法〉的决定》第二次修正 2005年10月27日第十届全国人民代表大会常务委员会第十八次会议修订 根据2013年12月28日第十二届全国人民代表大会常务委员会第六次会议《关于修改〈中华人民共和国海洋环境保护法〉等七部法律的决定》第三次修正 根据2018年10月26日第十三届全国人民代表大会常务委员会第六次会议《关于修改〈中华人民共和国公司法〉的决定》第四次修正 2023年12月29日第十四届全国人民代表大会常务委员会第七次会议修订）

目  录

第一章 总  则
第二章 公司登记
第三章 有限责任公司的设立和组织机构
  第一节 设  立
  第二节 组织机构
第四章 有限责任公司的股权转让
第五章 股份有限公司的设立和组织机构
  第一节 设  立
  第二节 股 东 会
  第三节 董事会、经理
  第四节 监 事 会
  第五节 上市公司组织机构的特别规定
第六章 股份有限公司的股份发行和转让
  第一节 股份发行
  第二节 股份转让
第七章 国家出资公司组织机构的特别规定
第八章 公司董事、监事、高级管理人员的资格和义务
第九章 公司债券
第十章 公司财务、会计
第十一章 公司合并、分立、增资、减资
第十二章 公司解散和清算
第十三章 外国公司的分支机构
第十四章 法律责任
第十五章 附  则''',
                'source_url': 'https://flk.npc.gov.cn'
            },
            {
                'law_id': 'sample-004',
                'title': '最高人民法院关于适用《中华人民共和国民法典》合同编通则若干问题的解释',
                'category': '司法解释',
                'publish_date': '2023-12-04',
                'effective_date': '2023-12-05',
                'status': '有效',
                'department': '最高人民法院',
                'document_number': '法释〔2023〕13号',
                'content': '''最高人民法院关于适用《中华人民共和国民法典》合同编通则若干问题的解释

（2023年5月23日最高人民法院审判委员会第1889次会议通过，自2023年12月5日起施行）

为正确审理合同纠纷案件以及非因合同产生的债权债务关系纠纷案件，依法保护当事人的合法权益，根据《中华人民共和国民法典》、《中华人民共和国民事诉讼法》等相关法律规定，结合审判实践，制定本解释。''',
                'source_url': 'https://flk.npc.gov.cn'
            }
        ]

        inserted = 0
        for law in sample_laws:
            if self.db.save_law(law):
                inserted += 1

        logger.info(f"示例数据生成完成: {inserted} 条")
        return inserted


# ============ 启动器 ============
def interactive_download():
    """交互式下载"""
    print("\n" + "=" * 60)
    print("中国法律法规下载器 v7.0")
    print("=" * 60)
    print()

    # 初始化数据库
    db = LawDatabase()

    # 检查已有数据
    stats = db.get_stats()
    if stats['total'] > 0:
        print(f"数据库中已有 {stats['total']} 条法规")
        print(f"按分类: {stats['by_category']}")
        print()

    # 选择操作
    print("请选择操作:")
    print("1. 下载全部法规（增量更新）")
    print("2. 按分类下载")
    print("3. 生成示例数据")
    print("4. 导出为JSON")
    print("5. 查看统计")
    print("0. 退出")
    print()

    choice = input("请输入选项 (0-5): ").strip()

    if choice == '1':
        downloader = LawDownloader(db)
        downloader.download_all()

    elif choice == '2':
        print("\n可选分类:")
        for i, cat in enumerate(CATEGORY_MAP.keys(), 1):
            print(f"  {i}. {cat}")

        cat_choice = input("\n请选择分类 (输入名称): ").strip()
        if cat_choice in CATEGORY_MAP:
            downloader = LawDownloader(db)
            downloader.download_category(cat_choice)
        else:
            print("无效分类")

    elif choice == '3':
        downloader = LawDownloader(db)
        downloader.generate_sample_data()

    elif choice == '4':
        db.export_to_json()

    elif choice == '5':
        stats = db.get_stats()
        print(f"\n统计信息:")
        print(f"  总计: {stats['total']} 条")
        print(f"  按分类:")
        for cat, count in stats['by_category'].items():
            print(f"    {cat}: {count} 条")
        print(f"  按状态:")
        for status, count in stats['by_status'].items():
            print(f"    {status}: {count} 条")

    elif choice == '0':
        print("退出")
        return

    print("\n操作完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='中国法律法规下载器 - 从国家法律法规数据库下载现行有效法规'
    )
    parser.add_argument('--auto', action='store_true',
                        help='自动下载全部法规（增量更新）')
    parser.add_argument('--category', type=str,
                        help='指定下载分类（如：法律/行政法规/司法解释）')
    parser.add_argument('--status', type=str, default='有效',
                        help='指定法规状态（默认：有效）')
    parser.add_argument('--sample', action='store_true',
                        help='生成示例数据')
    parser.add_argument('--export', action='store_true',
                        help='导出为JSON')
    parser.add_argument('--stats', action='store_true',
                        help='查看统计')
    parser.add_argument('--db', type=str, default='./download_data/legal_laws.db',
                        help='数据库路径')

    args = parser.parse_args()

    # 初始化数据库
    db = LawDatabase(args.db)

    if args.auto:
        print("自动下载全部法规...")
        downloader = LawDownloader(db)
        downloader.download_all(status=args.status)

    elif args.category:
        print(f"下载分类: {args.category}")
        downloader = LawDownloader(db)
        downloader.download_category(args.category, status=args.status)

    elif args.sample:
        print("生成示例数据...")
        downloader = LawDownloader(db)
        downloader.generate_sample_data()

    elif args.export:
        print("导出为JSON...")
        db.export_to_json()

    elif args.stats:
        stats = db.get_stats()
        print(f"总计: {stats['total']} 条")
        for cat, count in stats['by_category'].items():
            print(f"  {cat}: {count} 条")

    else:
        interactive_download()


if __name__ == '__main__':
    main()
