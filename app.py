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

# ================= UI CSS =================
st.markdown(
    """
    <style>
      /* 제목 기본 왼쪽 정렬 */
      h1 {
        font-size: 1.55rem !important;
        margin-bottom: 0.7rem;
      }

      /* 버튼 기본 Streamlit 스타일 유지 */
      .stButton>button {
        padding: 0.75rem 1rem;
        font-size: 1.15rem;
        font-weight: 800;
        border-radius: 16px;
      }

      .tp-wrap { margin-top: 0.75rem; }

      .tp-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0.35rem 0;
        flex-wrap: wrap;
      }

      /* 라벨 */
      .tp-label {
        font-weight: 900;
        font-size: 1.05rem;
        padding: 0.25rem 0.55rem;
        border-radius: 10px;
        color: white;
        white-space: nowrap;
      }
      .tp-label-red  { background: #e53935; }
      .tp-label-blue { background: #1e88e5; }

      /* 로또 공 */
      .tp-ball {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        font-size: 0.95rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.18);
        border: 1px solid rgba(0,0,0,0.15);
        user-select: none;
      }

      /* 구간별 색상 */
      .b1 { background: #f6c343; color: #111; } /* 1~9 */
      .b2 { background: #1e88e5; color: #fff; } /* 10~19 */
      .b3 { background: #e53935; color: #fff; } /* 20~29 */
      .b4 { background: #9e9e9e; color: #111; } /* 30~39 */
      .b5 { background: #43a047; color: #fff; } /* 40~45 */

      .tp-balls {
        display: inline-flex;
        gap: 7px;
        flex-wrap: wrap;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ================= Data =================
def empty_freq():
    return {str(i): 0 for i in range(1, 46)}

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
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

def parse_numbers(line):
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
        lines = f.readlines()[1:]
    for line in lines:
        nums = parse_numbers(line)
        if not nums:
            continue
        valid += 1
        for n in nums:
            freq[str(n)] += 1
    save_cache(valid, freq)
    return valid

# ================= Logic =================
def bucket_id(n):
    for i,(a,b) in enumerate(BUCKETS):
        if a <= n <= b:
            return i
    return 0

def passes_bucket_rule(nums):
    cnt = [0]*len(BUCKETS)
    for n in nums:
        cnt[bucket_id(n)] += 1
    return max(cnt) <= MAX_PER_BUCKET

def random_pick_with_filter(pool):
    for _ in range(MAX_TRIES):
        pick = sorted(random.sample(pool, 6))
        if passes_bucket_rule(pick):
            return pick
    return sorted(random.sample(pool, 6))

def make_games(freq):
    freq_int = {int(k):int(v) for k,v in freq.items()}
    sorted_nums = sorted(freq_int.items(), key=lambda x:(-x[1], x[0]))
    hot10 = [n for n,_ in sorted_nums[:10]]
    cold10 = [n for n,_ in sorted_nums[-10:]]

    games = []
    games.append(sorted(hot10[:6]))
    for _ in range(4):
        games.append(random_pick_with_filter(hot10))
    games.append(sorted(cold10[-6:]))
    for _ in range(4):
        games.append(random_pick_with_filter(cold10))
    return games

def fmt2(n): return f"{n:02d}"

def num_class(n):
    if n <= 9: return "b1"
    if n <= 19: return "b2"
    if n <= 29: return "b3"
    if n <= 39: return "b4"
    return "b5"

def label_text(idx):
    if idx == 1: return "多 (고정)"
    if 2 <= idx <= 5: return "多 (랜덤)"
    if idx == 6: return "小 (고정)"
    return "小 (랜덤)"

# ================= App =================
st.title("로또번호 (TaePung)")

cache = load_cache()
if cache is None:
    rebuild_cache_from_csv()
    cache = load_cache()
if cache is None:
    st.error("로또번호.csv 또는 캐시 오류")
    st.stop()

if "games" not in st.session_state:
    st.session_state["games"] = None

if st.button("로또번호생성", type="primary"):
    st.session_state["games"] = make_games(cache["freq"])

games = st.session_state["games"]
if games:
    st.markdown('<div class="tp-wrap">', unsafe_allow_html=True)
    for idx, nums in enumerate(games, 1):
        label_color = "tp-label-red" if idx <= 5 else "tp-label-blue"
        balls = "".join(
            f'<span class="tp-ball {num_class(n)}">{fmt2(n)}</span>'
            for n in nums
        )
        st.markdown(
            f'''
            <div class="tp-row">
              <span class="tp-label {label_color}">{label_text(idx)}</span>
              <span class="tp-balls">{balls}</span>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
