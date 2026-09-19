"""API CPV publique en lecture seule, indépendante des utilisateurs et des tables.

Les erreurs de saisie deviennent des réponses explicites pour le client Anvil.
Les erreurs inattendues se propagent ; elles ne sont jamais masquées.
"""

import anvil.server

from . import CPV_Metier


@anvil.server.callable
def rechercher_cpv(terme, limite=10):
    """Recherche des CPV par libellé officiel ou préfixe de code.

    Paramètres : terme (str, 200 caractères maximum), limite (int, 1 à 50).
    Retour : dict avec ok (bool), resultats (list[dict code/libelle]),
    message (str). Terme vide ou sans correspondance : succès avec [].
    Entrée invalide : ok=False, resultats=[], message explicatif.
    Les erreurs inattendues sont propagées.
    """
    try:
        codes_resultats = CPV_Metier.rechercher_dans_catalogue(terme, limite)
    except CPV_Metier.ErreurValidationCPV as erreur:
        return {"ok": False, "resultats": [], "message": str(erreur)}

    # La limitation a déjà été appliquée côté métier avant la sérialisation.
    resultats_cpv = CPV_Metier.convertir_resultats_anvil(codes_resultats)
    return {"ok": True, "resultats": resultats_cpv, "message": ""}


@anvil.server.callable
def obtenir_libelles_cpv(codes):
    """Résout les libellés officiels des codes sélectionnés.

    Paramètre : codes (list[str]), de 1 à 100 entrées de huit chiffres.
    Retour : dict avec ok, resultats (list[dict code/libelle]), message.
    Les doublons sont retirés dans l'ordre utilisateur. Liste vide, mauvais
    type ou code inconnu : ok=False, resultats=[], message explicatif.
    Les erreurs inattendues sont propagées.
    """
    try:
        codes_selectionnes = CPV_Metier.valider_codes_selectionnes(codes)
    except CPV_Metier.ErreurValidationCPV as erreur:
        return {"ok": False, "resultats": [], "message": str(erreur)}

    resultats_cpv = CPV_Metier.convertir_resultats_anvil(codes_selectionnes)
    return {"ok": True, "resultats": resultats_cpv, "message": ""}


def valider_selection_cpv(codes):
    """Valide côté serveur une sélection avant une future sauvegarde.

    Paramètre : codes (list[str]), de 1 à 100 entrées de huit chiffres.
    Retour : dict avec ok (bool), codes (list[str] dédupliquée), message (str).
    Entrée invalide : ok=False, codes=[], message explicatif.
    Fonction interne non callable ; elle n'effectue aucune sauvegarde.
    Les erreurs inattendues sont propagées.
    """
    try:
        codes_selectionnes = CPV_Metier.valider_codes_selectionnes(codes)
    except CPV_Metier.ErreurValidationCPV as erreur:
        return {"ok": False, "codes": [], "message": str(erreur)}
    return {"ok": True, "codes": codes_selectionnes, "message": ""}
