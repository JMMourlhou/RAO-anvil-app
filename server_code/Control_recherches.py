"""Registre RAO privé : toutes les opérations ciblent l'utilisateur connecté."""
from datetime import datetime, timezone

import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server


_ETATS_TERMINAUX = ("cancelled", "completed", "failed")
_ETATS_AUTORISES = ("registered", "running", "cancellation_requested") + _ETATS_TERMINAUX
# Nom exact de la colonne existante dans Anvil.
_COLONNE_FIN = "finished_at"


def _error(code, message):
    """Retourne un refus fonctionnel, distinct d'un état de recherche."""
    return {"ok": False, "error": code, "message": message}


def _get_identity(search_id):
    """Valide l'identité serveur et l'identifiant sans consulter les autres users."""
    user = anvil.users.get_user()
    if user is None:
        return None, _error("authentication_required", "Utilisateur connecté obligatoire.")
    if not isinstance(search_id, str) or not search_id.strip():
        return None, _error("invalid_search_id", "search_id doit être une chaîne non vide.")
    # L'identifiant est conservé exactement, sans normalisation implicite.
    return user, None


def _get_row(search_id, user):
    """Recherche exclusivement le couple (search_id, utilisateur connecté)."""
    return app_tables.bg_task_ctrl.get(search_id=search_id, user=user)


def _missing_state():
    """Ne révèle pas l'existence éventuelle d'une recherche d'un autre user."""
    return _error("not_found_or_not_authorized", "Recherche inconnue pour cet utilisateur ou accès non autorisé.")


def _serialize_state(row):
    """Retourne un instantané sérialisable ; une anomalie de registre lève."""
    status = row["status"]
    if status not in _ETATS_AUTORISES:
        raise ValueError("État RAO invalide dans le registre.")
    return {
        "ok": True,
        "search_id": row["search_id"],
        "status": status,
        "cancel_requested": row["cancel_requested_at"] is not None,
        "finished": status in _ETATS_TERMINAUX,
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "cancel_requested_at": row["cancel_requested_at"],
        "finished_at": row[_COLONNE_FIN],
        "background_task_id": row["background_task_id"],
    }


@anvil.server.callable
@tables.in_transaction
def enregistrer_recherche_rao(search_id):
    """Inscrit search_id pour le user courant ; une ligne existante est immuable ici.

    Retour : état structuré ou refus fonctionnel. Crée une ligne au besoin.
    Les erreurs de table ou conflits persistants remontent à l'appelant.
    """
    user, error = _get_identity(search_id)
    if error is not None:
        return error
    row = _get_row(search_id, user)
    if row is None:
        valeurs = {
            "search_id": search_id,
            "user": user,
            "status": "registered",
            "created_at": datetime.now(timezone.utc),
            "started_at": None,
            "cancel_requested_at": None,
            _COLONNE_FIN: None,
            "background_task_id": None,
        }
        row = app_tables.bg_task_ctrl.add_row(**valeurs)
    return _serialize_state(row)


@anvil.server.callable
@tables.in_transaction
def marquer_recherche_en_cours(search_id, background_task_id=None):
    """Note le démarrage et la Task facultative d'une recherche déjà inscrite.

    Préserve l'annulation et toute ligne terminale, y compris ses métadonnées.
    Retour : état structuré ou refus ; erreurs techniques propagées.
    """
    user, error = _get_identity(search_id)
    if error is not None:
        return error
    if background_task_id is not None:
        if not isinstance(background_task_id, str) or not background_task_id.strip():
            return _error("invalid_background_task_id", "background_task_id doit être une chaîne non vide.")
    row = _get_row(search_id, user)
    if row is None:
        return _missing_state()
    state = _serialize_state(row)
    if state["finished"]:
        return state

    # Un démarrage tardif ne peut pas retirer une demande d'annulation.
    valeurs = {}
    if state["status"] == "registered":
        valeurs["status"] = "running"
    if row["started_at"] is None:
        valeurs["started_at"] = datetime.now(timezone.utc)
    if background_task_id is not None:
        valeurs["background_task_id"] = background_task_id
    if valeurs:
        row.update(**valeurs)
    return _serialize_state(row)


@anvil.server.callable
@tables.in_transaction
def demander_annulation_recherche_rao(search_id):
    """Enregistre une demande d'arrêt, sans intervenir sur Anvil ou le Pi.

    search_id doit être déjà inscrit pour le user courant. Retour structuré.
    La première date d'annulation et les états terminaux sont conservés.
    """
    user, error = _get_identity(search_id)
    if error is not None:
        return error
    row = _get_row(search_id, user)
    if row is None:
        return _missing_state()
    state = _serialize_state(row)
    if state["finished"]:
        return state
    valeurs: dict = {"status": "cancellation_requested"}
    if row["cancel_requested_at"] is None:
        valeurs["cancel_requested_at"] = datetime.now(timezone.utc)
    row.update(**valeurs)
    return _serialize_state(row)


@anvil.server.callable
@tables.in_transaction
def obtenir_etat_recherche_rao(search_id):
    """Lit un instantané cohérent pour le user courant ; aucune ligne exposée."""
    user, error = _get_identity(search_id)
    if error is not None:
        return error
    row = _get_row(search_id, user)
    if row is None:
        return _missing_state()
    return _serialize_state(row)


@anvil.server.callable
@tables.in_transaction
def finaliser_recherche_rao(search_id, issue):
    """Finalise avec completed, cancelled ou failed ; retourne l'issue retenue.

    Une annulation déjà demandée transforme completed en cancelled.
    Une ligne terminale reste entièrement inchangée. Erreurs techniques propagées.
    """
    user, error = _get_identity(search_id)
    if error is not None:
        return error
    if issue not in _ETATS_TERMINAUX:
        return _error("invalid_issue", "issue doit être completed, cancelled ou failed.")
    row = _get_row(search_id, user)
    if row is None:
        return _missing_state()
    state = _serialize_state(row)
    if state["finished"]:
        return state
    etat_final = issue
    if state["status"] == "cancellation_requested" and issue == "completed":
        etat_final = "cancelled"
    valeurs: dict = {"status": etat_final}
    if row[_COLONNE_FIN] is None:
        valeurs[_COLONNE_FIN] = datetime.now(timezone.utc)
    row.update(**valeurs)
    return _serialize_state(row)


@anvil.server.callable
def diagnostic_origine_appel_rao():
    """Diagnostic temporaire de l'origine ; aucune identité ni donnée du registre.

    Sans paramètre. Retourne uniquement les types de contexte, la confiance
    déclarée par Anvil et la présence d'un utilisateur. Une propriété absente
    vaut None ; les erreurs techniques ne sont pas interceptées.
    """
    contexte = getattr(anvil.server, "context", None)
    appelant = getattr(contexte, "remote_caller", None)
    client = getattr(contexte, "client", None)
    return {
        "context_type": getattr(contexte, "type", None),
        "remote_caller_type": getattr(appelant, "type", None),
        "remote_caller_is_trusted": getattr(appelant, "is_trusted", None),
        "client_type": getattr(client, "type", None),
        "user_present": anvil.users.get_user() is not None,
    }
