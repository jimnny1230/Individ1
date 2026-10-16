import random
import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="NINO'S OHAASA",
    page_icon="🌼",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------- Theme ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&family=Noto+Sans+KR:wght@400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Nunito','Noto Sans KR',sans-serif; }
.stApp {
  background: linear-gradient(145deg, #fff0f4 0%, #fff8df 48%, #dcfff5 100%);
  color: #51404b;
}
.block-container { max-width: 760px; padding-top: 1.3rem; padding-bottom: 2rem; }
.hero {
  background: #23c5cf; border: 5px solid #087e91; border-radius: 26px;
  padding: 18px 16px; text-align: center; box-shadow: 0 7px 0 #f27e9e;
  margin-bottom: 20px;
}
.hero h1 { color: #fff6a8; font-weight: 900; font-size: clamp(1.6rem, 6vw, 2.6rem); margin: 0; text-shadow: 3px 3px #f06b91; }
.hero p { color: white; margin: 5px 0 0; font-weight: 800; letter-spacing: .15em; }
.card {
  background: rgba(255,255,255,.94); border-radius: 24px; padding: 22px;
  border-bottom: 6px solid #aeece5; margin: 15px 0; box-shadow: 0 3px 0 rgba(255,125,160,.12);
}
.kicker { letter-spacing: .18em; color: #218c99; font-size: .82rem; font-weight: 900; }
.rank { font-size: 3.5rem; line-height: 1.05; font-weight: 900; color: #ef668a; text-align:center; }
.small { color:#887986; font-size:.9rem; }
div.stButton > button {
  border: 0; border-radius: 18px; background: #21bec9; color: #064c5a;
  font-weight: 900; min-height: 3rem; box-shadow: 0 4px 0 #09899b;
}
div.stButton > button:hover { background:#48d1d8; color:#064c5a; border:0; }
a { color:#078f9c !important; font-weight:800; }
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <p>NINO'S MORNING NOTE</p>
  <h1>🌼 NINO SUNDAY 🌼</h1>
  <p>TODAY'S TAURUS REPORT</p>
</div>
""", unsafe_allow_html=True)

# Keep images inside the repository under images/
image_paths = sorted(Path("images").glob("nino_*.png"))
if image_paths:
    # Session state means the outfit stays stable during reruns until randomize is pressed.
    if "nino_image" not in st.session_state:
        st.session_state.nino_image = random.choice([str(p) for p in image_paths])
    left, center, right = st.columns([1, 5, 1])
    with center:
        st.image(st.session_state.nino_image, use_container_width=True)
    if st.button("🎀 니노 코디 바꾸기", use_container_width=True):
        choices = [str(p) for p in image_paths if str(p) != st.session_state.nino_image]
        st.session_state.nino_image = random.choice(choices or [str(image_paths[0])])
        st.rerun()
else:
    st.warning("images 폴더에 니노 이미지 6장을 넣어 주세요.")

st.markdown("""
<div class="card">
  <div class="kicker">TODAY'S TAURUS REPORT</div>
  <p>공식 오하아사 페이지에서 황소자리(おうし座)의 순위와 코멘트를 확인해 볼게.</p>
</div>
""", unsafe_allow_html=True)

OFFICIAL_URL = "https://www.asahi.co.jp/ohaasa/week/horoscope/"

def fetch_horoscope():
    """Best-effort parser. The official page may load its horoscope dynamically."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; NinoOhaasa/1.0)",
        "Accept-Language": "ja,en-US;q=0.8,en;q=0.7",
    }
    response = requests.get(OFFICIAL_URL, headers=headers, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")

    # Inspect the official HTML and any linked horoscope pages that look relevant.
    candidates = [(OFFICIAL_URL, soup)]
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(OFFICIAL_URL, a["href"])
        label = (a.get_text(" ", strip=True) + " " + href).lower()
        if "horoscope" in label or "星座" in label or "占い" in label:
            if href.startswith("https://www.asahi.co.jp/") and href != OFFICIAL_URL:
                links.append(href)
    for href in list(dict.fromkeys(links))[:5]:
        try:
            r = requests.get(href, headers=headers, timeout=10)
            if r.ok:
                r.encoding = r.apparent_encoding or r.encoding
                candidates.append((href, BeautifulSoup(r.text, "html.parser")))
        except requests.RequestException:
            pass

    # Taurus is おうし座. Try nearby rank text and common ranking patterns.
    for source_url, page in candidates:
        text = page.get_text("\n", strip=True)
        normalized = re.sub(r"[ \t]+", " ", text)
        patterns = [
            r"(\d{1,2})\s*位[\s\S]{0,100}おうし座",
            r"おうし座[\s\S]{0,100}?(\d{1,2})\s*位",
            r"(\d{1,2})\s*位[\s\S]{0,80}牡牛座",
            r"牡牛座[\s\S]{0,80}?(\d{1,2})\s*位",
        ]
        rank = None
        for pattern in patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match and 1 <= int(match.group(1)) <= 12:
                rank = int(match.group(1))
                break
        if rank:
            # Extract text around Taurus for a short comment if present.
            key = "おうし座" if "おうし座" in normalized else "牡牛座"
            pos = normalized.find(key)
            excerpt = normalized[max(0, pos-100):pos+400] if pos >= 0 else ""
            return {"rank": rank, "excerpt": excerpt, "source": source_url}

    # No rank found: do not invent a horoscope.
    raise ValueError("공식 페이지의 HTML에서 황소자리 순위를 찾지 못했어요. 페이지가 동적으로 표시되거나 구조가 바뀌었을 수 있어요.")

if "horoscope_result" not in st.session_state:
    st.session_state.horoscope_result = None
if "horoscope_error" not in st.session_state:
    st.session_state.horoscope_error = None

if st.button("🔎 오늘의 운세 확인 / 다시 확인", use_container_width=True):
    with st.spinner("공식 오하아사 페이지를 확인하고 있어…"):
        try:
            st.session_state.horoscope_result = fetch_horoscope()
            st.session_state.horoscope_error = None
        except Exception as exc:
            st.session_state.horoscope_result = None
            st.session_state.horoscope_error = str(exc)

result = st.session_state.horoscope_result
if result:
    st.markdown(f"""
    <div class="card">
      <div class="kicker">TODAY'S TAURUS RANKING · {date.today().isoformat()}</div>
      <div class="rank">{result['rank']}<span style="font-size:1.5rem">位</span></div>
      <p style="text-align:center;font-weight:800;">황소자리 · おうし座</p>
      <p class="small">순위가 감지됐어. 아래 공식 페이지에서 실제 운세 문구도 확인해 줘.</p>
    </div>
    """, unsafe_allow_html=True)
    if result.get("excerpt"):
        with st.expander("페이지에서 읽은 주변 문구 보기"):
            st.write(result["excerpt"])
    st.link_button("공식 오하아사 페이지 열기 ↗", OFFICIAL_URL, use_container_width=True)
elif st.session_state.horoscope_error:
    st.error("자동 확인에 실패했어. 확인되지 않은 순위를 임의로 표시하지 않을게.")
    st.caption(st.session_state.horoscope_error)
    st.link_button("공식 오하아사 별자리 페이지 열기 ↗", OFFICIAL_URL, use_container_width=True)
else:
    st.info("아직 오늘의 순위를 확인하지 않았어. 버튼을 눌러 공식 페이지를 확인해 줘.")
    st.link_button("공식 오하아사 별자리 페이지 열기 ↗", OFFICIAL_URL, use_container_width=True)

st.markdown("""
<div class="card">
  <div class="kicker">NINO'S MORNING NOTE</div>
  <p><b>ニノのひとこと：</b> う〜ん、ページがうまく読めないみたい。</p>
  <p class="small">운세를 자동으로 가져오지 못하면 공식 페이지를 직접 열어 확인할 수 있어. 자동 순위 확인은 공식 페이지의 구조에 따라 작동하지 않을 수 있어.</p>
</div>
<p style="text-align:center;color:#887986;font-size:.85rem;">おはよう！ NINO'S おはあさ<br>운세 정보는 아침의 작은 재미로만 즐겨 줘.</p>
""", unsafe_allow_html=True)
