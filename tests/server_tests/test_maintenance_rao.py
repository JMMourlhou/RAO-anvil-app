"""Campagne ciblée : vrais corps Python, transport et tables isolés.

Ne charge aucun collecteur et ne modifie jamais la clé de maintenance réelle.
Ces tests ne constituent pas une recette navigateur ni une preuve Pi5.
"""
import ast
import copy
from pathlib import Path
import sys
from threading import RLock
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
import test_search_recherche_cpv as search_support
from test_search_reset_historique import charger_initialisation


class Row(dict):
    def get_id(self):
        return "test-row"


class Table:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.writes = 0

    def get(self, **filters):
        matches = [row for row in self.rows if all(row.get(k) == v for k, v in filters.items())]
        if len(matches) > 1:
            raise RuntimeError("Ligne de maintenance dupliquée")
        return matches[0] if matches else None

    def add_row(self, **values):
        self.writes += 1
        row = Row(values)
        self.rows.append(row)
        return row

    def search(self, *args, **kwargs):
        return list(self.rows)


def charger(fichier, espace):
    """Charge les fonctions sans enregistrement callable ni imports d'application."""
    arbre = ast.parse((ROOT / fichier).read_text())
    corps = []
    for noeud in arbre.body:
        if isinstance(noeud, ast.Import):
            if any(alias.name.startswith("anvil") for alias in noeud.names):
                continue
        if isinstance(noeud, ast.ImportFrom):
            if noeud.level or (noeud.module or "").startswith("anvil"):
                continue
        if isinstance(noeud, ast.FunctionDef):
            noeud.decorator_list = [d for d in noeud.decorator_list
                                   if "anvil.server.callable" not in ast.unparse(d)
                                   and "anvil.server.background_task" not in ast.unparse(d)]
        corps.append(noeud)
    module = ast.fix_missing_locations(ast.Module(body=corps, type_ignores=[]))
    exec(compile(module, fichier, "exec"), espace)
    return SimpleNamespace(**espace)


class TestsMaintenanceRAO(unittest.TestCase):
    def setUp(self):
        self.globales = Table()
        self.registre = Table()
        self.user = Row(role="A", enabled=True, email="recette@example.invalid")
        self.server = SimpleNamespace(
            call=Mock(side_effect=AssertionError("Collecte externe interdite dans ces tests")),
            list_background_tasks=Mock(return_value=[]),
            get_background_task=Mock(),
        )
        for nom in ("BackgroundTaskNotFound", "UplinkDisconnectedError", "TimeoutError", "RuntimeUnavailableError"):
            setattr(self.server, nom, type(nom, (Exception,), {}))
        self.server.get_background_task.side_effect = self.server.BackgroundTaskNotFound()
        self.anvil = SimpleNamespace(server=self.server, users=SimpleNamespace(get_user=lambda: self.user))
        self.verrou = RLock()

        def transaction(fonction):
            def executer(*args, **kwargs):
                with self.verrou:
                    return fonction(*args, **kwargs)
            return executer

        self.espace = dict(anvil=self.anvil,
                           tables=SimpleNamespace(in_transaction=transaction),
                           app_tables=SimpleNamespace(global_variables=self.globales, bg_task_ctrl=self.registre))
        self.api = charger("server_code/Maintenance_RAO.py", self.espace)

    def attestation(self):
        return self.api.attestation_maintenance_rao()

    def task(self, statut=None):
        return SimpleNamespace(get_id=lambda: "task-recette", get_termination_status=lambda: statut)

    def test_classique_et_cpv_refusees_sans_transport(self):
        self.api.activer_maintenance_rao()
        for fonction in (self.api.lancer_recherche_classique_rao, self.api.lancer_recherche_cpv_rao):
            reponse = fonction(sources=["BOAMP"])
            self.assertFalse(reponse["ok"])
            self.assertEqual(reponse["error"], "maintenance")
            self.assertIn("maintenance", reponse["message"])
        self.server.call.assert_not_called()
        self.assertEqual(self.attestation()["operations"], [])

    def test_passage_task_et_arguments_sans_projection(self):
        task = self.task()
        self.server.call.side_effect = None
        self.server.call.return_value = task
        for fonction, nom in ((self.api.lancer_recherche_classique_rao, "lancer_recherche_multi_sources_background"),
                              (self.api.lancer_recherche_cpv_rao, "lancer_recherche_cpv_background")):
            self.assertIs(fonction(sources=["BOAMP"], filtre_jours=7)["task"], task)
            self.server.call.assert_called_with(nom, sources=["BOAMP"], filtre_jours=7)

    def test_veille_creation_et_reactivation_refusees_avant_corps(self):
        daily = charger("server_code/Daily_survey.py", dict(self.espace, Maintenance_RAO=self.api,
                        CPV_Metier=Mock(), app_tables=SimpleNamespace(daily_survey=Mock())))
        self.api.activer_maintenance_rao()
        for fonction in (daily.enregistrer_daily_survey, daily.enregistrer_daily_survey_cpv):
            resultat = fonction(sources=["BOAMP"])
            self.assertEqual(resultat["error"], "maintenance")
            self.assertIsNone(resultat["daily_survey_id"])
        self.server.call.assert_not_called()

    def test_inscription_refusee_annulation_et_finalisation_preservees(self):
        row = Row(search_id="recherche-en-cours", user=self.user, status="running",
                  created_at=None, started_at=None, cancel_requested_at=None,
                  finished_at=None, background_task_id="task-recette")
        self.registre.rows.append(row)
        control = charger("server_code/Control_recherches.py", dict(self.espace, Maintenance_RAO=self.api))
        self.server.launch_background_task = Mock()
        self.api.activer_maintenance_rao()
        self.assertEqual(control.enregistrer_recherche_rao("nouvelle")["error"], "maintenance")
        self.assertEqual(control.demander_annulation_recherche_rao("recherche-en-cours")["status"], "cancellation_requested")
        self.server.launch_background_task.assert_called_once_with("_signaler_annulation_recherche_rao", "recherche-en-cours")
        self.assertTrue(self.attestation()["registre_non_terminal"][0]["annulation_demandee"])
        self.assertEqual(control.finaliser_recherche_rao("recherche-en-cours", "completed")["status"], "cancelled")
        self.assertEqual(len(self.registre.rows), 1)

    def test_historique_consultable_sans_ecriture(self):
        self.api.activer_maintenance_rao()
        row = Row(mots_cles="recette", mots_ou="", mots_exclus="", nb_jours=7, departements="",
                  sources=["BOAMP"], mode_recherche="classique", cpv_selectionnes=[], revision_recherche=4,
                  statut_collecte="partielle", message_collecte="Avertissement conservé", offres=[{"titre": "Offre sauvegardée"}])
        avant = copy.deepcopy(row)
        histo = SimpleNamespace(get=Mock(return_value=row))
        api = charger_initialisation(self.anvil, SimpleNamespace(histo=histo,
                                    platformes=SimpleNamespace(search=lambda *args: [])))
        restauration = api["initialiser_form_search"](True)["histo"]
        self.assertEqual(restauration["offres"], row["offres"])
        self.assertEqual(restauration["message_collecte"], row["message_collecte"])
        self.assertEqual(row, avant)
        self.server.call.assert_not_called()

    def test_droits_admin_sans_nouvelle_gestion_utilisateurs(self):
        for user in (None, Row(role="U", enabled=True), Row(role="A", enabled=False)):
            self.user = user
            for fonction in (self.api.activer_maintenance_rao, self.api.desactiver_maintenance_rao,
                              self.api.attestation_maintenance_rao):
                with self.assertRaises(PermissionError):
                    fonction()
        self.assertEqual(self.globales.rows, [])

    def test_reconnexion_et_reouverture_uniquement_manuelle(self):
        self.api.activer_maintenance_rao()
        nouvelle_api = charger("server_code/Maintenance_RAO.py", dict(self.espace))
        self.assertTrue(nouvelle_api.attestation_maintenance_rao()["maintenance"])
        self.assertFalse(nouvelle_api.desactiver_maintenance_rao()["ok"])
        self.assertTrue(nouvelle_api.attestation_maintenance_rao()["maintenance"])
        self.assertTrue(nouvelle_api.desactiver_maintenance_rao(True, "Contrôle Pi5 fictif du test")["ok"])
        self.assertFalse(nouvelle_api.attestation_maintenance_rao()["maintenance"])
        self.assertIsNotNone(nouvelle_api.attestation_maintenance_rao()["activation"])

    def test_activation_pendant_transmission_ne_declare_pas_repos(self):
        task = self.task()

        def retour_tardif(*args, **kwargs):
            self.api.activer_maintenance_rao()
            instantane = self.attestation()
            self.assertFalse(instantane["aucune_task_anvil_active_confirmee"])
            self.assertEqual(instantane["etats_inconnus"][0]["raison"], "transmission")
            return task

        self.server.call.side_effect = retour_tardif
        self.assertIs(self.api.lancer_recherche_classique_rao()["task"], task)
        self.server.get_background_task.side_effect = None
        self.server.get_background_task.return_value = task
        self.assertFalse(self.attestation()["aucune_task_anvil_active_confirmee"])
        self.assertEqual(self.api.lancer_recherche_cpv_rao()["error"], "maintenance")
        self.assertEqual(self.server.call.call_count, 1)

    def test_erreur_de_transport_reste_inconnue_sans_retry(self):
        self.server.call.side_effect = self.server.TimeoutError("simulé")
        with self.assertRaises(self.server.TimeoutError):
            self.api.lancer_recherche_cpv_rao()
        resultat = self.attestation()
        self.assertFalse(resultat["aucune_task_anvil_active_confirmee"])
        self.assertEqual(resultat["etats_inconnus"][0]["raison"], "inconnue")
        self.assertEqual(self.server.call.call_count, 1)

    def test_task_absente_et_statuts_non_terminaux_ne_sont_pas_termines(self):
        self.server.call.side_effect = None
        self.server.call.return_value = self.task()
        self.api.lancer_recherche_classique_rao()
        self.assertFalse(self.attestation()["aucune_task_anvil_active_confirmee"])
        for statut in (None, "running", "missing", "inconnu", "completed", "failed", "killed"):
            self.server.get_background_task.side_effect = None
            self.server.get_background_task.return_value = self.task(statut)
            resultat = self.attestation()
            self.assertEqual(resultat["aucune_task_anvil_active_confirmee"], statut in ("completed", "failed", "killed"))
        self.assertFalse(resultat["gel_complet_pi5_verifie"])

    def test_liste_tasks_et_attestation_sans_ecriture(self):
        self.api.activer_maintenance_rao()
        avant = copy.deepcopy(self.globales.rows)
        self.server.list_background_tasks.return_value = [self.task()]
        self.assertFalse(self.attestation()["aucune_task_anvil_active_confirmee"])
        self.server.list_background_tasks.side_effect = self.server.TimeoutError()
        self.assertFalse(self.attestation()["aucune_task_anvil_active_confirmee"])
        self.assertEqual(self.globales.rows, avant)

    def test_activation_concurrente_a_la_lecture_signalee(self):
        self.server.list_background_tasks.side_effect = lambda **kwargs: (self.api.activer_maintenance_rao(), [])[1]
        resultat = self.attestation()
        self.assertFalse(resultat["instantane_stable"])
        self.assertFalse(resultat["aucune_task_anvil_active_confirmee"])

    def test_document_invalide_ou_duplique_nouvre_pas_la_barriere(self):
        self.globales.rows.append(Row(name=self.api._CLE_ETAT, value={"actif": "false"}))
        with self.assertRaises(ValueError):
            self.api.lancer_recherche_classique_rao()
        self.globales.rows.append(copy.deepcopy(self.globales.rows[0]))
        with self.assertRaises(RuntimeError):
            self.api.lancer_recherche_cpv_rao()
        self.server.call.assert_not_called()

    def test_formulaire_refus_classique_cpv_et_inscription(self):
        for mode, inscription_ok in (("classique", True), ("cpv", True), ("cpv", False)):
            preparation = search_support.TestsRechercheCPV()
            preparation.setUp()
            form = preparation.form
            if mode == "classique":
                form.cpv_selectionnes = []
                form.text_box_mots_obligatoires_cpv.text = "formation"
            refus = {"ok": False, "error": "maintenance", "message": "RAO en maintenance"}

            def transport(nom, *args, **kwargs):
                if nom == "enregistrer_recherche_rao" and inscription_ok:
                    return {"ok": True}
                if nom in ("lancer_recherche_classique_rao", "lancer_recherche_cpv_rao", "enregistrer_recherche_rao"):
                    return refus
                raise AssertionError("Appel non autorisé : " + nom)

            preparation.serveur.side_effect = transport
            form.lancer_recherche()
            self.assertFalse(form._recherche_en_cours)
            self.assertIsNone(form.task_recherche)
            self.assertEqual(form.timer_recherche_progress.interval, 0)
            self.assertTrue(form.f.navigation_link_search_go.enabled)
            alertes = preparation.espace["afficher_information"] if mode == "cpv" else preparation.espace["afficher_avertissement"]
            self.assertIn("maintenance", alertes.call_args.args[0])

    def test_formulaire_conserve_task_admise_dans_les_deux_modes(self):
        for mode in ("classique", "cpv"):
            preparation = search_support.TestsRechercheCPV()
            preparation.setUp()
            form = preparation.form
            if mode == "classique":
                form.cpv_selectionnes = []
                form.text_box_mots_obligatoires_cpv.text = "formation"
            task = Mock()

            def transport(nom, *args, **kwargs):
                if nom == "enregistrer_recherche_rao":
                    return {"ok": True}
                if nom in ("lancer_recherche_classique_rao", "lancer_recherche_cpv_rao"):
                    return {"ok": True, "task": task}
                raise AssertionError("Appel non autorisé : " + nom)

            preparation.serveur.side_effect = transport
            form.lancer_recherche()
            self.assertIs(form.task_recherche, task)
            self.assertTrue(form._recherche_en_cours)
            self.assertEqual(form.timer_recherche_progress.interval, 1)

    def test_veille_admise_avant_activation_termine_sans_ouvrir_autres_admissions(self):
        def ecrire_veille():
            self.api.activer_maintenance_rao()
            self.assertFalse(self.attestation()["aucune_task_anvil_active_confirmee"])
            return {"ok": True, "statut": "reactivee"}

        fonction = self.api.proteger_operation("veille_cpv")(ecrire_veille)
        self.assertTrue(fonction()["ok"])
        self.assertEqual(fonction()["error"], "maintenance")
        self.assertEqual(self.attestation()["operations"][0]["phase"], "terminee")


if __name__ == "__main__":
    unittest.main()
