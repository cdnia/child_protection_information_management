# Dictionnaire de données

## Modèle de données retenu

Nous avons choisi une structure de données au **format long** (_long format_).

Dans cette approche, chaque ligne représente une valeur d'indicateur déclarée par un partenaire, pour une activité, une zone géographique et une période de reporting données.

Par exemple, si un partenaire déclare avoir organisé 8 séances de sensibilisation ayant enregistré 240 participations, ces deux résultats seront enregistrés sur deux lignes distinctes : l'une pour le nombre de séances et l'autre pour le nombre de participations.

Ce choix permet de gérer différents indicateurs sans devoir créer une nouvelle colonne pour chacun d'eux. Il facilite également les contrôles de qualité, la consolidation des résultats et leur analyse.

Nous avons retenu ce format pour commencer avec une structure suffisamment simple à comprendre et à faire évoluer. D'autres approches pourront être étudiées dans les prochaines versions du projet, si les besoins le justifient.

## Organisation des données

Le modèle s'appuiera sur trois ensembles de données :

- `reports` : identifie les rapports mensuels des partenaires. Un rapport correspond à un partenaire et à une période de reporting.
- `submissions` : conserve les différentes transmissions d'un rapport, notamment lorsqu'un partenaire apporte des corrections à des données déjà envoyées.
- `observations` : contient les valeurs des indicateurs déclarées dans chaque transmission.

Des référentiels seront également utilisés pour définir les partenaires, les activités, les zones géographiques et les indicateurs autorisés.

Cette séparation doit permettre de retrouver l'origine d'un résultat, de suivre ses éventuelles corrections et d'éviter de compter plusieurs fois des données provenant de différentes versions d'un même rapport.

## Données utilisées

Le projet utilisera uniquement des données synthétiques et agrégées, créées pour les besoins des exercices et des tests.

Aucune donnée personnelle réelle concernant des enfants, des familles ou des bénéficiaires ne sera collectée.

Les résultats produits ne représenteront donc pas des statistiques réelles sur la protection de l'enfant au Burkina Faso.

## Champs et types de données

À définir lors de la conception détaillée des tables.

## Relations et règles d'unicité

À définir avant la mise en place des traitements.

## Contrôles de qualité

À définir en fonction des champs, des indicateurs et des règles de reporting retenus.
