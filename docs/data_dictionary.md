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

#### Cohérence temporelle avec la période de reporting

Chaque soumission doit être associée à un rapport dont la période de reporting est valide.

Dans le scénario actuel, `reporting_period` désigne un mois calendaire et `submitted_at` représente la date et l'heure de réception en UTC.

Une soumission ne doit pas être reçue avant le premier instant du mois auquel son rapport se rapporte.

Par exemple, pour `reporting_period = 2025-03`, la première date de réception autorisée est `2025-03-01T00:00:00Z`.

Une soumission reçue pendant le mois de reporting reste autorisée par ce contrôle. Celui-ci ne garantit pas que le rapport soit complet ou définitif.

Les soumissions reçues après la fin du mois restent autorisées, y compris lorsqu'il s'agit de corrections tardives.

Aucune date limite de transmission n'est imposée dans cette version du prototype.

Les révisions doivent toujours respecter leur ordre chronologique, indépendamment de cette règle.

Ce contrôle croisé entre `reports` et `submissions` est exécuté par l'orchestrateur après validation des rapports et des champs de base des soumissions, avant la vérification des chaînes de révision.

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

#### Valeurs autorisées du type de zone

Dans la version actuelle du prototype, `area_type` accepte uniquement la valeur `SIMULATED_ZONE`.

Cette restriction concerne exclusivement le jeu de données fictif. Elle empêche d'introduire silencieusement des catégories géographiques non définies.

L'utilisation de zones administratives réelles nécessitera une extension documentée des valeurs autorisées, accompagnée de nouveaux tests.

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

#### Correspondance entre indicateurs et unités de mesure

Dans la version actuelle du prototype, les unités des deux indicateurs définis sont fixées comme suit :

- `IND_SESSIONS_HELD` utilise exclusivement l'unité `SESSION`.
- `IND_PARTICIPATIONS` utilise exclusivement l'unité `PARTICIPATION`.

La validation des référentiels vérifie cette correspondance afin d'éviter qu'un indicateur soit associé à une unité incompatible avec sa définition.

Les unités sont conservées dans `indicators.csv` et ne sont pas répétées dans `observations.csv`.

Pour tout nouvel indicateur, sa définition et son unité devront être documentées. Les contrôles de cohérence devront être étendus lorsque de nouveaux indicateurs seront ajoutés.

#### Méthodes d'agrégation autorisées

Dans la version actuelle du prototype, `aggregation_method` accepte uniquement la valeur `SUM`.

Les deux indicateurs définis représentent des dénombrements additifs, sous réserve du respect des règles de consolidation.

La méthode `SUM` ne doit pas entraîner l'addition de plusieurs révisions du même rapport. Seules les observations issues des soumissions approuvées retenues peuvent être consolidées.

Toute nouvelle méthode d'agrégation devra être définie, documentée et testée avant son utilisation.

#### Agrégation et interprétation des résultats

Les deux indicateurs utilisent la méthode `SUM`, mais leur addition doit respecter certaines conditions.

Avant de calculer un total, il faut notamment vérifier que les observations proviennent des soumissions approuvées, qu'elles ne sont pas des doublons et que les résultats regroupés sont compatibles.

Un total de participations ne doit pas être présenté comme un nombre de bénéficiaires uniques.

Les règles d'agrégation pourront être complétées lorsque nous définirons les traitements et les contrôles de qualité du système.

#### Relation avec les activités

Une activité peut être associée à plusieurs indicateurs, et un même indicateur peut être utilisé pour plusieurs activités.

Les combinaisons autorisées entre `activity_code` et `indicator_code` seront définies séparément afin de pouvoir vérifier la cohérence des observations.

## Relations et règles d'unicité

Les tables sont reliées entre elles à l'aide d'identifiants communs. Ces relations permettent de retrouver l'origine des données et de vérifier leur cohérence.

Une clé primaire (_primary key_) identifie de manière unique un enregistrement dans une table. Une clé étrangère (_foreign key_) fait référence à un enregistrement d'une autre table.

### Relations entre les tables

| Table          | Champ            | Table de référence | Champ référencé  |
| -------------- | ---------------- | ------------------ | ---------------- |
| `reports`      | `partner_id`     | `partners`         | `partner_id`     |
| `submissions`  | `report_id`      | `reports`          | `report_id`      |
| `observations` | `submission_id`  | `submissions`      | `submission_id`  |
| `observations` | `area_code`      | `areas`            | `area_code`      |
| `observations` | `activity_code`  | `activities`       | `activity_code`  |
| `observations` | `indicator_code` | `indicators`       | `indicator_code` |

Un partenaire peut être associé à plusieurs rapports. Un rapport peut recevoir plusieurs soumissions, et chaque soumission peut contenir plusieurs observations.

Une observation appartient toutefois à une seule soumission.

Le champ `previous_submission_id` de `submissions` fait également référence à `submissions.submission_id`. Lorsqu'il est renseigné, il doit désigner la transmission précédente du même rapport.

### `activity_indicators` — Associations entre activités et indicateurs

La table `activity_indicators` définit les indicateurs autorisés pour chaque catégorie d'activité.

Elle permet de représenter une relation plusieurs-à-plusieurs : une activité peut utiliser plusieurs indicateurs, et un indicateur peut être utilisé pour plusieurs activités.

| Champ            | Type  | Obligatoire | Description                                        |
| ---------------- | ----- | ----------- | -------------------------------------------------- |
| `activity_code`  | Texte | Oui         | Code de l'activité concernée.                      |
| `indicator_code` | Texte | Oui         | Code de l'indicateur autorisé pour cette activité. |

#### Exemple de données

| activity_code             | indicator_code       |
| ------------------------- | -------------------- |
| `ACT_COMMUNITY_AWARENESS` | `IND_SESSIONS_HELD`  |
| `ACT_COMMUNITY_AWARENESS` | `IND_PARTICIPATIONS` |
| `ACT_GROUP_PSYCHOSOCIAL`  | `IND_SESSIONS_HELD`  |
| `ACT_GROUP_PSYCHOSOCIAL`  | `IND_PARTICIPATIONS` |

#### Règles de validation

- Le champ `activity_code` doit correspondre à une activité existante.
- Le champ `indicator_code` doit correspondre à un indicateur existant.
- Une même association entre activité et indicateur ne peut apparaître qu'une seule fois.
- Chaque observation doit utiliser une combinaison d'activité et d'indicateur présente dans cette table.

Le couple `activity_code` et `indicator_code` constitue la clé primaire composée (_composite primary key_) de cette table.

### Contraintes d'unicité

En plus des identifiants uniques définis pour chaque table, certaines combinaisons de champs ne doivent pas être répétées.

| Table                 | Combinaison unique                                                 |
| --------------------- | ------------------------------------------------------------------ |
| `reports`             | `partner_id` + `reporting_period`                                  |
| `submissions`         | `report_id` + `revision_no`                                        |
| `observations`        | `submission_id` + `area_code` + `activity_code` + `indicator_code` |
| `activity_indicators` | `activity_code` + `indicator_code`                                 |

Ces contraintes répondent à des besoins différents.

Dans `reports`, elles empêchent de créer deux rapports logiques pour le même partenaire et le même mois.

Dans `submissions`, elles empêchent d'attribuer le même numéro de révision à deux transmissions d'un même rapport.

Dans `observations`, elles empêchent de déclarer plusieurs valeurs pour un même indicateur, une même activité et une même zone au sein d'une soumission.

Enfin, dans `activity_indicators`, elles évitent d'enregistrer plusieurs fois la même association.

Les différentes révisions d'un rapport restent conservées. Lors de la consolidation, les observations doivent provenir de la transmission approuvée applicable à chaque rapport, afin d'éviter le double comptage.

## Contrôles de qualité

Les contrôles de qualité servent à repérer les erreurs et les incohérences dans les rapports transmis par les partenaires.

Ils interviennent avant la consolidation des résultats. Leur objectif est de signaler les problèmes rencontrés, de faciliter leur vérification et d'éviter que des données invalides soient utilisées dans les analyses.

Les données reçues seront conservées afin de pouvoir retrouver les informations d'origine et comprendre les corrections apportées.

### Niveaux de contrôle

Les anomalies seront classées selon trois niveaux :

| Niveau    | Signification                                          | Traitement                               |
| --------- | ------------------------------------------------------ | ---------------------------------------- |
| `ERROR`   | Erreur empêchant la validation des données concernées. | Correction nécessaire avant approbation. |
| `WARNING` | Situation inhabituelle ou potentiellement incohérente. | Vérification et décision documentée.     |
| `INFO`    | Information utile au suivi des traitements.            | Aucune correction nécessaire par défaut. |

Une alerte ne signifie pas systématiquement que la valeur déclarée est fausse. Certaines situations nécessitent une vérification auprès du partenaire.

### Vérification de la structure

Le système devra vérifier que les données respectent la structure définie dans le dictionnaire.

Les contrôles porteront notamment sur :

- La présence des champs obligatoires.
- Le respect des types de données attendus.
- La validité des dates et des périodes de reporting.
- La présence et l'unicité des identifiants.
- La cohérence des références entre les tables.

Une valeur manquante ne sera jamais remplacée automatiquement par zéro. Lorsqu'un champ obligatoire est absent, l'anomalie devra être signalée avant toute utilisation de l'enregistrement concerné.

### Vérification des valeurs

Les contrôles métier permettront notamment de détecter :

- Les valeurs négatives pour les indicateurs de dénombrement.
- Les nombres décimaux lorsque l'indicateur exige un entier.
- Les codes de partenaires, de zones, d'activités ou d'indicateurs inconnus.
- Les associations non autorisées entre activités et indicateurs.
- Les observations répétées pour une même combinaison de soumission, zone, activité et indicateur.

Les valeurs égales à zéro resteront autorisées lorsqu'elles correspondent à des résultats réellement déclarés.

Une valeur particulièrement élevée pourra déclencher un avertissement, sans être considérée automatiquement comme une erreur.

### Détection des doublons

Les doublons seront recherchés à plusieurs niveaux.

**Dans les observations :** deux lignes d'une même soumission ne doivent pas déclarer séparément une valeur pour la même combinaison de zone, d'activité et d'indicateur.

**Dans les soumissions :** deux transmissions ne doivent pas partager le même identifiant ni le même numéro de révision pour un rapport donné.

**Dans les rapports :** un partenaire ne doit pas posséder plusieurs rapports logiques pour la même période mensuelle.

Les doublons détectés seront signalés. Le système ne supprimera pas silencieusement les enregistrements concernés.

### Vérification des corrections

Lorsqu'un partenaire transmet une correction, le système devra vérifier que :

- Le rapport concerné existe.
- Le numéro de révision est valide et unique pour ce rapport.
- La transmission précédente existe et appartient au même rapport.
- La chaîne des révisions est cohérente.
- Les nouvelles valeurs sont soumises aux mêmes contrôles que celles du rapport initial.

La réception d'une correction ne signifie pas qu'elle est automatiquement approuvée.

### Validation des soumissions

Les contrôles automatiques et l'approbation d'une soumission sont deux étapes distinctes.

Une soumission présentant des erreurs bloquantes ne pourra pas être approuvée tant que ces erreurs ne sont pas résolues.

Les avertissements devront être examinés. La décision de les accepter ou de demander une correction devra pouvoir être justifiée.

Une soumission techniquement valide ne sera pas considérée comme approuvée sans décision de validation.

### Sélection des données à consolider

Les résultats consolidés seront calculés uniquement à partir des soumissions approuvées.

Lorsqu'un rapport possède plusieurs révisions approuvées, la révision approuvée portant le numéro le plus élevé sera retenue.

Les observations des anciennes révisions resteront conservées, mais elles ne seront pas additionnées à celles de la révision retenue.

Si une correction est encore en attente d'approbation, la dernière révision approuvée pourra rester utilisée, avec un signalement indiquant qu'une correction est en cours d'examen.

### Consolidation actuellement implémentée

La fonction `consolidate_observations()` regroupe en mémoire les observations issues des dernières soumissions approuvées retenues pour chaque rapport.

La sélection est effectuée par `select_latest_approved_submissions()`. Les anciennes révisions approuvées et les soumissions non approuvées ne contribuent pas aux totaux.

Les observations retenues sont regroupées selon quatre dimensions :

- `reporting_period` : période mensuelle du rapport.
- `area_code` : zone géographique.
- `activity_code` : activité déclarée.
- `indicator_code` : indicateur mesuré.

Les valeurs sont additionnées uniquement lorsque ces quatre dimensions sont identiques. Les indicateurs du prototype utilisent la méthode d'agrégation `SUM`.

Une valeur explicitement déclarée égale à `0` est conservée dans les résultats. Un rapport sans soumission approuvée est exclu. Si aucune soumission n'est approuvée, la fonction retourne une liste vide, ce qui ne doit pas être interprété comme un total égal à zéro.

Sur le jeu de données synthétiques de mars 2025, les tests attendent 12 lignes de résultats consolidés, totalisant 28 séances et 652 participations. Ces chiffres ne représentent pas des activités humanitaires réelles.

Les participations ne constituent pas un dénombrement de bénéficiaires uniques.

La consolidation évite de compter plusieurs révisions d'un même rapport, mais elle ne détecte pas automatiquement les activités réelles éventuellement déclarées par plusieurs partenaires.

La fonction `consolidate_observations()` suppose que les données reçues ont déjà été validées. Elle reste indépendante et n'exécute pas elle-même les contrôles de qualité.

Le parcours `run_consolidation(project_root)` appelle d'abord `run_validation()`. Si une étape échoue ou si toutes les étapes ne sont pas validées, la consolidation est refusée avec une exception `ValueError`.

Lorsque les cinq étapes ont le statut `PASS`, le parcours relit `reports.csv`, `submissions.csv` et `observations.csv`, puis appelle `consolidate_observations()`.

Cette intégration garantit l'ordre des opérations dans le parcours actuel, mais pas leur atomicité. Les fichiers pourraient être modifiés entre leur validation et leur seconde lecture. Une utilisation concurrente nécessiterait un instantané cohérent des données ou un autre mécanisme garantissant leur stabilité.

Les données sources ne sont pas modifiées par le calcul. Les résultats consolidés sont actuellement retournés en mémoire, sans export automatique.

### Vérification des agrégations

Avant de produire un total, le système devra vérifier que les observations sélectionnées :

- Proviennent des soumissions approuvées et applicables.
- Utilisent des indicateurs compatibles avec les activités concernées.
- Respectent les unités de mesure définies.
- Ne correspondent pas à des résultats comptés plusieurs fois.
- Peuvent être regroupées selon les règles d'agrégation des indicateurs.

Les participations enregistrées ne seront pas présentées comme un nombre de bénéficiaires uniques.

### Rapport de contrôle

Les contrôles produiront un rapport permettant de retrouver les anomalies détectées.

Pour chaque anomalie, nous chercherons à conserver au minimum :

- Son niveau de gravité.
- Le contrôle qui l'a détectée.
- L'identifiant de l'enregistrement concerné.
- Une description compréhensible du problème.
- Le résultat de son examen ou de sa correction, lorsqu'il est disponible.

Ce rapport aidera à vérifier les données avant leur consolidation et à expliquer les décisions prises pendant leur traitement.
