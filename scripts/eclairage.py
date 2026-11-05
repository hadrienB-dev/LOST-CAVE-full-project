"""Éclairage radial du niveau."""

import ctypes
from math import isqrt, pi, sin

import pyxel

from .config import (
    FONDU_LUMIERE,
    DEBUT_TRANSITION_ECLAIRAGE_X,
    DUREE_TRANSITION_ECLAIRAGE,
    HAUTEUR_JOUEUR,
    LARGEUR_JOUEUR,
    LUMINOSITE_AMBIANTE,
    NIVEAUX_ECLAIRAGE,
    PERIODE_VARIATION_LUMIERE,
    RAYON_LUMIERE,
    VARIATION_RAYON_LUMIERE,
)


_ECHELLE_SOUS_PIXEL = 8
_INDICE_AMBIANCE = 0


def _plafond_division(valeur, diviseur):
    """Arrondit une borne vers le haut pour ne pas couper la zone éclairée."""
    return -(-valeur // diviseur)


def creer_eclairage():
    """Précalcule les tables de couleurs et de distances utilisées à l'écran."""
    couleurs = _creer_table_couleurs()
    couleurs_progression = _creer_tables_progression(couleurs)
    distance_max = (RAYON_LUMIERE + FONDU_LUMIERE) * _ECHELLE_SOUS_PIXEL

    # La table remplace les calculs de distance et de luminosité à chaque pixel.
    indices_distance = bytes(
        _indice_luminosite(
            isqrt(distance_carree) // _ECHELLE_SOUS_PIXEL
        )
        for distance_carree in range(distance_max * distance_max + 1)
    )
    traductions_ambiance = tuple(
        bytes(
            table[_INDICE_AMBIANCE][couleur] if couleur < 16 else couleur
            for couleur in range(256)
        )
        for table in couleurs_progression
    )
    return {
        "couleurs": couleurs,
        "couleurs_progression": couleurs_progression,
        "indice_ambiance": _INDICE_AMBIANCE,
        "indices_distance": indices_distance,
        "traductions_ambiance": traductions_ambiance,
    }


def _composantes_rgb(couleur):
    return couleur >> 16 & 255, couleur >> 8 & 255, couleur & 255


def _creer_table_couleurs():
    """Associe chaque teinte assombrie à la couleur Pyxel la plus proche."""
    palette = [_composantes_rgb(pyxel.colors[index]) for index in range(16)]
    table = []

    for niveau in range(NIVEAUX_ECLAIRAGE):
        luminosite = LUMINOSITE_AMBIANTE + (
            (1 - LUMINOSITE_AMBIANTE) * niveau / (NIVEAUX_ECLAIRAGE - 1)
        )
        couleurs_niveau = []
        for rouge, vert, bleu in palette:
            couleur_cible = (
                rouge * luminosite,
                vert * luminosite,
                bleu * luminosite,
            )
            couleur_proche = min(
                range(len(palette)),
                key=lambda index: sum(
                    (composante - cible) ** 2
                    for composante, cible in zip(palette[index], couleur_cible)
                ),
            )
            couleurs_niveau.append(couleur_proche)
        table.append(couleurs_niveau)

    return table


def _creer_tables_progression(couleurs):
    """Prépare les palettes pour dissiper progressivement la pénombre."""
    tables = []
    for progression in range(NIVEAUX_ECLAIRAGE + 1):
        intensite = progression / NIVEAUX_ECLAIRAGE
        table = []
        for niveau, couleurs_niveau in enumerate(couleurs):
            intensite_lumiere = (
                LUMINOSITE_AMBIANTE
                + (1 - LUMINOSITE_AMBIANTE)
                * niveau / (NIVEAUX_ECLAIRAGE - 1)
            )
            intensite_lumiere += (
                (1 - intensite_lumiere) * intensite
            )
            table.append(_mapper_couleurs(intensite_lumiere))
        tables.append(table)
    return tuple(tables)


def _mapper_couleurs(intensite):
    palette = [_composantes_rgb(pyxel.colors[index]) for index in range(16)]
    return [
        min(
            range(len(palette)),
            key=lambda index: sum(
                (composante - cible) ** 2
                for composante, cible in zip(
                    palette[index],
                    (rouge * intensite, vert * intensite, bleu * intensite),
                )
            ),
        )
        for rouge, vert, bleu in palette
    ]


def _indice_luminosite(distance):
    """Convertit une distance en niveau discret de la palette."""
    if distance <= RAYON_LUMIERE:
        return NIVEAUX_ECLAIRAGE - 1
    if FONDU_LUMIERE == 0 or distance >= RAYON_LUMIERE + FONDU_LUMIERE:
        return _INDICE_AMBIANCE

    progression = (distance - RAYON_LUMIERE) / FONDU_LUMIERE
    return round((1 - progression) * (NIVEAUX_ECLAIRAGE - 1))


def _rayon_courant(frame_count):
    """Fait varier légèrement le rayon pour animer la lumière sans à-coups."""
    phase = 2 * pi * frame_count / PERIODE_VARIATION_LUMIERE
    rayon = RAYON_LUMIERE + VARIATION_RAYON_LUMIERE * sin(phase)
    return round(rayon * _ECHELLE_SOUS_PIXEL)


def _indice_progression_eclairage(joueur_x):
    if DUREE_TRANSITION_ECLAIRAGE <= 0:
        return NIVEAUX_ECLAIRAGE
    progression = (
        joueur_x - DEBUT_TRANSITION_ECLAIRAGE_X
    ) / DUREE_TRANSITION_ECLAIRAGE
    return round(
        max(0, min(1, progression)) * NIVEAUX_ECLAIRAGE
    )


def appliquer(etat, joueur_x, joueur_y, camera_x, camera_y):
    """Assombrit l'image hors du rayon lumineux avec une transition douce."""
    centre_x = round(
        (joueur_x + LARGEUR_JOUEUR / 2 - camera_x) * _ECHELLE_SOUS_PIXEL
    )
    centre_y = round(
        (joueur_y + HAUTEUR_JOUEUR / 2 - camera_y) * _ECHELLE_SOUS_PIXEL
    )
    largeur = pyxel.width
    hauteur = pyxel.height
    pixels = pyxel.screen.data_ptr()
    adresse_pixels = ctypes.addressof(pixels)

    rayon_interieur = _rayon_courant(pyxel.frame_count)
    rayon_interieur_carre = rayon_interieur * rayon_interieur
    rayon_exterieur = (
        rayon_interieur * (RAYON_LUMIERE + FONDU_LUMIERE)
        // RAYON_LUMIERE
    )
    rayon_exterieur_carre = rayon_exterieur * rayon_exterieur
    echelle_distance = (
        RAYON_LUMIERE * _ECHELLE_SOUS_PIXEL / rayon_interieur
    ) ** 2

    indice_progression = _indice_progression_eclairage(joueur_x)
    couleurs = etat["couleurs_progression"][indice_progression]
    indices_distance = etat["indices_distance"]
    traduction_ambiante = etat["traductions_ambiance"][indice_progression]

    for y in range(hauteur):
        distance_y = y * _ECHELLE_SOUS_PIXEL - centre_y
        distance_y_carree = distance_y * distance_y
        debut_ligne = y * largeur

        if distance_y_carree >= rayon_exterieur_carre:
            _assombrir_plage(
                pixels, adresse_pixels, debut_ligne, largeur,
                traduction_ambiante,
            )
            continue

        rayon_x_exterieur = isqrt(
            rayon_exterieur_carre - distance_y_carree
        )
        debut_x = max(
            0,
            _plafond_division(
                centre_x - rayon_x_exterieur, _ECHELLE_SOUS_PIXEL
            ),
        )
        fin_x = min(
            largeur,
            (centre_x + rayon_x_exterieur) // _ECHELLE_SOUS_PIXEL + 1,
        )

        # Les bandes extérieures utilisent une table de traduction rapide.
        _assombrir_plage(
            pixels, adresse_pixels, debut_ligne, debut_x,
            traduction_ambiante,
        )
        _assombrir_plage(
            pixels, adresse_pixels, debut_ligne + fin_x, largeur - fin_x,
            traduction_ambiante,
        )

        if distance_y_carree < rayon_interieur_carre:
            rayon_x_interieur = isqrt(
                rayon_interieur_carre - distance_y_carree
            )
            zones_a_eclairer = (
                (
                    debut_x,
                    max(
                        debut_x,
                        _plafond_division(
                            centre_x - rayon_x_interieur,
                            _ECHELLE_SOUS_PIXEL,
                        ),
                    ),
                ),
                (
                    min(
                        fin_x,
                        (centre_x + rayon_x_interieur)
                        // _ECHELLE_SOUS_PIXEL
                        + 1,
                    ),
                    fin_x,
                ),
            )
        else:
            zones_a_eclairer = ((debut_x, fin_x),)

        for debut, fin in zones_a_eclairer:
            for x in range(debut, fin):
                distance_carree = (
                    distance_y_carree
                    + (x * _ECHELLE_SOUS_PIXEL - centre_x) ** 2
                )
                indice_reference = min(
                    int(distance_carree * echelle_distance),
                    len(indices_distance) - 1,
                )
                indice_luminosite = indices_distance[indice_reference]
                index_pixel = debut_ligne + x
                pixels[index_pixel] = couleurs[indice_luminosite][
                    pixels[index_pixel]
                ]


def _assombrir_plage(
    pixels, adresse_pixels, debut, longueur, traduction_ambiante
):
    """Assombrit une bande entière sans recalculer la couleur pixel par pixel."""
    if longueur <= 0:
        return
    pixels_assombris = bytes(
        pixels[debut:debut + longueur]
    ).translate(traduction_ambiante)
    ctypes.memmove(adresse_pixels + debut, pixels_assombris, longueur)
