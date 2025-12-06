#!/usr/bin/env python3
"""
Client de personnalisation : Lubiana (Version Corrigée)
Fonctionnalités :
- Gestion automatique du déblocage PUK (12345678)
- Gestion des erreurs de communication T=0
- Attribution et Solde
"""
from smartcard.System import readers
from smartcard.Exceptions import CardConnectionException
from smartcard.util import toHexString
import json
import os
import random
import time

# --- CONSTANTES ---
CLA_PERSO   = 0x81
CLA_WALLET  = 0x82
CLA_SEC     = 0x80

INS_VERSION     = 0x00
INS_INTRO_PERSO = 0x01
INS_LIRE_PERSO  = 0x02

INS_LIRE_SOLDE  = 0x01
INS_CREDIT      = 0x02
INS_DEBIT       = 0x03

INS_VERIFY_PIN  = 0x20
INS_UNLOCK_PUK  = 0x21
INS_SET_PIN     = 0x30

MAX_PERSO = 32
DEFAULT_PUK = [1, 2, 3, 4, 5, 6, 7, 8] # PUK codé en dur dans le C
PINS_FILE   = "pins.json"
CURRENT_ATR = None

# --- GESTION FICHIER PIN ---
def load_pins():
    if not os.path.exists(PINS_FILE): return {}
    try:
        with open(PINS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_pins(pins):
    with open(PINS_FILE, "w") as f: json.dump(pins, f, indent=2)

def get_stored_pin():
    global CURRENT_ATR
    if not CURRENT_ATR: return None
    return load_pins().get(CURRENT_ATR)

# --- FONCTIONS BAS NIVEAU ---
def select_reader():
    global CURRENT_ATR
    r = readers()
    if not r:
        print("Erreur: Aucun lecteur détecté.")
        return None
    
    connection = r[0].createConnection()
    try:
        connection.connect()
        CURRENT_ATR = toHexString(connection.getATR())
        print(f"Connecté au lecteur. ATR: {CURRENT_ATR}\n")
        return connection
    except Exception as e:
        print(f"Erreur connexion: {e}")
        return None

def send_apdu(connection, cla, ins, p1=0, p2=0, data=None, le=None):
    apdu = [cla, ins, p1, p2]
    if data:
        apdu.append(len(data))
        apdu.extend(data)
    else:
        apdu.append(le if le is not None else 0)
    
    try:
        resp, sw1, sw2 = connection.transmit(apdu)
        return resp, sw1, sw2
    except Exception as e:
        print(f"Erreur transmission APDU: {e}")
        return [], 0x00, 0x00

def parse_sw(sw1, sw2):
    if sw1 == 0x90: return "OK"
    if sw1 == 0x61: return f"Attention (61 {sw2:02X})"
    if sw1 == 0x6C: return f"Erreur Longueur (Attendu: {sw2})"
    if sw1 == 0x69 and sw2 == 0x83: return "BLOQUÉ"
    if sw1 == 0x69 and sw2 == 0x82: return "NON AUTHENTIFIÉ"
    if sw1 == 0x63: return f"Échec (Essais restants: {sw2})"
    return f"Erreur Inconnue ({sw1:02X} {sw2:02X})"

# --- FONCTIONS MÉTIER ---

def unblock_card(connection):
    """Débloque la carte avec le PUK par défaut"""
    print("\n--- DÉBLOCAGE DE LA CARTE ---")
    print(f"Utilisation du PUK par défaut : {DEFAULT_PUK}")
    resp, sw1, sw2 = send_apdu(connection, CLA_SEC, INS_UNLOCK_PUK, data=DEFAULT_PUK)
    
    if sw1 == 0x90:
        print("SUCCÈS : La carte est débloquée !")
        print("Les compteurs sont réinitialisés.")
        # On réinitialise la session PIN dans le script aussi, bien que la carte le fasse
        return True
    else:
        print(f"ÉCHEC du déblocage : {parse_sw(sw1, sw2)}")
        return False

def verify_pin_flow(connection):
    """Gère la vérification PIN et propose le déblocage si nécessaire"""
    pin = get_stored_pin()
    if not pin:
        pin = "0000"
        print("Aucun PIN enregistré, essai avec '0000'.")
    
    print(f"Vérification PIN ({pin})...")
    data_pin = [int(c) for c in pin]
    
    resp, sw1, sw2 = send_apdu(connection, CLA_SEC, INS_VERIFY_PIN, data=data_pin)
    
    if sw1 == 0x90:
        print("PIN Vérifié.")
        return True
    elif sw1 == 0x69 and sw2 == 0x83:
        print("CARTE BLOQUÉE !")
        choix = input("Voulez-vous tenter de la débloquer avec le PUK admin ? (o/n) : ")
        if choix.lower() == 'o':
            if unblock_card(connection):
                # Après un déblocage, il faut souvent refaire le verify ou on est considéré comme non-authentifié pour certaines ops
                # Mais unlock_with_puk dans le C remet session_pin_ok à 0.
                print("Carte débloquée. Veuillez réessayer l'opération.")
        return False
    else:
        print(f"Erreur PIN : {parse_sw(sw1, sw2)}")
        return False

def lire_nom(connection):
    # 1. Demander la taille (Le=0)
    resp, sw1, sw2 = send_apdu(connection, CLA_PERSO, INS_LIRE_PERSO, le=0)
    
    if sw1 == 0x6C:
        taille = sw2
        if taille == 0:
            print("Aucun nom enregistré (Taille 0).")
            return
        # 2. Lire la donnée
        resp, sw1, sw2 = send_apdu(connection, CLA_PERSO, INS_LIRE_PERSO, le=taille)
    
    if sw1 == 0x90:
        # Filtrer les caractères non imprimables (cas où l'eeprom est sale)
        nom = "".join([chr(x) for x in resp if 32 <= x <= 126])
        print(f"Nom sur la carte : {nom}")
    else:
        print(f"Impossible de lire le nom : {parse_sw(sw1, sw2)}")

def ecrire_nom(connection):
    nom = input("Entrez le nouveau nom : ").strip()
    data = [ord(c) for c in nom[:MAX_PERSO]]
    resp, sw1, sw2 = send_apdu(connection, CLA_PERSO, INS_INTRO_PERSO, data=data)
    print(f"Résultat : {parse_sw(sw1, sw2)}")

def lire_solde(connection):
    resp, sw1, sw2 = send_apdu(connection, CLA_WALLET, INS_LIRE_SOLDE, le=2)
    
    if sw1 == 0x69 and sw2 == 0x83:
        print("Lecture impossible : Carte bloquée.")
        if input("Débloquer ? (o/n) ").lower() == 'o':
            unblock_card(connection)
        return

    if sw1 == 0x90:
        val = (resp[0] << 8) | resp[1]
        print(f"Solde actuel : {val/100:.2f} €")
    else:
        print(f"Erreur lecture solde : {parse_sw(sw1, sw2)}")

def set_pin_interaction(connection):
    if not verify_pin_flow(connection):
        return

    new_pin_str = f"{random.randint(0,9999):04d}"
    print(f"Génération nouveau PIN : {new_pin_str}")
    data = [int(c) for c in new_pin_str]
    
    resp, sw1, sw2 = send_apdu(connection, CLA_SEC, INS_SET_PIN, data=data)
    
    if sw1 == 0x90:
        print("PIN modifié avec succès sur la carte.")
        pins = load_pins()
        pins[CURRENT_ATR] = new_pin_str
        save_pins(pins)
        print("PIN sauvegardé dans pins.json")
    else:
        print(f"Erreur changement PIN : {parse_sw(sw1, sw2)}")

def mettre_solde(connection):
    if not verify_pin_flow(connection): return
    
    # Lire solde d'abord
    resp, sw1, sw2 = send_apdu(connection, CLA_WALLET, INS_LIRE_SOLDE, le=2)
    if sw1 != 0x90: return
    current = (resp[0] << 8) | resp[1]
    
    target = 100 # 1.00 euro
    diff = target - current
    
    if diff == 0:
        print("Solde déjà à 1.00 €")
        return
        
    op = INS_CREDIT if diff > 0 else INS_DEBIT
    val = abs(diff)
    data = [val >> 8, val & 0xFF]
    
    resp, sw1, sw2 = send_apdu(connection, CLA_WALLET, op, data=data)
    print(f"Mise à jour solde : {parse_sw(sw1, sw2)}")

# --- MENU ---
def main():
    conn = select_reader()
    if not conn: return

    while True:
        print("\n--- LUBIANA ---")
        print("1. Version")
        print("2. Lire Nom")
        print("3. Écrire Nom")
        print("4. Mettre Solde à 1€")
        print("5. Consulter Solde")
        print("6. Nouveau PIN")
        print("7. Débloquer Carte (Force)")
        print("8. Quitter")
        
        c = input("Choix : ")
        
        try:
            if c == '1':
                resp, sw1, sw2 = send_apdu(conn, CLA_PERSO, INS_VERSION, le=4)
                if sw1==0x90: print(f"Version: {''.join(chr(x) for x in resp)}")
            elif c == '2': lire_nom(conn)
            elif c == '3': ecrire_nom(conn)
            elif c == '4': mettre_solde(conn)
            elif c == '5': lire_solde(conn)
            elif c == '6': set_pin_interaction(conn)
            elif c == '7': unblock_card(conn)
            elif c == '8': break
        except Exception as e:
            print(f"Erreur critique: {e}")
            conn = select_reader() # Tentative reconnexion

if __name__ == "__main__":
    main()