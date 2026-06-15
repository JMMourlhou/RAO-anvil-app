import anvil.server

@anvil.server.callable
def task_killer(task, timing="0"):
    task_id = task.get_id()
    task.kill()
    print()
    print(f"task id {task_id} killed")
    if timing != "0":
        print(f"Tps de traitement: {timing} secondes")
    print()
