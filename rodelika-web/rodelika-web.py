#!/usr/bin/env python3

from flask import Flask, request, redirect, url_for, render_template_string
import mysql.connector

# ⚠️ Même config que dans ton rodelika.py
DB_CONFIG = {
    "user": "rodelika",           # adapte si besoin
    "password": "R0deLika123!",   # adapte si besoin
    "host": "localhost",
    "database": "purpledragon",
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

app = Flask(__name__)

# ----- CSS commun (inclus dans chaque template) -----
COMMON_CSS = """
<style>
/* === Palette === */
:root {
    --primary: #6a0dad;          /* Royal Purple */
    --primary-dark: #4b2e83;
    --primary-darker: #2e1a47;
    --accent: #ff6ec7;           /* Soft Pink Accent */
    --bg-light: #f8f1ff;
    --bg-card: #ffffff;
    --text-dark: #2d1b3e;
    --text-light: #5a4a66;
    --border: #e0d0eb;
    --success: #28a745;
    --danger: #dc3545;
}

/* === Reset & Base === */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', sans-serif;
    background: linear-gradient(135deg, #f5f0ff, #e6daff);
    color: var(--text-dark);
    line-height: 1.6;
    padding: 20px;
    min-height: 100vh;
}

.container {
    max-width: 900px;
    margin: 0 auto;
}

/* === Typography === */
h1 {
    font-weight: 700;
    font-size: 2.4rem;
    margin-bottom: 1.5rem;
    color: var(--primary-darker);
    text-align: center;
    position: relative;
}
h1:after {
    content: '';
    display: block;
    width: 80px;
    height: 4px;
    background: var(--primary);
    margin: 12px auto;
    border-radius: 2px;
}

h2 {
    font-weight: 600;
    font-size: 1.8rem;
    margin: 1.2rem 0;
    color: var(--primary-dark);
}

/* === Card Layout === */
.card {
    background: var(--bg-card);
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(106, 13, 173, 0.12);
    padding: 2rem;
    margin-bottom: 2rem;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px rgba(106, 13, 173, 0.18);
}

/* === Links & Buttons === */
a {
    color: var(--primary);
    text-decoration: none;
    font-weight: 600;
    transition: color 0.2s, transform 0.2s;
}
a:hover {
    color: var(--primary-dark);
    text-decoration: underline;
}

.btn {
    display: inline-block;
    background: var(--primary);
    color: white;
    padding: 12px 24px;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: center;
}
.btn:hover {
    background: var(--primary-dark);
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(106, 13, 173, 0.3);
}
.btn:active {
    transform: translateY(0);
}

/* === Lists & Menus === */
ul {
    list-style: none;
}
li {
    margin: 1rem 0;
    padding-left: 1.5rem;
    position: relative;
    font-size: 1.1rem;
}
li:before {
    content: "●";
    color: var(--primary);
    position: absolute;
    left: 0;
    font-weight: bold;
}

/* === Tables === */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    border-radius: 12px;
    overflow: hidden;
}
th, td {
    padding: 14px 18px;
    text-align: left;
    border-bottom: 1px solid var(--border);
}
th {
    background: var(--primary);
    color: white;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
tr:nth-child(even) {
    background-color: #faf7ff;
}
tr:hover {
    background-color: #f0e6ff !important;
}
td {
    color: var(--text-dark);
}

/* === Forms === */
form label {
    display: block;
    margin: 1.2rem 0 0.5rem;
    font-weight: 600;
    color: var(--primary-darker);
}
input[type="text"],
input[type="number"] {
    width: 100%;
    max-width: 400px;
    padding: 14px;
    border: 2px solid var(--border);
    border-radius: 12px;
    font-size: 1rem;
    transition: border-color 0.3s, box-shadow 0.3s;
    background: white;
}
input[type="text"]:focus,
input[type="number"]:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(106, 13, 173, 0.2);
}

/* === Messages === */
.message {
    padding: 12px 20px;
    border-radius: 10px;
    margin: 1.5rem 0;
    font-weight: 500;
}
.message.success {
    background: #e6f4ea;
    border-left: 4px solid var(--success);
    color: #155724;
}
.message.error {
    background: #fde9e9;
    border-left: 4px solid var(--danger);
    color: #721c24;
}

/* === Footer Link === */
.back-link {
    display: inline-flex;
    align-items: center;
    font-weight: 600;
    margin-top: 1.5rem;
}
.back-link:before {
    content: "←";
    margin-right: 8px;
    font-weight: bold;
}

/* === Responsive === */
@media (max-width: 768px) {
    .card {
        padding: 1.5rem;
    }
    h1 {
        font-size: 2rem;
    }
    table {
        font-size: 0.9rem;
    }
    th, td {
        padding: 10px 12px;
    }
}
</style>
"""

# ----- Templates avec CSS intégré -----
MENU_TEMPLATE = f"""
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rodelika - Interface web</title>
  {COMMON_CSS}
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>🐉 Rodelika — Gestion Étudiante</h1>
      <p style="text-align: center; color: var(--text-light); margin-bottom: 2rem; font-size: 1.1rem;">
        Interface web sécurisée • Base <strong>PurpleDragon</strong>
      </p>
      <ul>
        <li><a href="{{{{ url_for('liste_etudiants') }}}}">👥 1 — Afficher la liste des étudiants</a></li>
        <li><a href="{{{{ url_for('soldes_etudiants') }}}}">💰 2 — Afficher le solde des étudiants</a></li>
        <li><a href="{{{{ url_for('nouvel_etudiant') }}}}">➕ 3 — Saisir un nouvel étudiant</a></li>
        <li><a href="{{{{ url_for('bonus') }}}}">🎁 4 — Attribuer un bonus</a></li>
      </ul>
    </div>
  </div>
</body>
</html>
"""

LISTE_ETUDIANTS_TEMPLATE = f"""
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Liste des étudiants</title>
  {COMMON_CSS}
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>👥 Liste des étudiants</h1>
      {{% if etudiants %}}
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>🆔 Numéro</th>
                <th>👨‍🎓 Nom</th>
                <th>👩‍🎓 Prénom</th>
              </tr>
            </thead>
            <tbody>
              {{% for e in etudiants %}}
              <tr>
                <td><strong>{{{{ e[0] }}}}</strong></td>
                <td>{{{{ e[1] }}}}</td>
                <td>{{{{ e[2] }}}}</td>
              </tr>
              {{% endfor %}}
            </tbody>
          </table>
        </div>
      {{% else %}}
        <p style="text-align: center; color: var(--text-light); font-style: italic;">
          🕊️ Aucun étudiant trouvé dans la base de données.
        </p>
      {{% endif %}}
      <a href="{{{{ url_for('index') }}}}" class="back-link">Retour au menu principal</a>
    </div>
  </div>
</body>
</html>
"""

SOLDES_TEMPLATE = f"""
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Soldes des étudiants</title>
  {COMMON_CSS}
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>💰 Soldes des étudiants</h1>
      {{% if soldes %}}
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>🆔 Numéro</th>
                <th>👨‍🎓 Nom</th>
                <th>👩‍🎓 Prénom</th>
                <th>💵 Solde (€)</th>
              </tr>
            </thead>
            <tbody>
              {{% for e in soldes %}}
              <tr>
                <td><strong>{{{{ e[0] }}}}</strong></td>
                <td>{{{{ e[1] }}}}</td>
                <td>{{{{ e[2] }}}}</td>
                <td>
                  <span style="color: {{{{ 'var(--success)' if e[3] >= 0 else 'var(--danger)' }}}}; font-weight: 600;">
                    {{{{ "%+.2f"|format(e[3]) }}}} €
                  </span>
                </td>
              </tr>
              {{% endfor %}}
            </tbody>
          </table>
        </div>
        <p style="text-align: center; color: var(--text-light); margin-top: 1rem; font-size: 0.95rem;">
          💡 Un solde positif signifie un crédit (bonus), négatif un débit.
        </p>
      {{% else %}}
        <p style="text-align: center; color: var(--text-light); font-style: italic;">
          🕊️ Aucune opération comptable trouvée.
        </p>
      {{% endif %}}
      <a href="{{{{ url_for('index') }}}}" class="back-link">Retour au menu principal</a>
    </div>
  </div>
</body>
</html>
"""

NOUVEL_ETUDIANT_TEMPLATE = f"""
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nouvel étudiant</title>
  {COMMON_CSS}
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>➕ Saisir un nouvel étudiant</h1>
      <form method="post">
        <label for="nom">Nom complet :</label>
        <input type="text" id="nom" name="nom" required autocomplete="family-name">

        <label for="prenom">Prénom :</label>
        <input type="text" id="prenom" name="prenom" required autocomplete="given-name">

        <button type="submit" class="btn">✅ Enregistrer l'étudiant</button>
      </form>

      {{% if message %}}
        <div class="message {{% if 'ajouté' in message or 'Ajouté' in message %}}success{{% else %}}error{{% endif %}}">
          {{{{ message }}}}
        </div>
      {{% endif %}}

      <a href="{{{{ url_for('index') }}}}" class="back-link">Retour au menu principal</a>
    </div>
  </div>
</body>
</html>
"""

BONUS_TEMPLATE = f"""
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Attribuer un bonus</title>
  {COMMON_CSS}
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>🎁 Attribuer un bonus (+1.00 €)</h1>
      <form method="post">
        <label for="etu_num">Numéro d'étudiant :</label>
        <input type="number" id="etu_num" name="etu_num" required min="1" placeholder="Ex: 42">

        <label for="commentaire">Commentaire (motif du bonus) :</label>
        <input type="text" id="commentaire" name="commentaire" required maxlength="100" 
               placeholder="Ex: Participation au club informatique">

        <button type="submit" class="btn">✨ Ajouter le bonus</button>
      </form>

      {{% if message %}}
        <div class="message success">
          {{{{ message }}}}
        </div>
      {{% elif erreur %}}
        <div class="message error">
          {{{{ erreur }}}}
        </div>
      {{% endif %}}

      <a href="{{{{ url_for('index') }}}}" class="back-link">Retour au menu principal</a>
    </div>
  </div>
</body>
</html>
"""

# ----------------- Routes Flask -----------------

@app.route("/")
def index():
    return render_template_string(MENU_TEMPLATE)

@app.route("/etudiants")
def liste_etudiants():
    cnx = get_connection()
    cursor = cnx.cursor()
    cursor.execute("SELECT Etudiant.* FROM Etudiant")
    etudiants = cursor.fetchall()
    cursor.close()
    cnx.close()
    return render_template_string(LISTE_ETUDIANTS_TEMPLATE, etudiants=etudiants)

@app.route("/soldes")
def soldes_etudiants():
    cnx = get_connection()
    cursor = cnx.cursor()
    sql = """
        SELECT Etudiant.etu_num, Etudiant.etu_nom, Etudiant.etu_prenom,
               COALESCE(SUM(Compte.opr_montant), 0) AS solde
        FROM Etudiant
        LEFT JOIN Compte ON Etudiant.etu_num = Compte.etu_num
        GROUP BY Etudiant.etu_num, Etudiant.etu_nom, Etudiant.etu_prenom
    """
    cursor.execute(sql)
    soldes = cursor.fetchall()
    cursor.close()
    cnx.close()
    return render_template_string(SOLDES_TEMPLATE, soldes=soldes)

@app.route("/etudiant/nouveau", methods=["GET", "POST"])
def nouvel_etudiant():
    message = None
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()
        if nom and prenom:
            cnx = get_connection()
            cursor = cnx.cursor()
            sql = """INSERT INTO Etudiant (etu_num, etu_nom, etu_prenom)
                     VALUES (NULL, %s, %s)"""
            cursor.execute(sql, (nom, prenom))
            cnx.commit()
            message = f"✅ Étudiant ajouté avec l'id {cursor.lastrowid}"
            cursor.close()
            cnx.close()
        else:
            message = "⚠️ Nom et prénom obligatoires."
    return render_template_string(NOUVEL_ETUDIANT_TEMPLATE, message=message)

@app.route("/bonus", methods=["GET", "POST"])
def bonus():
    message = None
    erreur = None
    if request.method == "POST":
        etu_num_str = request.form.get("etu_num", "").strip()
        commentaire = request.form.get("commentaire", "").strip()

        try:
            etu_num = int(etu_num_str)
        except ValueError:
            erreur = "⚠️ Numéro d'étudiant invalide (doit être un entier)."
            return render_template_string(BONUS_TEMPLATE, message=message, erreur=erreur)

        if not commentaire:
            erreur = "⚠️ Le commentaire est obligatoire (max 100 caractères)."
            return render_template_string(BONUS_TEMPLATE, message=message, erreur=erreur)

        cnx = get_connection()
        cursor = cnx.cursor()

        # Vérifier l'existence de l'étudiant
        cursor.execute("SELECT 1 FROM Etudiant WHERE etu_num = %s", (etu_num,))
        if cursor.fetchone() is None:
            erreur = "❌ Aucun étudiant trouvé avec ce numéro."
            cursor.close()
            cnx.close()
            return render_template_string(BONUS_TEMPLATE, message=message, erreur=erreur)

        # Insertion du bonus — avec la faute *opeartion* comme dans votre schéma
        sql = """
            INSERT INTO Compte (etu_num, opr_date, opr_montant, opr_libelle, type_opeartion)
            VALUES (%s, NOW(), %s, %s, %s)
        """
        cursor.execute(sql, (etu_num, 1.00, commentaire, "Bonus"))
        cnx.commit()
        cursor.close()
        cnx.close()
        message = "🎉 Bonus de +1.00 € ajouté avec succès !"

    return render_template_string(BONUS_TEMPLATE, message=message, erreur=erreur)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
