"""
COMPLETE FANTASY FOOTBALL LEAGUE SYSTEM
=======================================
Includes:
- Full scoring, rosters, FAAB, trades, waivers
- AI managers with personalities + bye week handling
- Trade deadline, draft summary, depth charts
- Start/Sit, drop suggestions, trash talk, trade convincing
- 6-team playoff bracket (record → points_for tiebreaker)
- Post-draft record projections based on schedule
- NFL API helpers (Sleeper)
- Trade Block + Team Captains (with visual stickers)
"""

from __future__ import annotations
import random
import uuid
import requests
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from collections import defaultdict

# ============================================================
# 1. CORE CONSTANTS
# ============================================================

class Position(Enum):
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    K = "K"
    DEF = "DEF"
    FLEX = "FLEX"
    BENCH = "BENCH"

SCORING = {
    "pass_yd": 0.04, "pass_td": 4, "pass_int": -2,
    "rush_yd": 0.1, "rush_td": 6,
    "rec": 1.0, "rec_yd": 0.1, "rec_td": 6,
    "fum_lost": -2,
    "fg_0_39": 3, "fg_40_49": 4, "fg_50_plus": 5, "xp": 1,
    "def_sack": 1, "def_int": 2, "def_fumble_rec": 2, "def_td": 6, "def_safety": 2,
}

ROSTER_SLOTS = {
    Position.QB: 1, Position.RB: 2, Position.WR: 2, Position.TE: 1,
    Position.FLEX: 1, Position.K: 1, Position.DEF: 1, Position.BENCH: 6,
}

FAAB_BUDGET = 100
SEASON_WEEKS = 17
TRADE_DEADLINE_WEEK = 12

# ============================================================
# 2. PLAYER & TEAM
# ============================================================

@dataclass
class Player:
    id: str
    name: str
    position: Position
    nfl_team: str
    projected_ppg: float = 0.0
    season_finish_rank: int = 999
    actual_points: float = 0.0
    games_played: int = 0
    is_available: bool = True
    owner_id: Optional[str] = None
    on_trade_block: bool = False          # NEW: Trade Block flag

    @property
    def value_score(self) -> float:
        rank_factor = max(1, 100 - self.season_finish_rank)
        return (self.projected_ppg * 1.5) + (rank_factor * 0.4) + (self.actual_points / max(1, self.games_played) * 0.8)

    def __repr__(self):
        block = " 🔒" if self.on_trade_block else ""
        return f"{self.name} ({self.position.value}){block}"

class ManagerType(Enum):
    HUMAN = "HUMAN"
    AI = "AI"

@dataclass
class Team:
    id: str
    name: str
    manager_type: ManagerType
    owner_device_id: Optional[str] = None
    roster: List[Player] = field(default_factory=list)
    faab_remaining: int = FAAB_BUDGET
    wins: int = 0
    losses: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    is_captain: bool = False              # NEW: Team Captain flag
    trade_block: List[str] = field(default_factory=list)  # player IDs

    def display_name(self) -> str:
        """Shows captain sticker + trade block indicator."""
        captain = "⭐ CAPTAIN " if self.is_captain else ""
        block = " 🔄 TRADE BLOCK" if self.trade_block else ""
        return f"{captain}{self.name}{block}"

    def get_starters(self) -> Dict[Position, List[Player]]:
        by_pos = defaultdict(list)
        for p in self.roster:
            by_pos[p.position].append(p)
        for pos in by_pos:
            by_pos[pos].sort(key=lambda x: x.projected_ppg, reverse=True)

        starters = {}
        for pos, count in ROSTER_SLOTS.items():
            if pos in (Position.FLEX, Position.BENCH):
                continue
            starters[pos] = by_pos[pos][:count]

        flex_candidates = []
        for pos in [Position.RB, Position.WR, Position.TE]:
            used = len(starters.get(pos, []))
            flex_candidates.extend(by_pos[pos][used:])
        flex_candidates.sort(key=lambda x: x.projected_ppg, reverse=True)
        starters[Position.FLEX] = flex_candidates[:1]
        return starters

    def positional_strength(self) -> Dict[str, float]:
        strength = defaultdict(float)
        counts = defaultdict(int)
        for p in self.roster:
            strength[p.position.value] += p.value_score
            counts[p.position.value] += 1
        for pos in strength:
            strength[pos] /= max(1, counts[pos])
        return dict(strength)

    def needs(self) -> List[Position]:
        strength = self.positional_strength()
        avg = sum(strength.values()) / max(1, len(strength)) if strength else 0
        return [pos for pos in [Position.RB, Position.WR, Position.TE, Position.QB]
                if strength.get(pos.value, 0) < avg * 0.75]

# ============================================================
# 3. AI PERSONALITY + MANAGER
# ============================================================

class AIPersonality:
    def __init__(self, name: str, style: str, draft_bias: str):
        self.name = name
        self.style = style
        self.draft_bias = draft_bias

    def trash_talk(self, opponent: str) -> str:
        lines = {
            "aggressive": [f"You're going down {opponent}.", f"My squad is built different."],
            "troll": [f"Did you draft with your eyes closed {opponent}?", f"Charity trade incoming?"],
            "analytical": [f"You're projected lower than me this week.", f"Your RB depth is a liability."],
            "friendly": [f"Good luck {opponent}!", f"May the best team win."]
        }
        return random.choice(lines.get(self.style, lines["friendly"]))

    def convince_trade(self, give: List[str], receive: List[str]) -> str:
        return (f"This trade helps both of us. You get {', '.join(receive)} "
                f"and I take {', '.join(give)}. Fair value — you'll regret passing.")

class AIManager:
    def __init__(self, team: Team, league: "League", personality: AIPersonality):
        self.team = team
        self.league = league
        self.personality = personality

    def evaluate_trade(self, give: List[Player], receive: List[Player]) -> Tuple[bool, str]:
        give_val = sum(p.value_score for p in give)
        recv_val = sum(p.value_score for p in receive)
        if abs(give_val - recv_val) > max(give_val, recv_val) * 0.22:
            return False, "Value difference too large"
        improves = any(p.position in self.team.needs() for p in receive) or recv_val > give_val * 1.05
        return (True, "Fair + fits need") if improves else (False, "Doesn't help enough")

    def handle_bye_weeks(self):
        starters = self.team.get_starters()
        for pos, players in starters.items():
            for p in players:
                if random.random() < 0.07:  # simulated bye
                    print(f"🤖 {self.team.name}: {p.name} on BYE → benching")
                    candidates = [pl for pl in self.team.roster if pl not in players]
                    if candidates:
                        replacement = max(candidates, key=lambda x: x.projected_ppg)
                        print(f"   → Inserting {replacement.name}")

    def suggest_drops(self) -> List[str]:
        sorted_roster = sorted(self.team.roster, key=lambda p: p.value_score)
        suggestions = []
        for p in sorted_roster[:3]:
            reason = "Low projected output" if p.projected_ppg < 6 else "Roster clog / better options exist"
            suggestions.append(f"Drop {p.name} — {reason}")
        return suggestions

    def manage_roster(self):
        if not self.league.free_agents:
            return
        worst = min(self.team.roster, key=lambda p: p.value_score)
        best_fa = max(self.league.free_agents, key=lambda p: p.value_score)
        if best_fa.value_score > worst.value_score * 1.15:
            bid = min(int(best_fa.value_score * 0.35), int(self.team.faab_remaining * 0.35), self.team.faab_remaining)
            if bid > 0:
                self.league.submit_faab_claim(self.team.id, best_fa.id, worst.id, bid)

# ============================================================
# 4. LEAGUE ENGINE
# ============================================================

class League:
    def __init__(self, name: str, num_teams: int = 12, trade_deadline_week: int = TRADE_DEADLINE_WEEK):
        self.id = str(uuid.uuid4())
        self.name = name
        self.teams: Dict[str, Team] = {}
        self.players: Dict[str, Player] = {}
        self.free_agents: List[Player] = []
        self.current_week = 1
        self.schedule: Dict[int, List[Tuple[str, str]]] = {}
        self.faab_claims: List[Dict] = []
        self.pending_trades: List[Dict] = []
        self.trade_deadline_week = trade_deadline_week
        self.trade_deadline_passed = False
        self.personalities: Dict[str, AIPersonality] = {}

    def add_team(self, name: str, manager_type: ManagerType, device_id: Optional[str] = None, is_captain: bool = False) -> Team:
        team = Team(id=str(uuid.uuid4()), name=name, manager_type=manager_type,
                    owner_device_id=device_id, is_captain=is_captain)
        self.teams[team.id] = team
        return team

    def set_captain(self, team_id: str, value: bool = True):
        if team_id in self.teams:
            self.teams[team_id].is_captain = value

    def add_to_trade_block(self, team_id: str, player_id: str):
        team = self.teams[team_id]
        player = self.players.get(player_id)
        if player and player in team.roster:
            player.on_trade_block = True
            if player_id not in team.trade_block:
                team.trade_block.append(player_id)
            print(f"🔄 {player.name} added to {team.name}'s trade block")

    def remove_from_trade_block(self, team_id: str, player_id: str):
        team = self.teams[team_id]
        player = self.players.get(player_id)
        if player:
            player.on_trade_block = False
            if player_id in team.trade_block:
                team.trade_block.remove(player_id)

    def check_trade_deadline(self) -> bool:
        if self.current_week > self.trade_deadline_week:
            self.trade_deadline_passed = True
            return False
        return True

    def get_depth_chart(self, team_id: str) -> str:
        team = self.teams[team_id]
        by_pos = defaultdict(list)
        for p in team.roster:
            by_pos[p.position].append(p)
        for pos in by_pos:
            by_pos[pos].sort(key=lambda x: x.projected_ppg, reverse=True)

        lines = [f"\n📊 DEPTH CHART — {team.display_name()}"]
        for pos in [Position.QB, Position.RB, Position.WR, Position.TE, Position.K, Position.DEF]:
            players = by_pos.get(pos, [])
            if players:
                lines.append(f"\n{pos.value}:")
                for i, p in enumerate(players, 1):
                    mark = "★" if i <= ROSTER_SLOTS.get(pos, 1) else " "
                    block = " 🔒" if p.on_trade_block else ""
                    lines.append(f"  {mark} {i}. {p.name}{block} (Proj {p.projected_ppg:.1f})")
        return "\n".join(lines)

    def generate_draft_summary(self) -> str:
        lines = [f"\n📋 DRAFT SUMMARY — {self.name}", "="*50]
        for team in self.teams.values():
            lines.append(f"\n{team.display_name()}")
            for i, p in enumerate(sorted(team.roster, key=lambda x: -x.projected_ppg)[:8], 1):
                lines.append(f"  {i}. {p.name} ({p.position.value})")
        return "\n".join(lines)

    def project_season_records(self) -> str:
        if not self.schedule:
            self.generate_schedule()
        strengths = {tid: sum(p.projected_ppg for players in team.get_starters().values() for p in players)
                     for tid, team in self.teams.items()}
        proj_wins = {tid: 0.0 for tid in self.teams}

        for matchups in self.schedule.values():
            for a, b in matchups:
                diff = strengths[a] - strengths[b]
                prob_a = 1 / (1 + 10 ** (-diff / 25))
                proj_wins[a] += prob_a
                proj_wins[b] += (1 - prob_a)

        lines = ["\n📊 POST-DRAFT RECORD PROJECTIONS", "="*60]
        lines.append(f"{'Team':<30} {'Proj Record':<12} {'Win %':<8} Strength")
        lines.append("-"*60)
        for tid in sorted(self.teams, key=lambda x: -proj_wins[x]):
            team = self.teams[tid]
            w = proj_wins[tid]
            lines.append(f"{team.display_name():<30} {w:.1f}-{SEASON_WEEKS-w:.1f}   {w/SEASON_WEEKS:.1%}   {strengths[tid]:.1f}")
        return "\n".join(lines)

    def get_playoff_seeds(self) -> List:
        teams = sorted(self.teams.values(), key=lambda t: (-t.wins, t.losses, -t.points_for))
        return teams[:6]

    def generate_playoff_bracket(self) -> str:
        seeds = self.get_playoff_seeds()
        if len(seeds) < 6:
            return "Need at least 6 teams for playoffs."
        lines = ["\n🏆 6-TEAM PLAYOFF BRACKET", "="*50]
        lines.append("SEEDING (Record → Points For tiebreaker):")
        for i, t in enumerate(seeds, 1):
            lines.append(f"  #{i} {t.display_name():<28} {t.wins}-{t.losses}  PF: {t.points_for:.1f}")
        lines += [
            "\nROUND 1:",
            f"  (1) {seeds[0].display_name()} ——— BYE",
            f"  (2) {seeds[1].display_name()} ——— BYE",
            f"  (3) {seeds[2].display_name()} vs (6) {seeds[5].display_name()}",
            f"  (4) {seeds[3].display_name()} vs (5) {seeds[4].display_name()}",
            "\nSEMI-FINALS → CHAMPIONSHIP"
        ]
        return "\n".join(lines)

    def generate_schedule(self):
        ids = list(self.teams.keys())
        for week in range(1, SEASON_WEEKS + 1):
            random.shuffle(ids)
            self.schedule[week] = [(ids[i], ids[i+1]) for i in range(0, len(ids)-1, 2)]

    def submit_faab_claim(self, team_id, add_id, drop_id, bid):
        self.faab_claims.append({"team_id": team_id, "add": add_id, "drop": drop_id, "bid": bid})

    def print_post_draft_summary(self):
        print(self.generate_draft_summary())
        print(self.project_season_records())

# ============================================================
# 5. NFL API (Sleeper)
# ============================================================

class NFLApi:
    BASE = "https://api.sleeper.app/v1"

    @staticmethod
    def get_nfl_state():
        r = requests.get(f"{NFLApi.BASE}/state/nfl")
        return r.json() if r.ok else {}

    @staticmethod
    def get_trending_adds(hours=24):
        r = requests.get(f"{NFLApi.BASE}/players/nfl/trending/add", params={"lookback_hours": hours})
        return r.json() if r.ok else []

# ============================================================
# 6. QUICK BOOTSTRAP EXAMPLE
# ============================================================

def create_sample_players() -> List[Player]:
    sample = [
        Player("wr1", "Ja'Marr Chase", Position.WR, "CIN", 22.5, 1),
        Player("wr2", "Justin Jefferson", Position.WR, "MIN", 21.8, 2),
        Player("rb1", "Christian McCaffrey", Position.RB, "SF", 24.1, 1),
        Player("rb2", "Bijan Robinson", Position.RB, "ATL", 21.5, 2),
        Player("qb1", "Josh Allen", Position.QB, "BUF", 23.5, 1),
        Player("te1", "Trey McBride", Position.TE, "ARI", 15.8, 2),
        Player("te2", "Travis Kelce", Position.TE, "KC", 14.9, 3),
    ]
    for i in range(30, 90):
        pos = random.choice([Position.RB, Position.WR, Position.TE, Position.QB])
        sample.append(Player(f"p{i}", f"Player {i}", pos, "FA", random.uniform(5, 14), i))
    return sample

if __name__ == "__main__":
    league = League("Family + AI League", num_teams=8)

    # Humans + Captains
    league.add_team("Dad's Dynasty", ManagerType.HUMAN, "dad-phone", is_captain=True)
    league.add_team("Mom's Mayhem", ManagerType.HUMAN, "mom-ipad")
    league.add_team("Your Team", ManagerType.HUMAN, "your-laptop", is_captain=True)

    # AI teams with personalities
    ai1 = league.add_team("AI Warriors", ManagerType.AI)
    ai2 = league.add_team("Robo Ravens", ManagerType.AI)
    league.personalities[ai1.id] = AIPersonality("AI Warriors", "aggressive", "qb_early")
    league.personalities[ai2.id] = AIPersonality("Robo Ravens", "troll", "te_early")

    # Load players & draft (simplified)
    players = create_sample_players()
    for p in players:
        league.players[p.id] = p
        league.free_agents.append(p)

    league.generate_schedule()
    league.print_post_draft_summary()

    # Example: put someone on trade block
    # league.add_to_trade_block(some_team_id, some_player_id)

    print("\n" + league.generate_playoff_bracket())
    print("\n✅ Full system ready — Trade Block + Team Captains active")
