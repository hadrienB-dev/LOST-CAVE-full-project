"""Boucle de jeu, états, interface et rendu."""

from math import ceil

import pyxel
import pygame

from .config import *
from .config import DUREE_FONDU_SPLASH_FRAMES, FICHIER_FOND_INTRO, FICHIER_PORTRAIT_HERO
from .joueur import (
    creer_joueur,
    dessiner_joueur,
    mettre_a_jour_joueur,
    reapparaitre_joueur,
)
from .entites import creer_entites, dessiner_entites, mettre_a_jour_entites
from .eclairage import appliquer, creer_eclairage
from .tiled_map import (
    creer_carte,
    dessiner_carte,
    mettre_a_jour_objets_collectes,
    recolter_citrouilles,
    recolter_gold_skulls,
    reinitialiser_objets_collectes,
)


_SEQUENCE_CAMERA_SHAKE = (
    (3, -2),
    (-3, 2),
    (2, 1),
    (-2, -2),
    (2, -1),
    (-1, 2),
    (1, -1),
    (-1, 1),
    (1, 0),
    (0, -1),
    (0, 1),
    (0, 0),
)


def initialiser_jeu():
    """Charge une fois les ressources et crée l'état complet du jeu."""
    jeu = {
        "carte": None,
        "entites": None,
        "eclairage": None,
        "etat": "splash",
        "frames_splash": 0,
        "frame_animation_acide_titre": 0,
        "cadence_animation_acide_titre": 0,
        "frames_dithering_fond_titre": 0,
        "fondu_animation_acide_titre": None,
        "delai_intro_apres_transition": 0,
        "joueur": creer_joueur(),
        "gold_skulls": 0,
        "pumpkins": 0,
        "temps_jeu_frames": 0,
        "camera_shake_frames": 0,
        "camera_shake_duration_frames": 0,
        "transition_fondu": None,
        "frame_fondu": 0,
        "phase_intro": None,
        "dialogue_intro": 0,
        "caracteres_dialogue": 0,
        "frames_caractere_dialogue": 0,
        "phase_fin": None,
        "dialogue_fin": 0,
        "fin_declenchee": False,
        "attente_atterrissage_gardien": False,
        "image_fond_intro": None,
        "image_splash": None,
        "image_animation_acide_titre": None,
        "image_portrait_hero": None,
        "image_icones_hud": None,
        "son_splash": None,
        "canal_splash": None,
        "son_acide_transition": None,
        "canal_acide_transition": None,
        "son_dialogue": None,
        "canal_dialogue": None,
        "son_suspense_intro": None,
        "canal_suspense_intro": None,
        "son_impact_intro": None,
        "canal_impact_intro": None,
    }
    charger_ressources(jeu)
    jeu["carte"] = creer_carte()
    jeu["entites"] = creer_entites()
    jeu["eclairage"] = creer_eclairage()

    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    jeu["son_splash"] = pygame.mixer.Sound(FICHIER_SON_SPLASH)
    jeu["canal_splash"] = pygame.mixer.Channel(1)
    jeu["canal_splash"].play(jeu["son_splash"])
    jeu["son_acide_transition"] = pygame.mixer.Sound(FICHIER_SON_ACIDE_TRANSITION)
    jeu["canal_acide_transition"] = pygame.mixer.Channel(4)
    jeu["son_dialogue"] = pygame.mixer.Sound(FICHIER_SFX_DIALOGUE)
    jeu["canal_dialogue"] = pygame.mixer.Channel(0)
    jeu["son_suspense_intro"] = pygame.mixer.Sound(FICHIER_SON_SUSPENSE_INTRO)
    jeu["canal_suspense_intro"] = pygame.mixer.Channel(2)
    jeu["son_impact_intro"] = pygame.mixer.Sound(FICHIER_SON_IMPACT_INTRO)
    jeu["canal_impact_intro"] = pygame.mixer.Channel(3)
    pyxel.channels[1].gain = VOLUME_SAUT
    pyxel.sounds[1].pcm(FICHIER_SAUT)
    pyxel.sounds[3].pcm(FICHIER_FIN_SAUT)
    pyxel.sounds[4].pcm(FICHIER_COLLECTE_CRANE)
    return jeu


def changer_musique(fichier):
    pygame.mixer.music.load(fichier)
    pygame.mixer.music.play(-1)


def charger_ressources(jeu):
    pyxel.load(FICHIER_RESSOURCES)
    pyxel.images[BANQUE_JOUEUR].load(0, 0, FICHIER_SPRITESHEET)
    pyxel.images[BANQUE_JOUEUR].load(
        DEBUT_SPRITESHEET_SAUT, 0, FICHIER_SPRITESHEET_SAUT
    )
    pyxel.images[BANQUE_FOND].load(0, 0, FICHIER_FOND)
    pyxel.images[BANQUE_TITRE].load(0, ORIGINE_Y_FOND_TITRE, FICHIER_FOND_TITRE)
    pyxel.images[BANQUE_SOL].load(0, ORIGINE_Y_SOL, FICHIER_SOL)
    jeu["image_fond_intro"] = pyxel.Image(LARGEUR_ECRAN, HAUTEUR_ECRAN)
    jeu["image_fond_intro"].load(0, 0, FICHIER_FOND_INTRO)
    jeu["image_splash"] = pyxel.Image(LARGEUR_ECRAN, HAUTEUR_ECRAN)
    jeu["image_splash"].load(0, 0, FICHIER_SPLASH)
    jeu["image_animation_acide_titre"] = pyxel.Image(
        LARGEUR_FRAME_ANIMATION_ACIDE_TITRE * NB_FRAMES_ANIMATION_ACIDE_TITRE,
        HAUTEUR_FRAME_ANIMATION_ACIDE_TITRE,
    )
    jeu["image_animation_acide_titre"].load(
        0, 0, FICHIER_ANIMATION_ACIDE_TITRE
    )
    jeu["image_portrait_hero"] = pyxel.Image(73, 104)
    jeu["image_portrait_hero"].load(0, 0, FICHIER_PORTRAIT_HERO)
    jeu["image_icones_hud"] = pyxel.Image(32, 16)
    jeu["image_icones_hud"].load(0, 0, FICHIER_ICONES_HUD)


def mettre_a_jour_jeu(jeu):
    mettre_a_jour_camera_shake(jeu)
    # Chaque écran non jouable gère son propre cycle puis s'arrête ici.
    if jeu["etat"] == "splash":
        jeu["frames_splash"] += 1
        if jeu["frames_splash"] >= DUREE_SPLASH_FRAMES:
            jeu["etat"] = "menu"
            changer_musique(FICHIER_MUSIQUE_TITRE)
        return
    if jeu["etat"] == "menu":
        mettre_a_jour_menu(jeu)
        return
    if jeu["etat"] == "animation_acide_titre":
        mettre_a_jour_animation_acide_titre(jeu)
        return
    if jeu["etat"] in ("credits", "touches", "conseils"):
        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) and bouton_survole(
            74, 105, 92, 18
        ):
            jeu["etat"] = "menu"
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            jeu["etat"] = "menu"
        return

    if (
        jeu["etat"] == "jeu"
        and jeu["phase_intro"] is None
        and jeu.get("phase_fin") is None
    ):
        jeu["temps_jeu_frames"] += 1

    if jeu["transition_fondu"] is not None:
        mettre_a_jour_fondu(jeu)
        return

    # Le dialogue et les statistiques figent le monde jusqu'au retour au titre.
    if jeu.get("phase_fin") == "dialogue":
        _mettre_a_jour_dialogue_fin(jeu)
        return
    if jeu.get("phase_fin") == "stats":
        if (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and bouton_survole(37, 88, 168, 16)
        ):
            retourner_ecran_titre(jeu)
        return

    # L'intro et les transitions suspendent la partie pour éviter les déplacements hors écran.
    mettre_a_jour_objets_collectes(jeu["carte"])
    if jeu["phase_intro"] == "dialogue":
        _mettre_a_jour_dialogue_intro(jeu)
        return

    if jeu["attente_atterrissage_gardien"]:
        _mettre_a_jour_atterrissage_gardien(jeu)
        return

    joueur = jeu["joueur"]
    # La position précédente permet de distinguer un atterrissage sur un ennemi d'un contact latéral.
    ancienne_y = joueur["y"]
    ancienne_vitesse_y = joueur["velocity_y"]
    mettre_a_jour_joueur(joueur, jeu["carte"])
    mettre_a_jour_entites(
        jeu["entites"], joueur, ancienne_y, ancienne_vitesse_y
    )
    if joueur.get("impact_camera_demandee", False):
        demarrer_camera_shake(jeu)
        joueur["impact_camera_demandee"] = False
    if joueur["reapparition_demandee"]:
        jeu["transition_fondu"] = "sortie"
        jeu["frame_fondu"] = 0
        return

    cranes_recoltes = recolter_gold_skulls(
        jeu["carte"], joueur["x"], joueur["y"],
        LARGEUR_JOUEUR, HAUTEUR_JOUEUR,
    )
    citrouilles_recoltees = recolter_citrouilles(
        jeu["carte"], joueur["x"], joueur["y"],
        LARGEUR_JOUEUR, HAUTEUR_JOUEUR,
    )
    jeu["gold_skulls"] += cranes_recoltes
    jeu["pumpkins"] += citrouilles_recoltees
    if cranes_recoltes or citrouilles_recoltees:
        pyxel.play(2, 4)
    if (
        not jeu["fin_declenchee"]
        and _joueur_touche_declencheur_fin(joueur)
    ):
        jeu["fin_declenchee"] = True
        if joueur["au_sol"]:
            demarrer_fin_niveau(jeu)
        else:
            jeu["attente_atterrissage_gardien"] = True
            joueur["velocity_y"] = max(0, joueur["velocity_y"])
            joueur["moving"] = False


def _joueur_touche_declencheur_fin(joueur):
    """Détecte le déclencheur sur toute sa colonne, quelle que soit la hauteur."""
    colonne = POSITION_FIN_NIVEAU[0]
    debut_x = colonne * TAILLE_TILE
    fin_x = debut_x + TAILLE_TILE
    return joueur["x"] < fin_x and joueur["x"] + LARGEUR_JOUEUR > debut_x


def _mettre_a_jour_atterrissage_gardien(jeu):
    """Bloque le déplacement et attend que le joueur retombe avant le dialogue."""
    joueur = jeu["joueur"]
    mettre_a_jour_joueur(joueur, jeu["carte"], deplacement_force=0)
    if joueur["reapparition_demandee"]:
        jeu["attente_atterrissage_gardien"] = False
        jeu["fin_declenchee"] = False
        jeu["transition_fondu"] = "sortie"
        jeu["frame_fondu"] = 0
    elif joueur["au_sol"]:
        jeu["attente_atterrissage_gardien"] = False
        demarrer_fin_niveau(jeu)


def _mettre_a_jour_dialogue_intro(jeu):
    if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
        nombre_caracteres = sum(
            len(ligne) for ligne in LIGNES_DIALOGUE_INTRO[jeu["dialogue_intro"]]
        )
        if jeu["caracteres_dialogue"] < nombre_caracteres:
            jeu["caracteres_dialogue"] = nombre_caracteres
            arreter_son_dialogue(jeu)
        elif jeu["dialogue_intro"] == len(LIGNES_DIALOGUE_INTRO) - 1:
            # Le fondu final attend la fin de l'impact sonore pour préserver le rythme de l'introduction.
            if jeu["canal_impact_intro"].get_busy():
                return
            jeu["phase_intro"] = "fondu_dialogue"
            jeu["transition_fondu"] = "sortie_intro"
            jeu["frame_fondu"] = 0
            jeu["canal_suspense_intro"].stop()
        else:
            if jeu["dialogue_intro"] == 1:
                lancer_impact_intro(jeu)
            jeu["dialogue_intro"] += 1
            jeu["caracteres_dialogue"] = 0
            jeu["frames_caractere_dialogue"] = 0
            lancer_son_dialogue(jeu)
        return

    nombre_caracteres = sum(
        len(ligne) for ligne in LIGNES_DIALOGUE_INTRO[jeu["dialogue_intro"]]
    )
    if jeu["caracteres_dialogue"] < nombre_caracteres:
        _mettre_a_jour_revelation_dialogue(
            jeu, LIGNES_DIALOGUE_INTRO[jeu["dialogue_intro"]]
        )


def _mettre_a_jour_dialogue_fin(jeu):
    lignes = LIGNES_DIALOGUE_FIN[jeu["dialogue_fin"]]
    nombre_caracteres = sum(len(ligne) for ligne in lignes)
    if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
        if jeu["caracteres_dialogue"] < nombre_caracteres:
            jeu["caracteres_dialogue"] = nombre_caracteres
            arreter_son_dialogue(jeu)
        elif jeu["dialogue_fin"] == len(LIGNES_DIALOGUE_FIN) - 1:
            arreter_son_dialogue(jeu)
            jeu["phase_fin"] = "stats"
        else:
            jeu["dialogue_fin"] += 1
            jeu["caracteres_dialogue"] = 0
            jeu["frames_caractere_dialogue"] = 0
            lancer_son_dialogue(jeu)
        return
    if jeu["caracteres_dialogue"] < nombre_caracteres:
        _mettre_a_jour_revelation_dialogue(jeu, lignes)


def _mettre_a_jour_revelation_dialogue(jeu, lignes):
    jeu["frames_caractere_dialogue"] += 1
    if jeu["frames_caractere_dialogue"] >= FRAMES_PAR_CARACTERE_DIALOGUE:
        jeu["caracteres_dialogue"] += 1
        jeu["frames_caractere_dialogue"] = 0
        if jeu["caracteres_dialogue"] >= sum(map(len, lignes)):
            arreter_son_dialogue(jeu)


def demarrer_fin_niveau(jeu):
    jeu["fin_declenchee"] = True
    jeu["attente_atterrissage_gardien"] = False
    jeu["phase_fin"] = "dialogue"
    jeu["joueur"]["moving"] = False
    jeu["dialogue_fin"] = 0
    jeu["caracteres_dialogue"] = 0
    jeu["frames_caractere_dialogue"] = 0
    lancer_son_dialogue(jeu)


def mettre_a_jour_camera_shake(jeu):
    jeu["camera_shake_frames"] = max(0, jeu.get("camera_shake_frames", 0) - 1)


def decalage_camera_shake(jeu):
    if jeu["camera_shake_frames"] <= 0:
        return 0, 0
    duree = jeu.get(
        "camera_shake_duration_frames", len(_SEQUENCE_CAMERA_SHAKE)
    )
    frame = duree - jeu["camera_shake_frames"]
    frame_sequence = frame % len(_SEQUENCE_CAMERA_SHAKE)
    offset_x, offset_y = _SEQUENCE_CAMERA_SHAKE[frame_sequence]
    if duree <= len(_SEQUENCE_CAMERA_SHAKE):
        return offset_x, offset_y
    if frame >= duree - 1:
        return 0, 0
    # Réduit l'amplitude lorsque le son dure plus longtemps que la séquence visuelle.
    intensite = 1 - 0.6 * frame / (duree - 1)
    return round(offset_x * intensite), round(offset_y * intensite)


def demarrer_camera_shake(jeu, duree_frames=None):
    if duree_frames is None:
        duree_frames = len(_SEQUENCE_CAMERA_SHAKE)
    jeu["camera_shake_duration_frames"] = max(1, duree_frames)
    jeu["camera_shake_frames"] = jeu["camera_shake_duration_frames"]


def lancer_impact_intro(jeu):
    jeu["canal_impact_intro"].play(jeu["son_impact_intro"])
    duree_frames = ceil(jeu["son_impact_intro"].get_length() * FPS_JEU)
    demarrer_camera_shake(jeu, duree_frames)


def bouton_survole(x, y, largeur, hauteur):
    return (
        x <= pyxel.mouse_x < x + largeur
        and y <= pyxel.mouse_y < y + hauteur
    )


def mettre_a_jour_menu(jeu):
    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
        if bouton_survole(132, 43, 94, 18):
            demarrer_animation_acide_titre(jeu)
        elif bouton_survole(132, 67, 94, 18):
            jeu["etat"] = "credits"
        elif bouton_survole(132, 91, 94, 18):
            pyxel.quit()
    if pyxel.btnp(pyxel.KEY_RETURN):
        demarrer_animation_acide_titre(jeu)
    elif pyxel.btnp(pyxel.KEY_C):
        jeu["etat"] = "credits"
    elif pyxel.btnp(pyxel.KEY_K):
        jeu["etat"] = "touches"
    elif pyxel.btnp(pyxel.KEY_T):
        jeu["etat"] = "conseils"


def demarrer_jeu(jeu):
    jeu["etat"] = "jeu"
    jeu["temps_jeu_frames"] = 0
    pygame.mixer.music.stop()
    jeu["transition_fondu"] = None
    jeu["phase_intro"] = "dialogue"
    jeu["dialogue_intro"] = 0
    jeu["caracteres_dialogue"] = 0
    jeu["frames_caractere_dialogue"] = 0
    jeu["canal_suspense_intro"].play(jeu["son_suspense_intro"], loops=-1)
    lancer_son_dialogue(jeu)


def demarrer_animation_acide_titre(jeu):
    jeu["etat"] = "animation_acide_titre"
    jeu["frame_animation_acide_titre"] = 0
    jeu["cadence_animation_acide_titre"] = 0
    jeu["frames_dithering_fond_titre"] = 0
    jeu["fondu_animation_acide_titre"] = None
    jeu["delai_intro_apres_transition"] = 0
    pygame.mixer.music.stop()
    jeu["canal_acide_transition"].play(jeu["son_acide_transition"])


def mettre_a_jour_animation_acide_titre(jeu):
    jeu["frames_dithering_fond_titre"] = min(
        jeu["frames_dithering_fond_titre"] + 1,
        DUREE_DITHERING_FOND_TITRE_FRAMES,
    )
    if jeu["fondu_animation_acide_titre"] is not None:
        if jeu["delai_intro_apres_transition"] > 0:
            jeu["delai_intro_apres_transition"] -= 1
            if jeu["delai_intro_apres_transition"] == 0:
                demarrer_jeu(jeu)
                jeu["transition_fondu"] = "entree"
                jeu["frame_fondu"] = 0
        elif jeu["fondu_animation_acide_titre"] < DUREE_FONDU_FRAMES:
            jeu["fondu_animation_acide_titre"] += 1
            if jeu["fondu_animation_acide_titre"] >= DUREE_FONDU_FRAMES:
                jeu["delai_intro_apres_transition"] = (
                    DELAI_INTRO_APRES_TRANSITION_FRAMES
                )
        return

    jeu["cadence_animation_acide_titre"] += 1
    if (
        jeu["cadence_animation_acide_titre"]
        < FRAMES_PAR_FRAME_ANIMATION_ACIDE_TITRE
    ):
        return

    jeu["cadence_animation_acide_titre"] = 0
    if jeu["frame_animation_acide_titre"] < NB_FRAMES_ANIMATION_ACIDE_TITRE - 1:
        jeu["frame_animation_acide_titre"] += 1
    else:
        jeu["fondu_animation_acide_titre"] = 0


def _dessiner_ecran_noir(opacite):
    pyxel.dither(max(0, min(1, opacite)))
    pyxel.rect(0, 0, pyxel.width, pyxel.height, 0)
    pyxel.dither(1)


def lancer_son_dialogue(jeu):
    jeu["canal_dialogue"].play(jeu["son_dialogue"], loops=-1)


def arreter_son_dialogue(jeu):
    jeu["canal_dialogue"].stop()


def retourner_ecran_titre(jeu):
    """Réinitialise la partie terminée avant de revenir au menu."""
    arreter_son_dialogue(jeu)
    reapparaitre_joueur(jeu["joueur"])
    reinitialiser_objets_collectes(jeu["carte"])
    jeu["entites"] = creer_entites()
    jeu["gold_skulls"] = 0
    jeu["pumpkins"] = 0
    jeu["temps_jeu_frames"] = 0
    jeu["phase_fin"] = None
    jeu["dialogue_fin"] = 0
    jeu["fin_declenchee"] = False
    jeu["attente_atterrissage_gardien"] = False
    jeu["phase_intro"] = None
    jeu["dialogue_intro"] = 0
    jeu["caracteres_dialogue"] = 0
    jeu["frames_caractere_dialogue"] = 0
    jeu["transition_fondu"] = None
    jeu["frame_fondu"] = 0
    jeu["camera_shake_frames"] = 0
    jeu["camera_shake_duration_frames"] = 0
    jeu["etat"] = "menu"
    changer_musique(FICHIER_MUSIQUE_TITRE)


def mettre_a_jour_fondu(jeu):
    jeu["frame_fondu"] += 1
    if jeu["frame_fondu"] < DUREE_FONDU_FRAMES:
        return
    # Une sortie peut enchaîner sur une entrée; le joueur réapparaît pendant l'écran noir.
    if jeu["transition_fondu"] == "sortie_intro":
        jeu["phase_intro"] = None
        changer_musique(FICHIER_MUSIQUE)
        jeu["transition_fondu"] = "entree"
        jeu["frame_fondu"] = 0
    elif jeu["transition_fondu"] == "sortie":
        reapparaitre_joueur(jeu["joueur"])
        jeu["transition_fondu"] = "entree"
        jeu["frame_fondu"] = 0
    else:
        jeu["transition_fondu"] = None
        jeu["frame_fondu"] = 0


def dessiner_fondu(jeu):
    if jeu["transition_fondu"] in ("sortie", "sortie_intro"):
        opacite = jeu["frame_fondu"] / DUREE_FONDU_FRAMES
    elif jeu["transition_fondu"] == "entree":
        opacite = 1 - jeu["frame_fondu"] / DUREE_FONDU_FRAMES
    else:
        return
    _dessiner_ecran_noir(opacite)


def dessiner_bouton(texte, x, y, largeur, hauteur):
    survole = bouton_survole(x, y, largeur, hauteur)
    couleur_fond = 7 if survole else 0
    couleur_texte = 0 if survole else 7
    pyxel.rect(x, y, largeur, hauteur, couleur_fond)
    pyxel.rectb(x, y, largeur, hauteur, couleur_texte)
    pyxel.text(
        x + (largeur - len(texte) * 4) // 2,
        y + (hauteur - 5) // 2,
        texte,
        couleur_texte,
    )


def dessiner_menu():
    pyxel.blt(
        0, 0, BANQUE_TITRE, 0, ORIGINE_Y_FOND_TITRE,
        LARGEUR_ECRAN, HAUTEUR_ECRAN,
    )
    dessiner_bouton("JOUER", 132, 43, 94, 18)
    dessiner_bouton("CREDITS", 132, 67, 94, 18)
    dessiner_bouton("QUITTER", 132, 91, 94, 18)
    pyxel.text(8, 120, "K : Touches", 7)
    pyxel.text(182, 120, "T : Conseils", 7)


def dessiner_animation_acide_titre(jeu):
    dessiner_fond_titre()
    progression_dither = min(
        jeu["frames_dithering_fond_titre"]
        / DUREE_DITHERING_FOND_TITRE_FRAMES,
        1,
    )
    _dessiner_ecran_noir(progression_dither)
    pyxel.blt(
        0, 0, jeu["image_animation_acide_titre"],
        jeu["frame_animation_acide_titre"] * LARGEUR_FRAME_ANIMATION_ACIDE_TITRE,
        0, LARGEUR_ECRAN, HAUTEUR_ECRAN, 0,
    )
    if jeu["fondu_animation_acide_titre"] is not None:
        opacite = (
            jeu["fondu_animation_acide_titre"] / DUREE_FONDU_FRAMES
        )
        _dessiner_ecran_noir(opacite)


def dessiner_splash(jeu):
    pyxel.blt(
        0, 0, jeu["image_splash"], 0, 0,
        LARGEUR_ECRAN, HAUTEUR_ECRAN,
    )
    progression = min(
        (jeu["frames_splash"] + 1) / DUREE_FONDU_SPLASH_FRAMES,
        (DUREE_SPLASH_FRAMES - 1 - jeu["frames_splash"])
        / DUREE_FONDU_SPLASH_FRAMES,
        1,
    )
    # La même progression ouvre puis referme le splash sans ajouter d'état intermédiaire.
    pyxel.dither(1 - max(0, progression))
    pyxel.rect(0, 0, LARGEUR_ECRAN, HAUTEUR_ECRAN, 0)
    pyxel.dither(1)


def dessiner_credits(jeu):
    dessiner_fond_titre()
    pyxel.rect(108, 20, 122, 94, 1)
    pyxel.rectb(108, 20, 122, 94, 7)
    pyxel.text(148, 30, "CREDITS", 10)
    pyxel.text(121, 49, "Par Orb Studio :", 7)
    pyxel.text(
        121, 61,
        "- Hadrien BOISSY\n- Louka ROBIN\n- Raphael GADENNE\n\nREALISE EN PYTHON",
        7,
    )
    dessiner_bouton("RETOUR", 74, 105, 92, 18)


def dessiner_touches(jeu):
    dessiner_fond_titre()
    pyxel.rect(24, 25, 192, 72, 1)
    pyxel.rectb(24, 25, 192, 72, 7)
    pyxel.text(96, 36, "TOUCHES", 10)
    pyxel.text(45, 54, "GAUCHE / DROITE : SE DEPLACER", 7)
    pyxel.text(45, 68, "ESPACE : SAUTER", 7)
    pyxel.text(45, 80, "MAINTENIR : SAUTER PLUS HAUT", 7)
    dessiner_bouton("RETOUR", 74, 105, 92, 18)


def dessiner_conseils(jeu):
    dessiner_fond_titre()
    pyxel.rect(24, 25, 192, 72, 1)
    pyxel.rectb(24, 25, 192, 72, 7)
    pyxel.text(30, 31, "CONSEILS", 10)
    pyxel.text(
        30, 42,
        "- Utilisez un casque audio pour une meilleure\n"
        "experience.\n\n- Certains recoins cachent des citrouilles,\n"
        "cherchez-les bien !\n\n- Rebondissez sur le dessus d'un ennemi pour\n"
        "le tuer !",
        7,
    )
    dessiner_bouton("RETOUR", 74, 105, 92, 18)


def dessiner_fond_titre():
    pyxel.blt(
        0, 0, BANQUE_TITRE, 0, ORIGINE_Y_FOND_TITRE,
        LARGEUR_ECRAN, HAUTEUR_ECRAN,
    )


def dessiner_dialogue_intro(jeu):
    lignes = LIGNES_DIALOGUE_INTRO[jeu["dialogue_intro"]]
    x, y, largeur, hauteur = 8, 96, LARGEUR_ECRAN - 16, 32
    decalage_x, decalage_y = decalage_camera_shake(jeu)
    pyxel.blt(
        decalage_x, decalage_y, jeu["image_fond_intro"],
        0, 0, LARGEUR_ECRAN, HAUTEUR_ECRAN,
    )
    pyxel.blt(
        x + decalage_x, 37 + decalage_y, jeu["image_portrait_hero"],
        0, 0, 43, 61, COULEUR_TRANSPARENCE,
    )
    pyxel.rect(x + decalage_x, y + decalage_y, largeur, hauteur, 0)
    pyxel.rectb(x + decalage_x, y + decalage_y, largeur, hauteur, 7)
    debut_y = y + (hauteur - len(lignes) * 8) // 2
    caracteres_restants = jeu["caracteres_dialogue"]
    for index, ligne in enumerate(lignes):
        texte_visible = ligne[:caracteres_restants]
        caracteres_restants -= len(texte_visible)
        pyxel.text(
            x + 6 + decalage_x,
            debut_y + index * 8 + decalage_y,
            texte_visible,
            7,
        )
    nombre_caracteres = sum(len(ligne) for ligne in lignes)
    if jeu["caracteres_dialogue"] >= nombre_caracteres:
        pyxel.text(
            x + largeur - 30 + decalage_x,
            y + hauteur - 7 + decalage_y,
            "ESPACE",
            7,
        )


def dessiner_dialogue_fin(jeu):
    lignes = LIGNES_DIALOGUE_FIN[jeu["dialogue_fin"]]
    x, y, largeur, hauteur = 8, 88, LARGEUR_ECRAN - 16, 40
    pyxel.rect(x, y, largeur, hauteur, 0)
    pyxel.rectb(x, y, largeur, hauteur, 7)
    pyxel.text(x + 6, y + 4, "LE GARDIEN", 10)
    caracteres_restants = jeu["caracteres_dialogue"]
    for index, ligne in enumerate(lignes):
        texte_visible = ligne[:caracteres_restants]
        caracteres_restants -= len(texte_visible)
        pyxel.text(x + 6, y + 14 + index * 8, texte_visible, 7)
    if jeu["caracteres_dialogue"] >= sum(map(len, lignes)):
        pyxel.text(x + largeur - 30, y + hauteur - 7, "ESPACE", 7)


def dessiner_stats_fin(jeu):
    x, y, largeur, hauteur = 24, 24, LARGEUR_ECRAN - 48, 88
    pyxel.rect(x, y, largeur, hauteur, 0)
    pyxel.rectb(x, y, largeur, hauteur, 7)
    pyxel.text(x + 8, y + 7, "FIN DU CAUCHEMAR", 10)
    pyxel.text(x + 8, y + 21, f"Cranes d'or recuperes : {jeu['gold_skulls']}/20", 7)
    pyxel.text(x + 8, y + 31, f"Citrouilles recuperees : {jeu['pumpkins']}/3", 7)
    pyxel.text(x + 8, y + 43, f"Temps : {formater_temps(jeu)}", 7)
    dessiner_bouton("RETOUR A L'ECRAN TITRE", 37, 88, 168, 16)


def dessiner_jeu(jeu):
    pyxel.cls(0)
    if jeu["etat"] == "splash":
        dessiner_splash(jeu)
        return
    if jeu["etat"] == "menu":
        dessiner_menu()
        return
    if jeu["etat"] == "animation_acide_titre":
        dessiner_animation_acide_titre(jeu)
        return
    if jeu["etat"] == "credits":
        dessiner_credits(jeu)
        return
    if jeu["etat"] == "touches":
        dessiner_touches(jeu)
        return
    if jeu["etat"] == "conseils":
        dessiner_conseils(jeu)
        return
    if jeu["phase_intro"] in ("dialogue", "fondu_dialogue"):
        dessiner_dialogue_intro(jeu)
        dessiner_fondu(jeu)
        return

    pyxel.blt(
        0, 0, BANQUE_FOND, 0, 0, LARGEUR_ECRAN, HAUTEUR_ECRAN
    )
    joueur = jeu["joueur"]
    carte = jeu["carte"]
    camera_x = max(
        0,
        min(
            int(joueur["x"] + LARGEUR_JOUEUR / 2 - pyxel.width / 2),
            carte["largeur"] - pyxel.width,
        ),
    )
    camera_y = max(
        0,
        min(
            int(joueur["y"]) + HAUTEUR_JOUEUR // 2 - pyxel.height // 2,
            carte["hauteur"] - pyxel.height,
        ),
    )
    decalage_x, decalage_y = decalage_camera_shake(jeu)
    camera_x = max(0, min(camera_x + decalage_x, carte["largeur"] - pyxel.width))
    camera_y = max(0, min(camera_y + decalage_y, carte["hauteur"] - pyxel.height))
    # Ces calques passent derrière puis devant le joueur pour conserver la profondeur du décor.
    dessiner_carte(carte, camera_x, camera_y)
    dessiner_joueur(joueur, camera_x, camera_y)
    dessiner_carte(carte, camera_x, camera_y, devant=True)
    dessiner_entites(jeu["entites"], camera_x, camera_y)
    # L'éclairage assombrit la scène déjà composée; le HUD reste ainsi parfaitement lisible.
    appliquer(
        jeu["eclairage"], joueur["x"], joueur["y"], camera_x, camera_y
    )
    dessiner_compteurs_objets(jeu)
    dessiner_timer(jeu)
    if jeu.get("phase_fin") == "dialogue":
        dessiner_dialogue_fin(jeu)
    elif jeu.get("phase_fin") == "stats":
        dessiner_stats_fin(jeu)
    dessiner_fondu(jeu)


def formater_temps(jeu):
    total_millisecondes = jeu["temps_jeu_frames"] * 1000 // FPS_JEU
    secondes, millisecondes = divmod(total_millisecondes, 1000)
    return f"{secondes}.{millisecondes:03} s"


def dessiner_timer(jeu):
    texte = f"{formater_temps(jeu)}"
    pyxel.rect(2, 2, len(texte) * 4 + 6, 12, 0)
    pyxel.text(5, 5, texte, 7)


def dessiner_compteurs_objets(jeu):
    skulls = str(jeu["gold_skulls"])
    pumpkins = str(jeu["pumpkins"])
    taille_icone = 16
    espace_icone_texte = 2
    espace_compteurs = 6
    largeur_skulls = taille_icone + espace_icone_texte + len(skulls) * 4
    largeur_pumpkins = taille_icone + espace_icone_texte + len(pumpkins) * 4
    largeur_hud = largeur_skulls + espace_compteurs + largeur_pumpkins
    x = pyxel.width - largeur_hud - 4
    pyxel.rect(x - 2, 0, largeur_hud + 4, 16, 0)
    pyxel.blt(
        x, 0, jeu["image_icones_hud"], 0, 0, 16, 16,
        COULEUR_TRANSPARENCE,
    )
    pyxel.text(
        x + taille_icone + espace_icone_texte,
        (16 - 5) // 2, skulls, 10,
    )
    x_pumpkins = x + largeur_skulls + espace_compteurs
    pyxel.blt(
        x_pumpkins, 0, jeu["image_icones_hud"], 16, 0, 16, 16,
        COULEUR_TRANSPARENCE,
    )
    pyxel.text(
        x_pumpkins + taille_icone + espace_icone_texte,
        (16 - 5) // 2, pumpkins, 9,
    )
