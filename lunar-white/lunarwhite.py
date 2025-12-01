import smartcard.System as scardsys
import smartcard.util as scardutil
import smartcard.Exceptions as scardexcp

conn_reader = None
MODE_SIMULATION = False
solde_simulation_centimes = 200  # 2.00 € de base en mode simulation

def init_smart_card():
    global conn_reader, MODE_SIMULATION
    readers = scardsys.readers()
    if not readers:
        print("Aucun lecteur détecté -> MODE SIMULATION activé")
        MODE_SIMULATION = True
        return

    try:
        conn_reader = readers[0].createConnection()
        conn_reader.connect()
        print("Lecteur OK, ATR :", scardutil.toHexString(conn_reader.getATR()))
        MODE_SIMULATION = False
    except scardexcp.NoCardException as e:
        print("Pas de carte dans le lecteur :", e)
        print("Passage en MODE SIMULATION")
        MODE_SIMULATION = True
    except Exception as e:
        print("Erreur lecteur :", e)
        print("Passage en MODE SIMULATION")
        MODE_SIMULATION = True

def lire_solde():
    global solde_simulation_centimes

    if MODE_SIMULATION:
        # On travaille uniquement avec la variable globale
        return solde_simulation_centimes / 100.0

    # Mode réel : APDU 0x82 0x01 (lire solde, 2 octets)
    apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
    data, sw1, sw2 = conn_reader.transmit(apdu)
    if sw1 == 0x90 and sw2 == 0x00:
        solde_centimes = (data[0] << 8) + data[1]
        return solde_centimes / 100.0
    else:
        print(f"Erreur lecture solde : {sw1:02X} {sw2:02X}")
        return None

def debiter_carte(montant_euros):
    global solde_simulation_centimes

    centimes = int(montant_euros * 100)

    if MODE_SIMULATION:
        if solde_simulation_centimes < centimes:
            print("Solde insuffisant (simulation).")
            return False
        solde_simulation_centimes -= centimes
        print("Débit effectué (simulation).")
        return True

    # Mode réel : APDU 0x82 0x03 (débit)
    apdu = [
        0x82, 0x03, 0x00, 0x00, 0x02,
        (centimes >> 8) & 0xFF,
        centimes & 0xFF
    ]
    data, sw1, sw2 = conn_reader.transmit(apdu)

    if sw1 == 0x90 and sw2 == 0x00:
        return True
    elif sw1 == 0x61:
        print("Solde insuffisant sur la carte.")
        return False
    else:
        print(f"Erreur débit : {sw1:02X} {sw2:02X}")
        return False

def afficher_menu():
    print("")
    print("===== Machine à café - Lunar White =====")
    print("1 - Afficher le solde de la carte")
    print("2 - Café (0.20 €)")
    print("3 - Thé (0.20 €)")
    print("4 - Chocolat chaud (0.20 €)")
    print("5 - Quitter")

def commander_boisson(nom_boisson, prix):
    solde = lire_solde()
    if solde is None:
        return
    print(f"Solde actuel : {solde:.2f} €")

    if solde < prix:
        print("Solde insuffisant, opération annulée.")
        return

    if debiter_carte(prix):
        nouveau_solde = lire_solde()
        print(f"{nom_boisson} servi. Merci !")
        if nouveau_solde is not None:
            print(f"Nouveau solde : {nouveau_solde:.2f} €")

def main():
    init_smart_card()

    while True:
        afficher_menu()
        choix = input("Choix : ")

        if choix == "1":
            solde = lire_solde()
            if solde is not None:
                print(f"Solde actuel : {solde:.2f} €")

        elif choix == "2":
            commander_boisson("Café", 0.20)
        elif choix == "3":
            commander_boisson("Thé", 0.20)
        elif choix == "4":
            commander_boisson("Chocolat chaud", 0.20)
        elif choix == "5":
            print("Au revoir.")
            break
        else:
            print("Choix invalide.")

if __name__ == "__main__":
    main()


