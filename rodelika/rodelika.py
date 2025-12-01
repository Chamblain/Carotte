#!/usr/bin/env python3

import mysql.connector

# ⚠️ À ADAPTER avec tes identifiants MySQL
cnx = mysql.connector.connect(
    user='rodelika',
    password='R0deLika123!',
    host='localhost',
    database='purpledragon'
)

def print_hello_message():
    print("-----------------------------------")
    print("-- Logiciel de gestion : Rodelika --")
    print("-----------------------------------")

def print_menu():
    print(" 1 - Afficher la liste des étudiants ")
    print(" 2 - Afficher le solde des étudiants ")
    print(" 3 - Saisir un nouvel étudiant ")
    print(" 4 - Attribuer un bonus ")
    print(" 5 - Quitter")

def get_list_student():
    # Utiliser exactement le nom de la table : Etudiant
    sql = "SELECT Etudiant.* FROM Etudiant"
    cursor = cnx.cursor()
    cursor.execute(sql)
    row = cursor.fetchone()
    if row is None:
        print("Aucun étudiant.")
    while row is not None:
        print(row)
        row = cursor.fetchone()
    cursor.close()

def get_list_student_with_sold():
    # Même requête que dans le sujet, mais avec la bonne casse
    sql = """
        SELECT Etudiant.*, SUM(Compte.opr_montant) AS sold
        FROM Etudiant, Compte
        WHERE Etudiant.etu_num = Compte.etu_num
        GROUP BY Compte.etu_num
    """
    cursor = cnx.cursor()
    cursor.execute(sql)
    row = cursor.fetchone()
    if row is None:
        print("Aucun étudiant avec opérations.")
    while row is not None:
        print(row)
        row = cursor.fetchone()
    cursor.close()

def new_student():
    nom = input("Nom Etudiant : ")
    pre = input("Pre Etudiant : ")
    sql = """INSERT INTO Etudiant (etu_num, etu_nom, etu_prenom)
             VALUES (NULL, %s, %s);"""
    val = (nom, pre)
    cursor = cnx.cursor()
    cursor.execute(sql, val)
    cnx.commit()
    print("Nouvel étudiant créé avec l'id", cursor.lastrowid)
    cursor.close()

def add_bonus():
    num = input("Num Etudiant : ")
    com = input("Commentaire : ")

    # Validation de l'ID
    try:
        etu_num = int(num)
    except ValueError:
        print("Numéro d'étudiant invalide.")
        return

    cursor = cnx.cursor()

    # Vérifier que l'étudiant existe
    cursor.execute("SELECT 1 FROM Etudiant WHERE etu_num = %s", (etu_num,))
    if cursor.fetchone() is None:
        print("Aucun étudiant avec ce numéro.")
        cursor.close()
        return

    # Insérer un bonus de +1.00 euro
    # ⚠️ colonne EXACTE : type_opeartion (faute du sujet)
    sql = """
        INSERT INTO Compte (etu_num, opr_date, opr_montant, opr_libelle, type_opeartion)
        VALUES (%s, NOW(), %s, %s, %s)
    """
    val = (etu_num, 1.00, com, "Bonus")
    cursor.execute(sql, val)
    cnx.commit()
    cursor.close()

    print("Bonus + 1.00 euros")

def main():
    print_hello_message()
    while True:
        print_menu()
        choix = input("Choix : ")

        # On évite de crasher si l'utilisateur tape n'importe quoi
        try:
            cmd = int(choix)
        except ValueError:
            print("Commande inconnue !")
            print("\n ---\n")
            continue

        if cmd == 1:
            get_list_student()
        elif cmd == 2:
            get_list_student_with_sold()
        elif cmd == 3:
            new_student()
        elif cmd == 4:
            add_bonus()
        elif cmd == 5:
            print("Au revoir.")
            break
        else:
            print("Commande inconnue !")

        print("\n ---\n")

    cnx.close()

if __name__ == "__main__":
    main()
