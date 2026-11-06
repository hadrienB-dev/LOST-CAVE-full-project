"""Déplacements, collisions et animation du personnage principal.

Le joueur est représenté par un dictionnaire afin de garder son état simple
à lire et à modifier dans le programme.
"""

from math import pi, sin

import pyxel

from .config import (
    BANQUE_JOUEUR,
    COULEUR_TRANSPARENCE,
    DEBUT_SPRITESHEET_SAUT,
    DUREE_SAUT_MAX_FRAMES,
    FORCE_SAUT_MAINTENU,
    GRAVITE,
    HAUTEUR_JOUEUR,
    LARGEUR_JOUEUR,
    TAILLE_TILE,
    TOLERANCE_SAUT_FRAMES,
    VITESSE_ANIMATION,
    VITESSE_DEPLACEMENT,
    VITESSE_SAUT,
    Y_DEPART,
)
from .tiled_map import (
    case_acide,
    case_collision_complete,
    case_solide,
    chevauche_collision_complete,
)


def creer_joueur():
    """Centralise l'état initial pour faciliter les réapparitions."""
    x_depart = 44
    return {
        "x_depart": x_depart,
        "y_depart": float(Y_DEPART),
        "x": x_depart,
        "y": float(Y_DEPART),
        "velocity_y": 0.0,
        "direction": 1,
        "moving": False,
        "au_sol": True,
        "saut_en_attente": 0,
        "duree_saut": 0,
        "impact_atterrissage": 0,
        "reapparition_demandee": False,
        "impact_camera_demandee": False,
    }


def mettre_a_jour_joueur(joueur, carte, deplacement_force=None):
    """Applique les contrôles avant la gravité pour conserver des collisions cohérentes."""
    joueur["impact_atterrissage"] = max(0, joueur["impact_atterrissage"] - 1)
    if deplacement_force is None:
        gerer_saut(joueur)
    deplacer_horizontalement(joueur, carte, deplacement_force)
    appliquer_gravite(joueur, carte)
    gerer_limites_carte(joueur, carte)
    if est_dans_acide(joueur, carte):
        joueur["reapparition_demandee"] = True


def est_dans_acide(joueur, carte):
    """Détecte si une case d'acide touche la hitbox du personnage."""
    # Le -1 inclut le dernier pixel couvert sans compter la tuile suivante.
    colonne_min = int(joueur["x"] // TAILLE_TILE)
    colonne_max = int((joueur["x"] + LARGEUR_JOUEUR - 1) // TAILLE_TILE)
    ligne_min = int(joueur["y"] // TAILLE_TILE)
    ligne_max = int((joueur["y"] + HAUTEUR_JOUEUR - 1) // TAILLE_TILE)
    return any(
        case_acide(carte, colonne, ligne)
        for ligne in range(ligne_min, ligne_max + 1)
        for colonne in range(colonne_min, colonne_max + 1)
    )


def reapparaitre_joueur(joueur):
    """Réinitialise toute la physique pour éviter de conserver l'élan de la mort."""
    joueur.update({
        "x": joueur["x_depart"],
        "y": joueur["y_depart"],
        "velocity_y": 0.0,
        "direction": 1,
        "moving": False,
        "au_sol": True,
        "saut_en_attente": 0,
        "duree_saut": 0,
        "impact_atterrissage": 0,
        "reapparition_demandee": False,
        "impact_camera_demandee": False,
    })


def deplacer_horizontalement(joueur, carte, deplacement_force=None):
    """Déplace le joueur si la nouvelle position ne traverse pas un mur."""
    joueur["moving"] = False
    deplacement = 0

    if deplacement_force is not None:
        deplacement = deplacement_force
        if deplacement != 0:
            joueur["direction"] = 1 if deplacement > 0 else -1
            joueur["moving"] = True
    elif pyxel.btn(pyxel.KEY_LEFT):
        deplacement = -VITESSE_DEPLACEMENT
        joueur["direction"] = -1
        joueur["moving"] = True
    elif pyxel.btn(pyxel.KEY_RIGHT):
        deplacement = VITESSE_DEPLACEMENT
        joueur["direction"] = 1
        joueur["moving"] = True

    x_candidat = joueur["x"] + deplacement
    if not chevauche_collision_complete(
        carte,
        x_candidat, joueur["y"], LARGEUR_JOUEUR, HAUTEUR_JOUEUR
    ):
        joueur["x"] = x_candidat


def gerer_saut(joueur):
    """Applique la tolérance de saut pour rendre les contrôles plus souples."""
    if pyxel.btnp(pyxel.KEY_SPACE):
        # Mémorise brièvement la demande pour accepter un saut juste avant l'atterrissage.
        joueur["saut_en_attente"] = TOLERANCE_SAUT_FRAMES

    if joueur["saut_en_attente"] > 0 and joueur["au_sol"]:
        joueur["velocity_y"] = VITESSE_SAUT
        joueur["au_sol"] = False
        joueur["saut_en_attente"] = 0
        joueur["duree_saut"] = 0
        pyxel.play(1, 1)
    elif joueur["saut_en_attente"] > 0:
        joueur["saut_en_attente"] -= 1


def appliquer_gravite(joueur, carte):
    """Calcule la chute puis corrige la position au contact des plateformes."""
    ancienne_y = joueur["y"]
    etait_au_sol = joueur["au_sol"]
    joueur["velocity_y"] += GRAVITE

    if (
        joueur["velocity_y"] < 0
        and joueur["duree_saut"] < DUREE_SAUT_MAX_FRAMES
        and pyxel.btn(pyxel.KEY_SPACE)
    ):
        # La hauteur dépend de la durée pendant laquelle le joueur maintient le bouton.
        joueur["velocity_y"] -= FORCE_SAUT_MAINTENU
        joueur["duree_saut"] += 1

    joueur["y"] += joueur["velocity_y"]
    if joueur["y"] < 0:
        joueur["y"] = 0
        joueur["velocity_y"] = 0
        joueur["au_sol"] = False
        return

    colonne_min = int(joueur["x"] // TAILLE_TILE)
    colonne_max = int((joueur["x"] + LARGEUR_JOUEUR - 1) // TAILLE_TILE)
    hauteur_carte = carte["carte_originale"]["height"]

    # Balayer les lignes entre les deux positions empêche de traverser un plafond
    # si la vitesse verticale dépasse l'épaisseur d'une tuile.
    if joueur["velocity_y"] < 0:
        premiere_ligne = max(0, int((joueur["y"] - 1) // TAILLE_TILE))
        derniere_ligne = min(hauteur_carte - 1, int((ancienne_y - 1) // TAILLE_TILE))
        for ligne in range(premiere_ligne, derniere_ligne + 1):
            bas_tuile = (ligne + 1) * TAILLE_TILE
            if joueur["y"] <= bas_tuile <= ancienne_y:
                for colonne in range(colonne_min, colonne_max + 1):
                    if case_collision_complete(carte, colonne, ligne):
                        joueur["y"] = bas_tuile
                        joueur["velocity_y"] = 0
                        joueur["au_sol"] = False
                        return

    joueur["au_sol"] = False
    # Le balayage descendant évite les traversées et aligne le bas du joueur
    # exactement sur la première plateforme rencontrée.
    if joueur["velocity_y"] > 0:
        ancien_bas = ancienne_y + HAUTEUR_JOUEUR
        nouveau_bas = joueur["y"] + HAUTEUR_JOUEUR
        premiere_ligne = max(0, int(ancien_bas // TAILLE_TILE))
        derniere_ligne = min(hauteur_carte - 1, int(nouveau_bas // TAILLE_TILE))
        for ligne in range(premiere_ligne, derniere_ligne + 1):
            haut_tuile = ligne * TAILLE_TILE
            if ancien_bas <= haut_tuile <= nouveau_bas:
                for colonne in range(colonne_min, colonne_max + 1):
                    if case_solide(carte, colonne, ligne):
                        joueur["y"] = haut_tuile - HAUTEUR_JOUEUR
                        joueur["velocity_y"] = 0
                        joueur["au_sol"] = True
                        if not etait_au_sol:
                            joueur["impact_atterrissage"] = 6
                            pyxel.play(1, 3)
                        return


def gerer_limites_carte(joueur, carte):
    """Empêche le personnage de sortir horizontalement du niveau."""
    joueur["x"] = max(
        0, min(joueur["x"], carte["largeur"] - LARGEUR_JOUEUR)
    )


def dessiner_joueur(joueur, camera_x=0, camera_y=0):
    """Choisit la frame adaptée puis dessine le personnage à l'écran."""
    if not joueur["au_sol"]:
        source_x = DEBUT_SPRITESHEET_SAUT
        source_y = 0 if joueur["direction"] == 1 else HAUTEUR_JOUEUR
    elif joueur["moving"]:
        frame = (pyxel.frame_count // VITESSE_ANIMATION) % 4
        source_x = frame * LARGEUR_JOUEUR
        source_y = 0 if joueur["direction"] == 1 else HAUTEUR_JOUEUR
    else:
        source_x = 0
        source_y = 0 if joueur["direction"] == 1 else HAUTEUR_JOUEUR

    echelle = 1.0
    if joueur["impact_atterrissage"] > 0:
        phase = joueur["impact_atterrissage"] / 6
        echelle -= 0.15 * sin(pi * phase)

    largeur = round(LARGEUR_JOUEUR * echelle)
    hauteur = round(HAUTEUR_JOUEUR * echelle)
    pyxel.blt(
        int(joueur["x"] + (LARGEUR_JOUEUR - largeur) / 2 - camera_x),
        int(joueur["y"] + HAUTEUR_JOUEUR - hauteur - camera_y),
        BANQUE_JOUEUR, source_x, source_y,
        LARGEUR_JOUEUR, HAUTEUR_JOUEUR, COULEUR_TRANSPARENCE, 0, echelle,
    )
