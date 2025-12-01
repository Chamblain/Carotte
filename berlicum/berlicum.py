import smartcard.System as scardsys
import smartcard.util as scardutil
import smartcard.Exceptions as scardexcp
import mysql.connector
from decimal import Decimal

conn_reader = None
db = None

# -----------------------------------------
# Connexion au lecteur de carte
# -----------------------------------------
def init_smart_card():
    global conn_reader
    try:
        readers = scardsys.readers()
        if not readers:
            print("Aucun lecteur détecté.")
            exit(1)

        conn_reader = readers[0].createConnection()
        conn_reader.connect()

        print("Lecteur OK.")
        print("ATR :", scardutil.toHexString(conn_reader.getATR()))

    except scardexcp.NoCardException as e:
        print("Pas de carte dans le lecteur :", e)
        exit(1)
    except Exception as e:
        print("Erreur lecteur :", e)
        exit(1)

# -----------------------------------------
# Connexion à la base PurpleDragon
# -----------------------------------------
def init_db():
    global db
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="rodelika",
            password="R0deLika123!",
            database="purpledragon"
        )
        print("Connexion DB OK.")
    except Exception as e:
        print("Erreur DB :", e)
        exit(1)

# -----------------------------------------
# APDU helpers
# -----------------------------------------
def send_apdu(apdu):
    """Envoie une APDU brute et retourne (data, sw1, sw2)."""
    data, sw1, sw2 = conn_reader.transmit(apdu)
    return data, sw1, sw2

# -----------------------------------------
# Helpers carte / BDD
# -----------------------------------------
def lire_personnalisation():
    """
    Lit les données de personnalisation de la carte (CLA=0x81, INS=0x02).

    Pattern classique du sujet :
      1) APDU avec P3=0 pour récupérer la taille (sw1=0x6C, sw2=taille)
      2) APDU avec P3=taille pour récupérer les données.
    """
    # 1ère requête : P3 = 0 → juste pour connaître la taille
    apdu = [0x81, 0x02, 0x00, 0x00, 0x00]
    data, sw1, sw2 = send_apdu(apdu)

    if sw1 == 0x6C:  # longueur attendue dans sw2
        length = sw2
        apdu[4] = length
        data, sw1, sw2 = send_apdu(apdu)

    if sw1 != 0x90 or sw2 != 0x00:
        print(f"Erreur lecture perso (SW1={sw1:02X}, SW2={sw2:02X})")
        return None

    try:
        text = "".join(chr(b) for b in data)
    except Exception:
        text = None
    return text

def extraire_num_etudiant_depuis_perso(perso):
    """
    On suppose que la personnalisation commence par le numéro d'étudiant en ASCII,
    suivi d'un séparateur éventuel (ex: "1;Thompson;Allan").
    On lit les chiffres au début de la chaîne.
    """
    if not perso:
        return None

    digits = []
    for ch in perso:
        if ch.isdigit():
            digits.append(ch)
        else:
            break

    if not digits:
        return None

    try:
        return int("".join(digits))
    except ValueError:
        return None

def get_etu_num():
    """
    Récupère le numéro d'étudiant à partir de la carte.
    Si impossible, demande à l'utilisateur de le saisir.
    """
    perso = lire_personnalisation()
    if perso is not None:
        etu_num = extraire_num_etudiant_depuis_perso(perso)
        if etu_num is not None:
            return etu_num

    # Fallback : demande manuelle
    while True:
        saisie = input("Numéro d'étudiant (saisi manuellement) : ").strip()
        if saisie.isdigit():
            return int(saisie)
        print("Numéro invalide, recommence.")

def lire_solde_centimes():
    """
    Lit le solde de la carte (en centimes) via APDU:
      CLA=0x82, INS=0x01, P1=P2=0, P3=0x02
    Retourne un entier (centimes) ou None si erreur.
    """
    apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
    data, sw1, sw2 = send_apdu(apdu)

    if sw1 != 0x90 or sw2 != 0x00 or len(data) != 2:
        print(f"Erreur lecture solde (SW1={sw1:02X}, SW2={sw2:02X})")
        return None

    # big-endian: MSB, LSB (comme dans le C)
    return (data[0] << 8) + data[1]

def credit_carte_centimes(montant_centimes):
    """
    Crédite la carte d'un montant en centimes via APDU credit:
      CLA=0x82, INS=0x02, P3=0x02, Data=montant (MSB,LSB)
    Retourne True si OK, False sinon.
    """
    if montant_centimes <= 0 or montant_centimes > 0xFFFF:
        print("Montant de crédit invalide (doit tenir sur 2 octets).")
        return False

    msb = (montant_centimes >> 8) & 0xFF
    lsb = montant_centimes & 0xFF
    apdu = [0x82, 0x02, 0x00, 0x00, 0x02, msb, lsb]

    data, sw1, sw2 = send_apdu(apdu)
    if sw1 == 0x90 and sw2 == 0x00:
        return True

    if sw1 == 0x61:  # capacité max dépassée côté carte
        print("Capacité maximale de la carte dépassée.")
    else:
        print(f"Erreur crédit carte (SW1={sw1:02X}, SW2={sw2:02X})")
    return False

# -----------------------------------------
# FONCTIONS DE BERLICUM
# -----------------------------------------

def afficher_infos_carte():
    """
    Affiche les informations personnelles stockées sur la carte
    + celles de la table Etudiant si l'etu_num existe.
    """
    perso = lire_personnalisation()
    if perso is None:
        print("Impossible de lire les informations de la carte.")
        return

    etu_num = extraire_num_etudiant_depuis_perso(perso)
    print("------ Informations carte ------")

    if etu_num is not None:
        print(f"Numéro d'étudiant (déduit de la carte) : {etu_num}")

        # Affiche nom/prénom si présents dans la BDD
        cursor = db.cursor()
        cursor.execute(
            "SELECT etu_nom, etu_prenom FROM Etudiant WHERE etu_num = %s",
            (etu_num,)
        )
        row = cursor.fetchone()
        cursor.close()

        if row:
            nom, prenom = row
            print(f"Nom  : {nom}")
            print(f"Prénom : {prenom}")
        else:
            print("Étudiant introuvable dans la base.")

        # Le reste de la personnalisation brute (après le numéro)
        reste = perso[len(str(etu_num)):]
        if reste.startswith(";"):
            reste = reste[1:]
        if reste:
            print(f"Données perso brutes : {reste}")
    else:
        print(f"Données perso brutes : {perso}")

    print("--------------------------------")

def consulter_bonus():
    """
    Consulte les bonus attribués mais non encore transférés.

    Avec la BDD fournie :
      - table Compte
      - champ type_operation
      - valeur 'Bonus' pour les bonus initiaux
      - valeur 'Bonus transfere' quand ils sont transférés
    """
    etu_num = get_etu_num()
    cursor = db.cursor()

    sql = """
        SELECT COALESCE(SUM(opr_montant), 0)
        FROM Compte
        WHERE etu_num = %s
          AND type_operation = 'Bonus'
    """
    cursor.execute(sql, (etu_num,))
    row = cursor.fetchone()
    cursor.close()

    total = row[0] if row is not None else Decimal("0.00")
    print(f"Bonus disponibles pour l'étudiant {etu_num} : {total:.2f} €")

def transferer_bonus():
    """
    Transfère les bonus disponibles sur la carte ET marque en base
    qu'ils sont transférés ('Bonus' -> 'Bonus transfere').

    Avec la structure fournie :
      - Type(type_operation)
      - valeurs : 'Bonus', 'Recharge', 'Depense', 'Bonus transfere'
    """
    etu_num = get_etu_num()
    cursor = db.cursor()

    try:
        db.start_transaction()

        # 1) Calcul du total des bonus non transférés
        sql_total = """
            SELECT COALESCE(SUM(opr_montant), 0)
            FROM Compte
            WHERE etu_num = %s
              AND type_operation = 'Bonus'
        """
        cursor.execute(sql_total, (etu_num,))
        row = cursor.fetchone()
        total = row[0] if row is not None else Decimal("0.00")

        if total is None or total <= Decimal("0.00"):
            print("Aucun bonus à transférer.")
            db.rollback()
            cursor.close()
            return

        # Conversion en centimes (on garde 2 décimales, comme DECIMAL(15,2))
        total_str = f"{total:.2f}"  # ex "1.00"
        cents = int(total_str.replace(".", ""))

        print(f"Transfert de {total:.2f} € sur la carte...")

        # 2) Crédit de la carte
        ok = credit_carte_centimes(cents)
        if not ok:
            print("Échec du crédit sur la carte, annulation en base.")
            db.rollback()
            cursor.close()
            return

        # 3) Mise à jour des lignes "Bonus" -> "Bonus transfere"
        sql_update = """
            UPDATE Compte
            SET type_operation = 'Bonus transfere'
            WHERE etu_num = %s
              AND type_operation = 'Bonus'
        """
        cursor.execute(sql_update, (etu_num,))
        db.commit()
        cursor.close()

        print("Transfert effectué et base de données mise à jour.")

    except Exception as e:
        db.rollback()
        cursor.close()
        print("Erreur lors du transfert de bonus :", e)

def consulter_solde_carte():
    """
    Lecture du solde via APDU 82 01.
    Affiche le solde en euros.
    """
    cents = lire_solde_centimes()
    if cents is None:
        print("Impossible de lire le solde de la carte.")
        return

    euros = cents / 100.0
    print(f"Solde actuel de la carte : {euros:.2f} €")

def recharger_cb():
    """
    Simulation d'un paiement par carte bancaire :
      - demande du montant
      - simulation de la validation CB
      - crédit de la carte via APDU 82 02
      - insertion d'une ligne 'Recharge' dans Compte
        (cohérent avec la table Type)
    """
    etu_num = get_etu_num()

    # Saisie du montant en euros
    while True:
        saisie = input("Montant à recharger (en euros, ex 2.50) : ").replace(",", ".").strip()
        try:
            montant = Decimal(saisie)
            if montant <= 0:
                print("Montant doit être strictement positif.")
                continue
            break
        except Exception:
            print("Montant invalide, recommence.")

    print(f"Simulation paiement CB de {montant:.2f} € ...")
    print("Traitement en cours... (simulation)")
    print("Paiement accepté.")

    # Conversion en centimes
    montant_str = f"{montant:.2f}"
    cents = int(montant_str.replace(".", ""))

    # Crédit carte
    if not credit_carte_centimes(cents):
        print("Le crédit sur la carte a échoué, la recharge n'est pas enregistrée en base.")
        return

    # Enregistrement en base : type_operation = 'Recharge'
    try:
        cursor = db.cursor()
        sql = """
            INSERT INTO Compte (etu_num, opr_date, opr_montant, opr_libelle, type_operation)
            VALUES (%s, NOW(), %s, %s, %s)
        """
        libelle = "Recharge Berlicum"
        type_op = "Recharge"
        cursor.execute(sql, (etu_num, montant, libelle, type_op))
        db.commit()
        cursor.close()
        print(f"Recharge de {montant:.2f} € enregistrée pour l'étudiant {etu_num}.")
    except Exception as e:
        db.rollback()
        print("Erreur lors de l'enregistrement de la recharge en base :", e)

# -----------------------------------------
# MENU
# -----------------------------------------
def afficher_menu():
    print("")
    print("====== BERLICUM - BORNE DE RECHARGE ======")
    print("1 - Afficher mes informations")
    print("2 - Consulter mes bonus")
    print("3 - Transférer mes bonus sur ma carte")
    print("4 - Consulter mon solde")
    print("5 - Recharger par CB")
    print("6 - Quitter")

# -----------------------------------------
# MAIN
# -----------------------------------------
def main():
    init_smart_card()
    init_db()

    while True:
        afficher_menu()
        choix = input("Choix : ").strip()

        if choix == "1":
            afficher_infos_carte()
        elif choix == "2":
            consulter_bonus()
        elif choix == "3":
            transferer_bonus()
        elif choix == "4":
            consulter_solde_carte()
        elif choix == "5":
            recharger_cb()
        elif choix == "6":
            print("Au revoir.")
            break
        else:
            print("Choix invalide.")

if __name__ == "__main__":
    main()
