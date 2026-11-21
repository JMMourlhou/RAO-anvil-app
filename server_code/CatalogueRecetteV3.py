"""Passerelles synchrones de recette ; aucun accès direct à PostgreSQL.

L'Uplink V4 contrôle de nouveau la session native et l'origine du relais.
"""
from datetime import date
import re
import time

import anvil.server
import anvil.users

from . import Maintenance_RAO


# Ouvrir uniquement après installation et activation de l’Uplink Pi5 en recette.
CATALOGUE_V4_ACTIVE = False

# Ne passer à True qu'après confirmation de la fin du rattrapage côté Pi5.
COUVERTURE_TED_COMPLETE = False


def _refuser(code, message):
    return {"ok": False, "error": code, "message": message}


def _verifier_acces_catalogue():
    """Contrôle la ligne Users native et le verrou avant tout relais."""
    utilisateur = anvil.users.get_user()
    if utilisateur is None:
        return _refuser("authentication_required", "Connexion Anvil requise.")
    try:
        habilite = bool(utilisateur.get_id()) and utilisateur["enabled"] is True
    except (KeyError, TypeError):
        habilite = False
    if not habilite:
        return _refuser("access_denied", "Ce compte n'est pas autorisé à utiliser le catalogue.")
    if CATALOGUE_V4_ACTIVE is not True:
        return _refuser("catalogue_unavailable", "Catalogue V4 désactivé. Le moteur historique est disponible.")
    return None

def _entier_borne(valeur, minimum, maximum):
    return type(valeur) is int and minimum <= valeur <= maximum


def _liste_textes(valeur, optionnelle=False):
    if optionnelle and valeur is None:
        return True
    return isinstance(valeur, list) and all(isinstance(element, str) for element in valeur)


@anvil.server.callable(require_user=True)
def recette_catalogue_v3_rechercher(
    cpv_selectionnes, departements, filtre_jours, sources,
    mots_obligatoires=None, mots_exclus=None, mots_ou=None,
    limite=50, decalage=0, empreinte=None, date_reference=None
):
    """Valide les paramètres du contrat puis appelle la V4 dans la session native.

    Retour Uplink complété par _mesures_recette_v3 pour le chronométrage Anvil.
    Les erreurs fonctionnelles locales sont explicites.
    Les exceptions Uplink se propagent : une panne n'est jamais une liste vide.
    """
    refus = _verifier_acces_catalogue()
    if refus is not None:
        return refus

    if (not isinstance(cpv_selectionnes, list) or not 1 <= len(cpv_selectionnes) <= 100
            or not all(isinstance(code, str) and re.fullmatch(r"[0-9]{8}", code) for code in cpv_selectionnes)):
        return _refuser("invalid_parameters", "Fournir de 1 à 100 codes CPV de huit chiffres.")
    if not _liste_textes(departements):
        return _refuser("invalid_parameters", "Les départements doivent être une liste de chaînes, éventuellement vide.")
    if not _entier_borne(filtre_jours, 1, 365):
        return _refuser("invalid_parameters", "La période doit être un entier de 1 à 365 jours.")
    if (not isinstance(sources, list) or not 1 <= len(sources) <= 2
            or not all(isinstance(source, str) and source in ("BOAMP", "TED") for source in sources)):
        return _refuser("invalid_parameters", "Les sources doivent être BOAMP et/ou TED.")
    # Le plafond V4 de candidats est contrôlé par le Pi, indépendamment du décalage.
    if not _entier_borne(limite, 1, 100) or type(decalage) is not int or decalage < 0:
        return _refuser("invalid_parameters", "Limite attendue de 1 à 100 et décalage entier positif ou nul.")
    if not all(_liste_textes(valeur, optionnelle=True) for valeur in (mots_obligatoires, mots_exclus, mots_ou)):
        return _refuser("invalid_parameters", "Les mots de filtrage doivent être des listes de chaînes ou None.")
    if empreinte is not None and not isinstance(empreinte, str):
        return _refuser("invalid_parameters", "L'empreinte doit être une chaîne ou None.")
    if date_reference is not None:
        if not isinstance(date_reference, str):
            return _refuser("invalid_parameters", "La date de référence doit être au format AAAA-MM-JJ.")
        try:
            date_validee = date.fromisoformat(date_reference)
        except ValueError:
            return _refuser("invalid_parameters", "Date de référence invalide.")
        if date_validee.isoformat() != date_reference:
            return _refuser("invalid_parameters", "La date de référence doit être au format AAAA-MM-JJ.")
    if decalage > 0 and (not empreinte or date_reference is None):
        return _refuser("invalid_parameters", "Une page suivante exige l'empreinte et la date de référence retournées.")

    # Aucun e-mail, user_id, rôle SQL ou contexte n'est transmis comme argument.
    debut_uplink = time.perf_counter()
    retour_recu = False
    duree_pg = None
    try:
        resultat = anvil.server.call(
            "rechercher_offres_catalogue_pg",
            cpv_selectionnes, departements, filtre_jours, sources,
            mots_obligatoires=mots_obligatoires, mots_exclus=mots_exclus, mots_ou=mots_ou,
            limite=limite, decalage=decalage, empreinte=empreinte, date_reference=date_reference
        )
        fin_uplink = time.perf_counter()
        retour_recu = True
        if isinstance(resultat, dict):
            valeur = resultat.get("duree_ms")
            if type(valeur) in (int, float) and 0 <= valeur < float("inf"):
                duree_pg = valeur
    finally:
        fin_mesure = fin_uplink if retour_recu else time.perf_counter()
        duree_uplink_ms = (fin_mesure - debut_uplink) * 1000
        # Ne journaliser ni critères, ni identité, ni annonces, ni erreur brute.
        print("[RECETTE V3 SERVEUR]", {
            "uplink_ms": duree_uplink_ms,
            "postgresql_duree_ms": duree_pg,
            "appel_termine": retour_recu,
        })
    if isinstance(resultat, dict):
        resultat = dict(resultat)
        resultat["_mesures_recette_v3"] = {"uplink_ms": duree_uplink_ms}
    return resultat


@anvil.server.callable(require_user=True)
def recette_catalogue_v3_detail(offre_ids):
    """Obtient le détail de 1 à 10 identifiants décimaux, après nouvelle autorisation."""
    refus = _verifier_acces_catalogue()
    if refus is not None:
        return refus
    if (not isinstance(offre_ids, list) or not 1 <= len(offre_ids) <= 10
            or not all(isinstance(identifiant, str) and re.fullmatch(r"[0-9]+", identifiant) for identifiant in offre_ids)):
        return _refuser("invalid_parameters", "Fournir de 1 à 10 identifiants décimaux sous forme de chaînes.")
    return anvil.server.call("obtenir_detail_offre_catalogue_pg", offre_ids)


@anvil.server.callable(require_user=True)
def rechercher_page_catalogue_search(
    cpv_selectionnes, departements, filtre_jours, sources,
    mots_obligatoires=None, mots_exclus=None, mots_ou=None,
    limite=100, decalage=0, empreinte=None, date_reference=None
):
    """Page pour search : même session native et même autorisation que la recette.

    Pas de Task Anvil : remote_caller reste server_module pour la V4.
    Le contrôle de maintenance est renouvelé à chaque nouvelle page.
    """
    refus = _verifier_acces_catalogue()
    if refus is not None:
        return refus
    ticket, refus = Maintenance_RAO._admettre("recherche_catalogue")
    if refus is not None:
        return refus
    try:
        resultat = recette_catalogue_v3_rechercher(
            cpv_selectionnes, departements, filtre_jours, sources,
            mots_obligatoires, mots_exclus, mots_ou, limite, decalage,
            empreinte, date_reference
        )
        if not isinstance(resultat, dict) or type(resultat.get("ok")) is not bool:
            raise ValueError("Réponse catalogue PostgreSQL invalide.")
        if resultat["ok"]:
            if not isinstance(resultat.get("offres"), list):
                raise ValueError("Liste d'annonces PostgreSQL invalide.")
            resultat = dict(resultat)
            offres = []
            for offre in resultat["offres"]:
                if not isinstance(offre, dict):
                    raise ValueError("Annonce PostgreSQL invalide.")
                offre = dict(offre)
                offre["moteur_recherche"] = "catalogue_pg"
                offre["date_limite_rep"] = offre.get("date_limite_reponse") or offre.get("date_limite_rep") or ""
                offre["lien_source"] = offre.get("lien") or ""
                offre["idweb"] = str(offre.get("reference") or offre.get("offre_id") or "")
                offres.append(offre)
            resultat["offres"] = offres
            resultat["couverture_ted_complete"] = COUVERTURE_TED_COMPLETE
    except Exception:
        Maintenance_RAO._noter_issue(ticket, "inconnue")
        raise
    Maintenance_RAO._noter_issue(ticket, "terminee")
    return resultat
