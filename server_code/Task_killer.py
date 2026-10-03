import anvil.server
import time


@anvil.server.callable
def task_killer(task=None, timing="0"):
    if task is None:
        return {
            "ok": False,
            "message": "Aucune task fournie"
        }

    try:
        task_id = task.get_id()

        if task.is_running():
            task.kill()

            # Petite pause pour laisser Anvil mettre à jour le statut
            time.sleep(0.2)

            try:
                status = task.get_termination_status()
            except Exception:
                status = None

            print()
            print(f"task id {task_id} killed")
            print(f"status après kill : {status}")
            if timing != "0":
                print(f"Tps de traitement: {timing} secondes")
            print()

            return {
                "ok": True,
                "task_id": task_id,
                "status": status or "kill_requested",
                "message": "Task tuée"
            }

        else:
            status = task.get_termination_status()

            print()
            print(f"task id {task_id} non tuée : déjà terminée")
            print(f"status: {status}")
            print()

            return {
                "ok": True,
                "task_id": task_id,
                "status": status,
                "message": "Task déjà terminée"
            }

    except Exception as e:
        return {
            "ok": False,
            "message": str(e)
        }


@anvil.server.callable
def statut_tache_recherche(task):
    """Lit le statut Anvil d'une Task sans modifier son exécution.

    Paramètre : objet Task transmis par le client.
    Retour : None, completed, failed, killed ou missing.
    Les arguments invalides et erreurs de lecture lèvent une exception.
    """
    if task is None:
        raise ValueError("Aucune Task fournie.")

    lire_statut = getattr(task, "get_termination_status", None)
    if not callable(lire_statut):
        raise TypeError("L'objet fourni ne permet pas de lire un statut de Task.")

    return lire_statut()
