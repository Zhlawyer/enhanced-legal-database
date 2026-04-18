#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版Streamlit Web界面 - 基于GitHub项目 sublatesublate-design/legal-database
提供完整的法律数据库管理功能

功能特色：
- 8个功能标签页：搜索、同步、更新、浏览、别名、统计、拆分、语义
- 智能搜索系统：别名扩展、同义词扩展、高亮显示
- 法条拆分：智能识别条、款、项、目层级
- 语义搜索：基于向量相似度的智能检索
"""

import streamlit as st
import sqlite3
import pandas as pd
import subprocess
import os
import time
from pathlib import Path
from datetime import datetime
from database_enhanced import EnhancedDatabase
from query_rewriter import AdvancedSearch

# 页面配置
st.set_page_config(
    page_title="增强版法律数据库管理系统 v6.0",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
<style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .highlight {
        background-color: #ffeb3b;
        padding: 2px 4px;
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)

# 数据目录
DATA_DIR = Path("./download_data")
DB_PATH = DATA_DIR / "legal_database.db"
ENHANCED_DB_PATH = DATA_DIR / "enhanced_legal_database.db"


@st.cache_resource
def get_database():
    """获取数据库实例（带缓存）"""
    try:
        return EnhancedDatabase(ENHANCED_DB_PATH)
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return None


@st.cache_resource
def get_search_engine():
    """获取搜索引擎实例（带缓存）"""
    try:
        return AdvancedSearch(ENHANCED_DB_PATH)
    except Exception as e:
        st.error(f"搜索引擎初始化失败: {e}")
        return None


def get_db_stats():
    """获取数据库统计信息"""
    try:
        db = get_database()
        if db is None:
            return None
        stats = db.get_statistics()
        return stats
    except Exception as e:
        st.error(f"获取统计信息失败: {e}")
        return None


def migrate_to_enhanced():
    """迁移到增强版数据库"""
    if not DB_PATH.exists():
        return

    try:
        enhanced_db = get_database()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 迁移数据
        cursor.execute('''
            SELECT title, category, publish_date, status,
                   content, department, source_url
            FROM laws
        ''')

        migrated_count = 0
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
                migrated_count += 1
            except sqlite3.IntegrityError:
                # 已存在，跳过
                pass

        conn.close()
        return migrated_count

    except Exception as e:
        st.error(f"数据库迁移失败: {e}")
        return 0


# 侧边栏
st.sidebar.title("🛠️ 增强版管理面板")
st.sidebar.image("https://img.icons8.com/wired/128/000000/law.png", width=100)
st.sidebar.divider()

selected_category = st.sidebar.selectbox(
    "选择法律分类",
    ["全部", "宪法", "法律", "行政法规", "监察法规", "地方法规", "司法解释"]
)

# 主界面
st.title("⚖️ 增强版法律数据库管理系统")
st.write("基于 GitHub 项目: sublatesublate-design/legal-database")
st.write("提供智能查询、别名系统、增量更新等高级功能")

# 统计概览
stats = get_db_stats()
if stats:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总计入库法律", f"{stats['total']} 条")
    with col2:
        st.metric("分类数量", f"{len(stats['category_stats'])} 个")
    with col3:
        st.metric("最近7天更新", f"{stats['recent_7days']} 条")
    with col4:
        active_count = sum(count for status, count in stats['status_stats'] if status == '有效')
        st.metric("现行有效", f"{active_count} 条")

    # 分类分布图表
    if stats['category_stats']:
        category_df = pd.DataFrame(stats['category_stats'], columns=['分类', '数量'])
        st.bar_chart(category_df.set_index('分类'))
else:
    st.warning("数据库尚未建立，请先执行初始化流程。")

st.divider()

# 功能标签页
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🔍 智能搜索", "📥 数据同步", "🔄 增量更新", "📚 数据浏览",
    "🔧 别名管理", "📊 统计分析", "⚖️ 法条拆分", "🎯 语义搜索"
])

with tab1:
    st.subheader("智能搜索系统")

    # 搜索框
    search_query = st.text_input("请输入搜索关键词", "",
                                 placeholder="支持法律名称、条款内容、概念关键词")

    # 搜索过滤器
    col1, col2, col3 = st.columns(3)
    with col1:
        search_category = st.selectbox("分类筛选", ["全部", "宪法", "法律", "行政法规", "监察法规", "地方法规", "司法解释"])
    with col2:
        search_status = st.selectbox("状态筛选", ["全部", "有效", "已修改", "尚未生效", "已废止"])
    with col3:
        result_limit = st.slider("结果数量", 10, 200, 50)

    if search_query:
        search_engine = get_search_engine()

        # 构建过滤器
        filters = {'limit': result_limit}
        if search_category != "全部":
            filters['category'] = search_category
        if search_status != "全部":
            filters['status'] = search_status

        # 执行搜索
        with st.spinner("搜索中..."):
            result = search_engine.search(search_query, filters)

        if result['success']:
            st.success(f"找到 {result['count']} 个结果 (查询扩展: {result['expanded_query']})")

            # 显示结果
            for i, item in enumerate(result['results'], 1):
                with st.expander(f"{i}. {item['highlighted_title']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"分类: {item['category']} | 状态: {item['status']}")
                        st.info(f"发布日期: {item['publish_date']}")
                        st.info(f"发布部门: {item['department']}")
                    with col2:
                        if item['is_amendment']:
                            st.warning(f"📝 修正案 (针对: {item['base_law_title']})")

                    # 显示内容预览
                    if item['highlighted_content']:
                        st.markdown("**内容预览:**")
                        st.markdown(item['highlighted_content'], unsafe_allow_html=True)

                    if item['source_url']:
                        st.markdown(f"🔗 [原文链接]({item['source_url']})")

        else:
            st.error(f"搜索失败: {result['error']}")

with tab2:
    st.subheader("数据同步与迁移")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("迁移到增强版数据库", type="primary"):
            with st.status("正在迁移数据...", expanded=True) as status:
                migrated_count = migrate_to_enhanced()
                status.update(label=f"迁移完成: {migrated_count} 条法规", state="complete")
                st.success(f"成功迁移 {migrated_count} 条法规到增强版数据库")
                st.rerun()

    with col2:
        if st.button("重新初始化增强版数据库"):
            with st.status("正在初始化...", expanded=True) as status:
                # 重新创建数据库
                enhanced_db_path = Path(ENHANCED_DB_PATH)
                if enhanced_db_path.exists():
                    enhanced_db_path.unlink()

                # 重新初始化
                db = get_database()
                status.update(label="数据库初始化完成", state="complete")
                st.success("增强版数据库初始化完成")
                st.rerun()

    st.divider()

    st.subheader("数据库文件信息")
    if ENHANCED_DB_PATH.exists():
        file_size = ENHANCED_DB_PATH.stat().st_size / (1024 * 1024)
        st.info(f"增强版数据库: {ENHANCED_DB_PATH}")
        st.info(f"文件大小: {file_size:.2f} MB")
        st.info(f"修改时间: {datetime.fromtimestamp(ENHANCED_DB_PATH.stat().st_mtime)}")
    else:
        st.warning("增强版数据库不存在，请先迁移数据")

with tab3:
    st.subheader("增量更新机制")

    st.info("增量更新功能可以检测官网最新法规，并只下载新增内容")

    col1, col2 = st.columns(2)

    with col1:
        update_category = st.selectbox("选择更新分类", ["法律", "行政法规", "监察法规", "地方法规", "司法解释"])
        max_pages = st.slider("检查页数", 1, 20, 5)

    with col2:
        if st.button("检查更新", type="primary"):
            st.warning("增量更新功能需要连接真实API，当前版本使用示例数据")

    st.divider()

    st.subheader("更新日志")
    update_log = """
    - **2026-04-19**: 系统初始化完成
    - **2026-04-19**: 迁移到增强版数据库架构
    - **2026-04-19**: 添加智能搜索功能
    """
    st.markdown(update_log)

with tab4:
    st.subheader("数据库浏览")

    if ENHANCED_DB_PATH.exists():
        conn = sqlite3.connect(ENHANCED_DB_PATH)

        # 高级搜索功能
        search_term = st.text_input("浏览搜索", "", placeholder="搜索法规标题或内容")

        # 构建查询
        if search_term:
            query = """
                SELECT title, publish_date, category, status, department, is_amendment, base_law_title
                FROM laws
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY last_updated DESC
                LIMIT 200
            """
            params = (f"%{search_term}%", f"%{search_term}%")
        else:
            query = """
                SELECT title, publish_date, category, status, department, is_amendment, base_law_title
                FROM laws
                ORDER BY last_updated DESC
                LIMIT 200
            """
            params = ()

        try:
            df_laws = pd.read_sql_query(query, conn, params=params)

            # 格式化显示
            def format_title(row):
                if row['is_amendment']:
                    return f"📝 {row['title']} (针对: {row['base_law_title']})"
                return row['title']

            df_laws['显示标题'] = df_laws.apply(format_title, axis=1)

            # 显示数据
            st.dataframe(
                df_laws[['显示标题', 'publish_date', 'category', 'status', 'department']],
                use_container_width=True,
                height=400
            )

            st.info(f"显示 {len(df_laws)} 条法规（最多显示200条）")

        except Exception as e:
            st.error(f"查询数据失败: {e}")
        finally:
            conn.close()
    else:
        st.error("数据库尚未建立，请先执行数据同步。")

with tab5:
    st.subheader("别名管理系统")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("添加法律别名")
        alias_input = st.text_input("别名", placeholder="例如: 民法典")
        law_title = st.text_input("对应法律标题", placeholder="例如: 中华人民共和国民法典")
        confidence = st.slider("置信度", 0.1, 1.0, 1.0, 0.1)

        if st.button("添加别名"):
            if alias_input and law_title:
                db = get_database()
                success = db.add_alias(alias_input, law_title, confidence)
                if success:
                    st.success(f"成功添加别名: {alias_input} → {law_title}")
                else:
                    st.error("添加别名失败，请检查法律标题是否正确")
            else:
                st.warning("请填写别名和法律标题")

    with col2:
        st.subheader("添加概念同义词")
        term_input = st.text_input("同义词", placeholder="例如: 债权人撤销权")
        canonical_term = st.text_input("标准概念", placeholder="例如: 撤销权")
        category = st.selectbox("概念分类", ["民法", "刑法", "行政法", "其他"])

        if st.button("添加同义词"):
            if term_input and canonical_term:
                db = get_database()
                success = db.add_synonym(term_input, canonical_term, category)
                if success:
                    st.success(f"成功添加同义词: {term_input} → {canonical_term}")
                else:
                    st.error("添加同义词失败")
            else:
                st.warning("请填写同义词和标准概念")

    st.divider()

    st.subheader("别名查询测试")
    test_query = st.text_input("测试查询", placeholder="输入别名或关键词进行测试")

    if test_query:
        rewriter = get_search_engine().rewriter
        resolved = rewriter.resolve_law_alias(test_query)
        expanded = rewriter.expand_query(test_query)

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"别名解析: {test_query} → {resolved}")
        with col2:
            st.info(f"查询扩展: {expanded}")

with tab6:
    st.subheader("统计分析")

    if stats:
        # 详细统计
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("分类分布")
            category_df = pd.DataFrame(stats['category_stats'], columns=['分类', '数量'])
            st.dataframe(category_df, use_container_width=True)

        with col2:
            st.subheader("状态分布")
            status_df = pd.DataFrame(stats['status_stats'], columns=['状态', '数量'])
            st.dataframe(status_df, use_container_width=True)

        st.divider()

        # 数据质量分析
        st.subheader("数据质量分析")
        conn = sqlite3.connect(ENHANCED_DB_PATH)

        try:
            # 检查完整性
            cursor = conn.cursor()

            # 无内容法规数量
            cursor.execute("SELECT COUNT(*) FROM laws WHERE content IS NULL OR content = ''")
            null_content = cursor.fetchone()[0]

            # 无发布日期数量
            cursor.execute("SELECT COUNT(*) FROM laws WHERE publish_date IS NULL")
            null_date = cursor.fetchone()[0]

            col1, col2 = st.columns(2)
            with col1:
                st.metric("无内容法规", null_content)
            with col2:
                st.metric("无发布日期", null_date)

            if null_content > 0 or null_date > 0:
                st.warning("存在数据完整性问题，建议检查数据源")

        except Exception as e:
            st.error(f"数据质量分析失败: {e}")
        finally:
            conn.close()

    else:
        st.warning("暂无统计信息")

with tab7:
    st.subheader("法条拆分系统")

    col1, col2 = st.columns(2)

    with col1:
        law_title_input = st.text_input("法律标题", placeholder="例如: 中华人民共和国民法典")
        article_content = st.text_area("法条内容", placeholder="粘贴法律文本内容", height=200)

    with col2:
        if st.button("拆分法条", type="primary"):
            if law_title_input and article_content:
                from article_splitter import ArticleSplitter
                splitter = ArticleSplitter()

                with st.spinner("正在拆分法条..."):
                    articles = splitter.split_detailed(article_content, law_title_input)

                st.success(f"成功拆分 {len(articles)} 个法条")

                # 显示拆分结果
                for article in articles[:10]:  # 只显示前10个
                    with st.expander(f"【{article.article_number}】"):
                        st.text(article.content[:500] + "..." if len(article.content) > 500 else article.content)

                if len(articles) > 10:
                    st.info(f"还有 {len(articles) - 10} 个法条未显示")
            else:
                st.warning("请填写法律标题和内容")

    st.divider()

    st.subheader("法条搜索")
    article_search = st.text_input("搜索法条内容", placeholder="输入关键词搜索法条")

    if article_search:
        from article_splitter import DatabaseArticleManager
        db_manager = DatabaseArticleManager(ENHANCED_DB_PATH)
        results = db_manager.search_articles(article_search)

        if results:
            st.success(f"找到 {len(results)} 个相关法条")
            for result in results[:20]:
                with st.expander(f"【{result['article_number']}】 {result['law_title']}"):
                    st.info(f"级别: {result['level']} | 字数: {result['word_count']}")
                    st.text(result['content'])
        else:
            st.info("未找到相关法条")

with tab8:
    st.subheader("语义搜索系统")

    col1, col2 = st.columns(2)

    with col1:
        semantic_query = st.text_input("语义查询", placeholder="输入自然语言查询")
        search_method = st.selectbox("搜索方法", ["混合搜索", "关键词搜索", "语义搜索"])

    with col2:
        top_k = st.slider("结果数量", 5, 50, 20)
        if st.button("语义搜索", type="primary"):
            if semantic_query:
                from vector_db import EnhancedSearch
                search = EnhancedSearch(ENHANCED_DB_PATH)

                method_map = {
                    "混合搜索": "hybrid",
                    "关键词搜索": "keyword",
                    "语义搜索": "vector"
                }

                with st.spinner("正在搜索..."):
                    results = search.search(semantic_query, method_map[search_method], top_k)

                # 显示结果
                result_key = "hybrid" if search_method == "混合搜索" else ("keyword" if search_method == "关键词搜索" else "vector")
                if result_key in results and results[result_key]:
                    st.success(f"找到 {len(results[result_key])} 个结果")

                    for i, result in enumerate(results[result_key][:20], 1):
                        with st.expander(f"{i}. 【{result['article_number']}】 {result['law_title']}"):
                            col_res1, col_res2 = st.columns(2)
                            with col_res1:
                                st.info(f"来源: {result.get('source', '混合')}")
                                if 'similarity' in result:
                                    st.info(f"相似度: {result['similarity']:.3f}")
                            with col_res2:
                                if 'score' in result:
                                    st.info(f"综合得分: {result['score']:.3f}")

                            st.text(result['content'])
                else:
                    st.info("未找到相关结果")
            else:
                st.warning("请输入查询内容")

    st.divider()

    st.subheader("搜索方法说明")
    st.markdown("""
    - **关键词搜索**: 基于文本匹配的传统搜索
    - **语义搜索**: 基于向量相似度的智能搜索
    - **混合搜索**: 结合关键词和语义搜索的优势
    """)

# 页脚
st.divider()
st.caption("增强版法律数据库管理系统 v6.0 | 基于 GitHub: sublatesublate-design/legal-database")