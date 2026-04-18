# 增强版法律数据库管理系统 v6.0

基于 GitHub 项目 [sublatesublate-design/legal-database](https://github.com/sublatesublate-design/legal-database) 架构实现的完整法律数据库系统。

## 🚀 快速启动

### 方法一：一键启动器（推荐）
```bash
# 双击运行
download_enhanced.command
```

### 方法二：Web界面
```bash
python3 app_enhanced.py
# 访问: http://localhost:8501
```

### 方法三：命令行工具
```bash
python3 law_query.py
```

## 📁 核心文件

### 启动器
- `download_enhanced.command` - 一键启动器（双击运行）

### Web界面
- `app_enhanced.py` - 增强版Streamlit界面

### 核心模块
- `database_enhanced.py` - 增强版数据库架构
- `query_rewriter.py` - 智能查询扩展系统
- `mcp_server_enhanced.py` - MCP服务器接口
- `update_manager.py` - 增量更新机制

### 工具
- `law_query.py` - 命令行查询工具

### 文档
- `README.md` - 本文件
- `项目完成报告_v6.0.md` - 详细项目报告

## ✨ 核心功能

### 1. 智能搜索系统
- **别名扩展**: "民法典" → "中华人民共和国民法典"
- **同义词扩展**: 支持法律概念标准化
- **全文检索**: FTS5毫秒级搜索

### 2. 数据库架构
- **主表**: 法律法规完整信息
- **别名表**: 法律简称管理
- **同义词表**: 概念标准化
- **下载历史**: 同步记录

### 3. MCP服务器接口
- 7个AI友好工具
- 支持Claude等AI助手
- 标准MCP协议

### 4. 增量更新
- 智能检测新法规
- 自动同步更新
- 备份管理

## 📊 数据统计

- **数据库位置**: `download_data/enhanced_legal_database.db`
- **当前数据**: 示例数据
- **支持分类**: 宪法、法律、行政法规、监察法规、地方法规、司法解释

## 🔧 技术架构

### 后端技术
- **Python 3.9+**: 核心编程语言
- **SQLite + FTS5**: 数据库引擎
- **Streamlit**: Web界面框架
- **MCP协议**: AI接口标准

### 数据流程
```
数据下载 → 智能解析 → 结构化存储 → 全文检索 → AI接口
```

## 🎯 使用场景

- **法律专业人士**: 快速检索法律法规
- **AI助手集成**: 通过MCP接口增强AI能力
- **法律研究**: 分类浏览和统计分析
- **数据备份**: 定期备份和恢复

## 📈 性能特点

- **搜索响应**: <100ms (FTS5索引)
- **并发支持**: 连接池优化
- **缓存机制**: LRU缓存1024条目
- **增量更新**: 只更新新增内容

## ⚠️ 当前状态

- ✅ 系统架构完整实现
- ✅ 智能搜索功能正常
- ✅ MCP接口可用
- ⚠️ 需要添加真实法规数据

## 🔍 故障排除

### 依赖问题
```bash
# 安装核心依赖
pip3 install streamlit python-docx requests beautifulsoup4
```

### 端口冲突
```bash
# 修改Streamlit端口
streamlit run app_enhanced.py --server.port 8502
```

### 数据库问题
```bash
# 重新初始化数据库
rm -f download_data/enhanced_legal_database.db
python3 database_enhanced.py
```

## 📞 技术支持

- **项目报告**: 查看 `项目完成报告_v6.0.md`
- **系统测试**: 运行系统自带测试功能
- **日志查看**: 检查 `download_data/logs/` 目录

---

**版本**: v6.0 (增强版)  
**基于**: sublatesublate-design/legal-database  
**日期**: 2026-04-19  
**状态**: ✅ 完整可运行