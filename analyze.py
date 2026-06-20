# X Post Analyzer — 可复用分析脚本 v3.0
# 列名自动识别 · 11 DNA 维度 · TOP5 展示 · 互动指标 · 中立语言

import csv, re
from collections import defaultdict, Counter
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════
#  列名自动识别（兼容不同 X Analytics 导出格式）
# ═══════════════════════════════════════════════════

COLUMN_ALIASES = {
    '_text':       ['post text', 'post', 'content', 'tweet text', 'tweet', 'text', '正文'],
    '_imp':        ['impressions', 'views', 'impressions (organic)', '曝光', '展示'],
    '_follows':    ['new follows', 'follows', 'new followers', 'followers gained', '涨粉', '新增关注'],
    '_likes':      ['likes', 'favorites', 'hearts', '赞', '点赞'],
    '_replies':    ['replies', 'comments', 'reply count', '回复', '评论'],
    '_reposts':    ['reposts', 'retweets', 'retweets (organic)', 'shares', '转发'],
    '_bookmarks':  ['bookmarks', 'saves', '书签', '收藏'],
    '_date':       ['date', 'post date', 'created', 'timestamp', 'time', '日期', '发布时间'],
}


def normalize_columns(posts):
    """
    自动识别 CSV 列名，映射到标准字段。
    返回 (posts_with_mapped_cols, available_fields, warnings)
    """
    if not posts:
        return posts, set(), ["⚠ 空数据：CSV 中没有记录"]

    raw_cols = [c.lower().strip() for c in posts[0].keys()]
    mapping = {}  # standard_key -> raw_csv_key
    available = set()
    warnings = []

    for std_key, aliases in COLUMN_ALIASES.items():
        for raw_key in posts[0].keys():
            if raw_key.lower().strip() in aliases:
                mapping[std_key] = raw_key
                available.add(std_key)
                break

    # 检查必需字段
    if '_text' not in available:
        warnings.append("⚠ 缺少推文正文列（需要 Post text/Content 等列）")
    if '_imp' not in available:
        warnings.append("⚠ 缺少曝光列（需要 Impressions/Views 等列）")

    # 检查推荐字段
    optional_missing = []
    if '_follows' not in available:
        optional_missing.append("涨粉数据")
    if '_likes' not in available:
        optional_missing.append("点赞数据")
    if optional_missing:
        warnings.append(f"ℹ 缺少可选列：{', '.join(optional_missing)}，相关分析将跳过")

    # 映射数据到标准字段
    for p in posts:
        for std_key, raw_key in mapping.items():
            if std_key in available:
                p[std_key] = p.get(raw_key, '')

    return posts, available, warnings


# ═══════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════

def has_emoji(text):
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U00002460-\U000024FF"
        "\U0001F100-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U0000FE00-\U0000FE0F"
        "\U0000200D"
        "]+", flags=re.UNICODE)
    return bool(emoji_pattern.search(str(text)))


def extract_emojis(text):
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U00002460-\U000024FF"
        "\U0001F100-\U0001F251\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF\U00002600-\U000026FF]+", flags=re.UNICODE)
    return emoji_pattern.findall(str(text))


def has_numbers(text):
    digits = re.findall(r'\d+', str(text))
    return any(len(d) >= 2 for d in digits)


def person_type(text):
    text = str(text).lower()
    first_sent = text.split('\n')[0].lower()
    wo = first_sent.count('我')
    ni = first_sent.count('你')
    if wo > ni and wo > 0:
        return '我'
    elif ni > wo and ni > 0:
        return '你'
    else:
        return '中性'


def text_lines(text):
    return len([l for l in str(text).split('\n') if l.strip()])


def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y',
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def safe_int(val):
    """安全取整，空值返回 0"""
    try:
        return int(float(str(val).replace(',', '')))
    except (ValueError, TypeError):
        return 0


# ═══════════════════════════════════════════════════
#  分类系统 v2
# ═══════════════════════════════════════════════════

def classify_post(text):
    text_raw = str(text)
    text_lower = text_raw.lower()

    if text_raw.strip().startswith('@'):
        return '回复互动'
    if text_raw.strip().startswith('http'):
        return '长文/链接'

    categories = {
        '搞钱/商业': [
            '赚钱', '搞钱', '副业', '变现', '月入', '收入', '付费',
            '创业', '生意', '客户', '利润', '薪资', '成本', '现金流',
            '卖课', '知识付费', '一人公司', '自由职业', '接单',
            '睡后收入', '被动收入', '财务自由', '暴利',
        ],
        'AI/技术': [
            'claude', 'chatgpt', 'gpt-', 'deepseek', 'agent',
            '提示词', '大模型', '大语言模型', 'skill', 'codex',
            '编程', '代码', 'api', '开源', 'cursor', 'windsurf',
            'ai编程', 'ai写作', 'ai工具', 'ai agent', 'llm',
            '机器学习', '深度学习', '神经网络',
        ],
        '认知/观点': [
            '人生', '努力', '选择', '焦虑', '自由', '格局',
            '教育', '学历', '后悔', '认知', '底层逻辑',
            '思维方式', '长期主义', '复利', '延迟满足',
        ],
    }

    for cat, kws in categories.items():
        if any(kw in text_lower for kw in kws):
            return cat
    return '泛流量/生活'


def opening_style(text):
    text = str(text).strip()
    first = text.split('\n')[0].split('。')[0].strip().lower()
    if not first:
        return '其他'
    if any(w in first for w in ['不是', '其实', '真相', '骗', '错觉', '没人告诉', '你以为']):
        return '反常识/颠覆'
    if any(w in first for w in ['昨天', '今天', '上周', '刚才', '晚上', '早上', '刚', '最近']):
        return '场景/故事'
    if any(w in first for w in ['最', '永远', '从来', '所有', '每个人', '唯一']):
        return '结论/判断'
    if '？' in first or '?' in first:
        return '提问/悬念'
    if any(c.isdigit() for c in first) and len([c for c in first if c.isdigit()]) >= 2:
        return '数据开场'
    return '陈述/观点'


# ═══════════════════════════════════════════════════
#  新增 v3.0: 最佳推文 TOP5
# ═══════════════════════════════════════════════════

def top_tweets(posts, available, n=5):
    """展示涨粉最多的 N 条推文原文"""
    if '_follows' not in available:
        return

    non_reply = [p for p in posts
                 if not str(p.get('_text', '')).startswith('@')
                 and not str(p.get('_text', '')).startswith('http')]
    if not non_reply:
        return

    top = sorted(non_reply, key=lambda p: safe_int(p.get('_follows', 0)), reverse=True)[:n]

    print(f"\n── 涨粉最强 TOP{n} 推文 ──")
    for i, p in enumerate(top, 1):
        text = str(p.get('_text', '')).replace('\n', '\\n')[:120]
        follows = safe_int(p.get('_follows', 0))
        imp = safe_int(p.get('_imp', 0))
        likes = safe_int(p.get('_likes', 0))
        cat = classify_post(p.get('_text', ''))
        print(f"  #{i} [{cat}] 涨粉{follows}  曝光{imp:,}  赞{likes}")
        print(f"     \"{text}{'...' if len(str(p.get('_text', ''))) > 120 else ''}\"")
        print()


# ═══════════════════════════════════════════════════
#  新增 v3.0: 互动指标（回复率/转发率/书签率）
# ═══════════════════════════════════════════════════

def engagement_metrics(posts, available):
    """分析回复率、转发率、书签率（按方向分组）"""
    metrics_available = [k for k in ['_replies', '_reposts', '_bookmarks'] if k in available]
    if not metrics_available:
        return

    metric_labels = {
        '_replies':   ('回复率', '回复/曝光'),
        '_reposts':   ('转发率', '转发/曝光'),
        '_bookmarks': ('书签率', '书签/曝光'),
    }

    non_reply = [p for p in posts
                 if not str(p.get('_text', '')).startswith('@')
                 and not str(p.get('_text', '')).startswith('http')]
    if len(non_reply) < 5:
        return

    for col_key in metrics_available:
        label, ratio_label = metric_labels[col_key]

        cat_data = defaultdict(lambda: {'count': 0, 'total_val': 0, 'total_imp': 0})

        for p in non_reply:
            cat = classify_post(p.get('_text', ''))
            val = safe_int(p.get(col_key, 0))
            imp = safe_int(p.get('_imp', 0))
            if imp > 0:
                cat_data[cat]['count'] += 1
                cat_data[cat]['total_val'] += val
                cat_data[cat]['total_imp'] += imp

        # 至少 2 个方向有数据才显示
        active_cats = [cat for cat, d in cat_data.items() if d['count'] >= 2]
        if len(active_cats) < 1:
            continue

        print(f"\n📌 {label}（{ratio_label}）")
        print(f"  {'方向':<14} {'条数':>4} {'总数':>6} {'比率':>7}  {'分布'}")
        print(f"  {'─'*14} {'─'*4} {'─'*6} {'─'*7}  {'─'*20}")

        max_rate = max(
            d['total_val'] / max(d['total_imp'], 1) for cat, d in cat_data.items()
        ) or 1

        for cat, d in sorted(cat_data.items(),
                             key=lambda x: x[1]['total_val'] / max(x[1]['total_imp'], 1),
                             reverse=True):
            if d['count'] < 1:
                continue
            rate = d['total_val'] / max(d['total_imp'], 1) * 100
            bar_len = int(rate / max(max_rate, 1) * 20)
            bar = '█' * bar_len
            print(f"  {cat:<14} {d['count']:>4} {d['total_val']:>6} {rate:>6.2f}%  {bar}")


# ═══════════════════════════════════════════════════
#  DNA 维度 (7-11)
# ═══════════════════════════════════════════════════

def emoji_analysis(posts, available):
    if len(posts) < 5:
        return

    print("\n📌 Emoji 使用分析")

    emoji_data = {'with': {'count': 0, 'total_imp': 0, 'total_follows': 0, 'total_likes': 0},
                  'without': {'count': 0, 'total_imp': 0, 'total_follows': 0, 'total_likes': 0}}
    emoji_stats = defaultdict(lambda: {'count': 0, 'total_imp': 0, 'total_follows': 0})

    for p in posts:
        text = str(p.get('_text', ''))
        imp = safe_int(p.get('_imp', 0))
        follows = safe_int(p.get('_follows', 0))
        likes = safe_int(p.get('_likes', 0))

        key = 'with' if has_emoji(text) else 'without'
        emoji_data[key]['count'] += 1
        emoji_data[key]['total_imp'] += imp
        emoji_data[key]['total_follows'] += follows
        emoji_data[key]['total_likes'] += likes

        for e in set(extract_emojis(text)):
            emoji_stats[e]['count'] += 1
            emoji_stats[e]['total_imp'] += imp
            emoji_stats[e]['total_follows'] += follows

    for k, label in [('with', '带 emoji'), ('without', '不带 emoji')]:
        d = emoji_data[k]
        if d['count'] > 0:
            print(f"  {label}: {d['count']}条  均曝光 {d['total_imp']/d['count']:.0f}  均涨粉 {d['total_follows']/d['count']:.2f}  均赞 {d['total_likes']/d['count']:.1f}")

    top_emoji = sorted(emoji_stats.items(), key=lambda x: x[1]['total_follows']/max(x[1]['count'],1), reverse=True)[:5]
    if top_emoji:
        print("  涨粉最强 emoji Top 5:")
        for e, s in top_emoji:
            if s['count'] >= 2:
                print(f"    {e} ({s['count']}次): 均涨粉 {s['total_follows']/s['count']:.2f}")


def engagement_rate_analysis(posts, available):
    if len(posts) < 5:
        return

    print("\n📌 互动深度（点赞率 = 赞/曝光 × 100）")

    cat_eng = defaultdict(lambda: {'count': 0, 'total_likes': 0, 'total_imp': 0, 'total_follows': 0})
    overall_avg_imp = sum(safe_int(p.get('_imp', 0)) for p in posts) / max(len(posts), 1)

    for p in posts:
        cat = classify_post(p.get('_text', ''))
        cat_eng[cat]['count'] += 1
        cat_eng[cat]['total_likes'] += safe_int(p.get('_likes', 0))
        cat_eng[cat]['total_imp'] += safe_int(p.get('_imp', 0))
        cat_eng[cat]['total_follows'] += safe_int(p.get('_follows', 0))

    print(f"  {'方向':<14} {'条数':>4} {'点赞率':>7} {'均涨粉':>7}  {'诊断'}")
    print(f"  {'─'*14} {'─'*4} {'─'*7} {'─'*7}  {'─'*20}")

    for cat, d in sorted(cat_eng.items(), key=lambda x: x[1]['total_likes']/max(x[1]['total_imp'],1), reverse=True):
        like_rate = d['total_likes'] / max(d['total_imp'], 1) * 100
        avg_follows = d['total_follows'] / max(d['count'], 1)
        avg_imp = d['total_imp'] / max(d['count'], 1)

        if like_rate > 3:
            diag = '🔥 高互动'
        elif like_rate < 0.5:
            diag = '💤 低互动'
        else:
            diag = '➖ 中等'

        if avg_imp > overall_avg_imp * 1.3:
            diag += ' · 高曝光'
        elif avg_imp < overall_avg_imp * 0.7:
            diag += ' · 低曝光'

        if d['count'] >= 2:
            print(f"  {cat:<14} {d['count']:>4} {like_rate:>6.1f}% {avg_follows:>7.2f}  {diag}")


def time_analysis(posts, available):
    if '_date' not in available:
        print("\n📌 发文时段：无日期列，跳过")
        return

    dated = []
    for p in posts:
        dt = parse_date(p.get('_date', ''))
        if dt:
            dated.append({**p, '_dt': dt})

    if len(dated) < 7:
        print("\n📌 发文时段：日期数据不足（需要 ≥7 条），跳过")
        return

    print("\n📌 发文时段（星期几）")

    WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    day_data = defaultdict(lambda: {'count': 0, 'total_imp': 0, 'total_follows': 0, 'total_likes': 0})

    for p in dated:
        wd = p['_dt'].weekday()
        day_data[wd]['count'] += 1
        day_data[wd]['total_imp'] += safe_int(p.get('_imp', 0))
        day_data[wd]['total_follows'] += safe_int(p.get('_follows', 0))
        day_data[wd]['total_likes'] += safe_int(p.get('_likes', 0))

    print(f"  {'星期':<6} {'条数':>4} {'占比':>6} {'均曝光':>8} {'均涨粉':>7} {'均赞':>6}")
    print(f"  {'─'*6} {'─'*4} {'─'*6} {'─'*8} {'─'*7} {'─'*6}")

    for wd in range(7):
        d = day_data[wd]
        if d['count'] > 0:
            pct = d['count'] / len(dated) * 100
            print(f"  {WEEKDAYS[wd]:<6} {d['count']:>4} {pct:>5.0f}% {d['total_imp']/d['count']:>8.0f} {d['total_follows']/d['count']:>7.2f} {d['total_likes']/d['count']:>6.0f}")


def viral_chain_analysis(posts, available):
    if '_date' not in available:
        print("\n📌 爆款连锁：无日期列，跳过")
        return

    dated = []
    for p in posts:
        dt = parse_date(p.get('_date', ''))
        if dt:
            dated.append({**p, '_dt': dt, '_imp_val': safe_int(p.get('_imp', 0))})

    if len(dated) < 10:
        print("\n📌 爆款连锁：数据不足（需要 ≥10 条），跳过")
        return

    dated.sort(key=lambda x: x['_dt'])
    imps = [p['_imp_val'] for p in dated]
    mean_imp = sum(imps) / len(imps)
    threshold = max(mean_imp * 2, sorted(imps, reverse=True)[max(1, len(imps)//5)])

    viral_posts = [p for p in dated if p['_imp_val'] >= threshold]
    if not viral_posts:
        print("\n📌 爆款连锁：无爆款（阈值过高），跳过")
        return

    viral_times = {p['_dt'] for p in viral_posts}

    ripple_imps, ripple_follows = [], []
    non_ripple_imps, non_ripple_follows = [], []

    for p in dated:
        is_ripple = any(timedelta(hours=0) < (p['_dt'] - vt) <= timedelta(hours=24)
                       for vt in viral_times)
        if is_ripple and p['_dt'] not in viral_times:
            ripple_imps.append(p['_imp_val'])
            ripple_follows.append(safe_int(p.get('_follows', 0)))
        elif p['_dt'] not in viral_times:
            non_ripple_imps.append(p['_imp_val'])
            non_ripple_follows.append(safe_int(p.get('_follows', 0)))

    print(f"\n📌 爆款连锁效应")
    print(f"  爆款阈值: 均曝光 ≥ {threshold:.0f}")
    print(f"  爆款推文: {len(viral_posts)} 条")

    if ripple_imps:
        avg_r_imp = sum(ripple_imps) / len(ripple_imps)
        avg_r_fol = sum(ripple_follows) / len(ripple_follows)
        avg_n_imp = sum(non_ripple_imps) / len(non_ripple_imps) if non_ripple_imps else 0
        avg_n_fol = sum(non_ripple_follows) / len(non_ripple_follows) if non_ripple_follows else 0

        print(f"  爆款后24h ({len(ripple_imps)}条):  均曝光 {avg_r_imp:.0f}  均涨粉 {avg_r_fol:.2f}")
        print(f"  普通推文   ({len(non_ripple_imps)}条):  均曝光 {avg_n_imp:.0f}  均涨粉 {avg_n_fol:.2f}")

        if avg_n_imp > 0:
            lift = (avg_r_imp / avg_n_imp - 1) * 100
            if lift > 20:
                print(f"  🔥 爆款有显著带动效应：后续曝光提升 {lift:.0f}%")
            elif lift > 5:
                print(f"  📈 爆款有轻微带动：后续曝光提升 {lift:.0f}%")
            else:
                print(f"  ➖ 无明显连锁效应：各条推文表现相对独立")
    else:
        print("  无后续推文可分析（爆款可能都在数据末尾）")


def sentence_analysis(posts, available):
    if len(posts) < 5:
        return

    print("\n📌 句式结构")

    question_data = {'count': 0, 'total_imp': 0, 'total_follows': 0}
    exclaim_data = {'count': 0, 'total_imp': 0, 'total_follows': 0}
    normal_data = {'count': 0, 'total_imp': 0, 'total_follows': 0}
    sentence_lengths = []

    for p in posts:
        text = str(p.get('_text', '')).strip()
        imp = safe_int(p.get('_imp', 0))
        follows = safe_int(p.get('_follows', 0))

        sentences = re.split(r'[。.！!？?\n]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            sentence_lengths.append(sum(len(s) for s in sentences) / len(sentences))

        is_question = text.endswith('？') or text.endswith('?')
        has_exclaim = '！' in text or '!' in text

        if is_question:
            question_data['count'] += 1
            question_data['total_imp'] += imp
            question_data['total_follows'] += follows
        if has_exclaim:
            exclaim_data['count'] += 1
            exclaim_data['total_imp'] += imp
            exclaim_data['total_follows'] += follows
        if not is_question and not has_exclaim:
            normal_data['count'] += 1
            normal_data['total_imp'] += imp
            normal_data['total_follows'] += follows

    total = len(posts)
    print(f"  {'句式':<10} {'条数':>4} {'占比':>6} {'均曝光':>8} {'均涨粉':>7}")
    print(f"  {'─'*10} {'─'*4} {'─'*6} {'─'*8} {'─'*7}")

    for label, d in [('问句结尾', question_data), ('含感叹号', exclaim_data), ('陈述句', normal_data)]:
        if d['count'] > 0:
            pct = d['count'] / total * 100
            print(f"  {label:<10} {d['count']:>4} {pct:>5.0f}% {d['total_imp']/d['count']:>8.0f} {d['total_follows']/d['count']:>7.2f}")

    if sentence_lengths:
        avg_sl = sum(sentence_lengths) / len(sentence_lengths)
        print(f"  平均句长: {avg_sl:.0f} 字符/句")


# ═══════════════════════════════════════════════════
#  高频词关联
# ═══════════════════════════════════════════════════

def word_correlation(posts):
    non_reply = [p for p in posts if not str(p.get('_text', '')).startswith('@')]
    if not non_reply:
        return {}

    word_stats = defaultdict(lambda: {'count': 0, 'total_imp': 0, 'total_follows': 0})

    for p in non_reply:
        text = str(p.get('_text', ''))
        imp = safe_int(p.get('_imp', 0))
        follows = safe_int(p.get('_follows', 0))

        keywords = set()
        for m in re.finditer(r'[\u4e00-\u9fff]{2,4}', text):
            keywords.add(m.group())
        for m in re.finditer(r'[a-zA-Z]{3,}', text):
            keywords.add(m.group().lower())

        for kw in keywords:
            word_stats[kw]['count'] += 1
            word_stats[kw]['total_imp'] += imp
            word_stats[kw]['total_follows'] += follows

    stopwords = {
        '一个', '这个', '那个', '什么', '怎么', '为什么', '可以', '但是', '因为',
        '所以', '如果', '虽然', '而且', '还是', '或者', '没有', '已经', '不是',
        '就是', '都是', '不会', '不能', '不要', '只是', '很多', '自己',
        '他们', '我们', '你们', '知道', '觉得', '可能', '应该',
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'are',
    }

    results = {}
    for kw, stats in word_stats.items():
        if kw.lower() in stopwords or stats['count'] < 3:
            continue
        results[kw] = {
            'count': stats['count'],
            'avg_imp': stats['total_imp'] / stats['count'],
            'avg_follows': stats['total_follows'] / stats['count'],
        }
    return results


# ═══════════════════════════════════════════════════
#  核心分析
# ═══════════════════════════════════════════════════

def dna_analysis(posts, available):
    """表 5: 内容 DNA 分析 — 11 个维度（+ v3.0 新增互动指标）"""
    non_reply = [p for p in posts
                 if not str(p.get('_text', '')).startswith('@')
                 and not str(p.get('_text', '')).startswith('http')]

    if len(non_reply) < 10:
        print("\n🔬 表 5: 内容 DNA 分析")
        print("  ⚠ 非回复帖不足10条，DNA分析跳过（样本太小）")
        return

    sep = "\n" + "─" * 56
    print(f"{sep}\n🔬 表 5: 内容 DNA 分析{sep}")

    # ── 1. 人称分析 ──
    print("\n📌 人称分析（我 vs 你 vs 中性）")
    person_data = defaultdict(lambda: {'count': 0, 'total_imp': 0, 'total_follows': 0, 'total_likes': 0})
    for p in non_reply:
        pt = person_type(p.get('_text', ''))
        person_data[pt]['count'] += 1
        person_data[pt]['total_imp'] += safe_int(p.get('_imp', 0))
        person_data[pt]['total_follows'] += safe_int(p.get('_follows', 0))
        person_data[pt]['total_likes'] += safe_int(p.get('_likes', 0))

    for pt in ['我', '你', '中性']:
        d = person_data[pt]
        if d['count'] > 0:
            print(f"  「{pt}」: {d['count']}条  均曝光 {d['total_imp']/d['count']:.0f}  均涨粉 {d['total_follows']/d['count']:.2f}  均赞 {d['total_likes']/d['count']:.1f}")

    # ── 2. 数字密度 ──
    print("\n📌 数字密度")
    num_data = {'with': {'count': 0, 'total_imp': 0, 'total_follows': 0},
                'without': {'count': 0, 'total_imp': 0, 'total_follows': 0}}
    for p in non_reply:
        key = 'with' if has_numbers(p.get('_text', '')) else 'without'
        num_data[key]['count'] += 1
        num_data[key]['total_imp'] += safe_int(p.get('_imp', 0))
        num_data[key]['total_follows'] += safe_int(p.get('_follows', 0))

    for k, label in [('with', '带数字'), ('without', '不带数字')]:
        d = num_data[k]
        if d['count'] > 0:
            print(f"  {label}: {d['count']}条  均曝光 {d['total_imp']/d['count']:.0f}  均涨粉 {d['total_follows']/d['count']:.2f}")

    # ── 3. 行数分析 ──
    print("\n📌 推文长度")
    len_data = defaultdict(lambda: {'count': 0, 'total_imp': 0, 'total_follows': 0})
    for p in non_reply:
        lines = text_lines(p.get('_text', ''))
        bucket = '1-3行' if lines <= 3 else ('4-5行' if lines <= 5 else '6行+')
        len_data[bucket]['count'] += 1
        len_data[bucket]['total_imp'] += safe_int(p.get('_imp', 0))
        len_data[bucket]['total_follows'] += safe_int(p.get('_follows', 0))

    for bucket in ['1-3行', '4-5行', '6行+']:
        d = len_data[bucket]
        if d['count'] > 0:
            print(f"  {bucket}: {d['count']}条  均曝光 {d['total_imp']/d['count']:.0f}  均涨粉 {d['total_follows']/d['count']:.2f}")

    # ── 4. 开头风格 ──
    print("\n📌 开头风格")
    open_data = defaultdict(lambda: {'count': 0, 'total_imp': 0, 'total_follows': 0})
    for p in non_reply:
        style = opening_style(p.get('_text', ''))
        open_data[style]['count'] += 1
        open_data[style]['total_imp'] += safe_int(p.get('_imp', 0))
        open_data[style]['total_follows'] += safe_int(p.get('_follows', 0))

    for style, d in sorted(open_data.items(),
                           key=lambda x: x[1]['total_imp']/max(x[1]['count'],1), reverse=True):
        if d['count'] > 0:
            print(f"  「{style}」: {d['count']}条  均曝光 {d['total_imp']/d['count']:.0f}  均涨粉 {d['total_follows']/d['count']:.2f}")

    # ── 5. 高频词关联 ──
    print("\n📌 高频词 × 涨粉关联 Top 10")
    wc = word_correlation(posts)
    top_follows = sorted(wc.items(), key=lambda x: x[1]['avg_follows'], reverse=True)[:10]
    if top_follows:
        for kw, s in top_follows:
            if s['avg_follows'] > 0:
                print(f"  「{kw}」: {s['count']}次  均曝光 {s['avg_imp']:.0f}  均涨粉 {s['avg_follows']:.2f}")
    else:
        print("  （数据不足，无法计算高频词关联）")

    # ── 6. 写作指纹 ──
    print("\n📌 写作指纹（按内容方向拆解 DNA）")
    fingerprints = [
        ('搞钱/商业', [p for p in non_reply if classify_post(p.get('_text', '')) == '搞钱/商业']),
        ('AI/技术', [p for p in non_reply if classify_post(p.get('_text', '')) == 'AI/技术']),
        ('认知/观点', [p for p in non_reply if classify_post(p.get('_text', '')) == '认知/观点']),
        ('泛流量/生活', [p for p in non_reply if classify_post(p.get('_text', '')) == '泛流量/生活']),
    ]

    for label, subset in fingerprints:
        if subset:
            pt_counter = Counter(person_type(p.get('_text', '')) for p in subset)
            digit_pct = sum(1 for p in subset if has_numbers(p.get('_text', ''))) / len(subset) * 100
            avg_lines = sum(text_lines(p.get('_text', '')) for p in subset) / len(subset)
            emoji_pct = sum(1 for p in subset if has_emoji(p.get('_text', ''))) / len(subset) * 100
            top_person = pt_counter.most_common(1)[0][0] if pt_counter else '中性'
            print(f"  {label}: {top_person}开头  {digit_pct:.0f}%带数字  均{avg_lines:.1f}行  emoji{emoji_pct:.0f}%")

    # ── 7–11: DNA 维度 ──
    emoji_analysis(non_reply, available)
    engagement_rate_analysis(non_reply, available)
    time_analysis(posts, available)
    viral_chain_analysis(posts, available)
    sentence_analysis(non_reply, available)

    # ── v3.0: 互动指标 ──
    engagement_metrics(posts, available)


def analyze(posts):
    """主分析入口：输出表 1–5 + TOP5（v3.0）"""
    # 列名自动识别
    posts, available, warnings = normalize_columns(posts)

    # 显示列识别结果
    col_names = {
        '_text': '正文', '_imp': '曝光', '_follows': '涨粉',
        '_likes': '点赞', '_replies': '回复', '_reposts': '转发',
        '_bookmarks': '书签', '_date': '日期'
    }
    detected = [col_names[k] for k in sorted(available) if k in col_names]
    if detected:
        print(f"📋 识别到 {len(detected)} 个数据列: {', '.join(detected)}")

    # 显示警告
    if warnings:
        for w in warnings:
            if w.startswith('⚠'):
                print(w)
            else:
                print(w)
        if '_text' not in available or '_imp' not in available:
            print("\n❌ 缺少必需列，无法继续分析。请检查 CSV 列名。")
            return

    for p in posts:
        p['category'] = classify_post(p.get('_text', ''))

    total = len(posts)
    SEP = "═" * 62

    # ── 表 1: 按内容方向对比 ──
    cat_stats = defaultdict(lambda: {'count': 0, 'total_imp': 0, 'total_follows': 0})
    for p in posts:
        cat = p['category']
        cat_stats[cat]['count'] += 1
        cat_stats[cat]['total_imp'] += safe_int(p.get('_imp', 0))
        cat_stats[cat]['total_follows'] += safe_int(p.get('_follows', 0))

    print(f"\n{SEP}")
    print(f"  表 1: 按内容方向对比")
    print(f"{SEP}")
    print(f"  {'方向':<15} {'条数':>5} {'占比':>6} {'均曝光':>9} {'均涨粉':>8} {'总涨粉':>7}")
    print(f"  {'─'*15} {'─'*5} {'─'*6} {'─'*9} {'─'*8} {'─'*7}")
    for cat, s in sorted(cat_stats.items(), key=lambda x: x[1]['total_follows']/max(x[1]['count'],1), reverse=True):
        cnt = s['count']
        pct = cnt / total * 100
        avg_imp = s['total_imp'] / max(cnt, 1)
        avg_follows = s['total_follows'] / max(cnt, 1)
        print(f"  {cat:<15} {cnt:>5} {pct:>5.0f}% {avg_imp:>9.0f} {avg_follows:>8.2f} {s['total_follows']:>7}")

    # ── 表 2: 回复帖真相 ──
    reply_posts = [p for p in posts if p['category'] == '回复互动']
    reply_imp = sum(safe_int(p.get('_imp', 0)) for p in reply_posts)
    reply_follows = sum(safe_int(p.get('_follows', 0)) for p in reply_posts)
    top10 = sorted(posts, key=lambda p: safe_int(p.get('_imp', 0)), reverse=True)[:10]
    top10_reply = sum(1 for p in top10 if p['category'] == '回复互动')
    top10_follows = sum(safe_int(p.get('_follows', 0)) for p in top10)

    print(f"\n{SEP}")
    print(f"  表 2: 回复帖真相")
    print(f"{SEP}")
    print(f"  回复帖占总发帖量:    {len(reply_posts)}/{total} = {len(reply_posts)/total*100:.0f}%")
    print(f"  回复帖总曝光:        {reply_imp:,}")
    print(f"  回复帖总涨粉:        {reply_follows}")
    print(f"  TOP10 曝光中回复帖:   {top10_reply}/10")
    print(f"  TOP10 合计涨粉:       {top10_follows}")

    # ── 表 3: 涨粉效率排行榜 ──
    print(f"\n{SEP}")
    print(f"  表 3: 涨粉效率排行榜")
    print(f"{SEP}")
    for cat, s in sorted(cat_stats.items(), key=lambda x: x[1]['total_follows']/max(x[1]['count'],1), reverse=True):
        eff = s['total_follows'] / max(s['count'], 1)
        star = " ★" if eff > 0 else ""
        bar_len = min(int(eff * 10), 30)
        bar = '█' * bar_len if bar_len > 0 else '▁'
        print(f"  {cat:<15} {eff:>6.2f}/条 {bar}{star}")

    # ── 表 4: 时间分配（中立语言）──
    print(f"\n{SEP}")
    print(f"  表 4: 发帖方向分布")
    print(f"{SEP}")
    print(f"  {'方向':<15} {'条数':>5} {'占比':>6}  {'分布'}")
    print(f"  {'─'*15} {'─'*5} {'─'*6}  {'─'*30}")
    time_spent = Counter(p['category'] for p in posts)
    for cat, cnt in time_spent.most_common():
        pct = cnt / total * 100
        bar = '█' * int(pct / 2)
        print(f"  {cat:<15} {cnt:>5} {pct:>5.0f}%  {bar}")

    # ── 一句话对比（中立语言）──
    if '_follows' in available:
        gaoqian = cat_stats.get('搞钱/商业', {'total_follows': 0, 'count': 1})
        other_follows = sum(s['total_follows'] for cat, s in cat_stats.items() if cat != '搞钱/商业')
        other_count = sum(s['count'] for cat, s in cat_stats.items() if cat != '搞钱/商业')

        print(f"\n{SEP}")
        print(f"  💡 涨粉方向分布")
        print(f"{SEP}")
        print(f"  搞钱/商业: {gaoqian['count']}条 → {gaoqian['total_follows']}粉")
        print(f"  其他方向:  {other_count}条 → {other_follows}粉")

    # ── v3.0: TOP5 推文 ──
    top_tweets(posts, available)

    # ── 表 5: DNA 分析 ──
    dna_analysis(posts, available)


def analyze_with_positioning(posts, positioning):
    """带账号定位的完整分析（表 1-7 + TOP5）"""
    # 列名自动识别
    posts, available, warnings = normalize_columns(posts)

    col_names = {
        '_text': '正文', '_imp': '曝光', '_follows': '涨粉',
        '_likes': '点赞', '_replies': '回复', '_reposts': '转发',
        '_bookmarks': '书签', '_date': '日期'
    }
    detected = [col_names[k] for k in sorted(available) if k in col_names]
    if detected:
        print(f"📋 识别到 {len(detected)} 个数据列: {', '.join(detected)}")

    for w in warnings:
        if w.startswith('⚠'):
            print(w)
        else:
            print(w)

    if '_text' not in available or '_imp' not in available:
        print("\n❌ 缺少必需列，无法继续分析。")
        return

    for p in posts:
        p['category'] = classify_post(p.get('_text', ''))

    total = len(posts)

    def map_to_positioning(category, positioning):
        for pos in positioning:
            for kw in pos.get('keywords', []):
                if kw in category:
                    return pos['name']
        cat_lower = category.lower()
        for pos in positioning:
            if any(w in cat_lower for w in pos['name'].lower().split()):
                return pos['name']
        return '其他/未匹配'

    pos_counts = defaultdict(int)
    pos_follows = defaultdict(int)
    for p in posts:
        mapped = map_to_positioning(p['category'], positioning)
        pos_counts[mapped] += 1
        pos_follows[mapped] += safe_int(p.get('_follows', 0))

    # 先跑基础分析（表 1–5 + TOP5）
    analyze(posts)

    SEP = "═" * 62

    # ── 表 6: 定位 vs 现实 ──
    print(f"\n{SEP}")
    print(f"  表 6: 定位 vs 现实")
    print(f"{SEP}")
    print(f"  {'定位方向':<18} {'期望':>5} {'实际':>5} {'偏差':>7} {'均涨粉':>7}")
    print(f"  {'─'*18} {'─'*5} {'─'*5} {'─'*7} {'─'*7}")
    for pos in positioning:
        name = pos['name']
        target = pos.get('target', 0)
        actual = pos_counts.get(name, 0) / total * 100
        deviation = actual - target
        marker = ' 🔴' if abs(deviation) > 15 else ''
        avg_fol = pos_follows.get(name, 0) / max(pos_counts.get(name, 1), 1)
        print(f"  {name:<18} {target:>4}% {actual:>4.0f}% {deviation:>+6.0f}pp{marker} {avg_fol:>7.2f}")

    # ── 表 7: 定位分析（中立语言）──
    print(f"\n{SEP}")
    print(f"  表 7: 定位分析")
    print(f"{SEP}")

    biggest_gap = max(positioning,
                      key=lambda p: abs(pos_counts.get(p['name'], 0)/total*100 - p.get('target', 0)))
    gap_name = biggest_gap['name']
    gap_target = biggest_gap.get('target', 0)
    gap_actual = pos_counts.get(gap_name, 0) / total * 100

    pillar_names = ' + '.join(f'{p["name"]} {p["target"]}%' for p in positioning)

    if gap_actual < gap_target * 0.5:
        print(f"  定位声明：「{pillar_names}」")
        print(f"  「{gap_name}」实际占比 {gap_actual:.0f}%（目标 {gap_target:.0f}%）")
        print(f"  🔴 核心方向与目标偏差较大，数据不支撑当前定位声明。")

    reply_pct = sum(1 for p in posts if p['category'] == '回复互动') / total * 100
    if reply_pct > 25:
        print(f"  回复互动占总发帖量 {reply_pct:.0f}%。这部分不属于任何定位方向。")
        print(f"  🔴 超过四分之一的内容与定位方向无关。")

    aligned = sum(pos_counts.get(p['name'], 0) for p in positioning)
    aligned_pct = aligned / total * 100
    if aligned_pct < 50:
        print(f"  与定位方向相关的内容仅占 {aligned_pct:.0f}%。")
        print(f"  🔴 多数发帖内容与账号定位方向不匹配。")
    else:
        print(f"  {aligned_pct:.0f}% 内容与定位方向匹配 ✓ 基本合格。")
