#!/usr/bin/env python3
"""
Lubiana Web — Interface Web Interactive pour la gestion de carte à puce
Design : Univers visuel "Rodelika" (violet royal, élégance, clarté)
Correction : Gestion des accolades f-string pour le CSS/JS et logique APDU.
"""

from flask import Flask, render_template_string, request, jsonify
import sys

# --- Simuler les dépendances smartcard si non disponibles ---
try:
    from smartcard.System import readers
    from smartcard.Exceptions import CardConnectionException, NoCardException
    from smartcard.util import toHexString
    SMARTCARD_AVAILABLE = True
except ImportError:
    SMARTCARD_AVAILABLE = False
    # Classes bouchons pour éviter les erreurs d'import
    class CardConnectionException(Exception): pass
    class NoCardException(Exception): pass

# --- Constantes APDU ---
CLA_PERSO  = 0x81  # personnalisation
CLA_WALLET = 0x82  # gestion du solde

INS_VERSION     = 0x00
INS_INTRO_PERSO = 0x01
INS_LIRE_PERSO  = 0x02
INS_LIRE_SOLDE  = 0x01
INS_CREDIT      = 0x02
INS_DEBIT       = 0x03

MAX_PERSO = 32

# --- CSS moderne (Thème Violet Royal) ---
# Note : Stocké dans une string simple pour éviter les conflits d'accolades
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

/* Dark mode auto */
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

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', sans-serif;
    background: linear-gradient(135deg, var(--bg-light), #e6daff);
    color: var(--text-dark);
    line-height: 1.6;
    padding: 20px;
    min-height: 100vh;
}

.container {
    max-width: 1000px;
    margin: 0 auto;
}

/* Header */
.header {
    text-align: center;
    margin-bottom: 2rem;
}
.logo {
    font-size: 3.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, var(--primary), #a145e7);
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
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
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
.btn i {
    font-size: 1.8rem;
}
.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
}

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
.terminal-line {
    margin: 4px 0;
}
.cmd { color: var(--terminal-purple); }
.resp { color: var(--terminal-green); }
.sw-ok { color: var(--terminal-green); font-weight: bold; }
.sw-err { color: var(--terminal-red); font-weight: bold; }
.sw-warn { color: var(--terminal-yellow); }
.prompt { color: var(--terminal-yellow); }

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
.status-ready { color: var(--success); }
.status-error { color: var(--danger); }
.status-waiting { color: var(--warning); }

/* Responsive */
@media (max-width: 768px) {
    .btn-grid { grid-template-columns: 1fr; }
    .logo { font-size: 2.4rem; }
}
</style>
"""

# --- Template HTML principal ---
# IMPORTANT : Dans une f-string Python, les accolades CSS/JS doivent être doublées {{ }}
HTML_TEMPLATE = f"""
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lubiana — Gestion Carte à Puce</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  {COMMON_CSS}
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="logo">LUBIANA</h1>
      <p class="subtitle">Interface Web pour la personnalisation de carte à puce</p>
    </div>

    <div class="card">
      <h2 class="card-title"><i class="fas fa-microchip"></i> Actions disponibles</h2>
      <div class="btn-grid">
        <button class="btn" onclick="sendCommand('version')" id="btn-version">
          <i class="fas fa-info-circle"></i>
          <span>Version carte</span>
        </button>
        <button class="btn" onclick="sendCommand('lire_perso')" id="btn-lire">
          <i class="fas fa-id-card"></i>
          <span>Lire données</span>
        </button>
        <button class="btn" onclick="attribuerCarte()" id="btn-attribuer">
          <i class="fas fa-edit"></i>
          <span>Attribuer carte</span>
        </button>
        <button class="btn" onclick="sendCommand('solde_initial')" id="btn-credit">
          <i class="fas fa-coins"></i>
          <span>Crédit initial (1€)</span>
        </button>
        <button class="btn" onclick="sendCommand('lire_solde')" id="btn-solde">
          <i class="fas fa-wallet"></i>
          <span>Lire solde</span>
        </button>
        <button class="btn" onclick="clearTerminal()" style="border-color: #6c757d;">
          <i class="fas fa-trash"></i>
          <span>Effacer</span>
        </button>
      </div>

      <div class="status" id="status-bar">
        <span>🔍 État : <span id="status-text">En attente</span></span>
        <span id="reader-info">Lecteur : <span id="reader-status">Non détecté</span></span>
      </div>
    </div>

    <div class="card">
      <h2 class="card-title"><i class="fas fa-terminal"></i> Journal des opérations</h2>
      <div class="terminal" id="terminal-output">
        <div class="terminal-line">Bienvenue dans l'interface Lubiana Web.</div>
        <div class="terminal-line">Connectez une carte à puce pour commencer.</div>
      </div>
    </div>
  </div>

  <script>
    let terminal = document.getElementById('terminal-output');
    let statusText = document.getElementById('status-text');
    let readerStatus = document.getElementById('reader-status');

    function logLine(text, className = '') {{
        const div = document.createElement('div');
        div.className = `terminal-line ${{className}}`;
        div.textContent = text;
        terminal.appendChild(div);
        terminal.scrollTop = terminal.scrollHeight;
    }}

    function logAPDU(apdu) {{
        logLine(`--> APDU : ${{apdu}}`, 'cmd');
    }}

    function logResponse(resp, sw) {{
        logLine(`<-- Réponse : ${{resp}}  SW = ${{sw}}`, 'resp');
        if (sw === '90 00') {{
            logLine('✅ OK (90 00)', 'sw-ok');
        }} else if (sw.startsWith('6C')) {{
            logLine(`⚠️ Taille incorrecte : ${{sw}}`, 'sw-warn');
        }} else if (sw.startsWith('61')) {{
            logLine(`⚠️ Condition non satisfaite : ${{sw}}`, 'sw-warn');
        }} else {{
            logLine(`❌ Erreur : ${{sw}}`, 'sw-err');
        }}
    }}

    function updateStatus(text, type = 'waiting') {{
        statusText.textContent = text;
        statusText.className = type;
        if (type === 'error') statusText.style.color = 'var(--danger)';
        else if (type === 'ready') statusText.style.color = 'var(--success)';
        else statusText.style.color = 'var(--warning)';
    }}

    function clearTerminal() {{
        terminal.innerHTML = '<div class="terminal-line">Terminal vidé.</div>';
    }}

    async function sendCommand(cmd) {{
        try {{
            updateStatus('Envoi de la commande...', 'waiting');
            
            const response = await fetch('/api/command', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ command: cmd }})
            }});

            const data = await response.json();
            
            if (data.error) {{
                updateStatus('Erreur', 'error');
                logLine(`[ERREUR] ${{data.error}}`, 'sw-err');
            }} else {{
                updateStatus('Prêt', 'ready');
                // Afficher chaque ligne du journal
                data.log.forEach(line => {{
                    if (line.type === 'apdu') logAPDU(line.text);
                    else if (line.type === 'resp') logResponse(line.resp, line.sw);
                    else if (line.type === 'info') logLine(line.text);
                    else if (line.type === 'error') logLine(`[ERREUR] ${{line.text}}`, 'sw-err');
                }});
            }}
        }} catch (e) {{
            updateStatus('Échec communication', 'error');
            logLine(`[ERREUR RÉSEAU] ${{e.message}}`, 'sw-err');
        }}
    }}

    async function attribuerCarte() {{
        const name = prompt("Nom à écrire dans la carte (max 32 caractères) :");
        if (name === null) return;
        if (name.trim() === "") {{
            logLine("[ERREUR] Nom vide.", 'sw-err');
            return;
        }}

        try {{
            updateStatus('Écriture en cours...', 'waiting');
            
            const response = await fetch('/api/command', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ command: 'intro_perso', name: name }})
            }});

            const data = await response.json();
            
            if (data.error) {{
                updateStatus('Erreur', 'error');
                logLine(`[ERREUR] ${{data.error}}`, 'sw-err');
            }} else {{
                updateStatus('Prêt', 'ready');
                data.log.forEach(line => {{
                    if (line.type === 'apdu') logAPDU(line.text);
                    else if (line.type === 'resp') logResponse(line.resp, line.sw);
                    else if (line.type === 'info') logLine(line.text);
                }});
            }}
        }} catch (e) {{
            updateStatus('Échec', 'error');
            logLine(`[ERREUR] ${{e.message}}`, 'sw-err');
        }}
    }}

    // Vérifier l'état du lecteur toutes les 3s
    function checkReaderStatus() {{
        fetch('/api/reader-status')
            .then(r => r.json())
            .then(data => {{
                readerStatus.textContent = data.status;
                readerStatus.style.color = data.status === 'OK' ? 'var(--success)' : 'var(--danger)';
            }})
            .catch(() => {{
                readerStatus.textContent = 'Erreur';
                readerStatus.style.color = 'var(--danger)';
            }});
    }}

    // Initialisation
    document.addEventListener('DOMContentLoaded', () => {{
        checkReaderStatus();
        setInterval(checkReaderStatus, 3000);
    }});
  </script>
</body>
</html>
"""

# --- Fonctions utilitaires ---
def select_first_reader():
    """Retourne une connexion vers la carte sur le premier lecteur disponible."""
    if not SMARTCARD_AVAILABLE:
        return None, "Bibliothèque pyscard non installée."
    
    r = readers()
    if not r:
        return None, "Aucun lecteur PC/SC détecté."

    try:
        connection = r[0].createConnection()
        connection.connect()
        atr = toHexString(connection.getATR())
        return connection, f"OK (ATR: {atr})"
    except Exception as e:
        return None, f"Erreur connexion : {str(e)}"


def send_apdu_web(connection, cla, ins, p1=0x00, p2=0x00, data=None, le=None):
    """
    Version modifiée pour retourner un log structuré (pas d'affichage direct).
    """
    apdu = [cla, ins, p1, p2]

    if data is None:
        data = []
    else:
        data = list(data)

    if len(data) > 0:
        apdu.append(len(data))
        apdu.extend(data)
        # Note: Si Lc est présent, Le ne doit souvent pas l'être dans le même APDU (TP standard)
        if le is not None:
             raise ValueError("APDU Lc+Le non utilisée dans ce TP")
    else:
        if le is not None:
            apdu.append(le)
        else:
            # Case 1 ou Case 2 court sans Le explicite (souvent 00 ajouté par pyscard selon protocole)
            apdu.append(0)

    apdu_hex = toHexString(apdu)
    
    try:
        resp, sw1, sw2 = connection.transmit(apdu)
        resp_hex = toHexString(resp)
        sw_hex = f"{sw1:02X} {sw2:02X}"
        return {
            "apdu": apdu_hex,
            "resp": resp_hex,
            "sw": sw_hex,
            "success": (sw1 == 0x90 and sw2 == 0x00),
            "data": resp
        }
    except Exception as e:
        return {
            "apdu": apdu_hex,
            "error": str(e),
            "sw": "ERREUR",
            "success": False
        }

# --- Actions métier (retournent un journal structuré) ---
def action_get_version():
    conn, err = select_first_reader()
    if not conn:
        return [{"type": "error", "text": err}]

    log = []
    try:
        result = send_apdu_web(conn, CLA_PERSO, INS_VERSION, le=4)
        log.append({"type": "apdu", "text": result["apdu"]})
        if "error" in result:
            log.append({"type": "error", "text": result["error"]})
        else:
            log.append({"type": "resp", "resp": result["resp"], "sw": result["sw"]})
            if result["success"]:
                try:
                    version_str = "".join(chr(b) for b in result["data"])
                    log.append({"type": "info", "text": f"✅ Version de la carte : {version_str}"})
                except:
                    log.append({"type": "info", "text": "✅ Version reçue (non ASCII)"})
    finally:
        try: conn.disconnect()
        except: pass
    return log


def action_lire_perso():
    conn, err = select_first_reader()
    if not conn:
        return [{"type": "error", "text": err}]

    log = []
    try:
        # Première tentative avec Le=0
        result = send_apdu_web(conn, CLA_PERSO, INS_LIRE_PERSO, le=0)
        log.append({"type": "apdu", "text": result["apdu"]})
        log.append({"type": "resp", "resp": result.get("resp", ""), "sw": result.get("sw", "ERREUR")})

        if "error" in result:
            log.append({"type": "error", "text": result["error"]})
        else:
            sw = result["sw"]
            if sw.startswith("6C"):
                taille = int(sw.split()[1], 16)
                log.append({"type": "info", "text": f"→ Nouvelle tentative avec taille = {taille} octets"})
                result2 = send_apdu_web(conn, CLA_PERSO, INS_LIRE_PERSO, le=taille)
                log.append({"type": "apdu", "text": result2["apdu"]})
                log.append({"type": "resp", "resp": result2.get("resp", ""), "sw": result2.get("sw", "ERREUR")})
                if result2.get("success"):
                    name = "".join(chr(b) for b in result2["data"])
                    log.append({"type": "info", "text": f"📄 Nom stocké : '{name}'"})
            elif result["success"]:
                name = "".join(chr(b) for b in result["data"])
                log.append({"type": "info", "text": f"📄 Nom stocké : '{name}'"})
    finally:
        try: conn.disconnect()
        except: pass
    return log


def action_intro_perso(name):
    conn, err = select_first_reader()
    if not conn:
        return [{"type": "error", "text": err}]

    data = name.encode("ascii", errors="ignore")
    if len(data) == 0:
        return [{"type": "error", "text": "Nom vide"}]
    if len(data) > MAX_PERSO:
        data = data[:MAX_PERSO]

    log = []
    try:
        result = send_apdu_web(conn, CLA_PERSO, INS_INTRO_PERSO, data=data)
        log.append({"type": "apdu", "text": result["apdu"]})
        log.append({"type": "resp", "resp": result.get("resp", ""), "sw": result.get("sw", "ERREUR")})
        if result.get("success"):
            log.append({"type": "info", "text": f"✅ Nom '{name[:len(data)]}' écrit avec succès"})
    finally:
        try: conn.disconnect()
        except: pass
    return log


def action_lire_solde():
    conn, err = select_first_reader()
    if not conn:
        return [{"type": "error", "text": err}]

    log = []
    try:
        result = send_apdu_web(conn, CLA_WALLET, INS_LIRE_SOLDE, le=2)
        log.append({"type": "apdu", "text": result["apdu"]})
        log.append({"type": "resp", "resp": result.get("resp", ""), "sw": result.get("sw", "ERREUR")})
        if result.get("success") and len(result.get("data", [])) == 2:
            montant = (result["data"][0] << 8) | result["data"][1]
            euros = montant / 100.0
            log.append({"type": "info", "text": f"💰 Solde : {montant} centimes ({euros:.2f} €)"})
    finally:
        try: conn.disconnect()
        except: pass
    return log


def action_mettre_solde_initial():
    conn, err = select_first_reader()
    if not conn:
        return [{"type": "error", "text": err}]

    log = []
    try:
        # Lire solde actuel
        result = send_apdu_web(conn, CLA_WALLET, INS_LIRE_SOLDE, le=2)
        log.append({"type": "apdu", "text": result["apdu"]})
        log.append({"type": "resp", "resp": result.get("resp", ""), "sw": result.get("sw", "ERREUR")})
        
        if not result.get("success") or len(result.get("data", [])) != 2:
            log.append({"type": "error", "text": "Impossible de lire le solde actuel"})
            return log

        solde = (result["data"][0] << 8) | result["data"][1]
        cible = 100 # 1 euro
        diff = cible - solde
        original_diff = diff # On garde le signe pour l'affichage

        if diff == 0:
            log.append({"type": "info", "text": "✅ Solde déjà à 1.00 €"})
        else:
            op = INS_CREDIT if diff > 0 else INS_DEBIT
            diff = abs(diff) # Valeur absolue pour l'APDU
            data = [diff >> 8, diff & 0xFF]
            result2 = send_apdu_web(conn, CLA_WALLET, op, data=data)
            log.append({"type": "apdu", "text": result2["apdu"]})
            log.append({"type": "resp", "resp": result2.get("resp", ""), "sw": result2.get("sw", "ERREUR")})
            if result2.get("success"):
                signe = '+' if original_diff > 0 else '-'
                log.append({"type": "info", "text": f"✅ Solde ajusté à 1.00 € (diff = {signe}{abs(original_diff)/100:.2f} €)"})
    finally:
        try: conn.disconnect()
        except: pass
    return log


# --- Flask App ---
app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/reader-status")
def reader_status():
    if not SMARTCARD_AVAILABLE:
        return jsonify({"status": "pyscard manquant"})
    
    r = readers()
    if not r:
        return jsonify({"status": "Aucun lecteur"})
    
    try:
        # Test de connexion rapide
        conn = r[0].createConnection()
        conn.connect()
        conn.disconnect()
        return jsonify({"status": "OK"})
    except:
        return jsonify({"status": "Carte absente"})

@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json()
    command = data.get("command")
    name = data.get("name", "")

    log = []

    try:
        if command == "version":
            log = action_get_version()
        elif command == "lire_perso":
            log = action_lire_perso()
        elif command == "intro_perso":
            if not name:
                return jsonify({"error": "Nom requis"})
            log = action_intro_perso(name)
        elif command == "lire_solde":
            log = action_lire_solde()
        elif command == "solde_initial":
            log = action_mettre_solde_initial()
        else:
            return jsonify({"error": "Commande inconnue"})
    except Exception as e:
        log.append({"type": "error", "text": f"Exception interne : {str(e)}"})

    return jsonify({"log": log})

if __name__ == "__main__":
    print("🚀 Démarrage de Lubiana Web...")
    print("➡️  Ouvrez http://localhost:5000 dans votre navigateur")
    if not SMARTCARD_AVAILABLE:
        print("⚠️  Attention : pyscard non installé — fonctionne en mode simulation (erreurs de connexion).")
        print("   → Installez-le avec : pip install pyscard")
    
    app.run(host="0.0.0.0", port=5000, debug=True)