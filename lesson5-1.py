# ============================================================
# 配置区 —— 所有账号信息统一在此修改
# ============================================================
DB_HOST     = "192.168.40.83"
DB_PORT     = 3306
DB_USER     = "student"
DB_PASSWORD = "mlbb2026"   # ← 在这里填入你的密码
DB_NAME     = "homework_db"

# 分析结果配置
MIN_GAMES   = 30                     # 最低场次门槛
OUTPUT_FILE = "hero_winrate.xlsx"    # 导出文件名

# ============================================================
# 导入依赖
# ============================================================
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


# ============================================================
# 核心函数：创建数据库连接引擎（封装，便于复用）
# ============================================================
def get_engine():
    """
    根据顶部配置创建并返回 SQLAlchemy Engine。
    使用 pymysql 作为驱动，连接 MySQL 数据库。
    """
    connection_url = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        f"?charset=utf8mb4"
    )
    engine = create_engine(
        connection_url,
        pool_pre_ping=True,
        echo=False
    )
    return engine


# ============================================================
# 工具函数：执行 SELECT 查询，返回 DataFrame
# ============================================================
def query_to_df(sql: str, params: dict = None) -> pd.DataFrame:
    """
    执行 SQL 查询，将结果以 pandas DataFrame 返回。

    参数：
        sql    : 要执行的 SQL 字符串，支持 :param 占位符
        params : 可选，绑定参数字典
    返回：
        pd.DataFrame
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        return df
    except SQLAlchemyError as e:
        print(f"[错误] 数据库查询失败：{e}")
        raise


# ============================================================
# 第一步：验证连接 —— 查询 hero 表 LIMIT 5
# ============================================================
def verify_connection():
    """查询 hero 表前 5 条，验证数据库连接是否正常。"""
    print("=" * 55)
    print("  Step 1 / 4  验证数据库连接")
    print("=" * 55)

    verify_sql = """
        SELECT hero_id, hero_name, role, attack_type
        FROM hero
        LIMIT 5
    """
    df = query_to_df(verify_sql)
    print(f"✅ 连接成功！hero 表前 5 条记录：\n")
    print(df.to_string(index=False))
    print()


# ============================================================
# 第二步：从数据库读取原始数据
# ============================================================
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """分别读取 hero 表和 battle_record 表，返回两个 DataFrame。"""
    print("=" * 55)
    print("  Step 2 / 4  读取原始数据")
    print("=" * 55)

    sql_hero   = "SELECT hero_id, hero_name, role, attack_type FROM hero"
    sql_battle = "SELECT hero_id, is_win, battle_date FROM battle_record"

    df_hero   = query_to_df(sql_hero)
    df_battle = query_to_df(sql_battle)

    print(f"✅ hero 表：{len(df_hero)} 条记录")
    print(f"✅ battle_record 表：{len(df_battle)} 条记录\n")

    return df_hero, df_battle


# ============================================================
# 第三步：数据处理 —— 合并、计算、筛选、排序
# ============================================================
def process_data(df_hero: pd.DataFrame,
                 df_battle: pd.DataFrame) -> pd.DataFrame:
    """
    合并两表，计算每个英雄的总场次 / 胜场数 / 胜率，
    筛选总场次 >= MIN_GAMES，按胜率降序排列。
    """
    print("=" * 55)
    print("  Step 3 / 4  数据处理与统计")
    print("=" * 55)

    # ── 3-1  按英雄聚合战绩 ──────────────────────────────────
    df_stats = (
        df_battle
        .groupby("hero_id", as_index=False)
        .agg(
            total_games = ("is_win", "count"),   # 总场次
            win_games   = ("is_win", "sum")      # 胜场数（is_win=1 直接求和）
        )
    )

    # ── 3-2  计算胜率（百分比，保留一位小数）────────────────
    df_stats["win_rate"] = (
        (df_stats["win_games"] / df_stats["total_games"] * 100)
        .round(1)
    )

    # ── 3-3  LEFT JOIN hero 表，补充英雄名称和职业信息 ───────
    df_merged = pd.merge(df_hero, df_stats, on="hero_id", how="left")

    # 填充没有战绩的英雄（total_games = 0）
    df_merged[["total_games", "win_games"]] = (
        df_merged[["total_games", "win_games"]].fillna(0).astype(int)
    )
    df_merged["win_rate"] = df_merged["win_rate"].fillna(0.0)

    # ── 3-4  筛选：总场次 >= MIN_GAMES ──────────────────────
    df_filtered = df_merged[df_merged["total_games"] >= MIN_GAMES].copy()

    # ── 3-5  按胜率从高到低排序 ──────────────────────────────
    df_result = (
        df_filtered
        .sort_values("win_rate", ascending=False)
        .reset_index(drop=True)
    )

    # ── 3-6  调整最终列顺序与列名（更易读）─────────────────
    df_result = df_result[[
        "hero_id", "hero_name", "role", "attack_type",
        "total_games", "win_games", "win_rate"
    ]]
    df_result.columns = [
        "英雄ID", "英雄名称", "职业", "普攻类型",
        "总场次", "胜场数", "胜率(%)"
    ]

    print(f"✅ 满足场次门槛（>= {MIN_GAMES} 场）的英雄：{len(df_result)} 位\n")
    print(df_result.to_string(index=False))
    print()

    return df_result


# ============================================================
# 第四步：导出 Excel + 打印统计摘要
# ============================================================
def export_and_summary(df_result: pd.DataFrame):
    """将结果导出为 Excel，并在终端打印关键统计摘要。"""
    print("=" * 55)
    print("  Step 4 / 4  导出结果 & 统计摘要")
    print("=" * 55)

    # ── 4-1  导出 Excel ──────────────────────────────────────
    df_result.to_excel(OUTPUT_FILE, index=False, sheet_name="英雄胜率")
    print(f"✅ 结果已导出：{OUTPUT_FILE}\n")

    # ── 4-2  统计摘要 ────────────────────────────────────────
    total_heroes  = len(df_result)
    avg_win_rate  = df_result["胜率(%)"].mean().round(1)

    # 胜率最高的英雄（可能并列，全部展示）
    max_rate      = df_result["胜率(%)"].max()
    top_heroes    = df_result[df_result["胜率(%)"] == max_rate]

    print("┌─────────────────────────────────────────┐")
    print("│              📊 统计摘要                 │")
    print("├─────────────────────────────────────────┤")
    print(f"│  纳入统计英雄总数：{total_heroes:<4} 位               │")
    print(f"│  所有英雄平均胜率：{avg_win_rate:<5} %              │")
    print(f"│  胜率最高英雄：                          │")

    for _, row in top_heroes.iterrows():
        line = f"│    · {row['英雄名称']}（{row['职业']}）胜率 {row['胜率(%)']}%"
        # 对齐右边框
        print(f"{line:<43}│")

    print("└─────────────────────────────────────────┘")


# ============================================================
# 主流程入口
# ============================================================
if __name__ == "__main__":

    try:
        verify_connection()              # Step 1：验证连接
        df_hero, df_battle = load_data() # Step 2：读取数据
        df_result = process_data(        # Step 3：处理数据
            df_hero, df_battle
        )
        export_and_summary(df_result)    # Step 4：导出 + 摘要

    except Exception as e:
        print(f"\n❌ 程序异常终止：{e}")
