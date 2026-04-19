#!/bin/bash

# 中国法律法规WPS文档下载器启动器
# 从 flk.npc.gov.cn 下载法规的WPS版本(.doc/.docx)

cd "$(dirname "$0")"

clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        中国法律法规WPS文档下载器 v1.0                      ║"
echo "║        数据源: flk.npc.gov.cn                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    read -p "按回车键退出..."
    exit 1
fi

# 检查Playwright
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "⚠️  需要安装 Playwright 浏览器自动化工具"
    echo ""
    echo "正在安装..."
    pip3 install playwright
    playwright install chromium
    echo ""
fi

echo "✅ 环境检查完成"
echo ""

# 创建下载目录
mkdir -p download_data/wps_docs
echo "📁 下载目录: $(pwd)/download_data/wps_docs"
echo ""

# 显示选项
echo "请选择操作模式:"
echo ""
echo "1️⃣  从URL下载 - 输入法规详情页链接"
echo "2️⃣  搜索下载 - 按关键词搜索并下载"
echo "3️⃣  查看统计 - 显示已下载文件统计"
echo "0️⃣  退出"
echo ""

read -p "请输入选择 (0-3): " choice

case $choice in
    1)
        echo ""
        read -p "请输入法规详情页URL (例如 https://flk.npc.gov.cn/detail?id=...): " url
        if [ -n "$$url" ]; then
            echo "🚀 开始下载..."
            python3 law_wps_downloader.py --url "$url"
        fi
        ;;
    2)
        echo ""
        read -p "请输入搜索关键词 (可选): " keyword
        read -p "请输入分类 (法律/行政法规/司法解释等): " category
        read -p "最大下载数量 (默认10): " max_count
        max_count=${max_count:-10}
        echo "🚀 搜索下载..."
        python3 law_wps_downloader.py --search "$keyword" --category "$category" --max "$max_count"
        ;;
    3)
        echo "📊 下载统计..."
        python3 law_wps_downloader.py --stats
        ;;
    0)
        echo "退出"
        exit 0
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
echo "📁 WPS文档已保存到 download_data/wps_docs/ 目录"
echo ""
echo "目录结构:"
echo "  download_data/wps_docs/"
echo "  ├── 宪法/"
echo "  ├── 法律/"
echo "  ├── 行政法规/"
echo "  ├── 司法解释/"
echo "  └── ..."
echo ""

read -p "按回车键关闭窗口..."
