"""Chargement, affichage et collisions de la carte Tiled."""

import json
import time
from pathlib import Path

import pyxel


DOSSIER = Path(__file__).resolve().parent.parent / "assets" / "maps"
TAILLE_TILE = 32
COULEUR_TRANSPARENCE = 8
DUREE_ANIMATION_COLLECTE = 18
NOMS_CALQUES_COLLISION_COMPLETE = {"strict_collider"}
NOMS_CALQUES_COLLISION = {"passages", *NOMS_CALQUES_COLLISION_COMPLETE}
FICHIER_CARTE = DOSSIER / "level_1_pyxel.json"
FICHIER_COLLISIONS = DOSSIER / "level_1.json"


def creer_carte(fichier_carte=FICHIER_CARTE, fichier_collisions=FICHIER_COLLISIONS):
    """Charge une carte et prépare ses tuiles, couches et zones de collision."""
    fichier_carte = Path(fichier_carte)
    fichier_collisions = Path(fichier_collisions)
    with fichier_carte.open("r", encoding="utf-8") as fichier:
        donnees = json.load(fichier)
    with fichier_collisions.open("r", encoding="utf-8") as fichier:
        donnees_originales = json.load(fichier)

    # Le JSON converti sert au dessin; le JSON Tiled original garde les bons GID de collision.
    atlas = []
    animations = {}
    for tileset in donnees["tilesets"]:
        image = (fichier_carte.parent / tileset["image"]).resolve()
        planche = pyxel.Image(
            tileset["columns"] * TAILLE_TILE,
            tileset["imageheight"],
        )
        planche.load(0, 0, str(image))
        atlas.append({
            "firstgid": tileset["firstgid"],
            "tilecount": tileset["tilecount"],
            "columns": tileset["columns"],
            "image": planche,
        })
        for tuile in tileset.get("tiles", []):
            if tuile.get("animation"):
                # Les frames sont stockées en GID globaux pour pouvoir changer d'atlas.
                animations[tileset["firstgid"] + tuile["id"]] = [
                    (
                        frame["gid"]
                        if "gid" in frame
                        else tileset["firstgid"] + frame["tileid"],
                        frame["duration"],
                    )
                    for frame in tuile["animation"]
                ]

    calques = [
        couche for couche in donnees["layers"]
        if couche["type"] == "tilelayer"
        and couche.get("visible", True)
        and couche["name"].lower() not in NOMS_CALQUES_COLLISION
        and not couche["name"].endswith("_2")
    ]
    calques_devant = [
        couche for couche in donnees["layers"]
        if couche["type"] == "tilelayer"
        and couche.get("visible", True)
        and couche["name"].lower() not in NOMS_CALQUES_COLLISION
        and couche["name"].endswith("_2")
    ]
    calques_par_nom = {
        couche["name"]: couche
        for couche in donnees["layers"]
        if couche["type"] == "tilelayer"
    }

    # Les ensembles rendent les tests de collision rapides pendant la boucle de jeu.
    collisions = set()
    collisions_completes = set()
    acide = set()
    largeur = donnees_originales["width"]
    for couche in donnees_originales["layers"]:
        if couche["type"] != "tilelayer":
            continue
        nom = couche["name"].lower()
        positions = (
            collisions if nom == "passages"
            else collisions_completes
            if nom in NOMS_CALQUES_COLLISION_COMPLETE
            else acide if nom.startswith("acide")
            else None
        )
        if positions is None:
            continue
        for index, gid in enumerate(couche.get("data", [])):
            # Les bits supérieurs de Tiled décrivent le retournement, pas l'identité de la tuile.
            if gid & 0x1FFFFFFF:
                positions.add((index % largeur, index // largeur))

    return {
        "fichier": fichier_carte,
        "carte": donnees,
        "carte_originale": donnees_originales,
        "atlas": atlas,
        "animations": animations,
        "debut_animations": time.perf_counter(),
        "cranes_collectes": {},
        "citrouilles_collectees": {},
        "largeur": donnees["width"] * TAILLE_TILE,
        "hauteur": donnees["height"] * TAILLE_TILE,
        "calques": calques,
        "calques_devant": calques_devant,
        "calques_par_nom": calques_par_nom,
        "collisions": collisions,
        "collisions_completes": collisions_completes,
        "acide": acide,
    }


def objets_collectes_pour_calque(carte, nom_calque):
    if nom_calque == "Gold_skulls_1":
        return carte["cranes_collectes"]
    if nom_calque == "Pumpkin_1":
        return carte["citrouilles_collectees"]
    return None


def dessiner_carte(carte, camera_x=0, camera_y=0, devant=False):
    """Dessine uniquement les tuiles visibles, puis les objets en collecte."""
    temps_animation_ms = int(
        (time.perf_counter() - carte["debut_animations"]) * 1000
    )
    donnees_carte = carte["carte"]
    largeur_carte = donnees_carte["width"]
    hauteur_carte = donnees_carte["height"]
    # Limiter les boucles à la caméra évite de parcourir les cellules hors écran.
    premiere_colonne = max(0, camera_x // TAILLE_TILE)
    derniere_colonne = min(
        largeur_carte,
        (camera_x + pyxel.width + TAILLE_TILE - 1) // TAILLE_TILE,
    )
    premiere_ligne = max(0, camera_y // TAILLE_TILE)
    derniere_ligne = min(
        hauteur_carte,
        (camera_y + pyxel.height + TAILLE_TILE - 1) // TAILLE_TILE,
    )

    calques = carte["calques_devant"] if devant else carte["calques"]
    for couche in calques:
        donnees = couche.get("data", [])
        objets_collectes = objets_collectes_pour_calque(carte, couche["name"])
        for ligne in range(premiere_ligne, derniere_ligne):
            y = ligne * TAILLE_TILE - camera_y
            debut_ligne = ligne * largeur_carte
            for colonne in range(premiere_colonne, derniere_colonne):
                index = debut_ligne + colonne
                if index >= len(donnees):
                    continue
                gid = donnees[index] & 0x1FFFFFFF
                # L'animation de collecte dessine encore la tuile avant de l'effacer.
                if (
                    gid == 0
                    or objets_collectes is not None
                    and index in objets_collectes
                ):
                    continue
                gid = gid_anime(carte, gid, temps_animation_ms)
                image_atlas, source_x, source_y = source_tuile(carte, gid)
                x = colonne * TAILLE_TILE - camera_x
                pyxel.blt(
                    x, y, image_atlas, source_x, source_y,
                    TAILLE_TILE, TAILLE_TILE, COULEUR_TRANSPARENCE,
                )
        if objets_collectes is not None:
            dessiner_objets_collectes(
                carte, couche, objets_collectes, camera_x, camera_y,
                temps_animation_ms,
            )


def dessiner_objets_collectes(
    carte, couche, objets_collectes, camera_x, camera_y, temps_animation_ms=None
):
    """Garde la tuile visible jusqu'à la fin de son effet de collecte."""
    donnees = couche.get("data", [])
    largeur_carte = carte["carte"]["width"]
    if temps_animation_ms is None:
        temps_animation_ms = int(
            (time.perf_counter() - carte["debut_animations"]) * 1000
        )
    for index, frame in objets_collectes.items():
        gid = donnees[index] & 0x1FFFFFFF
        progress = frame / DUREE_ANIMATION_COLLECTE
        colonne = index % largeur_carte
        ligne = index // largeur_carte
        x = colonne * TAILLE_TILE - camera_x
        y = ligne * TAILLE_TILE - camera_y
        gid = gid_anime(carte, gid, temps_animation_ms)
        image_atlas, source_x, source_y = source_tuile(carte, gid)
        pyxel.dither(1 - progress)
        pyxel.blt(
            int(x), int(y), image_atlas, source_x, source_y,
            TAILLE_TILE, TAILLE_TILE, COULEUR_TRANSPARENCE,
        )
        pyxel.dither(1)


def source_tuile(carte, gid):
    """Convertit un GID compacté en banque et coordonnées de spritesheet."""
    for atlas in carte["atlas"]:
        debut = atlas["firstgid"]
        if debut <= gid < debut + atlas["tilecount"]:
            indice = gid - debut
            return (
                atlas["image"],
                (indice % atlas["columns"]) * TAILLE_TILE,
                (indice // atlas["columns"]) * TAILLE_TILE,
            )
    raise ValueError(f"GID de tuile compact introuvable : {gid}")


def mettre_a_jour_objets_collectes(carte):
    """Fait progresser les deux animations et efface les tuiles terminées."""
    _mettre_a_jour_objets_collectes(
        carte, "Gold_skulls_1", carte["cranes_collectes"], obligatoire=True
    )
    _mettre_a_jour_objets_collectes(
        carte, "Pumpkin_1", carte["citrouilles_collectees"]
    )


def _mettre_a_jour_objets_collectes(
    carte, nom_calque, objets_collectes, obligatoire=False
):
    couche = carte["calques_par_nom"].get(nom_calque)
    if couche is None:
        if obligatoire:
            raise ValueError(f"Calque {nom_calque} introuvable dans la carte")
        return
    donnees = couche.get("data", [])
    for index, frame in tuple(objets_collectes.items()):
        frame += 1
        if frame >= DUREE_ANIMATION_COLLECTE:
            donnees[index] = 0
            del objets_collectes[index]
        else:
            objets_collectes[index] = frame


def gid_anime(carte, gid, temps_ms):
    """Sélectionne la frame courante sans modifier les données de la carte."""
    frames = carte["animations"].get(gid)
    if not frames:
        return gid
    duree_totale = sum(duree for _, duree in frames)
    if duree_totale <= 0:
        return gid
    # Le modulo rend l'animation cyclique sans stocker d'état par tuile.
    temps_frame = temps_ms % duree_totale
    for gid_frame, duree in frames:
        if temps_frame < duree:
            return gid_frame
        temps_frame -= duree
    return gid


def recolter_gold_skulls(carte, x, y, largeur, hauteur):
    return _recolter_objets(
        carte, "Gold_skulls_1", carte["cranes_collectes"],
        x, y, largeur, hauteur,
    )


def recolter_citrouilles(carte, x, y, largeur, hauteur):
    return _recolter_objets(
        carte, "Pumpkin_1", carte["citrouilles_collectees"],
        x, y, largeur, hauteur,
    )


def _recolter_objets(carte, nom_calque, objets_collectes, x, y, largeur, hauteur):
    donnees_carte = carte["carte"]
    colonne_min = max(0, int(x // TAILLE_TILE))
    colonne_max = min(
        donnees_carte["width"] - 1,
        int((x + largeur - 1) // TAILLE_TILE),
    )
    ligne_min = max(0, int(y // TAILLE_TILE))
    ligne_max = min(
        donnees_carte["height"] - 1,
        int((y + hauteur - 1) // TAILLE_TILE),
    )
    recoltes = 0
    couche = carte["calques_par_nom"].get(nom_calque)
    if couche is None:
        return 0
    donnees = couche.get("data", [])
    for ligne in range(ligne_min, ligne_max + 1):
        for colonne in range(colonne_min, colonne_max + 1):
            index = ligne * donnees_carte["width"] + colonne
            if (
                index < len(donnees)
                and donnees[index] & 0x1FFFFFFF
                and index not in objets_collectes
            ):
                objets_collectes[index] = 0
                recoltes += 1
    return recoltes


def trouver_surface(carte, colonne):
    largeur = carte["carte_originale"]["width"]
    hauteur = carte["carte_originale"]["height"]
    if not 0 <= colonne < largeur:
        raise ValueError(f"Colonne de départ invalide : {colonne}")
    for ligne in range(hauteur):
        if case_solide(carte, colonne, ligne):
            return ligne * TAILLE_TILE
    raise ValueError(f"Aucune plateforme solide dans la colonne {colonne}")


def case_solide(carte, colonne, ligne):
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
    return (
        0 <= colonne < carte["carte_originale"]["width"]
        and 0 <= ligne < carte["carte_originale"]["height"]
        and (colonne, ligne) in carte["collisions_completes"]
    )


def chevauche_collision_complete(carte, x, y, largeur, hauteur):
    largeur_carte = carte["carte_originale"]["width"]
    hauteur_carte = carte["carte_originale"]["height"]
    colonne_min = max(0, int(x // TAILLE_TILE))
    colonne_max = min(
        largeur_carte - 1,
        int((x + largeur - 1) // TAILLE_TILE),
    )
    ligne_min = max(0, int(y // TAILLE_TILE))
    ligne_max = min(
        hauteur_carte - 1,
        int((y + hauteur - 1) // TAILLE_TILE),
    )
    # Seules les cases traversées par la hitbox sont consultées.
    return any(
        case_collision_complete(carte, colonne, ligne)
        for ligne in range(ligne_min, ligne_max + 1)
        for colonne in range(colonne_min, colonne_max + 1)
    )


def case_acide(carte, colonne, ligne):
    return (colonne, ligne) in carte["acide"]
