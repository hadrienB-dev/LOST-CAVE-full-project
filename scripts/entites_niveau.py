"""Définitions françaises et compactes des entités du niveau."""


def _creer_cadres(ligne, colonnes):
    return [
        {"colonne": colonne, "ligne": ligne}
        for colonne in colonnes
    ]


def _creer_animation_monstre():
    return {
        "largeur_cadre": 32,
        "hauteur_cadre": 32,
        "nombre_colonnes": 3,
        "nombre_cadres": 2,
        "ligne": 1,
        "cadres_par_seconde": 5.0,
        "duree_cadre_ms": 200.0,
        "animations_par_direction": {
            "gauche": _creer_cadres(0, (0, 1)),
            "droite": _creer_cadres(0, (2, 3)),
            "mort": [
                {"colonne": colonne, "ligne": ligne}
                for ligne in range(1, 4)
                for colonne in range(4)
            ],
        },
        "reglages_direction": {
            "mort": {
                "duree_cadre_ms": 75.0,
                "inverser_x": "direction_droite",
            },
        },
    }


def _creer_mouvement_monstre(patrouiller):
    etapes = (
        [
            {"direction": "gauche", "distance": 32.0},
            {"direction": "droite", "distance": 32.0},
        ]
        if patrouiller
        else []
    )
    return {
        "mode": "etapes",
        "axe": "position_x",
        "vitesse": 0.4,
        "portee": 32.0,
        "etapes": etapes,
        "gravite": True,
        "rebondir": True,
        "orientation": "droite",
    }


def _creer_monstre(identifiant, position_x, position_y, patrouiller=False):
    return {
        "identifiant": identifiant,
        "categorie": "ennemi",
        "position_x": position_x,
        "position_y": position_y,
        "largeur": 32,
        "hauteur": 32,
        "boite_collision": {
            "decalage_x": 4,
            "decalage_y": 16,
            "largeur": 24,
            "hauteur": 16,
        },
        "peut_etre_tue": True,
        "collision": True,
        "fichier_sprite": "assets/sprites/monster_1.png",
        "animation": _creer_animation_monstre(),
        "mouvement": _creer_mouvement_monstre(patrouiller),
        "effets": {
            "declencheur": "contact",
            "action": "blesser",
            "fichier_son": "assets/audio/kill_ennemy.ogg",
            "cible": "joueur",
        },
    }


def creer_entites_niveau():
    """Crée des données françaises fraîches pour chaque partie."""
    return [
        {
            "identifiant": "pic-1",
            "categorie": "ennemi",
            "position_x": 96,
            "position_y": 192,
            "largeur": 32,
            "hauteur": 32,
            "boite_collision": {
                "decalage_x": 12,
                "decalage_y": 16,
                "largeur": 8,
                "hauteur": 16,
            },
            "collision": True,
            "mouvement": {
                "mode": "immobile",
                "axe": "position_x",
                "vitesse": 1.0,
                "portee": 96.0,
                "etapes": [],
                "gravite": False,
                "rebondir": False,
                "orientation": "droite",
            },
            "effets": {
                "declencheur": "contact",
                "action": "blesser",
                "fichier_son": "assets/audio/hurt.ogg",
                "cible": "joueur",
            },
        },
        _creer_monstre("ennemi-3", 512, 480, patrouiller=True),
        _creer_monstre("ennemi-4", 768, 512),
        _creer_monstre("ennemi-5", 640, 160),
    ]
