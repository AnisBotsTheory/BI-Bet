"""
Schéma de données commun, partagé par tous les sports.
Chaque connecteur de source (sources/*.py) doit produire des objets
conformes à ce schéma, quelle que soit la structure brute de l'API/CSV
d'origine. C'est ce qui permet au moteur de rating et aux dashboards
Streamlit de rester génériques.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Sport(str, Enum):
    FOOTBALL = "football"
    TENNIS = "tennis"
    HIPPIQUE = "hippique"
    MMA = "mma"


@dataclass
class Participant:
    """Un participant à un événement : équipe, joueur, cheval ou combattant."""
    id: str  # identifiant STABLE dans la source d'origine (ne pas régénérer)
    name: str
    sport: Sport
    meta: dict = field(default_factory=dict)  # ex: surface préférée, poids, corde...


@dataclass
class Event:
    """Un événement sportif générique : match, combat ou course."""
    id: str
    sport: Sport
    date: datetime
    participants: list[Participant]  # 2 pour foot/tennis/MMA, n pour hippique
    competition: Optional[str] = None
    meta: dict = field(default_factory=dict)
    brut: dict = field(default_factory=dict)  # réponse brute complète de la source, sans filtrage


@dataclass
class OddsSnapshot:
    """Une cote à un instant T pour un participant sur un événement."""
    event_id: str
    participant_id: str
    market: str  # ex: "1X2", "vainqueur", "over_2.5"
    odds: float
    captured_at: datetime
    bookmaker: Optional[str] = None


@dataclass
class Result:
    """Résultat final d'un événement."""
    event_id: str
    ranking: list[str]  # liste des participant_id, du 1er au dernier
    raw_score: Optional[dict] = None  # ex: {"home_goals": 2, "away_goals": 1}
