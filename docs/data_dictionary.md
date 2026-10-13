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

### `reports` — Rapports

La table `reports` permet d'identifier les rapports mensuels des partenaires et de les distinguer de leurs différentes transmissions.

Chaque rapport est associé à un partenaire et à une période de reporting. Son identifiant reste inchangé lorsqu'une nouvelle transmission vient corriger des données déjà déclarées.

| Champ              | Type              | Obligatoire | Description                                                        |
| ------------------ | ----------------- | ----------- | ------------------------------------------------------------------ |
| `report_id`        | Texte             | Oui         | Identifiant unique du rapport, conservé même en cas de correction. |
| `partner_id`       | Texte             | Oui         | Identifiant du partenaire responsable du rapport.                  |
| `reporting_period` | Texte (`YYYY-MM`) | Oui         | Mois et année auxquels se rapportent les données.                  |

#### Règles de validation

- Chaque rapport possède un `report_id` unique.
- Un partenaire ne possède qu'un seul rapport logique pour une période mensuelle donnée.
- Le couple `partner_id` et `reporting_period` doit donc être unique.
- Le champ `partner_id` doit correspondre à un partenaire enregistré dans le référentiel.
- La période doit respecter le format `YYYY-MM` et correspondre à un mois valide.
- Les corrections d'un rapport sont enregistrées dans `submissions`, sans créer de nouveau rapport logique.

### `submissions` — Soumissions

La table `submissions` conserve les différentes transmissions d'un rapport. Elle permet de suivre les corrections apportées par les partenaires sans perdre les données précédemment reçues.

Chaque transmission possède son propre identifiant et un numéro de révision. Plusieurs transmissions peuvent ainsi être associées au même rapport.

| Champ                    | Type                                   | Obligatoire | Description                                                                                   |
| ------------------------ | -------------------------------------- | ----------- | --------------------------------------------------------------------------------------------- |
| `submission_id`          | Texte                                  | Oui         | Identifiant unique de la transmission.                                                        |
| `report_id`              | Texte                                  | Oui         | Identifiant du rapport auquel appartient la transmission.                                     |
| `revision_no`            | Entier positif                         | Oui         | Numéro de révision de la transmission, en commençant par 1.                                   |
| `previous_submission_id` | Texte                                  | Non         | Identifiant de la transmission précédente du même rapport, lorsqu'il s'agit d'une correction. |
| `submitted_at`           | Date et heure (`YYYY-MM-DDTHH:MM:SSZ`) | Oui         | Date et heure de réception de la transmission, exprimées en temps universel coordonné.        |
| `status`                 | Texte                                  | Oui         | État de traitement de la transmission.                                                        |

#### États de traitement

Les états suivants seront utilisés :

- `RECEIVED` : transmission reçue, en attente d'examen.
- `UNDER_REVIEW` : transmission en cours de vérification.
- `APPROVED` : transmission validée et utilisable pour la consolidation.
- `REJECTED` : transmission refusée à la suite des vérifications.

#### Règles de validation

- Chaque transmission possède un `submission_id` unique.
- Le champ `report_id` doit correspondre à un rapport existant.
- Le numéro de révision doit être supérieur ou égal à 1.
- Pour un même rapport, deux transmissions ne peuvent pas avoir le même numéro de révision.
- Une correction doit référencer la transmission précédente du même rapport.
- La première transmission d'un rapport ne possède pas de transmission précédente.
- La date de réception doit être valide et inclure l'heure.
- Le champ `status` doit correspondre à l'un des états autorisés.
- Seules les transmissions approuvées peuvent être utilisées pour produire les résultats consolidés.
- Lorsqu'un rapport possède plusieurs transmissions approuvées, seule celle portant le numéro de révision le plus élevé est retenue pour les nouvelles consolidations.

Les transmissions précédentes sont conservées afin de pouvoir retracer les corrections apportées aux rapports.

### `observations` — Observations

La table `observations` contient les résultats déclarés dans les rapports des partenaires.

Chaque ligne correspond à une valeur d'indicateur pour une activité et une zone géographique données. La période de reporting et le partenaire sont retrouvés à partir du rapport auquel appartient la soumission.

Cette organisation permet de conserver les résultats sous un format long (_long format_), sans créer une colonne différente pour chaque indicateur.

| Champ            | Type               | Obligatoire | Description                                           |
| ---------------- | ------------------ | ----------- | ----------------------------------------------------- |
| `observation_id` | Texte              | Oui         | Identifiant unique de l'observation.                  |
| `submission_id`  | Texte              | Oui         | Identifiant de la soumission contenant l'observation. |
| `area_code`      | Texte              | Oui         | Code de la zone géographique concernée.               |
| `activity_code`  | Texte              | Oui         | Code de l'activité déclarée.                          |
| `indicator_code` | Texte              | Oui         | Code de l'indicateur mesuré.                          |
| `reported_value` | Entier non négatif | Oui         | Valeur déclarée pour l'indicateur.                    |

#### Règles de validation

- Chaque observation possède un `observation_id` unique.
- Le champ `submission_id` doit correspondre à une soumission existante.
- Les codes des zones, des activités et des indicateurs doivent appartenir aux référentiels autorisés.
- L'indicateur déclaré doit être compatible avec l'activité concernée.
- Une observation ne peut pas contenir de valeur négative.
- Les indicateurs retenus représentent des dénombrements : leurs valeurs doivent donc être des nombres entiers.
- Une valeur égale à zéro est autorisée lorsqu'elle correspond à un résultat réellement déclaré.
- Une valeur manquante ne doit pas être remplacée automatiquement par zéro.
- Une soumission ne peut pas contenir plusieurs observations pour la même combinaison de zone géographique, d'activité et d'indicateur.

#### Unités de mesure

Chaque indicateur possède une définition et une unité de mesure précisées dans son référentiel.

Par exemple, le nombre de séances réalisées et le nombre de participations enregistrées sont deux indicateurs différents, même s'ils concernent la même activité.

Le nombre de participations ne doit pas être interprété automatiquement comme un nombre de personnes distinctes.

Les unités de mesure seront conservées dans le référentiel des indicateurs plutôt que répétées dans chaque observation.

## Relations et règles d'unicité

À définir avant la mise en place des traitements.

## Contrôles de qualité

À définir en fonction des champs, des indicateurs et des règles de reporting retenus.
