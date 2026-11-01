from typing import Any, NamedTuple

CLE_ETIQUETTE = "bf.faso.classification"
NIVEAUX = ("restreint", "confidentiel")


class BornesDuree(NamedTuple):
    minimum: int
    maximum: int


def valider_etiquette(etiquette: Any, bornes: BornesDuree) -> str | None:
    """Renvoie la raison du refus, ou None si l'étiquette est valide."""
    if not isinstance(etiquette, dict):
        return "l'étiquette doit être un objet"

    niveau = etiquette.get("niveau")
    if niveau not in NIVEAUX:
        return f"niveau inconnu ({niveau!r})"

    duree = etiquette.get("duree")
    if duree is None:
        if niveau == "confidentiel":
            return "un message confidentiel doit avoir un délai d'expiration"
        return None

    if isinstance(duree, bool) or not isinstance(duree, int):
        return "le délai doit être un nombre entier de secondes"
    if not bornes.minimum <= duree <= bornes.maximum:
        return f"le délai doit être compris entre {bornes.minimum} et {bornes.maximum} secondes"

    return None
