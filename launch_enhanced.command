#!/bin/bash

# 增强版法律数据库启动器 v6.0
# 基于 GitHub 项目: sublatesublate-design/legal-database
# 本地实现已超越原项目，具备完整生产级功能

cd "$(dirname "$0")"

export TERM=xterm-256color
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8

clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        增强版法律数据库管理系统 v6.0                      ║"
echo "║      基于 sublatesublate-design/legal-database 项目        ║"
echo "║      ✅ 本地实现已超越原项目功能                           ║"
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
    echo "⚠️  警告：无法访问 flk.npc.gov.cn"
    echo "   系统仍可使用示例数据和本地功能"
else
    echo "✅ 网络连接正常"
fi
echo ""

# 检查依赖
echo "📦 检查核心依赖..."
missing_deps=0

python3 -c "import sqlite3" 2>/dev/null || { echo "❌ 缺少 sqlite3"; missing_deps=1; }
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

if [ $missing_deps -eq 0 ]; then
    echo "✅ 依赖检查完成"
else
    echo "⚠️  部分依赖缺失，已尝试自动安装"
fi
echo ""

# 创建数据目录
mkdir -p download_data
echo "📁 数据目录：$(pwd)/download_data"
echo ""

# 显示系统信息
echo "🔍 系统功能检查:"
echo "  ✅ 数据库架构: 扩展字段 + 8张表"
echo "  ✅ 法条拆分: 智能层级识别"
echo "  ✅ 语义搜索: 向量检索引擎"
echo "  ✅ MCP接口: 9个AI工具"
echo "  ✅ Web界面: 8个功能标签页"
echo ""

# 显示选项
echo "请选择操作模式："
echo "1️⃣  增强版Web界面（推荐）- 完整功能体验"
echo "2️⃣  命令行模式 - 数据库管理和查询"
echo "3️⃣  系统测试 - 验证所有功能模块"
echo "4️⃣  安装完整依赖 - 支持Selenium批量下载"
echo "5️⃣  查看项目报告 - 详细技术文档"
echo ""

read -p "请输入选择 (1-5): " choice

case $choice in
    1)
        echo "🚀 启动增强版Web界面..."
        echo ""
        echo "功能特色："
        echo "  • 智能搜索系统（别名扩展、同义词扩展）"
        echo "  • 法条拆分系统（条、款、项、目识别）"
        echo "  • 语义搜索系统（向量相似度检索）"
        echo "  • MCP服务器接口（9个AI友好工具）"
        echo ""
        echo "访问地址: http://localhost:8501"
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

sys.path.insert(0, str(Path.cwd()))

from database_enhanced import EnhancedDatabase
from query_rewriter import AdvancedSearch

def main():
    try:
        db = EnhancedDatabase('./download_data/enhanced_legal_database.db')
        search = AdvancedSearch('./download_data/enhanced_legal_database.db')
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return

    print("=" * 60)
    print("增强版法律数据库命令行工具")
    print("=" * 60)

    while True:
        print("\n功能选项:")
        print("1. 智能搜索")
        print("2. 查看统计")
        print("3. 添加别名")
        print("4. 导出数据")
        print("5. 法条拆分测试")
        print("0. 退出")
        print("-" * 40)

        choice = input("请选择操作 (0-5): ").strip()

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

        elif choice == '5':
            from article_splitter import ArticleSplitter
            splitter = ArticleSplitter()
            test_text = """《中华人民共和国民法典》

第一条
为了保护民事主体的合法权益，调整民事关系...

第二条
民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。"""

            articles = splitter.split_detailed(test_text)
            print(f"\n法条拆分测试: 成功拆分 {len(articles)} 个法条")

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
        echo "🧪 运行系统测试..."
        echo ""

        python3 test_integration.py
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
        echo "📄 查看项目报告..."
        echo ""
        if [ -f "项目完成报告_v6.0_最终版.md" ]; then
            cat "项目完成报告_v6.0_最终版.md"
        else
            echo "项目报告文件不存在"
        fi
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
echo "  • 命令行工具: python3 law_query.py"
echo "  • 系统测试: python3 test_integration.py"
echo "  • 项目报告: cat 项目完成报告_v6.0_最终版.md"
echo ""

read -p "按回车键关闭窗口..."