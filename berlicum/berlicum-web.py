#!/usr/bin/env python3
import smartcard.System as scardsys
import smartcard.util as scardutil
import smartcard.Exceptions as scardexcp
import mysql.connector
from decimal import Decimal

from flask import Flask, request, jsonify, render_template_string

# ======================================================================
#  Constantes
# ======================================================================

DB_HOST = "localhost"
DB_USER = "rodelika"
DB_PASS = "R0deLika123!"
DB_NAME = "purpledragon"

TYPE_BONUS = "Bonus"
TYPE_BONUS_TRANSFER = "Bonus transféré"
TYPE_RECHARGE = "Recharge"

# ======================================================================
#  État global (lecteur + BDD)
# ======================================================================

conn_reader = None
db = None

# ======================================================================
#  CSS & HTML (design fourni)
# ======================================================================

COMMON_CSS = """
<style>
:root {
    --primary: #6a0dad;
    --primary-dark: #4b2e83;
    --primary-darker: #2e1a47;
    --accent: #ff6ec7;
    --bg-light: #f8f1ff;
    --bg-card: #ffffff;
    --text-dark: #2d1b3e;
    --text-light: #5a4a66;
    --border: #e0d0eb;
    --success: #28a745;
    --warning: #ffc107;
    --danger: #dc3545;
    --gray: #6c757d;
    --terminal-bg: #1e1e2e;
    --terminal-text: #cdd6f4;
    --terminal-green: #a6e3a1;
    --terminal-yellow: #f9e2af;
    --terminal-red: #f38ba8;
    --terminal-purple: #cba6f7;
}

@media (prefers-color-scheme: dark) {
    :root {
        --bg-light: #0f0a15;
        --bg-card: #181123;
        --text-dark: #e6e1ff;
        --text-light: #b9a9d9;
        --border: #3a2a5d;
        --terminal-bg: #11111b;
    }
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: linear-gradient(135deg, var(--bg-light), #e6daff);
    color: var(--text-dark);
    line-height: 1.6;
    padding: 20px;
    min-height: 100vh;
}
.container { max-width: 1000px; margin: 0 auto; }

/* Header */
.header {
    text-align: center;
    margin-bottom: 2rem;
}
.logo {
    font-size: 3.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, var(--primary), #8a4fff);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin-bottom: 0.5rem;
}
.subtitle {
    color: var(--text-light);
    font-size: 1.2rem;
}

/* Card */
.card {
    background: var(--bg-card);
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(106, 13, 173, 0.15);
    padding: 2rem;
    margin-bottom: 2rem;
    transition: all 0.3s ease;
}
.card-title {
    font-size: 1.8rem;
    color: var(--primary-darker);
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 12px;
}
.card-title::before {
    content: "";
    display: inline-block;
    width: 6px;
    height: 24px;
    background: var(--primary);
    border-radius: 3px;
}

/* Buttons grid */
.btn-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
    margin: 1.5rem 0;
}
.btn {
    background: var(--bg-card);
    border: 2px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    font-weight: 600;
    color: var(--primary-darker);
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
}
.btn:hover {
    transform: translateY(-4px);
    border-color: var(--primary);
    box-shadow: 0 6px 15px rgba(106, 13, 173, 0.2);
    color: var(--primary);
}
.btn i { font-size: 1.6rem; }

/* Terminal */
.terminal {
    background: var(--terminal-bg);
    border-radius: 12px;
    padding: 1.2rem;
    font-family: 'Fira Code', 'Courier New', monospace;
    color: var(--terminal-text);
    overflow: auto;
    max-height: 400px;
    white-space: pre-wrap;
    tab-size: 4;
    border: 1px solid var(--border);
}
.terminal-line { margin: 4px 0; }
.cmd { color: var(--terminal-purple); }
.resp { color: var(--terminal-green); }
.sw-ok { color: var(--terminal-green); font-weight: bold; }
.sw-err { color: var(--terminal-red); font-weight: bold; }
.sw-warn { color: var(--terminal-yellow); }
.info { color: var(--terminal-text); }

/* Status bar */
.status {
    display: flex;
    justify-content: space-between;
    padding: 12px;
    background: var(--bg-card);
    border-radius: 12px;
    border: 1px solid var(--border);
    font-weight: 500;
}
@media (max-width: 768px) {
    .btn-grid { grid-template-columns: 1fr; }
    .logo { font-size: 2.4rem; }
    .status { flex-direction: column; gap: 8px; text-align: center; }
}
</style>
"""

HTML_TEMPLATE = f"""
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Berlicum — Borne de Recharge NFC</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  {COMMON_CSS}
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="logo">BERLICUM</h1>
      <p class="subtitle">Borne de recharge et gestion des bonus — Interface Web</p>
    </div>

    <div class="card">
      <h2 class="card-title"><i class="fas fa-charging-station"></i> Actions disponibles</h2>
      <div class="btn-grid">
        <button class="btn" onclick="sendCommand('infos')">
          <i class="fas fa-id-card"></i>
          <span>Infos carte</span>
        </button>
        <button class="btn" onclick="sendCommand('bonus')">
          <i class="fas fa-gift"></i>
          <span>Consulter bonus</span>
        </button>
        <button class="btn" onclick="sendCommand('transferer')">
          <i class="fas fa-exchange-alt"></i>
          <span>Transférer bonus</span>
        </button>
        <button class="btn" onclick="sendCommand('solde')">
          <i class="fas fa-wallet"></i>
          <span>Solde carte</span>
        </button>
        <button class="btn" onclick="rechargerCB()">
          <i class="fas fa-credit-card"></i>
          <span>Recharger par CB</span>
        </button>
        <button class="btn" onclick="clearTerminal()" style="border-color: #6c757d;">
          <i class="fas fa-trash"></i>
          <span>Effacer</span>
        </button>
      </div>

      <div class="status">
        <span>🔌 Carte : <span id="card-status">Inconnu</span></span>
        <span>💾 Base : <span id="db-status">Inconnu</span></span>
        <span>🌐 État : <span id="global-status">En attente</span></span>
      </div>
    </div>

    <div class="card">
      <h2 class="card-title"><i class="fas fa-terminal"></i> Journal des opérations</h2>
      <div class="terminal" id="terminal-output">
        <div class="terminal-line info">Bienvenue sur la borne Berlicum Web.</div>
        <div class="terminal-line info">Insérez votre carte à puce pour commencer.</div>
      </div>
    </div>
  </div>

  <script>
    const terminal = document.getElementById('terminal-output');
    const cardStatus = document.getElementById('card-status');
    const dbStatus = document.getElementById('db-status');
    const globalStatus = document.getElementById('global-status');

    function log(text, className = 'info') {{
        const div = document.createElement('div');
        div.className = `terminal-line ${{className}}`;
        div.textContent = text;
        terminal.appendChild(div);
        terminal.scrollTop = terminal.scrollHeight;
    }}

    function clearTerminal() {{
        terminal.innerHTML = '<div class="terminal-line info">Terminal vidé.</div>';
    }}

    function updateStatus() {{
        fetch('/api/status')
            .then(r => r.json())
            .then(data => {{
                cardStatus.textContent = data.card;
                cardStatus.style.color = data.card === 'OK' ? 'var(--success)' : 'var(--danger)';
                
                dbStatus.textContent = data.db;
                dbStatus.style.color = data.db === 'OK' ? 'var(--success)' : 'var(--danger)';
                
                globalStatus.textContent = data.global;
                globalStatus.style.color = 
                    data.global === 'Prêt' ? 'var(--success)' :
                    data.global === 'Attention' ? 'var(--warning)' : 'var(--danger)';
            }})
            .catch(() => {{
                cardStatus.textContent = 'Erreur';
                dbStatus.textContent = 'Erreur';
                globalStatus.textContent = 'Erreur';
            }});
    }}

    async function sendCommand(cmd) {{
        try {{
            globalStatus.textContent = 'En cours...';
            globalStatus.style.color = 'var(--warning)';

            const response = await fetch('/api/command', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ command: cmd }})
            }});

            const data = await response.json();

            if (data.log) {{
                data.log.forEach(line => {{
                    const type = line.type || 'info';
                    if (type === 'info') log(line.text, 'info');
                    else if (type === 'error') log(`[ERREUR] ${{line.text}}`, 'sw-err');
                }});
            }}
            if (data.error) {{
                log(`[ERREUR] ${{data.error}}`, 'sw-err');
            }}
        }} catch (e) {{
            log(`[ERREUR RÉSEAU] ${{e.message}}`, 'sw-err');
        }} finally {{
            updateStatus();
        }}
    }}

    async function rechargerCB() {{
        const montant = prompt("Montant à recharger (en euros, ex: 2.50) :");
        if (montant === null) return;
        if (montant.trim() === "") {{
            log("[ERREUR] Montant vide.", 'sw-err');
            return;
        }}

        try {{
            globalStatus.textContent = 'Paiement CB...';
            globalStatus.style.color = 'var(--warning)';

            const response = await fetch('/api/command', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ command: 'recharger', montant: montant }})
            }});

            const data = await response.json();

            if (data.log) {{
                data.log.forEach(line => {{
                    const type = line.type || 'info';
                    if (type === 'info') log(line.text, 'info');
                    else if (type === 'error') log(`[ERREUR] ${{line.text}}`, 'sw-err');
                }});
            }}
            if (data.error) {{
                log(`[ERREUR] ${{data.error}}`, 'sw-err');
            }}
        }} catch (e) {{
            log(`[ERREUR] ${{e.message}}`, 'sw-err');
        }} finally {{
            updateStatus();
        }}
    }}

    document.addEventListener('DOMContentLoaded', () => {{
        updateStatus();
        setInterval(updateStatus, 3000);
    }});
  </script>
</body>
</html>
"""

# ======================================================================
#  Helpers BDD & Carte (adaptés pour le Web)
# ======================================================================

def init_db(log=None):
    """Assure une connexion DB globale."""
    global db
    if db is not None:
        try:
            if db.is_connected():
                return True
        except Exception:
            db = None

    try:
        db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        if log is not None:
            log.append({"type": "info", "text": "Connexion base de données OK."})
        return True
    except Exception as e:
        if log is not None:
            log.append({"type": "error", "text": f"Connexion BDD échouée : {e}"})
        db = None
        return False


def init_smart_card(log=None):
    """Assure une connexion globale au lecteur/carte."""
    global conn_reader
    if conn_reader is not None:
        return True

    try:
        r = scardsys.readers()
        if not r:
            if log is not None:
                log.append({"type": "error", "text": "Aucun lecteur de carte détecté."})
            return False

        conn_reader = r[0].createConnection()
        conn_reader.connect()

        atr = scardutil.toHexString(conn_reader.getATR())
        if log is not None:
            log.append({"type": "info", "text": f"Lecteur connecté ({r[0]}), ATR: {atr}"})
        return True

    except scardexcp.NoCardException as e:
        if log is not None:
            log.append({"type": "error", "text": f"Aucune carte insérée : {e}"})
        conn_reader = None
        return False
    except Exception as e:
        if log is not None:
            log.append({"type": "error", "text": f"Erreur lecteur : {e}"})
        conn_reader = None
        return False


def send_apdu(apdu):
    """Envoie une APDU brute et retourne (data, sw1, sw2)."""
    data, sw1, sw2 = conn_reader.transmit(apdu)
    return data, sw1, sw2


def lire_personnalisation(log=None):
    """
    Lit les données de personnalisation de la carte (CLA=0x81, INS=0x02).
    Format: "3;Nom;Prenom" par ex.
    """
    # 1ère requête : P3 = 0 → juste pour connaître la taille
    apdu = [0x81, 0x02, 0x00, 0x00, 0x00]
    try:
        data, sw1, sw2 = send_apdu(apdu)
    except Exception as e:
        if log is not None:
            log.append({"type": "error", "text": f"Erreur APDU perso (1ère étape) : {e}"})
        return None

    if sw1 == 0x6C:  # longueur attendue dans sw2
        length = sw2
        apdu[4] = length
        try:
            data, sw1, sw2 = send_apdu(apdu)
        except Exception as e:
            if log is not None:
                log.append({"type": "error", "text": f"Erreur APDU perso (2ème étape) : {e}"})
            return None

    if sw1 != 0x90 or sw2 != 0x00:
        if log is not None:
            log.append({"type": "error",
                        "text": f"Erreur lecture perso (SW1={sw1:02X}, SW2={sw2:02X})"})
        return None

    try:
        text = "".join(chr(b) for b in data)
        if log is not None:
            log.append({"type": "info", "text": f"Données de personnalisation: {text}"})
    except Exception:
        text = None
    return text


def extraire_num_etudiant_depuis_perso(perso):
    """
    On suppose que la personnalisation commence par le numéro d'étudiant en ASCII,
    par ex: "3;Nom;Prenom". On lit les chiffres au début de la chaîne.
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


def get_etu_num(log):
    """
    Récupère le numéro d'étudiant à partir de la carte.
    (En Web, pas de saisie clavier : si perso absente ou mal formée, on renvoie None.)
    """
    if not init_smart_card(log):
        return None

    perso = lire_personnalisation(log)
    if perso is None:
        log.append({"type": "error", "text": "Impossible de lire la personnalisation de la carte."})
        return None

    etu_num = extraire_num_etudiant_depuis_perso(perso)
    if etu_num is None:
        log.append({"type": "error",
                    "text": "Numéro d'étudiant introuvable dans la personnalisation (format attendu: 'ID;Nom;Prénom')."})
        return None

    log.append({"type": "info", "text": f"Numéro d'étudiant détecté: {etu_num}"})
    return etu_num


def lire_solde_centimes(log):
    """
    Lit le solde de la carte (en centimes) via APDU:
      CLA=0x82, INS=0x01, P1=P2=0, P3=0x02
    Retourne un entier (centimes) ou None si erreur.
    """
    if not init_smart_card(log):
        return None

    apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = send_apdu(apdu)
    except Exception as e:
        log.append({"type": "error", "text": f"Erreur APDU lecture solde : {e}"})
        return None

    if sw1 != 0x90 or sw2 != 0x00 or len(data) != 2:
        log.append({"type": "error",
                    "text": f"Erreur lecture solde (SW1={sw1:02X}, SW2={sw2:02X})"})
        return None

    cents = (data[0] << 8) + data[1]
    log.append({"type": "info", "text": f"Solde brut lu (centimes) : {cents}"})
    return cents


def credit_carte_centimes(montant_centimes, log):
    """
    Crédite la carte d'un montant en centimes via APDU credit:
      CLA=0x82, INS=0x02, P3=0x02, Data=montant (MSB,LSB)
    Retourne True si OK, False sinon.
    """
    if not init_smart_card(log):
        return False

    if montant_centimes <= 0 or montant_centimes > 0xFFFF:
        log.append({"type": "error",
                    "text": "Montant de crédit invalide (doit être >0 et <=65535 centimes)."})
        return False

    msb = (montant_centimes >> 8) & 0xFF
    lsb = montant_centimes & 0xFF
    apdu = [0x82, 0x02, 0x00, 0x00, 0x02, msb, lsb]

    try:
        data, sw1, sw2 = send_apdu(apdu)
    except Exception as e:
        log.append({"type": "error", "text": f"Erreur APDU crédit : {e}"})
        return False

    if sw1 == 0x90 and sw2 == 0x00:
        log.append({"type": "info",
                    "text": f"Crédit sur la carte effectué ({montant_centimes} centimes)."})
        return True

    if sw1 == 0x61:
        log.append({"type": "error",
                    "text": "Capacité maximale de la carte dépassée (SW=61xx)."})
    else:
        log.append({"type": "error",
                    "text": f"Erreur crédit carte (SW1={sw1:02X}, SW2={sw2:02X})"})
    return False

# ======================================================================
#  Actions Berlicum (retournent une liste de logs pour l'interface Web)
# ======================================================================

def action_infos():
    log = []

    if not init_db(log):
        return log

    etu_num = get_etu_num(log)
    if etu_num is None:
        return log

    # Récupération Nom/Prénom
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT etu_nom, etu_prenom FROM Etudiant WHERE etu_num = %s",
            (etu_num,)
        )
        row = cursor.fetchone()
        cursor.close()

        if row:
            nom, prenom = row
            log.append({"type": "info", "text": f"Étudiant {etu_num} : {prenom} {nom}"})
        else:
            log.append({"type": "error",
                        "text": "Étudiant introuvable dans la base (table Etudiant)."})
    except Exception as e:
        log.append({"type": "error", "text": f"Erreur DB (infos carte) : {e}"})

    return log


def action_bonus():
    log = []

    if not init_db(log):
        return log

    etu_num = get_etu_num(log)
    if etu_num is None:
        return log

    try:
        cursor = db.cursor()

        # Nombre total de bonus gagnés (Bonus + Bonus transféré)
        sql_total = """
            SELECT COUNT(*)
            FROM Compte
            WHERE etu_num = %s
              AND type_operation IN (%s, %s)
        """
        cursor.execute(sql_total, (etu_num, TYPE_BONUS, TYPE_BONUS_TRANSFER))
        row = cursor.fetchone()
        nb_total = row[0] if row is not None else 0

        # Bonus disponibles (type_operation = 'Bonus')
        sql_dispo = """
            SELECT COALESCE(COUNT(*), 0) AS nb_dispo,
                   COALESCE(SUM(opr_montant), 0) AS montant_dispo
            FROM Compte
            WHERE etu_num = %s
              AND type_operation = %s
        """
        cursor.execute(sql_dispo, (etu_num, TYPE_BONUS))
        row = cursor.fetchone()
        cursor.close()

        nb_dispo = row[0] if row is not None else 0
        if row is not None and row[1] is not None:
            montant_dispo = Decimal(str(row[1]))
        else:
            montant_dispo = Decimal("0.00")

        log.append({"type": "info", "text": f"Étudiant : {etu_num}"})
        log.append({"type": "info",
                    "text": f"Nombre total de bonus gagnés      : {nb_total}"})
        log.append({"type": "info",
                    "text": f"Nombre de bonus encore disponibles: {nb_dispo}"})
        log.append({"type": "info",
                    "text": f"Montant de bonus disponibles      : {montant_dispo:.2f} €"})

    except Exception as e:
        log.append({"type": "error", "text": f"Erreur DB (bonus) : {e}"})

    return log


def action_transferer():
    log = []

    if not init_db(log):
        return log

    etu_num = get_etu_num(log)
    if etu_num is None:
        return log

    try:
        db.start_transaction()
        cursor = db.cursor()

        # Total des bonus non transférés
        sql_total = """
            SELECT COALESCE(SUM(opr_montant), 0)
            FROM Compte
            WHERE etu_num = %s
              AND type_operation = %s
        """
        cursor.execute(sql_total, (etu_num, TYPE_BONUS))
        row = cursor.fetchone()
        if row is not None and row[0] is not None:
            total = Decimal(str(row[0]))
        else:
            total = Decimal("0.00")

        if total <= Decimal("0.00"):
            log.append({"type": "info", "text": "Aucun bonus à transférer."})
            db.rollback()
            cursor.close()
            return log

        total_str = f"{total:.2f}"   # ex: "2.00"
        cents = int(total_str.replace(".", ""))

        log.append({"type": "info",
                    "text": f"Transfert de {total:.2f} € sur la carte (soit {cents} centimes)..."})

        # Crédit carte
        ok = credit_carte_centimes(cents, log)
        if not ok:
            log.append({"type": "error",
                        "text": "Échec du crédit sur la carte, annulation en base."})
            db.rollback()
            cursor.close()
            return log

        # Mise à jour des lignes Bonus -> Bonus transféré
        sql_update = """
            UPDATE Compte
            SET type_operation = %s
            WHERE etu_num = %s
              AND type_operation = %s
        """
        cursor.execute(sql_update, (TYPE_BONUS_TRANSFER, etu_num, TYPE_BONUS))
        nb_lignes = cursor.rowcount

        db.commit()
        cursor.close()

        log.append({"type": "info",
                    "text": f"Transfert effectué : {total:.2f} € crédités, "
                            f"{nb_lignes} ligne(s) passée(s) en '{TYPE_BONUS_TRANSFER}'."})

    except Exception as e:
        db.rollback()
        log.append({"type": "error", "text": f"Erreur lors du transfert de bonus : {e}"})

    return log


def action_solde():
    log = []

    cents = lire_solde_centimes(log)
    if cents is None:
        return log

    euros = cents / 100.0
    log.append({"type": "info",
                "text": f"Solde actuel de la carte : {euros:.2f} €"})
    return log


def action_recharger(montant_str):
    log = []

    if not init_db(log):
        return log

    etu_num = get_etu_num(log)
    if etu_num is None:
        return log

    # Parsing du montant
    if montant_str is None:
        log.append({"type": "error", "text": "Montant non fourni."})
        return log

    montant_str = montant_str.replace(",", ".").strip()
    try:
        montant = Decimal(montant_str)
        if montant <= 0:
            log.append({"type": "error",
                        "text": "Le montant doit être strictement positif."})
            return log
    except Exception:
        log.append({"type": "error",
                    "text": f"Montant invalide : '{montant_str}'."})
        return log

    log.append({"type": "info",
                "text": f"Simulation paiement CB de {montant:.2f} €..."})

    montant_str2 = f"{montant:.2f}"
    cents = int(montant_str2.replace(".", ""))

    # Crédit sur la carte
    if not credit_carte_centimes(cents, log):
        log.append({"type": "error",
                    "text": "Crédit sur la carte échoué, la recharge n'est pas enregistrée en base."})
        return log

    # Enregistrement en base
    try:
        cursor = db.cursor()
        sql = """
            INSERT INTO Compte (etu_num, opr_date, opr_montant, opr_libelle, type_operation)
            VALUES (%s, NOW(), %s, %s, %s)
        """
        libelle = "Recharge Berlicum"
        cursor.execute(sql, (etu_num, montant, libelle, TYPE_RECHARGE))
        db.commit()
        cursor.close()

        log.append({"type": "info",
                    "text": f"Recharge de {montant:.2f} € enregistrée pour l'étudiant {etu_num}."})
    except Exception as e:
        db.rollback()
        log.append({"type": "error", "text": f"Erreur DB (recharge) : {e}"})

    return log

# ======================================================================
#  Flask app & routes
# ======================================================================

app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/status")
def api_status():
    # État DB
    db_ok = init_db()
    db_status = "OK" if db_ok else "Erreur"

    # État Lecteur
    try:
        r = scardsys.readers()
        card_status = "OK" if r else "Aucun lecteur"
    except Exception:
        card_status = "Erreur"

    if db_status == "OK" and card_status == "OK":
        global_st = "Prêt"
    elif db_status == "OK" or card_status == "OK":
        global_st = "Attention"
    else:
        global_st = "Erreur"

    return jsonify({"card": card_status, "db": db_status, "global": global_st})


@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json(force=True)
    cmd = data.get("command")
    montant = data.get("montant", "")
    log = []

    try:
        if cmd == "infos":
            log = action_infos()
        elif cmd == "bonus":
            log = action_bonus()
        elif cmd == "transferer":
            log = action_transferer()
        elif cmd == "solde":
            log = action_solde()
        elif cmd == "recharger":
            log = action_recharger(montant)
        else:
            log = [{"type": "error", "text": f"Commande inconnue : {cmd}"}]
    except Exception as e:
        log.append({"type": "error", "text": f"Exception serveur : {e}"})

    return jsonify({"log": log})


if __name__ == "__main__":
    print("🚀 BERLICUM Web démarré.")
    print("🌍 Accessible sur : http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
