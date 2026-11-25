import streamlit as st
import requests
import base64
import time
import uuid
import hmac
import json
from hashlib import sha1
from PIL import Image
from io import BytesIO
from datetime import datetime
from pathlib import Path
import csv

# ============================================================
# AIGC Experiment 3
# 2 × 3 interface-complexity experiment
#
# B1 = Low  Feature Complexity
# B2 = High Feature Complexity
# A1 = Low  Design Complexity
# A2 = Mid  Design Complexity
# A3 = High Design Complexity
#
# API: LiblibAI OpenAPI
# ============================================================

st.set_page_config(
    page_title="AIGC 文生图实验",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).parent
RECORD_DIR = BASE_DIR / "records"
RECORD_DIR.mkdir(exist_ok=True)

LIBLIB_DOMAIN = "https://openapi.liblibai.cloud"
DEFAULT_TEMPLATE_UUID = "5d7e67009b344550bc1aa6ccbfa1d7f4"

# ------------------------------------------------------------
# 1. Session state
# ------------------------------------------------------------
defaults = {
    "participant": "",
    "feature": None,          # "B1" or "B2"
    "design": None,           # 1 / 2 / 3
    "page": "home",
    "api_ready": False,
    "api_config": {},
    "generated_images": [],
    "current_image": None,
    "current_duration": 0,
    "history": [],
    "events": [],
    "prompt": "",
    "negative_prompt": "",
    "generation_count": 0,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ------------------------------------------------------------
# 2. API configuration (secrets first, then manual page)
# ------------------------------------------------------------
def get_api_config_from_secrets():
    try:
        ak = st.secrets.get("LIBLIB_ACCESS_KEY", "")
        sk = st.secrets.get("LIBLIB_SECRET_KEY", "")
        tpl = st.secrets.get("LIBLIB_TEMPLATE_UUID", DEFAULT_TEMPLATE_UUID)
        if ak and sk:
            return {"ak": ak, "sk": sk, "tpl": tpl}
    except Exception:
        pass
    return None

secret_config = get_api_config_from_secrets()
if secret_config:
    st.session_state.api_config = secret_config
    st.session_state.api_ready = True

# ------------------------------------------------------------
# 3. Global CSS
# ------------------------------------------------------------
st.markdown("""
<style>
/* ==================== 全局 ==================== */
.stApp { background:#f5f8fc; }
.block-container { max-width:1500px; padding-top:.8rem; }
[data-testid="stHeader"] { background:transparent; }

/* ==================== B1 卡片（低特征复杂度） ==================== */
/* 设计原则：纯白、极简、无阴影、单色系、细线边框 */
[class*="st-key-b1card"] {
    background:#ffffff !important;
    border:1px solid #dfe6ef !important;
    border-radius:12px !important;
    box-shadow:none !important;
}
[class*="st-key-b1card"] h1,
[class*="st-key-b1card"] h2,
[class*="st-key-b1card"] h3 { color:#213f63; }

/* ==================== B2 卡片（高特征复杂度） ==================== */
/* 设计原则：多角径向光晕 + 渐变边框 + 双层彩色柔和阴影 + 内高光。
   复杂度体现在"卡片自身质感"而非外挂装饰条。 */
[class*="st-key-b2card"] {
    background:
        radial-gradient(circle at 0% 0%,     rgba(139,92,246,.10), transparent 42%),
        radial-gradient(circle at 100% 0%,   rgba(244,114,182,.08), transparent 40%),
        radial-gradient(circle at 100% 100%, rgba(32,200,255,.10),  transparent 42%),
        radial-gradient(circle at 0% 100%,   rgba(99,102,241,.06),  transparent 40%),
        linear-gradient(135deg, #ffffff 0%, #fdfcff 45%, #f8fdff 100%) !important;
    border:1.5px solid transparent !important;
    border-radius:14px !important;
    background-clip: padding-box !important;
    box-shadow:
        0 6px 24px rgba(139,92,246,.12),
        0 2px 8px  rgba(32,200,255,.10),
        inset 0 1px 0 rgba(255,255,255,.9) !important;
    position:relative !important;
    overflow:hidden !important;
}
/* 渐变边框（伪元素 + mask-composite） */
[class*="st-key-b2card"]::before {
    content:"";
    position:absolute; inset:0;
    border-radius:14px;
    padding:1.5px;
    background:linear-gradient(135deg,
        rgba(139,92,246,.55) 0%,
        rgba(32,200,255,.45) 50%,
        rgba(244,114,182,.55) 100%);
    -webkit-mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
            mask-composite: exclude;
    pointer-events:none;
}
[class*="st-key-b2card"] h1,
[class*="st-key-b2card"] h2,
[class*="st-key-b2card"] h3 { color:#453a8f; }

/* B2 增强的控件视觉（功能不变，仅视觉边缘/装饰变化） */
[class*="st-key-b2card"] textarea,
[class*="st-key-b2card"] input {
    border:1px solid #cfd0fa !important;
    background:linear-gradient(180deg,#ffffff,#fbfaff) !important;
    box-shadow:0 1px 4px rgba(139,92,246,.06) inset !important;
    border-radius:8px !important;
}
[class*="st-key-b2card"] div[data-baseweb="select"] > div {
    border:1px solid #cfd0fa !important;
    background:linear-gradient(180deg,#ffffff,#fbfaff) !important;
    border-radius:8px !important;
}
[class*="st-key-b2card"] button[kind="primary"] {
    background:linear-gradient(135deg,#8b5cf6 0%,#6366f1 50%,#20c8ff 100%) !important;
    border:none !important;
    box-shadow:
        0 6px 16px rgba(139,92,246,.35),
        0 2px 6px  rgba(32,200,255,.20),
        inset 0 1px 0 rgba(255,255,255,.35) !important;
    color:#fff !important;
    font-weight:750 !important;
}
[class*="st-key-b2card"] button[kind="secondary"] {
    border:1px solid #cfd0fa !important;
    background:linear-gradient(180deg,#ffffff,#f8f4ff) !important;
    color:#5b3ed6 !important;
}

/* ==================== 顶部工具栏 ==================== */
.app-topbar {
    height:58px; display:flex; align-items:center;
    padding:0 18px; border-radius:12px; margin-bottom:10px;
    box-sizing:border-box;
}
.app-topbar.b1 { background:#ffffff; border:1px solid #dfe7f1; box-shadow:none; }
.app-topbar.b2 {
    background:
        radial-gradient(circle at 5% 50%,   rgba(139,92,246,.10), transparent 30%),
        radial-gradient(circle at 95% 50%,  rgba(32,200,255,.10),  transparent 30%),
        linear-gradient(100deg, #ffffff 0%, #f3efff 30%, #eefbff 65%, #fff3f8 100%);
    border:1.5px solid transparent;
    background-clip: padding-box;
    box-shadow:
        0 6px 20px rgba(106,78,220,.12),
        0 2px 8px  rgba(32,200,255,.08);
    position:relative; overflow:hidden;
}
.app-topbar.b2::before {
    content:"";
    position:absolute; inset:0;
    border-radius:12px;
    padding:1.5px;
    background:linear-gradient(90deg,
        rgba(139,92,246,.55),
        rgba(32,200,255,.45) 50%,
        rgba(244,114,182,.55));
    -webkit-mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
            mask-composite: exclude;
    pointer-events:none;
}
.brand-mark {
    width:27px; height:27px; border-radius:8px;
    display:flex; align-items:center; justify-content:center;
    margin-right:9px; font-size:15px;
}
.app-topbar.b1 .brand-mark { color:#245fca; background:#edf4ff; }
.app-topbar.b2 .brand-mark {
    color:#fff;
    background:linear-gradient(135deg,#8b5cf6,#20c8ff);
    box-shadow:
        0 3px 10px rgba(139,92,246,.35),
        inset 0 1px 0 rgba(255,255,255,.40);
}
.brand-name { font-size:18px; font-weight:750; }
.app-topbar.b1 .brand-name { color:#183d69; }
.app-topbar.b2 .brand-name {
    background:linear-gradient(90deg,#5b3ed6,#0ea5e9);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    font-weight:800;
}
.topbar-spacer { flex:1; }
.condition-pill {
    font-size:11px; font-weight:700;
    border-radius:999px; padding:6px 12px; margin-right:10px;
}
.app-topbar.b1 .condition-pill {
    color:#35618e; background:#eef5ff; border:1px solid #dbe7f7;
}
.app-topbar.b2 .condition-pill {
    color:#fff; border:none;
    background:linear-gradient(90deg,#8b5cf6,#f472b6,#27c8f5);
    box-shadow:0 3px 10px rgba(139,92,246,.30);
}
.top-icon { font-size:14px; margin-left:14px; }
.app-topbar.b1 .top-icon { color:#71849b; }
.app-topbar.b2 .top-icon { color:#6f5cc8; }

/* ==================== 侧边导航 ==================== */
.side-nav {
    min-height:700px; padding:8px 5px;
    border-radius:12px; box-sizing:border-box;
}
.side-nav.b1 { background:#ffffff; border:1px solid #e0e7ef; }
.side-nav.b2 {
    background:
        radial-gradient(circle at 20% 10%, rgba(139,92,246,.08), transparent 40%),
        radial-gradient(circle at 80% 90%, rgba(32,200,255,.08), transparent 40%),
        linear-gradient(180deg,#fbf9ff,#f5fbff);
    border:1px solid #ddd9f6;
    box-shadow:0 4px 18px rgba(90,78,180,.08);
}
.nav {
    padding:11px 7px; border-radius:9px; margin-bottom:6px;
    font-size:14px; text-align:center; white-space:nowrap;
    position:relative;
}
.side-nav.b1 .nav { color:#66788f; }
.side-nav.b1 .nav.active {
    background:#eaf2ff; color:#1769d2; font-weight:700;
}
.side-nav.b2 .nav {
    color:#66788f;
    border:1px dashed #d9d2f0;
    background:linear-gradient(90deg,#ffffff,#faf7ff);
}
.side-nav.b2 .nav.active {
    color:#fff;
    background:linear-gradient(135deg,#7758f5,#4dbfff);
    box-shadow:
        0 5px 14px rgba(99,84,226,.20),
        inset 0 1px 0 rgba(255,255,255,.30);
    border:1px solid transparent;
}
/* B2 激活态：右侧小白点指示灯（常见 UI 细节，不是横条） */
.side-nav.b2 .nav.active::after {
    content:"";
    position:absolute; right:8px; top:50%; transform:translateY(-50%);
    width:5px; height:5px; border-radius:50%;
    background:#fff;
    box-shadow:0 0 6px rgba(255,255,255,.9);
}
.nav span { display:block; font-size:11px; margin-top:3px; }

/* ==================== 历史记录面板 ==================== */
.history-panel {
    border-radius:9px; margin-top:10px; padding:10px;
    font-size:12px;
}
.history-panel.b1 { border:1px solid #e1e7ef; background:#ffffff; color:#536a84; }
.history-panel.b2 {
    border:1px solid #ddd8f5; color:#536a84;
    background:
        radial-gradient(circle at 100% 0%, rgba(139,92,246,.06), transparent 45%),
        linear-gradient(90deg,#fbf9ff,#f5fdff);
    box-shadow:0 3px 12px rgba(90,78,180,.06);
}
.history-item { padding:7px 4px; font-size:11px; color:#65768c; }
.history-panel.b1 .history-item { border-bottom:1px solid #edf0f4; }
.history-panel.b2 .history-item { border-bottom:1px dashed #e6def7; }
.history-item:last-child { border-bottom:none; }
.version-item {
    border-radius:6px; padding:7px 9px; margin-top:5px;
    font-size:11px; color:#586b83;
}
.history-panel.b1 .version-item { background:#f5f7fa; }
.history-panel.b2 .version-item {
    background:linear-gradient(90deg,#f5f0ff,#eefaff);
    border-left:3px solid #8b5cf6;
}

/* ==================== 占位图 ==================== */
.image-placeholder {
    height:360px; border-radius:9px;
    display:flex; flex-direction:column;
    align-items:center; justify-content:center;
    font-size:12px;
}
.image-placeholder.b1 {
    border:1px dashed #cfd9e5; color:#9aa8b8; background:#fbfcfe;
}
.image-placeholder.b2 {
    border:1px dashed #cfc8f5; color:#9aa8b8;
    background:
        radial-gradient(circle at 30% 30%, rgba(139,92,246,.08), transparent 50%),
        radial-gradient(circle at 70% 70%, rgba(32,200,255,.08), transparent 50%),
        linear-gradient(135deg,#faf8ff,#f1fbff);
}
.placeholder-icon { font-size:28px; margin-bottom:8px; }
.image-placeholder.b1 .placeholder-icon { color:#b6c2d0; }
.image-placeholder.b2 .placeholder-icon {
    color:#8b5cf6;
    text-shadow:0 2px 12px rgba(139,92,246,.45);
}

/* ==================== 提示词语法框 ==================== */
.syntax-box { border-radius:8px; padding:10px; font-size:12px; color:#536a84; }
.syntax-box.b1 { border:1px solid #dce4ed; background:#fbfcfe; }
.syntax-box.b2 {
    border:1px solid #d8cff5;
    background:
        repeating-linear-gradient(45deg,
            transparent 0 6px,
            rgba(139,92,246,.03) 6px 12px),
        linear-gradient(135deg,#ffffff,#faf7ff);
    box-shadow:inset 0 1px 3px rgba(139,92,246,.05);
}
.syntax-add { float:right; color:#4c88df; }

/* ==================== 标题 ==================== */
.exp-title { font-size:26px; font-weight:800; color:#183d69; margin-bottom:6px; }
.exp-subtitle { font-size:14px; color:#63788f; margin-bottom:18px; }

/* ==================== 首页 / 设计选择卡片 ==================== */
.choice-card {
    border-radius:12px; padding:16px; box-sizing:border-box;
    min-height:120px;
}
.choice-card.b1 { background:#ffffff; border:1px solid #dfe6ef; }
.choice-card.b2 {
    background:
        radial-gradient(circle at 0% 0%,   rgba(139,92,246,.10), transparent 45%),
        radial-gradient(circle at 100% 100%, rgba(32,200,255,.10), transparent 45%),
        linear-gradient(135deg,#ffffff 0%,#faf8ff 40%,#f4fcff 100%);
    border:1.5px solid transparent;
    background-clip: padding-box;
    box-shadow:
        0 6px 20px rgba(90,78,180,.12),
        0 2px 8px  rgba(32,200,255,.08);
    position:relative;
}
.choice-card.b2::before {
    content:"";
    position:absolute; inset:0;
    border-radius:12px;
    padding:1.5px;
    background:linear-gradient(135deg,
        rgba(139,92,246,.55),
        rgba(32,200,255,.45) 50%,
        rgba(244,114,182,.55));
    -webkit-mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
            mask-composite: exclude;
    pointer-events:none;
}
.choice-card h3 { margin:6px 0 8px 0; }
.choice-card.b1 h3 { color:#213f63; }
.choice-card.b2 h3 { color:#453a8f; }
.condition-badge {
    display:inline-block; padding:3px 10px; border-radius:999px;
    font-size:11px; font-weight:700;
}
.choice-card.b1 .condition-badge {
    background:#edf3fb; color:#33577e; border:1px solid #dbe6f2;
}
.choice-card.b2 .condition-badge {
    background:linear-gradient(90deg,#8b5cf6,#20c8ff); color:#fff;
    border:none; box-shadow:0 2px 6px rgba(139,92,246,.30);
}

/* ==================== 响应式 ==================== */
@media(max-width:900px) {
    .block-container { padding-left:8px; padding-right:8px; }
    .side-nav { min-height:80px; }
    .nav span { display:none; }
}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# 4. Logging
# ------------------------------------------------------------
def log_event(event, detail=""):
    row = {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "participant": st.session_state.participant,
        "condition": f"A{st.session_state.design or '-'}B{st.session_state.feature or '-'}",
        "feature_complexity": st.session_state.feature or "",
        "design_complexity": st.session_state.design or "",
        "event": event,
        "detail": detail,
    }
    st.session_state.events.append(row)

def save_event_to_csv(row):
    path = RECORD_DIR / "experiment_events.csv"
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not exists:
            writer.writeheader()
        writer.writerow(row)

def record(event, detail=""):
    log_event(event, detail)
    save_event_to_csv(st.session_state.events[-1])


# ------------------------------------------------------------
# 5. LiblibAI API
# ------------------------------------------------------------
def liblib_request(uri, payload):
    cfg = st.session_state.api_config
    timestamp = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())

    content = "&".join((uri, timestamp, nonce))
    digest = hmac.new(cfg["sk"].encode(), content.encode(), sha1).digest()
    signature = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    params = {
        "AccessKey": cfg["ak"],
        "Signature": signature,
        "Timestamp": timestamp,
        "SignatureNonce": nonce,
    }
    try:
        response = requests.post(
            f"{LIBLIB_DOMAIN}{uri}", params=params, json=payload, timeout=60
        )
        return response.json()
    except Exception as e:
        st.error(f"API请求异常：{e}")
        return None


def generate_image(prompt, steps=30, width=1024, height=1024):
    start_time = time.time()
    payload = {
        "templateUuid": st.session_state.api_config["tpl"],
        "generateParams": {
            "prompt": prompt,
            "imgCount": 1,
            "steps": int(steps),
            "imageSize": {"width": int(width), "height": int(height)},
        },
    }
    submit = liblib_request("/api/generate/webui/text2img/ultra", payload)
    if not submit or submit.get("code") != 0:
        st.error(f"Liblib提交失败：{submit}")
        return None, 0
    task_id = submit.get("data", {}).get("generateUuid")
    if not task_id:
        st.error("未能获取生成任务UUID。")
        return None, 0

    for _ in range(60):
        status = liblib_request("/api/generate/webui/status", {"generateUuid": task_id})
        if not status or status.get("code") != 0:
            time.sleep(2); continue
        data = status.get("data", {})
        state = data.get("generateStatus")
        if state in [2, 5]:
            images = data.get("images", [])
            if images:
                image_url = images[0].get("imageUrl")
                image_data = requests.get(image_url, timeout=60).content
                image = Image.open(BytesIO(image_data)).convert("RGB")
                return image, time.time() - start_time
        if state in [3, 4]:
            st.error(f"生图任务失败，状态码：{state}")
            return None, 0
        time.sleep(2)
    st.error("生图超时，请检查Liblib任务状态或API配置。")
    return None, 0


# ------------------------------------------------------------
# 6. Helpers
# ------------------------------------------------------------
def current_condition():
    return f"A{st.session_state.design}B{st.session_state.feature}"

def width_height_from_ratio(ratio):
    return {"1:1": (1024, 1024), "4:3": (1024, 768), "16:9": (1024, 576)}[ratio]

def card_key(prefix, name, high_visual):
    """Generate a Streamlit container key that gets styled by B1 or B2 CSS."""
    stem = "b2card" if high_visual else "b1card"
    return f"{stem}_{prefix}_{name}"

def render_decor(high_visual):
    """B2 的视觉丰富度完全由 CSS 实现（多角径向光晕 + 渐变边框 + 彩色阴影）。
    此函数保留为空函数，避免逐处删除调用。"""
    return


# ------------------------------------------------------------
# 7. API setup page
# ------------------------------------------------------------
if not st.session_state.api_ready:
    st.markdown('<div class="exp-title">AIGC 文生图实验 · API配置</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="exp-subtitle">本地测试阶段可直接输入 LiblibAI 参数；正式部署建议使用 Streamlit Secrets。</div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown("### LiblibAI API")
        name = st.text_input("被试/测试编号", placeholder="例如 P001")
        ak = st.text_input("Liblib AccessKey", type="password")
        sk = st.text_input("Liblib SecretKey", type="password")
        tpl = st.text_input("Template UUID", value=DEFAULT_TEMPLATE_UUID)
        if st.button("连接 LiblibAI 并进入实验", type="primary", use_container_width=True):
            if not name.strip() or not ak.strip() or not sk.strip():
                st.error("请完整填写编号、AccessKey 和 SecretKey。")
            else:
                st.session_state.participant = name.strip()
                st.session_state.api_config = {"ak": ak.strip(), "sk": sk.strip(), "tpl": tpl.strip()}
                st.session_state.api_ready = True
                record("api_login", "manual_config")
                st.rerun()
    st.info("安全提醒：不要把 AccessKey / SecretKey 写进 GitHub 的 app.py。正式部署请使用 Streamlit Secrets。")
    st.stop()


# ------------------------------------------------------------
# 8. Home: choose B1 or B2
# ------------------------------------------------------------
if st.session_state.page == "home":
    st.markdown('<div class="exp-title">AIGC 文生图界面实验</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="exp-subtitle">实验条件：Feature Complexity (B) × Design Complexity (A)</div>',
        unsafe_allow_html=True,
    )
    st.write(f"当前被试：**{st.session_state.participant}**")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("""
        <div class="choice-card b1">
            <div class="condition-badge">B1</div>
            <h3>低特征复杂度</h3>
            <p style="color:#6b7b90;font-size:13px;line-height:1.6;">
            简洁、统一、低视觉变化。功能结构与 B2 对应条件保持一致。
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入 B1", use_container_width=True, type="primary", key="enter_b1"):
            st.session_state.feature = "B1"
            record("select_feature", "B1")
            st.session_state.page = "design_select"
            st.rerun()

    with c2:
        st.markdown("""
        <div class="choice-card b2">
            <div class="condition-badge">B2</div>
            <h3>高特征复杂度</h3>
            <p style="color:#6b7b90;font-size:13px;line-height:1.6;">
            在不增加功能数量的前提下，增加视觉层级、渐变边框、彩色阴影、图标风格变化与视觉分组。
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入 B2", use_container_width=True, key="enter_b2"):
            st.session_state.feature = "B2"
            record("select_feature", "B2")
            st.session_state.page = "design_select"
            st.rerun()


# ------------------------------------------------------------
# 9. Design-complexity selection
# ------------------------------------------------------------
elif st.session_state.page == "design_select":
    feature = st.session_state.feature
    high_visual = feature == "B2"

    st.markdown('<div class="exp-title">选择设计复杂度</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="exp-subtitle">当前特征复杂度：<b>{feature}</b></div>',
        unsafe_allow_html=True,
    )

    cards = [
        (1, "低设计复杂度", "仅保留正面提示词、图像展示和保存图片。"),
        (2, "中设计复杂度", "增加负面提示词、2–3 个基础参数、重新生成、变体及线性历史。"),
        (3, "高设计复杂度", "增加提示词权重、完整参数面板、高级设置、局部重绘、对比及版本管理。"),
    ]
    cols = st.columns(3)
    for col, (d, title, desc) in zip(cols, cards):
        with col:
            b_cls = "choice-card b2" if high_visual else "choice-card b1"
            st.markdown(f"""
            <div class="{b_cls}">
                <div class="condition-badge">A{d}</div>
                <h3>{title}</h3>
                <p style="color:#6b7b90;font-size:13px;line-height:1.6;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(
                f"进入 A{d}", key=f"enter_a{d}", use_container_width=True,
                type="primary" if d == 1 else "secondary",
            ):
                st.session_state.design = d
                record("select_design", f"A{d}")
                st.session_state.page = "interface"
                st.rerun()

    st.divider()
    if st.button("← 返回 B 选择"):
        st.session_state.page = "home"
        st.rerun()


# ------------------------------------------------------------
# 10. Main experiment interface
# ------------------------------------------------------------
elif st.session_state.page == "interface":
    feature = st.session_state.feature
    design = st.session_state.design
    high_visual = feature == "B2"

    # -------- top bar --------
    top_cls = "app-topbar b2" if high_visual else "app-topbar b1"
    st.markdown(f'''
    <div class="{top_cls}">
        <div class="brand-mark">✦</div>
        <div class="brand-name">Stable Diffusion</div>
        <div class="topbar-spacer"></div>
        <div class="condition-pill">A{design} B{feature[-1]}</div>
        <div class="top-icon">☼</div>
        <div class="top-icon">●</div>
        <div class="top-icon">⋮</div>
    </div>
    ''', unsafe_allow_html=True)

    # -------- sidebar + workspace --------
    sidebar_col, workspace_col = st.columns([0.12, 0.88], gap="small")

    with sidebar_col:
        side_cls = "side-nav b2" if high_visual else "side-nav b1"
        st.markdown(f'''
        <div class="{side_cls}">
            <div class="nav active">✦<span>生成</span></div>
            <div class="nav">◷<span>历史</span></div>
            <div class="nav">⚙<span>设置</span></div>
        </div>
        ''', unsafe_allow_html=True)

    with workspace_col:
        left, right = st.columns([1.02, 0.98], gap="medium")

        # ---------- left column: prompt + params ----------
        with left:
            with st.container(border=True, key=card_key("prompt", "main", high_visual)):
                st.markdown(
                    '<div style="color:#213f63;font-size:15px;font-weight:750;margin-bottom:10px;">✦ 提示词设置</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div style="color:#345272;font-size:12px;font-weight:700;margin:8px 0 6px;">正面提示词</div>',
                    unsafe_allow_html=True,
                )
                prompt = st.text_area(
                    "prompt", value=st.session_state.prompt, height=95,
                    placeholder="请输入正面提示词（如：一幅雪山湖泊的山川风景）",
                    key=f"prompt_{feature}_{design}", label_visibility="collapsed",
                )
                st.session_state.prompt = prompt

                if design >= 2:
                    st.markdown(
                        '<div style="color:#345272;font-size:12px;font-weight:700;margin:10px 0 6px;">负面提示词</div>',
                        unsafe_allow_html=True,
                    )
                    negative = st.text_area(
                        "negative", value=st.session_state.negative_prompt, height=70,
                        placeholder="请输入负面提示词（可选）",
                        key=f"negative_{feature}_{design}", label_visibility="collapsed",
                    )
                    st.session_state.negative_prompt = negative

                if design >= 3:
                    st.markdown(
                        '<div style="color:#345272;font-size:12px;font-weight:700;margin:10px 0 6px;">提示词权重 / 语法</div>',
                        unsafe_allow_html=True,
                    )
                    syntax_cls = "syntax-box b2" if high_visual else "syntax-box b1"
                    st.markdown(
                        f'<div class="{syntax_cls}">雪山 <b>[1.2]</b>&nbsp;&nbsp; 湖泊 <b>[1.0]</b>&nbsp;&nbsp; 蓝天 <b>[1.0]</b>'
                        f'<span class="syntax-add">＋ 添加</span></div>',
                        unsafe_allow_html=True,
                    )

            # -------- params card --------
            if design >= 2:
                with st.container(border=True, key=card_key("params", "main", high_visual)):
                    st.markdown(
                        '<div style="color:#213f63;font-size:15px;font-weight:750;margin-bottom:10px;">▦ 生成参数</div>',
                        unsafe_allow_html=True,
                    )

                    style, ratio, steps_basic = None, None, None
                    if design == 2:
                        p1, p2, p3 = st.columns(3)
                        with p1: style = st.selectbox("风格选择", ["写实", "动漫", "油画", "插画"], key=f"style_{feature}")
                        with p2: ratio = st.selectbox("宽高比", ["1:1", "4:3", "16:9"], key=f"ratio_{feature}")
                        with p3: steps_basic = st.selectbox("生成步数", [20, 25, 30], index=2, key=f"steps_basic_{feature}")

                    steps_adv = cfg = sampler = seed = ratio_adv = batch = None
                    if design >= 3:
                        p = st.columns(3)
                        with p[0]: steps_adv = st.number_input("Sampling Steps", 10, 60, 30, 1, key=f"steps_adv_{feature}")
                        with p[1]: cfg = st.number_input("CFG Scale", 1.0, 20.0, 7.5, 0.5, key=f"cfg_{feature}")
                        with p[2]: sampler = st.selectbox("Sampler", ["Euler a", "Euler", "DPM++ 2M"], key=f"sampler_{feature}")
                        p2 = st.columns(3)
                        with p2[0]: seed = st.number_input("Seed", 0, 999999999, 0, key=f"seed_{feature}")
                        with p2[1]: ratio_adv = st.selectbox("Image Size", ["1024×1024", "1024×768", "1024×576"], key=f"ratio_adv_{feature}")
                        with p2[2]: batch = st.number_input("Batch", 1, 4, 1, key=f"batch_{feature}")
                        with st.expander("高级设置"):
                            st.slider("Denoising Strength", 0.0, 1.0, 0.75)
                            st.checkbox("Face Restoration")
                            st.checkbox("High Resolution Fix")

                    # resolve API call values
                    if design == 1:
                        steps, width, height = 30, 1024, 1024
                        api_note = "A1 fixed"
                    elif design == 2:
                        steps = int(steps_basic)
                        width, height = width_height_from_ratio(ratio)
                        api_note = f"style={style}; ratio={ratio}"
                    else:
                        steps = int(steps_adv)
                        ratio_map = {"1024×1024": (1024, 1024), "1024×768": (1024, 768), "1024×576": (1024, 576)}
                        width, height = ratio_map[ratio_adv]
                        api_note = f"cfg={cfg}; sampler={sampler}; seed={seed}; batch={batch}"

                    if st.button(
                        "✦  生成" + ("（约 30s）" if design >= 2 else ""),
                        key=f"generate_{feature}_{design}",
                        use_container_width=True, type="primary",
                    ):
                        if not prompt.strip():
                            st.warning("请输入提示词后再生成。")
                        else:
                            with st.spinner("正在通过 LiblibAI 生成图片..."):
                                img, duration = generate_image(prompt=prompt, steps=steps, width=width, height=height)
                            if img is not None:
                                st.session_state.current_image = img
                                st.session_state.current_duration = duration
                                st.session_state.generation_count += 1
                                st.session_state.generated_images.append(img)
                                st.session_state.history.append({
                                    "time": datetime.now().strftime("%H:%M:%S"),
                                    "prompt": prompt, "duration": round(duration, 2),
                                })
                                record("generate", json.dumps({
                                    "api_steps": steps, "width": width, "height": height,
                                    "negative_prompt_length": len(st.session_state.negative_prompt),
                                    "ui_parameters": api_note,
                                    "generation_duration": round(duration, 3),
                                    "generation_count": st.session_state.generation_count,
                                }, ensure_ascii=False))
                                st.success(f"生成完成，用时 {duration:.2f} 秒。")

            # for A1 the generate button is outside the params card
            if design == 1:
                with st.container(border=True, key=card_key("generate", "main", high_visual)):
                    if st.button("✦  生成", key=f"generate_{feature}_{design}",
                                 use_container_width=True, type="primary"):
                        if not prompt.strip():
                            st.warning("请输入提示词后再生成。")
                        else:
                            with st.spinner("正在通过 LiblibAI 生成图片..."):
                                img, duration = generate_image(prompt=prompt, steps=30, width=1024, height=1024)
                            if img is not None:
                                st.session_state.current_image = img
                                st.session_state.current_duration = duration
                                st.session_state.generation_count += 1
                                st.session_state.generated_images.append(img)
                                st.session_state.history.append({
                                    "time": datetime.now().strftime("%H:%M:%S"),
                                    "prompt": prompt, "duration": round(duration, 2),
                                })
                                record("generate", json.dumps({
                                    "api_steps": 30, "width": 1024, "height": 1024,
                                    "ui_parameters": "A1 fixed",
                                    "generation_duration": round(duration, 3),
                                    "generation_count": st.session_state.generation_count,
                                }, ensure_ascii=False))
                                st.success(f"生成完成，用时 {duration:.2f} 秒。")

        # ---------- right column: result ----------
        with right:
            with st.container(border=True, key=card_key("result", "main", high_visual)):
                st.markdown(
                    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
                    '<div style="color:#213f63;font-size:15px;font-weight:750;">▣ 生成结果</div>'
                    f'<div style="color:#5e748d;font-size:11px;"><span style="color:#22b878;">●</span> 已完成 '
                    f'&nbsp;<small>{st.session_state.current_duration:.1f}s</small></div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                if st.session_state.current_image is not None:
                    st.image(st.session_state.current_image, use_container_width=True)
                    buf = BytesIO()
                    st.session_state.current_image.save(buf, format="PNG")
                    st.download_button(
                        "保存图片", data=buf.getvalue(),
                        file_name=f"{current_condition()}_generation.png",
                        mime="image/png", use_container_width=True,
                    )
                else:
                    ph_cls = "image-placeholder b2" if high_visual else "image-placeholder b1"
                    st.markdown(f'''
                    <div class="{ph_cls}">
                        <div class="placeholder-icon">✦</div>
                        <div>生成结果将在此显示</div>
                    </div>
                    ''', unsafe_allow_html=True)

            if design >= 2:
                with st.container(border=True, key=card_key("actions", "main", high_visual)):
                    a, b = st.columns(2)
                    with a:
                        if st.button("↻ 重新生成", use_container_width=True, key=f"regen_{feature}_{design}"):
                            if st.session_state.prompt.strip():
                                with st.spinner("正在重新生成..."):
                                    img, duration = generate_image(st.session_state.prompt, steps=30, width=1024, height=1024)
                                if img:
                                    st.session_state.current_image = img
                                    st.session_state.current_duration = duration
                                    st.session_state.generation_count += 1
                                    record("regenerate", f"duration={duration:.3f}")
                                    st.rerun()
                    with b:
                        if st.button("◇ 生成变体", use_container_width=True, key=f"variation_{feature}_{design}"):
                            if st.session_state.prompt.strip():
                                with st.spinner("正在生成变体..."):
                                    img, duration = generate_image(st.session_state.prompt, steps=30, width=1024, height=1024)
                                if img:
                                    st.session_state.current_image = img
                                    st.session_state.current_duration = duration
                                    st.session_state.generation_count += 1
                                    record("variation", f"duration={duration:.3f}")
                                    st.rerun()

                    if design >= 3:
                        a2, b2 = st.columns(2)
                        with a2:
                            if st.button("⌁ 局部重绘", use_container_width=True, key=f"inpaint_{feature}"):
                                record("inpaint_click")
                                st.info("局部重绘原型按钮已记录。")
                        with b2:
                            if st.button("◉ 对比视图", use_container_width=True, key=f"compare_{feature}"):
                                record("compare_click")
                                st.info("对比视图原型按钮已记录。")

            # -------- history --------
            if design >= 2:
                hist_cls = "history-panel b2" if high_visual else "history-panel b1"
                st.markdown(f'<div class="{hist_cls}"><b>历史记录</b>', unsafe_allow_html=True)
                if st.session_state.history:
                    for item in reversed(st.session_state.history[-5:]):
                        st.markdown(
                            f'<div class="history-item">生成结果 · {item["time"]} · {item["duration"]} s</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown('<div class="history-item">暂无生成记录</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            if design >= 3:
                hist_cls = "history-panel b2" if high_visual else "history-panel b1"
                st.markdown(f'<div class="{hist_cls}"><b>版本管理</b>', unsafe_allow_html=True)
                n = max(1, len(st.session_state.history))
                for i in range(n, 0, -1):
                    tag = "当前版本" if i == len(st.session_state.history) else "可恢复"
                    st.markdown(f'<div class="version-item">版本 {i} · {tag}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # -------- bottom navigation --------
    st.divider()
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("← 返回复杂度选择", use_container_width=True):
            st.session_state.page = "design_select"
            st.rerun()
    with c2:
        if st.button("返回首页", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
    with c3:
        data = json.dumps(st.session_state.events, ensure_ascii=False, indent=2)
        st.download_button(
            "下载当前测试日志", data=data,
            file_name=f"{st.session_state.participant}_{current_condition()}_events.json",
            mime="application/json", use_container_width=True,
        )