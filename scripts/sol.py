"""Décor de sol (l'acide)"""

import pyxel

from .config import (
    BANQUE_SOL,
    COULEUR_TRANSPARENCE,
    HAUTEUR_ECRAN,
    LARGEUR_ECRAN,
    ORIGINE_Y_SOL,
    TAILLE_TILE,
)


def dessiner_sol():
    """Évite les bandes vides sous les scènes de présentation."""
    position_y = HAUTEUR_ECRAN - TAILLE_TILE
    nombre_tiles = (LARGEUR_ECRAN + TAILLE_TILE - 1) // TAILLE_TILE
    for colonne in range(nombre_tiles):
        pyxel.blt(
            colonne * TAILLE_TILE, position_y,
            BANQUE_SOL, 0, ORIGINE_Y_SOL,
            TAILLE_TILE, TAILLE_TILE, COULEUR_TRANSPARENCE,
        )
