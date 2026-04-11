import anvil.users
import re
import sys

def is_valid_email(email: str) -> bool:
    """
    Retourne True si email est au format user@domaine.tld :
    - local-part : lettres, chiffres, . _ % + -
    - domaine  : labels séparés par un seul point, chaque label :
        - commence et finit par lettre ou chiffre
        - peut contenir des tirets à l’intérieur
    - TLD d’au moins 2 lettres
    """
    pattern = (
        r"^[A-Za-z0-9._%+-]+"                              # local-part
        r"@"
        r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+"  # un ou plusieurs labels
        r"[A-Za-z]{2,}$"                                   # TLD
    )
    return re.fullmatch(pattern, email) is not None