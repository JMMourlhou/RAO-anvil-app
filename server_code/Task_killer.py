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