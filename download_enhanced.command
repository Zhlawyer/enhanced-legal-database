#!/bin/bash

# 增强版法律数据库启动器 v6.0
# 基于 GitHub 项目: sublatesublate-design/legal-database

cd "$(dirname "$0")"

export TERM=xterm-256color
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8

clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        增强版法律数据库管理系统 v6.0                      ║"
echo "║      基于 sublatesublate-design/legal-database 项目        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python3"
    read -p "按回车键退出..."
    exit 1
fi

# 检查网络连接
echo "📡 检查网络连接..."
if ! curl -s --head https://flk.npc.gov.cn > /dev/null; then
    echo "❌ 错误：无法访问 flk.npc.gov.cn"
    echo "   请检查网络连接"
    read -p "按回车键退出..."
    exit 1
fi
echo "✅ 网络连接正常"
echo ""

# 检查依赖
echo "📦 检查依赖..."
python3 -c "import sqlite3" 2>/dev/null || {
    echo "❌ 错误：未找到 sqlite3"
    exit 1
}

python3 -c "import streamlit" 2>/dev/null || {
    echo "正在安装 Streamlit..."
    pip3 install streamlit --break-system-packages 2>/dev/null || pip3 install streamlit
}

python3 -c "import docx" 2>/dev/null || {
    echo "正在安装 python-docx..."
    pip3 install python-docx --break-system-packages 2>/dev/null || pip3 install python-docx
}

python3 -c "import requests, bs4" 2>/dev/null || {
    echo "正在安装网络请求依赖..."
    pip3 install requests beautifulsoup4 --break-system-packages 2>/dev/null || pip3 install requests beautifulsoup4
}

echo "✅ 依赖检查完成"
echo ""

# 创建数据目录
mkdir -p download_data
echo "📁 数据目录：$(pwd)/download_data"
echo ""

# 显示选项
echo "请选择操作模式："
echo "1️⃣  增强版Web界面（推荐）- 提供智能搜索、增量更新等功能"
echo "2️⃣  命令行模式 - 数据库管理和查询"
echo "3️⃣  数据迁移 - 迁移到增强版数据库"
echo "4️⃣  安装完整依赖 - 支持Selenium批量下载"
echo "5️⃣  系统测试 - 验证系统完整性"
echo ""

read -p "请输入选择 (1-5): " choice

case $choice in
    1)
        echo "🚀 启动增强版Web界面..."
        echo ""
        echo "提示：Web界面将在浏览器中打开"
        echo "      如果无法自动打开，请手动访问: http://localhost:8501"
        echo ""
        echo "功能特色："
        echo "  • 智能搜索系统（支持别名扩展、同义词扩展）"
        echo "  • 增量更新机制"
        echo "  • 数据同步管理"
        echo "  • 别名管理系统"
        echo "  • 统计分析功能"
        echo ""
        read -p "按回车键继续..."

        python3 app_enhanced.py
        ;;
    2)
        echo "📥 运行命令行模式..."
        echo ""

        python3 << 'PYEOF'
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path.cwd()))

from database_enhanced import EnhancedDatabase
from query_rewriter import AdvancedSearch

def main():
    db = EnhancedDatabase('./download_data/enhanced_legal_database.db')
    search = AdvancedSearch('./download_data/enhanced_legal_database.db')

    print("=" * 60)
    print("增强版法律数据库命令行工具")
    print("=" * 60)

    while True:
        print("\n功能选项:")
        print("1. 智能搜索")
        print("2. 查看统计")
        print("3. 添加别名")
        print("4. 导出数据")
        print("0. 退出")
        print("-" * 40)

        choice = input("请选择操作 (0-4): ").strip()

        if choice == '1':
            query = input("请输入搜索关键词: ").strip()
            if query:
                result = search.search(query, {'limit': 20})
                if result['success']:
                    print(f"\n找到 {result['count']} 个结果:")
                    for i, item in enumerate(result['results'][:10], 1):
                        print(f"{i}. [{item['category']}] {item['title']}")
                else:
                    print(f"搜索失败: {result['error']}")

        elif choice == '2':
            stats = db.get_statistics()
            print(f"\n数据库统计:")
            print(f"  总法规数: {stats['total']}")
            print(f"  最近7天更新: {stats['recent_7days']}")
            print("  分类统计:")
            for category, count in stats['category_stats']:
                print(f"    {category}: {count} 条")

        elif choice == '3':
            alias = input("请输入别名: ").strip()
            title = input("请输入法律标题: ").strip()
            if alias and title:
                success = db.add_alias(alias, title)
                if success:
                    print(f"✅ 成功添加别名: {alias} → {title}")
                else:
                    print("❌ 添加别名失败")

        elif choice == '4':
            export_file = db.export_to_json()
            print(f"✅ 数据已导出到: {export_file}")

        elif choice == '0':
            print("感谢使用，再见！")
            break

        else:
            print("无效选择，请重新输入")

if __name__ == "__main__":
    main()
PYEOF
        ;;
    3)
        echo "🔄 数据迁移到增强版数据库..."
        echo ""

        python3 << 'PYEOF'
import sqlite3
from pathlib import Path
from database_enhanced import EnhancedDatabase

def migrate_data():
    old_db = Path("./download_data/legal_database.db")
    new_db = Path("./download_data/enhanced_legal_database.db")

    if not old_db.exists():
        print("❌ 未找到旧版数据库")
        return

    print(f"迁移数据库: {old_db} → {new_db}")

    # 创建增强版数据库
    enhanced_db = EnhancedDatabase(str(new_db))

    # 迁移数据
    conn = sqlite3.connect(old_db)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT title, category, publish_date, status,
               content, department, source_url
        FROM laws
    ''')

    migrated = 0
    for row in cursor.fetchall():
        try:
            enhanced_db.add_law(
                title=row[0],
                category=row[1],
                publish_date=row[2],
                status=row[3],
                content=row[4],
                department=row[5],
                source_url=row[6]
            )
            migrated += 1
        except sqlite3.IntegrityError:
            pass  # 已存在

    conn.close()

    print(f"✅ 迁移完成: {migrated} 条法规")

    # 添加示例别名
    enhanced_db.add_alias('民法典', '中华人民共和国民法典')
    enhanced_db.add_alias('宪法', '中华人民共和国宪法')
    print("✅ 已添加示例别名")

if __name__ == "__main__":
    migrate_data()
PYEOF
        ;;
    4)
        echo "📦 安装完整依赖..."
        echo ""

        echo "安装Selenium和webdriver-manager..."
        pip3 install selenium webdriver-manager --break-system-packages 2>/dev/null || pip3 install selenium webdriver-manager

        echo ""
        echo "安装Playwright..."
        pip3 install playwright --break-system-packages 2>/dev/null || pip3 install playwright
        playwright install chromium

        echo ""
        echo "安装其他依赖..."
        pip3 install aiohttp jieba numpy scikit-learn --break-system-packages 2>/dev/null || pip3 install aiohttp jieba numpy scikit-learn

        echo ""
        echo "✅ 完整依赖安装完成"
        echo ""
        echo "现在可以使用:"
        echo "  • Selenium批量下载"
        echo "  • 语义搜索功能"
        echo "  • 异步处理"
        ;;
    5)
        echo "🧪 运行系统测试..."
        echo ""

        python3 << 'PYEOF'
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

def test_system():
    print("增强版法律数据库系统测试")
    print("=" * 50)

    # 测试数据库
    try:
        from database_enhanced import EnhancedDatabase
        db = EnhancedDatabase('./download_data/enhanced_legal_database.db')
        stats = db.get_statistics()
        print(f"✅ 数据库测试通过: {stats['total']} 条法规")
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return

    # 测试查询重写
    try:
        from query_rewriter import QueryRewriter
        rewriter = QueryRewriter('./download_data/enhanced_legal_database.db')
        expanded = rewriter.expand_query('民法典')
        print(f"✅ 查询重写测试通过: {expanded}")
    except Exception as e:
        print(f"❌ 查询重写测试失败: {e}")

    # 测试MCP服务
    try:
        from mcp_server_enhanced import LegalMCPService
        service = LegalMCPService('./download_data/enhanced_legal_database.db')
        result = service.get_statistics()
        if result['success']:
            print(f"✅ MCP服务测试通过: {result['total_laws']} 条法规")
        else:
            print(f"❌ MCP服务测试失败: {result.get('error', '未知错误')}")
    except Exception as e:
        print(f"❌ MCP服务测试失败: {e}")

    print("\n🎉 系统测试完成!")

if __name__ == "__main__":
    test_system()
PYEOF
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 所有操作已完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 数据已保存到 download_data/ 目录"
echo ""
echo "后续操作："
echo "  • 增强版Web界面: python3 app_enhanced.py"
echo "  • 命令行工具: python3 database_enhanced.py"
echo "  • MCP服务器: python3 mcp_server_enhanced.py"
echo "  • 系统测试: 选择菜单中的系统测试选项"
echo ""

read -p "按回车键关闭窗口..."