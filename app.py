import os
import json
import random
from datetime import datetime
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "로또번호.csv")
CACHE_FILE = os.path.join(BASE_DIR, "lotto_cache.json")

# 구간: 1~9 / 10~19 / 20~29 / 30~39 / 40~45
BUCKETS = [(1, 9), (10, 19), (20, 29), (30, 39), (40, 45)]
MAX_PER_BUCKET = 3  # 한 구간 최대 3개(=4개 이상 금지)
MAX_TRIES = 5000

st.set_page_config(page_title="로또번호 (태풍)", page_icon="🎲", layout="centered")


def empty_freq():
    return {str(i): 0 for i in range(1, 46)}


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cache(last_draw, freq):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "last_draw": int(last_draw),
                "freq": freq,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def parse_numbers(line: str):
    nums, buf = [], ""
    for ch in line:
        if ch.isdigit():
            buf += ch
        else:
            if buf:
                nums.append(int(buf))
                buf = ""
    if buf:
        nums.append(int(buf))
    nums = [n for n in nums if 1 <= n <= 45]
    return nums[:6] if len(nums) >= 6 else None


def rebuild_cache_from_csv():
    if not os.path.exists(CSV_FILE):
        return None

    freq = empty_freq()
    valid = 0

    with open(CSV_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # 첫 줄 헤더 제외
    data_lines = lines[1:] if len(lines) > 0 else []
    for line in data_lines:
        nums = parse_numbers(line)
        if not nums:
            continue
        valid += 1
        for n in nums:
            freq[str(n)] += 1

    save_cache(valid, freq)
    return valid


def bucket_id(n: int) -> int:
    for i, (a, b) in enumerate(BUCKETS):
        if a <= n <= b:
            return i
    return 0


def passes_bucket_rule(nums):
    counts = [0] * len(BUCKETS)
    for n in nums:
        counts[bucket_id(n)] += 1
    return max(counts) <= MAX_PER_BUCKET


def random_pick_with_filter(pool):
    for _ in range(MAX_TRIES):
        pick = sorted(random.sample(pool, 6))
        if passes_bucket_rule(pick):
            return pick
    return sorted(random.sample(pool, 6))


def make_games(freq):
    freq_int = {int(k): int(v) for k, v in freq.items()}
    sorted_nums = sorted(freq_int.items(), key=lambda x: (-x[1], x[0]))

    hot10 = [n for n, _ in sorted_nums[:10]]
    cold10 = [n for n, _ in sorted_nums[-10:]]

    games = []
    # 1: HOT TOP6 고정
    games.append(sorted(hot10[:6]))
    # 2~5: HOT TOP10 랜덤
    for _ in range(4):
        games.append(random_pick_with_filter(hot10))
    # 6: COLD BOTTOM6 고정
    games.append(sorted(cold10[-6:]))
    # 7~10: COLD BOTTOM10 랜덤
    for _ in range(4):
        games.append(random_pick_with_filter(cold10))

    return games


# --- 앱 시작 ---
st.title("로또번호 (태풍)")

# 캐시 없으면 자동 생성
cache = load_cache()
if cache is None:
    rebuilt = rebuild_cache_from_csv()
    cache = load_cache()

if cache is None:
    st.error("로또번호.csv 또는 캐시 생성에 문제가 있습니다.")
    st.stop()

if st.button("로또번호생성", type="primary"):
    games = make_games(cache["freq"])
    lines = []
    for i, g in enumerate(games, 1):
        lines.append(f"{i:02d}게임: " + " - ".join(map(str, g)))
    st.text("\n".join(lines))
