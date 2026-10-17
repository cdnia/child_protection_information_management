# Politique de validation des données

## Objet

Ce document décrit les contrôles actuellement implémentés dans le prototype `child_protection_information_management`.

Il complète `data_dictionary.md`, qui définit le modèle de données et les règles métier.

Le projet utilise exclusivement des données synthétiques et agrégées. Aucun résultat ne représente une activité humanitaire réelle.

## Lecture des fichiers CSV

Le lecteur `read_csv()` vérifie la structure des fichiers : en-têtes attendus et nombre de colonnes par enregistrement.

Les règles appliquées sont les suivantes :

- Un fichier sans en-tête valide est rejeté.
- Une ligne blanche ou composée uniquement d'espaces est rejetée lorsqu'elle ne respecte pas le nombre de colonnes attendu.
- Une cellule vide est conservée lors de la lecture si la structure de la ligne est correcte.
- Un fichier contenant uniquement son en-tête produit une liste vide.

La lecture correcte d'un fichier ne garantit pas sa validité métier.

## Fichiers sans données

Dans le scénario actuel, les fichiers transactionnels `reports.csv`, `submissions.csv` et `observations.csv` doivent contenir au moins un enregistrement.

Un fichier comportant uniquement son en-tête est rejeté par l'orchestrateur avec l'un des codes suivants :

- `EMPTY_REPORTS`
- `EMPTY_SUBMISSIONS`
- `EMPTY_OBSERVATIONS`

Les cinq référentiels doivent également être non vides.

Cette politique s'applique au lot de démonstration. Elle ne signifie pas qu'une absence de déclaration constitue systématiquement une erreur dans une situation opérationnelle.

## Valeurs manquantes et valeurs égales à zéro

Une cellule obligatoire vide est vérifiée par le validateur métier correspondant.

Les champs facultatifs peuvent rester vides lorsque les règles du modèle l'autorisent.

Une valeur `reported_value` égale à `0` est acceptée. Une valeur absente n'est jamais remplacée automatiquement par zéro.

Une absence de déclaration ne permet pas de conclure qu'aucune activité n'a été réalisée.

## États du processus de validation

L'orchestrateur utilise trois états :

- `PASS` : les contrôles implémentés pour cette étape ont été exécutés sans anomalie détectée.
- `FAIL` : au moins une anomalie bloquante a été détectée.
- `SKIPPED` : l'étape n'a pas été exécutée, notamment parce qu'une validation préalable a échoué.

Les contrôles suivent cet ordre :

1. Référentiels
2. Rapports
3. Soumissions
4. Chaînes de révision
5. Observations

Un contrôle dépendant n'est pas exécuté lorsque ses données préalables sont invalides.

## Limites actuelles

Un résultat `PASS` ne signifie pas que toutes les règles métier possibles ont été vérifiées.

Le prototype ne garantit pas encore :

- La réception des déclarations de tous les partenaires attendus.
- L'application complète des valeurs autorisées pour certains champs de référence.
- La vérification de toutes les contraintes temporelles entre tables.
- La production d'un rapport de qualité avec niveaux de gravité.
- La sélection et la consolidation des seules révisions approuvées.

Ces fonctionnalités nécessitent des développements et des tests supplémentaires.

La validation automatique ne constitue pas une décision d'approbation métier.

## Principe de traçabilité

Les anomalies sont signalées sans correction silencieuse des données sources.

Les tests utilisent des données synthétiques et, lorsque des modifications sont nécessaires, des fichiers temporaires.

Les limites connues doivent rester explicites jusqu'à leur résolution ou à l'adoption d'une politique métier documentée.
