# -*- coding: utf-8 -*-
"""直播日志解析核心模块（与 UI 解耦，便于单独测试）。

场次规则：
1. 主播“已开播”到同主播后续第一个“已下播”算一场，跨天也归属开播那天；
2. 没有配对下播线时，按日志时间断层切场：同一主播相邻数据行间隔
   超过 GAP_MINUTES 分钟即视为新的一场。
"""
import re
from datetime import datetime, timedelta

# 行首时间戳
pattern_line_time = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
# 主播“xx”（房间号：yy）...已开播
pattern_start = re.compile(r'主播“(.*?)”（房间号：(\d+)）.*已开播')
# 主播“xx”实时数据（房间号：yy），在线人数：a，总观看人数：b，点赞数：c，新增粉丝数：d（d 允许为空）
pattern_data = re.compile(
    r'主播“(.*?)”.*?（房间号：(\d+)），在线人数：(\d+).*总观看人数：(\d+)'
    r'.*点赞数：(\d+).*新增粉丝数：(\d*)'
)
# 主播“xx”已下播（房间号：yy），下播时间：MM-DD HH:MM:SS，直播时长：zz，...
pattern_end = re.compile(
    r'主播“(.*?)”已下播（房间号：(\d+)），下播时间：(\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    r'.*直播时长：(.*?)，'
)

GAP_MINUTES = 10  # 数据行时间断层阈值（分钟）


def _parse_end_time(start_dt: datetime, raw: str) -> datetime:
    """把 'MM-DD HH:MM:SS' 与开播日期合成完整下播时间；跨年自动进位。"""
    end_dt = datetime.strptime(f'{start_dt.year}-{raw}', '%Y-%m-%d %H:%M:%S')
    if end_dt < start_dt:
        end_dt = end_dt.replace(year=end_dt.year + 1)
    return end_dt


def _new_session(anchor, room, start_dt, implicit=False):
    return {
        "主播名": anchor,
        "房间号": room,
        "开播时间": start_dt,
        "下播时间": None,
        "直播时长": None,
        "implicit": implicit,       # 是否为无开播线、按数据断层推断的场次
        "last_time": start_dt,      # 最近一条数据行时间，用于断层判断
    }


def parse_live_log(text: str):
    """解析直播日志文本，返回 (数据行列表, 场次列表)。"""
    lines = text.split('\n')
    data = []
    sessions = []               # 全部场次（按出现顺序）
    open_by_anchor = {}         # 主播名 -> 当前未结束的场次

    def close_current(anchor):
        open_by_anchor.pop(anchor, None)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if '已开播' in line:
            m = pattern_start.search(line)
            if not m:
                continue
            anchor = m.group(1)
            # 同主播已有进行中的场（还没等到下播线）→ 视为断线重连，忽略重复开播
            if anchor in open_by_anchor:
                continue
            tm = pattern_line_time.match(line)
            start_dt = datetime.strptime(tm.group(1), '%Y-%m-%d %H:%M:%S') if tm else None
            s = _new_session(anchor, m.group(2), start_dt)
            sessions.append(s)
            open_by_anchor[anchor] = s

        elif '在线人数：' in line:
            m = pattern_data.search(line)
            if not m:
                continue
            anchor, room = m.group(1), m.group(2)
            tm = pattern_line_time.match(line)
            if not tm:
                continue
            log_time = datetime.strptime(tm.group(1), '%Y-%m-%d %H:%M:%S')

            s = open_by_anchor.get(anchor)
            # 仅对无开播线的推断场次做断层切分；显式开播的场次不受间隔影响，
            # 直到下播线或下一次开播才结束
            if s is not None and s['implicit'] and (log_time - s['last_time']) > timedelta(minutes=GAP_MINUTES):
                close_current(anchor)
                s = None
            if s is None:
                s = _new_session(anchor, room, log_time, implicit=True)
                sessions.append(s)
                open_by_anchor[anchor] = s

            new_fans_raw = m.group(6).strip()
            data.append({
                "日志时间": log_time,
                "主播名": anchor,
                "房间号": room,
                "session_idx": len(sessions) - 1,
                "在线人数": int(m.group(3)),
                "总观看人数": int(m.group(4)),
                "点赞数": int(m.group(5)),
                "新增粉丝数": int(new_fans_raw) if new_fans_raw else 0,
            })
            s['last_time'] = log_time

        elif '已下播' in line:
            m = pattern_end.search(line)
            if not m:
                continue
            anchor, room = m.group(1), m.group(2)
            s = open_by_anchor.get(anchor)
            # 主播与房间号都必须匹配当前进行中的场，才认定是同一场的下播
            if s is not None and s['开播时间'] is not None and s['房间号'] == room:
                s['下播时间'] = _parse_end_time(s['开播时间'], m.group(3))
                s['直播时长'] = m.group(4)
                close_current(anchor)

    # 按所属场次回填：日期归属开播那天，跨天不拆分
    for row in data:
        s = sessions[row["session_idx"]]
        start = s["开播时间"]
        row["场次号"] = row.pop("session_idx")
        row["直播日期"] = start.date() if start else row["日志时间"].date()
        row["相对时间(分钟)"] = (
            (row["日志时间"] - start).total_seconds() / 60 if start else None
        )
        row["开播时间"] = start
        row["下播时间"] = s["下播时间"]
        row["直播时长"] = s["直播时长"]
    return data, sessions


def build_dataframe(data):
    """把解析结果转成 pandas DataFrame。"""
    import pandas as pd
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values("日志时间").reset_index(drop=True)
    return df
