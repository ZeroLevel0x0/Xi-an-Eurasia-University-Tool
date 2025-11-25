#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
import urllib.request
import json
import datetime
import subprocess
import random

def print_banner() -> None:
    _TEXT = "ZEROLEVEL0X0"
    _SPACING = 1
    _SHADOW_DR = 1
    _SHADOW_DC = 2
    _SEED = 20250923
    _USE_COLOR = sys.stdout.isatty()
    _WHITE = "\033[97m" if _USE_COLOR else ""
    _GRAY  = "\033[90m" if _USE_COLOR else ""
    _RESET = "\033[0m"  if _USE_COLOR else ""

    _GLYPHS = {
        "Z": ["11111","00001","00100","01000","11111"],
        "E": ["11111","10000","11110","10000","11111"],
        "R": ["11110","10001","11110","10100","10010"],
        "O": ["01110","10001","10001","10001","01110"],
        "L": ["10000","10000","10000","10000","11111"],
        "V": ["10001","10001","10001","01010","00100"],
        "X": ["10001","01010","00100","01010","10001"],
        "0": ["01110","10011","10101","11001","01110"],
        "?": ["00100","00000","00100","00000","00100"],
    }

    def _get_glyph(ch: str):
        if ch in _GLYPHS: return _GLYPHS[ch]
        up = ch.upper()
        if up in _GLYPHS: return _GLYPHS[up]
        return _GLYPHS["?"]

    def _build_base_grid(text: str, spacing: int):
        chars = list(text)
        glyph_h = len(next(iter(_GLYPHS.values())))
        glyph_w = len(next(iter(_GLYPHS.values()))[0])
        total_w = sum(glyph_w for _ in chars) + spacing * (len(chars) - 1)
        grid = [[False] * total_w for _ in range(glyph_h)]
        c = 0
        for ch in chars:
            glyph = _get_glyph(ch)
            for r, row in enumerate(glyph):
                for i, bit in enumerate(row):
                    if bit == "1":
                        grid[r][c + i] = True
            c += glyph_w + spacing
        return grid

    def _compose_with_shadow(base_grid, dr, dc, seed):
        rnd = random.Random(seed)
        h = len(base_grid)
        w = len(base_grid[0]) if h else 0
        final_h = h + dr + 2
        final_w = w + dc + 4
        final = [[" " for _ in range(final_w)] for _ in range(final_h)]
        for r in range(h):
            for c in range(w):
                if base_grid[r][c]:
                    final[r][c] = "█"
        for r in range(h):
            for c in range(w):
                if base_grid[r][c]:
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < final_h and 0 <= cc < final_w and final[rr][cc] == " ":
                        p = rnd.random()
                        shade = "░" if p < 0.18 else "▒" if p < 0.56 else "▓"
                        final[rr][cc] = shade
                    if rnd.random() < 0.09:
                        rr2 = r + dr + 1
                        cc2 = c + dc + 2
                        if 0 <= rr2 < final_h and 0 <= cc2 < final_w and final[rr2][cc2] == " ":
                            final[rr2][cc2] = "·"
        return final

    def _grid_to_lines(grid):
        return ["".join(row).rstrip() for row in grid]

    def _colorize_line(line):
        if not _USE_COLOR: return line
        out = []
        for ch in line:
            if ch == "█": out.append(_WHITE + ch + _RESET)
            elif ch in ("▓","▒","░","·"): out.append(_GRAY + ch + _RESET)
            else: out.append(ch)
        return "".join(out)

    base = _build_base_grid(_TEXT, _SPACING)
    final_grid = _compose_with_shadow(base, _SHADOW_DR, _SHADOW_DC, _SEED)
    lines = _grid_to_lines(final_grid)
    banner = "\n".join(_colorize_line(line) for line in lines)
    sys.stdout.write("\n" + banner + "\n\n")
    sys.stdout.flush()

BASE_URL = "http://kedurp.eurasia.edu:8000/external/timetable-item"
HEAD = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; 23013RK75C Build/TKQ1.220905.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/104.0.5112.97 Mobile Safari/537.36TronClass/common;webank/h5face;webank/1.0;netType:NETWORK_MOBILE;appVersion:1000003;packageName:com.wisdomgarden.trpc",
    "Cookie": "platformMultilingual=zh_CN; NINJA_LANG=zh-CN"
}

_last_uid: str | None = None

def get_uid() -> str:
    global _last_uid
    if _last_uid:
        ans = input(f"是否使用上次的 UID（{_last_uid}）？ [y]/n: ").strip().lower()
        if ans == '' or ans == 'y':
            return _last_uid
    while True:
        uid = input("请输入你的14位学号(25xxxxxxxxxxxx)：").strip()
        if len(uid) == 14 and uid.isdigit():
            _last_uid = uid
            return uid
        print("格式有误，请重新输入14位数字学号！")

def date_range(a: str, b: str):
    dta = datetime.date.fromisoformat(a)
    dtb = datetime.date.fromisoformat(b)
    while dta <= dtb:
        yield str(dta)
        dta += datetime.timedelta(days=1)

def show_timetable():
    UID = get_uid()
    start = input("开始日期 (YYYY-MM-DD，默认本周一): ").strip()
    end   = input("结束日期 (YYYY-MM-DD，默认本周日): ").strip()
    if not start:
        today = datetime.date.today()
        start = str(today - datetime.timedelta(days=today.weekday()))
    if not end:
        today = datetime.date.today()
        end = str(today + datetime.timedelta(days=6-today.weekday()))
    for day in date_range(start, end):
        url = f"{BASE_URL}?start={day}&end={day}&ownerType=STUDENT&ownerId={UID}"
        req = urllib.request.Request(url, headers=HEAD)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
        print(f"\n【{day} 课程一览】")
        if not data:
            print("  当天没课")
            continue
        for row in sorted(data, key=lambda x: x["beginSlot"]):
            print(f"  {row['beginSlot']}节 {row['startTime']}-{row['endTime']} | "
                  f"{row['courseName']} | {row['roomBuilding']} {row['roomName']} | {row['teacherName']}")
    input("\n按回车返回主菜单")

def add_reminders():
    UID = get_uid()
    start = input("开始日期 (YYYY-MM-DD，默认本周一): ").strip()
    end   = input("结束日期 (YYYY-MM-DD，默认本周日): ").strip()
    if not start:
        today = datetime.date.today()
        start = str(today - datetime.timedelta(days=today.weekday()))
    if not end:
        today = datetime.date.today()
        end = str(today + datetime.timedelta(days=6-today.weekday()))
    for day in date_range(start, end):
        url = f"{BASE_URL}?start={day}&end={day}&ownerType=STUDENT&ownerId={UID}"
        req = urllib.request.Request(url, headers=HEAD)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
        for row in sorted(data, key=lambda x: x["beginSlot"]):
            remind_time = f"{row['date']} {row['startTime']}:00"
            title = f"{row['courseName']}  ({row['roomBuilding']} {row['roomName']})"
            script = f'''
            tell application "Reminders"
                if (list "课表" exists) = false then
                    make new list with properties {{name:"课表"}}
                end if
                tell list "课表"
                    make new reminder with properties {{name:"{title}", due date:date "{remind_time}"}}
                end tell
            end tell
            '''
            subprocess.run(["osascript", "-e", script], check=True)
            print(f"已添加提醒: {title}  @ {remind_time}")
    input("\n全部完成！按回车返回主菜单")

def clear_reminders():
    script = '''
    tell application "Reminders"
        if (list "课表" exists) then
            set delList to list "课表"
            set rems to reminders of delList
            repeat with r in rems
                delete r
            end repeat
            log "已清空课表列表"
        else
            log "课表列表不存在，无需清理"
        end if
    end tell
    '''
    subprocess.run(["osascript", "-e", script])
    print("课表提醒已全部删除！")
    input("按回车返回主菜单")

def main():
    menu = """
╔═════════ 欧亚课表小工具 ═════════╗
║  1. 查课表                       ║
║  2. 课表写入 macOS 提醒事项      ║
║  3. 清除“课表”提醒事项           ║
║  4. 退出                         ║
╚══════════════════════════════════╝
请选择 (1/2/3/4)："""
    while True:
        choice = input(menu).strip()
        if choice == "1":
            show_timetable()
        elif choice == "2":
            add_reminders()
        elif choice == "3":
            clear_reminders()
        elif choice == "4":
            sys.exit("Bye~")
        else:
            print("输入有误，请重新选择！")

if __name__ == "__main__":
    print_banner()
    main()
