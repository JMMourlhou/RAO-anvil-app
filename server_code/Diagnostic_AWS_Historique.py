"""Diagnostic temporaire AWS, sans écriture ni consultation à l'import.

À retirer avec son test après utilisation et accord de l'utilisateur.
"""
import anvil.server
import anvil.users
import re
from typing import Any, cast
from urllib.parse import urlsplit


_TASKS = (
    ("Task 1", "r277srvhoh7zoh7aw5osymxkno5n2awf3u5pyyck"),
    ("Task 2", "dgxwmp3vsohth7npt5hczzde5vigpf7hsxjwcqlb"),
    ("Task 3", "dryn4orhnlvbcwrcq6f6ugqgdeimq54ykklqhpxp"),
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
# Ces deux vocabulaires doivent être confirmés par le collecteur ; ne pas
# assimiler ses catégories structurelles aux catégories historiques de motifs.
_SIGNATURE_TEXTES = {
    "branche_parseur": ("papier_enveloppe", "papier_paragraphes"),
    "categorie_refus": (
        "enveloppe_non_reconnue",
        "champs_descriptifs_incomplets",
    ),
}
_SIGNATURE_NOMBRES = ("nombre_h1_directs", "nombre_h2_directs")
_SIGNATURE_BOOLEENS = (
    "table_interieure_presente", "titre_h1_reconnu", "acheteur_h2_non_vide",
    "titre_present", "nature_presente", "procedure_presente",
)
# Messages exacts du rapport Pi5 du 12 octobre 2026, sans normalisation.
PREFIXE_AWS = "Collecte AWS CPV incomplète : "
URL_MOTIF = r"https?://[^\s]+"
MESSAGES_PAR_CATEGORIE = {
    "papier_enveloppe_invalide": (
        "format de détail flux papier non pris en charge",
    ),
    "papier_champs_invalides": (
        "nature de marché flux papier ambiguë",
    ),
    "papier_lieu_contradictoire": (
        "lieu principal flux papier contradictoire",
    ),
    "papier_cpv_structure_invalide": (
        "rattachement du bloc CPV après un en-tête de lot invérifiable",
        "bloc de classification CPV flux papier ambigu",
        "classification CPV flux papier hors bloc reconnu",
        "classification CPV flux papier ambiguë",
        "bloc de classification CPV flux papier vide",
        "classification CPV imbriquée ou non reconnue",
        "structure CPV flux papier non reconnue",
    ),
    "papier_lots_structure_invalide": (
        "identifiant de lot flux papier absent ou ambigu",
        "classification CPV imbriquée dans un en-tête de lot",
        "plusieurs en-têtes de lot dans un même paragraphe",
        "structure CPV de lot flux papier non reconnue",
        "en-tête de lot flux papier imbriqué ou non reconnu",
    ),
    "papier_date_contexte_invalide": (
        "échéance flux papier imbriquée ou de contexte non reconnu",
    ),
    "papier_date_format_invalide": (
        "format d'échéance flux papier non pris en charge",
        "mois d'échéance flux papier non reconnu",
    ),
    "papier_date_valeur_invalide": ("échéance flux papier invalide",),
    "papier_dates_contradictoires": ("échéances globales flux papier contradictoires",),
    "numerote_cpv_non_pris_en_charge": ("classification CPV flux papier numéroté non reconnue",),
    "numerote_lots_non_pris_en_charge": ("structure de lot flux papier numéroté non reconnue",),
    "numerote_structure_invalide": (
        "texte hors paragraphe flux papier numéroté",
        "structure de rubrique flux papier numéroté non reconnue",
        "en-tête de rubrique flux papier numéroté imbriqué",
        "rubrique flux papier numéroté inconnue ou contradictoire",
        "en-tête de rubrique flux papier numéroté mal structuré",
        "valeur hors rubrique flux papier numéroté",
    ),
    "numerote_champs_invalides": (
        "rubrique obligatoire flux papier numéroté absente ou vide",
        "rubrique flux papier numéroté vide",
        "valeur de rubrique flux papier numéroté ambiguë",
        "acheteur flux papier numéroté contradictoire",
        "nature de marché flux papier numéroté non reconnue",
    ),
    "numerote_date_contexte_invalide": ("échéance flux papier numéroté hors rubrique reconnue",),
    "numerote_date_format_invalide": (
        "format de date flux papier numéroté non reconnu",
        "échéance flux papier numéroté non reconnue",
        "date d'envoi flux papier numéroté ambiguë",
    ),
    "numerote_date_valeur_invalide": ("date flux papier numéroté invalide",),
    "numerote_dates_contradictoires": (
        "jour d'échéance flux papier numéroté contradictoire",
        "échéances flux papier numéroté contradictoires",
    ),
}


_SOUS_MOTIFS = {
    "identifiant de lot flux papier absent ou ambigu": "lot_identifiant_absent_ou_ambigu",
    "classification CPV imbriquée dans un en-tête de lot": "lot_cpv_dans_entete",
    "plusieurs en-têtes de lot dans un même paragraphe": "lot_entetes_multiples",
    "structure CPV de lot flux papier non reconnue": "lot_structure_cpv_non_reconnue",
    "en-tête de lot flux papier imbriqué ou non reconnu": "lot_entete_imbrique_ou_non_reconnu",
    "structure de lot flux papier numéroté non reconnue": "lot_numerote_structure_non_reconnue",
    "échéance flux papier imbriquée ou de contexte non reconnu": "date_contexte_imbrique_ou_non_reconnu",
    "format d'échéance flux papier non pris en charge": "date_format_non_pris_en_charge",
    "mois d'échéance flux papier non reconnu": "date_mois_non_reconnu",
    "échéance flux papier invalide": "date_valeur_invalide",
    "échéances globales flux papier contradictoires": "dates_globales_contradictoires",
    "échéance flux papier numéroté hors rubrique reconnue": "date_numerotee_hors_rubrique",
    "format de date flux papier numéroté non reconnu": "date_numerotee_format_non_reconnu",
    "échéance flux papier numéroté non reconnue": "date_numerotee_echeance_non_reconnue",
    "date d'envoi flux papier numéroté ambiguë": "date_numerotee_envoi_ambigu",
    "date flux papier numéroté invalide": "date_numerotee_valeur_invalide",
    "jour d'échéance flux papier numéroté contradictoire": "date_numerotee_jour_contradictoire",
    "échéances flux papier numéroté contradictoires": "dates_numerotees_contradictoires",
}


def _extraire_message_papier(motif):
    """Retire l'enveloppe exacte en mémoire ; aucun contenu libre n'est restitué au client."""
    enveloppe_papier = (
        re.escape(PREFIXE_AWS + "détail ") + URL_MOTIF
        + re.escape(" : " + PREFIXE_AWS) + r"([^\r\n]+)"
    )
    correspondance = re.fullmatch(enveloppe_papier, motif)
    return correspondance.group(1) if correspondance is not None else None


def classifier_motif_format(motif):
    """Classe un message complet du collecteur en catégorie technique fixe.

    Les variables URL, libellé et lot sont consommées sans être retournées.
    Aucun affichage ni effet de bord. Inconnu ou ambigu : motif_non_classe.
    """
    if type(motif) is not str:
        return "motif_non_classe"
    refus_global = re.escape(PREFIXE_AWS + "format de détail non pris en charge : ") + URL_MOTIF
    if re.fullmatch(refus_global, motif):
        return "format_global_non_reconnu"
    message_parseur = _extraire_message_papier(motif)
    if message_parseur is None:
        return "motif_non_classe"
    # Le parseur partage ce message entre deux conditions de refus différentes.
    if message_parseur == "structure de détail flux papier non reconnue":
        return "motif_non_classe"
    for categorie, messages in MESSAGES_PAR_CATEGORIE.items():
        if message_parseur in messages:
            return categorie
    if re.fullmatch(re.escape("champ flux papier absent ou contradictoire : ") + r"[^\r\n]+", message_parseur):
        return "papier_champs_invalides"
    if re.fullmatch(re.escape("échéance dans le contexte du lot ") + r"[A-Za-z0-9]+" + re.escape(" non prise en charge"), message_parseur):
        return "papier_date_contexte_invalide"
    return "motif_non_classe"


def _classer_motif(etape, motif):
    """Classe seulement une correspondance exacte confirmée ; jamais le texte brut."""
    if type(etape) is not str or etape != "format":
        return "motif_non_classe"
    return classifier_motif_format(motif)


def _enveloppe_papier_certaine(motif):
    """Vérifie la forme locale de l'enveloppe, sans valider la destination réseau.

    La regex historique reste inchangée dans le classificateur principal.
    Pour le diagnostic secondaire, URL vide, HTML, contrôles, port invalide ou
    enveloppes répétées empêchent de conclure. Aucun contenu libre n'est retourné.
    """
    modele = (
        re.escape(PREFIXE_AWS + "détail ") + "(" + URL_MOTIF + ")"
        + re.escape(" : " + PREFIXE_AWS) + r"([^\r\n]+)"
    )
    correspondance = re.fullmatch(modele, motif)
    if correspondance is None or motif.count(PREFIXE_AWS) != 2:
        return False
    url = correspondance.group(1)
    if any(ord(caractere) < 32 or ord(caractere) == 127 or caractere in '<>"' for caractere in url):
        return False
    try:
        adresse = urlsplit(url)
        # Lire port déclenche ValueError si sa syntaxe ou sa plage est invalide.
        port = adresse.port
        return bool(adresse.hostname) and adresse.username is None and adresse.password is None and (port is None or port > 0)
    except ValueError:
        return False


def _sous_categorie_format(etape, motif, categorie):
    """Explique un refus avec des libellés fixes, sans supposer sa cause externe.

    Seul le retrait strict de l'enveloppe normalise le texte. Les autres étapes
    ne sont pas interprétées avec les règles du parseur format.
    """
    if type(etape) is not str or etape != "format":
        return "non_applicable"
    if motif is None or (type(motif) is str and motif == ""):
        return "motif_absent"
    if type(motif) is not str:
        return "motif_type_incorrect"
    message = _extraire_message_papier(motif)
    if categorie == "motif_non_classe":
        if message is None:
            return "enveloppe_non_reconnue"
        if not _enveloppe_papier_certaine(motif):
            return "motif_non_classe"
        if message == "structure de détail flux papier non reconnue":
            return "message_ambigu_connu"
        return "message_inconnu"
    if message in _SOUS_MOTIFS:
        return _SOUS_MOTIFS[message]
    if categorie == "papier_date_contexte_invalide" and message is not None:
        # Le classificateur principal a déjà vérifié le gabarit alphanumérique du lot.
        return "date_dans_contexte_lot_non_prise_en_charge"
    return "sous_motif_non_detaille"


def _valeur_autorisee(valeur, autorisees, remplacement):
    """Écarte les textes libres et les valeurs de type inattendu."""
    if type(valeur) is str and valeur in autorisees:
        return valeur
    return remplacement


def _portail(valeur):
    return _valeur_autorisee(valeur, _PORTAILS, "portail_non_reconnu")


def _filtrer_signature_structurelle(signature):
    """Copie exclusivement les champs et valeurs autorisés d'une signature.

    Un champ absent reste absent ; None signifie non évalué et reste None.
    Les valeurs malformées sont omises, jamais converties en zéro ou False.
    Retour : dictionnaire expurgé, ou None si la signature n'est pas un dict.
    """
    if type(signature) is not dict:
        return None
    propre: dict[str, Any] = {}
    for nom, autorisees in _SIGNATURE_TEXTES.items():
        if nom not in signature:
            continue
        valeur = signature[nom]
        if valeur is None or (type(valeur) is str and valeur in autorisees):
            propre[nom] = valeur
    for nom in _SIGNATURE_NOMBRES:
        if nom not in signature:
            continue
        valeur = signature[nom]
        if valeur is None or (type(valeur) is int and valeur >= 0):
            propre[nom] = valeur
    for nom in _SIGNATURE_BOOLEENS:
        if nom not in signature:
            continue
        valeur = signature[nom]
        if valeur is None or type(valeur) is bool:
            propre[nom] = valeur
    if "portail" in signature:
        valeur = signature["portail"]
        if valeur is None or (type(valeur) is str and valeur in _PORTAILS):
            propre["portail"] = valeur
    return propre


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
        "anomalies_par_portail_etape_portee_sous_categorie": [],
        "signatures_structurelles_par_portail": [],
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
    details = {}
    signatures = {}
    for anomalie in anomalies:
        if isinstance(anomalie, dict):
            portail = _portail(anomalie.get("portail"))
            etape = _valeur_autorisee(anomalie.get("etape"), _ETAPES, "autre_ou_non_reconnue")
            categorie = _classer_motif(anomalie.get("etape"), anomalie.get("motif"))
            sous_categorie = _sous_categorie_format(anomalie.get("etape"), anomalie.get("motif"), categorie)
            portee = _valeur_autorisee(anomalie.get("portee"), ("fiche", "portail"), "portee_non_reconnue")
            if etape == "format" and "signature_structurelle" in anomalie:
                signature = _filtrer_signature_structurelle(anomalie["signature_structurelle"])
                if signature is not None:
                    # Regroupement après filtrage : aucun champ libre dans les clés.
                    # Le portail de l'anomalie reste le portail de regroupement.
                    cle_signature = (portail, tuple(signature.items()))
                    signatures[cle_signature] = signatures.get(cle_signature, 0) + 1
        else:
            portail = "portail_non_reconnu"
            etape = "structure_non_reconnue"
            categorie = "motif_non_classe"
            sous_categorie = "non_applicable"
            portee = "portee_non_reconnue"
        cle = (portail, etape)
        groupes[cle] = groupes.get(cle, 0) + 1
        cle_categorie = (portail, etape, categorie)
        categories[cle_categorie] = categories.get(cle_categorie, 0) + 1
        cle_detail = (portail, etape, portee, categorie, sous_categorie)
        details[cle_detail] = details.get(cle_detail, 0) + 1
    for (portail, etape), nombre in sorted(groupes.items()):
        sortie["anomalies_par_portail_et_etape"].append({"portail": portail, "etape": etape, "nombre": nombre})
    for (portail, etape, categorie), nombre in sorted(categories.items()):
        sortie["anomalies_par_portail_et_categorie"].append({"portail": portail, "etape": etape, "categorie": categorie, "nombre": nombre})
    for (portail, etape, portee, categorie, sous_categorie), nombre in sorted(details.items()):
        sortie["anomalies_par_portail_etape_portee_sous_categorie"].append({
            "portail": portail, "etape": etape, "portee": portee,
            "categorie": categorie, "sous_categorie": sous_categorie, "nombre": nombre,
        })
    for (portail, champs), nombre in signatures.items():
        sortie["signatures_structurelles_par_portail"].append({
            "portail": portail, "signature_structurelle": dict(champs), "nombre": nombre,
        })
    return sortie


@anvil.server.callable
def consulter_diagnostics_aws_historiques():
    """Lit trois Tasks fixes pour un administrateur authentifié côté serveur.

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
