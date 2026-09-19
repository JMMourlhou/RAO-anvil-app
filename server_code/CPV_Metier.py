"""Recherche et validation CPV pures, sans accès Anvil, réseau ou données utilisateur."""

import re
import unicodedata

from .CPV_Catalogue import LIBELLES_PAR_CODE


LIMITE_RESULTATS_MAXIMALE = 50
NOMBRE_CODES_MAXIMAL = 100
LONGUEUR_TERME_MAXIMALE = 200


class ErreurValidationCPV(ValueError):
    """Entrée utilisateur invalide pouvant être présentée dans l'interface."""


def normaliser_texte(texte):
    """Normalise une chaîne str pour comparaison ; retourne str sans accents.

    La casse et les espaces successifs sont neutralisés. Cette fonction interne
    attend un texte déjà validé ; elle ne modifie jamais les libellés retournés.
    """
    texte_decompose = unicodedata.normalize("NFD", texte.casefold())
    caracteres_conserves = []
    for caractere in texte_decompose:
        if not unicodedata.combining(caractere):
            caracteres_conserves.append(caractere)
    texte_sans_accents = "".join(caracteres_conserves)
    return " ".join(texte_sans_accents.split())


# Préparer les comparaisons une seule fois, sans altérer le texte officiel.
LIBELLES_NORMALISES = {}
for code_cpv, libelle_officiel in LIBELLES_PAR_CODE.items():
    LIBELLES_NORMALISES[code_cpv] = normaliser_texte(libelle_officiel)


def valider_entrees_recherche(terme, limite):
    """Valide terme (str, 200 caractères maximum) et limite (int, 1 à 50).

    Retourne le terme normalisé (str), éventuellement vide. Lève
    ErreurValidationCPV pour un mauvais type ou une borne invalide.
    Les booléens ne sont pas acceptés comme entiers.
    """
    if not isinstance(terme, str):
        raise ErreurValidationCPV("Le terme de recherche doit être une chaîne.")
    if len(terme) > LONGUEUR_TERME_MAXIMALE:
        raise ErreurValidationCPV("Le terme est limité à 200 caractères.")
    if type(limite) is not int:
        raise ErreurValidationCPV("La limite doit être un entier.")
    if not 1 <= limite <= LIMITE_RESULTATS_MAXIMALE:
        raise ErreurValidationCPV("La limite doit être comprise entre 1 et 50.")
    return normaliser_texte(terme)


def rechercher_dans_catalogue(terme, limite=10):
    """Recherche un libellé partiel ou un préfixe de code dans le catalogue.

    Paramètres : terme (str, au plus 200 caractères), limite (int, 1 à 50).
    Retour : list[str] des codes classés, limitée ; [] si terme vide ou absent.
    Erreurs : ErreurValidationCPV si type ou limites invalides.
    Aucun synonyme, rapprochement flou ou libellé inventé n'est utilisé.
    """
    terme_normalise = valider_entrees_recherche(terme, limite)
    if not terme_normalise:
        return []

    recherche_par_code = re.fullmatch(r"[0-9]+", terme_normalise) is not None
    correspondances = []
    for code_cpv, libelle_normalise in LIBELLES_NORMALISES.items():
        priorite = None
        if recherche_par_code:
            if code_cpv == terme_normalise:
                priorite = 0
            elif code_cpv.startswith(terme_normalise):
                priorite = 1
        else:
            if libelle_normalise == terme_normalise:
                priorite = 0
            elif libelle_normalise.startswith(terme_normalise):
                priorite = 1
            elif terme_normalise in libelle_normalise:
                priorite = 2

        if priorite is not None:
            correspondances.append((priorite, libelle_normalise, code_cpv))

    # Un tri explicite rend les égalités reproductibles entre deux appels.
    correspondances.sort()
    resultats_limites = correspondances[:limite]
    codes_resultats = []
    for priorite, libelle_normalise, code_cpv in resultats_limites:
        codes_resultats.append(code_cpv)
    return codes_resultats


def valider_codes_selectionnes(codes):
    """Valide une sélection de 1 à 100 codes officiels et retire les doublons.

    Paramètre : codes (list[str]), codes strictement composés de huit chiffres.
    Retour : nouvelle list[str], dans l'ordre de la première occurrence.
    Erreurs : ErreurValidationCPV si liste vide, trop longue, mauvais type,
    format invalide ou code inconnu. Aucun résultat partiel n'est retourné.
    """
    if not isinstance(codes, list):
        raise ErreurValidationCPV("La sélection doit être une liste de chaînes.")
    if not codes:
        raise ErreurValidationCPV("Sélectionnez au moins un code CPV.")
    if len(codes) > NOMBRE_CODES_MAXIMAL:
        raise ErreurValidationCPV("La sélection est limitée à 100 entrées.")

    codes_selectionnes = []
    codes_deja_vus = set()
    for code_cpv in codes:
        if not isinstance(code_cpv, str):
            raise ErreurValidationCPV("Chaque code CPV doit être une chaîne.")
        if re.fullmatch(r"[0-9]{8}", code_cpv) is None:
            raise ErreurValidationCPV("Chaque code CPV doit contenir huit chiffres.")
        if code_cpv not in LIBELLES_PAR_CODE:
            raise ErreurValidationCPV("Code CPV inconnu : " + code_cpv)
        if code_cpv not in codes_deja_vus:
            codes_selectionnes.append(code_cpv)
            codes_deja_vus.add(code_cpv)
    return codes_selectionnes


def convertir_resultats_anvil(codes):
    """Convertit des codes internes validés (list[str]) en list[dict].

    Chaque dictionnaire contient code (str) et libelle (str officiel).
    Un code absent provoque KeyError : il s'agit d'une erreur interne,
    non d'un résultat utilisateur à masquer.
    """
    resultats_cpv = []
    for code_cpv in codes:
        resultats_cpv.append({"code": code_cpv, "libelle": LIBELLES_PAR_CODE[code_cpv]})
    return resultats_cpv
