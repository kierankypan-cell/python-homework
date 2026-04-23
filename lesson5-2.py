# ============================================================
# 导入依赖
# ============================================================
import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量（文件不存在时静默跳过）
load_dotenv()

# ============================================================
# 配置区 —— 敏感信息从环境变量读取，其余参数在此修改
# ============================================================
DB_HOST     = os.environ.get("DB_HOST",     "192.168.40.83")
DB_PORT     = int(os.environ.get("DB_PORT", "3306"))
DB_USER     = os.environ.get("DB_USER",     "student")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME     = os.environ.get("DB_NAME",     "homework_db")

# 分析结果配置
MIN_GAMES   = 30                     # 最低场次门槛
OUTPUT_FILE = "hero_winrate.xlsx"    # 导出文件名
ANALYST     = os.environ.get("ANALYST", "潘柯岩")


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
    print("  Step 1 / 5  验证数据库连接")
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
    print("  Step 2 / 5  读取原始数据")
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
    返回的列与 analysis_log 表结构对齐（含 analyst / run_time）。
    """
    print("=" * 55)
    print("  Step 3 / 5  数据处理与统计")
    print("=" * 55)

    # ── 3-1  按英雄聚合战绩 ──────────────────────────────────
    df_stats = (
        df_battle
        .groupby("hero_id", as_index=False)
        .agg(
            total_games = ("is_win", "count"),
            win_games   = ("is_win", "sum")
        )
    )

    # ── 3-2  计算胜率（小数形式，保留4位，如 0.5234）────────
    # analysis_log.win_rate 定义为小数（0.52 表示 52%）
    df_stats["win_rate"] = (
        df_stats["win_games"] / df_stats["total_games"]
    ).round(4)

    # ── 3-3  LEFT JOIN hero 表 ───────────────────────────────
    df_merged = pd.merge(df_hero, df_stats, on="hero_id", how="left")

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

    # ── 3-6  新增 analyst 和 run_time 两列 ──────────────────
    df_result["analyst"] = ANALYST               # 分析人姓名
    df_result["run_time"] = datetime.now()        # 当前运行时间

    # ── 3-7  打印预览（胜率转成百分比显示，仅用于终端展示）─
    df_display = df_result.copy()
    df_display["win_rate_pct"] = (df_display["win_rate"] * 100).round(1).astype(str) + "%"

    print(f"✅ 满足场次门槛（>= {MIN_GAMES} 场）的英雄：{len(df_result)} 位\n")
    print(
        df_display[[
            "hero_id", "hero_name", "role",
            "total_games", "win_games", "win_rate_pct",
            "analyst", "run_time"
        ]].to_string(index=False)
    )
    print()

    return df_result


# ============================================================
# 第四步：导出 Excel + 打印统计摘要
# ============================================================
def export_and_summary(df_result: pd.DataFrame):
    """将结果导出为 Excel，并在终端打印关键统计摘要。"""
    print("=" * 55)
    print("  Step 4 / 5  导出 Excel & 统计摘要")
    print("=" * 55)

    # ── 4-1  导出 Excel（展示用，胜率转为百分比） ────────────
    df_excel = df_result.copy()
    df_excel["win_rate"] = (df_excel["win_rate"] * 100).round(1)
    df_excel = df_excel[[
        "hero_id", "hero_name", "role", "attack_type",
        "total_games", "win_games", "win_rate", "analyst", "run_time"
    ]]
    df_excel.columns = [
        "英雄ID", "英雄名称", "职业", "普攻类型",
        "总场次", "胜场数", "胜率(%)", "分析人", "运行时间"
    ]
    df_excel.to_excel(OUTPUT_FILE, index=False, sheet_name="英雄胜率")
    print(f"✅ 结果已导出：{OUTPUT_FILE}\n")

    # ── 4-2  统计摘要 ────────────────────────────────────────
    total_heroes = len(df_result)
    avg_win_rate = round(df_result["win_rate"].mean() * 100, 1)
    max_rate     = df_result["win_rate"].max()
    top_heroes   = df_result[df_result["win_rate"] == max_rate]

    print("┌─────────────────────────────────────────┐")
    print("│              📊 统计摘要                 │")
    print("├─────────────────────────────────────────┤")
    print(f"│  纳入统计英雄总数：{total_heroes:<4} 位               │")
    print(f"│  所有英雄平均胜率：{avg_win_rate:<5} %              │")
    print(f"│  胜率最高英雄：                          │")
    for _, row in top_heroes.iterrows():
        rate_pct = round(row["win_rate"] * 100, 1)
        line = f"│    · {row['hero_name']}（{row['role']}）胜率 {rate_pct}%"
        print(f"{line:<43}│")
    print("└─────────────────────────────────────────┘")
    print()


# ============================================================
# 第五步：写入 analysis_log 表，并查询所有人记录打印
# ============================================================
def write_and_read_log(df_result: pd.DataFrame):
    """
    5-1 将本次分析结果写入 analysis_log 表（append 模式）
    5-2 查询 analysis_log 全表，打印所有人的历史记录
    """
    print("=" * 55)
    print("  Step 5 / 5  写入 analysis_log & 查询全表")
    print("=" * 55)

    # ── 5-1  整理待写入的 DataFrame，列名须与数据库字段完全一致 ──
    df_to_write = df_result[[
        "hero_id",
        "hero_name",
        "total_games",
        "win_games",
        "win_rate",
        "analyst",
        "run_time"
    ]].copy()

    # log_id 为自增主键，不需要写入，pandas 会自动跳过不存在的列

    # ── 5-2  写入数据库 ──────────────────────────────────────
    engine = get_engine()
    try:
        df_to_write.to_sql(
            name      = "analysis_log",   # 目标表名
            con       = engine,
            if_exists = "append",         # 追加写入，不覆盖历史数据
            index     = False,            # 不把 DataFrame 行号写进去
            chunksize = 500               # 分批写入，防止单次数据量过大
        )
        print(f"✅ 成功写入 {len(df_to_write)} 条记录到 analysis_log 表\n")
    except SQLAlchemyError as e:
        print(f"[错误] 写入失败：{e}")
        raise

    # ── 5-3  查询 analysis_log 全表，打印所有人的历史记录 ────
    sql_read_log = """
        SELECT
            log_id,
            hero_id,
            hero_name,
            total_games,
            win_games,
            ROUND(win_rate * 100, 1)  AS win_rate_pct,
            analyst,
            run_time
        FROM analysis_log
        ORDER BY run_time DESC, hero_id ASC
    """
    df_log = query_to_df(sql_read_log)

    # 重命名列，终端显示更友好
    df_log.columns = [
        "日志ID", "英雄ID", "英雄名称",
        "总场次", "胜场数", "胜率(%)",
        "分析人", "运行时间"
    ]

    print(f"📋 analysis_log 表当前共 {len(df_log)} 条记录（所有人）：\n")
    print(df_log.to_string(index=False))
    print()


# ============================================================
# 主流程入口
# ============================================================
if __name__ == "__main__":

    try:
        verify_connection()                       # Step 1：验证连接
        df_hero, df_battle = load_data()          # Step 2：读取数据
        df_result = process_data(df_hero,         # Step 3：处理数据
                                 df_battle)
        export_and_summary(df_result)             # Step 4：导出 + 摘要
        write_and_read_log(df_result)             # Step 5：写库 + 回读

    except Exception as e:
        print(f"\n❌ 程序异常终止：{e}")
