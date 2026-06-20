---
name: x-post-analyzer
description: 把 X（Twitter）推文数据 CSV 扔进来，自动分类并对比——只把数据摊开，不做诊断建议。11维DNA分析+定位检测+互动指标。
---

# X Post Analyzer

把 X Analytics 导出的 CSV 扔进来，自动跑完整分析。不给你建议——只把数字摊开，让你自己看。

## 触发条件

当用户说以下任意关键词时使用本 skill：
- "分析我的X数据" / "分析推文数据" / "看下我的X数据"
- "对比推文" / "涨粉分析" / "内容方向分析"
- 用户上传或指定了一个 X Analytics CSV 文件

## 输入

用户需要提供一个 X Analytics 导出的 CSV 文件路径。CSV 至少需要包含正文列和曝光列。

**列名自动识别**，中英文都支持：
- 正文：`Post text` / `Content` / `Tweet text` / `正文`
- 曝光：`Impressions` / `Views` / `曝光`
- 涨粉（可选）：`New follows` / `Follows` / `涨粉`
- 点赞（可选）：`Likes` / `赞`
- 日期（可选）：`Date` / `Post date` / `日期`
- 回复/转发/书签（可选）：有则自动纳入对应分析，无则跳过

## 执行方式

**首先检查 analyze.py 是否存在**，按以下优先级查找：
1. 与本 SKILL.md 同目录下的 `analyze.py`
2. 用户指定的路径
3. 当前工作目录下的 `x-post-analyzer/analyze.py`

找到后，用 Python 执行：

```python
import csv, sys
sys.path.insert(0, '/path/to/x-post-analyzer')
from analyze import analyze

with open('/path/to/data.csv', encoding='utf-8') as f:
    posts = list(csv.DictReader(f))

analyze(posts)
```

也可以直接用命令行（如果 analyze.py 在当前目录）：

```bash
python3 analyze.py /path/to/data.csv
```

## 如果用户提供了账号定位

用户可能会说类似这样的话：
- "我的定位是搞钱50%+AI30%+个人成长20%"
- "账号定位：AI工具 40%，副业 30%，认知 30%"

此时使用 `analyze_with_positioning` 代替 `analyze`：

```python
from analyze import analyze_with_positioning

positioning = [
    {'name': '搞钱/商业', 'target': 50, 'keywords': ['搞钱', '副业', '赚钱', '商业']},
    {'name': 'AI/技术', 'target': 30, 'keywords': ['ai', '技术']},
    {'name': '个人成长', 'target': 20, 'keywords': ['认知', '成长', '观点']},
]

with open('/path/to/data.csv', encoding='utf-8') as f:
    posts = list(csv.DictReader(f))

analyze_with_positioning(posts, positioning)
```

定位方向的数量和名称根据用户原话调整，每个方向的 `keywords` 用最核心的 3-4 个词即可。

## 输出内容

分析会输出以下内容（按顺序），**直接展示给用户，不要总结、不要追加建议**：

1. 列识别结果（识别到哪些列、缺失了哪些列）
2. 表 1：按内容方向对比（方向/条数/占比/均曝光/均涨粉/总涨粉）
3. 表 2：回复帖真相（回复帖占比/曝光/涨粉/TOP10统计）
4. 表 3：涨粉效率排行榜（带可视化 bar）
5. 表 4：发帖方向分布（时间花在哪些方向）
6. 最佳推文 TOP5（涨粉最多的 5 条原文片段）
7. 表 5：内容 DNA 分析（11 个维度）
   - 人称分析、数字密度、推文长度、开头风格
   - 高频词 × 涨粉关联 Top 10
   - 写作指纹（按方向拆解）
   - Emoji 分析、互动深度、发文时段、爆款连锁、句式结构
   - 回复率/转发率/书签率（如果 CSV 有这些列）
8. 表 6-7：定位分析（如果用户提供了定位）

## 内容分类规则

脚本按以下规则自动分类每条推文（优先级从上到下）：

| 方向 | 判断规则 |
|------|---------|
| 回复互动 | 以 `@` 开头 |
| 长文/链接 | 以 `http` 开头 |
| 搞钱/商业 | 包含：赚钱、搞钱、副业、变现、月入、收入、付费、创业、生意、客户、利润、薪资、成本、现金流、卖课、知识付费、一人公司、自由职业、接单、睡后收入、被动收入、财务自由、暴利 |
| AI/技术 | 包含：claude、chatgpt、gpt-、deepseek、agent、提示词、大模型、skill、codex、编程、代码、api、开源、cursor、windsurf、ai编程、ai写作、ai工具、llm、机器学习、深度学习、神经网络 |
| 认知/观点 | 包含：人生、努力、选择、焦虑、自由、格局、教育、学历、后悔、认知、底层逻辑、思维方式、长期主义、复利、延迟满足 |
| 泛流量/生活 | 以上都不匹配 |

**如果用户想自定义分类**，告诉他们在 `analyze.py` 的 `classify_post()` 函数里修改 `categories` 字典即可。

## 重要原则

- **不要追加任何主观建议或诊断**。脚本输出什么就展示什么，不要在末尾加"你应该…""建议…""下一步…"。
- **输出用中文**。脚本输出本身就是中文，不要翻译成英文。
- **如果脚本报错**，告诉用户具体错误信息，不要说"分析完成"。
- **如果 CSV 缺少必需列**，脚本自己会打印警告，直接展示给用户即可。

## 如果没有找到 analyze.py

如果三个路径都找不到 `analyze.py`，告诉用户：
"需要下载 analyze.py 放到 SKILL.md 同目录下。下载地址：https://github.com/LouisWeiiii/x-post-analyzer"

不要自己写一个——直接用仓库里的版本。
