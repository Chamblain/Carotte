#!/usr/bin/env python3
"""
BERLICUM Web — Borne de recharge NFC & gestion bonus
Correction : Formatage f-string, Verrouillage Threading, Reconnexion DB auto
Host : 0.0.0.0 (Accessible réseau)
"""

from flask import Flask, render_template_string, request, jsonify
import threading
import time
import sys
from decimal import Decimal

# --- Gestion smartcard ---
try:
    from smartcard.System import readers
    from smartcard.util import toHexString
    from smartcard.Exceptions import NoCardException, CardConnectionException
    SMARTCARD_AVAILABLE = True
except ImportError:
    SMARTCARD_AVAILABLE = False
    # Classes bouchons pour éviter les erreurs d'import
    class NoCardException(Exception): pass
    class CardConnectionException(Exception): pass

# --- Gestion base de données ---
try:
    import mysql.connector
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# --- Verrous pour gérer les accès concurrents (Thread-Safe) ---
scard_lock = threading.Lock()
db_lock = threading.Lock()

# --- Variable Globale DB ---
db_connection = None

# --- CSS (Design Rodelika/Lubiana) ---
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

# --- Template HTML (F-String corrigée : doubles accolades pour JS/CSS) ---
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

    function logAPDU(apdu) {{
        log(`--> APDU : ${{apdu}}`, 'cmd');
    }}

    function logResponse(resp, sw) {{
        log(`<-- Réponse : ${{resp}}  SW = ${{sw}}`, 'resp');
        if (sw === '90 00') {{
            log('✅ OK (90 00)', 'sw-ok');
        }} else if (sw.startsWith('6C')) {{
            log(`⚠️ Taille incorrecte : ${{sw}}`, 'sw-warn');
        }} else if (sw.startsWith('61')) {{
            log(`⚠️ Condition non satisfaite : ${{sw}}`, 'sw-warn');
        }} else {{
            log(`❌ Erreur : ${{sw}}`, 'sw-err');
        }}
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

    function clearTerminal() {{
        terminal.innerHTML = '<div class="terminal-line info">Terminal vidé.</div>';
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
                    if (line.type === 'apdu') logAPDU(line.text);
                    else if (line.type === 'resp') logResponse(line.resp, line.sw);
                    else if (line.type === 'info') log(line.text);
                    else if (line.type === 'error') log(`[ERREUR] ${{line.text}}`, 'sw-err');
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
                    if (line.type === 'apdu') logAPDU(line.text);
                    else if (line.type === 'resp') logResponse(line.resp, line.sw);
                    else if (line.type === 'info') log(line.text);
                    else if (line.type === 'error') log(`[ERREUR] ${{line.text}}`, 'sw-err');
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

# --- Helpers Système (Thread-Safe) ---

def get_db():
    """Récupère une connexion DB active ou tente de reconnecter."""
    global db_connection
    with db_lock:
        if not DB_AVAILABLE:
            return None
        
        try:
            if db_connection and db_connection.is_connected():
                db_connection.ping(reconnect=True, attempts=3, delay=1)
                return db_connection
        except:
            pass
            
        try:
            db_connection = mysql.connector.connect(
                host="localhost",
                user="rodelika",
                password="R0deLika123!",
                database="purpledragon",
                autocommit=False
            )
            return db_connection
        except Exception:
            return None

def send_apdu_safe(apdu):
    """Exécute un APDU de manière thread-safe (connexion unique par commande)."""
    if not SMARTCARD_AVAILABLE:
        return {"error": "Bibliothèque pyscard manquante"}

    with scard_lock:
        conn = None
        try:
            r_list = readers()
            if not r_list:
                return {"error": "Aucun lecteur détecté"}
            
            conn = r_list[0].createConnection()
            conn.connect()
            
            data, sw1, sw2 = conn.transmit(apdu)
            
            return {
                "apdu": toHexString(apdu),
                "resp": toHexString(data),
                "sw": f"{sw1:02X} {sw2:02X}",
                "success": (sw1 == 0x90 and sw2 == 0x00),
                "data": data
            }
        except Exception as e:
            return {"apdu": toHexString(apdu), "error": str(e), "sw": "ERREUR"}
        finally:
            if conn:
                try: conn.disconnect()
                except: pass

# --- Logique métier ---

def lire_personnalisation():
    apdu = [0x81, 0x02, 0x00, 0x00, 0x00]
    result = send_apdu_safe(apdu)
    
    if "error" in result:
        return None, [{"type": "error", "text": result["error"]}]
        
    log = [{"type": "apdu", "text": result["apdu"]}]
    log.append({"type": "resp", "resp": result.get("resp",""), "sw": result.get("sw","")})

    if result["sw"].startswith("6C"):
        length = int(result["sw"].split()[1], 16)
        apdu[4] = length
        result2 = send_apdu_safe(apdu)
        log.append({"type": "apdu", "text": result2["apdu"]})
        log.append({"type": "resp", "resp": result2.get("resp", ""), "sw": result2.get("sw", "")})
        result = result2

    if not result.get("success"):
        return None, log

    try:
        text = "".join(chr(b) for b in result["data"])
        return text, log
    except:
        log.append({"type": "error", "text": "Données illisibles"})
        return None, log

def extraire_num_etudiant_depuis_perso(perso):
    if not perso: return None
    digits = []
    for ch in perso:
        if ch.isdigit(): digits.append(ch)
        else: break
    if not digits: return None
    try: return int("".join(digits))
    except: return None

def lire_solde_centimes():
    apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
    result = send_apdu_safe(apdu)
    log = [{"type": "apdu", "text": result.get("apdu", "")}]
    
    if "error" in result:
        log.append({"type": "error", "text": result["error"]})
        return None, log

    log.append({"type": "resp", "resp": result.get("resp", ""), "sw": result.get("sw", "")})
    
    if result.get("success") and len(result.get("data", [])) == 2:
        val = (result["data"][0] << 8) + result["data"][1]
        return val, log
    return None, log

def credit_carte_centimes(montant_centimes):
    if not (0 < montant_centimes <= 0xFFFF):
        return False, [{"type": "error", "text": "Montant invalide"}]
    
    msb = (montant_centimes >> 8) & 0xFF
    lsb = montant_centimes & 0xFF
    apdu = [0x82, 0x02, 0x00, 0x00, 0x02, msb, lsb]
    
    result = send_apdu_safe(apdu)
    log = [{"type": "apdu", "text": result.get("apdu", "")}]
    
    if "error" in result:
        log.append({"type": "error", "text": result["error"]})
        return False, log

    log.append({"type": "resp", "resp": result.get("resp", ""), "sw": result.get("sw", "")})
    return result.get("success"), log

# --- Actions API ---

def action_infos():
    perso, log = lire_personnalisation()
    if perso is None: return log

    etu_num = extraire_num_etudiant_depuis_perso(perso)
    log.append({"type": "info", "text": "------ Informations carte ------"})

    if etu_num is not None:
        log.append({"type": "info", "text": f"Numéro étudiant : {etu_num}"})
        db = get_db()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT etu_nom, etu_prenom FROM Etudiant WHERE etu_num = %s", (etu_num,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    log.append({"type": "info", "text": f"Identité : {row[0]} {row[1]}"})
                else:
                    log.append({"type": "info", "text": "Inconnu en base de données"})
            except Exception as e:
                log.append({"type": "error", "text": f"Erreur SQL : {e}"})
        
        reste = perso[len(str(etu_num)):]
        if reste.startswith(";"): reste = reste[1:]
        if reste: log.append({"type": "info", "text": f"Données supp : {reste}"})
    else:
        log.append({"type": "info", "text": f"Données brutes : {perso}"})
    
    return log

def action_bonus():
    perso, _ = lire_personnalisation()
    etu_num = extraire_num_etudiant_depuis_perso(perso) if perso else None
    
    if etu_num is None:
        return [{"type": "error", "text": "Numéro étudiant illisible"}]
    
    db = get_db()
    if not db:
        return [{"type": "error", "text": "Base de données inaccessible"}]
    
    try:
        cursor = db.cursor()
        cursor.execute("SELECT COALESCE(SUM(opr_montant), 0) FROM Compte WHERE etu_num = %s AND type_operation = 'Bonus'", (etu_num,))
        row = cursor.fetchone()
        cursor.close()
        total = Decimal(row[0]) if row else Decimal("0.00")
        return [{"type": "info", "text": f"Bonus disponibles : {total:.2f} €"}]
    except Exception as e:
        return [{"type": "error", "text": f"Erreur SQL : {e}"}]

def action_transferer():
    perso, log = lire_personnalisation()
    etu_num = extraire_num_etudiant_depuis_perso(perso) if perso else None
    
    if etu_num is None:
        return log + [{"type": "error", "text": "Numéro étudiant illisible"}]
    
    db = get_db()
    if not db:
        return log + [{"type": "error", "text": "Base de données inaccessible"}]
    
    try:
        cursor = db.cursor()
        cursor.execute("SELECT COALESCE(SUM(opr_montant), 0) FROM Compte WHERE etu_num = %s AND type_operation = 'Bonus'", (etu_num,))
        row = cursor.fetchone()
        total = Decimal(row[0]) if row else Decimal("0.00")
        
        if total <= 0:
            cursor.close()
            log.append({"type": "info", "text": "Aucun bonus à transférer"})
            return log
            
        cents = int(total * 100)
        ok, credit_log = credit_carte_centimes(cents)
        log.extend(credit_log)
        
        if ok:
            cursor.execute("UPDATE Compte SET type_operation = 'Bonus transfere' WHERE etu_num = %s AND type_operation = 'Bonus'", (etu_num,))
            db.commit()
            log.append({"type": "info", "text": f"✅ Transfert réussi : {total:.2f} €"})
        else:
            log.append({"type": "error", "text": "Échec écriture carte, base non débitée"})
            
        cursor.close()
        return log
    except Exception as e:
        if db: db.rollback()
        return log + [{"type": "error", "text": f"Erreur Transaction : {e}"}]

def action_solde():
    solde, log = lire_solde_centimes()
    if solde is not None:
        log.append({"type": "info", "text": f"💰 Solde actuel : {solde/100.0:.2f} €"})
    return log

def action_recharger(montant_str):
    try:
        montant = Decimal(montant_str.replace(",", "."))
        if montant <= 0: raise ValueError
    except:
        return [{"type": "error", "text": "Montant invalide"}]
        
    perso, _ = lire_personnalisation()
    etu_num = extraire_num_etudiant_depuis_perso(perso) if perso else None
    
    if etu_num is None:
        return [{"type": "error", "text": "Carte non lue ou inconnue"}]
        
    cents = int(montant * 100)
    ok, log = credit_carte_centimes(cents)
    
    if not ok: return log
    
    db = get_db()
    if db:
        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO Compte (etu_num, opr_date, opr_montant, opr_libelle, type_operation) VALUES (%s, NOW(), %s, %s, %s)", 
                           (etu_num, montant, "Recharge CB Berlicum", "Recharge"))
            db.commit()
            cursor.close()
            log.append({"type": "info", "text": f"✅ Recharge {montant:.2f}€ enregistrée en base"})
        except Exception as e:
            db.rollback()
            log.append({"type": "error", "text": f"Erreur sauvegarde DB: {e}"})
    else:
        log.append({"type": "error", "text": "⚠️ DB déconnectée : Recharge carte OK, mais pas d'historique !"})
        
    return log

# --- Flask Routes ---

app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/status")
def api_status():
    # Test DB
    db = get_db()
    db_status = "OK" if db else "Erreur"
    
    # Test Lecteur (rapide)
    card_status = "Inconnu"
    if SMARTCARD_AVAILABLE:
        try:
            r = readers()
            card_status = "OK" if r else "Aucun lecteur"
        except:
            card_status = "Erreur"
    else:
        card_status = "Lib manquante"
        
    global_st = "Prêt" if (db_status=="OK" and card_status=="OK") else "Attention"
    
    return jsonify({"card": card_status, "db": db_status, "global": global_st})

@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json()
    cmd = data.get("command")
    montant = data.get("montant", "")
    log = []
    
    try:
        if cmd == "infos": log = action_infos()
        elif cmd == "bonus": log = action_bonus()
        elif cmd == "transferer": log = action_transferer()
        elif cmd == "solde": log = action_solde()
        elif cmd == "recharger": log = action_recharger(montant)
        else: log = [{"type": "error", "text": "Commande inconnue"}]
    except Exception as e:
        log.append({"type": "error", "text": f"Exception Serveur : {e}"})
        
    return jsonify({"log": log})

if __name__ == "__main__":
    print("🚀 BERLICUM Web démarré.")
    print("🌍 Accessible sur le réseau : http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)