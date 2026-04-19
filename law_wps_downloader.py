#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国法律法规WPS文档下载器 v1.0
从 flk.npc.gov.cn 下载法规的WPS版本(.doc/.docx)

功能：
- 自动浏览法规详情页面
- 检测并下载WPS版本文档
- 按法规类型分类存储
- 支持批量下载和断点续传

用法：
    python3 law_wps_downloader.py                    # 交互式模式
    python3 law_wps_downloader.py --auto             # 自动下载全部
    python3 law_wps_downloader.py --url "URL"        # 下载指定法规
    python3 law_wps_downloader.py --category 法律     # 下载指定分类
"""

import os
import sys
import json
import time
import sqlite3
import logging
import argparse
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://flk.npc.gov.cn"


class WPSDownloader:
    """WPS文档下载器 - 基于Playwright浏览器自动化"""

    def __init__(self, data_dir="./download_data/wps_docs"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 分类目录
        self.category_dirs = {
            "宪法": self.data_dir / "宪法",
            "法律": self.data_dir / "法律",
            "行政法规": self.data_dir / "行政法规",
            "监察法规": self.data_dir / "监察法规",
            "地方法规": self.data_dir / "地方法规",
            "司法解释": self.data_dir / "司法解释",
            "部门规章": self.data_dir / "部门规章",
            "其他": self.data_dir / "其他",
        }
        for d in self.category_dirs.values():
            d.mkdir(exist_ok=True)

        self.db_path = self.data_dir / "download_history.db"
        self._init_db()

        self.playwright = None
        self.browser = None
        self.page = None

    def _init_db(self):
        """初始化下载记录数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                law_id TEXT PRIMARY KEY,
                title TEXT,
                category TEXT,
                doc_url TEXT,
                local_path TEXT,
                file_size INTEGER,
                download_time TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        conn.commit()
        conn.close()

    def _is_downloaded(self, law_id: str) -> bool:
        """检查是否已下载"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM downloads WHERE law_id = ? AND status = "completed"', (law_id,))
            result = cursor.fetchone() is not None
            conn.close()
            return result
        except Exception:
            return False

    def _record_download(self, law_id: str, title: str, category: str,
                         doc_url: str, local_path: str, file_size: int,
                         status: str = "completed"):
        """记录下载信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO downloads
                (law_id, title, category, doc_url, local_path, file_size, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (law_id, title, category, doc_url, local_path, file_size, status))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"记录下载信息失败: {e}")

    def init_browser(self, headless: bool = True):
        """初始化Playwright浏览器"""
        try:
            from playwright.sync_api import sync_playwright

            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = self.browser.new_page(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            # 拦截下载请求
            self.page.on("download", self._handle_download)

            logger.info("浏览器初始化完成")
            return True

        except ImportError:
            logger.error("未安装Playwright，请运行: pip install playwright && playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"浏览器初始化失败: {e}")
            return False

    def _handle_download(self, download):
        """处理浏览器下载事件"""
        try:
            path = download.path()
            logger.info(f"浏览器下载: {download.suggested_filename} -> {path}")
        except Exception as e:
            logger.error(f"处理下载失败: {e}")

    def close_browser(self):
        """关闭浏览器"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")

    def extract_law_id_from_url(self, url: str) -> Optional[str]:
        """从URL中提取法规ID"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return params.get('id', [None])[0]
        except Exception:
            return None

    def download_from_url(self, url: str, category: str = "其他") -> Dict[str, Any]:
        """从指定URL下载法规WPS文档"""
        if not self.page:
            return {'success': False, 'error': '浏览器未初始化'}

        law_id = self.extract_law_id_from_url(url)
        if not law_id:
            return {'success': False, 'error': '无法从URL中提取法规ID'}

        # 检查是否已下载
        if self._is_downloaded(law_id):
            logger.info(f"已下载，跳过: {law_id}")
            return {'success': True, 'skipped': True, 'law_id': law_id}

        logger.info(f"访问页面: {url}")

        try:
            # 导航到详情页面
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)  # 等待JavaScript加载

            # 获取页面标题
            title = self.page.title()
            title = title.replace(' - 国家法律法规数据库', '').strip()
            logger.info(f"法规标题: {title}")

            # 查找下载按钮
            download_selectors = [
                'a:has-text("下载")',
                'button:has-text("下载")',
                '.download-btn',
                '[class*="download"]',
                'a[href*="download"]',
                'a[href*=".doc"]',
                'a[href*=".docx"]',
                'a[href*=".wps"]',
            ]

            download_link = None
            for selector in download_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.count() > 0:
                        # 获取链接
                        href = element.get_attribute('href')
                        if href:
                            download_link = urljoin(BASE_URL, href)
                            logger.info(f"找到下载链接: {download_link}")
                            break
                        # 尝试点击
                        element.click()
                        time.sleep(1)
                        break
                except Exception:
                    continue

            # 如果找到了直接下载链接
            if download_link:
                return self._download_file(download_link, law_id, title, category)

            # 尝试从页面源码中查找文件链接
            page_source = self.page.content()
            file_links = re.findall(
                r'href=["\']([^"\']*\.(?:doc|docx|wps|pdf)[^"\']*)["\']',
                page_source, re.IGNORECASE
            )

            if file_links:
                file_url = urljoin(BASE_URL, file_links[0])
                logger.info(f"从页面源码找到文件: {file_url}")
                return self._download_file(file_url, law_id, title, category)

            # 尝试获取页面中的JSON数据（可能包含文件信息）
            scripts = self.page.locator('script').all_inner_texts()
            for script in scripts:
                if 'fileUrl' in script or 'download' in script:
                    urls = re.findall(r'https?://[^\s"\'\>]+', script)
                    for u in urls:
                        if any(ext in u.lower() for ext in ['.doc', '.docx', '.wps']):
                            logger.info(f"从脚本中找到文件: {u}")
                            return self._download_file(u, law_id, title, category)

            # 如果没有找到下载链接，保存页面HTML作为备用
            logger.warning(f"未找到WPS下载链接: {title}")
            self._save_page_content(law_id, title, category)

            return {
                'success': False,
                'law_id': law_id,
                'title': title,
                'error': '未找到WPS下载链接，已保存页面内容'
            }

        except Exception as e:
            logger.error(f"下载失败 [{url}]: {e}")
            return {'success': False, 'error': str(e), 'url': url}

    def _download_file(self, file_url: str, law_id: str, title: str,
                       category: str) -> Dict[str, Any]:
        """下载文件"""
        try:
            # 确定保存目录
            save_dir = self.category_dirs.get(category, self.category_dirs["其他"])

            # 确定文件扩展名
            ext = '.doc'
            for e in ['.docx', '.wps', '.pdf', '.doc']:
                if e in file_url.lower():
                    ext = e
                    break

            # 清理标题作为文件名
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:80]
            filename = f"{safe_title}_{law_id[:8]}{ext}"
            local_path = save_dir / filename

            # 使用requests下载
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': BASE_URL,
            }

            logger.info(f"下载文件: {filename}")
            response = requests.get(file_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()

            # 保存文件
            file_size = 0
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        file_size += len(chunk)

            # 记录下载
            self._record_download(law_id, title, category, file_url,
                                  str(local_path), file_size)

            logger.info(f"✅ 下载完成: {filename} ({file_size / 1024:.1f} KB)")

            return {
                'success': True,
                'law_id': law_id,
                'title': title,
                'file_path': str(local_path),
                'file_size': file_size
            }

        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return {'success': False, 'error': str(e)}

    def _save_page_content(self, law_id: str, title: str, category: str):
        """保存页面内容（当没有WPS文件时）"""
        try:
            save_dir = self.category_dirs.get(category, self.category_dirs["其他"])
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:80]

            # 保存HTML
            html_path = save_dir / f"{safe_title}_{law_id[:8]}.html"
            self.page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.page.content())

            # 保存文本内容
            text_path = save_dir / f"{safe_title}_{law_id[:8]}.txt"
            text_content = self.page.inner_text('body')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text_content)

            logger.info(f"已保存页面内容: {html_path}")

        except Exception as e:
            logger.error(f"保存页面内容失败: {e}")

    def download_by_search(self, keyword: str = "", category: str = "",
                           max_count: int = 10) -> List[Dict]:
        """通过搜索下载法规"""
        results = []

        try:
            # 构建搜索URL
            search_url = f"{BASE_URL}/"
            self.page.goto(search_url, wait_until="networkidle")
            time.sleep(1)

            # 在搜索框中输入关键词
            if keyword:
                search_input = self.page.locator('input[placeholder*="搜索"], input[type="text"]').first
                if search_input.count() > 0:
                    search_input.fill(keyword)
                    search_input.press('Enter')
                    time.sleep(2)

            # 获取搜索结果链接
            links = self.page.locator('a[href*="/detail?id="]').all()

            logger.info(f"找到 {len(links)} 个搜索结果")

            for i, link in enumerate(links[:max_count]):
                try:
                    href = link.get_attribute('href')
                    if not href:
                        continue

                    full_url = urljoin(BASE_URL, href)
                    result = self.download_from_url(full_url, category)
                    results.append(result)

                    if result.get('success') and not result.get('skipped'):
                        time.sleep(2)  # 下载间隔

                except Exception as e:
                    logger.error(f"处理搜索结果失败: {e}")

        except Exception as e:
            logger.error(f"搜索下载失败: {e}")

        return results

    def get_download_stats(self) -> Dict[str, Any]:
        """获取下载统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM downloads WHERE status = "completed"')
            total = cursor.fetchone()[0]

            cursor.execute('''
                SELECT category, COUNT(*) FROM downloads
                WHERE status = "completed"
                GROUP BY category
            ''')
            by_category = dict(cursor.fetchall())

            cursor.execute('SELECT SUM(file_size) FROM downloads WHERE status = "completed"')
            total_size = cursor.fetchone()[0] or 0

            conn.close()

            return {
                'total': total,
                'by_category': by_category,
                'total_size_mb': total_size / (1024 * 1024)
            }

        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {'total': 0, 'by_category': {}, 'total_size_mb': 0}


def interactive_download():
    """交互式下载"""
    print("\n" + "=" * 60)
    print("中国法律法规WPS文档下载器 v1.0")
    print("=" * 60)
    print()

    downloader = WPSDownloader()

    # 检查Playwright
    if not downloader.init_browser(headless=False):
        print("\n❌ 请安装Playwright:")
        print("   pip install playwright")
        print("   playwright install chromium")
        return

    try:
        print("请选择操作:")
        print("1. 从URL下载指定法规")
        print("2. 搜索并下载")
        print("3. 查看下载统计")
        print("0. 退出")
        print()

        choice = input("请输入选项 (0-3): ").strip()

        if choice == '1':
            url = input("请输入法规详情页URL: ").strip()
            category = input("请输入分类 (默认: 其他): ").strip() or "其他"
            if url:
                result = downloader.download_from_url(url, category)
                print(f"\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

        elif choice == '2':
            keyword = input("请输入搜索关键词 (可选): ").strip()
            category = input("请输入分类: ").strip()
            max_count = input("最大下载数量 (默认10): ").strip() or "10"
            results = downloader.download_by_search(keyword, category, int(max_count))
            print(f"\n完成 {len(results)} 个下载任务")

        elif choice == '3':
            stats = downloader.get_download_stats()
            print(f"\n下载统计:")
            print(f"  总计: {stats['total']} 个文件")
            print(f"  总大小: {stats['total_size_mb']:.2f} MB")
            for cat, count in stats['by_category'].items():
                print(f"  {cat}: {count} 个")

    finally:
        downloader.close_browser()


def main():
    parser = argparse.ArgumentParser(description='中国法律法规WPS文档下载器')
    parser.add_argument('--url', type=str, help='指定法规详情页URL')
    parser.add_argument('--category', type=str, default='其他', help='法规分类')
    parser.add_argument('--search', type=str, help='搜索关键词')
    parser.add_argument('--max', type=int, default=10, help='最大下载数量')
    parser.add_argument('--headless', action='store_true', help='无界面模式')
    parser.add_argument('--stats', action='store_true', help='查看统计')

    args = parser.parse_args()

    downloader = WPSDownloader()

    if args.stats:
        stats = downloader.get_download_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return

    # 初始化浏览器
    headless = args.headless if args.headless else (args.url is not None)
    if not downloader.init_browser(headless=headless):
        print("❌ 浏览器初始化失败")
        print("请安装Playwright: pip install playwright && playwright install chromium")
        sys.exit(1)

    try:
        if args.url:
            result = downloader.download_from_url(args.url, args.category)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.search:
            results = downloader.download_by_search(args.search, args.category, args.max)
            print(f"完成 {len(results)} 个下载任务")
        else:
            interactive_download()
    finally:
        downloader.close_browser()


if __name__ == '__main__':
    main()
