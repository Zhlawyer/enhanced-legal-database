#!/bin/bash

# GitHub上传助手脚本
# 使用方法: ./upload_to_github.sh

echo "🚀 开始上传到 GitHub..."
echo ""

# 检查是否在正确的目录
if [ ! -f "launch_enhanced.command" ]; then
    echo "❌ 错误：请在项目目录中运行此脚本"
    exit 1
fi

# 检查Git状态
echo "📊 检查Git状态..."
git status
echo ""

# 配置远程仓库（如果还没有配置）
if ! git remote | grep -q "origin"; then
    echo "配置远程仓库..."
    git remote add origin https://github.com/Zhlawyer/enhanced-legal-database.git
    echo "✅ 远程仓库已配置"
else
    echo "✅ 远程仓库已存在"
fi
echo ""

# 显示远程仓库信息
echo "远程仓库信息:"
git remote -v
echo ""

# 推送代码
echo "📤 推送代码到 GitHub..."
echo ""
echo "如果提示输入用户名和密码:"
echo "  用户名: Zhlawyer"
echo "  密码: 使用个人访问令牌 (以 ghp_ 开头)"
echo ""
echo "如需创建令牌: https://github.com/settings/tokens"
echo "令牌权限: 勾选 'repo'"
echo ""

read -p "按回车键继续推送..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 上传成功！"
    echo "访问地址: https://github.com/Zhlawyer/enhanced-legal-database"
else
    echo ""
    echo "❌ 上传失败，请检查认证信息"
    echo "如需帮助，请参考: https://docs.github.com/authentication"
fi