#!/usr/bin/env python3
from datetime import datetime
from smartcard.System import readers
from smartcard.Exceptions import CardConnectionException
from smartcard.util import toHexString

# Même protocole que Lubiana
CLA_WALLET    = 0x82        # gestion du solde
INS_LIRE_SOLDE = 0x01       # 82 01 00 00 02 : lire_solde()
INS_DEBIT      = 0x03       # 82 03 00 00 02 : debit()

PRIX_BOISSON = 0.20         # 20 centimes


def ouvrir_lecteur():
    """Retourne une connexion vers la carte sur le premier lecteur disponible."""
    r = readers()
    if not r:
        print("Aucun lecteur PC/SC détecté.")
        return None

    print("Lecteurs disponibles :")
    for i, reader in enumerate(r):
        print(f"  {i}: {reader}")

    lecteur = r[0]
    print(f"\nUtilisation du lecteur 0 : {lecteur}")

    conn = lecteur.createConnection()
    try:
        conn.connect()
    except CardConnectionException as e:
        print(f"Impossible de se connecter à la carte : {e}")
        return None

    atr = conn.getATR()
    print(f"ATR : {toHexString(atr)}\n")
    return conn


def lire_solde(conn):
    """Lit le solde sur la carte avec 82 01 00 00 02, comme dans Lubiana."""
    apdu = [CLA_WALLET, INS_LIRE_SOLDE, 0x00, 0x00, 0x02]
    print(f"--> APDU lire solde : {toHexString(apdu)}")
    data, sw1, sw2 = conn.transmit(apdu)
    print(f"<-- Réponse : {toHexString(data)}  SW1 SW2 = {sw1:02X} {sw2:02X}")

    if sw1 != 0x90 or sw2 != 0x00 or len(data) != 2:
        print(f"Erreur lecture solde : SW1={sw1:02X}, SW2={sw2:02X}")
        return None

    montant_centimes = (data[0] << 8) | data[1]
    return montant_centimes / 100.0


def debiter(conn, montant_euros):
    """
    Débite la carte avec l'APDU 82 03 00 00 02 hi lo.
    C'est exactement l'exemple du sujet pour Lunar White, adapté à ta carte.
    """
    centimes = int(round(montant_euros * 100))
    hi = (centimes >> 8) & 0xFF
    lo = centimes & 0xFF

    apdu = [CLA_WALLET, INS_DEBIT, 0x00, 0x00, 0x02, hi, lo]
    print(f"--> APDU débit : {toHexString(apdu)}")
    data, sw1, sw2 = conn.transmit(apdu)
    print(f"<-- Réponse : {toHexString(data)}  SW1 SW2 = {sw1:02X} {sw2:02X}")

    if sw1 == 0x90 and sw2 == 0x00:
        # Débit accepté
        return True
    elif sw1 == 0x61:
        # Dans le TP, 61 xx sert souvent pour "solde insuffisant" ou "capacité max"
        print("Solde insuffisant ou condition non satisfaite (61 xx).")
        return False
    else:
        print(f"Erreur débit : SW1={sw1:02X}, SW2={sw2:02X}")
        return False


def log_transaction(nom_boisson, prix, solde_initial, solde_final, statut):
    with open("log.txt", "a") as f:
        f.write(
            f"date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"boisson: {nom_boisson} | "
            f"prix: {prix:.2f}€ | "
            f"solde_initial: {solde_initial:.2f}€ | "
            f"solde_final: {solde_final:.2f}€ | "
            f"statut: {statut}\n"
        )


def afficher_menu(solde):
    print("")
    print("===== Machine à café - Lunar White =====")
    print(f"Solde de la carte : {solde:.2f} euros")
    print("----------------------------------------")
    print("Choisissez votre boisson :")
    print("1 - Café (0.20 €)")
    print("2 - Thé (0.20 €)")
    print("3 - Chocolat chaud (0.20 €)")
    print("4 - Annuler / Quitter")


def commander_boisson(conn, nom_boisson, prix):
    solde = lire_solde(conn)
    if solde is None:
        print("Impossible de lire le solde, opération annulée.")
        return

    if solde < prix:
        print(f"Solde insuffisant ({solde:.2f} €). Boisson non servie.")
        # log refus solde insuffisant
        log_transaction(nom_boisson, prix, solde, solde, "REFUS_SOLDE")
        return

    print(f"Tentative de débit de {prix:.2f} € pour un {nom_boisson}...")
    if debiter(conn, prix):
        nouveau_solde = lire_solde(conn)
        print("Boisson servie. Merci !")
        if nouveau_solde is not None:
            print(f"Nouveau solde : {nouveau_solde:.2f} €")
            # log succès
            log_transaction(nom_boisson, prix, solde, nouveau_solde, "OK")
        else:
            # on log quand même, même si on n'a pas pu relire le solde
            log_transaction(nom_boisson, prix, solde, solde - prix, "OK_SOLDE_INCONNU")
    else:
        print("Débit refusé. Boisson non servie.")
        # log autre refus (erreur APDU, etc.)
        log_transaction(nom_boisson, prix, solde, solde, "REFUS_AUTRE")




def main():
    conn = ouvrir_lecteur()
    if conn is None:
        return

    try:
        while True:
            solde = lire_solde(conn)
            if solde is None:
                print("Impossible de lire le solde, arrêt de la machine.")
                break

            afficher_menu(solde)
            choix = input("Votre choix : ").strip()

            if choix == "1":
                commander_boisson(conn, "café", PRIX_BOISSON)
            elif choix == "2":
                commander_boisson(conn, "thé", PRIX_BOISSON)
            elif choix == "3":
                commander_boisson(conn, "chocolat chaud", PRIX_BOISSON)
            elif choix == "4":
                print("Opération annulée. Au revoir.")
                break
            else:
                print("Choix invalide.")

    except KeyboardInterrupt:
        print("\nArrêt de la machine (Ctrl+C).")
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()


