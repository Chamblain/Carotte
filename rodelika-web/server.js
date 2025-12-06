// server.js (Backend Node.js/Express)

const express = require('express');
const mysql = require('mysql2/promise');
const cors = require('cors');

const app = express();
const port = 5000;

// Configuration de la base de données (À ADAPTER)
const dbConfig = {
    host: 'localhost',
    user: 'rodelika',           
    password: 'R0deLika123!',   
    database: 'purpledragon'
};

// Middleware
app.use(cors()); // Permet les requêtes depuis le frontend Vue.js
app.use(express.json()); // Pour parser les requêtes JSON (POST, PUT)

// --- A. Route d'accueil ---
app.get('/', (req, res) => {
    res.send('Rodelika Web Backend running!');
});

// --- B. 👥 1 - Afficher la liste des étudiants ---
app.get('/api/etudiants', async (req, res) => {
    try {
        const connection = await mysql.createConnection(dbConfig);
        const [rows] = await connection.execute('SELECT etu_num, etu_nom, etu_prenom FROM Etudiant ORDER BY etu_num');
        connection.end();
        res.json(rows);
    } catch (error) {
        console.error('Erreur lors de la récupération des étudiants:', error);
        res.status(500).json({ erreur: 'Erreur serveur lors de la récupération des étudiants.' });
    }
});

// --- C. 💰 2 - Afficher le solde des étudiants ---
app.get('/api/soldes', async (req, res) => {
    try {
        const connection = await mysql.createConnection(dbConfig);
        const sql = `
            SELECT Etudiant.etu_num, Etudiant.etu_nom, Etudiant.etu_prenom,
                   COALESCE(SUM(Compte.opr_montant), 0) AS solde
            FROM Etudiant
            LEFT JOIN Compte ON Etudiant.etu_num = Compte.etu_num
            GROUP BY Etudiant.etu_num, Etudiant.etu_nom, Etudiant.etu_prenom
            ORDER BY Etudiant.etu_num
        `;
        const [rows] = await connection.execute(sql);
        connection.end();
        res.json(rows);
    } catch (error) {
        console.error('Erreur lors de la récupération des soldes:', error);
        res.status(500).json({ erreur: 'Erreur serveur lors de la récupération des soldes.' });
    }
});

// --- D. ➕ 3 - Saisir un nouvel étudiant ---
app.post('/api/etudiant/nouveau', async (req, res) => {
    const { nom, prenom } = req.body;

    if (!nom || !prenom) {
        return res.status(400).json({ erreur: 'Nom et prénom sont obligatoires.' });
    }

    try {
        const connection = await mysql.createConnection(dbConfig);
        const sql = "INSERT INTO Etudiant (etu_nom, etu_prenom) VALUES (?, ?)";
        const [result] = await connection.execute(sql, [nom, prenom]);
        connection.end();
        res.status(201).json({ 
            message: `Étudiant ajouté avec succès. ID: ${result.insertId}`, 
            id: result.insertId 
        });
    } catch (error) {
        console.error('Erreur lors de l\'ajout d\'un étudiant:', error);
        res.status(500).json({ erreur: 'Erreur serveur lors de l\'ajout de l\'étudiant.' });
    }
});

// --- E. 🎁 4 - Attribuer un bonus (+1.00 €) ---
app.post('/api/bonus', async (req, res) => {
    const { etu_num, commentaire } = req.body;
    const montantBonus = 1.00; // 1.00 € comme spécifié [cite: 55, 57]
    const typeOperation = 'Bonus';

    if (!etu_num || !commentaire) {
        return res.status(400).json({ erreur: 'Numéro d\'étudiant et commentaire sont obligatoires.' });
    }
    
    // Vérification simple de l'ID (doit être un entier positif)
    if (isNaN(parseInt(etu_num)) || parseInt(etu_num) <= 0) {
        return res.status(400).json({ erreur: 'Numéro d\'étudiant invalide.' });
    }

    try {
        const connection = await mysql.createConnection(dbConfig);

        // 1. Vérifier l'existence de l'étudiant
        const [etuRows] = await connection.execute('SELECT 1 FROM Etudiant WHERE etu_num = ?', [etu_num]);
        if (etuRows.length === 0) {
            connection.end();
            return res.status(404).json({ erreur: `Aucun étudiant trouvé avec le numéro ${etu_num}.` });
        }

        // 2. Insérer le bonus
        // La colonne utilisée est bien 'type_operation' (corrigée par rapport au script Flask initial)
        const sql = `
            INSERT INTO Compte (etu_num, opr_date, opr_montant, opr_libelle, type_operation)
            VALUES (?, NOW(), ?, ?, ?)
        `;
        await connection.execute(sql, [etu_num, montantBonus, commentaire, typeOperation]);

        connection.end();
        res.status(201).json({ message: `🎉 Bonus de +${montantBonus.toFixed(2)} € ajouté avec succès pour l'étudiant ${etu_num} !` });

    } catch (error) {
        console.error('Erreur lors de l\'ajout du bonus:', error);
        res.status(500).json({ erreur: 'Erreur serveur lors de l\'ajout du bonus.' });
    }
});


// Lancement du serveur
app.listen(port, '0.0.0.0', () => {
    console.log(`Rodelika Web Backend écoutant sur http://0.0.0.0:${port}`);
    console.log('Maintenant accessible depuis le réseau local de l\'hôte.');
});
