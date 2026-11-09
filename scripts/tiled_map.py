"""Charge, dessine et interroge la carte Tiled.

Le fichier converti par Pyxel sert à l'affichage. Le fichier Tiled original
fournit les calques de collision et les dimensions en cases.
"""

import json
import time
from pathlib import Path

import pyxel

from .paths import RACINE_PROJET


DOSSIER = RACINE_PROJET / "assets" / "maps"
TAILLE_TILE = 32
COULEUR_TRANSPARENCE = 8
DUREE_ANIMATION_COLLECTE = 18
MASQUE_GID_TILED = 0x1FFFFFFF
NOMS_CALQUES_COLLISION_COMPLETE = {"strict_collider"}
NOMS_CALQUES_COLLISION = {"passages", *NOMS_CALQUES_COLLISION_COMPLETE}
CALQUES_OBJETS_RECUPERABLES = {
    "Gold_skulls_1": "cranes_collectes",
    "Pumpkin_1": "citrouilles_collectees",
}
FICHIER_CARTE = DOSSIER / "level_1_pyxel.json"
FICHIER_COLLISIONS = DOSSIER / "level_1.json"


# Chargement des données

def creer_carte(fichier_carte=FICHIER_CARTE, fichier_collisions=FICHIER_COLLISIONS):
    """Charge les ressources et construit l'état utilisé par le jeu."""
    fichier_carte = Path(fichier_carte)
    fichier_collisions = Path(fichier_collisions)
    donnees = _lire_json(fichier_carte)
    donnees_originales = _lire_json(fichier_collisions)
    planches, animations = _charger_planches(fichier_carte, donnees)
    calques, calques_devant, calques_par_nom = _preparer_calques(donnees)
    donnees_objets_originales = {
        nom: list(calques_par_nom[nom].get("data", []))
        for nom in CALQUES_OBJETS_RECUPERABLES
        if nom in calques_par_nom
    }
    collisions, collisions_completes, acide = _preparer_collisions(
        donnees_originales
    )

    return {
        "fichier": fichier_carte,
        "carte": donnees,
        "carte_originale": donnees_originales,
        "planches": planches,
        "animations": animations,
        "debut_animations": time.perf_counter(),
        "cranes_collectes": {},
        "citrouilles_collectees": {},
        "largeur": donnees["width"] * TAILLE_TILE,
        "hauteur": donnees["height"] * TAILLE_TILE,
        "calques": calques,
        "calques_devant": calques_devant,
        "calques_par_nom": calques_par_nom,
        "donnees_objets_originales": donnees_objets_originales,
        "collisions": collisions,
        "collisions_completes": collisions_completes,
        "acide": acide,
    }


def _lire_json(chemin):
    """Lit un fichier JSON du niveau et renvoie ses données."""
    with chemin.open("r", encoding="utf-8") as fichier:
        return json.load(fichier)


def _charger_planches(fichier_carte, donnees):
    """Charge les planches de sprites et mémorise les animations des tuiles."""
    planches = []
    animations = {}
    for jeu_tuiles in donnees["tilesets"]:
        chemin_image = (fichier_carte.parent / jeu_tuiles["image"]).resolve()
        image = pyxel.Image(
            jeu_tuiles["columns"] * TAILLE_TILE,
            jeu_tuiles["imageheight"],
        )
        image.load(0, 0, str(chemin_image))
        planches.append({
            "premier_gid": jeu_tuiles["firstgid"],
            "nombre_tuiles": jeu_tuiles["tilecount"],
            "colonnes": jeu_tuiles["columns"],
            "image": image,
        })

        # Les GID globaux permettent aux animations de traverser les spritesheets.
        premier_gid = jeu_tuiles["firstgid"]
        for tuile in jeu_tuiles.get("tiles", []):
            if tuile.get("animation"):
                animations[premier_gid + tuile["id"]] = [
                    (
                        cadre["gid"]
                        if "gid" in cadre
                        else premier_gid + cadre["tileid"],
                        cadre["duration"],
                    )
                    for cadre in tuile["animation"]
                ]
    return planches, animations


def _preparer_calques(donnees):
    """Sépare les calques de décor selon qu'ils passent devant le joueur."""
    calques_tuiles = [
        couche for couche in donnees["layers"]
        if couche["type"] == "tilelayer"
    ]
    calques_par_nom = {
        couche["name"]: couche
        for couche in calques_tuiles
    }
    calques_dessinables = [
        couche for couche in calques_tuiles
        if couche.get("visible", True)
        and couche["name"].lower() not in NOMS_CALQUES_COLLISION
    ]
    calques = [
        couche for couche in calques_dessinables
        if not couche["name"].endswith("_2")
    ]
    calques_devant = [
        couche for couche in calques_dessinables
        if couche["name"].endswith("_2")
    ]
    return calques, calques_devant, calques_par_nom


def _preparer_collisions(donnees_originales):
    """Convertit les calques Tiled en ensembles rapides de coordonnées."""
    collisions = set()
    collisions_completes = set()
    acide = set()
    largeur = donnees_originales["width"]

    for couche in donnees_originales["layers"]:
        if couche["type"] != "tilelayer":
            continue
        nom = couche["name"].lower()
        if nom == "passages":
            positions = collisions
        elif nom in NOMS_CALQUES_COLLISION_COMPLETE:
            positions = collisions_completes
        elif nom.startswith("acide"):
            positions = acide
        else:
            continue

        for indice, identifiant_tuile in enumerate(couche.get("data", [])):
            # Les bits de retournement de Tiled ne font pas partie du GID.
            if identifiant_tuile & MASQUE_GID_TILED:
                positions.add((indice % largeur, indice // largeur))
    return collisions, collisions_completes, acide


# Affichage des tuiles et animations

def objets_collectes_pour_calque(carte, nom_calque):
    """Renvoie le suivi de collecte associé à un calque, s'il existe."""
    cle = CALQUES_OBJETS_RECUPERABLES.get(nom_calque)
    return carte[cle] if cle is not None else None


def dessiner_carte(carte, decalage_camera_x=0, decalage_camera_y=0, devant=False):
    """Dessine uniquement les tuiles visibles, puis les objets en collecte."""
    temps_animation_ms = int(
        (time.perf_counter() - carte["debut_animations"]) * 1000
    )
    donnees_carte = carte["carte"]
    largeur_carte = donnees_carte["width"]
    hauteur_carte = donnees_carte["height"]
    # Limiter les boucles à la caméra évite de parcourir les cellules hors écran.
    premiere_colonne = max(0, decalage_camera_x // TAILLE_TILE)
    derniere_colonne = min(
        largeur_carte,
        (decalage_camera_x + pyxel.width + TAILLE_TILE - 1) // TAILLE_TILE,
    )
    premiere_ligne = max(0, decalage_camera_y // TAILLE_TILE)
    derniere_ligne = min(
        hauteur_carte,
        (decalage_camera_y + pyxel.height + TAILLE_TILE - 1) // TAILLE_TILE,
    )

    calques = carte["calques_devant"] if devant else carte["calques"]
    for couche in calques:
        donnees = couche.get("data", [])
        objets_collectes = objets_collectes_pour_calque(carte, couche["name"])
        for ligne in range(premiere_ligne, derniere_ligne):
            y = ligne * TAILLE_TILE - decalage_camera_y
            debut_ligne = ligne * largeur_carte
            for colonne in range(premiere_colonne, derniere_colonne):
                indice = debut_ligne + colonne
                if indice >= len(donnees):
                    continue
                identifiant_tuile = donnees[indice] & MASQUE_GID_TILED
                # L'animation de collecte dessine encore la tuile avant de l'effacer.
                if (
                    identifiant_tuile == 0
                    or (
                        objets_collectes is not None
                        and indice in objets_collectes
                    )
                ):
                    continue
                identifiant_tuile = gid_anime(
                    carte, identifiant_tuile, temps_animation_ms
                )
                image, origine_x, origine_y = source_tuile(
                    carte, identifiant_tuile
                )
                x = colonne * TAILLE_TILE - decalage_camera_x
                pyxel.blt(
                    x, y, image, origine_x, origine_y,
                    TAILLE_TILE, TAILLE_TILE, COULEUR_TRANSPARENCE,
                )
        if objets_collectes is not None:
            dessiner_objets_collectes(
                carte,
                couche,
                objets_collectes,
                decalage_camera_x,
                decalage_camera_y,
                temps_animation_ms,
            )


def dessiner_objets_collectes(
    carte,
    couche,
    objets_collectes,
    decalage_camera_x,
    decalage_camera_y,
    temps_animation_ms=None,
):
    """Affiche les objets en train d'être ramassés jusqu'à la fin de l'effet."""
    donnees = couche.get("data", [])
    largeur_carte = carte["carte"]["width"]
    if temps_animation_ms is None:
        temps_animation_ms = int(
            (time.perf_counter() - carte["debut_animations"]) * 1000
        )
    for indice, cadre in objets_collectes.items():
        identifiant_tuile = donnees[indice] & MASQUE_GID_TILED
        progression = cadre / DUREE_ANIMATION_COLLECTE
        colonne = indice % largeur_carte
        ligne = indice // largeur_carte
        x = colonne * TAILLE_TILE - decalage_camera_x
        y = ligne * TAILLE_TILE - decalage_camera_y
        identifiant_tuile = gid_anime(
            carte, identifiant_tuile, temps_animation_ms
        )
        image, origine_x, origine_y = source_tuile(
            carte, identifiant_tuile
        )
        pyxel.dither(1 - progression)
        pyxel.blt(
            int(x), int(y), image, origine_x, origine_y,
            TAILLE_TILE, TAILLE_TILE, COULEUR_TRANSPARENCE,
        )
        pyxel.dither(1)


def source_tuile(carte, identifiant_tuile):
    """Trouve la planche et les coordonnées correspondant à un GID."""
    for planche in carte["planches"]:
        premier_gid = planche["premier_gid"]
        if (
            premier_gid
            <= identifiant_tuile
            < premier_gid + planche["nombre_tuiles"]
        ):
            indice = identifiant_tuile - premier_gid
            return (
                planche["image"],
                (indice % planche["colonnes"]) * TAILLE_TILE,
                (indice // planche["colonnes"]) * TAILLE_TILE,
            )
    raise ValueError(f"GID de tuile introuvable : {identifiant_tuile}")


def mettre_a_jour_objets_collectes(carte):
    """Fait avancer les effets de collecte et efface les tuiles terminées."""
    _mettre_a_jour_objets_collectes(
        carte, "Gold_skulls_1", carte["cranes_collectes"], obligatoire=True
    )
    _mettre_a_jour_objets_collectes(
        carte, "Pumpkin_1", carte["citrouilles_collectees"]
    )


def reinitialiser_objets_collectes(carte):
    """Restaure les données de départ des calques d'objets récupérables."""
    for nom, donnees_originales in carte["donnees_objets_originales"].items():
        couche = carte["calques_par_nom"][nom]
        couche["data"][:] = donnees_originales
    carte["cranes_collectes"].clear()
    carte["citrouilles_collectees"].clear()


def _mettre_a_jour_objets_collectes(
    carte, nom_calque, objets_collectes, obligatoire=False
):
    couche = carte["calques_par_nom"].get(nom_calque)
    if couche is None:
        if obligatoire:
            raise ValueError(f"Calque {nom_calque} introuvable dans la carte")
        return
    donnees = couche.get("data", [])
    for indice, cadre in tuple(objets_collectes.items()):
        cadre += 1
        if cadre >= DUREE_ANIMATION_COLLECTE:
            donnees[indice] = 0
            del objets_collectes[indice]
        else:
            objets_collectes[indice] = cadre


def gid_anime(carte, identifiant_tuile, temps_ms):
    """Renvoie le GID de l'image d'animation courante, sans changer la carte."""
    cadres = carte["animations"].get(identifiant_tuile)
    if not cadres:
        return identifiant_tuile
    duree_totale = sum(duree for _, duree in cadres)
    if duree_totale <= 0:
        return identifiant_tuile
    # Le modulo rend l'animation cyclique sans stocker d'état par tuile.
    temps_cadre = temps_ms % duree_totale
    for identifiant_cadre, duree in cadres:
        if temps_cadre < duree:
            return identifiant_cadre
        temps_cadre -= duree
    return identifiant_tuile


def recolter_gold_skulls(carte, x, y, largeur, hauteur):
    """Démarre la collecte des crânes croisant la boîte du joueur."""
    return _recolter_objets(
        carte, "Gold_skulls_1", carte["cranes_collectes"],
        x, y, largeur, hauteur,
    )


def recolter_citrouilles(carte, x, y, largeur, hauteur):
    """Démarre la collecte des citrouilles croisant la boîte du joueur."""
    return _recolter_objets(
        carte, "Pumpkin_1", carte["citrouilles_collectees"],
        x, y, largeur, hauteur,
    )


def _recolter_objets(carte, nom_calque, objets_collectes, x, y, largeur, hauteur):
    """Marque chaque objet dont la tuile croise la boîte du joueur."""
    donnees_carte = carte["carte"]
    colonne_min, colonne_max, ligne_min, ligne_max = _bornes_cases_touchees(
        x,
        y,
        largeur,
        hauteur,
        donnees_carte["width"],
        donnees_carte["height"],
    )
    couche = carte["calques_par_nom"].get(nom_calque)
    if couche is None:
        return 0

    donnees = couche.get("data", [])
    recoltes = 0
    for ligne in range(ligne_min, ligne_max + 1):
        for colonne in range(colonne_min, colonne_max + 1):
            indice = ligne * donnees_carte["width"] + colonne
            if (
                indice < len(donnees)
                and donnees[indice] & MASQUE_GID_TILED
                and indice not in objets_collectes
            ):
                objets_collectes[indice] = 0
                recoltes += 1
    return recoltes


def _bornes_cases_touchees(x, y, largeur, hauteur, nombre_colonnes, nombre_lignes):
    """Renvoie les limites inclusives des cases touchées par une boîte."""
    return (
        max(0, int(x // TAILLE_TILE)),
        min(
            nombre_colonnes - 1,
            int((x + largeur - 1) // TAILLE_TILE),
        ),
        max(0, int(y // TAILLE_TILE)),
        min(
            nombre_lignes - 1,
            int((y + hauteur - 1) // TAILLE_TILE),
        ),
    )


def trouver_surface(carte, colonne):
    """Renvoie la hauteur de la première case solide dans une colonne."""
    largeur = carte["carte_originale"]["width"]
    hauteur = carte["carte_originale"]["height"]
    if not 0 <= colonne < largeur:
        raise ValueError(f"Colonne de départ invalide : {colonne}")
    for ligne in range(hauteur):
        if case_solide(carte, colonne, ligne):
            return ligne * TAILLE_TILE
    raise ValueError(f"Aucune plateforme solide dans la colonne {colonne}")


def case_solide(carte, colonne, ligne):
    """Indique si une case est solide pour le joueur."""
    hauteur = carte["carte_originale"]["height"]
    largeur = carte["carte_originale"]["width"]
    return (
        0 <= colonne < largeur
        and 0 <= ligne < hauteur
        and (
            (colonne, ligne) in carte["collisions"]
            or (colonne, ligne) in carte["collisions_completes"]
        )
    )


def case_collision_complete(carte, colonne, ligne):
    """Indique si la case bloque entièrement le déplacement."""
    return (
        0 <= colonne < carte["carte_originale"]["width"]
        and 0 <= ligne < carte["carte_originale"]["height"]
        and (colonne, ligne) in carte["collisions_completes"]
    )


def chevauche_collision_complete(carte, x, y, largeur, hauteur):
    """Indique si une boîte recouvre au moins une case à collision complète."""
    donnees = carte["carte_originale"]
    colonne_min, colonne_max, ligne_min, ligne_max = _bornes_cases_touchees(
        x,
        y,
        largeur,
        hauteur,
        donnees["width"],
        donnees["height"],
    )
    return any(
        case_collision_complete(carte, colonne, ligne)
        for ligne in range(ligne_min, ligne_max + 1)
        for colonne in range(colonne_min, colonne_max + 1)
    )


def case_acide(carte, colonne, ligne):
    """Indique si une case appartient à un calque d'acide."""
    return (colonne, ligne) in carte["acide"]
