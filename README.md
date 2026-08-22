import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="Holland Family Fantasy", page_icon="🏈", layout="centered")

# ---------- Approximate Yahoo ADP order (top players first) ----------
YAHOO_ADP_ORDER = [
    "Jahmyr Gibbs", "Bijan Robinson", "Ja'Marr Chase", "Puka Nacua", "Christian McCaffrey",
    "Jaxon Smith-Njigba", "Jonathan Taylor", "Amon-Ra St. Brown", "CeeDee Lamb", "James Cook",
    "Justin Jefferson", "Ashton Jeanty", "De'Von Achane", "Saquon Barkley", "Chase Brown",
    "Drake London", "Josh Allen", "Omarion Hampton", "Derrick Henry", "Brock Bowers",
    "Nico Collins", "Kenneth Walker III", "George Pickens", "Trey McBride", "A.J. Brown",
    "Josh Jacobs", "Chris Olave", "Kyren Williams", "Malik Nabers", "Lamar Jackson",
    "Rashee Rice", "Tee Higgins", "Javonte Williams", "Tetairoa McMillan", "Breece Hall",
    "Travis Etienne", "Zay Flowers", "Drake Maye", "Cam Skattebo", "Joe Burrow",
    "Ladd McConkey", "Garrett Wilson", "Davante Adams", "Bucky Irving", "Jaylen Waddle",
    "Jayden Daniels", "Jalen Hurts", "Justin Herbert", "Caleb Williams", "Dak Prescott"
]

@st.cache_data(ttl=3600)
def get_sleeper_players():
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    data = response.json()
    
    players = []
    for pid, p in data.items():
        if p.get("active") and p.get("position") in ["QB", "RB", "WR", "TE"]:
            full_name = p.get("full_name") or f"{p.get('first_name','')} {p.get('last_name','')}".strip()
            team = p.get("team") or "FA"
            pos = p.get("position")
            if full_name:
                # Rank by Yahoo ADP if known, otherwise put later
                try:
                    adp_rank = YAHOO_ADP_ORDER.index(full_name) + 1
                except ValueError:
                    adp_rank = 9999
                
                players.append({
                    "name": full_name,
                    "position": pos,
                    "team": team,
                    "adp_rank": adp_rank,
                    "display": f"{full_name} ({pos} - {team})"
                })
    
    # Sort by ADP rank then name
    players.sort(key=lambda x: (x["adp_rank"], x["name"]))
    return players

# ---------- SESSION STATE ----------
if "teams" not in st.session_state:
    st.session_state.teams = {f"Team {i}": {"record": "0-0", "pf": 0.0, "captain": i<=2, "roster": []} for i in range(1,11)}

if "draft_order" not in st.session_state:
    st.session_state.draft_order = list(st.session_state.teams.keys())

if "current_pick" not in st.session_state:
    st.session_state.current_pick = 1

if "drafted_players" not in st.session_state:
    st.session_state.drafted_players = set()

if "trade_block" not in st.session_state:
    st.session_state.trade_block = {}

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

def get_current_team():
    total = len(st.session_state.draft_order)
    round_num = (st.session_state.current_pick - 1) // total + 1
    pick_in_round = (st.session_state.current_pick - 1) % total
    if round_num % 2 == 1:
        return st.session_state.draft_order[pick_in_round]
    return st.session_state.draft_order[-(pick_in_round + 1)]

def get_round():
    return (st.session_state.current_pick - 1) // len(st.session_state.draft_order) + 1

def rename_team(old, new):
    if new and new != old and new not in st.session_state.teams:
        st.session_state.teams[new] = st.session_state.teams.pop(old)
        st.session_state.draft_order = [new if t == old else t for t in st.session_state.draft_order]
        if old in st.session_state.trade_block:
            st.session_state.trade_block[new] = st.session_state.trade_block.pop(old)

all_players = get_sleeper_players()
available = [p for p in all_players if p["name"] not in st.session_state.drafted_players]

# ---------- SIDEBAR ----------
st.sidebar.title("🏈 Holland Fantasy 2026")
selected_team = st.sidebar.selectbox("Select Your Team", list(st.session_state.teams.keys()))

page = st.sidebar.radio("Navigation", [
    "🏠 Home / Standings",
    "⚔️ My Matchup",
    "📋 My Roster",
    "🎯 Draft Room",
    "📈 Waiver Wire",
    "🔄 Trade Block",
    "💬 League Chat",
    "🏆 Playoff Bracket",
    "✏️ Rename My Team"
])

# ---------- PAGES ----------
if page == "🏠 Home / Standings":
    st.title("🏆 League Standings")
    standings = sorted(st.session_state.teams.items(), key=lambda x: (-int(x[1]["record"].split("-")[0]), -x[1]["pf"]))
    for i, (name, data) in enumerate(standings, 1):
        cap = " ⭐" if data["captain"] else ""
        st.markdown(f"**#{i} {name}{cap}** — {data['record']} | PF: {data['pf']} | {len(data['roster'])} players")

elif page == "⚔️ My Matchup":
    st.title(f"⚔️ {selected_team} Matchup")
    st.info("Matchups appear once the season starts.")

elif page == "📋 My Roster":
    st.title(f"📋 {selected_team}")
    data = st.session_state.teams[selected_team]
    if data["captain"]:
        st.success("⭐ Team Captain")
    if not data["roster"]:
        st.info("No players yet.")
    else:
        for i, p in enumerate(data["roster"], 1):
            st.write(f"{i}. {p}")

elif page == "🎯 Draft Room":
    st.title("🎯 15-Round Snake Draft")
    total_picks = 150
    if st.session_state.current_pick > total_picks:
        st.success("Draft complete!")
    else:
        current = get_current_team()
        st.subheader(f"Round {get_round()} • Pick {st.session_state.current_pick}")
        st.info(f"**On the clock:** {current}")

        pos = st.selectbox("Filter", ["All", "QB", "RB", "WR", "TE"])
        filtered = available if pos == "All" else [p for p in available if p["position"] == pos]

        if filtered:
            options = [p["display"] for p in filtered]
            choice = st.selectbox("Player (sorted by Yahoo ADP)", options)
            player = next(p for p in filtered if p["display"] == choice)
            if st.button("Draft Player", type="primary"):
                st.session_state.teams[current]["roster"].append(player["display"])
                st.session_state.drafted_players.add(player["name"])
                st.session_state.current_pick += 1
                st.rerun()
        else:
            st.warning("No players left.")

    st.divider()
    st.write("**Draft Order:** " + " → ".join(st.session_state.draft_order))

elif page == "📈 Waiver Wire":
    st.title("📈 Waiver Wire (Yahoo ADP order)")
    st.write(f"{len(available)} players available")
    pos = st.selectbox("Position", ["All", "QB", "RB", "WR", "TE"], key="w")
    filtered = available if pos == "All" else [p for p in available if p["position"] == pos]
    for p in filtered[:200]:
        rank = f"ADP ~{p['adp_rank']}" if p["adp_rank"] < 9999 else ""
        st.write(f"{p['display']}  {rank}")

elif page == "🔄 Trade Block":
    st.title("🔄 Trade Block")
    if not st.session_state.trade_block:
        st.info("Nothing on the block yet.")
    else:
        for team, pls in st.session_state.trade_block.items():
            st.markdown(f"**{team}**")
            for p in pls:
                st.write(f"• {p}")
    st.divider()
    roster = st.session_state.teams[selected_team]["roster"]
    if roster:
        add = st.selectbox("Add from your roster", roster)
        if st.button("Put on Trade Block"):
            st.session_state.trade_block.setdefault(selected_team, []).append(add)
            st.rerun()

elif page == "💬 League Chat":
    st.title("💬 League Chat")
    for msg in st.session_state.chat_messages:
        st.markdown(f"**{msg['team']}** ({msg['time']}): {msg['text']}")
    msg = st.text_area("Message")
    if st.button("Send") and msg.strip():
        st.session_state.chat_messages.append({
            "team": selected_team,
            "text": msg.strip(),
            "time": datetime.now().strftime("%I:%M %p")
        })
        st.rerun()

elif page == "🏆 Playoff Bracket":
    st.title("🏆 Playoff Bracket")
    st.info("Top 6 by record → Points For tiebreaker. Seeds 1 & 2 get byes.")

elif page == "✏️ Rename My Team":
    st.title("✏️ Rename My Team")
    st.write(f"Current: **{selected_team}**")
    new = st.text_input("New name", value=selected_team)
    if st.button("Save") and new.strip() and new.strip() != selected_team:
        if new.strip() in st.session_state.teams:
            st.error("Name taken")
        else:
            rename_team(selected_team, new.strip())
            st.success(f"Renamed to {new.strip()}")
            st.rerun()

st.sidebar.caption("Live Sleeper players • Sorted by Yahoo ADP")
