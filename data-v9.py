import pandas as pd
import streamlit as st
import plotly.express as px
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori
import bcrypt
import time


# 设置页面
st.set_page_config(
    page_title="数据分析平台",
    layout="wide",
    page_icon="📊"
)

# 添加自定义CSS
st.markdown("""
<style>
    /* 调整Metric主数值字体大小 */
    [data-testid="stMetricValue"] {
        font-size: 24px;
    }
</style>
""", unsafe_allow_html=True)


# 验证密码
def verify_password(stored_hash, input_password):
    try:
        # 将存储的哈希值编码回bytes
        hashed = stored_hash.encode('utf-8')
        return bcrypt.checkpw(input_password.encode('utf-8'), hashed)
    except Exception as e:
        st.error(f"密码验证错误: {str(e)}")
        return False

# 密码哈希
users_db = {
    "admin": {
        "password_hash": "$2b$12$E3EHW5qw51z49OOz2ukqe.G907YBxJAcPhRupamEb3DNuGLg162Am",
        "role": "admin",
        "name": "系统管理员"
    },
    "guest": {
        "password_hash": "$2b$12$Yrq2EGj4vW9EQ/Rdg3WqZeilyV8G7dRNGqzyyVOm/sHjdXNHl2o3a",
        "role": "guest",
        "name": "访客用户"
    }
}

# 用户认证
def authenticate(username, password):
    if username in users_db:
        stored_hash = users_db[username]["password_hash"]
        return verify_password(stored_hash, password)
    return False


# 检查会话状态
def check_session():
    # 从URL参数获取会话信息
    query_params = st.query_params.to_dict()

    if "auth" in query_params and "user" in query_params:
        auth_token = query_params["auth"]
        username = query_params["user"]

        # 验证会话是否有效
        if username in users_db:
            # 检查session state中的token是否匹配
            if "auth_token" in st.session_state and st.session_state["auth_token"] == auth_token:
                # 检查会话是否超时（30分钟）
                current_time = time.time()
                last_activity = st.session_state.get("last_activity", 0)
                if current_time - last_activity < 1800:  # 30分钟
                    st.session_state["last_activity"] = current_time
                    return True
    return False


def login_page():
    # 使用columns创建居中布局
    col1, col2, col3 = st.columns([1, 2, 1])  # 左右留白，中间内容区域

    with col2:  # 只在中间列显示内容
        st.markdown(
            """
            <div style='display: flex; justify-content: center;'>
                <h3>欢迎登录数据分析平台</h3>
            </div>
            """, unsafe_allow_html=True
        )

        # 使用card样式容器
        with st.container(border=True):  # Streamlit 1.29+ 支持border参数
            # 登录表单
            with st.form("login_form"):
                username = st.text_input(
                    "用户名",
                    key="username_input",
                    placeholder="请输入用户名"
                )
                password = st.text_input(
                    "密码", type="password",
                    key="password_input",
                    placeholder="请输入密码"
                )
                submit_button = st.form_submit_button(
                    "登 录",
                    use_container_width=True,
                    type="primary"
                )

                if submit_button:
                    if not username or not password:
                        st.error("请输入用户名和密码")
                    elif authenticate(username, password):
                        # 创建会话
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = username
                        st.session_state["role"] = users_db[username]["role"]
                        st.session_state["last_activity"] = time.time()

                        # 生成并存储auth token
                        auth_token = f"{username}_{time.time()}"
                        st.session_state["auth_token"] = auth_token
                        # 设置URL参数保持会话
                        st.query_params["auth"] = auth_token
                        st.query_params["user"] = username
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")

# 数据分析
@st.cache_data
def load_data(file_path):
    """加载并预处理数据"""
    df = pd.read_excel(file_path)
    df['购买日期'] = pd.to_datetime(df['购买日期'])
    df['年月'] = df['购买日期'].dt.to_period('M')
    df['年'] = df['购买日期'].dt.year
    df['月'] = df['购买日期'].dt.month
    df['周'] = df['购买日期'].dt.isocalendar().week
    df['星期'] = df['购买日期'].dt.day_name()
    # return df
    return df.sort_values(['客户ID', "购买日期"])

# 分析内容
def show_analysis(uploaded_file):
    # 加载原始数据
    raw_df = load_data(uploaded_file)

    with st.sidebar:
        st.header("功能导航")
        selected = st.selectbox(
            label="选择分析维度",
            options=["销售数据概览", "购买行为分析", "地理位置分析", "热销产品分析", "复购次数分析", "产品组合分析"],
            index=0,  # 默认选中第一个
            help="使用下拉菜单切换不同功能模块"
        )

    # 添加侧边栏日期范围选择
    with st.sidebar:
        st.header("日期选项")
        date_range = st.date_input(
            "选择日期范围",
            value=[raw_df['购买日期'].min().date(), raw_df['购买日期'].max().date()],
            min_value=raw_df['购买日期'].min().date(),
            max_value=raw_df['购买日期'].max().date()
        )

        # 应用日期范围筛选
        if date_range:
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            df = raw_df[(raw_df['购买日期'] >= start_date) & (raw_df['购买日期'] <= end_date)].copy()
        else:
            df = raw_df.copy()

    # 显示原始数据
    if st.checkbox("显示原始数据表格"):
        st.subheader("原始销售数据表格")
        st.write(f"数据范围: {df['购买日期'].min().date()} 至 {df['购买日期'].max().date()}")
        st.dataframe(df)

    if selected == "销售数据概览":
        # 1.销售数据概览
        st.header("销售数据概览")

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        total_sales = df['总价'].sum()
        total_customers = df['客户ID'].nunique()
        total_products = df['产品ID'].nunique()
        total_orders = len(df[['客户ID', '购买日期']].drop_duplicates())
        total_boxes = df['数量'].sum()
        total_logistics_cost = df['运费'].sum()
        # avg_order_value = total_sales / len(df) if len(df) > 0 else 0 # 平均单价

        col1.metric("总销售额", f"¥{total_sales:,.2f}")
        col2.metric("总订单数", total_orders)
        col3.metric("总客户数", total_customers)
        col4.metric("总产品数", total_products)
        col5.metric("总箱数", total_boxes)
        col6.metric("总运费", f"{total_logistics_cost:,.2f}")

        # 2.时间趋势分析
        st.subheader("销售时间趋势")

        time_group = st.radio("时间颗粒度", ["日", "周", "月", "季", "年"], horizontal=True)

        if time_group == "日":
            time_df = df.groupby(df['购买日期'].dt.date)['总价'].sum().reset_index()
        elif time_group == "周":
            time_df = df.groupby(['year', 'week'])['总价'].sum().reset_index()
            time_df['date_label'] = time_df['year'].astype(str) + '-W' + time_df['week'].astype(str)
        elif time_group == "月":
            time_df = df.groupby(['year', 'month'])['总价'].sum().reset_index()
            time_df['date_label'] = time_df['year'].astype(str) + '-' + time_df['month'].astype(str).str.zfill(2)
        elif time_group == "季":
            time_df = df.copy()
            time_df['quarter'] = time_df['购买日期'].dt.quarter
            time_df = time_df.groupby(['year', 'quarter'])['总价'].sum().reset_index()
            time_df['date_label'] = time_df['year'].astype(str) + '-Q' + time_df['quarter'].astype(str)
        else:  # 年
            time_df = df.groupby('year')['总价'].sum().reset_index()
            time_df['date_label'] = time_df['year'].astype(str)

        fig = px.line(time_df,
                      x='date_label' if time_group != "日" else '购买日期',
                      y='总价',
                      title=f"按{time_group}统计的销售趋势",
                      text='总价',  # 可选：显示数值的列
                      labels={'总价': '销售额', 'date_label': '时间', '购买日期': '日期'})
        fig.update_traces(textposition="top center")    # 可选：显示数值标签（位置自动调整）
        st.plotly_chart(fig, use_container_width=True)

    elif selected == "购买行为分析":
        # 7. 客户购买行为变化分析
        st.header("购买行为分析")

        # 选择客户
        selected_customer = st.selectbox(
            "选择客户进行分析",
            df['客户名称'].unique(),    # 去重后的客户列表
            index=0     # 默认选择第一个客户
        )

        # 1.获取选定客户的数据
        customer_data = df[df["客户名称"] == selected_customer]

        # 2.按购买日期分组，整理每次购买的产品列表
        customer_purchases = (
            customer_data.groupby(["客户ID", "客户名称", "购买日期"])["产品名称"]
            .apply(list)  # 获取每次购买的所有产品
            .reset_index()
        )

        if len(customer_data) > 1:
            # 计算每次购买的变化
            customer_data['上次购买日期'] = customer_data['购买日期'].shift(1)
            customer_data['购买间隔天数'] = (
                    customer_data['购买日期'] - customer_data['上次购买日期']).dt.days

            # 客户购买历史
            # st.subheader(f"【{selected_customer}】客户购买历史")
            st.subheader("客户购买历史")
            st.dataframe(
                customer_data[['购买日期', '产品名称', '单价', '数量', '运费', '总价']])

            # 购买间隔分析
            st.subheader("购买间隔天数")
            fig = px.line(customer_data[1:],
                          x='购买日期',
                          y='购买间隔天数',
                          title="两次购买之间的间隔天数")
            st.plotly_chart(fig, use_container_width=True)


        # 3.产品比较函数
        def compare_products(group):
            group = group.sort_values("购买日期").copy()

            # 初始化新列
            group["上次的产品"] = None
            group["添加的产品"] = None
            group["减少的产品"] = None
            group["未变的产品"] = None

            # 遍历每一行计算差异
            for i in range(1, len(group)):
                current_products = set(group.at[i, "产品名称"])
                previous_products = set(group.at[i - 1, "产品名称"])

                group.at[i, "上次的产品"] = group.at[i - 1, "产品名称"]
                group.at[i, "添加的产品"] = list(current_products - previous_products)
                group.at[i, "减少的产品"] = list(previous_products - current_products)
                group.at[i, "未变的产品"] = list(current_products & previous_products)

            return group

        # 4.应用计算
        result = customer_purchases.groupby("客户ID", group_keys=False).apply(compare_products)

        # 5.只保留有对比的记录
        final_result = result[result["上次的产品"].notna()]

        # 6.显示结果
        # st.subheader(f"【{selected_customer}】购买产品变化")
        st.subheader("购买产品变化")
        if not final_result.empty:
            # 优化显示格式
            display_cols = ["购买日期", "产品名称", "上次的产品",
                            "添加的产品", "减少的产品", "未变的产品"]
            st.dataframe(final_result[display_cols])
        else:
            st.warning("该客户只有一次购买记录，无法比较差异！")

    elif selected == "地理位置分析":
        # 3.地理位置分析
        st.subheader("地理位置分析")

        company_type_sales = df.groupby('区域').agg({
            '总价': 'sum',
            '客户ID': 'nunique',
            '产品ID': pd.Series.nunique
        }).reset_index()
        company_type_sales.columns = ['区域位置', '总销售额', '客户数量', '产品种类']

        col1, col2 = st.columns(2, gap="large")

        with col1:
            fig = px.pie(company_type_sales,
                         values='总销售额',
                         names='区域位置',
                         title='各区域位置的销售额占比')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(company_type_sales,
                         x='区域位置',
                         y='客户数量',
                         title='各区域位置的客户数量',
                         text_auto=True,    # 显示数值
                         color='区域位置',  # 按类别分配颜色
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)

    elif selected == "热销产品分析":
        # 4.热销产品分析
        st.header("热销产品分析")

        product_sales = df.groupby(['产品ID', '产品名称']).agg({
            '数量': 'sum',
            '总价': 'sum',
            '客户ID': 'nunique'
        }).reset_index()
        product_sales.columns = ['产品ID', '产品名称', '销售数量', '销售额', '购买客户数']

        col1, col2 = st.columns(2, gap="large")

        with col1:
            top_n = st.slider("选择显示前N个产品", 3, 10, 6)
            fig = px.bar(product_sales.nlargest(top_n, '销售额'),
                         x='产品名称',
                         y='销售额',
                         text_auto=True,  # 显示数值
                         title=f"销售额前{top_n}的产品",
                         color='产品名称',  # 按类别分配颜色
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.treemap(product_sales,
                             path=['产品名称'],
                             values='销售额',
                             title="产品销售额占比")
            # 显示绝对值和百分比
            # fig.update_traces(textinfo='label+value+percent parent')
            fig.update_traces(textinfo='label+percent parent')
            st.plotly_chart(fig, use_container_width=True)

    elif selected == "复购次数分析":
        # 5.客户复购分析
        st.header("复购次数分析")

        # 计算每个客户的购买次数
        customer_purchase_count = df.groupby('客户ID')['购买日期'].nunique().reset_index()
        customer_purchase_count.columns = ['客户ID', 'purchase_count']

        # 分类客户
        customer_purchase_count['customer_type'] = pd.cut(
            customer_purchase_count['purchase_count'],
            bins=[0, 1, 3, 5, float('inf')],
            labels=['一次性客户', '偶尔复购(2-3次)', '经常复购(4-5次)', '高复购(5次以上)']
        )

        customer_type_dist = customer_purchase_count['customer_type'].value_counts().reset_index()
        customer_type_dist.columns = ['客户类型', '客户数量']

        fig = px.pie(customer_type_dist,
                     values='客户数量',
                     names='客户类型',
                     title="客户复购类型分布")
        st.plotly_chart(fig, use_container_width=True)

    elif selected == "产品组合分析":
        # 6.产品组合分析
        st.header("产品组合分析")

        # 获取每个订单购买的产品列表
        order_products = df.groupby(['客户ID', '购买日期'])['产品名称'].apply(list).reset_index()

        # 转换为适合关联规则挖掘的格式
        te = TransactionEncoder()
        te_ary = te.fit(order_products['产品名称']).transform(order_products['产品名称'])
        product_df = pd.DataFrame(te_ary, columns=te.columns_)

        # 使用Apriori算法找出频繁项集
        min_support = st.slider("设置最小支持度阈值", 0.01, 0.2, 0.05, 0.01, key="min_support")
        frequent_itemsets = apriori(product_df, min_support=min_support, use_colnames=True)

        # 将frozenset转换为可显示的字符串
        frequent_itemsets['itemsets'] = frequent_itemsets['itemsets'].apply(lambda x: ', '.join(list(x)))
        frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(lambda x: len(x.split(', ')))

        # 显示频繁购买的产品组合
        st.subheader("频繁购买的产品组合")
        st.dataframe(
            frequent_itemsets[frequent_itemsets['length'] > 1]
            .sort_values('support', ascending=False)
            .rename(columns={'support': '支持度', 'itemsets': '产品组合', 'length': '组合产品数量'})
        )


# 主应用界面
def main_app():
    # 显示用户信息和登出按钮
    st.sidebar.write(f"当前用户: {st.session_state['username']}")

    if st.sidebar.button("登出"):
        st.session_state["authenticated"] = False
        st.session_state.pop("username", None)
        st.session_state.pop("role", None)
        st.rerun()

    # 根据角色限制功能
    if st.session_state["role"] == "guest":
        st.warning("当前是访客用户，部分功能受限")

    # 上传文件 - 管理员和分析师可以上传
    if st.session_state["role"] in ["admin", "analyst"]:
        uploaded_file = st.file_uploader("请上传Excel表格文件进行数据分析", type=["xlsx", "xls"])
    else:
        # st.info("访客用户无法上传数据，正在使用示例数据进行分析")
        uploaded_file = None

    if uploaded_file is not None:
        show_analysis(uploaded_file)
    elif st.session_state["role"] == "guest":
        # 为访客用户提供示例数据
        st.info("系统正在使用示例数据进行演示...")
        # 加载内置的示例数据
        show_analysis("./example.xlsx")


if __name__ == "__main__":
    # 初始化session state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    # 检查会话状态
    if check_session():
        main_app()
        # 添加左下角作者信息
        st.sidebar.markdown(
            """
            <style>
            .sidebar-footer {
                position: fixed;
                bottom: 0;
                left: 2;
                width: 25%;
                padding: 2px;
                font-size: 12px;
                color: gray;
            }
            </style>

            <div class="sidebar-footer">
                <p>GitHub: <a href="https://github.com/Jonas-Mao">xiaofeng.mao</a></p>
                <p>©2025 Copy Right®</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # 会话无效，显示登录页面
        if "authenticated" in st.session_state:
            del st.session_state["authenticated"]
        login_page()