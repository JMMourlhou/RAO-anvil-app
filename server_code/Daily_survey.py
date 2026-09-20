import anvil.server
import anvil.users

from anvil.tables import app_tables

from datetime import datetime
import anvil.tz

import hashlib
import json
import re

from . import CPV_Metier


def nettoyer_espace(valeur):
    """
    Supprime les espaces inutiles sans modifier le contenu.
    """

    return re.sub(
        r"\s+",
        " ",
        str(valeur or "").strip()
    )


def extraire_elements(valeur):
    """
    Transforme une chaîne ou une liste en éléments distincts.

    Séparateurs acceptés :
    - virgule
    - point-virgule
    - retour à la ligne
    """

    if valeur is None:
        return []

    if isinstance(valeur, (list, tuple, set)):
        valeurs = list(valeur)
    else:
        valeurs = [valeur]

    resultat = []
    deja_vus = set()

    for element in valeurs:
        morceaux = re.split(
            r"[,;\n]+",
            str(element or "")
        )

        for morceau in morceaux:
            texte = nettoyer_espace(morceau)

            if not texte:
                continue

            cle = texte.casefold()

            if cle in deja_vus:
                continue

            deja_vus.add(cle)
            resultat.append(texte)

    return resultat


def normaliser_sources(sources):
    """
    Retourne une liste de sources unique et triée.
    """

    if sources is None:
        return []

    if isinstance(sources, str):
        sources = [sources]

    resultat = []
    deja_vues = set()

    for source in sources:
        source_propre = nettoyer_espace(source).upper()

        if not source_propre:
            continue

        if source_propre in deja_vues:
            continue

        deja_vues.add(source_propre)
        resultat.append(source_propre)

    return sorted(resultat)


def texte_depuis_elements(elements):
    """
    Reconstitue une chaîne compatible avec les champs de Search.
    """

    return ", ".join(elements)


def elements_pour_cle(elements):
    """
    Prépare une liste triée utilisée uniquement pour détecter
    les veilles identiques.
    """

    return sorted(
        nettoyer_espace(element).casefold()
        for element in elements
        if nettoyer_espace(element)
    )


def creer_cle_requete(
    email,
    sources,
    mots_cles,
    mots_ou,
    mots_exclus,
    departements
):
    """
    Crée une signature stable de la veille.

    L’ordre de saisie des mots ou des départements
    ne crée pas artificiellement une nouvelle veille.
    """

    contenu = {
        "version": 1,
        "email": nettoyer_espace(email).casefold(),
        "sources": sorted(sources),
        "mots_cles": elements_pour_cle(mots_cles),
        "mots_ou": elements_pour_cle(mots_ou),
        "mots_exclus": elements_pour_cle(mots_exclus),
        "departements": elements_pour_cle(departements),
        "nb_jours": 1
    }

    texte = json.dumps(
        contenu,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        texte.encode("utf-8")
    ).hexdigest()


@anvil.server.callable(require_user=True)
def enregistrer_daily_survey(
    sources,
    mots_cles="",
    mots_ou="",
    mots_exclus="",
    departements=""
):
    """
    Enregistre une recherche devant être exécutée chaque nuit.

    Le nombre de jours est volontairement fixé à 1 côté serveur.
    """

    
    user = anvil.users.get_user()

    if not user:
        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": "Utilisateur non connecté."
        }

    email_texte = user['email']
    print(email_texte)
    if not email_texte:
        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": "Adresse e-mail introuvable."
        }

    sources_propres = normaliser_sources(sources)

    mots_cles_liste = extraire_elements(mots_cles)
    mots_ou_liste = extraire_elements(mots_ou)
    mots_exclus_liste = extraire_elements(mots_exclus)
    departements_liste = extraire_elements(departements)

    if not sources_propres:
        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": "Sélectionnez au moins une source."
        }

    if not mots_cles_liste and not mots_ou_liste:
        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": (
                "Saisissez au moins un mot obligatoire "
                "ou un mot OU."
            )
        }

    cle_requete = creer_cle_requete(
        email=email_texte,
        sources=sources_propres,
        mots_cles=mots_cles_liste,
        mots_ou=mots_ou_liste,
        mots_exclus=mots_exclus_liste,
        departements=departements_liste
    )

    lignes_existantes = app_tables.daily_survey.search(
        email=user,
        cle_requete=cle_requete
    )

    ligne_existante = next(
        iter(lignes_existantes),
        None
    )

    if ligne_existante is not None:

        if bool(ligne_existante["active"]):
            return {
                "ok": False,
                "statut": "deja_active",
                "daily_survey_id": ligne_existante.get_id(),
                "message": (
                    "Rien de grave: Cette veille quotidienne est déjà active !\n Il faut changer de paramètres pour créer une autre veille."
                )
            }

        # Une veille identique désactivée est réactivée.
        ligne_existante["active"] = True
        ligne_existante["derniere_erreur"] = ""

        return {
            "ok": True,
            "statut": "reactivee",
            "daily_survey_id": ligne_existante.get_id(),
            "message": (
                "Cette veille existait déjà et vient "
                "d’être réactivée."
            )
        }
    try:
        nouvelle_ligne = app_tables.daily_survey.add_row(
            email=user,
            sources=sources_propres,
            mots_cles=texte_depuis_elements(
                mots_cles_liste
            ),
            mots_ou=texte_depuis_elements(
                mots_ou_liste
            ),
            mots_exclus=texte_depuis_elements(
                mots_exclus_liste
            ),
            nb_jours=1,
            departements=texte_depuis_elements(
                departements_liste
            ),
            active=True,
            date_creation=datetime.now(anvil.tz.tzutc()),
            derniere_recherche=None,
            nb_offres_derniere_recherche=0,
            dernier_statut="jamais_lancee",
            derniere_erreur="",
            cle_requete=cle_requete
        )

        return {
            "ok": True,
            "statut": "creee",
            "daily_survey_id": nouvelle_ligne.get_id(),
            "message": "La veille quotidienne a été créée."
        }

    except Exception as e:
        print(
            "ERREUR enregistrer_daily_survey :",
            repr(e)
        )

        return {
            "ok": False,
            "statut": "erreur",
            "daily_survey_id": None,
            "message": (
                f"Erreur lors de la création de la veille : {repr(e)}"
            )
        }


# Parcours CPV indépendant : les fonctions legacy ci-dessus restent inchangées.
SOURCES_VEILLE_CPV = ("BOAMP", "TED", "AWS", "CARIF")

# Le sélecteur affiche et transmet CARIF-OREF, tandis que le moteur CPV
# attend CARIF. Seuls les alias explicitement listés sont acceptés.
ALIASES_SOURCES_CPV = {
    "BOAMP": "BOAMP",
    "TED": "TED",
    "AWS": "AWS",
    "CARIF": "CARIF",
    "CARIF-OREF": "CARIF",
}


class ErreurValidationVeilleCPV(ValueError):
    """Critère de veille CPV invalide pouvant être expliqué à l'utilisateur."""


def verifier_saisie_textuelle_cpv(valeur, nom_critere):
    """Vérifie un critère facultatif sans transformer ni muter sa valeur.

    Paramètres : valeur (str, list[str] ou None), nom_critere (str).
    Retour : None. Lève ErreurValidationVeilleCPV pour tout autre type,
    y compris une liste contenant autre chose que des chaînes.
    """
    if valeur is None or isinstance(valeur, str):
        return
    if not isinstance(valeur, list):
        raise ErreurValidationVeilleCPV(nom_critere + " : texte ou liste de chaînes attendu.")
    for element in valeur:
        if not isinstance(element, str):
            raise ErreurValidationVeilleCPV(nom_critere + " : chaque élément doit être une chaîne.")


def normaliser_sources_cpv(sources):
    """Normalise et contrôle les sources autorisées du parcours CPV.

    Paramètre : sources (str pour une seule source, ou list[str]).
    Retour : list[str] canonique non vide, dédupliquée et triée.
    L'alias CARIF-OREF devient CARIF après nettoyage des espaces et de la casse.
    Lève ErreurValidationVeilleCPV si type invalide, sélection vide ou source
    inconnue. Les éléments vides sont ignorés comme dans le parcours historique.
    """
    verifier_saisie_textuelle_cpv(sources, "Sources")
    sources_normalisees = normaliser_sources(sources)
    if not sources_normalisees:
        raise ErreurValidationVeilleCPV("Sélectionnez au moins une source.")
    sources_canoniques = set()
    for source in sources_normalisees:
        if source not in ALIASES_SOURCES_CPV:
            raise ErreurValidationVeilleCPV("Source non supportée : " + source)
        source_canonique = ALIASES_SOURCES_CPV[source]
        sources_canoniques.add(source_canonique)
    return sorted(sources_canoniques)


def normaliser_departements_cpv(departements):
    """Normalise les départements pour la colonne texte existante.

    Paramètre : departements (str, list[str] ou None).
    Retour : str triée, dédupliquée, en majuscules et séparée par ', ',
    ou '' si vide. Séparateurs : virgule, point-virgule et retour à la ligne.
    Lève ErreurValidationVeilleCPV pour un mauvais type. L'existence des codes
    n'est pas contrôlée : aucun référentiel départemental fiable n'est disponible.
    """
    verifier_saisie_textuelle_cpv(departements, "Départements")
    elements_departements = extraire_elements(departements)
    departements_normalises = set()
    for departement in elements_departements:
        departements_normalises.add(departement.upper())
    return texte_depuis_elements(sorted(departements_normalises))


def normaliser_exclusions_cpv(mots_exclus):
    """Normalise les exclusions sans reformuler les expressions saisies.

    Paramètre : mots_exclus (str, list[str] ou None).
    Retour : str séparée par ', ', ou '' si vide. Le nettoyage historique
    retire les doublons sans distinction de casse et conserve la première
    graphie ainsi que l'ordre. Lève ErreurValidationVeilleCPV si type invalide.
    """
    verifier_saisie_textuelle_cpv(mots_exclus, "Mots exclus")
    return texte_depuis_elements(extraire_elements(mots_exclus))


def creer_cle_requete_cpv(email_utilisateur, codes_cpv_valides, sources, departements, mots_exclus):
    """Calcule l'empreinte SHA-256 version 2 des critères CPV déjà normalisés.

    Paramètres : email_utilisateur (str), codes_cpv_valides (list[str]),
    sources (list[str]), departements et mots_exclus (str).
    Retour : str hexadécimale de 64 caractères. Helper interne : les entrées
    doivent avoir été validées avant l'appel. Les erreurs inattendues se propagent.
    """
    # L'ordre de sélection est utile à l'interface, mais ne doit pas créer
    # une veille supplémentaire lorsque seuls les critères sont réordonnés.
    contenu_canonique = {
        "version": 2,
        "mode_recherche": "cpv",
        "email": email_utilisateur.strip().casefold(),
        "cpv_selectionnes": sorted(codes_cpv_valides),
        "sources": sorted(sources),
        "departements": elements_pour_cle(extraire_elements(departements)),
        "mots_exclus": elements_pour_cle(extraire_elements(mots_exclus)),
        "nb_jours": 1,
    }
    texte_canonique = json.dumps(contenu_canonique, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texte_canonique.encode("utf-8")).hexdigest()


def rechercher_doublon_cpv(utilisateur, cle_requete):
    """Recherche une veille identique appartenant au seul utilisateur connecté.

    Paramètres : utilisateur (ligne Users obtenue côté serveur), cle_requete (str).
    Retour : ligne daily_survey ou None. Les erreurs Data Tables se propagent.
    Cette fonction n'est pas callable ; l'identité ne vient jamais du client.
    """
    lignes_existantes = app_tables.daily_survey.search(email=utilisateur, cle_requete=cle_requete)
    return next(iter(lignes_existantes), None)


def creer_ligne_veille_cpv(utilisateur, codes_cpv_valides, sources, departements, mots_exclus, cle_requete):
    """Insère une veille CPV dont tous les critères ont déjà été validés.

    Paramètres : utilisateur (ligne Users), codes_cpv_valides et sources
    (list[str]), departements, mots_exclus et cle_requete (str).
    Retour : nouvelle ligne daily_survey. Les erreurs Data Tables se propagent.
    Helper interne, sans appel automatique lors de l'import du module.
    """
    colonnes_veille = {
        "email": utilisateur,
        "sources": sources,
        "mots_cles": "",
        "mots_ou": "",
        "mots_exclus": mots_exclus,
        "nb_jours": 1,
        "departements": departements,
        "active": True,
        "date_creation": datetime.now(anvil.tz.tzutc()),
        "derniere_recherche": None,
        "dernier_statut": "jamais_lancee",
        "derniere_erreur": "",
        "cle_requete": cle_requete,
        "nb_offres_derniere_recherche": 0,
        "mode_recherche": "cpv",
        "cpv_selectionnes": codes_cpv_valides,
    }
    return app_tables.daily_survey.add_row(**colonnes_veille)


def repondre_erreur_veille_cpv(message):
    """Construit une réponse de validation conforme au contrat des veilles.

    Paramètre : message (str explicatif). Retour : dict avec ok=False,
    statut='erreur', daily_survey_id=None et message. Aucun effet de bord.
    """
    return {"ok": False, "statut": "erreur", "daily_survey_id": None, "message": message}


@anvil.server.callable(require_user=True)
def enregistrer_daily_survey_cpv(cpv_selectionnes, sources, departements=None, mots_exclus=None):
    """Crée ou réactive une veille quotidienne CPV pour l'utilisateur connecté.

    Paramètres
    ----------
    cpv_selectionnes : list[str]
        De 1 à 100 entrées CPV officielles ; doublons retirés dans l'ordre saisi.
    sources : list[str] ou str
        Sources parmi BOAMP, TED, AWS et CARIF ; au moins une est requise.
    departements, mots_exclus : str, list[str] ou None
        Critères facultatifs, stockés dans les colonnes texte existantes.

    Retour
    ------
    dict
        ok (bool), statut ('cree', 'deja_active', 'reactivee' ou 'erreur'),
        daily_survey_id (str ou None), message (str).
        Comme dans le legacy, un doublon actif retourne ok=False.

    Erreurs
    -------
    Anvil refuse les appels non authentifiés. Le contrôle interne reste présent
    pour les appels directs. Identité ou critères invalides : retour 'erreur'
    avant tout accès à daily_survey. Les erreurs inattendues se propagent.
    """
    utilisateur = anvil.users.get_user()
    if utilisateur is None:
        return repondre_erreur_veille_cpv("Utilisateur non connecté.")

    email_utilisateur = utilisateur["email"]
    if not isinstance(email_utilisateur, str):
        return repondre_erreur_veille_cpv("Adresse e-mail utilisateur inexploitable.")
    email_utilisateur = email_utilisateur.strip()
    if re.fullmatch(r"[^@\s]+@[^@\s]+", email_utilisateur) is None:
        return repondre_erreur_veille_cpv("Adresse e-mail utilisateur inexploitable.")

    try:
        codes_cpv_valides = CPV_Metier.valider_codes_selectionnes(cpv_selectionnes)
        sources_normalisees = normaliser_sources_cpv(sources)
        departements_normalises = normaliser_departements_cpv(departements)
        exclusions_normalisees = normaliser_exclusions_cpv(mots_exclus)
    except (CPV_Metier.ErreurValidationCPV, ErreurValidationVeilleCPV) as erreur:
        return repondre_erreur_veille_cpv(str(erreur))

    cle_requete = creer_cle_requete_cpv(
        email_utilisateur, codes_cpv_valides, sources_normalisees,
        departements_normalises, exclusions_normalisees
    )
    ligne_existante = rechercher_doublon_cpv(utilisateur, cle_requete)
    if ligne_existante is not None:
        if ligne_existante["active"]:
            return {
                "ok": False,
                "statut": "deja_active",
                "daily_survey_id": ligne_existante.get_id(),
                "message": "Cette veille CPV est déjà active.",
            }

        # Conserver les critères et l'historique de cette même ligne :
        # une réactivation ne correspond pas à une nouvelle recherche.
        ligne_existante["active"] = True
        ligne_existante["derniere_erreur"] = ""
        return {
            "ok": True,
            "statut": "reactivee",
            "daily_survey_id": ligne_existante.get_id(),
            "message": "La veille CPV a été réactivée.",
        }

    nouvelle_ligne = creer_ligne_veille_cpv(
        utilisateur, codes_cpv_valides, sources_normalisees,
        departements_normalises, exclusions_normalisees, cle_requete
    )
    return {
        "ok": True,
        "statut": "cree",
        "daily_survey_id": nouvelle_ligne.get_id(),
        "message": "La veille quotidienne CPV a été créée.",
    }
