# AGENTS.md — Instructions Codex pour RAO-Anvil

## 1. Règle générale : ne rien modifier sans accord explicite

Par défaut, analyser uniquement.

Ne jamais modifier, créer, supprimer, renommer ou déplacer un fichier, un Form, un Module, un Server Module, un Asset ou un composant Anvil sans accord explicite de l'utilisateur.

Avant toute modification :
- expliquer précisément ce qui sera modifié ;
- indiquer les fichiers ou composants concernés ;
- indiquer le risque éventuel ;
- attendre un accord explicite.

Si la demande porte uniquement sur une analyse, un diagnostic, une vérification ou un rapport :
- ne modifier aucun fichier ;
- ne faire aucun commit ;
- ne créer aucune branche ;
- ne changer aucune configuration.

Ne pas effectuer de correction automatique globale sans validation préalable.

---

## 2. Priorité à la lisibilité humaine du code

Le code doit rester facile à lire, maintenir et comprendre par un humain.

Privilégier :
- des noms explicites ;
- des blocs simples ;
- des fonctions courtes quand cela améliore la compréhension ;
- des appels de fonctions sur une seule ligne quand ils restent lisibles ;
- des commentaires utiles avant les blocs importants ;
- des commentaires expliquant le pourquoi, pas seulement le quoi.

Éviter :
- les expressions trop compactes ;
- les compréhensions complexes ;
- les chaînes d'appels difficiles à lire ;
- les abstractions inutiles ;
- les refactorings massifs sans bénéfice clair ;
- les noms trop courts ou ambigus.

Exemple à privilégier :

```python
afficher_temps("TOTAL __init__", t_total)
```

plutôt qu'une mise en forme inutilement éclatée sur plusieurs lignes.

---

## 3. Commentaires et structure des scripts

Lors de la création ou modification d'un script :
- conserver les commentaires existants utiles ;
- ajouter des commentaires avant les blocs importants ;
- documenter les fonctions non triviales ;
- expliquer les traitements spécifiques à Anvil, aux Uplinks, aux Background Tasks et aux composants personnalisés ;
- éviter les commentaires évidents ou redondants.

Pour les fonctions importantes, utiliser des docstrings simples précisant :
- le rôle ;
- les paramètres ;
- le retour ;
- les effets de bord éventuels ;
- les erreurs attendues.

---

## 4. Modifications minimales

Toujours rechercher la modification la plus petite et la plus sûre.

Ne pas :
- réécrire une fonction entière si une correction de quelques lignes suffit ;
- renommer massivement les composants ;
- modifier plusieurs parcours fonctionnels en même temps ;
- toucher à du code fonctionnel sans nécessité.

Lorsqu'un bug est identifié :
1. localiser la cause exacte ;
2. proposer la correction minimale ;
3. vérifier les impacts ;
4. attendre l'accord avant modification.

---

## 5. Validation Anvil : faux positifs connus

Le validateur statique Anvil peut générer des diagnostics qui ne correspondent pas à des erreurs réelles d'exécution.

Ne pas compter comme erreur applicative les diagnostics portant uniquement sur des propriétés standard Anvil comme :

- `enabled`
- `visible`
- `text`
- `checked`
- `align`
- `background`
- `foreground`
- `bold`
- `role`
- `items`
- `selected`
- `spacing_above`
- `spacing_below`

si le composant existe réellement dans le template et que l'utilisation est normale dans Anvil.

Exemples de diagnostics à classer comme faux positifs probables :

```text
Cannot assign to attribute "enabled" for class "Button"
Cannot assign to attribute "enabled" for class "TextBox"
Cannot assign to attribute "text" for class "Text"
Cannot assign to attribute "checked" for class "Checkbox"
```

Ces diagnostics doivent être regroupés dans une section :

`Faux positifs connus du validateur Anvil`

Ils ne doivent pas être inclus dans le nombre principal d'erreurs réelles.

---

## 6. RepeatingPanel et get_components()

`RepeatingPanel.get_components()` peut être typé statiquement comme retournant des `Component` génériques.

Ne pas considérer automatiquement comme erreur :

- `row.checkbox_vu`
- `ligne.item`
- `ligne.actualiser_etat_bouton()`
- ou d'autres propriétés/méthodes spécifiques au RowTemplate

si le RowTemplate réellement utilisé définit bien ces attributs ou méthodes.

Classer ces diagnostics comme :

`Faux positif de typage dû au Component générique retourné par get_components()`

Ne pas les inclure dans les erreurs réelles.

---

## 7. JavaScript, DOM et composants personnalisés

Les accès suivants sont dynamiques et peuvent être mal compris par l'analyse statique :

- `popover.dom_popover`
- `popover.dom_popover.style`
- `composant._dd`
- `composant._dd._dom_node`
- `node.style`
- `node.style.setProperty(...)`

Ne pas les considérer comme erreurs uniquement parce que le validateur statique ne connaît pas ces attributs.

Les classer sous :

`API JavaScript / Anvil dynamique non vérifiable statiquement`

En revanche :
- signaler qu'un accès repose sur une API interne ou privée s'il peut être fragile ;
- ne pas masquer une vraie erreur JavaScript ou Anvil si elle est objectivement identifiable.

---

## 8. Uplinks externes

Certains callables sont fournis par des Uplinks Python externes exécutés sur le Raspberry Pi et ne sont pas forcément présents dans les Server Modules Anvil.

Exemples connus :

- `lancer_recherche_multi_sources_background`
- `lancer_recherche_cpv_background`

Un diagnostic :

```text
Unknown server callable
```

pour ces fonctions doit être classé comme :

`Callable Uplink externe non vérifiable localement`

et non comme erreur applicative, si le nom correspond bien à l'Uplink attendu.

---

## 9. Ce qui doit rester une vraie erreur

Continuer à signaler normalement :

- composant réellement absent du template ;
- faute de frappe dans un nom de composant ;
- variable non définie ;
- méthode réellement inexistante ;
- argument manquant ou incorrect ;
- mauvais nom de callable ;
- `AttributeError` crédible à l'exécution ;
- `KeyError` possible ;
- erreur avant un `try` censé protéger le code ;
- incohérence entre état UI et état métier ;
- erreur dans une Background Task ;
- interface qui peut rester verrouillée ;
- tâche qui peut rester active ou mal nettoyée ;
- incohérence entre critères utilisés pour une recherche et critères sauvegardés ;
- erreur de logique pouvant empêcher un bouton ou une recherche de fonctionner ;
- mauvais type pouvant réellement parvenir au runtime ;
- perte de données ou comportement incohérent.

Ne jamais classer automatiquement une erreur réelle comme faux positif sous prétexte qu'Anvil est dynamique.

---

## 10. Robustesse des chaînes de caractères

Quand une valeur provenant d'un composant Anvil peut être typée de façon ambiguë, privilégier une conversion défensive simple :

```python
texte = str(self.mon_text_box.text or "").strip()
```

avant d'utiliser :

```python
.strip()
.split(...)
.lower()
```

Ne pas ajouter ces conversions partout sans raison.

Les utiliser lorsque cela améliore réellement la robustesse ou supprime une ambiguïté de type crédible.

---

## 11. Gestion des exceptions

Éviter les `except Exception:` trop larges lorsqu'ils masquent une erreur importante.

Quand un `except Exception:` existe :
- vérifier qu'il est justifié ;
- ne pas masquer silencieusement un bug critique ;
- conserver un `print()` ou un message utile pour le diagnostic lorsque pertinent.

Ne pas transformer une erreur technique importante en simple message utilisateur sans conserver un moyen de diagnostic.

---

## 12. Background Tasks

Pour toute modification concernant une Background Task :
- vérifier le lancement ;
- vérifier le timer client ;
- vérifier la lecture de l'état ;
- vérifier la récupération du résultat ;
- vérifier les erreurs ;
- vérifier l'arrêt du timer ;
- vérifier le déverrouillage de l'interface ;
- vérifier l'annulation éventuelle ;
- vérifier que `task_recherche` est correctement réinitialisée.

Ne pas modifier ce flux sans analyse préalable complète.

---

## 13. Cohérence des critères de recherche

Quand une recherche est lancée :
- privilégier un instantané des critères ;
- éviter de relire des champs UI modifiables pendant le traitement si les critères doivent rester figés ;
- vérifier que les critères sauvegardés dans l'historique correspondent réellement aux critères utilisés pour la recherche.

Signaler toute incohérence possible entre :
- critères saisis ;
- critères envoyés au serveur/Uplink ;
- critères utilisés pour le filtrage ;
- critères affichés ;
- critères sauvegardés.

---

## 14. Rapport d'analyse attendu

Lors d'une analyse de code ou d'une validation, produire quatre sections distinctes.

### A. Erreurs réelles ou potentiellement bloquantes

Uniquement les problèmes susceptibles de produire :
- une exception ;
- un mauvais fonctionnement ;
- un blocage ;
- une perte ou incohérence de données.

Pour chaque point :
- ligne ;
- code concerné ;
- cause ;
- gravité ;
- impact ;
- correction proposée.

### B. Problèmes de robustesse non bloquants

Exemples :
- API interne ;
- code fragile ;
- dépendance à un comportement Anvil implicite ;
- incohérence possible mais non bloquante.

### C. Faux positifs du validateur Anvil

Regrouper les diagnostics similaires.

Exemple :

```text
Button.enabled : 10 occurrences
Text.text : 5 occurrences
Component générique : 4 occurrences
DOM dynamique : 8 occurrences
```

Ne pas détailler inutilement chaque occurrence si elles ont la même cause.

### D. Avertissements externes

Exemples :
- callables Uplink non vérifiables ;
- dépendances externes ;
- éléments nécessitant un test navigateur ou serveur.

---

## 15. Compteurs de rapport

En tête du rapport, utiliser ce format :

```text
Erreurs réelles/potentielles : X
Robustesse : X
Faux positifs Anvil : X
Avertissements externes : X
```

Ne pas utiliser comme chiffre principal le nombre brut de diagnostics du validateur statique.

Par exemple, ne pas écrire :

```text
34 erreurs
```

si les 34 diagnostics sont principalement des faux positifs Anvil.

---

## 16. Avant toute modification proposée

Avant de modifier le code, fournir :

```text
Fichier / Form concerné :
Fonction concernée :
Problème :
Modification proposée :
Impact attendu :
Risque :
```

Puis attendre l'accord explicite de l'utilisateur.

---

## 17. Après une modification autorisée

Après modification :
- résumer exactement les changements ;
- indiquer les lignes ou fonctions modifiées ;
- ne pas annoncer qu'un bug est corrigé sans vérification ;
- préciser ce qui a été testé ;
- préciser ce qui n'a pas pu être testé ;
- indiquer si un test navigateur, serveur ou Uplink reste nécessaire.

---

## 18. Git

Ne jamais :
- commit ;
- push ;
- merge ;
- rebase ;
- créer ou supprimer une branche

sans demande explicite de l'utilisateur.

Avant un commit demandé :
- afficher les fichiers modifiés ;
- résumer les changements ;
- signaler toute modification inattendue.

---

## 19. Principe général

Priorité absolue :

1. comprendre le fonctionnement existant ;
2. distinguer vraie erreur et faux positif ;
3. proposer la correction minimale ;
4. préserver le comportement fonctionnel existant ;
5. conserver un code lisible par un humain ;
6. ne modifier qu'après accord explicite.
