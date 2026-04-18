#!/usr/bin/env python3
"""
法律法规数据库查询工具
提供友好的命令行界面查询法律法规数据库
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime


class LawDatabase:
    """法律法规数据库查询类"""

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            print(f"❌ 数据库文件不存在: {db_path}")
            print("请先运行法律法规收集脚本")
            sys.exit(1)

    def search_by_keyword(self, keyword, limit=50):
        """按关键词搜索"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT title, category, publish_date, department, source_url
            FROM laws
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY publish_date DESC
            LIMIT ?
        ''', (f'%{keyword}%', f'%{keyword}%', limit))

        results = cursor.fetchall()
        conn.close()

        return results

    def get_by_type(self, law_type, limit=50):
        """按类型查询"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT title, publish_date, department, source_url
            FROM laws
            WHERE category = ?
            ORDER BY publish_date DESC
            LIMIT ?
        ''', (law_type, limit))

        results = cursor.fetchall()
        conn.close()

        return results

    def get_recent(self, days=30, limit=50):
        """获取最近发布的法规"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT title, category, publish_date, department, source_url
            FROM laws
            WHERE publish_date >= date('now', ?)
            ORDER BY publish_date DESC
            LIMIT ?
        ''', (f'-{days} days', limit))

        results = cursor.fetchall()
        conn.close()

        return results

    def get_statistics(self):
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 总数
        cursor.execute('SELECT COUNT(*) FROM laws')
        total = cursor.fetchone()[0]

        # 按类型统计
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM laws
            GROUP BY category
            ORDER BY count DESC
        ''')
        type_stats = cursor.fetchall()

        # 最近发布
        cursor.execute('''
            SELECT COUNT(*) FROM laws
            WHERE publish_date >= date('now', '-30 days')
        ''')
        recent_count = cursor.fetchone()[0]

        conn.close()

        return {
            'total': total,
            'type_stats': type_stats,
            'recent_30days': recent_count
        }

    def export_to_text(self, output_file):
        """导出为文本文件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT title, category, publish_date, department, source_url
            FROM laws
            ORDER BY category, publish_date DESC
        ''')

        results = cursor.fetchall()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("中国法律法规数据库导出\n")
            f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"法规总数: {len(results)}\n")
            f.write("=" * 80 + "\n\n")

            current_type = None
            for title, category, publish_date, department, url in results:
                if category != current_type:
                    f.write(f"\n{'='*40}\n")
                    f.write(f"{category}\n")
                    f.write(f"{'='*40}\n\n")
                    current_type = category

                f.write(f"标题: {title}\n")
                f.write(f"发布日期: {publish_date}\n")
                f.write(f"发布部门: {department}\n")
                f.write(f"链接: {url}\n")
                f.write("-" * 40 + "\n")

        conn.close()
        print(f"已导出到: {output_file}")


def main():
    """主函数"""
    db_path = "./download_data/legal_database.db"
    db = LawDatabase(db_path)

    print("=" * 60)
    print("法律法规数据库查询工具")
    print("=" * 60)

    while True:
        print("\n功能选项:")
        print("1. 关键词搜索")
        print("2. 按类型查询")
        print("3. 最近发布法规")
        print("4. 统计信息")
        print("5. 导出为文本")
        print("0. 退出")
        print("-" * 40)

        choice = input("请选择操作 (0-5): ").strip()

        if choice == '1':
            keyword = input("请输入关键词: ").strip()
            if keyword:
                results = db.search_by_keyword(keyword)
                print(f"\n找到 {len(results)} 个结果:")
                for i, (title, law_type, publish_date, department, url) in enumerate(results, 1):
                    print(f"\n{i}. [{law_type}] {title}")
                    print(f"   发布日期: {publish_date}")
                    print(f"   发布部门: {department}")
                    print(f"   链接: {url}")

        elif choice == '2':
            law_type = input("请输入法规类型 (法律/行政法规/司法解释/地方法规/监察法规/部门规章): ").strip()
            if law_type:
                results = db.get_by_type(law_type)
                print(f"\n{law_type} 共 {len(results)} 条:")
                for i, (title, publish_date, department, url) in enumerate(results, 1):
                    print(f"\n{i}. {title}")
                    print(f"   发布日期: {publish_date}")
                    print(f"   发布部门: {department}")

        elif choice == '3':
            days = input("最近几天 (默认30): ").strip()
            days = int(days) if days.isdigit() else 30
            results = db.get_recent(days)
            print(f"\n最近{days}天发布的法规共 {len(results)} 条:")
            for i, (title, law_type, publish_date, department, url) in enumerate(results, 1):
                print(f"\n{i}. [{law_type}] {title}")
                print(f"   发布日期: {publish_date}")
                print(f"   发布部门: {department}")

        elif choice == '4':
            stats = db.get_statistics()
            print(f"\n统计信息:")
            print(f"总法规数: {stats['total']}")
            print(f"最近30天新增: {stats['recent_30days']}")
            print("\n按类型统计:")
            for law_type, count in stats['type_stats']:
                print(f"  {law_type}: {count} 条")

        elif choice == '5':
            output_file = input("请输入输出文件名 (默认: laws_export.txt): ").strip()
            if not output_file:
                output_file = "./download_data/laws_export.txt"
            db.export_to_text(output_file)

        elif choice == '0':
            print("感谢使用，再见！")
            break

        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    main()