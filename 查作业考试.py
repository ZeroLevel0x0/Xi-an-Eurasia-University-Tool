#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
import random
import base64
import datetime as dt
import subprocess
import requests
import pytz
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from urllib.parse import urljoin

_TEXT = "ZEROLEVEL0X0"
_SPACING = 1
_SHADOW_DR = 1
_SHADOW_DC = 2
_SEED = 20250923
_USE_COLOR = sys.stdout.isatty()
_WHITE = "\033[97m" if _USE_COLOR else ""
_GRAY = "\033[90m" if _USE_COLOR else ""
_RESET = "\033[0m" if _USE_COLOR else ""
_GLYPHS = {
    "Z": ["11111", "00001", "00100", "01000", "11111"],
    "E": ["11111", "10000", "11110", "10000", "11111"],
    "R": ["11110", "10001", "11110", "10100", "10010"],
    "O": ["01110", "10001", "10001", "10001", "01110"],
    "L": ["10000", "10000", "10000", "10000", "11111"],
    "V": ["10001", "10001", "10001", "01010", "00100"],
    "X": ["10001", "01010", "00100", "01010", "10001"],
    "0": ["01110", "10011", "10101", "11001", "01110"],
    "?": ["00100", "00000", "00100", "00000", "00100"],
}


def _get_glyph(ch: str):
    return _GLYPHS.get(ch.upper(), _GLYPHS["?"])


def _build_base_grid(text: str, spacing: int):
    chars, glyph_h = list(text), len(next(iter(_GLYPHS.values())))
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
    rnd, h, w = random.Random(seed), len(base_grid), len(base_grid[0])
    final_h, final_w = h + dr + 2, w + dc + 4
    final = [[" " for _ in range(final_w)] for _ in range(final_h)]
    for r in range(h):
        for c in range(w):
            if base_grid[r][c]:
                final[r][c] = "█"
    for r in range(h):
        for c in range(w):
            if base_grid[r][c]:
                rr, cc = r + dr, c + dc
                if 0 <= rr < final_h and 0 <= cc < final_w and final[rr][cc] == " ":
                    p = rnd.random()
                    shade = "░" if p < 0.18 else "▒" if p < 0.56 else "▓"
                    final[rr][cc] = shade
                if rnd.random() < 0.09:
                    rr2, cc2 = r + dr + 1, c + dc + 2
                    if 0 <= rr2 < final_h and 0 <= cc2 < final_w and final[rr2][cc2] == " ":
                        final[rr2][cc2] = "·"
    return final


def _grid_to_lines(grid):
    return ["".join(row).rstrip() for row in grid]


def _colorize_line(line):
    if not _USE_COLOR:
        return line
    out = []
    for ch in line:
        if ch == "█":
            out.append(_WHITE + ch + _RESET)
        elif ch in ("▓", "▒", "░", "·"):
            out.append(_GRAY + ch + _RESET)
        else:
            out.append(ch)
    return "".join(out)


def print_banner(text: str = _TEXT):
    base = _build_base_grid(text, _SPACING)
    final_grid = _compose_with_shadow(base, _SHADOW_DR, _SHADOW_DC, _SEED)
    lines = _grid_to_lines(final_grid)
    banner = "\n".join(_colorize_line(line) for line in lines)
    sys.stdout.write("\n" + banner + "\n\n")
    sys.stdout.flush()


LOGIN_URL = (
    "http://sso.eurasia.edu/authserver/login"
    "?service=https%3A%2F%2Fidentity.eurasia.edu%2Fauth%2Frealms%2Feurasia%2Fbroker%2Fcas-client%2Fendpoint"
    "%3Fstate%3DinOgixqdurD7MNgCF_FCYWvZpIGcbrQXC8vz-HNX3ik.X8w1MASIGII.TronClass-web"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
    "Referer": LOGIN_URL,
    "Origin": "http://sso.eurasia.edu",
}

AES_CHARS = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"


def random_string(n):
    return "".join(random.choices(AES_CHARS, k=n))


def pkcs7_pad(data):
    pad = AES.block_size - len(data) % AES.block_size
    return data + bytes([pad] * pad)


def encrypt_password(password: str, key: str) -> str:
    salt, iv = random_string(64), random_string(16)
    key_b = key.encode("utf-8")[:16]
    iv_b = iv.encode("utf-8")[:16]
    plain = (salt + password).encode("utf-8")
    cipher = AES.new(key_b, AES.MODE_CBC, iv_b)
    return base64.b64encode(cipher.encrypt(pkcs7_pad(plain))).decode()


def login(student_id: str, password: str) -> requests.Session | None:
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get(LOGIN_URL)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    execution = soup.find("input", {"name": "execution"})["value"]
    encrypt_key = soup.find("input", {"id": "pwdEncryptSalt"})["value"]
    encrypted_pwd = encrypt_password(password, encrypt_key)
    data = {
        "username": student_id,
        "password": encrypted_pwd,
        "captcha": "",
        "rememberMe": "true",
        "_eventId": "submit",
        "cllt": "userNameLogin",
        "dllt": "generalLogin",
        "lt": "",
        "execution": execution,
    }
    resp = s.post(LOGIN_URL, data=data, allow_redirects=False)
    if resp.status_code != 302 or "Location" not in resp.headers:
        print("❌ 登录失败，请检查学号/密码或参数是否变化")
        return None

    s.get(resp.headers["Location"])

    lms_index = "https://lms.eurasia.edu/user/index"
    s.headers.update({"Referer": lms_index, "Origin": "https://lms.eurasia.edu"})
    s.get(lms_index)
    print("登录成功!")
    return s


API = "https://lms.eurasia.edu/api/todos?no-intercept=true"
TZ = pytz.timezone("Asia/Shanghai")


def fetch_todos(session: requests.Session) -> list[dict]:
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://lms.eurasia.edu/user/index",
        "Origin": "https://lms.eurasia.edu",
    }
    resp = session.get(API, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()["todo_list"]


def add_reminder(title: str, due: dt.datetime) -> None:
    if sys.platform != "darwin":
        return
    safe_title = title.translate(str.maketrans("", "", '"“”'))
    date_str = due.strftime("%Y-%m-%d %H:%M:%S")
    script = f"""
    tell application "Reminders"
        if (list "作业考试" exists) = false then
            make new list with properties {{name:"作业考试"}}
        end if
        tell list "作业考试"
            if (count of (reminders whose name is "{safe_title}")) = 0 then
                make new reminder with properties {{name:"{safe_title}", due date:(date "{date_str}"), remind me date:(date "{date_str}")}}
            end if
        end tell
    end tell
    """
    subprocess.run(["osascript", "-e", script], check=True)


def list_homework(session: requests.Session) -> None:
    tasks = fetch_todos(session)
    tasks.sort(key=lambda x: x["end_time"])
    type_map = {"homework": "作业", "exam": "考试"}
    header = "{:<12} | {:<4} | {:<40} | {:}".format("截止时间", "类型", "任务标题", "科目")
    print(f"\n共 {len(tasks)} 条作业（按截止时间排序）")
    print("-" * len(header) * 2)
    print(header)
    print("-" * len(header) * 2)
    for t in tasks:
        local = dt.datetime.fromisoformat(t["end_time"].replace("Z", "+00:00")).astimezone(TZ)
        type_cn = type_map.get(t["type"], t["type"])
        title = t["title"]
        course = t["course_name"]
        if "（" in course:
            idx = course.rfind("（")
            course = course[:idx] + course[idx:].split("）")[0] + "）"
        print("{:<12} | {:<4} | {:<40} | {:}".format(f"{local:%m-%d %H:%M}", type_cn, title, course))
    input("\n按回车返回主菜单")


def sync_homework(session: requests.Session) -> None:
    tasks = fetch_todos(session)
    tasks.sort(key=lambda x: x["end_time"])
    print(f"共 {len(tasks)} 条，开始写入提醒事项...")
    for t in tasks:
        raw = t["end_time"]
        utc = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        local = utc.astimezone(TZ)
        print(f"原始:{raw}  →  本地:{local:%Y-%m-%d %H:%M:%S}")
        title = f"{t['title']}（{t['course_name']}）"
        add_reminder(title, local)
        print(f"  ✔ {title}")
    print("全部写入完成！打开“提醒事项”看看吧～")
    input("\n按回车返回主菜单")


def clear_reminders() -> None:
    if sys.platform != "darwin":
        print("非 macOS 系统，跳过清空提醒事项")
        input("\n按回车返回主菜单")
        return
    script = """
    tell application "Reminders"
        if (list "作业考试" exists) then
            tell list "作业考试"
                delete (every reminder)
            end tell
        end if
    end tell
    """
    subprocess.run(["osascript", "-e", script])
    print("已清空「作业考试」列表！")
    input("\n按回车返回主菜单")


# ---------- 主流程 ----------
def main() -> None:
    print_banner()
    print("欢迎使用欧亚查作业提醒小工具")
    sid = input("请输入你的学号: ").strip()
    pwd = input("请输入你的密码: ").strip()
    session = login(sid, pwd)
    if not session:
        sys.exit(1)

    menu = """
╔════════════ 菜单 ═══════════╗
║  1. 查作业                  ║
║  2. 查作业并同步至提醒事项  ║
║  3. 清除macOS作业提醒       ║
║  4. 退出                    ║
╚═════════════════════════════╝
请选择 (1/2/3/4)："""
    while True:
        choice = input(menu).strip()
        if choice == "1":
            list_homework(session)
        elif choice == "2":
            sync_homework(session)
        elif choice == "3":
            clear_reminders()
        elif choice == "4":
            sys.exit("Bye~")
        else:
            print("输入有误，请重新选择！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nInterrupted.")
