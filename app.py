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

# ---- UI CSS ----
st.markdown(
    """
    <style>
      h1 { font-size: 1.55rem !important; margin-bottom: 0.55rem; }

      .stButton>button {
        width: 100%;
        padding: 0.75rem 1rem;
        font-size: 1.15rem;
        font-weight: 800;
        border-radius: 14px;
      }

      .tp-wrap { margin-top: 0.70rem; }

      /* 한 줄 레이아웃 */
      .tp-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0.35rem 0;
        flex-wrap: wrap;
      }

      /* 라벨(01게임 多(고정) 등) */
      .tp-label {
        font-weight: 900;
        font-size: 1.10rem;
        padding: 0.25rem 0.45rem;
        border-radius: 10px;
        color: white;
        line-height: 1.25rem;
        white-space: nowrap;
      }
      .tp-label-red  { background: #e53935; }
      .tp-label-blue { background: #1e88e5; }

      /* 공(로또볼) */
      .tp-ball {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        font-size: 1.05rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.18);
        border: 1px solid rgba(0,0,0,0.15);
        user-select: none;
      }

      /* 구간별 색상 */
      .b1  { background: #f6c343; color: #111; }  /* 1~9 노랑 */
      .b2  { background: #1e88e5; color: #fff; }  /* 10~19 파랑 */
      .b3  { background: #e53935; color: #fff; }  /* 20~29 빨강 */
      .b4  { background: #9e9e9e; color: #111; }  /* 30~39 회색 */
      .b5  { background: #43a047; color: #fff; }  /* 40~45 초록 */

      /* 공 컨테이너 */
      .tp-balls {
        display: inline-flex;
        gap: 8px;
        flex-wrap: wrap;
      }
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
    games.append(sorted(hot10[:6]))            # 01 多(고정)
    for _ in range(4):                         # 02~05 多(램덤)
        games.append(random_pick_with_filter(hot10))
    games.append(sorted(cold10[-6:]))          # 06 小(고정)
    for _ in range(4):                         # 07~10 小(램덤)
        games.append(random_pick_with_filter(cold10))
    return games

def fmt2(n: int) -> str:
    return f"{n:02d}"

def num_class(n: int) -> str:
    if 1 <= n <= 9:
        return "b1"
    if 10 <= n <= 19:
        return "b2"
    if 20 <= n <= 29:
        return "b3"
    if 30 <= n <= 39:
        return "b4"
    return "b5"  # 40~45

def game_name(idx: int) -> str:
    # 01~05: 多, 06~10: 小
    if idx == 1:
        return f"{idx:02d}게임  多(고정)"
    if 2 <= idx <= 5:
        return f"{idx:02d}게임  多(램덤)"
    if idx == 6:
        return f"{idx:02d}게임  小(고정)"
    return f"{idx:02d}게임  小(램덤)"

# ---- 앱 시작 ----
st.title("로또번호 (TaePung)")

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
        label_color = "tp-label-red" if idx <= 5 else "tp-label-blue"
        label_text = game_name(idx)

        balls_html = ""
        for n in nums:
            balls_html += f'<span class="tp-ball {num_class(n)}">{fmt2(n)}</span>'

        row_html = (
            f'<div class="tp-row">'
            f'  <span class="tp-label {label_color}">{label_text}</span>'
            f'  <span class="tp-balls">{balls_html}</span>'
            f'</div>'
        )
        st.markdown(row_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
