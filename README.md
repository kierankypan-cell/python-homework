# README.md

```markdown
# 英雄信息管理系统 API 文档

## 环境依赖

```bash
pip install fastapi uvicorn pandas
```

## 启动服务

**方式一：直接运行 Python 文件**

在 `main.py` 末尾确认包含以下代码后，点击 VSCode 运行按钮或执行：

```bash
python main.py
```

**方式二：命令行启动**

```bash
# 使用默认数据文件路径（./英雄信息.csv）
uvicorn main:app --reload

# 自定义数据文件路径
HERO_FILE_PATH=./data/英雄信息.csv uvicorn main:app --reload  # Mac/Linux
set HERO_FILE_PATH=./data/英雄信息.csv && uvicorn main:app --reload  # Windows
```

启动成功后，服务运行于：`http://127.0.0.1:8000`

> 在线接口调试页面：`http://127.0.0.1:8000/docs`

---

## 接口说明

### 1. 列表查询

> 输入任意关键词，在英雄ID、英雄名称、职业三列中模糊匹配，返回所有符合条件的英雄信息。

| 项目 | 内容 |
|------|------|
| 路由 | `POST /hero/search` |
| Content-Type | `application/json` |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | ✅ | 查询关键词，可输入英雄ID、英雄名称或职业 |

**请求示例**

```json
{
  "keyword": "射手"
}
```

**返回示例（有匹配数据）**

```json
{
  "count": 1,
  "results": [
    {
      "英雄ID": 1,
      "英雄名称": "弥亚",
      "职业": "射手"
    }
  ]
}
```

**返回示例（无匹配数据）**

```json
{
  "count": 0,
  "results": []
}
```

---

### 2. 按 ID 查单个英雄

> 输入英雄ID，返回该英雄的完整信息；查不到时返回 404。

| 项目 | 内容 |
|------|------|
| 路由 | `POST /hero/detail` |
| Content-Type | `application/json` |

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hero_id | integer | ✅ | 英雄ID，必须为正整数 |

**请求示例**

```json
{
  "hero_id": 1
}
```

**返回示例（找到）**

```json
{
  "英雄ID": 1,
  "英雄名称": "弥亚",
  "职业": "射手"
}
```

**返回示例（未找到，HTTP 404）**

```json
{
  "detail": {
    "error": "未找到 英雄ID 为 99 的英雄，请确认ID是否正确。"
  }
}
```

---

### 3. 职业统计

> 统计每个职业下的英雄数量，按数量从多到少排序返回。

| 项目 | 内容 |
|------|------|
| 路由 | `POST /hero/profession/stats` |
| Content-Type | `application/json` |

**请求参数**

无需传入参数，请求体传空 JSON 对象即可。

**请求示例**

```json
{}
```

**返回示例**

```json
{
  "total": 2,
  "stats": [
    {"职业": "射手", "英雄数量": 1},
    {"职业": "战士", "英雄数量": 1}
  ]
}
```

---

## 异常返回说明

| HTTP 状态码 | 触发场景 | 返回格式 |
|------------|---------|---------|
| `404` | 按ID查询时，英雄ID不存在 | `{"detail": {"error": "错误说明"}}` |
| `422` | 请求参数类型错误或不符合校验规则 | FastAPI 自动返回校验错误详情 |
| `500` | 服务内部异常（如数据文件未加载） | `{"detail": {"error": "错误说明"}}` |

---

## 调用方示例

```python
import requests

BASE_URL = "http://127.0.0.1:8000"

# 列表查询
requests.post(f"{BASE_URL}/hero/search", json={"keyword": "射手"})

# 按ID查询
requests.post(f"{BASE_URL}/hero/detail", json={"hero_id": 1})

# 职业统计
requests.post(f"{BASE_URL}/hero/profession/stats", json={})
```
```