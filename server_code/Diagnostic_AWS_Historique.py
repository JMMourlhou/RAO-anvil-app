"""Diagnostic temporaire AWS, sans écriture ni consultation à l'import.

À retirer avec son test après utilisation et accord de l'utilisateur.
"""
import anvil.server
import anvil.users
from typing import Any, cast


_TASKS = (
    ("Task 1", "r277srvhoh7zoh7aw5osymxkno5n2awf3u5pyyck"),
    ("Task 2", "dgxwmp3vsohth7npt5hczzde5vigpf7hsxjwcqlb"),
)
_CHAMPS = ("ok", "statut_collecte", "message_collecte", "anomalies", "portails")
# Identifiants techniques AWS confirmés par l'utilisateur.
_PORTAILS = ("gm", "ml", "nr", "so", "dl", "mp74", "ldm")
_ETAPES = ("formulaire", "recherche", "pagination", "telechargement", "format", "cpv", "geographie")
_STATUTS = ("complete", "partielle", "echouee")
_COMPTEURS = (
    "offres_conservees", "nb_offres", "fiches_verifiees",
    "fiches_rejetees", "fiches_collectees", "nb_anomalies",
    "nombre_offres", "nombre_anomalies", "nombre_avis_verifies",
)
_BOOLEENS = ("candidats_parcourus", "collecte_exploitable")
# Aucune règle exacte du parseur Pi5 n'est disponible dans ce projet.
# N'ajouter ici que des couples (étape, motif exact) vérifiés dans ce parseur.
_MOTIFS_CONNUS: dict[tuple[str, str], str] = {}


def _classer_motif(etape, motif):
    """Classe seulement une correspondance exacte confirmée ; jamais le texte brut."""
    if type(etape) is not str or type(motif) is not str:
        return "motif_non_classe"
    return _MOTIFS_CONNUS.get((etape, motif), "motif_non_classe")


def _valeur_autorisee(valeur, autorisees, remplacement):
    """Écarte les textes libres et les valeurs de type inattendu."""
    if type(valeur) is str and valeur in autorisees:
        return valeur
    return remplacement


def _portail(valeur):
    return _valeur_autorisee(valeur, _PORTAILS, "portail_non_reconnu")


def _resumer_diagnostics(diagnostics):
    """Retourne uniquement des catégories fixes et des compteurs présents.

    Les portails inconnus sont regroupés ; aucun texte libre n'est restitué.
    Les compteurs non reconnus ou imbriqués ne sont pas interprétés.
    """
    sortie = {
        "ok": diagnostics["ok"] if type(diagnostics["ok"]) is bool else None,
        "statut_collecte": _valeur_autorisee(diagnostics["statut_collecte"], _STATUTS, "absent_ou_non_reconnu"),
        "message_collecte_present": bool(diagnostics["message_collecte"]),
        "portails": [],
        "anomalies_par_portail_et_etape": [],
        "anomalies_par_portail_et_categorie": [],
    }
    portails = diagnostics["portails"]
    sortie["structure_portails_reconnue"] = isinstance(portails, (dict, list))
    if isinstance(portails, dict):
        entrees = list(portails.items())
    elif isinstance(portails, list):
        entrees = []
        for bilan in portails:
            identifiant = bilan.get("portail") if isinstance(bilan, dict) else None
            entrees.append((identifiant, bilan))
    else:
        entrees = []

    for identifiant, bilan in entrees:
        resume = {"portail": _portail(identifiant), "structure_reconnue": isinstance(bilan, dict)}
        if isinstance(bilan, dict):
            compteurs = {}
            for nom in _COMPTEURS:
                valeur = bilan.get(nom)
                if type(valeur) is int and valeur >= 0:
                    compteurs[nom] = valeur
            resume["compteurs"] = compteurs
            for nom in _BOOLEENS:
                valeur = bilan.get(nom)
                if type(valeur) is bool:
                    resume[nom] = valeur
            resume["statut_collecte"] = _valeur_autorisee(bilan.get("statut_collecte"), _STATUTS, "absent_ou_non_reconnu")
        sortie["portails"].append(resume)

    anomalies = diagnostics["anomalies"]
    sortie["structure_anomalies_reconnue"] = isinstance(anomalies, list)
    if not isinstance(anomalies, list):
        return sortie
    groupes = {}
    categories = {}
    for anomalie in anomalies:
        if isinstance(anomalie, dict):
            portail = _portail(anomalie.get("portail"))
            etape = _valeur_autorisee(anomalie.get("etape"), _ETAPES, "autre_ou_non_reconnue")
            categorie = _classer_motif(anomalie.get("etape"), anomalie.get("motif"))
        else:
            portail = "portail_non_reconnu"
            etape = "structure_non_reconnue"
            categorie = "motif_non_classe"
        cle = (portail, etape)
        groupes[cle] = groupes.get(cle, 0) + 1
        cle_categorie = (portail, etape, categorie)
        categories[cle_categorie] = categories.get(cle_categorie, 0) + 1
    for (portail, etape), nombre in sorted(groupes.items()):
        sortie["anomalies_par_portail_et_etape"].append({"portail": portail, "etape": etape, "nombre": nombre})
    for (portail, etape, categorie), nombre in sorted(categories.items()):
        sortie["anomalies_par_portail_et_categorie"].append({"portail": portail, "etape": etape, "categorie": categorie, "nombre": nombre})
    return sortie


@anvil.server.callable
def consulter_diagnostics_aws_historiques():
    """Lit deux Tasks fixes pour un administrateur authentifié côté serveur.

    Retour : bilans expurgés, jamais le résultat brut. Aucune écriture.
    Introuvable/retour absent sont attendus ; les autres erreurs remontent.
    Aucun rôle ou identifiant n'est accepté en argument depuis le navigateur.
    """
    utilisateur = anvil.users.get_user()
    if utilisateur is None or utilisateur["role"] != "A":
        raise PermissionError("Accès administrateur requis.")

    rapports = []
    for libelle, task_id in _TASKS:
        rapport: dict[str, Any] = {"task": libelle}
        try:
            task = anvil.server.get_background_task(task_id)
            rapport["accessible"] = True
            # API publique documentée, absente du stub BackgroundTaskState local.
            statut = cast(Any, task).get_termination_status()
            rapport["statut_task"] = _valeur_autorisee(statut, ("completed", "failed", "killed", "missing"), "en_cours_ou_non_reconnu")
            if statut != "completed":
                rapports.append(rapport)
                continue
            resultat = task.get_return_value()
        except anvil.server.BackgroundTaskNotFound:
            # La Task peut aussi disparaître entre sa récupération et sa lecture.
            rapport["accessible"] = False
            rapport["diagnostic"] = "BackgroundTaskNotFound"
            rapports.append(rapport)
            continue

        if resultat is None:
            rapport["resultat_exploitable"] = False
            rapport["diagnostic"] = "retour_absent_ou_indisponible"
        elif not isinstance(resultat, dict):
            rapport["resultat_exploitable"] = False
            rapport["diagnostic"] = "structure_resultat_non_reconnue"
        else:
            diagnostics = {champ: resultat.get(champ) for champ in _CHAMPS}
            rapport["resultat_exploitable"] = True
            rapport["champs_absents"] = [champ for champ in _CHAMPS if champ not in resultat]
            rapport["bilan"] = _resumer_diagnostics(diagnostics)
        rapports.append(rapport)
    return rapports
