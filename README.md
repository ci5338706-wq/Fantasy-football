import streamlit as st
import random
from datetime import datetime

st.set_page_config(
    page_title="Holland Family Fantasy",
    page_icon="🏈",
    layout="centered"
)

# ---------- DATA ----------
teams = {
    "Dad's Dynasty": {
        "record": "3-1",
        "pf": 412.5,
        "captain": True,
        "roster": ["Ja'Marr Chase", "Bijan Robinson", "Josh Allen", "Trey McBride", "DK Metcalf", "Rachaad White"]
    },
    "Mom's Mayhem": {
        "record": "2-2",
        "pf": 389.1,
        "captain": False,
        "roster": ["Justin Jefferson", "Breece Hall", "Lamar Jackson", "Mark Andrews", "Chris Olave", "Javonte Williams"]
    },
    "Your Team": {
        "record": "4-0",
        "pf": 445.8,
        "captain": True,
        "roster": ["CeeDee Lamb", "Christian McCaffrey", "Jalen Hurts", "Travis Kelce", "Amon-Ra St. Brown", "James Cook"]
    },
    "Sister's Squad": {
        "record": "1-3",
        "pf": 356.4,
        "captain": False,
        "roster": ["Tyreek Hill", "Saquon Barkley", "Patrick Mahomes", "Sam LaPorta", "Garrett Wilson", "Ray Davis"]
    },
    "AI Warriors": {
        "record": "2-2",
        "pf": 401.2,
        "captain": False,
        "roster": ["A.J. Brown", "Jahmyr Gibbs", "Dak Prescott", "George Kittle", "DeVonta Smith", "Xavier Legette"]
    },
    "Robo Ravens": {
        "record": "3-1",
        "pf": 428.7,
        "captain": False,
        "roster": ["Puka Nacua", "Jonathan Taylor", "Joe Burrow", "Evan Engram", "Nico Collins", "Josh Downs"]
    }
}

free_agents = [
    "Caleb Williams", "Rome Odunze", "MarShawn Lloyd", "Keon Coleman",
    "Trey Benson", "Ladd McConkey", "Brian Thomas Jr.", "Kimani Vidal"
]

trade_block = {
    "Dad's Dynasty": ["DK Metcalf"],
    "Mom's Mayhem": ["Chris Olave"],
    "AI Warriors": ["DeVonta Smith"]
}

# ---------- SIDEBAR ----------
st.sidebar.title("🏈 Holland Fantasy 2026")
selected_team = st.sidebar.selectbox("Select Your Team", list(teams.keys()))

page = st.sidebar.radio("Go to", [
    "Home / Standings",
    "My Roster",
    "Waiver Wire",
    "Trade Block",
    "Playoff Bracket",
    "AI Suggestions"
])

# ---------- PAGES ----------
if page == "Home / Standings":
    st.title("🏆 Holland Family Fantasy")
    st.caption(f"Updated {datetime.now().strftime('%b %d, %Y')}")

    st.subheader("Current Standings")
    standings = sorted(teams.items(), key=lambda x: (-int(x[1]["record"].split("-")[0]), -x[1]["pf"]))

    for i, (name, data) in enumerate(standings, 1):
        captain = " ⭐" if data["captain"] else ""
        st.markdown(f"**#{i} {name}{captain}**  \n{data['record']} • PF: {data['pf']}")

elif page == "My Roster":
    st.title(f"📋 {selected_team}")
    data = teams[selected_team]

    if data["captain"]:
        st.success("⭐ Team Captain")

    st.subheader("Depth Chart")
    for i, player in enumerate(data["roster"], 1):
        on_block = " 🔒" if player in trade_block.get(selected_team, []) else ""
        st.write(f"{i}. {player}{on_block}")

elif page == "Waiver Wire":
    st.title("📈 Waiver Wire")
    st.write("Available players:")
    for i, player in enumerate(free_agents, 1):
        st.write(f"{i}. {player}")

    st.divider()
    claim = st.selectbox("Submit FAAB claim for:", free_agents)
    bid = st.slider("FAAB Bid ($)", 1, 50, 10)
    if st.button("Submit Claim"):
        st.success(f"✅ Claim submitted: {claim} for ${bid}")

elif page == "Trade Block":
    st.title("🔄 Trade Block")
    for team, players in trade_block.items():
        st.markdown(f"**{team}**")
        for p in players:
            st.write(f"• {p}")
        st.write("")

    st.divider()
    st.subheader("Propose a Trade")
    target = st.selectbox("Trade with:", [t for t in teams if t != selected_team])
    give = st.multiselect("You give:", teams[selected_team]["roster"])
    receive = st.multiselect("You receive:", teams[target]["roster"])
    if st.button("Send Trade Offer"):
        st.success(f"Trade offer sent to {target}!")

elif page == "Playoff Bracket":
    st.title("🏆 6-Team Playoff Bracket")
    seeds = sorted(teams.items(), key=lambda x: (-int(x[1]["record"].split("-")[0]), -x[1]["pf"]))[:6]

    st.write("**Current Seeding**")
    for i, (name, data) in enumerate(seeds, 1):
        st.write(f"#{i} {name} — {data['record']} | PF: {data['pf']}")

    st.divider()
    st.write("**Round 1**")
    st.write(f"(1) {seeds[0][0]} — BYE")
    st.write(f"(2) {seeds[1][0]} — BYE")
    st.write(f"(3) {seeds[2][0]} vs (6) {seeds[5][0]}")
    st.write(f"(4) {seeds[3][0]} vs (5) {seeds[4][0]}")

elif page == "AI Suggestions":
    st.title("🤖 AI Suggestions")
    st.write(f"For **{selected_team}**")

    st.subheader("Start / Sit")
    st.info("Start your top projected players. Sit anyone on bye or with a tough matchup.")

    st.subheader("Possible Drops")
    st.warning("Consider dropping lower-value players if better free agents are available.")

    st.subheader("Trade Idea")
    st.success("Look to upgrade weak positions by trading surplus depth.")

st.sidebar.markdown("---")
st.sidebar.caption("Holland Family League 2
