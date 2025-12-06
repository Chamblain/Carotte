#!/usr/bin/env python3
import time
from datetime import datetime
from decimal import Decimal

from smartcard.System import readers
from smartcard.Exceptions import CardConnectionException
from smartcard.util import toHexString

import mysql.connector
from mysql.connector import Error

from flask import Flask, request, jsonify, render_template_string

# ====================== Constantes ======================

# Carte (même protocole que Lubiana)
CLA_WALLET     = 0x82
INS_LIRE_SOLDE = 0x01   # 82 01 00 00 02
INS_DEBIT      = 0x03   # 82 03 00 00 02

PRIX_BOISSON = Decimal("0.20")     # 0.20 €

# BDD
DB_HOST = "localhost"
DB_USER = "rodelika"
DB_PASS = "R0deLika123!"
DB_NAME = "purpledragon"

# État global
conn_reader = None
db = None

# ====================== CSS / HTML ======================

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
.badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 999px;
    border: 1px solid var(--border);
    font-size: 0.85rem;
    background: rgba(106, 13, 173, 0.05);
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
  <title>Lunar White — Machine à café NFC</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  {COMMON_CSS}
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="logo">LUNAR WHITE</h1>
      <p class="subtitle">Machine à café NFC — Débit & traçabilité</p>
    </div>

    <div class="card">
      <h2 class="card-title"><i class="fas fa-mug-hot"></i> Actions disponibles</h2>
      <div class="btn-grid">
        <button class="btn" onclick="sendCommand('solde')">
          <i class="fas fa-wallet"></i>
          <span>Consulter solde</span>
        </button>
        <button class="btn" onclick="sendCommand('cafe')">
          <i class="fas fa-coffee"></i>
          <span>Café (0,20 €)</span>
        </button>
        <button class="btn" onclick="sendCommand('the')">
          <i class="fas fa-mug-saucer"></i>
          <span>Thé (0,20 €)</span>
        </button>
        <button class="btn" onclick="sendCommand('chocolat')">
          <i class="fas fa-ice-cream"></i>
          <span>Chocolat chaud (0,20 €)</span>
        </button>
        <button class="btn" onclick="chooseStudent()">
          <i class="fas fa-id-card"></i>
          <span>Choisir étudiant</span>
        </button>
        <button class="btn" onclick="clearTerminal()" style="border-color: #6c757d;">
          <i class="fas fa-trash"></i>
          <span>Effacer</span>
        </button>
      </div>

      <div class="status">
        <span>🔌 Carte : <span id="card-status">Inconnu</span></span>
        <span>💾 Base : <span id="db-status">Inconnu</span></span>
        <span>👤 Étudiant : <span id="etu-badge" class="badge">non choisi</span></span>
        <span>🌐 État : <span id="global-status">En attente</span></span>
      </div>
    </div>

    <div class="card">
      <h2 class="card-title"><i class="fas fa-terminal"></i> Journal des opérations</h2>
      <div class="terminal" id="terminal-output">
        <div class="terminal-line info">Bienvenue sur Lunar White Web.</div>
        <div class="terminal-line info">Insérez votre carte et choisissez un étudiant pour commencer.</div>
      </div>
    </div>
  </div>

  <script>
    let etuNum = null;

    const terminal = document.getElementById('terminal-output');
    const cardStatus = document.getElementById('card-status');
    const dbStatus = document.getElementById('db-status');
    const globalStatus = document.getElementById('global-status');
    const etuBadge = document.getElementById('etu-badge');

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

    function chooseStudent() {{
        const val = prompt("Numéro d'étudiant :");
        if (val === null) return;
        const trimmed = val.trim();
        if (!/^[0-9]+$/.test(trimmed)) {{
            log("[ERREUR] Numéro d'étudiant invalide.", 'sw-err');
            return;
        }}
        etuNum = parseInt(trimmed, 10);
        etuBadge.textContent = etuNum;
        etuBadge.style.color = 'var(--success)';
        log("Étudiant courant: " + trimmed, "info");
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
        // Pour les boissons, on impose d'avoir un étudiant
        if ((cmd === 'cafe' || cmd === 'the' || cmd === 'chocolat') && (etuNum === null)) {{
            log("[ERREUR] Choisissez d'abord un numéro d'étudiant.", 'sw-err');
            return;
        }}

        try {{
            globalStatus.textContent = 'En cours...';
            globalStatus.style.color = 'var(--warning)';

            const payload = {{ command: cmd }};
            if (etuNum !== null) payload.etu_num = etuNum;

            const response = await fetch('/api/command', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload)
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

    document.addEventListener('DOMContentLoaded', () => {{
        updateStatus();
        setInterval(updateStatus, 3000);
    }});
  </script>
</body>
</html>
"""

# ====================== BDD helpers ======================

def init_db(log=None):
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
    except Error as e:
        if log is not None:
            log.append({"type": "error", "text": f"Connexion BDD échouée : {e}"})
        db = None
        return False


def enregistrer_depense_db(etu_num, nom_boisson, prix, log):
    if not init_db(log):
        log.append({"type": "error", "text": "Impossible d'enregistrer la dépense en base (pas de BDD)."})
        return

    try:
        cur = db.cursor()
        sql = """
            INSERT INTO Compte (etu_num, opr_date, opr_montant, opr_libelle, type_operation)
            VALUES (%s, NOW(), %s, %s, %s)
        """
        montant_negatif = -abs(prix)
        cur.execute(sql, (etu_num, float(montant_negatif), nom_boisson, "Depense"))
        db.commit()
        cur.close()
        log.append({"type": "info", "text": "Dépense enregistrée en base de données."})
    except Error as e:
        log.append({"type": "error", "text": f"Erreur lors de l'insertion en BDD : {e}"})


# ====================== Carte helpers ======================

def init_smart_card(log=None):
    global conn_reader
    if conn_reader is not None:
        return True

    try:
        r = readers()
        if not r:
            if log is not None:
                log.append({"type": "error", "text": "Aucun lecteur PC/SC détecté."})
            return False

        lecteur = r[0]
        conn = lecteur.createConnection()
        conn.connect()
        conn_reader = conn

        atr = conn_reader.getATR()
        if log is not None:
            log.append({"type": "info", "text": f"Lecteur connecté ({lecteur}), ATR: {toHexString(atr)}"})
        return True

    except CardConnectionException as e:
        if log is not None:
            log.append({"type": "error", "text": f"Impossible de se connecter à la carte : {e}"})
        conn_reader = None
        return False
    except Exception as e:
        if log is not None:
            log.append({"type": "error", "text": f"Erreur lecteur : {e}"})
        conn_reader = None
        return False


def lire_solde(log):
    if not init_smart_card(log):
        return None

    apdu = [CLA_WALLET, INS_LIRE_SOLDE, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except Exception as e:
        log.append({"type": "error", "text": f"Erreur APDU lire solde : {e}"})
        return None

    log.append({"type": "info", "text": f"--> APDU lire solde : {toHexString(apdu)}"})
    log.append({"type": "info", "text": f"<-- Réponse : {toHexString(data)}  SW1 SW2 = {sw1:02X} {sw2:02X}"})

    if sw1 != 0x90 or sw2 != 0x00 or len(data) != 2:
        log.append({"type": "error", "text": f"Erreur lecture solde : SW1={sw1:02X}, SW2={sw2:02X}"})
        return None

    montant_centimes = (data[0] << 8) | data[1]
    return Decimal(montant_centimes) / Decimal(100)


def debiter(montant_euros, log):
    if not init_smart_card(log):
        return False

    centimes = int(round(float(montant_euros) * 100))
    hi = (centimes >> 8) & 0xFF
    lo = centimes & 0xFF
    apdu = [CLA_WALLET, INS_DEBIT, 0x00, 0x00, 0x02, hi, lo]

    log.append({"type": "info", "text": f"--> APDU débit : {toHexString(apdu)}"})

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except Exception as e:
        log.append({"type": "error", "text": f"Erreur APDU débit : {e}"})
        return False

    log.append({"type": "info", "text": f"<-- Réponse : {toHexString(data)}  SW1 SW2 = {sw1:02X} {sw2:02X}"})

    if sw1 == 0x90 and sw2 == 0x00:
        return True
    elif sw1 == 0x61:
        log.append({"type": "error", "text": "Solde insuffisant ou condition non satisfaite (61 xx)."})
        return False
    else:
        log.append({"type": "error", "text": f"Erreur débit : SW1={sw1:02X}, SW2={sw2:02X}"})
        return False


# ====================== Actions ======================

def action_solde():
    log = []
    solde = lire_solde(log)
    if solde is None:
        return log
    log.append({"type": "info", "text": f"Solde actuel de la carte : {solde:.2f} €"})
    return log


def action_boisson(etu_num, nom_boisson):
    log = []

    if etu_num is None:
        log.append({"type": "error", "text": "Étudiant non fourni."})
        return log

    solde = lire_solde(log)
    if solde is None:
        log.append({"type": "error", "text": "Impossible de lire le solde, opération annulée."})
        return log

    if solde < PRIX_BOISSON:
        log.append({"type": "error",
                    "text": f"Solde insuffisant ({solde:.2f} €). Boisson non servie."})
        return log

    log.append({"type": "info",
                "text": f"Tentative de débit de {PRIX_BOISSON:.2f} € pour un {nom_boisson}..."})

    if debiter(PRIX_BOISSON, log):
        # Animation "texte"
        etapes = ["[■□□□□]", "[■■□□□]", "[■■■□□]", "[■■■■□]", "[■■■■■]"]
        for e in etapes:
            log.append({"type": "info", "text": f"Préparation {nom_boisson} {e}"})
            # sur le web on évite time.sleep trop longs, on garde petit
            time.sleep(0.1)

        nouveau_solde = lire_solde(log)
        log.append({"type": "info", "text": f"Boisson servie : {nom_boisson}."})
        if nouveau_solde is not None:
            log.append({"type": "info",
                        "text": f"Nouveau solde : {nouveau_solde:.2f} €"})
        # Enregistrement en BDD (même si on n'a pas pu relire le solde)
        enregistrer_depense_db(etu_num, nom_boisson, PRIX_BOISSON, log)
    else:
        log.append({"type": "error", "text": "Débit refusé. Boisson non servie."})

    return log


# ====================== Flask ======================

app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/status")
def api_status():
    # DB
    db_ok = init_db()
    db_status = "OK" if db_ok else "Erreur"

    # Lecteur
    try:
        r = readers()
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
    etu_num = data.get("etu_num", None)

    if isinstance(etu_num, str) and etu_num.isdigit():
        etu_num = int(etu_num)
    elif not isinstance(etu_num, int):
        etu_num = None

    log = []

    try:
        if cmd == "solde":
            log = action_solde()
        elif cmd == "cafe":
            log = action_boisson(etu_num, "café")
        elif cmd == "the":
            log = action_boisson(etu_num, "thé")
        elif cmd == "chocolat":
            log = action_boisson(etu_num, "chocolat chaud")
        else:
            log = [{"type": "error", "text": f"Commande inconnue : {cmd}"}]
    except Exception as e:
        log.append({"type": "error", "text": f"Exception serveur : {e}"})

    return jsonify({"log": log})


if __name__ == "__main__":
    print("🚀 LUNAR WHITE Web démarré.")
    print("🌍 Accessible sur : http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
