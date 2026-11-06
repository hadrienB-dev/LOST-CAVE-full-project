"""Chargement, mouvements et rendu des entités placées dans l'éditeur."""

import json
import math
from pathlib import Path
import time

import pygame
import pyxel

from .config import (
    COULEUR_TRANSPARENCE,
    HAUTEUR_JOUEUR,
    LARGEUR_JOUEUR,
    TAILLE_TILE,
    VITESSE_SAUT,
)
from .paths import RACINE_PROJET
from .tiled_map import FICHIER_CARTE


_DIRECTION_DEPLACEMENT = {
    "left": ("x", -1),
    "right": ("x", 1),
    "up": ("y", -1),
    "down": ("y", 1),
}


def creer_entites(fichier_carte=FICHIER_CARTE):
    """Crée l'état des entités associé à une carte et charge ses ressources."""
    fichier_carte = Path(fichier_carte).resolve()
    etat = {
        "fichier_carte": fichier_carte,
        "fichier_entites": fichier_carte.with_name(
            f"{fichier_carte.stem}.entities.json"
        ),
        "entites": [],
        "entites_affichage": [],
        "images": {},
        "directions": {},
        "points_courants": {},
        "origines": {},
        "pas_courants": {},
        "distance_restante": {},
        "orientations": {},
        "morts": {},
        "sons_effets": {},
        "debut_animations": time.perf_counter(),
    }
    charger_entites(etat)
    return etat


def charger_entites(etat):
    """Normalise les données enregistrées avant de préparer le jeu."""
    fichier_entites = etat["fichier_entites"]
    if not fichier_entites.exists():
        etat["entites"] = []
        etat["entites_affichage"] = []
        return
    with fichier_entites.open("r", encoding="utf-8") as fichier:
        document = json.load(fichier)
    entites = document.get("entities")
    if not isinstance(entites, list):
        raise ValueError(f"La liste 'entities' est absente de {fichier_entites}.")
    for entite in entites:
        if not isinstance(entite, dict):
            raise ValueError("Chaque entité du niveau doit être un objet JSON.")
        _valider_entite(etat, entite)
        mouvement = entite.get("movement", {})
        if not isinstance(mouvement, dict):
            raise ValueError("Le mouvement d'une entité doit être un objet.")
        etapes = mouvement.get("steps", [])
        if not isinstance(etapes, list):
            raise ValueError("Les étapes de déplacement doivent être une liste.")
        for etape in etapes:
            if (
                not isinstance(etape, dict)
                or etape.get("direction") not in ("left", "right", "up", "down")
                or isinstance(etape.get("steps"), bool)
                or not isinstance(etape.get("steps"), (int, float))
                or not math.isfinite(etape["steps"])
                or etape["steps"] <= 0
            ):
                raise ValueError(
                    f"Étape de déplacement invalide pour l'entité "
                    f"'{entite['id']}'."
                )
        # Les défauts permettent de relire les fichiers créés par les anciennes versions.
        animation = entite.setdefault("animation", {})
        animation.setdefault("frame_width", TAILLE_TILE)
        animation.setdefault("frame_height", TAILLE_TILE)
        animation.setdefault("columns", 1)
        animation.setdefault("frame_count", 1)
        animation.setdefault("row", 0)
        animation.setdefault("fps", 8)
        animation.setdefault(
            "frame_delay_ms",
            1000 / max(0.1, float(animation.get("fps", 8))),
        )
        animation.setdefault("sequences", {})
        animation.setdefault("loop", True)
        animation.setdefault("offset_x", 0)
        animation.setdefault("offset_y", 0)
        animation.setdefault("flip_x", False)
        animation.setdefault("flip_y", False)
        entite.setdefault("movement", {})
        hitbox = entite.setdefault("hitbox", {})
        hitbox.setdefault("x", 4)
        hitbox.setdefault("y", 16)
        hitbox.setdefault("width", 24)
        hitbox.setdefault("height", 16)
        entite.setdefault("effects", {})
        entite.setdefault("visible", True)
        entite.setdefault("enabled", True)
        entite.setdefault("killable", False)

    etat["entites"] = entites
    # L'ordre de profondeur ne change pas pendant la partie : on le calcule une fois.
    etat["entites_affichage"] = sorted(
        entites, key=lambda entite: entite.get("layer", 0)
    )
    etat["directions"] = {entite["id"]: 1 for entite in entites}
    etat["points_courants"] = {entite["id"]: 0 for entite in entites}
    etat["pas_courants"] = {entite["id"]: 0 for entite in entites}
    etat["distance_restante"] = {}
    for entite in entites:
        etapes = entite["movement"].get("steps", [])
        # La première étape est prête immédiatement après le chargement.
        etat["distance_restante"][entite["id"]] = (
            float(etapes[0]["steps"]) if etapes else 0
        )
    etat["orientations"] = {
        entite["id"]: (
            entite.get("movement", {}).get("facing")
            if entite.get("movement", {}).get("facing") in ("left", "right")
            else "right"
        )
        for entite in entites
    }
    etat["morts"] = {}
    etat["origines"] = {
        entite["id"]: (float(entite["x"]), float(entite["y"]))
        for entite in entites
    }
    _charger_images(etat)


def _valider_entite(etat, entite):
    """Refuse les positions et dimensions qui rendraient le jeu incohérent."""
    for cle in ("id", "x", "y", "width", "height"):
        if cle not in entite:
            raise ValueError(
                f"La propriété '{cle}' est absente d'une entité dans "
                f"{etat['fichier_entites']}."
            )
    for cle in ("x", "y", "width", "height"):
        valeur = entite[cle]
        if (
            isinstance(valeur, bool)
            or not isinstance(valeur, (int, float))
            or not math.isfinite(valeur)
        ):
            raise ValueError(f"La propriété '{cle}' d'une entité est invalide.")
    if entite["width"] <= 0 or entite["height"] <= 0:
        raise ValueError("La largeur et la hauteur d'une entité doivent être positives.")


def _charger_images(etat):
    etat["images"] = {}
    for entite in etat["entites"]:
        sprite = entite.get("sprite", "")
        if not sprite:
            continue
        chemin = Path(sprite)
        if not chemin.is_absolute():
            chemin = (RACINE_PROJET / chemin).resolve()
        if not chemin.is_file():
            raise FileNotFoundError(
                f"Sprite introuvable pour l'entité '{entite['id']}' : {chemin}"
            )
        try:
            surface = pygame.image.load(str(chemin))
            largeur_image, hauteur_image = surface.get_size()
            if largeur_image > 256 or hauteur_image > 256:
                raise ValueError("Pyxel limite les spritesheets à 256 x 256 pixels.")
            image = pyxel.Image(256, 256)
            image.load(0, 0, str(chemin))
            pixels = []
            for y in range(hauteur_image):
                ligne = []
                for x in range(largeur_image):
                    # Pyxel ne conserve pas l'alpha du PNG : les pixels transparents
                    # doivent donc prendre la couleur clé utilisée par le jeu.
                    couleur = (
                        COULEUR_TRANSPARENCE
                        if surface.get_at((x, y)).a == 0
                        else image.pget(x, y)
                    )
                    ligne.append(format(couleur, "x"))
                pixels.append("".join(ligne))
            image.set(0, 0, pixels)
        except (ValueError, RuntimeError) as erreur:
            raise ValueError(
                f"Impossible de charger le sprite de l'entité "
                f"'{entite['id']}' ({chemin}) : {erreur}"
            ) from erreur

        animation = entite["animation"]
        largeur = int(animation["frame_width"])
        hauteur = int(animation["frame_height"])
        colonnes = int(animation["columns"])
        if (
            largeur <= 0
            or hauteur <= 0
            or colonnes <= 0
        ):
            raise ValueError(
                f"Les dimensions des frames du sprite de l'entité "
                f"'{entite['id']}' doivent être positives."
            )
        lignes = math.ceil(int(animation["frame_count"]) / colonnes)
        if largeur * colonnes > 256 or hauteur * lignes > 256:
            raise ValueError(
                f"Les frames du sprite de l'entité '{entite['id']}' "
                "dépassent les dimensions prises en charge (256 x 256)."
            )
        sequences = animation.get("sequences", {})
        if not isinstance(sequences, dict):
            raise ValueError(
                f"Les séquences d'animation de l'entité '{entite['id']}' "
                "doivent être un objet."
            )
        for nom in ("left", "right", "death"):
            frames = sequences.get(nom, [])
            if not isinstance(frames, list):
                raise ValueError(
                    f"La séquence '{nom}' de l'entité '{entite['id']}' "
                    "doit être une liste."
                )
            for frame in frames:
                if (
                    not isinstance(frame, dict)
                    or any(
                        isinstance(frame.get(cle), bool)
                        or not isinstance(frame.get(cle), int)
                        or frame[cle] < 0
                        for cle in ("column", "row")
                    )
                    or frame["column"] * largeur + largeur > largeur_image
                    or frame["row"] * hauteur + hauteur > hauteur_image
                ):
                    raise ValueError(
                        f"Une frame de la séquence '{nom}' de l'entité "
                        f"'{entite['id']}' dépasse le spritesheet."
                    )
        etat["images"][entite["id"]] = image


def mettre_a_jour_entites(
    etat, joueur, ancienne_y=None, ancienne_vitesse_y=None
):
    """Déplace les entités et applique leurs collisions avec le joueur."""
    maintenant = time.perf_counter()
    if ancienne_y is None:
        ancienne_y = joueur["y"]
    if ancienne_vitesse_y is None:
        ancienne_vitesse_y = joueur["velocity_y"]
    for entite in etat["entites"]:
        identifiant = entite["id"]
        if identifiant in etat["morts"]:
            # L'entité reste désactivée pendant sa séquence, puis disparaît.
            frames_mort = entite["animation"].get("sequences", {}).get("death", [])
            delai = _delai_sequence(entite["animation"], "death")
            if (
                not frames_mort
                or (maintenant - etat["morts"][identifiant]) * 1000
                >= len(frames_mort) * delai
            ):
                del etat["morts"][identifiant]
            continue
        if not entite.get("enabled", True):
            continue
        _mettre_a_jour_mouvement(etat, entite, joueur)
        if (
            not entite.get("collision", True)
            or entite.get("category") != "enemy"
        ):
            continue

        hitbox = _hitbox(entite)
        if not _chevauche(entite, joueur, hitbox):
            continue
        hitbox_top = float(entite["y"]) + hitbox["y"]
        player_bottom_before = ancienne_y + HAUTEUR_JOUEUR
        player_bottom_after = joueur["y"] + HAUTEUR_JOUEUR
        landed_from_above = (
            ancienne_vitesse_y > 0
            and player_bottom_before <= hitbox_top + max(2, ancienne_vitesse_y)
            and player_bottom_after >= hitbox_top
        )
        # La position et la vitesse précédentes distinguent un saut sur l'ennemi
        # d'un choc latéral.
        if entite.get("killable", False) and landed_from_above:
            entite["enabled"] = False
            _jouer_son_effet(etat, entite)
            joueur["impact_camera_demandee"] = True
            if entite["animation"].get("sequences", {}).get("death"):
                etat["morts"][identifiant] = maintenant
            joueur["y"] = hitbox_top - HAUTEUR_JOUEUR
            joueur["velocity_y"] = VITESSE_SAUT * 0.55
            joueur["au_sol"] = False
            joueur["duree_saut"] = 0
            joueur["saut_en_attente"] = 0
            continue
        effet = entite.get("effects", {})
        if (
            effet.get("trigger", "contact") == "contact"
            and effet.get("action", "damage") == "damage"
            and effet.get("target", "player") in ("player", "all")
        ):
            _jouer_son_effet(etat, entite)
            joueur["reapparition_demandee"] = True
            joueur["impact_camera_demandee"] = True


def _mettre_a_jour_mouvement(etat, entite, joueur):
    """Applique le mode de déplacement configuré pour une entité."""
    mouvement = entite["movement"]
    mode = mouvement.get("type", "stationary")
    if mode == "stationary":
        return
    vitesse = abs(float(mouvement.get("speed", 0)))
    if vitesse == 0:
        return

    if mode in ("horizontal", "vertical", "patrol"):
        _deplacer_en_patrouille(etat, entite, mouvement, vitesse)
        return
    if mode == "loop":
        _deplacer_en_boucle(etat, entite, mouvement, vitesse)
        return
    if mode == "steps":
        _deplacer_par_etapes(etat, entite, mouvement, vitesse)
        return
    if mode == "follow":
        _suivre_joueur(etat, entite, joueur, vitesse)
        return
    if mode == "path":
        _suivre_trajectoire(etat, entite, mouvement, vitesse)
        return
    if mode == "projectile":
        _deplacer_projectile(etat, entite, mouvement, vitesse)


def _deplacer_en_patrouille(etat, entite, mouvement, vitesse):
    """Fait rebondir l'entité entre les deux bornes de sa patrouille."""
    identifiant = entite["id"]
    axe = (
        "y"
        if mouvement.get("type") == "vertical"
        else mouvement.get("axis", "x")
    )
    origine = etat["origines"][identifiant][0 if axe == "x" else 1]
    demi_portee = max(0, float(mouvement.get("range", 0))) / 2
    minimum, maximum = origine - demi_portee, origine + demi_portee
    direction = etat["directions"].get(identifiant, 1)
    ancienne_coordonnee = float(entite[axe])
    coordonnee = ancienne_coordonnee + vitesse * direction

    if coordonnee >= maximum:
        coordonnee, direction = maximum, -1
    elif coordonnee <= minimum:
        coordonnee, direction = minimum, 1

    entite[axe] = coordonnee
    etat["directions"][identifiant] = direction
    if axe == "x":
        _orienter(etat, entite, coordonnee - ancienne_coordonnee)


def _deplacer_en_boucle(etat, entite, mouvement, vitesse):
    """Ramène l'entité au début de sa trajectoire après la distance définie."""
    axe = mouvement.get("axis", "x")
    identifiant = entite["id"]
    origine = etat["origines"][identifiant][0 if axe == "x" else 1]
    portee = max(0, float(mouvement.get("range", 0)))
    if portee:
        entite[axe] = (
            origine + (float(entite[axe]) - origine + vitesse) % portee
        )
        if axe == "x":
            _orienter(etat, entite, 1)


def _deplacer_par_etapes(etat, entite, mouvement, vitesse):
    """Exécute une suite de déplacements sans perdre la vitesse restante."""
    identifiant = entite["id"]
    etapes = mouvement.get("steps", [])
    if not etapes:
        return

    # Une étape terminée en cours de frame transmet le reliquat à la suivante.
    budget_restant = vitesse
    while budget_restant > 0:
        index = etat["pas_courants"][identifiant] % len(etapes)
        etat["pas_courants"][identifiant] = index
        distance = min(budget_restant, etat["distance_restante"][identifiant])
        direction = etapes[index]["direction"]
        axe, signe = _DIRECTION_DEPLACEMENT[direction]
        entite[axe] += signe * distance
        if axe == "x":
            _orienter(etat, entite, signe)
        budget_restant -= distance
        etat["distance_restante"][identifiant] -= distance
        if etat["distance_restante"][identifiant] <= 0:
            index = (index + 1) % len(etapes)
            etat["pas_courants"][identifiant] = index
            etat["distance_restante"][identifiant] = float(
                etapes[index]["steps"]
            )


def _suivre_joueur(etat, entite, joueur, vitesse):
    """Déplace l'entité vers le joueur à vitesse constante."""
    dx = float(joueur["x"]) - float(entite["x"])
    dy = float(joueur["y"]) - float(entite["y"])
    longueur = math.hypot(dx, dy)
    if longueur:
        entite["x"] += dx / longueur * vitesse
        entite["y"] += dy / longueur * vitesse
        _orienter(etat, entite, dx)


def _suivre_trajectoire(etat, entite, mouvement, vitesse):
    """Avance vers le prochain point et évite de le dépasser."""
    points = mouvement.get("waypoints", [])
    if not points:
        return
    identifiant = entite["id"]
    index = etat["points_courants"].get(identifiant, 0) % len(points)
    cible_x, cible_y = points[index]
    dx, dy = cible_x - entite["x"], cible_y - entite["y"]
    longueur = math.hypot(dx, dy)
    if longueur <= vitesse:
        entite["x"], entite["y"] = cible_x, cible_y
        etat["points_courants"][identifiant] = (index + 1) % len(points)
        _orienter(etat, entite, dx)
    elif longueur:
        entite["x"] += dx / longueur * vitesse
        entite["y"] += dy / longueur * vitesse
        _orienter(etat, entite, dx)


def _deplacer_projectile(etat, entite, mouvement, vitesse):
    """Maintient le projectile sur son axe et dans son sens de lancement."""
    axe = mouvement.get("axis", "x")
    direction = -1 if mouvement.get("facing") in ("left", "up") else 1
    entite[axe] += vitesse * direction
    if axe == "x":
        _orienter(etat, entite, direction)


def _orienter(etat, entite, direction):
    """Ne change l'orientation que lorsqu'un déplacement horizontal existe."""
    if direction:
        etat["orientations"][entite["id"]] = (
            "right" if direction > 0 else "left"
        )


def _chevauche(entite, joueur, hitbox):
    """Compare les hitbox sans tenir compte des pixels transparents du sprite."""
    gauche = float(entite["x"]) + hitbox["x"]
    haut = float(entite["y"]) + hitbox["y"]
    return (
        gauche < joueur["x"] + LARGEUR_JOUEUR
        and gauche + hitbox["width"] > joueur["x"]
        and haut < joueur["y"] + HAUTEUR_JOUEUR
        and haut + hitbox["height"] > joueur["y"]
    )


def _hitbox(entite):
    """Complète une hitbox personnalisée avec les dimensions de l'entité."""
    hitbox = entite.get("hitbox", {})
    return {
        "x": float(hitbox.get("x", 0)),
        "y": float(hitbox.get("y", 0)),
        "width": float(hitbox.get("width", entite["width"])),
        "height": float(hitbox.get("height", entite["height"])),
    }


def _jouer_son_effet(etat, entite):
    chemin_son = entite.get("effects", {}).get("sound", "")
    if not chemin_son:
        return
    chemin = Path(chemin_son)
    if not chemin.is_absolute():
        chemin = (RACINE_PROJET / chemin).resolve()
    if not chemin.is_file():
        raise FileNotFoundError(
            f"Son introuvable pour l'entité '{entite['id']}' : {chemin}"
        )
    son = etat["sons_effets"].get(chemin)
    if son is None:
        # La mise en cache évite de relire et recréer un son à chaque contact.
        son = pygame.mixer.Sound(str(chemin))
        etat["sons_effets"][chemin] = son
    son.play()


def _delai_sequence(animation, nom_sequence):
    reglages = animation.get("direction_settings", {}).get(nom_sequence, {})
    delai = reglages.get("frame_delay_ms")
    if delai is None:
        delai = animation.get("frame_delay_ms", 125)
    return max(1, float(delai))


def _retourner_sequence(animation, nom_sequence, orientation, axe):
    """Résout le retournement propre à une séquence ou à la direction de mort."""
    reglages = animation.get("direction_settings", {}).get(nom_sequence, {})
    valeur = reglages.get(f"flip_{axe}")
    if valeur is None:
        return animation.get(f"flip_{axe}", False)
    if isinstance(valeur, bool):
        return valeur
    if nom_sequence == "death" and valeur in (
        "direction_right", "direction_left"
    ):
        direction_cible = "right" if valeur == "direction_right" else "left"
        return orientation == direction_cible
    raise ValueError(
        f"Réglage flip_{axe} invalide pour la séquence '{nom_sequence}'."
    )


def dessiner_entites(etat, camera_x=0, camera_y=0):
    """Dessine les sprites dans l'ordre de profondeur préparé au chargement."""
    maintenant = time.perf_counter()
    for entite in etat["entites_affichage"]:
        identifiant = entite["id"]
        est_mort = identifiant in etat["morts"]
        if (
            not entite.get("visible", True)
            or (not entite.get("enabled", True) and not est_mort)
        ):
            continue
        image = etat["images"].get(identifiant)
        if image is None:
            continue
        animation = entite["animation"]
        orientation = etat["orientations"].get(identifiant, "right")
        nom_sequence = "death" if est_mort else orientation
        sequence = animation.get("sequences", {}).get(nom_sequence, [])
        if sequence:
            # La mort démarre à l'élimination; les autres séquences bouclent depuis le lancement.
            debut = etat["morts"][identifiant] if est_mort else etat["debut_animations"]
            delai = _delai_sequence(animation, nom_sequence)
            frame = int((maintenant - debut) * 1000 / delai)
            if est_mort:
                if frame >= len(sequence):
                    etat["morts"].pop(identifiant, None)
                    continue
                frame = min(frame, len(sequence) - 1)
            else:
                frame %= len(sequence)
            source_x = sequence[frame]["column"] * int(animation["frame_width"])
            source_y = sequence[frame]["row"] * int(animation["frame_height"])
        else:
            if est_mort:
                continue
            frame_count = max(1, int(animation.get("frame_count", 1)))
            fps = max(0.1, float(animation.get("fps", 8)))
            frame = int((maintenant - etat["debut_animations"]) * fps)
            if animation.get("loop", True):
                frame %= frame_count
            else:
                frame = min(frame, frame_count - 1)
            colonnes = max(1, int(animation.get("columns", 1)))
            source_x = (frame % colonnes) * int(animation["frame_width"])
            source_y = (
                int(animation.get("row", 0)) + frame // colonnes
            ) * int(animation["frame_height"])

        largeur = int(animation["frame_width"])
        hauteur = int(animation["frame_height"])
        flip_x = (
            _retourner_sequence(animation, nom_sequence, orientation, "x")
            if sequence else animation.get("flip_x", False)
        )
        flip_y = (
            _retourner_sequence(animation, nom_sequence, orientation, "y")
            if sequence else animation.get("flip_y", False)
        )
        if flip_x:
            largeur = -largeur
        if flip_y:
            hauteur = -hauteur
        pyxel.blt(
            int(entite["x"] - camera_x + animation.get("offset_x", 0)),
            int(entite["y"] - camera_y + animation.get("offset_y", 0)),
            image, source_x, source_y, largeur, hauteur,
            COULEUR_TRANSPARENCE,
        )
