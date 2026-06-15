import anvil.server


@anvil.server.callable
def task_killer_by_id(task_id=None, timing=None):
    """
    Tue une background task Anvil à partir de son ID.
    """

    if not task_id:
        return {
            "ok": False,
            "message": "Aucun task_id fourni"
        }

    try:
        task = anvil.server.get_background_task(task_id)

        if task.is_running():
            task.kill()
            status = task.get_termination_status()

            print()
            print(f"task id {task_id} killed")
            if timing is not None:
                print(f"Tps de traitement: {timing} secondes")
            print()

            return {
                "ok": True,
                "task_id": task_id,
                "status": status,
                "message": "Task tuée"
            }

        else:
            status = task.get_termination_status()

            return {
                "ok": True,
                "task_id": task_id,
                "status": status,
                "message": "Task déjà terminée"
            }

    except Exception as e:
        return {
            "ok": False,
            "task_id": task_id,
            "message": str(e)
        }
