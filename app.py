import os
import json
import random
from datetime import datetime
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "로또번호.csv")
CACHE_FILE = os.path.join(BASE_DIR, "lotto_cache.json")

BUCKETS = [(1, 9), (10, 19), (20, 29), (30, 39), (40, 45)]
MAX_PER_BUCKET = 3
MAX_TRIES = 5000

st.set_page_config(page_title="로또번호 (TaePung)", page_icon="🎲", layout="centered")

# ---- 모바일 가독성용 CSS ----
st.markdown(
    """
    <style>
      /* 타이틀 살짝 조정 */
      h1 { margin-bottom: 0.6rem; }

      /* 버튼 크게 */
      .stButton>button {
        width: 100%;
        padding: 0.9rem 1rem;
        font-size: 1.25rem;   /* 크게 */
        font-weight: 800;
        border-radius: 14px;
      }

      /* 결과 라인 글씨 크게(2단계 업) */
      .tp-line {
        font-size: 1.35rem;   /* 기본보다 확 크게 */
        line-height: 1.85rem;
        font-weight: 800;
        letter-spacing: 0.2px;
        margin: 0.25rem 0;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      }
      .tp-red { color: #e53935; }
      .tp-blue { color: #1e88e5; }

      /* 결과 영역 여백 */
      .tp-wrap { margin-top: 0.7rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

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

    data_lines = lines[1:] if len(lines) > 0 else []  # 헤더 제외
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
    games.append(sorted(hot10[:6]))            # 01 HOT 고정
    for _ in range(4):                         # 02~05 HOT 랜덤
        games.append(random_pick_with_filter(hot10))
    games.append(sorted(cold10[-6:]))          # 06 COLD 고정
    for _ in range(4):                         # 07~10 COLD 랜덤
        games.append(random_pick_with_filter(cold10))
    return games

# --- 앱 시작 ---
st.title("로또번호 (TaePung)")

# 캐시 없으면 자동 생성
cache = load_cache()
if cache is None:
    rebuild_cache_from_csv()
    cache = load_cache()

if cache is None:
    st.error("로또번호.csv 또는 캐시 생성에 문제가 있습니다.")
    st.stop()

if "games" not in st.session_state:
    st.session_state["games"] = None

if st.button("로또번호생성", type="primary"):
    st.session_state["games"] = make_games(cache["freq"])

games = st.session_state["games"]
if games:
    st.markdown('<div class="tp-wrap">', unsafe_allow_html=True)

    for idx, nums in enumerate(games, start=1):
        color_class = "tp-red" if idx <= 5 else "tp-blue"
        line = f"{idx:02d}게임: " + " - ".join(map(str, nums))
        st.markdown(
            f'<div class="tp-line {color_class}">{line}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
