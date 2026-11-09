"""Chargement, mouvements et rendu des entités du niveau."""

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
from .entites_niveau import creer_entites_niveau
from .paths import RACINE_PROJET


_DIRECTION_DEPLACEMENT = {
    "gauche": ("position_x", -1),
    "droite": ("position_x", 1),
    "haut": ("position_y", -1),
    "bas": ("position_y", 1),
}


def creer_entites():
    """Crée l'état des entités associé à une carte et charge ses ressources."""
    etat = {
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
    """Prépare les définitions Python des entités avant le lancement."""
    entites = creer_entites_niveau()
    for entite in entites:
        _valider_entite(entite)
        mouvement = entite.get("mouvement", {})
        if not isinstance(mouvement, dict):
            raise ValueError("Le mouvement d'une entité doit être un objet.")
        etapes = mouvement.get("etapes", [])
        if not isinstance(etapes, list):
            raise ValueError("Les étapes de déplacement doivent être une liste.")
        for etape in etapes:
            if (
                not isinstance(etape, dict)
                or etape.get("direction") not in ("gauche", "droite", "haut", "bas")
                or isinstance(etape.get("distance"), bool)
                or not isinstance(etape.get("distance"), (int, float))
                or not math.isfinite(etape["distance"])
                or etape["distance"] <= 0
            ):
                raise ValueError(
                    f"Étape de déplacement invalide pour l'entité "
                    f"'{entite['identifiant']}'."
                )
        animation = entite.setdefault("animation", {})
        animation.setdefault("largeur_cadre", TAILLE_TILE)
        animation.setdefault("hauteur_cadre", TAILLE_TILE)
        animation.setdefault("nombre_colonnes", 1)
        animation.setdefault("nombre_cadres", 1)
        animation.setdefault("ligne", 0)
        animation.setdefault("cadres_par_seconde", 8)
        animation.setdefault(
            "duree_cadre_ms",
            1000 / max(0.1, float(animation.get("cadres_par_seconde", 8))),
        )
        animation.setdefault("animations_par_direction", {})
        animation.setdefault("boucler", True)
        animation.setdefault("decalage_x", 0)
        animation.setdefault("decalage_y", 0)
        animation.setdefault("inverser_x", False)
        animation.setdefault("inverser_y", False)
        entite.setdefault("mouvement", {})
        boite_collision = entite.setdefault("boite_collision", {})
        boite_collision.setdefault("decalage_x", 4)
        boite_collision.setdefault("decalage_y", 16)
        boite_collision.setdefault("largeur", 24)
        boite_collision.setdefault("hauteur", 16)
        entite.setdefault("effets", {})
        entite.setdefault("visible", True)
        entite.setdefault("actif", True)
        entite.setdefault("peut_etre_tue", False)

    etat["entites"] = entites
    # L'ordre de profondeur ne change pas pendant la partie : on le calcule une fois.
    etat["entites_affichage"] = sorted(
        entites, key=lambda entite: entite.get("calque", 0)
    )
    etat["directions"] = {entite["identifiant"]: 1 for entite in entites}
    etat["points_courants"] = {entite["identifiant"]: 0 for entite in entites}
    etat["pas_courants"] = {entite["identifiant"]: 0 for entite in entites}
    etat["distance_restante"] = {}
    for entite in entites:
        etapes = entite["mouvement"].get("etapes", [])
        # La première étape est prête immédiatement après le chargement.
        etat["distance_restante"][entite["identifiant"]] = (
            float(etapes[0]["distance"]) if etapes else 0
        )
    etat["orientations"] = {
        entite["identifiant"]: (
            entite.get("mouvement", {}).get("orientation")
            if entite.get("mouvement", {}).get("orientation") in ("gauche", "droite")
            else "droite"
        )
        for entite in entites
    }
    etat["morts"] = {}
    etat["origines"] = {
        entite["identifiant"]: (float(entite["position_x"]), float(entite["position_y"]))
        for entite in entites
    }
    _charger_images(etat)


def _valider_entite(entite):
    """Refuse les positions et dimensions qui rendraient le jeu incohérent."""
    for cle in ("identifiant", "position_x", "position_y", "largeur", "hauteur"):
        if cle not in entite:
            raise ValueError(
                f"La propriété '{cle}' est absente de l'entité "
                f"'{entite.get('identifiant', 'inconnue')}'."
            )
    for cle in ("position_x", "position_y", "largeur", "hauteur"):
        valeur = entite[cle]
        if (
            isinstance(valeur, bool)
            or not isinstance(valeur, (int, float))
            or not math.isfinite(valeur)
        ):
            raise ValueError(f"La propriété '{cle}' d'une entité est invalide.")
    if entite["largeur"] <= 0 or entite["hauteur"] <= 0:
        raise ValueError("La largeur et la hauteur d'une entité doivent être positives.")


def _charger_images(etat):
    etat["images"] = {}
    for entite in etat["entites"]:
        sprite = entite.get("fichier_sprite", "")
        if not sprite:
            continue
        chemin = Path(sprite)
        if not chemin.is_absolute():
            chemin = (RACINE_PROJET / chemin).resolve()
        if not chemin.is_file():
            raise FileNotFoundError(
                f"Sprite introuvable pour l'entité '{entite['identifiant']}' : {chemin}"
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
                f"'{entite['identifiant']}' ({chemin}) : {erreur}"
            ) from erreur

        animation = entite["animation"]
        largeur = int(animation["largeur_cadre"])
        hauteur = int(animation["hauteur_cadre"])
        colonnes = int(animation["nombre_colonnes"])
        if (
            largeur <= 0
            or hauteur <= 0
            or colonnes <= 0
        ):
            raise ValueError(
                f"Les dimensions des cadres du sprite de l'entité "
                f"'{entite['identifiant']}' doivent être positives."
            )
        lignes = math.ceil(int(animation["nombre_cadres"]) / colonnes)
        if largeur * colonnes > 256 or hauteur * lignes > 256:
            raise ValueError(
                f"Les cadres du sprite de l'entité '{entite['identifiant']}' "
                "dépassent les dimensions prises en charge (256 x 256)."
            )
        sequences = animation.get("animations_par_direction", {})
        if not isinstance(sequences, dict):
            raise ValueError(
                f"Les séquences d'animation de l'entité '{entite['identifiant']}' "
                "doivent être un objet."
            )
        for nom in ("gauche", "droite", "mort"):
            cadres = sequences.get(nom, [])
            if not isinstance(cadres, list):
                raise ValueError(
                    f"La séquence '{nom}' de l'entité '{entite['identifiant']}' "
                    "doit être une liste."
                )
            for cadre in cadres:
                if (
                    not isinstance(cadre, dict)
                    or any(
                        isinstance(cadre.get(cle), bool)
                        or not isinstance(cadre.get(cle), int)
                        or cadre[cle] < 0
                        for cle in ("colonne", "ligne")
                    )
                    or cadre["colonne"] * largeur + largeur > largeur_image
                    or cadre["ligne"] * hauteur + hauteur > hauteur_image
                ):
                    raise ValueError(
                        f"Un cadre de la séquence '{nom}' de l'entité "
                        f"'{entite['identifiant']}' dépasse la feuille de sprites."
                    )
        etat["images"][entite["identifiant"]] = image


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
        identifiant = entite["identifiant"]
        if identifiant in etat["morts"]:
            # L'entité reste désactivée pendant sa séquence, puis disparaît.
            cadres_mort = entite["animation"].get("animations_par_direction", {}).get("mort", [])
            delai_cadre = _delai_cadre_sequence(entite["animation"], "mort")
            if (
                not cadres_mort
                or (maintenant - etat["morts"][identifiant]) * 1000
                >= len(cadres_mort) * delai_cadre
            ):
                del etat["morts"][identifiant]
            continue
        if not entite.get("actif", True):
            continue
        _mettre_a_jour_mouvement(etat, entite, joueur)
        if (
            not entite.get("collision", True)
            or entite.get("categorie") != "ennemi"
        ):
            continue

        boite_collision = _boite_collision(entite)
        if not _chevauche(entite, joueur, boite_collision):
            continue
        haut_collision = (
            float(entite["position_y"]) + boite_collision["decalage_y"]
        )
        bas_joueur_avant_contact = ancienne_y + HAUTEUR_JOUEUR
        bas_joueur_apres_contact = joueur["y"] + HAUTEUR_JOUEUR
        rebondit_sur_entite = (
            ancienne_vitesse_y > 0
            and bas_joueur_avant_contact
            <= haut_collision + max(2, ancienne_vitesse_y)
            and bas_joueur_apres_contact >= haut_collision
        )
        # La position et la vitesse précédentes distinguent un saut sur l'ennemi
        # d'un choc latéral.
        if entite.get("peut_etre_tue", False) and rebondit_sur_entite:
            entite["actif"] = False
            _jouer_son_effet(etat, entite)
            joueur["impact_camera_demandee"] = True
            if entite["animation"].get("animations_par_direction", {}).get("mort"):
                etat["morts"][identifiant] = maintenant
            joueur["y"] = haut_collision - HAUTEUR_JOUEUR
            joueur["velocity_y"] = VITESSE_SAUT * 0.55
            joueur["au_sol"] = False
            joueur["duree_saut"] = 0
            joueur["saut_en_attente"] = 0
            continue
        effet = entite.get("effets", {})
        if (
            effet.get("declencheur", "contact") == "contact"
            and effet.get("action", "blesser") == "blesser"
            and effet.get("cible", "joueur") in ("joueur", "tous")
        ):
            _jouer_son_effet(etat, entite)
            joueur["reapparition_demandee"] = True
            joueur["impact_camera_demandee"] = True


def _mettre_a_jour_mouvement(etat, entite, joueur):
    """Applique le mode de déplacement configuré pour une entité."""
    mouvement = entite["mouvement"]
    mode = mouvement.get("mode", "immobile")
    if mode == "immobile":
        return
    vitesse = abs(float(mouvement.get("vitesse", 0)))
    if vitesse == 0:
        return

    if mode in ("horizontal", "vertical", "patrouille"):
        _deplacer_en_patrouille(etat, entite, mouvement, vitesse)
        return
    if mode == "boucle":
        _deplacer_en_boucle(etat, entite, mouvement, vitesse)
        return
    if mode == "etapes":
        _deplacer_par_etapes(etat, entite, mouvement, vitesse)
        return
    if mode == "suivre":
        _suivre_joueur(etat, entite, joueur, vitesse)
        return
    if mode == "trajectoire":
        _suivre_trajectoire(etat, entite, mouvement, vitesse)
        return
    if mode == "projectile":
        _deplacer_projectile(etat, entite, mouvement, vitesse)


def _deplacer_en_patrouille(etat, entite, mouvement, vitesse):
    """Fait rebondir l'entité entre les deux bornes de sa patrouille."""
    identifiant = entite["identifiant"]
    axe = (
        "position_y"
        if mouvement.get("mode") == "vertical"
        else mouvement.get("axe", "position_x")
    )
    origine = etat["origines"][identifiant][0 if axe == "position_x" else 1]
    demi_portee = max(0, float(mouvement.get("portee", 0))) / 2
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
    if axe == "position_x":
        _orienter(etat, entite, coordonnee - ancienne_coordonnee)


def _deplacer_en_boucle(etat, entite, mouvement, vitesse):
    """Ramène l'entité au début de sa trajectoire après la distance définie."""
    axe = mouvement.get("axe", "position_x")
    identifiant = entite["identifiant"]
    origine = etat["origines"][identifiant][0 if axe == "position_x" else 1]
    portee = max(0, float(mouvement.get("portee", 0)))
    if portee:
        entite[axe] = (
            origine + (float(entite[axe]) - origine + vitesse) % portee
        )
        if axe == "position_x":
            _orienter(etat, entite, 1)


def _deplacer_par_etapes(etat, entite, mouvement, vitesse):
    """Exécute une suite de déplacements sans perdre la vitesse restante."""
    identifiant = entite["identifiant"]
    etapes = mouvement.get("etapes", [])
    if not etapes:
        return

    # Une étape terminée pendant le déplacement transmet le reliquat à la suivante.
    budget_restant = vitesse
    while budget_restant > 0:
        indice = etat["pas_courants"][identifiant] % len(etapes)
        etat["pas_courants"][identifiant] = indice
        distance = min(budget_restant, etat["distance_restante"][identifiant])
        direction = etapes[indice]["direction"]
        axe, signe = _DIRECTION_DEPLACEMENT[direction]
        entite[axe] += signe * distance
        if axe == "position_x":
            _orienter(etat, entite, signe)
        budget_restant -= distance
        etat["distance_restante"][identifiant] -= distance
        if etat["distance_restante"][identifiant] <= 0:
            indice = (indice + 1) % len(etapes)
            etat["pas_courants"][identifiant] = indice
            etat["distance_restante"][identifiant] = float(
                etapes[indice]["distance"]
            )


def _suivre_joueur(etat, entite, joueur, vitesse):
    """Déplace l'entité vers le joueur à vitesse constante."""
    dx = float(joueur["x"]) - float(entite["position_x"])
    dy = float(joueur["y"]) - float(entite["position_y"])
    longueur = math.hypot(dx, dy)
    if longueur:
        entite["position_x"] += dx / longueur * vitesse
        entite["position_y"] += dy / longueur * vitesse
        _orienter(etat, entite, dx)


def _suivre_trajectoire(etat, entite, mouvement, vitesse):
    """Avance vers le prochain point et évite de le dépasser."""
    points = mouvement.get("points_passage", [])
    if not points:
        return
    identifiant = entite["identifiant"]
    indice = etat["points_courants"].get(identifiant, 0) % len(points)
    cible_x, cible_y = points[indice]
    dx, dy = cible_x - entite["position_x"], cible_y - entite["position_y"]
    longueur = math.hypot(dx, dy)
    if longueur <= vitesse:
        entite["position_x"], entite["position_y"] = cible_x, cible_y
        etat["points_courants"][identifiant] = (indice + 1) % len(points)
        _orienter(etat, entite, dx)
    elif longueur:
        entite["position_x"] += dx / longueur * vitesse
        entite["position_y"] += dy / longueur * vitesse
        _orienter(etat, entite, dx)


def _deplacer_projectile(etat, entite, mouvement, vitesse):
    """Maintient le projectile sur son axe et dans son sens de lancement."""
    axe = mouvement.get("axe", "position_x")
    direction = -1 if mouvement.get("orientation") in ("gauche", "haut") else 1
    entite[axe] += vitesse * direction
    if axe == "position_x":
        _orienter(etat, entite, direction)


def _orienter(etat, entite, direction):
    """Ne change l'orientation que lorsqu'un déplacement horizontal existe."""
    if direction:
        etat["orientations"][entite["identifiant"]] = (
            "droite" if direction > 0 else "gauche"
        )


def _chevauche(entite, joueur, boite_collision):
    """Compare les hitbox sans tenir compte des pixels transparents du sprite."""
    gauche = float(entite["position_x"]) + boite_collision["decalage_x"]
    haut = float(entite["position_y"]) + boite_collision["decalage_y"]
    return (
        gauche < joueur["x"] + LARGEUR_JOUEUR
        and gauche + boite_collision["largeur"] > joueur["x"]
        and haut < joueur["y"] + HAUTEUR_JOUEUR
        and haut + boite_collision["hauteur"] > joueur["y"]
    )


def _boite_collision(entite):
    """Complète une hitbox personnalisée avec les dimensions de l'entité."""
    boite_collision = entite.get("boite_collision", {})
    return {
        "decalage_x": float(boite_collision.get("decalage_x", 0)),
        "decalage_y": float(boite_collision.get("decalage_y", 0)),
        "largeur": float(boite_collision.get("largeur", entite["largeur"])),
        "hauteur": float(boite_collision.get("hauteur", entite["hauteur"])),
    }


def _jouer_son_effet(etat, entite):
    chemin_son = entite.get("effets", {}).get("fichier_son", "")
    if not chemin_son:
        return
    chemin = Path(chemin_son)
    if not chemin.is_absolute():
        chemin = (RACINE_PROJET / chemin).resolve()
    if not chemin.is_file():
        raise FileNotFoundError(
            f"Son introuvable pour l'entité '{entite['identifiant']}' : {chemin}"
        )
    son = etat["sons_effets"].get(chemin)
    if son is None:
        # La mise en cache évite de relire et recréer un son à chaque contact.
        son = pygame.mixer.Sound(str(chemin))
        etat["sons_effets"][chemin] = son
    son.play()


def _delai_cadre_sequence(animation, nom_sequence):
    reglages = animation.get("reglages_direction", {}).get(nom_sequence, {})
    delai_cadre = reglages.get("duree_cadre_ms")
    if delai_cadre is None:
        delai_cadre = animation.get("duree_cadre_ms", 125)
    return max(1, float(delai_cadre))


def _retourner_sequence(animation, nom_sequence, orientation, axe):
    """Résout le retournement propre à une séquence ou à la direction de mort."""
    reglages = animation.get("reglages_direction", {}).get(nom_sequence, {})
    valeur = reglages.get(f"inverser_{axe}")
    if valeur is None:
        return animation.get(f"inverser_{axe}", False)
    if isinstance(valeur, bool):
        return valeur
    if nom_sequence == "mort" and valeur in (
        "direction_droite", "direction_gauche"
    ):
        direction_cible = "droite" if valeur == "direction_droite" else "gauche"
        return orientation == direction_cible
    raise ValueError(
        f"Réglage inverser_{axe} invalide pour la séquence '{nom_sequence}'."
    )


def dessiner_entites(etat, decalage_camera_x=0, decalage_camera_y=0):
    """Dessine les sprites dans l'ordre de profondeur préparé au chargement."""
    maintenant = time.perf_counter()
    for entite in etat["entites_affichage"]:
        identifiant = entite["identifiant"]
        est_mort = identifiant in etat["morts"]
        if (
            not entite.get("visible", True)
            or (not entite.get("actif", True) and not est_mort)
        ):
            continue
        image = etat["images"].get(identifiant)
        if image is None:
            continue
        animation = entite["animation"]
        orientation = etat["orientations"].get(identifiant, "droite")
        nom_sequence = "mort" if est_mort else orientation
        sequence = animation.get("animations_par_direction", {}).get(nom_sequence, [])
        if sequence:
            # La mort démarre à l'élimination; les autres séquences bouclent depuis le lancement.
            debut = etat["morts"][identifiant] if est_mort else etat["debut_animations"]
            delai_cadre = _delai_cadre_sequence(animation, nom_sequence)
            numero_cadre = int((maintenant - debut) * 1000 / delai_cadre)
            if est_mort:
                if numero_cadre >= len(sequence):
                    etat["morts"].pop(identifiant, None)
                    continue
                numero_cadre = min(numero_cadre, len(sequence) - 1)
            else:
                numero_cadre %= len(sequence)
            origine_sprite_x = (
                sequence[numero_cadre]["colonne"]
                * int(animation["largeur_cadre"])
            )
            origine_sprite_y = (
                sequence[numero_cadre]["ligne"]
                * int(animation["hauteur_cadre"])
            )
        else:
            if est_mort:
                continue
            nombre_cadres = max(1, int(animation.get("nombre_cadres", 1)))
            cadres_par_seconde = max(
                0.1, float(animation.get("cadres_par_seconde", 8))
            )
            numero_cadre = int(
                (maintenant - etat["debut_animations"]) * cadres_par_seconde
            )
            if animation.get("boucler", True):
                numero_cadre %= nombre_cadres
            else:
                numero_cadre = min(numero_cadre, nombre_cadres - 1)
            colonnes = max(1, int(animation.get("nombre_colonnes", 1)))
            origine_sprite_x = (
                numero_cadre % colonnes
            ) * int(animation["largeur_cadre"])
            origine_sprite_y = (
                int(animation.get("ligne", 0)) + numero_cadre // colonnes
            ) * int(animation["hauteur_cadre"])

        largeur = int(animation["largeur_cadre"])
        hauteur = int(animation["hauteur_cadre"])
        inverser_x = (
            _retourner_sequence(animation, nom_sequence, orientation, "x")
            if sequence else animation.get("inverser_x", False)
        )
        inverser_y = (
            _retourner_sequence(animation, nom_sequence, orientation, "y")
            if sequence else animation.get("inverser_y", False)
        )
        if inverser_x:
            largeur = -largeur
        if inverser_y:
            hauteur = -hauteur
        pyxel.blt(
            int(
                entite["position_x"] - decalage_camera_x
                + animation.get("decalage_x", 0)
            ),
            int(
                entite["position_y"] - decalage_camera_y
                + animation.get("decalage_y", 0)
            ),
            image, origine_sprite_x, origine_sprite_y, largeur, hauteur,
            COULEUR_TRANSPARENCE,
        )
