"""Point d’entrée de Lost Cave."""

import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lost Cave")
    parser.parse_args(argv)

    import pyxel
    from scripts.config import FPS_JEU, LARGEUR_ECRAN, HAUTEUR_ECRAN, TITRE
    from scripts.jeu import dessiner_jeu, initialiser_jeu, mettre_a_jour_jeu

    pyxel.init(LARGEUR_ECRAN, HAUTEUR_ECRAN, title=TITRE, fps=FPS_JEU)
    pyxel.mouse(True)

    jeu = initialiser_jeu()
    pyxel.run(
        lambda: mettre_a_jour_jeu(jeu),
        lambda: dessiner_jeu(jeu),
    )


if __name__ == "__main__":
    main()