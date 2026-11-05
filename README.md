# Lost Cave

Jeu de plateforme 2D d'horreur realise en Python avec Pyxel.

## Lancer le jeu

Depuis la racine du projet :

```bash
pip install -r requirements.txt
python main.py
```

## Organisation

- `main.py` : lancement du jeu.
- `scripts/` : boucle fonctionnelle, états sous forme de dictionnaires,
  personnage, éclairage, entités et carte Tiled.
- `assets/sprites/` et `assets/audio/` : ressources du jeu.
- `assets/maps/` : cartes et donnees des entites du niveau.

Le niveau utilise un eclairage radial qui suit le joueur, avec une penombre
ambiante et une transition douce autour de la zone eclairee. La lueur varie
doucement en continu ; son rayon de base, son amplitude, sa periode, le fondu et
la luminosite ambiante se reglent dans `scripts/config.py`. Les cranes dores et
les citrouilles recoltes sont comptes dans le HUD avec leurs icones respectives.
La camera tremble brievement lorsqu'un ennemi est ecrase ou que le joueur subit
des degats.

## Architecture pédagogique

Les scripts de `scripts/` n'utilisent pas de classes. `main.py` initialise
Pyxel, crée l'état du jeu avec `initialiser_jeu()`, puis délègue chaque image
aux fonctions `mettre_a_jour_jeu()` et `dessiner_jeu()`. Le joueur, la carte,
les entités et l'éclairage sont représentés par des dictionnaires manipulés
par des fonctions dédiées.

La carte convertie et les donnees de collision sont chargées une seule fois.
Les collisions sont précalculées en ensembles de coordonnées; seuls les tiles
visibles sont dessinés. Les entités du fichier annexe restent des dictionnaires
et leurs sprites sont chargés au démarrage.
