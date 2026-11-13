"""Barrière Anvil manuelle. Le gel des services/PostgreSQL relève du Pi5.

Une seule ligne persistante, aucun cache de session et aucune expiration.
Une admission antérieure au gel peut finir : son ticket interdit alors de
confondre « barrière active » et « application au repos ».
"""
from copy import deepcopy
from datetime import datetime, timezone
from functools import wraps
from typing import Any, cast
import uuid

import anvil.server
import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables


_CLE_ETAT = "rao_maintenance_v1"
_APPLICATION_CIBLE = "G6OBBXFGT3T7OU2J"
_VERSION_CODE = "maintenance-rao-v1"
_VERSION_BASE = "2c9cba0a23cd4eaa74085e76455c7af635a60f65"
_MESSAGE = "RAO est en maintenance. Les nouvelles recherches et veilles sont temporairement indisponibles."
_TERMINAUX_TASK = ("completed", "failed", "killed")
_POINTS = ("recherche_classique", "recherche_cpv", "recherche_catalogue", "veille_classique", "veille_cpv")


def _maintenant():
    return datetime.now(timezone.utc).isoformat()


def _etat_initial():
    return {"actif": False, "revision": 0, "activation": None,
            "modification": None, "operateur": None, "operations": {},
            "verification_services": None}


def _charger_etat():
    """Lit sans écrire. Un document invalide lève et n'ouvre jamais la barrière."""
    row = app_tables.global_variables.get(name=_CLE_ETAT)
    if row is None:
        return None, _etat_initial()
    etat = deepcopy(row["value"])
    if (not isinstance(etat, dict) or type(etat.get("actif")) is not bool
            or type(etat.get("revision")) is not int
            or not isinstance(etat.get("operations"), dict)):
        raise ValueError("État de maintenance RAO invalide : nouveaux lancements interdits.")
    return row, etat


def _ecrire_etat(row, etat):
    etat["revision"] += 1
    if row is None:
        app_tables.global_variables.add_row(name=_CLE_ETAT, value=etat,
                                           commentaires="Barrière RAO manuelle ; aucune expiration.")
    else:
        row.update(value=etat)


def _bloque(etat, point):
    recherches = ("recherche_classique", "recherche_cpv", "recherche_catalogue")
    return etat["actif"] and not (point in recherches and etat.get("recherches_autorisees") is True)


def refus_si_maintenance(point=None):
    """Contrôle serveur utilisable dans une transaction ou à l'entrée d'une Task.

    Ne remplace pas l'admission suivie pour une opération avec effet de bord.
    Aucune lecture d'historique, aucun appel externe.
    """
    _, etat = _charger_etat()
    if _bloque(etat, point):
        return {"ok": False, "error": "maintenance", "message": _MESSAGE,
                "statut": "erreur", "daily_survey_id": None}
    return None


def _administrateur():
    """Réutilise uniquement le rôle administrateur existant, sans compte nouveau."""
    user = anvil.users.get_user()
    if user is None or user["enabled"] is not True or user["role"] != "A":
        raise PermissionError("Compte administrateur RAO actif requis.")
    return user.get_id()


@anvil.server.callable(require_user=True)
@tables.in_transaction
def activer_maintenance_rao():
    """Ferme les nouvelles admissions, sans tuer les opérations déjà admises."""
    operateur = _administrateur()
    row, etat = _charger_etat()
    if not etat["actif"] or etat.get("recherches_autorisees") is True:
        etat.update(actif=True, activation=_maintenant(), modification=_maintenant(),
                    operateur=operateur, verification_services=None, recherches_autorisees=False)
        _ecrire_etat(row, etat)
    return {"ok": True, "maintenance": etat["actif"], "activation": etat["activation"],
            "message": "Barrière active ; vérifier les tâches et le gel Pi5 séparément."}


@anvil.server.callable(require_user=True)
@tables.in_transaction
def desactiver_maintenance_rao(services_verifies=False, reference_verification=""):
    """Réouverture manuelle après contrôle Pi5 effectué par l'opérateur.

    La référence est une trace du contrôle humain, jamais une sonde PostgreSQL.
    Ne pas transmettre de secret dans cette référence.
    """
    operateur = _administrateur()
    if services_verifies is not True or not isinstance(reference_verification, str) or not reference_verification.strip():
        return {"ok": False, "message": "Confirmer le contrôle des services Pi5 et sa référence avant réouverture."}
    row, etat = _charger_etat()
    etat.update(actif=False, modification=_maintenant(), operateur=operateur,
                verification_services={"reference": reference_verification.strip(),
                                       "date": _maintenant(), "operateur": operateur,
                                       "origine": "confirmation_manuelle"})
    _ecrire_etat(row, etat)
    return {"ok": True, "maintenance": False, "message": "Admissions Anvil rouvertes manuellement."}


@anvil.server.callable(require_user=True)
@tables.in_transaction
def rouvrir_recherches_rao():
    """Rouvre uniquement les recherches. Ne change ni les veilles ni le Pi5.

    Une nouvelle activation de maintenance referme aussi cette exception.
    À appeler manuellement dans la session administrateur de l'environnement visé.
    """
    operateur = _administrateur()
    row, etat = _charger_etat()
    etat.update(recherches_autorisees=True, modification=_maintenant(), operateur=operateur)
    _ecrire_etat(row, etat)
    return {"ok": True, "recherches_autorisees": True, "maintenance": etat["actif"],
            "message": "Recherches rouvertes ; état des veilles inchangé."}


@tables.in_transaction
def _admettre(point):
    """Sérialise admission et activation sur la même ligne durable."""
    row, etat = _charger_etat()
    if _bloque(etat, point):
        return None, {"ok": False, "error": "maintenance", "message": _MESSAGE,
                      "statut": "erreur", "daily_survey_id": None}
    ticket = str(uuid.uuid4())
    etat["operations"][ticket] = {"point": point, "date": _maintenant(),
                                  "phase": "transmission", "task_id": None}
    _ecrire_etat(row, etat)
    return ticket, None


@tables.in_transaction
def _noter_issue(ticket, phase, task_id=None):
    row, etat = _charger_etat()
    etat["operations"][ticket].update(phase=phase, task_id=task_id)
    _ecrire_etat(row, etat)


def proteger_operation(point):
    """Suit une création/réactivation de veille déjà admise jusqu'à son retour."""
    def decorer(fonction):
        @wraps(fonction)
        def executer(*args, **kwargs):
            ticket, refus = _admettre(point)
            if refus is not None:
                return refus
            try:
                resultat = fonction(*args, **kwargs)
            except Exception:
                # Une erreur réseau/commit ne prouve pas l'absence d'effet.
                _noter_issue(ticket, "inconnue")
                raise
            _noter_issue(ticket, "terminee")
            return resultat
        return executer
    return decorer


def _lancer(point, callable_pi5, criteres):
    """Transmet uniquement une admission persistée ; renvoie la Task inchangée.

    Les admissions antérieures au gel peuvent encore recevoir leur Task.
    Une panne laisse une trace inconnue ; aucun retry ni kill automatique.
    """
    if anvil.users.get_user() is None:
        raise PermissionError("Utilisateur connecté requis.")
    ticket, refus = _admettre(point)
    if refus is not None:
        return refus
    try:
        task = anvil.server.call(callable_pi5, **criteres)
        if task is None:
            _noter_issue(ticket, "inconnue")
            return {"ok": False, "error": "task_absente", "message": "Aucune Task reçue ; vérifier son état avant de relancer."}
        task_id = task.get_id()
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("Identifiant de Task RAO invalide.")
    except Exception:
        _noter_issue(ticket, "inconnue")
        raise
    _noter_issue(ticket, "task", task_id)
    return {"ok": True, "task": task}


@anvil.server.callable(require_user=True)
def lancer_recherche_classique_rao(**criteres):
    return _lancer("recherche_classique", "lancer_recherche_multi_sources_background", criteres)


@anvil.server.callable(require_user=True)
def lancer_recherche_cpv_rao(**criteres):
    return _lancer("recherche_cpv", "lancer_recherche_cpv_background", criteres)


def _observer_task(task):
    statut = cast(Any, task).get_termination_status()
    return {"task_id": task.get_id(), "statut": statut,
            "terminee_confirmee": statut in _TERMINAUX_TASK}


@anvil.server.callable(require_user=True)
def attestation_maintenance_rao():
    """Instantané administratif en lecture seule, sans résultat ni secret.

    Inconnu/non terminal ne signifie jamais terminé. Aucune preuve de repos
    global Pi5 n'est déduite de la seule observation Anvil.
    """
    operateur = _administrateur()
    _, avant = _charger_etat()
    tasks = []
    inconnues = []
    try:
        for task in anvil.server.list_background_tasks(all_environments=True):
            tasks.append(_observer_task(task))
    except (anvil.server.BackgroundTaskNotFound, anvil.server.UplinkDisconnectedError,
            anvil.server.TimeoutError, anvil.server.RuntimeUnavailableError) as erreur:
        inconnues.append({"origine": "liste_tasks", "raison": type(erreur).__name__})

    # Les retours de lancement sont suivis même après la fin de leur RPC.
    observations = {task["task_id"]: task for task in tasks}
    operations = []
    for ticket, operation in avant["operations"].items():
        observation = dict(operation, ticket=ticket)
        if operation["phase"] == "task":
            task_id = operation["task_id"]
            if task_id not in observations:
                try:
                    observations[task_id] = _observer_task(anvil.server.get_background_task(task_id))
                except (anvil.server.BackgroundTaskNotFound, anvil.server.UplinkDisconnectedError,
                        anvil.server.TimeoutError, anvil.server.RuntimeUnavailableError) as erreur:
                    inconnues.append({"origine": ticket, "raison": type(erreur).__name__})
            observation["task"] = observations.get(task_id)
        elif operation["phase"] != "terminee":
            inconnues.append({"origine": ticket, "raison": operation["phase"]})
        operations.append(observation)

    # Conserver les états métier comme tels, sans les transformer en états Task.
    registre = []
    for row in app_tables.bg_task_ctrl.search():
        if row["status"] not in ("completed", "failed", "cancelled"):
            registre.append({"search_id": row["search_id"], "etat_registre": row["status"],
                             "task_id": row["background_task_id"],
                             "annulation_demandee": row["cancel_requested_at"] is not None})

    _, apres = _charger_etat()
    stable = avant["revision"] == apres["revision"]
    non_terminees = [task for task in observations.values() if not task["terminee_confirmee"]]
    return {
        "application_id": _APPLICATION_CIBLE,
        "origine_application_id": "cible_declaree_dans_le_code_non_verifiee_par_API_runtime",
        "version_code": _VERSION_CODE, "version_base": _VERSION_BASE,
        "version_publiee": "non_verifiee", "date_observation": _maintenant(),
        "operateur_attestation": operateur, "maintenance": apres["actif"],
        "recherches_autorisees": not _bloque(apres, "recherche_cpv"),
        "activation": apres["activation"], "operateur_modification": apres["operateur"],
        "verification_services": apres["verification_services"],
        "points_proteges": list(_POINTS) + ["enregistrer_recherche_rao"],
        "instantane_stable": stable, "operations": operations,
        "tasks_observees": list(observations.values()), "etats_inconnus": inconnues,
        "registre_non_terminal": registre,
        "aucune_task_anvil_active_confirmee": stable and not inconnues and not non_terminees and not registre,
        "gel_complet_pi5_verifie": False,
        "hors_perimetre": ["appels Uplink directs et anciens clients", "Tasks de collecte Pi5",
                           "systemd et timers Pi5", "PostgreSQL RAO", "schedulers externes",
                           "autres environnements utilisant une autre base"],
    }
