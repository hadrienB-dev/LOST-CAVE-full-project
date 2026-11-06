"""Constantes de configuration du jeu."""

# Dimensions de la fenêtre et cadence visée par la boucle Pyxel.
LARGEUR_ECRAN = 240
HAUTEUR_ECRAN = 135
TITRE = "LOST CAVE"
FPS_JEU = 60

TAILLE_TILE = 32
# Ces coordonnées sont des colonnes/lignes de tuiles, pas des pixels.
DEBUT_TRANSITION_ECLAIRAGE_X = 37 * TAILLE_TILE
DUREE_TRANSITION_ECLAIRAGE = TAILLE_TILE
POSITION_FIN_NIVEAU = (54, 16)
LARGEUR_JOUEUR = 20
HAUTEUR_JOUEUR = 32
Y_DEPART = 192
DEBUT_SPRITESHEET_SAUT = LARGEUR_JOUEUR * 4

VITESSE_DEPLACEMENT = 1
VITESSE_ANIMATION = 15
TOLERANCE_SAUT_FRAMES = 6
COULEUR_TRANSPARENCE = 8
DUREE_FONDU_FRAMES = 24
DUREE_CAMERA_SHAKE_FRAMES = 12
DELAI_INTRO_APRES_TRANSITION_FRAMES = 2 * FPS_JEU

# Paramètres visuels partagés par le rendu du niveau et ses transitions.
RAYON_LUMIERE = 34
FONDU_LUMIERE = 30
VARIATION_RAYON_LUMIERE = 3
PERIODE_VARIATION_LUMIERE = 180
# Correspond à la luminosité minimale, hors du rayon du joueur.
LUMINOSITE_AMBIANTE = 0.2
NIVEAUX_ECLAIRAGE = 32
DUREE_SPLASH_FRAMES = 120
DUREE_FONDU_SPLASH_FRAMES = 24
FRAMES_PAR_CARACTERE_DIALOGUE = 2
DUREE_AFFICHAGE_STATS_FIN_FRAMES = 5 * FPS_JEU
LIGNES_DIALOGUE_INTRO = (
    ("Qu'est-ce que je fais ici ?",),
    (
        "Cet endroit est sinistre...",
    ),
    ("...",),
)
LIGNES_DIALOGUE_FIN = (
    (
        "TU AS REUSSI CETTE EPREUVE AVEC BRIO.",
        "PEU DE GENS AURAIENT SURVECU.",
    ),
    (
        "RECOIS LES FELICITATIONS",
        "DU MAITRE DES LIEUX.",
    ),
)

GRAVITE = 0.35
VITESSE_SAUT = -6.36
FORCE_SAUT_MAINTENU = 0.19
DUREE_SAUT_MAX_FRAMES = 12
VOLUME_SAUT = 0.04

# Banques et coordonnées utilisées pour éviter de recharger les images en jeu.
BANQUE_JOUEUR = 0
BANQUE_FOND = 1
BANQUE_SOL = 0
BANQUE_TITRE = 0
ORIGINE_Y_FOND_TITRE = 64
ORIGINE_Y_SOL = 224

# Ressources chargées une fois au démarrage.
FICHIER_RESSOURCES = "assets/pyxel/theme.pyxres"
FICHIER_SPRITESHEET = "assets/sprites/spritesheet_80x64.png"
FICHIER_SPRITESHEET_SAUT = "assets/sprites/spritesheet_jump.png"
FICHIER_ICONES_HUD = "assets/sprites/hud_icons.png"
FICHIER_FOND = "assets/sprites/level_background_240x135.png"
FICHIER_FOND_TITRE = "assets/sprites/title_screen_background.png"
FICHIER_ANIMATION_ACIDE_TITRE = "assets/sprites/animation_acide_title_screen.png"
FICHIER_SPLASH = "assets/sprites/splash.png"
FICHIER_FOND_INTRO = "assets/sprites/background_intro.png"
FICHIER_SOL = "assets/sprites/acide.png"
FICHIER_PORTRAIT_HERO = "assets/sprites/hero_mugshot.png"
FICHIER_MUSIQUE = "assets/audio/lost_cave.ogg"
FICHIER_MUSIQUE_TITRE = "assets/audio/title_screen.mp3"
LARGEUR_FRAME_ANIMATION_ACIDE_TITRE = 242
HAUTEUR_FRAME_ANIMATION_ACIDE_TITRE = 242
NB_FRAMES_ANIMATION_ACIDE_TITRE = 14
FRAMES_PAR_FRAME_ANIMATION_ACIDE_TITRE = 4
DUREE_DITHERING_FOND_TITRE_FRAMES = (
    NB_FRAMES_ANIMATION_ACIDE_TITRE
    * FRAMES_PAR_FRAME_ANIMATION_ACIDE_TITRE
    // 2
)
FICHIER_SON_SPLASH = "assets/audio/logo_reveal.ogg"
FICHIER_SON_ACIDE_TRANSITION = "assets/audio/acide_transition.ogg"
FICHIER_SON_SUSPENSE_INTRO = "assets/audio/horror_suspense_intro.mp3"
FICHIER_SON_IMPACT_INTRO = "assets/audio/horror_impact_intro.mp3"
FICHIER_SFX_DIALOGUE = "assets/audio/text_loop_speech.ogg"
FICHIER_SAUT = "assets/audio/jump.ogg"
FICHIER_FIN_SAUT = "assets/audio/jump_end.ogg"
FICHIER_COLLECTE_CRANE = "assets/audio/skull_collect.ogg"
