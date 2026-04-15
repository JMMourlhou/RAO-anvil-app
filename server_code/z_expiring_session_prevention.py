import anvil.server

@anvil.server.callable
def ping():
    print("pong")
    return "pong"
   
