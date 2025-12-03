def afficher_menu():
    print("==== LUBIANA ====")
    print("1. Afficher version carte")
    print("2. Afficher données carte")
    print("3. Attribuer la carte")
    print("4. Créditer la carte (solde initial)")
    print("5. Lire le solde")
    print("0. Quitter")


def main():
    while True:
        afficher_menu()
        choix = input("Choix : ")

        if choix == "1":
            print("Lecture version (à implémenter)")
        elif choix == "2":
            print("Lecture données (à implémenter)")
        elif choix == "3":
            print("Attribution carte (à implémenter)")
        elif choix == "4":
            print("Crédit initial (à implémenter)")
        elif choix == "5":
            print("Lecture solde (à implémenter)")
        elif choix == "0":
            print("Au revoir")
            break
        else:
            print("Choix invalide")

#!/usr/bin/env python3
"""
Client de personnalisation : Lubiana.

Fonctionnalités :
- Afficher la version de la carte
- Afficher les données de la carte (personnalisation)
- Attribuer la carte (écrire la personnalisation)
- Mettre le solde initial (1.00 €)
- Consulter le solde
"""
from smartcard.System import readers
from smartcard.Exceptions import CardConnectionException
from smartcard.util import toHexString

# Classes et instructions conformes au sujet
CLA_PERSO  = 0x81  # personnalisation
CLA_WALLET = 0x82  # gestion du solde

INS_VERSION     = 0x00  # 81 00 00 00 04 : version()
INS_INTRO_PERSO = 0x01  # 81 01 00 00 P3 : intro_perso()
INS_LIRE_PERSO  = 0x02  # 81 02 00 00 P3 : lire_perso()

INS_LIRE_SOLDE  = 0x01  # 82 01 00 00 02 : lire_solde()
INS_CREDIT      = 0x02  # 82 02 00 00 02 : credit()
INS_DEBIT       = 0x03  # 82 03 00 00 02 : debit()

MAX_PERSO = 32



# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def select_first_reader():
    """Retourne une connexion vers la carte sur le premier lecteur disponible."""
    r = readers()
    if not r:
        print("Aucun lecteur PC/SC détecté.")
        return None

    print("Lecteurs disponibles :")
    for i, reader in enumerate(r):
        print(f"  {i}: {reader}")

    reader = r[0]
    print(f"\nUtilisation du lecteur 0 : {reader}")

    connection = reader.createConnection()
    try:
        # On laisse PC/SC choisir le protocole (T=0/T=1)
        connection.connect()
    except CardConnectionException as e:
        print(f"Impossible de se connecter à la carte : {e}")
        return None

    atr = connection.getATR()
    print(f"ATR : {toHexString(atr)}\n")
    return connection



def send_apdu(connection, cla, ins, p1=0x00, p2=0x00, data=None, le=None):
    """
    Envoie une APDU et retourne (resp_data, sw1, sw2).
    data est une liste d'octets (ou None).
    le est soit None, soit un entier (longueur attendue).
    """
    apdu = [cla, ins, p1, p2]

    if data is None:
        data = []

    if len(data) > 0:
        apdu.append(len(data))  # P3 = Lc
        apdu.extend(data)
        if le is not None:
            # Cas APDU avec Lc et Le : rare dans notre TP, on ne le gère pas ici
            raise ValueError("APDU Lc+Le non utilisée dans ce TP")
    else:
        if le is not None:
            apdu.append(le)  # P3 = Le
        else:
            apdu.append(0)   # P3 = 0

    print(f"--> APDU : {toHexString(apdu)}")

    resp, sw1, sw2 = connection.transmit(apdu)
    print(f"<-- Réponse : {toHexString(resp)}  SW1 SW2 = {sw1:02X} {sw2:02X}")

    return resp, sw1, sw2


def parse_sw(sw1, sw2):
    """Retourne un message lisible pour SW1/SW2."""
    if sw1 == 0x90 and sw2 == 0x00:
        return "OK (90 00)"

    if sw1 == 0x6C:
        return f"Taille incorrecte, taille attendue = {sw2}"

    if sw1 == 0x61:
        # Dans ton TP, 61 00 est utilisé pour capacité max ou solde insuffisant
        return f"Condition non satisfaite (61 {sw2:02X})"

    if sw1 == 0x6D:
        return "INS inconnu (6D XX)"

    if sw1 == 0x6E:
        return "Classe (CLA) inconnue (6E XX)"

    return f"Code SW inconnu : {sw1:02X} {sw2:02X}"


# ---------------------------------------------------------------------------
# Fonctions métier (version, perso, solde, crédit, débit)
# ---------------------------------------------------------------------------

def get_version(connection):
    resp, sw1, sw2 = send_apdu(connection, CLA_PERSO, INS_VERSION,
                               p1=0, p2=0, data=None, le=4)
    print(parse_sw(sw1, sw2))
    if sw1 == 0x90 and sw2 == 0x00:
        # resp contient les octets ASCII de "1.00"
        version_str = "".join(chr(b) for b in resp)
        print(f"Version de la carte : {version_str}")
    print()


def intro_perso(connection):
    name = input("Nom à écrire dans la carte (max 32 caractères) : ").strip()
    data = name.encode("ascii", errors="ignore")
    if len(data) == 0:
        print("Nom vide, opération annulée.\n")
        return
    if len(data) > MAX_PERSO:
        print(f"Nom trop long (>{MAX_PERSO}), il sera tronqué.")
        data = data[:MAX_PERSO]

    resp, sw1, sw2 = send_apdu(connection, CLA_PERSO, INS_INTRO_PERSO,
                               p1=0, p2=0, data=list(data), le=None)
    print(parse_sw(sw1, sw2))
    print()


def lire_perso(connection):
    print("Lecture de la personnalisation (tentative 1, P3=0)...")
    resp, sw1, sw2 = send_apdu(connection, CLA_PERSO, INS_LIRE_PERSO,
                               p1=0, p2=0, data=None, le=0)
    msg = parse_sw(sw1, sw2)
    print(msg)

    if sw1 == 0x6C:
        taille = sw2
        print(f"Nouvelle tentative avec taille = {taille}...")
        resp, sw1, sw2 = send_apdu(connection, CLA_PERSO, INS_LIRE_PERSO,
                                   p1=0, p2=0, data=None, le=taille)
        print(parse_sw(sw1, sw2))
        if sw1 == 0x90 and sw2 == 0x00:
            name = "".join(chr(b) for b in resp)
            print(f"Nom stocké dans la carte : {name}")
    elif sw1 == 0x90 and sw2 == 0x00:
        name = "".join(chr(b) for b in resp)
        print(f"Nom stocké dans la carte : {name}")

    print()


def lire_solde(connection):
    # APDU : 82 01 00 00 02
    resp, sw1, sw2 = send_apdu(connection, CLA_WALLET, INS_LIRE_SOLDE,
                               p1=0, p2=0, data=None, le=2)
    print(parse_sw(sw1, sw2))
    if sw1 == 0x90 and sw2 == 0x00 and len(resp) == 2:
        # big-endian, comme dans bourse.c
        montant = (resp[0] << 8) | resp[1]
        euros = montant / 100.0
        print(f"Solde : {montant} centimes ({euros:.2f} €)")
    print()


def mettre_solde_initial(connection):
    # Lecture du solde actuel
    resp, sw1, sw2 = send_apdu(connection, CLA_WALLET, INS_LIRE_SOLDE,
                               p1=0, p2=0, data=None, le=2)
    solde = (resp[0] << 8) | resp[1]

    cible = 100
    diff = cible - solde

    # Si diff > 0 → CREDIT, si diff < 0 → DEBIT
    if diff != 0:
        op = INS_CREDIT if diff > 0 else INS_DEBIT
        diff = abs(diff)
        data = [diff >> 8, diff & 0xFF]
        send_apdu(connection, CLA_WALLET, op, p1=0, p2=0, data=data, le=None)

    print("Solde ajusté à 1.00 €.\n")




# ---------------------------------------------------------------------------
# Boucle principale (menu)
# ---------------------------------------------------------------------------

def menu(connection):
    """Boucle principale de dialogue avec la carte."""
    while True:
        print("---------------------------------------------")
        print("-- Logiciel de personnalisation : Lubiana --")
        print("---------------------------------------------")
        print("1. Afficher la version de carte")
        print("2. Afficher les données de la carte")
        print("3. Attribuer la carte")
        print("4. Mettre le solde initial")
        print("5. Consulter le solde")
        print("6. Quitter")
        choice = input("Votre choix : ").strip()

        try:
            if choice == "1":
                # Afficher la version de la carte
                get_version(connection)

            elif choice == "2":
                # Afficher les données de la carte (personnalisation)
                lire_perso(connection)

            elif choice == "3":
                # Attribuer la carte (écriture de la personnalisation)
                intro_perso(connection)

            elif choice == "4":
                # Mettre le solde initial (1.00 €)
                mettre_solde_initial(connection)

            elif choice == "5":
                # Consulter le solde
                lire_solde(connection)

            elif choice == "6":
                print("Au revoir.")
                break

            else:
                print("Choix incorrect.\n")

        except CardConnectionException:
            
            pass

        except Exception as e:
            # Là seulement on affiche un vrai message d'erreur Python
            print(f"[ERREUR INTERNE] {e}\n")



def main():
    # On se connecte au lecteur une fois
    connection = select_first_reader()
    if connection is None:
        print("Impossible de se connecter à la carte. Vérifie le lecteur / la carte.")
        return

    try:
        menu(connection)   # <-- reste dans le menu tant que tu ne choisis pas "Quitter"
    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur (Ctrl+C).")
    finally:
        try:
            connection.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    main()