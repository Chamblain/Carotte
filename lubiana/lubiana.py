def afficher_menu():
    print("==== LUBIANA ====")
    print("1. Afficher version carte")
    print("2. Afficher données carte")
    print("3. Attribuer la carte")
    print("4. Créditer la carte (solde initial)")
    print("5. Lire le solde")
    print("0. Quitter")


def main():
    while True:
        afficher_menu()
        choix = input("Choix : ")

        if choix == "1":
            print("Lecture version (à implémenter)")
        elif choix == "2":
            print("Lecture données (à implémenter)")
        elif choix == "3":
            print("Attribution carte (à implémenter)")
        elif choix == "4":
            print("Crédit initial (à implémenter)")
        elif choix == "5":
            print("Lecture solde (à implémenter)")
        elif choix == "0":
            print("Au revoir")
            break
        else:
            print("Choix invalide")


if __name__ == "__main__":
    main()


