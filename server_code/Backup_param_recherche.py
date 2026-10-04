import anvil.server
import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables

from . import CPV_API


def nettoyer_valeur_pour_histo(valeur):
    """
    Convertit récursivement une valeur en donnée sérialisable par Anvil.
    """

    if valeur is None:
        return ""

    if isinstance(valeur, (str, int, float, bool)):
        return valeur

    if isinstance(valeur, dict):
        return {
            str(cle): nettoyer_valeur_pour_histo(sous_valeur)
            for cle, sous_valeur in valeur.items()
        }

    if isinstance(valeur, (list, tuple, set)):
        return [
            nettoyer_valeur_pour_histo(element)
            for element in valeur
        ]

    return str(valeur)


def nettoyer_offres_pour_histo(offres):
    """
    Garantit une liste de dictionnaires sérialisables contenant la clé ``vu``.
    """

    offres_nettoyees = []

    for offre in offres or []:
        try:
            offre_dict = dict(offre)
        except Exception:
            continue

        offre_propre = nettoyer_valeur_pour_histo(offre_dict)
        offre_propre["vu"] = bool(offre_propre.get("vu", False))
        offres_nettoyees.append(offre_propre)

    return offres_nettoyees


def nettoyer_sources(sources):
    """Retourne une liste propre d’identifiants de plateformes."""

    if sources is None:
        return []

    if not isinstance(sources, (list, tuple, set)):
        sources = [sources]

    resultat = []

    for source in sources:
        source = str(source or "").strip()
        if source and source not in resultat:
            resultat.append(source)

    return resultat


@anvil.server.callable(require_user=True)
@tables.in_transaction
def backup_requete(
    sources,
    mots_cles,
    mots_ou,
    mots_exclus,
    nb_jours,
    departements,
    date_heure,
    offres,
    mode_recherche,
    cpv_selectionnes
):
    """Enregistre la dernière recherche et incrémente sa révision.

    Reçoit les critères figés, les offres et les codes CPV.
    Retourne l'identifiant stable, la révision et le nombre d'offres.
    Une erreur technique annule la transaction.
    """

    def refuser(message):
        return {
            "ok": False,
            "message": message,
            "histo_id": None,
            "revision_recherche": None
        }

    user = anvil.users.get_user()
    if not user or not user["email"]:
        return refuser("Utilisateur non connecté.")

    if mode_recherche not in ("classique", "cpv"):
        return refuser("Mode de recherche invalide.")

    try:
        periode = int(nb_jours)
    except (ValueError, TypeError, OverflowError):
        return refuser("Le nombre de jours doit être un entier.")

    if periode < 1:
        return refuser("Le nombre de jours doit être supérieur à zéro.")

    if date_heure is None:
        return refuser("La date de recherche est manquante.")

    # Une recherche classique efface la sélection CPV précédente.
    codes_cpv = []
    if mode_recherche == "cpv":
        validation = CPV_API.valider_selection_cpv(cpv_selectionnes)
        if not validation["ok"]:
            return refuser(validation["message"])
        codes_cpv = validation["codes"]

    sources_nettoyees = nettoyer_sources(sources)
    offres_nettoyees = nettoyer_offres_pour_histo(offres)

    # Recherche et création conditionnelle dans une transaction standard.
    row = app_tables.histo.get(email=user["email"])
    nouvelle_revision = 1
    if row is not None:
        nouvelle_revision = row["revision_recherche"] + 1

    valeurs = {
        "email": user["email"],
        "date_heure": date_heure,
        "sources": sources_nettoyees,
        "mots_cles": str(mots_cles or ""),
        "mots_ou": str(mots_ou or ""),
        "mots_exclus": str(mots_exclus or ""),
        "nb_jours": periode,
        "departements": str(departements or ""),
        "offres": offres_nettoyees,
        "nb_offres": len(offres_nettoyees),
        "mode_recherche": mode_recherche,
        "cpv_selectionnes": codes_cpv,
        "revision_recherche": nouvelle_revision
    }

    if row is None:
        row = app_tables.histo.add_row(**valeurs)
    else:
        row.update(**valeurs)

    return {
        "ok": True,
        "histo_id": row.get_id(),
        "revision_recherche": nouvelle_revision,
        "nb_offres": len(offres_nettoyees),
        "message": "Dernière recherche sauvegardée."
    }
