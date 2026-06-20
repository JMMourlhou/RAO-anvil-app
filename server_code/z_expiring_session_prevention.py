import anvil.server

"""
D’après la documentation Anvil, une session Anvil reste ouverte tant qu’une opération a été faite dans les **30 dernières minutes**, pas 300 secondes.
Quand la session expire, la prochaine opération serveur déclenche le message **Session Expired**.
Une opération serveur peut être un `anvil.server.call()`,
une recherche dans une Data Table, ou tout autre échange avec le serveur.
"""

@anvil.server.callable
def ping():
    #print("Pong !")
    return "pong"
   
