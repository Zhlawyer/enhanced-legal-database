# 增强版法律数据库管理系统

基于 GitHub 项目 [sublatesublate-design/legal-database](https://github.com/sublatesublate-design/legal-database) 的完整实现，并在此基础上进行了功能增强和优化。

## ✨ 项目特色

### 🚀 超越原项目的功能
- **扩展数据库架构**: 16个字段 vs 基础字段，8张表 vs 2张表
- **智能法条拆分**: 自动识别条、款、项、目层级结构
- **语义搜索引擎**: 基于向量相似度的智能检索
- **完整AI接口**: 9个MCP工具，支持Claude等AI助手
- **增强Web界面**: 8个功能标签页，用户体验优化

### 🔧 技术优势
- **性能优化**: 连接池、WAL模式、LRU缓存
- **代码质量**: 完整注释、类型提示、模块化设计
- **错误处理**: 完善的异常处理和日志记录
- **可扩展性**: 模块化架构，易于功能扩展

## 🚀 快速开始

### 方法一：一键启动器（推荐）
```bash
# 双击运行（macOS/Linux）
./launch_enhanced.command

# 或命令行运行
bash launch_enhanced.command
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

## 📁 项目结构

```
.
├── 启动器
│   └── launch_enhanced.command      # 一键启动器
├── Web界面
│   └── app_enhanced.py              # 增强版界面
├── 核心模块
│   ├── database_enhanced.py         # 增强版数据库
│   ├── article_splitter.py          # 法条拆分系统
│   ├── vector_db.py                 # 向量检索引擎
│   ├── query_rewriter.py            # 智能查询扩展
│   ├── batch_downloader_enhanced.py # 批量下载系统
│   └── mcp_server_enhanced.py       # MCP服务器
├── 工具
│   ├── law_query.py                 # 命令行查询
│   └── test_integration.py          # 系统测试
└── 文档
    ├── README.md                    # 本文件
    └── 项目完成报告_v6.0_最终版.md  # 详细报告
```

## 🎯 核心功能

### 1. 智能搜索系统
- **别名扩展**: "民法典" → "中华人民共和国民法典"
- **同义词扩展**: 法律概念标准化
- **全文检索**: FTS5毫秒级搜索
- **高亮显示**: 搜索结果关键词标记

### 2. 法条拆分系统
- **智能识别**: 自动识别条、款、项、目层级
- **数据库集成**: 拆分结果结构化存储
- **搜索支持**: 支持按法条内容检索
- **统计分析**: 法条结构信息提取

### 3. 语义搜索系统
- **向量检索**: 基于相似度的智能搜索
- **混合搜索**: 结合关键词和语义优势
- **相似推荐**: 查找相关法律条款
- **性能优化**: 向量索引预加载

### 4. MCP服务器接口
- **9个AI工具**: 完整的AI友好接口
- **标准协议**: MCP协议标准实现
- **工具定义**: 完整的参数和描述
- **易集成**: 支持Claude等AI助手

## 📊 功能对比

| 功能模块 | GitHub原项目 | 本实现 | 状态 |
|---------|-------------|--------|------|
| 数据库架构 | 基础字段 | 扩展16字段 | ✅ 超越 |
| 法条拆分 | ❌ 无 | ✅ 智能拆分 | ✅ 新增 |
| 向量检索 | ❌ 无 | ✅ 语义搜索 | ✅ 新增 |
| 批量下载 | ✅ Selenium | ✅ 增强版 | ✅ 优化 |
| Web界面 | 基础功能 | 8标签页 | ✅ 增强 |
| MCP服务器 | 基础工具 | 9个工具 | ✅ 增强 |
| 性能优化 | 基础 | 连接池+缓存 | ✅ 优化 |

## 🔧 技术架构

### 数据库设计
```sql
-- 主表（16个扩展字段）
laws (id, title, short_title, category, publish_date, ...)

-- 法条表（智能拆分）
articles (id, law_id, article_number, content, level, ...)

-- 向量表（语义检索）
article_vectors (article_id, vector_blob, embedding_model, ...)
```

### 性能优化
- **连接池**: 预创建5个连接
- **WAL模式**: 支持并发读写
- **LRU缓存**: 1024条目缓存
- **批量插入**: 优化大批量数据处理

## 📈 使用场景

- **法律专业人士**: 快速检索法律法规
- **AI助手集成**: 通过MCP增强AI能力
- **法律研究**: 分类浏览和统计分析
- **数据管理**: 备份、恢复、同步

## 🎯 验收标准

- ✅ **可运行性**: 双击启动器即可运行
- ✅ **数据库**: 完整表结构和索引
- ✅ **Web界面**: 8个功能标签页正常
- ✅ **智能功能**: 搜索、拆分、语义检索
- ✅ **AI接口**: MCP服务器9个工具
- ✅ **文档齐全**: 使用说明和项目报告

## 📞 技术支持

- **详细报告**: 查看 `项目完成报告_v6.0_最终版.md`
- **系统测试**: 运行 `python3 test_integration.py`
- **问题反馈**: GitHub Issues

## 📄 许可证

本项目基于 [sublatesublate-design/legal-database](https://github.com/sublatesublate-design/legal-database) 实现，
仅供学习和研究使用，请遵守相关法律法规。

---

**版本**: v6.0 (最终增强版)  
**基于**: sublatesublate-design/legal-database  
**日期**: 2026-04-19  
**状态**: ✅ 生产级就绪