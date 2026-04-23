import pandas as pd

# 定义要诊断的文件名
file_name = "Hero.csv"

print(f"========== 正在诊断文件: {file_name} ==========\n")

try:
    # --- 诊断方法1: 打印原始字节内容 ---
    # 这会显示所有“看不见”的字符，比如不同的换行符 (\n, \r\n) 和分隔符
    print("--- 诊断1: 打印文件前5行的原始字节表示 ---")
    with open(file_name, 'rb') as f:
        for i in range(5):
            try:
                line_bytes = next(f)
                print(f"第 {i+1} 行: {repr(line_bytes)}")
            except StopIteration:
                break
    print("-" * 20)

    # --- 诊断方法2: 尝试用Python原生方式读取 ---
    # 这可以验证文件的编码和换行是否能被Python正确识别
    print("\n--- 诊断2: 尝试用Python原生方式按行读取 ---")
    with open(file_name, 'r', encoding='utf-8') as f:
        for i in range(5):
            try:
                line_text = next(f)
                print(f"第 {i+1} 行: {line_text.strip()}")
            except StopIteration:
                break
            except UnicodeDecodeError:
                print(f"错误：文件 '{file_name}' 不是一个标准的 UTF-8 编码文件！")
                break
    print("-" * 20)


    # --- 诊断方法3: 让Pandas猜测分隔符 ---
    # 看看在最简单的情况下，Pandas识别出的分隔符是什么
    print("\n--- 诊断3: 让Pandas自动猜测分隔符 (仅读取前5行) ---")
    try:
        df_guess = pd.read_csv(file_name, sep=None, engine='python', header=None, nrows=5)
        print("Pandas读取成功，以下是DataFrame的列：")
        print(df_guess.columns)
        print("\n以下是读取到的数据预览：")
        print(df_guess.head())
    except Exception as e:
        print(f"Pandas在猜测分隔符时失败: {e}")

    print("\n========== 诊断结束 ==========")
    print("请将以上所有输出信息提供给我进行分析。")


except FileNotFoundError:
    print(f"错误：找不到文件 '{file_name}'，请确保它和脚本在同一个目录下。")
except Exception as e:
    print(f"发生了未知错误: {e}")

