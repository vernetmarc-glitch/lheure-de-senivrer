# L’Heure de s’enivrer — fichiers développeur

## Fichiers
- `icon-dark.svg` : icône carrée, vectorielle, fond sombre intégré.
- `logo-horizontal-dark.svg` : signature horizontale pour les interfaces sombres (fond transparent hors icône).
- `logo-horizontal-light.svg` : signature horizontale pour les interfaces claires.

## Direction retenue
Trois horizons concentriques traversés par un rayon lumineux. Le point central représente l'observateur ; le trait lumineux évoque le déplacement de la lumière et relie les codes rouge-orangé, blanc et bleu-violet.

## Couleurs
- Fond principal : `#04050A`
- Accent bleu pâle : `#CFE6FF`
- Lumière rouge : `#FF593D`
- Lumière chaude : `#FFB06D`
- Lumière blanche : `#FFF9ED`
- Lumière violet : `#A99AFF`
- Lumière bleue : `#8BCAFF`
- Texte clair : `#F4F0E8`

## Typographies
- Titre / logo : Cinzel (prévoir le chargement de la fonte dans l'application).
- Interface : Jost.
- Fallback du SVG : Times New Roman / serif. Pour un rendu identique partout, convertir le texte du logo en tracés dans l'outil vectoriel de votre choix après validation de la fonte Cinzel exacte.

## Intégration
- Les SVG sont responsives et peuvent être utilisés directement comme assets.
- Icône : prévoir des exports PNG aux tailles 16, 32, 48, 180, 192, 512 px et un favicon `.ico` côté build.
- Garder une zone de protection égale à environ 10 % de la largeur de l'icône.
- Ne pas réduire les trois anneaux à moins de 24 px de diamètre extérieur ; à 32 px, privilégier l'icône complète sans détails supplémentaires.
- Ne pas ajouter d'ombre portée, de planète, de fusée ou de photographie de galaxie.
- La variante claire est prévue pour un fond ivoire ; l'icône conserve son fond cosmique sombre pour préserver le contraste.

## Note
Ces SVG constituent une base vectorielle exploitable et modifiable, pas une charte graphique finalisée. Le rendu typographique exact dépend de la présence de Cinzel dans le projet.
