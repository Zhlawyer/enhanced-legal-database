#!/bin/bash

# 中国法律法规下载器启动器 v7.0
# 自动下载国家法律法规数据库 (flk.npc.gov.cn) 的现行有效法规

cd "$(dirname "$0")"

export TERM=xterm-256color
export LANG=zh_CN.UTF-8

clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        中国法律法规下载器 v7.0                            ║"
echo "║        数据源: flk.npc.gov.cn (国家法律法规数据库)        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    read -p "按回车键退出..."
    exit 1
fi

echo "✅ Python3 已安装"
echo ""

# 检查依赖
echo "📦 检查依赖..."
python3 -c "import sqlite3" 2>/dev/null || { echo "❌ 缺少 sqlite3"; exit 1; }
python3 -c "import requests" 2>/dev/null || {
    echo "正在安装 requests..."
    pip3 install requests
}
echo "✅ 依赖检查完成"
echo ""

# 创建数据目录
mkdir -p download_data
echo "📁 数据目录: $(pwd)/download_data"
echo ""

# 显示选项
echo "请选择操作模式:"
echo ""
echo "1️⃣  交互式下载 (推荐) - 选择分类和状态"
echo "2️⃣  自动下载全部 - 下载所有现行有效法规"
echo "3️⃣  仅下载法律类 - 全国人大及其常委会制定的法律"
echo "4️⃣  仅下载司法解释 - 最高人民法院/检察院解释"
echo "5️⃣  仅下载行政法规 - 国务院制定的行政法规"
echo "6️⃣  生成示例数据 - 用于测试系统"
echo "7️⃣  导出JSON - 将数据库导出为JSON文件"
echo "8️⃣  查看统计 - 显示已下载法规统计"
echo ""

read -p "请输入选择 (1-8): " choice

case $choice in
    1)
        echo "🚀 启动交互式下载..."
        python3 law_downloader.py
        ;;
    2)
        echo "🚀 自动下载全部现行有效法规..."
        echo "⚠️  注意: 这可能需要较长时间"
        echo ""
        read -p "按回车键开始下载..."
        python3 law_downloader.py --auto --status 有效
        ;;
    3)
        echo "🚀 下载法律类法规..."
        python3 law_downloader.py --category 法律 --status 有效
        ;;
    4)
        echo "🚀 下载司法解释..."
        python3 law_downloader.py --category 司法解释 --status 有效
        ;;
    5)
        echo "🚀 下载行政法规..."
        python3 law_downloader.py --category 行政法规 --status 有效
        ;;
    6)
        echo "🚀 生成示例数据..."
        python3 law_downloader.py --sample
        ;;
    7)
        echo "📤 导出为JSON..."
        python3 law_downloader.py --export
        ;;
    8)
        echo "📊 查看统计..."
        python3 law_downloader.py --stats
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 操作完成!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 数据已保存到 download_data/ 目录"
echo ""
echo "后续操作:"
echo "  • 查看统计: python3 law_downloader.py --stats"
echo "  • 导出JSON: python3 law_downloader.py --export"
echo "  • 增量更新: python3 law_downloader.py --auto"
echo ""

read -p "按回车键关闭窗口..."
