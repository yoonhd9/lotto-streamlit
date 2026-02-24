import os
import json
import random
from datetime import datetime

import streamlit as st

# =========================
# 경로/파일
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "로또번호.csv")
CACHE_FILE = os.path.join(BASE_DIR, "lotto_cache.json")

# =========================
# 설정
# =========================
BUCKETS = [(1, 9), (10, 19), (20, 29), (30, 39), (40, 45)]
MAX_PER_BUCKET = 3  # 4개 이상 금지

GAMES_TOTAL = 10
MAX_TRIES = 5000

st.set_page_config(page_title="로또 번호 추천기 (HOT vs COLD)", page_icon="🎲", layout="centered")


# =========================
# 캐시
# =========================
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

# =========================
# CSV → 캐시 자동 반영
# =========================
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

    # 첫 줄 헤더 제외(헤더가 없으면 첫 줄이 데이터일 수도 있으니 안전장치)
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

# =========================
# 필터/추천
# =========================
def bucket_id(n: int) -> int:
    for i, (a, b) in enumerate(BUCKETS):
        if a <= n <= b:
            return i
    return 0

def passes_bucket_rule(nums):
    buckets = [0] * len(BUCKETS)
    for n in nums:
        buckets[bucket_id(n)] += 1
    return max(buckets) <= MAX_PER_BUCKET

def random_pick_with_filter(pool):
    for _ in range(MAX_TRIES):
        pick = sorted(random.sample(pool, 6))
        if passes_bucket_rule(pick):
            return pick
    return sorted(random.sample(pool, 6))

def make_games(freq):
    freq_int = {int(k): int(v) for k, v in freq.items()}

    # 많이 나온 순(내림차순), 동률이면 숫자 오름차순
    sorted_nums = sorted(freq_int.items(), key=lambda x: (-x[1], x[0]))
    hot10 = [n for n, _ in sorted_nums[:10]]
    cold10 = [n for n, _ in sorted_nums[-10:]]

    games = []
    # 1번: HOT TOP6 고정
    games.append(sorted(hot10[:6]))
    # 2~5번: HOT TOP10 랜덤
    for _ in range(4):
        games.append(random_pick_with_filter(hot10))
    # 6번: COLD BOTTOM6 고정
    games.append(sorted(cold10[-6:]))
    # 7~10번: COLD BOTTOM10 랜덤
    for _ in range(4):
        games.append(random_pick_with_filter(cold10))

    return games, hot10, cold10

def format_result(last_draw, games):
    lines = []
    lines.append("모드 : offline_cache (CSV 기반)")
    lines.append(f"회차 기준 : {last_draw}")
    lines.append("")
    for i, g in enumerate(games, 1):
        if i == 1:
            tag = " (HOT 고정)"
        elif 2 <= i <= 5:
            tag = " (HOT 랜덤)"
        elif i == 6:
            tag = " (COLD 고정)"
        else:
            tag = " (COLD 랜덤)"
        lines.append(f"{i:02d}게임 : " + " - ".join(map(str, g)) + tag)
    return "\n".join(lines)


# =========================
# UI
# =========================
st.title("🎲 로또 번호 추천기 (HOT vs COLD)")
st.caption("CSV(로또번호.csv)를 기반으로 캐시를 자동 재생성하고, HOT/COLD 전략으로 10게임을 추천합니다.")

with st.expander("필터 규칙 보기"):
    st.write("- 구간: 1~9 / 10~19 / 20~29 / 30~39 / 40~45")
    st.write(f"- 어떤 구간도 4개 이상 금지 (최대 {MAX_PER_BUCKET}개)")
    st.write("- 1번: HOT TOP6 고정 / 2~5번: HOT TOP10 랜덤")
    st.write("- 6번: COLD BOTTOM6 고정 / 7~10번: COLD BOTTOM10 랜덤")

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    seed_text = st.text_input("시드(선택)", value="", placeholder="예: 1234")
with col2:
    do_rebuild = st.button("CSV 최신 반영")
with col3:
    st.write("")
    st.write("※ `로또번호.csv`가 저장소에 있어야 합니다.")

if seed_text.strip():
    try:
        random.seed(int(seed_text.strip()))
    except ValueError:
        st.warning("시드는 숫자만 가능합니다. (시드 없이 진행)")

if do_rebuild:
    last = rebuild_cache_from_csv()
    if last:
        st.success(f"캐시 재생성 완료! (회차 기준: {last})")
    else:
        st.error("로또번호.csv를 찾지 못했습니다. 저장소에 파일이 있는지 확인하세요.")

# 앱 로딩 시(또는 캐시가 없을 때) 자동 반영 1회
cache = load_cache()
if cache is None:
    last = rebuild_cache_from_csv()
    cache = load_cache()
    if cache is None:
        st.error("캐시 생성에 실패했습니다. 로또번호.csv 형식을 확인하세요.")
        st.stop()

# 생성 버튼
if st.button("추천 10게임 생성", type="primary"):
    games, hot10, cold10 = make_games(cache["freq"])
    result_text = format_result(cache["last_draw"], games)

    st.text_area("결과", value=result_text, height=320)
    st.download_button(
        "결과 TXT 다운로드",
        data=result_text.encode("utf-8"),
        file_name="lotto_recommendation.txt",
        mime="text/plain",
    )

    st.divider()
    st.write("HOT TOP10:", ", ".join(map(str, hot10)))
    st.write("COLD BOTTOM10:", ", ".join(map(str, cold10)))

else:
    st.info("버튼을 누르면 10게임 추천이 생성됩니다.")