"""
Moteur de rating mutualisé entre tous les sports.

Pourquoi TrueSkill plutôt qu'un Elo classique :
- Elo est pensé nativement pour des duels à 2 (foot, tennis, MMA)
- TrueSkill gère nativement aussi bien les duels à 2 QUE les classements
  à n participants (hippique : 15 chevaux classés dans une même course)
  sans changer d'algorithme, juste en passant plus de participants.

C'est le SEUL module que tous les sports partagent à 100% sans adaptation.
Les features spécifiques à chaque sport (surface, musique, forme...) restent
dans features/<sport>_features.py et viennent compléter ce rating, pas le
remplacer.
"""

import trueskill

# Environnement TrueSkill unique et partagé pour la cohérence des ratings
# entre tous les sports (mu=25, sigma=25/3 sont les valeurs par défaut
# recommandées par la librairie).
_env = trueskill.TrueSkill(draw_probability=0.0)


def nouveau_rating() -> trueskill.Rating:
    """Rating initial pour un participant qui n'a pas encore d'historique."""
    return _env.create_rating()


def mettre_a_jour_duel(rating_gagnant: trueskill.Rating, rating_perdant: trueskill.Rating):
    """Cas foot / tennis / MMA : un gagnant, un perdant."""
    nouveau_gagnant, nouveau_perdant = _env.rate_1vs1(rating_gagnant, rating_perdant)
    return nouveau_gagnant, nouveau_perdant


def mettre_a_jour_classement(ratings_ordonnes: list[trueskill.Rating]):
    """
    Cas hippique : classement à n participants.
    `ratings_ordonnes` doit être trié du 1er (vainqueur) au dernier.
    Retourne les nouveaux ratings dans le même ordre.
    """
    groupes = [[r] for r in ratings_ordonnes]
    nouveaux_groupes = _env.rate(groupes, ranks=list(range(len(groupes))))
    return [g[0] for g in nouveaux_groupes]


def probabilite_victoire_duel(rating_a: trueskill.Rating, rating_b: trueskill.Rating) -> float:
    """Probabilité que le participant A batte le participant B."""
    delta_mu = rating_a.mu - rating_b.mu
    denom = (2 * (_env.beta ** 2) + rating_a.sigma ** 2 + rating_b.sigma ** 2) ** 0.5
    return _env.cdf(delta_mu / denom)


def score_affichable(rating: trueskill.Rating) -> float:
    """
    Score simple à afficher dans les dashboards (mu - 3*sigma) :
    pénalise les ratings encore incertains (peu d'historique).
    """
    return rating.mu - 3 * rating.sigma
