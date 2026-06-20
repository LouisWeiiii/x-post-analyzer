# X Post Analyzer 🔬

把 X（Twitter）推文数据 CSV 扔进来，自动分类对比——**只摊数据，不做诊断**。

## 能告诉你什么

### 4 张基础对比表
- 什么方向涨粉/不涨粉
- 回复帖占了多少曝光、涨了几个粉
- 涨粉效率排行榜
- 发帖方向分布（时间到底花在哪了）

### 11 维内容 DNA 分析
| 维度 | 问题 |
|------|------|
| 人称 | 「我」vs「你」vs 中性，哪种涨粉多？ |
| 数字 | 带数字的推文数据差多少？ |
| 长度 | 1-3行 vs 4-5行 vs 6行+，哪个好？ |
| 开头 | 反常识/故事/结论/提问/数据开场，哪种曝光高？ |
| 高频词 | 哪个词跟涨粉关联最强？Top 10 |
| 写作指纹 | 每个方向用「我」还是「你」、带数字比例、emoji率 |
| Emoji | 带 vs 不带，差多少？哪个 emoji 涨粉最强？ |
| 互动深度 | 点赞率按方向分组——高曝光低互动 vs 高互动低曝光 |
| 时段 | 周几发推数据最好？ |
| 爆款连锁 | 一条爆款能不能带动后续？ |
| 句式 | 问句/感叹句/陈述句，哪种效果好？ |

### 可选：定位 vs 现实
提供你的账号定位（如"搞钱50%+AI30%+成长20%"），自动对比**你声称的**和**数据说的**差多远。

### 互动指标（有数据则自动纳入）
回复率 / 转发率 / 书签率 按方向分组。

---

## 使用方法

### 1. 从 X 导出数据
X Premium → Analytics → 导出 CSV

### 2. 一行代码分析

```python
import csv
from analyze import analyze

with open('your_x_data.csv', encoding='utf-8') as f:
    posts = list(csv.DictReader(f))

analyze(posts)
```

带定位的分析：

```python
from analyze import analyze_with_positioning

positioning = [
    {'name': '搞钱/商业', 'target': 50, 'keywords': ['搞钱', '赚钱']},
    {'name': 'AI/工具', 'target': 30, 'keywords': ['ai', '技术']},
    {'name': '个人成长', 'target': 20, 'keywords': ['认知', '观点']},
]

with open('your_x_data.csv', encoding='utf-8') as f:
    posts = list(csv.DictReader(f))

analyze_with_positioning(posts, positioning)
```

### 3. CSV 格式要求

**必需列**（列名自动识别，中英文都行）：
- 正文：`Post text` / `Content` / `Tweet text` / `正文`
- 曝光：`Impressions` / `Views` / `曝光`

**可选列**（有则分析，无则跳过）：
- 涨粉：`New follows` / `Follows` / `涨粉`
- 点赞：`Likes` / `赞`
- 回复/转发/书签/日期

---

## 原则

- **只对比，不诊断**。不写"你应该减少回复"。只写"回复帖占55%，涨粉0"。
- **数字即观点**。涨粉效率 0.10 vs 0.00，不需要解释。
- **中立语言**。不用"你的时间花在哪了"，用"发帖方向分布"。

---

## License

MIT
