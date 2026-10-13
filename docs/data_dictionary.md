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

## Référentiels

Les référentiels regroupent les codes et les informations de référence utilisés dans les rapports. Ils permettent notamment de vérifier qu'une valeur déclarée correspond à un partenaire, une zone, une activité ou un indicateur connu du système.

### `partners` — Partenaires

La table `partners` contient les organisations partenaires dont les activités sont suivies dans le projet.

Chaque partenaire possède un identifiant stable, utilisé dans les rapports, et un nom permettant de l'identifier plus facilement lors des analyses.

| Champ          | Type  | Obligatoire | Description                       |
| -------------- | ----- | ----------- | --------------------------------- |
| `partner_id`   | Texte | Oui         | Identifiant unique du partenaire. |
| `partner_name` | Texte | Oui         | Nom du partenaire.                |

#### Exemple de données

| partner_id    | partner_name              |
| ------------- | ------------------------- |
| `PARTNER_001` | Organisation partenaire A |
| `PARTNER_002` | Organisation partenaire B |
| `PARTNER_003` | Organisation partenaire C |

Ces organisations sont fictives et servent uniquement aux exercices et aux tests.

#### Règles de validation

- Chaque partenaire possède un `partner_id` unique et non vide.
- Le nom du partenaire ne doit pas être vide.
- Un identifiant ne doit pas être réattribué à un autre partenaire.
- Le champ `partner_id` utilisé dans `reports` doit correspondre à un partenaire enregistré dans ce référentiel.

### `areas` — Zones géographiques

La table `areas` contient les zones géographiques utilisées pour localiser les activités déclarées par les partenaires.

Chaque zone possède un code unique et un nom. Un champ supplémentaire permet de préciser le type de zone auquel elle correspond.

| Champ       | Type  | Obligatoire | Description                          |
| ----------- | ----- | ----------- | ------------------------------------ |
| `area_code` | Texte | Oui         | Code unique de la zone géographique. |
| `area_name` | Texte | Oui         | Nom de la zone géographique.         |
| `area_type` | Texte | Oui         | Type de zone géographique.           |

#### Exemple de données

| area_code | area_name      | area_type        |
| --------- | -------------- | ---------------- |
| `ZONE_A`  | Zone fictive A | `SIMULATED_ZONE` |
| `ZONE_B`  | Zone fictive B | `SIMULATED_ZONE` |
| `ZONE_C`  | Zone fictive C | `SIMULATED_ZONE` |

Ces zones sont entièrement fictives et ne correspondent pas à des circonscriptions administratives réelles du Burkina Faso.

La valeur `SIMULATED_ZONE` permet de les identifier explicitement comme des zones créées pour les exercices et les tests.

#### Règles de validation

- Chaque zone possède un `area_code` unique et non vide.
- Le nom et le type de la zone doivent être renseignés.
- Le champ `area_type` doit correspondre à un type de zone autorisé.
- Un code géographique ne doit pas être réattribué à une autre zone.
- Le champ `area_code` utilisé dans `observations` doit correspondre à une zone enregistrée dans ce référentiel.

#### Références géographiques

L'utilisation de zones administratives réelles nécessitera un référentiel géographique fiable, accompagné de sa source et de sa date de référence.

Cela permettra de tenir compte des éventuelles modifications du découpage administratif et d'éviter de mélanger des données géographiques qui ne correspondent pas aux mêmes limites territoriales.

### `activities` — Activités

La table `activities` répertorie les catégories d'activités suivies dans les rapports des partenaires.

Chaque activité possède un code unique, un nom et une description. Ces informations permettent d'utiliser les mêmes catégories dans l'ensemble des rapports et d'éviter les différences de désignation entre partenaires.

| Champ                  | Type  | Obligatoire | Description                              |
| ---------------------- | ----- | ----------- | ---------------------------------------- |
| `activity_code`        | Texte | Oui         | Code unique de l'activité.               |
| `activity_name`        | Texte | Oui         | Nom de l'activité.                       |
| `activity_description` | Texte | Oui         | Description du type d'activité concerné. |

#### Exemple de données

| activity_code             | activity_name                  | activity_description                                                                                  |
| ------------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `ACT_COMMUNITY_AWARENESS` | Sensibilisation communautaire  | Séances collectives consacrées à l'information et à la sensibilisation sur la protection de l'enfant. |
| `ACT_GROUP_PSYCHOSOCIAL`  | Soutien psychosocial collectif | Séances collectives de soutien psychosocial déclarées dans le cadre du scénario fictif.               |

Ces catégories servent à construire un jeu de données d'exercice. Elles ne constituent pas une classification officielle des activités de protection de l'enfant.

#### Règles de validation

- Chaque activité possède un `activity_code` unique et non vide.
- Le nom et la description de l'activité doivent être renseignés.
- Un code ne doit pas être réattribué à une autre activité.
- Le champ `activity_code` utilisé dans `observations` doit correspondre à une activité enregistrée dans ce référentiel.
- Les indicateurs associés à une activité doivent être compatibles avec sa définition.

#### Relation avec les indicateurs

Une même activité peut être suivie à l'aide de plusieurs indicateurs.

Par exemple, une activité de sensibilisation communautaire peut être mesurée par le nombre de séances réalisées et le nombre de participations enregistrées.

Ces deux résultats sont distincts et doivent être déclarés séparément.

La liste des indicateurs autorisés et leurs unités de mesure seront définies dans le référentiel `indicators`.

### `indicators` — Indicateurs

La table `indicators` définit les indicateurs utilisés pour mesurer les résultats des activités déclarées par les partenaires.

Chaque indicateur possède un code unique, un nom, une définition et une unité de mesure. Une règle d'agrégation précise également comment ses valeurs peuvent être regroupées lors des analyses.

| Champ                  | Type  | Obligatoire | Description                                                  |
| ---------------------- | ----- | ----------- | ------------------------------------------------------------ |
| `indicator_code`       | Texte | Oui         | Code unique de l'indicateur.                                 |
| `indicator_name`       | Texte | Oui         | Nom de l'indicateur.                                         |
| `indicator_definition` | Texte | Oui         | Définition de ce qui est mesuré et comptabilisé.             |
| `measure_unit`         | Texte | Oui         | Unité dans laquelle la valeur est exprimée.                  |
| `aggregation_method`   | Texte | Oui         | Méthode utilisée pour regrouper les valeurs de l'indicateur. |

#### Exemple de données

| indicator_code       | indicator_name              | measure_unit    | aggregation_method |
| -------------------- | --------------------------- | --------------- | ------------------ |
| `IND_SESSIONS_HELD`  | Séances réalisées           | `SESSION`       | `SUM`              |
| `IND_PARTICIPATIONS` | Participations enregistrées | `PARTICIPATION` | `SUM`              |

Ces indicateurs sont définis pour les besoins du projet et ne constituent pas un référentiel officiel d'indicateurs humanitaires.

#### Définition des indicateurs

**Séances réalisées (`IND_SESSIONS_HELD`)**

Cet indicateur mesure le nombre de séances effectivement organisées pendant la période de reporting, dans le cadre d'une activité donnée et dans une zone géographique déterminée.

Les séances annulées ou simplement prévues ne sont pas comptabilisées.

**Participations enregistrées (`IND_PARTICIPATIONS`)**

Cet indicateur mesure le nombre total de participations déclarées aux séances réalisées.

Une personne ayant participé à plusieurs séances peut être comptée plusieurs fois. L'indicateur ne mesure donc pas le nombre de personnes distinctes ayant bénéficié d'une activité.

#### Règles de validation

- Chaque indicateur possède un `indicator_code` unique et non vide.
- Le nom, la définition et l'unité de mesure doivent être renseignés.
- Un code ne doit pas être réattribué à un indicateur ayant une autre signification.
- Le champ `indicator_code` utilisé dans `observations` doit correspondre à un indicateur enregistré dans ce référentiel.
- Les valeurs des indicateurs définis ici doivent être des entiers non négatifs.
- La méthode d'agrégation doit appartenir aux méthodes autorisées.
- La méthode `SUM` correspond à l'addition des valeurs, lorsque les données concernées peuvent être additionnées sans double comptage.

#### Agrégation et interprétation des résultats

Les deux indicateurs utilisent la méthode `SUM`, mais leur addition doit respecter certaines conditions.

Avant de calculer un total, il faut notamment vérifier que les observations proviennent des soumissions approuvées, qu'elles ne sont pas des doublons et que les résultats regroupés sont compatibles.

Un total de participations ne doit pas être présenté comme un nombre de bénéficiaires uniques.

Les règles d'agrégation pourront être complétées lorsque nous définirons les traitements et les contrôles de qualité du système.

#### Relation avec les activités

Une activité peut être associée à plusieurs indicateurs, et un même indicateur peut être utilisé pour plusieurs activités.

Les combinaisons autorisées entre `activity_code` et `indicator_code` seront définies séparément afin de pouvoir vérifier la cohérence des observations.

## Relations et règles d'unicité

À définir avant la mise en place des traitements.

## Contrôles de qualité

À définir en fonction des champs, des indicateurs et des règles de reporting retenus.
