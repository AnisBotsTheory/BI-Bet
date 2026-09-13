"""
Calcul de la probabilité implicite du marché à partir d'une cote.
Identique quel que soit le sport - module 100% mutualisé.
"""


def probabilite_implicite_brute(cote: float) -> float:
    """Probabilité brute, cote non ajustée de la marge du bookmaker."""
    if cote <= 0:
        raise ValueError("La cote doit être strictement positive")
    return 1 / cote


def normaliser_marche(cotes: list[float]) -> list[float]:
    """
    Retire la marge du bookmaker (overround) pour obtenir des probabilités
    qui somment à 1. Exemple : cotes 1X2 d'un match de foot.
    """
    probas_brutes = [probabilite_implicite_brute(c) for c in cotes]
    total = sum(probas_brutes)
    return [p / total for p in probas_brutes]


def ecart_modele_vs_marche(proba_modele: float, proba_marche: float) -> float:
    """
    Écart entre la probabilité calculée par notre rating (proba_modele)
    et celle du marché (proba_marche, déjà normalisée).
    Positif = notre modèle est plus optimiste que le marché sur ce participant.
    """
    return proba_modele - proba_marche
