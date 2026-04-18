#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统集成测试 - 测试所有新功能模块
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path.cwd()))


def test_all_modules():
    """测试所有功能模块"""
    print("=== 系统集成测试 ===\n")

    # 1. 测试数据库
    print("1. 测试增强版数据库...")
    try:
        from database_enhanced import EnhancedDatabase
        db = EnhancedDatabase('./download_data/enhanced_legal_database.db')
        print("   ✅ 数据库初始化成功")
    except Exception as e:
        print(f"   ❌ 数据库失败: {e}")
        return False

    # 2. 测试法条拆分
    print("2. 测试法条拆分模块...")
    try:
        from article_splitter import ArticleSplitter, DatabaseArticleManager
        splitter = ArticleSplitter()

        test_text = """
《中华人民共和国民法典》

第一条
为了保护民事主体的合法权益，调整民事关系，维护社会和经济秩序，适应中国特色社会主义发展要求，弘扬社会主义核心价值观，根据宪法，制定本法。

第二条
民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。

第三条
民事主体的人身权利、财产权利以及其他合法权益受法律保护，任何组织或者个人不得侵犯。
"""

        articles = splitter.split_detailed(test_text)
        print(f"   ✅ 成功拆分 {len(articles)} 个法条")

        # 测试数据库集成
        db_manager = DatabaseArticleManager('./download_data/enhanced_legal_database.db')
        db_manager.init_article_tables()
        print("   ✅ 法条表结构初始化完成")

    except Exception as e:
        print(f"   ❌ 法条拆分失败: {e}")
        return False

    # 3. 测试向量检索
    print("3. 测试向量检索模块...")
    try:
        from vector_db import VectorIndex, EnhancedSearch
        vector_index = VectorIndex('./download_data/enhanced_legal_database.db')
        vector_index.init_vector_table()
        print("   ✅ 向量索引初始化完成")

        search = EnhancedSearch('./download_data/enhanced_legal_database.db')
        print("   ✅ 增强搜索初始化完成")
    except Exception as e:
        print(f"   ❌ 向量检索失败: {e}")
        return False

    # 4. 测试批量下载
    print("4. 测试批量下载模块...")
    try:
        from batch_downloader_enhanced import BatchDownloader, SampleDataGenerator
        downloader = BatchDownloader()
        print(f"   ✅ 批量下载器初始化完成")
        print(f"   支持分类: {list(downloader.categories.keys())}")

        # 测试示例数据生成
        generator = SampleDataGenerator(db)
        result = generator.generate_sample_data()
        print(f"   ✅ {result['message']}")
    except Exception as e:
        print(f"   ❌ 批量下载失败: {e}")
        return False

    # 5. 测试查询重写
    print("5. 测试查询重写模块...")
    try:
        from query_rewriter import QueryRewriter, AdvancedSearch
        rewriter = QueryRewriter('./download_data/enhanced_legal_database.db')

        # 测试查询扩展
        expanded = rewriter.expand_query('民法典')
        print(f"   ✅ 查询扩展: {expanded}")

        # 测试别名解析
        resolved = rewriter.resolve_law_alias('民法典')
        print(f"   ✅ 别名解析: {resolved}")
    except Exception as e:
        print(f"   ❌ 查询重写失败: {e}")
        return False

    # 6. 测试MCP服务器
    print("6. 测试MCP服务器...")
    try:
        from mcp_server_enhanced import LegalMCPService, create_mcp_tools
        service = LegalMCPService('./download_data/enhanced_legal_database.db')

        # 测试统计功能
        result = service.get_statistics()
        if result['success']:
            print(f"   ✅ MCP统计功能: {result['total_laws']} 条法规")
        else:
            print(f"   ⚠️ MCP统计功能异常: {result.get('error')}")

        # 测试工具定义
        tools = create_mcp_tools(service)
        print(f"   ✅ MCP工具定义: {len(tools)} 个工具")
    except Exception as e:
        print(f"   ❌ MCP服务器失败: {e}")
        return False

    # 7. 测试Web界面文件
    print("7. 测试Web界面文件...")
    try:
        files = [
            'app_enhanced.py',
            'download_enhanced.command',
            'law_query.py'
        ]

        for file in files:
            if Path(file).exists():
                print(f"   ✅ {file} 存在")
            else:
                print(f"   ❌ {file} 缺失")
                return False
    except Exception as e:
        print(f"   ❌ 文件检查失败: {e}")
        return False

    print("\n🎉 所有模块测试通过！")
    return True


def show_system_info():
    """显示系统信息"""
    print("\n=== 系统信息 ===")
    print(f"Python版本: {sys.version}")
    print(f"项目路径: {Path.cwd()}")

    # 数据库信息
    db_path = Path('./download_data/enhanced_legal_database.db')
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"数据库大小: {size_mb:.2f} MB")
    else:
        print("数据库: 不存在（首次运行时创建）")

    print("\n核心功能模块:")
    modules = [
        "database_enhanced.py - 增强版数据库架构",
        "article_splitter.py - 法条智能拆分",
        "vector_db.py - 向量语义检索",
        "query_rewriter.py - 智能查询扩展",
        "batch_downloader_enhanced.py - 批量下载",
        "mcp_server_enhanced.py - AI接口服务",
        "app_enhanced.py - Web管理界面",
        "law_query.py - 命令行工具"
    ]

    for module in modules:
        print(f"  • {module}")


if __name__ == "__main__":
    # 显示系统信息
    show_system_info()

    # 运行集成测试
    success = test_all_modules()

    if success:
        print("\n✅ 系统集成测试完成 - 所有功能正常")
        print("\n🚀 可以开始使用增强版法律数据库系统！")
        print("   启动命令: python3 app_enhanced.py")
    else:
        print("\n❌ 系统集成测试失败 - 请检查上述错误")
        sys.exit(1)