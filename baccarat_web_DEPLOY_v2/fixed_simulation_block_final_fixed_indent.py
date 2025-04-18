

ai_patterns = {
'BBBPB': '莊',
'PPPBP': '閒',
'PBBPB': '莊',
'BBPPP': '閒',
'BBBPP': '莊',
'PPBBB': '莊',
'BBPPB': '莊',
'PBPPP': '閒',
'BPPPB': '莊',
'PPPBB': '莊',
'PPBPB': '閒',
'BPBBB': '莊',
'PPPBB': '閒',
'PBBPP': '閒',
'PPBBP': '莊',
'BBPBB': '莊',
'PBBBP': '莊',
'BPPBB': '莊',
'PPPBP': '閒'
}

import streamlit as st
import json
import bcrypt
import random
import time
from collections import Counter
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="百家送你花 僅供參考 Le關心你", layout="wide")
USER_FILE = Path("users.json")

# 載入使用者資料
try:
    with open(USER_FILE, "r") as f:
        users = json.load(f)
except FileNotFoundError:
    users = {}

# 初始化登入狀態
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 登入流程
if not st.session_state.authenticated:
    tab1 = st.tabs(["🔐 登入"])[0]
with tab1:
    with st.form("login_form"):
        username = st.text_input("帳號")
        password = st.text_input("密碼", type="password")
        submitted = st.form_submit_button("登入")

    if submitted:
        if username in users and bcrypt.checkpw(password.encode(), users[username]["password"].encode()):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.role = users[username].get("role", "user")
            users[username]["last_login"] = datetime.now().isoformat()
            with open(USER_FILE, "w") as f:
                json.dump(users, f)
            st.success(f"✅ 歡迎 {username}！登入成功。")
            st.experimental_rerun()
        else:
            st.error("❌ 帳號或密碼錯誤，請再試一次")
st.stop()

# ===== 功能模組 =====
def show_simulator_tab():
    st.title("🎲 百家送你花 僅供參考 Le關心你")
if "deck" not in st.session_state:
    deck = []
    for _ in range(8):
        for card in range(1, 14):
            for _ in range(4):
                deck.append(card)
    random.shuffle(deck)
    
    st.session_state.deck = deck
    st.session_state.used_cards = []
    st.session_state.round_count = 0

st.write(f"目前剩餘牌數：{len(st.session_state.deck)} 張")

if st.checkbox("顯示剩餘牌分布"):
    count_remain = Counter(st.session_state.deck)
    for num in range(1, 14):
        name = {1: "A", 11: "J", 12: "Q", 13: "K"}.get(num, str(num))
        st.write(f"{name}: {count_remain[num]} 張")

    st.divider()
cards_input = st.text_input("請輸入本局開過的牌（空白隔開，例如：1 3 13 6 3）")

if st.button("模擬下一局勝率"):
    try:
        cards = list(map(int, cards_input.strip().split()))
        if not all(1 <= c <= 13 for c in cards):
            st.error("請輸入 1 到 13 的有效牌值")
        else:
            st.session_state.round_count += 1
            st.session_state.used_cards.extend(cards)
            st.session_state.deck = create_deck()
            st.session_state.deck = update_deck(
                st.session_state.deck,
                st.session_state.used_cards
            )
            if len(st.session_state.deck) < 6:
                st.warning("剩餘牌數不足，模擬結束")
            else:
                st.info(f"第 {st.session_state.round_count} 局模擬中...")

            start = time.time()
            result = simulate_with_draw_split(st.session_state.deck, simulations_per_round=40000, rounds=5)
            end = time.time()

            banker_adj = result['Banker Win Rate'] * 0.95
            banker_exp = banker_adj - result['Player Win Rate']
            player_exp = result['Player Win Rate'] - result['Banker Win Rate']

            st.subheader("模擬結果")
            st.write(f"莊勝率: {result['Banker Win Rate']*100:.2f}%")
            st.write(f"閒勝率: {result['Player Win Rate']*100:.2f}%")
            st.write(f"模擬耗時：{end - start:.2f} 秒")
            st.write(f"扣除抽水後莊勝率: {banker_adj*100:.2f}%")
            st.write(f"莊家期望值: {banker_exp*100:.2f}%")
            st.write(f"閒家期望值: {player_exp*100:.2f}%")

            better = "莊家" if banker_exp > player_exp else "閒家"
            st.success(f"建議下注：{better}")

            gap = abs(banker_exp - player_exp)
            if gap < 0.002:
                level = "低信心"
                mood = "局勢不明，建議觀望"
            elif gap < 0.005:
                level = "中信心"
                mood = "稍有優勢，穩紮穩打"
            else:
                level = "高信心"
                mood = "強烈推薦，大膽出手！"
                st.info(f"信心等級：{level} | 💬 {mood}")
try:
    start_time = time.time()
    result = simulate_with_draw_split(st.session_state.deck, simulations_per_round=50000, rounds=3)
    end_time = time.time()
    duration = end_time - start_time

    banker_odds = 100 / (result['Banker Win Rate'] * 100)
    player_odds = 100 / (result['Player Win Rate'] * 100)
    tie_odds = 100 / (result['Tie Rate'] * 100)
    adjusted_banker_rate = result['Banker Win Rate'] * 0.95

    banker_expectation = adjusted_banker_rate + result['Player Win Rate'] * -1
    player_expectation = result['Player Win Rate'] * 1 + result['Banker Win Rate'] * -1
    tie_expectation = result['Tie Rate'] * 8 * (1 - result['Tie Rate']) * -1

except Exception as e:
    st.error(f"❌ 模擬錯誤：{e}")


def simulate_with_draw_split(deck, simulations_per_round=10000, rounds=10):
    total_player_win = 0
    total_banker_win = 0
    total_tie = 0

    for _ in range(rounds):
    player_win = 0
    banker_win = 0
    tie = 0

    temp_deck = deck.copy()
    for _ in range(simulations_per_round):
        if len(temp_deck) < 6:
            temp_deck = deck.copy()
        random.shuffle(temp_deck)

        player_cards = [temp_deck.pop(), temp_deck.pop()]
        banker_cards = [temp_deck.pop(), temp_deck.pop()]

        def baccarat_value(card):
            return 0 if card >= 10 else card

        player_total = (baccarat_value(player_cards[0]) + baccarat_value(player_cards[1])) % 10
        banker_total = (baccarat_value(banker_cards[0]) + baccarat_value(banker_cards[1])) % 10

        player_third_card = None
        if player_total <= 5:
            player_third_card = baccarat_value(temp_deck.pop())
            player_total = (player_total + player_third_card) % 10

        def banker_should_draw(bt, ptc):
            if bt >= 7:
                return False
            if bt <= 2:
                return True
            if bt == 3:
                return ptc != 8
            if bt == 4:
                return 2 <= ptc <= 7
            if bt == 5:
                return 4 <= ptc <= 7
            if bt == 6:
                return 6 <= ptc <= 7
            return False

        if player_third_card is None:
            if banker_total <= 5:
                banker_total = (banker_total + baccarat_value(temp_deck.pop())) % 10
        else:
            if banker_should_draw(banker_total, player_third_card):
                banker_total = (banker_total + baccarat_value(temp_deck.pop())) % 10

        if player_total > banker_total:
            player_win += 1
        elif banker_total > player_total:
            banker_win += 1
        else:
            tie += 1

    total_player_win += player_win
    total_banker_win += banker_win
    total_tie += tie

total = total_player_win + total_banker_win + total_tie
return {
    "Player Win Rate": total_player_win / total,
    "Banker Win Rate": total_banker_win / total,
    "Tie Rate": total_tie / total
}

# 顯示主畫面
if st.session_state.role == "admin":
    tab1, tab2, tab3 = st.tabs(["👤 帳號管理後台", "🎴 百家樂模擬區", "📊 AI 趨勢分析"])

with tab2:
    show_simulator_tab()

with tab3:
show_trend_ai_tab()
with tab1:
    st.header("🔧 帳號管理後台")

    st.subheader("📋 所有帳號")
    if users:
        for user, data in users.items():
            created_time = data.get("created_at", "(未記錄)")
            last_login = data.get("last_login", "(從未登入)")
            st.write(f"👤 `{user}` - 權限：{data.get('role', 'user')} - 建立：{created_time} - 最後登入：{last_login}")
    else:
        st.write("目前尚無使用者資料。")

    st.divider()

    st.subheader("➕ 新增帳號")
    with st.form("add_user_form"):
        new_user = st.text_input("新帳號")
        new_pass = st.text_input("新密碼", type="password")
        submit_add = st.form_submit_button("新增帳號")
        if submit_add:
            if new_user in users:
                st.warning("❗ 此帳號已存在")
            elif len(new_pass) < 6:
                st.warning("❗ 密碼請至少6位數")
            else:
                hashed_pw = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                users[new_user] = {
                    "password": hashed_pw,
                    "role": "user",
                    "created_at": datetime.now().isoformat()
                }
                with open(USER_FILE, "w") as f:
                    json.dump(users, f)
                st.success(f"✅ 已新增帳號 `{new_user}`")

    st.subheader("🗑️ 刪除帳號")
    deletable_users = [u for u in users if u != st.session_state.username]
    if deletable_users:
        with st.form("delete_user_form"):
            del_user = st.selectbox("選擇帳號刪除", deletable_users)
            submit_del = st.form_submit_button("刪除帳號")
            if submit_del:
                users.pop(del_user)
                with open(USER_FILE, "w") as f:
                    json.dump(users, f)
                st.success(f"✅ `{del_user}` 已被刪除")
    else:
        st.info("（無可刪除的其他帳號）")

else:
    show_simulator_tab()
show_simulator_tab()
# AI樣式判斷規則（五局模式 + 推薦下注）
ai_patterns = [
    ("pppbp", "P", "✨ AI提示：可考慮續押閒"),
    ("bbbpb", "B", "✨ AI提示：可考慮續押莊"),
    ("bbpbp", "B", "✨ AI提示：可考慮續押莊"),
    ("ppppb", "B", "✨ AI提示：可考慮續押莊"),
    ("pbppp", "P", "✨ AI提示：可考慮續押閒"),
    ("ppppp", "P", "✨ AI提示：可考慮續押閒"),
    ("bbbbb", "B", "✨ AI提示：可考慮續押莊"),
    ("bpppp", "P", "✨ AI提示：可考慮續押閒"),
    ("pbbbb", "B", "✨ AI提示：可考慮續押莊"),
    ("ppbbb", "B", "✨ AI提示：可考慮續押莊"),
    ("bppbp", "P", "✨ AI提示：可考慮續押閒"),
    ("pbbpp", "P", "✨ AI提示：可考慮續押閒"),
    ("bpbpp", "P", "✨ AI提示：可考慮續押閒"),
    ("bppbb", "B", "✨ AI提示：可考慮續押莊"),
    ("ppbpp", "P", "✨ AI提示：可考慮續押閒"),
    ("ppbbp", "B", "✨ AI提示：可考慮續押莊"),
    ("bbppp", "P", "✨ AI提示：可考慮續押閒"),
    ("bbppb", "B", "✨ AI提示：可考慮續押莊"),
    ("bpppp", "P", "✨ AI提示：可考慮續押閒"),
    ("ppbpb", "B", "✨ AI提示：可考慮續押莊"),
    ("bpbbp", "B", "✨ AI提示：可考慮續押莊"),
    ("pbppb", "B", "✨ AI提示：可考慮續押莊"),
    ("pbbpb", "B", "✨ AI提示：可考慮續押莊"),
    ("bpbpb", "B", "✨ AI提示：可考慮續押莊"),
    ("pppbb", "B", "✨ AI提示：可考慮續押莊"),
    ("pbbbp", "P", "✨ AI提示：可考慮續押閒"),
    ("bbpbp", "B", "✨ AI提示：可考慮續押莊"),
    ("bpbbb", "B", "✨ AI提示：可考慮續押莊"),
    ("pbpbp", "P", "✨ AI提示：可考慮續押閒"),
    ("ppppb", "B", "✨ AI提示：可考慮續押莊"),
    ("bpppb", "B", "✨ AI提示：可考慮續押莊"),
    ("ppppp", "P", "✨ AI提示：可考慮續押閒"),
    ("ppbpp", "P", "✨ AI提示：可考慮續押閒"),
    ("bbbbb", "B", "✨ AI提示：可考慮續押莊"),
    ("bbbpb", "B", "✨ AI提示：可考慮續押莊"),
    ("ppbbp", "B", "✨ AI提示：可考慮續押莊"),
    ("bppbp", "P", "✨ AI提示：可考慮續押閒"),
    ("pbbpp", "P", "✨ AI提示：可考慮續押閒"),
    ("bpbpp", "P", "✨ AI提示：可考慮續押閒"),
    ("bppbb", "B", "✨ AI提示：可考慮續押莊"),
    ("ppbpp", "P", "✨ AI提示：可考慮續押閒"),
    ("ppbbp", "B", "✨ AI提示：可考慮續押莊"),
    ("bbppp", "P", "✨ AI提示：可考慮續押閒"),
    ("bbppb", "B", "✨ AI提示：可考慮續押莊"),
    ("pbppb", "B", "✨ AI提示：可考慮續押莊"),
    ("pbbpb", "B", "✨ AI提示：可考慮續押莊"),
    ("ppbpb", "B", "✨ AI提示：可考慮續押莊"),
    ("bpbbp", "B", "✨ AI提示：可考慮續押莊"),
    ("bpbpb", "B", "✨ AI提示：可考慮續押莊"),
    ("ppppb", "B", "✨ AI提示：可考慮續押莊"),
    ("pbppp", "P", "✨ AI提示：可考慮續押閒"),
]

def show_trend_ai_tab():
    st.header("📈 AI 趨勢分析區")
    st.markdown("這裡將展示下注走勢、下注記錄、期望值與推薦等資訊，協助你做出更聰明的決策。")

    if "trend_data" not in st.session_state:
    st.session_state.trend_data = []

    st.subheader("🎯 請點選你剛剛實際下注的結果")
    col1, col2, col3 = st.columns(3)
    if col1.button("下注莊"):
    st.session_state.trend_data.append("B")
    if col2.button("下注閒"):
    st.session_state.trend_data.append("P")
    if col3.button("下注和"):
    st.session_state.trend_data.append("T")

    st.markdown(f"目前走勢紀錄：{' → '.join(st.session_state.trend_data)}")

    if len(st.session_state.trend_data) >= 65:
    st.warning("🔚 已達模擬局數上限（65局），建議重新開始新一局。")
    st.stop()

    if len(st.session_state.trend_data) >= 5:
    pattern = ''.join(st.session_state.trend_data[-5:])
    st.info(f"最近五局模式：{pattern}")
    for ai_pattern, ai_suggestion, ai_message in ai_patterns:
    if pattern == ai_pattern:
        st.success(f"✨ AI建議：建議第六局下注【{ai_suggestion}】！{ai_message}")
        break
    else:
    st.warning("📉 AI提示：目前無明顯趨勢，請小心操作")


    if st.button("🔄 重設下注記錄"):
    st.session_state.trend_data = []
