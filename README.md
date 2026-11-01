# Projet Gestion de l'information pour la protection de l'enfant

Prototype Python de validation, de consolidation et d'export de données de reporting dans un contexte de protection de l'enfant.

Ce projet utilise exclusivement des données synthétiques et agrégées. Il ne contient aucune donnée personnelle réelle d'enfant ou de bénéficiaire. Les partenaires, les zones et les résultats présentés sont fictifs.

Il s'agit d'un projet personnel de démonstration technique, indépendant de toute organisation humanitaire.

## Contexte et objectif

Le suivi d'activités réalisées par plusieurs partenaires nécessite des données cohérentes et suffisamment fiables pour être consolidées.

Un même rapport peut être transmis plusieurs fois lorsqu'un partenaire apporte des corrections. Les données peuvent également contenir des références inconnues, des valeurs invalides ou des incohérences entre fichiers.

J'ai développé ce prototype pour explorer ces problèmes à travers un processus de reporting mensuel, depuis la validation des fichiers sources jusqu'à la production de résultats consolidés.

Le système permet actuellement de :

- vérifier les référentiels et les données déclarées ;
- signaler les anomalies sans modifier silencieusement les fichiers sources ;
- contrôler les relations entre rapports, soumissions et observations ;
- vérifier les chaînes de révision ;
- sélectionner la dernière soumission approuvée de chaque rapport ;
- consolider les valeurs retenues par période, zone, activité et indicateur ;
- afficher les résultats dans le terminal ou les exporter au format CSV ;
- tester automatiquement les règles métier et les comportements attendus.

## Fonctionnement

Le traitement repose sur trois ensembles de données transactionnelles et cinq fichiers de référence.

Les données sont d'abord soumises à cinq étapes de validation :

1. Référentiels (`references`)
2. Rapports (`reports`)
3. Soumissions (`submissions`)
4. Chaînes de révision (`revision_chains`)
5. Observations (`observations`)

Chaque étape produit un état `PASS`, `FAIL` ou `SKIPPED`.

La consolidation est refusée si la validation échoue ou reste incomplète.

Lorsqu'un rapport possède plusieurs soumissions approuvées, seule celle ayant le numéro de révision le plus élevé est retenue. Les observations associées aux autres versions ne sont pas additionnées aux résultats.

Les valeurs retenues sont regroupées selon quatre dimensions : la période de reporting, la zone, l'activité et l'indicateur.

## Technologies utilisées

| Technologie                  | Utilisation                                         |
| ---------------------------- | --------------------------------------------------- |
| Python 3.13                  | Implémentation des traitements                      |
| Bibliothèque standard Python | Lecture des CSV, validation, agrégation et export   |
| uv                           | Gestion du projet et de l'environnement Python      |
| Pytest                       | Tests automatisés                                   |
| Ruff                         | Analyse statique et formatage                       |
| Mypy                         | Vérification statique des types                     |
| Git et GitHub                | Gestion des versions et historique du développement |

La version Python indiquée dans `.python-version` est `3.13.13`. Le projet accepte la série Python 3.13 selon `pyproject.toml`.

Les dépendances de développement figurent dans `pyproject.toml`, avec leurs versions résolues dans `uv.lock`.

## Installation

Le dépôt est disponible à l'adresse suivante :

https://github.com/cdnia/child_protection_information_management

### Prérequis

- Git, pour récupérer le dépôt ;
- uv, pour préparer l'environnement Python ;
- un environnement compatible avec Python 3.13.

Après avoir récupéré le dépôt, ouvrir sa racine dans un terminal.

Pour préparer un nouvel environnement à partir du fichier de verrouillage :

```sh
uv sync --locked
```

Cette commande peut créer ou modifier l'environnement virtuel `.venv` et installer les dépendances nécessaires.

Elle n'est pas nécessaire si l'environnement a déjà été préparé correctement.

La reproduction complète sur une installation propre reste une vérification à effectuer séparément.

## Utilisation

Les commandes suivantes s'exécutent depuis la racine du dépôt, après préparation de l'environnement.

L'option `--no-sync` permet de réutiliser l'environnement existant sans demander une nouvelle synchronisation.

### Afficher l'aide

```sh
uv run --no-sync python -m child_protection_information_management --help
```

### Valider les données

```sh
uv run --no-sync python -m child_protection_information_management validate
```

Avec les données synthétiques fournies, les cinq étapes produisent :

```text
references: PASS
reports: PASS
submissions: PASS
revision_chains: PASS
observations: PASS
```

Les anomalies détectées sont affichées avec leur code et, lorsque cette information est disponible, leur localisation.

### Consolider les observations

```sh
uv run --no-sync python -m child_protection_information_management consolidate
```

Cette commande valide le jeu de données avant d'afficher les résultats regroupés.

Pour le scénario synthétique de mars 2025, le traitement produit douze lignes consolidées.

### Exporter les résultats en CSV

Sur Linux, avec une destination qui n'existe pas encore :

```sh
uv run --no-sync python -m child_protection_information_management consolidate --output /tmp/cpim-demo-2025-03.csv
```

L'export comporte cinq colonnes :

```csv
reporting_period,area_code,activity_code,indicator_code,total_value
```

Le contenu est écrit en UTF-8, avec des fins de ligne LF et un ordre de lignes déterministe.

Le programme refuse de remplacer un fichier existant. Il refuse également les destinations situées dans le dossier source `data/`, selon les contrôles actuellement implémentés.

Le répertoire parent de la destination doit déjà exister.

Pour produire un nouvel export, il faut choisir un autre chemin de destination ou gérer explicitement le fichier précédent.

### Choisir un autre dossier de données

Les sous-commandes `validate` et `consolidate` acceptent l'option `--project-root PATH`.

Cette option indique la racine du projet contenant le dossier `data/`.

Lorsqu'un chemin relatif est fourni à `--output`, il est interprété depuis le répertoire courant d'exécution, et non depuis `--project-root`.

### Codes de sortie

| Code | Signification                                     |
| ---- | ------------------------------------------------- |
| `0`  | Opération réussie                                 |
| `1`  | Échec de validation, de consolidation ou d'export |
| `2`  | Argument de ligne de commande invalide            |

## Données de démonstration

Le jeu de données fourni correspond à un scénario fictif de reporting pour mars 2025.

| Résultat                    | Valeur synthétique |
| --------------------------- | -----------------: |
| Séances réalisées           |                 28 |
| Participations enregistrées |                652 |
| Groupes consolidés          |                 12 |

Ces valeurs servent uniquement à vérifier le fonctionnement du système.

Les **652 participations** ne représentent pas nécessairement 652 personnes distinctes. Une même personne peut participer à plusieurs activités ou séances.

Aucun de ces résultats ne doit être présenté comme une statistique humanitaire réelle.

## Modèle de données

Le projet utilise un modèle au **format long** (_long format_). Chaque observation représente une valeur d'indicateur associée à une soumission, une zone et une activité.

Les trois tables transactionnelles sont :

- `reports` : rapports mensuels associés aux partenaires ;
- `submissions` : transmissions et révisions successives des rapports ;
- `observations` : valeurs des indicateurs déclarées dans chaque soumission.

Cinq référentiels complètent ces tables :

- `partners` : partenaires fictifs ;
- `areas` : zones fictives ;
- `activities` : catégories d'activités ;
- `indicators` : définitions et unités des indicateurs ;
- `activity_indicators` : associations autorisées entre activités et indicateurs.

Le modèle et ses contraintes sont décrits dans le [dictionnaire de données](docs/data_dictionary.md).

Les contrôles implémentés et leurs limites sont documentés dans la [politique de validation](docs/validation_policy.md).

## Structure du dépôt

```text
data/
├── raw/
│   ├── reports.csv
│   ├── submissions.csv
│   └── observations.csv
└── reference/
    ├── partners.csv
    ├── areas.csv
    ├── activities.csv
    ├── indicators.csv
    └── activity_indicators.csv

docs/
├── data_dictionary.md
└── validation_policy.md

src/child_protection_information_management/
├── cli.py
├── consolidation.py
├── csv_export.py
├── csv_io.py
├── observation_validation.py
├── pipeline.py
├── reference_validation.py
├── selection.py
├── submission_validation.py
├── validation.py
└── workflow.py

tests/
├── test_cli.py
├── test_consolidation.py
├── test_csv_export.py
├── test_csv_io.py
├── test_observation_validation.py
├── test_pipeline.py
├── test_reference_validation.py
├── test_selection.py
├── test_submission_validation.py
├── test_validation.py
└── test_workflow.py
```

## Tests et contrôles de qualité

Après préparation de l'environnement, les contrôles suivants peuvent être exécutés depuis la racine du projet :

```sh
uv run --no-sync pytest -q
uv run --no-sync ruff check src tests
uv run --no-sync ruff format --check src tests
uv run --no-sync mypy src tests
```

Lors de la dernière vérification locale communiquée, le 1er novembre 2026 :

- 219 tests Pytest ont réussi ;
- Ruff n'a signalé aucune erreur ;
- les 24 fichiers Python contrôlés respectaient le formatage attendu ;
- Mypy n'a signalé aucune erreur de typage.

Ces résultats concernent l'environnement testé. Ils ne constituent pas une garantie de fonctionnement sur toutes les plateformes.

Les tests utilisent des fichiers temporaires lorsqu'ils doivent simuler des erreurs ou modifier des données.

## Décisions de conception

Plusieurs principes guident le développement :

**Conserver les versions des déclarations.** Une correction doit pouvoir être retracée sans perdre les transmissions précédentes.

**Ne pas mélanger les états de validation.** Une observation issue d'une soumission non approuvée ne doit pas entrer dans la consolidation.

**Distinguer les valeurs manquantes et les zéros.** Une absence de donnée ne constitue pas une déclaration d'activité nulle.

**Respecter les unités des indicateurs.** Le nombre de séances et le nombre de participations ne peuvent pas être interprétés comme une même mesure.

**Préserver les fichiers sources.** Les erreurs sont signalées plutôt que corrigées silencieusement.

**Tester les comportements, y compris les échecs.** Les tests vérifient notamment les références invalides, les révisions, les données absentes, les destinations existantes et le refus de certains exports dangereux.

## Limites connues

Le prototype n'est pas un système d'information humanitaire prêt pour un environnement de production.

Il ne garantit notamment pas :

- la réception de tous les rapports attendus ;
- la détection des éventuels doubles comptages d'activités réelles entre partenaires ;
- la couverture complète de toutes les règles métier ;
- la cohérence transactionnelle des fichiers lorsqu'ils sont modifiés pendant le traitement ;
- une protection absolue contre les changements concurrents malveillants du système de fichiers ;
- une interprétation identique du CSV par tous les tableurs ;
- la gestion d'utilisateurs, de rôles ou de permissions métier.

L'export prépare le fichier dans une destination temporaire avant de le publier sans remplacement, mais cette méthode ne constitue pas une transaction complète.

Les tests automatisés ne remplacent pas non plus une revue métier par des spécialistes de la gestion de l'information et de la protection de l'enfant.

Une vérification complète sur une installation propre et une automatisation des contrôles dans un système d'intégration continue restent à réaliser.

## Licence

Aucun fichier `LICENSE` n'est encore publié dans le dépôt.

Le projet est consultable sur GitHub, mais aucune licence open source explicite n'a encore été choisie. Les conditions de réutilisation devront être clarifiées avant de présenter le code comme librement redistribuable.
