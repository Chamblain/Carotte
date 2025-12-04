#!/usr/bin/env python3
from flask import Flask, jsonify, request, send_from_directory
import os
from lunarwhite import (
    ouvrir_lecteur,
    lire_solde,
    debiter,
    PRIX_BOISSON,
    log_transaction,
)
import threading

app = Flask(__name__)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route("/")
def index():
    # renvoie index.html qui est dans le même dossier que ce script
    return send_from_directory(BASE_DIR, "index.html")


# Mode simulation si on n'a pas de lecteur ou pas de carte
MODE_SIMU = False
_solde_simulation = 2.00  # 2 euros pour les tests
_lock = threading.Lock()

conn = ouvrir_lecteur()
if conn is None:
    print("[INFO] Pas de lecteur/carte : passage en mode simulation.")
    MODE_SIMU = True


def get_solde():
    global _solde_simulation
    if MODE_SIMU:
        with _lock:
            return _solde_simulation
    else:
        return lire_solde(conn)


def debit_carte(montant_euros, nom_boisson):
    """
    Retourne (ok: bool, message: str, nouveau_solde: float | None)
    """
    global _solde_simulation

    solde_initial = get_solde()
    if solde_initial is None:
        return False, "Impossible de lire le solde", None

    if solde_initial < montant_euros:
        # refus solde insuffisant
        log_transaction(nom_boisson, montant_euros, solde_initial, solde_initial, "REFUS_SOLDE")
        return False, f"Solde insuffisant ({solde_initial:.2f} €)", solde_initial

    if MODE_SIMU:
        # Simule le débit
        with _lock:
            _solde_simulation -= montant_euros
            nouveau_solde = _solde_simulation
        log_transaction(nom_boisson, montant_euros, solde_initial, nouveau_solde, "OK_SIMU")
        return True, "Boisson servie (simulation)", nouveau_solde
    else:
        # Carte réelle
        if debiter(conn, montant_euros):
            nouveau_solde = get_solde()
            if nouveau_solde is None:
                log_transaction(nom_boisson, montant_euros, solde_initial, solde_initial - montant_euros, "OK_SOLDE_INCONNU")
                return True, "Débit effectué, solde non relu", None
            else:
                log_transaction(nom_boisson, montant_euros, solde_initial, nouveau_solde, "OK")
                return True, "Boisson servie", nouveau_solde
        else:
            log_transaction(nom_boisson, montant_euros, solde_initial, solde_initial, "REFUS_AUTRE")
            return False, "Débit refusé par la carte", solde_initial


@app.get("/api/solde")
def api_solde():
    solde = get_solde()
    if solde is None:
        return jsonify({"ok": False, "message": "Impossible de lire le solde"}), 500
    return jsonify({"ok": True, "solde": solde})


@app.post("/api/boisson")
def api_boisson():
    data = request.get_json(silent=True) or {}
    type_boisson = data.get("type", "cafe")

    # pour l’instant toutes les boissons coûtent le même prix
    prix = PRIX_BOISSON
    ok, message, nouveau_solde = debit_carte(prix, type_boisson)

    return jsonify({
        "ok": ok,
        "message": message,
        "prix": prix,
        "nouveau_solde": nouveau_solde,
        "type": type_boisson
    }), (200 if ok else 400)


if __name__ == "__main__":
    # host="0.0.0.0" si tu veux accéder depuis une autre machine/VM
    app.run(host="127.0.0.1", port=5000, debug=True)


