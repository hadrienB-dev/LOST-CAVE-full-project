"""Chemins des ressources en développement et dans l'exécutable distribué."""

import sys
from pathlib import Path


RACINE_PROJET = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
)


def chemin_ressource(*parties):
    return str(RACINE_PROJET.joinpath(*parties))
