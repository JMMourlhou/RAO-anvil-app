# Score_pertinence.py
import anvil.server
import re

"""
Module de calcul du score de pertinence des offres.

Principe :
- l'utilisateur fournit un dictionnaire de mots_score :
    {
        "rénovation": 10,
        "agrandissement": 10,
        "restructuration": 5,
        "finition": 1
    }

- si un mot_score est trouvé dans le texte de l'offre, son poids est ajouté au score.
- par défaut, un mot_score ne compte qu'une seule fois par offre.
"""

# ---------------------------------------------------------------------
# Normalisation texte
# ---------------------------------------------------------------------

_ACCENTS = {
    "à": "a", "â": "a", "ä": "a",
    "á": "a", "ã": "a", "å": "a",

    "ç": "c",

    "é": "e", "è": "e", "ê": "e", "ë": "e",

    "î": "i", "ï": "i", "í": "i", "ì": "i",

    "ô": "o", "ö": "o", "ó": "o", "ò": "o", "õ": "o",

    "ù": "u", "û": "u", "ü": "u", "ú": "u",

    "ÿ": "y",
    "ñ": "n",

    "œ": "oe",
    "æ": "ae",
}

# appelé par le module search après le retour des offres 
@anvil.server.callable
def scorer_offres(offres, dict_mots_score=None):
    """
    Reçoit une liste d'offres préparées côté client,
    ajoute score / pertinence / mots_score_trouves,
    puis trie par score décroissant.
    """

    if dict_mots_score is None:
        dict_mots_score = {}

    return scorer_et_trier_offres(
        offres=offres,
        dict_mots_score=dict_mots_score,
        compter_occurrences=False,
        accepter_pluriel=True,
    )

    
def sans_accents(texte):
    """Remplace les accents courants sans dépendre de unicodedata."""
    if texte is None:
        return ""

    texte = str(texte).lower()

    for accent, simple in _ACCENTS.items():
        texte = texte.replace(accent, simple)

    return texte


def normaliser_texte(texte):
    """
    Normalise un texte pour permettre une recherche fiable :
    - minuscules
    - suppression/remplacement des accents
    - ponctuation remplacée par des espaces
    - espaces multiples supprimés

    Exemple :
    "Travaux de rénovation-extension" devient :
    "travaux de renovation extension"
    """
    if texte is None:
        return ""

    texte = sans_accents(texte)

    caracteres = []
    for c in texte:
        if c.isalnum():
            caracteres.append(c)
        else:
            caracteres.append(" ")

    texte = "".join(caracteres)
    texte = " ".join(texte.split())

    return texte


# ---------------------------------------------------------------------
# Récupération du texte de l'offre
# ---------------------------------------------------------------------

def get_valeur(item, cle, defaut=None):
    """
    Récupère une valeur dans un dictionnaire ou objet compatible.
    Utile si tes offres sont des dicts classiques.
    """
    try:
        return item.get(cle, defaut)
    except Exception:
        try:
            return item[cle]
        except Exception:
            return defaut


def texte_offre(offre, champs=None):
    """
    Construit le texte dans lequel chercher les mots_score.

    On privilégie search_text, mais on ajoute aussi quelques champs utiles
    si search_text est absent ou incomplet.
    """
    if champs is None:
        champs = (
            "search_text",
            "titre",
            "description",
            "acheteur",
            "nature",
            "procedure",
            "lieu",
            "departement",
        )

    morceaux = []

    for champ in champs:
        valeur = get_valeur(offre, champ, "")
        if valeur:
            morceaux.append(str(valeur))

    return "\n".join(morceaux)


# ---------------------------------------------------------------------
# Recherche des mots_score
# ---------------------------------------------------------------------

def variantes_mot_score(mot_normalise, accepter_pluriel=True):
    """
    Retourne les variantes simples d'un mot_score.

    Exemple :
    "renovation" cherchera aussi "renovations".

    Pour une expression comme "maitrise oeuvre", on ne génère pas de pluriel.
    """
    if not mot_normalise:
        return []

    variantes = [mot_normalise]

    if accepter_pluriel and " " not in mot_normalise:
        if len(mot_normalise) > 3 and not mot_normalise.endswith("s"):
            variantes.append(mot_normalise + "s")

    return variantes


def contient_expression(texte_normalise, expression_normalisee):
    """
    Vérifie qu'une expression est présente comme mot ou groupe de mots complet.

    Cela évite par exemple que "finition" soit trouvé dans "définition".
    """
    if not texte_normalise or not expression_normalisee:
        return False

    texte_prepare = " " + texte_normalise + " "
    expression_preparee = " " + expression_normalisee + " "

    return expression_preparee in texte_prepare


def compter_expression(texte_normalise, expression_normalisee):
    """
    Compte le nombre d'apparitions exactes d'une expression normalisée.
    Fonction disponible si tu veux un jour compter les occurrences.
    """
    if not texte_normalise or not expression_normalisee:
        return 0

    texte_prepare = " " + texte_normalise + " "
    expression_preparee = " " + expression_normalisee + " "

    return texte_prepare.count(expression_preparee)


# ---------------------------------------------------------------------
# Calcul du score
# ---------------------------------------------------------------------

def calculer_score_offre(
    offre,
    dict_mots_score,
    champs=None,
    compter_occurrences=False,
    max_occurrences_par_mot=3,
    accepter_pluriel=True,
):
    """
    Calcule le score d'une offre.

    Paramètres :
    - offre : dictionnaire de l'offre
    - dict_mots_score : {"rénovation": 10, "aménagement": 1, ...}
    - champs : champs de l'offre à analyser
    - compter_occurrences :
        False = un mot_score compte une seule fois par offre
        True  = chaque apparition compte, avec plafond
    - max_occurrences_par_mot :
        utilisé seulement si compter_occurrences=True
    - accepter_pluriel :
        "rénovation" trouve aussi "rénovations"

    Retour :
    {
        "score": 25,
        "mots_score_trouves": ["rénovation", "restructuration"],
        "details_score": {
            "rénovation": {
                "valeur": 10,
                "occurrences": 1,
                "points": 10
            }
        }
    }
    """

    if not dict_mots_score:
        return {
            "score": 0,
            "mots_score_trouves": [],
            "details_score": {},
        }

    texte = texte_offre(offre, champs=champs)
    texte_normalise = normaliser_texte(texte)

    score = 0
    mots_score_trouves = []
    details_score = {}

    for mot_score, valeur in dict_mots_score.items():

        mot_normalise = normaliser_texte(mot_score)

        try:
            poids = int(valeur)
        except Exception:
            poids = 0

        if not mot_normalise or poids == 0:
            continue

        variantes = variantes_mot_score(
            mot_normalise,
            accepter_pluriel=accepter_pluriel
        )

        nb_occurrences = 0

        for variante in variantes:
            if compter_occurrences:
                nb_occurrences += compter_expression(texte_normalise, variante)
            else:
                if contient_expression(texte_normalise, variante):
                    nb_occurrences = 1
                    break

        if nb_occurrences > 0:
            if compter_occurrences:
                nb_occurrences = min(nb_occurrences, max_occurrences_par_mot)
                points = nb_occurrences * poids
            else:
                points = poids

            score += points
            mots_score_trouves.append(mot_score)

            details_score[mot_score] = {
                "valeur": poids,
                "occurrences": nb_occurrences,
                "points": points,
            }

    return {
        "score": score,
        "mots_score_trouves": mots_score_trouves,
        "details_score": details_score,
    }


# ---------------------------------------------------------------------
# Libellé de pertinence
# ---------------------------------------------------------------------

def libelle_pertinence(score):
    """
    Convertit un score numérique en libellé simple.

    Tu pourras ajuster ces seuils après quelques tests réels.
    """
    try:
        score = int(score)
    except Exception:
        score = 0

    if score >= 30:
        return "Très pertinente"
    elif score >= 15:
        return "Pertinente"
    elif score >= 5:
        return "Peu pertinente"
    else:
        return ""


# ---------------------------------------------------------------------
# Enrichissement et tri des offres
# ---------------------------------------------------------------------

def ajouter_score_aux_offres(
    offres,
    dict_mots_score,
    champs=None,
    compter_occurrences=False,
    max_occurrences_par_mot=3,
    accepter_pluriel=True,
):
    """
    Ajoute directement dans chaque offre :
    - score
    - pertinence
    - mots_score_trouves
    - details_score

    Retourne la liste modifiée.
    """

    if offres is None:
        return []

    for offre in offres:
        resultat = calculer_score_offre(
            offre=offre,
            dict_mots_score=dict_mots_score,
            champs=champs,
            compter_occurrences=compter_occurrences,
            max_occurrences_par_mot=max_occurrences_par_mot,
            accepter_pluriel=accepter_pluriel,
        )

        offre["score"] = resultat["score"]
        offre["pertinence"] = libelle_pertinence(resultat["score"])
        offre["mots_score_trouves"] = resultat["mots_score_trouves"]
        offre["details_score"] = resultat["details_score"]

    return offres


def trier_offres_par_score(offres):
    """
    Trie les offres par score décroissant.
    En cas d'égalité, on garde les offres les plus récentes en premier
    si date_publication existe.
    """

    if offres is None:
        return []

    def cle_tri(offre):
        score = get_valeur(offre, "score", 0) or 0
        date_publication = get_valeur(offre, "date_publication", "") or ""

        return (
            int(score),
            str(date_publication),
        )

    return sorted(offres, key=cle_tri, reverse=True)


def scorer_et_trier_offres(
    offres,
    dict_mots_score,
    champs=None,
    compter_occurrences=False,
    max_occurrences_par_mot=3,
    accepter_pluriel=True,
):
    """
    Fonction principale à utiliser dans ton app.

    Elle :
    1. calcule les scores
    2. ajoute les détails dans chaque offre
    3. trie les offres par score décroissant
    """

    offres = ajouter_score_aux_offres(
        offres=offres,
        dict_mots_score=dict_mots_score,
        champs=champs,
        compter_occurrences=compter_occurrences,
        max_occurrences_par_mot=max_occurrences_par_mot,
        accepter_pluriel=accepter_pluriel,
    )

    return trier_offres_par_score(offres)