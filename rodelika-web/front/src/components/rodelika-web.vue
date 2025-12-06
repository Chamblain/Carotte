<template>
  <div class="container">
    <div class="card">
      <h1>🐉 Rodelika — Gestion Étudiante</h1>
      <p class="subtitle">Interface web sécurisée • Base <strong>PurpleDragon</strong></p>
      
      <div v-if="view === 'menu'">
        <ul class="main-menu">
          <li><a href="#" @click.prevent="setView('liste')">👥 1 — Afficher la liste des étudiants</a></li>
          <li><a href="#" @click.prevent="loadSoldes()">💰 2 — Afficher le solde des étudiants</a></li>
          <li><a href="#" @click.prevent="setView('nouveau')">➕ 3 — Saisir un nouvel étudiant</a></li>
          <li><a href="#" @click.prevent="setView('bonus')">🎁 4 — Attribuer un bonus</a></li>
        </ul>
      </div>

      <div v-if="view === 'liste'">
        <h2>👥 Liste des étudiants</h2>
        <p v-if="loading" class="loading">Chargement...</p>
        <div v-if="etudiants.length > 0" class="table-responsive">
          <table>
            <thead>
              <tr><th>🆔 Numéro</th><th>👨‍🎓 Nom</th><th>👩‍🎓 Prénom</th></tr>
            </thead>
            <tbody>
              <tr v-for="e in etudiants" :key="e.etu_num">
                <td><strong>{{ e.etu_num }}</strong></td>
                <td>{{ e.etu_nom }}</td>
                <td>{{ e.etu_prenom }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else-if="!loading" class="empty">🕊️ Aucun étudiant trouvé dans la base de données.</p>
      </div>

      <div v-if="view === 'soldes'">
        <h2>💰 Soldes des étudiants</h2>
        <p v-if="loading" class="loading">Chargement...</p>
        <div v-if="soldes.length > 0" class="table-responsive">
          <table>
            <thead>
              <tr><th>🆔 Numéro</th><th>👨‍🎓 Nom</th><th>👩‍🎓 Prénom</th><th>💵 Solde (€)</th></tr>
            </thead>
            <tbody>
              <tr v-for="e in soldes" :key="e.etu_num">
                <td><strong>{{ e.etu_num }}</strong></td>
                <td>{{ e.etu_nom }}</td>
                <td>{{ e.etu_prenom }}</td>
                <td>
                  <span :class="{'success-text': e.solde >= 0, 'danger-text': e.solde < 0}">
                    {{ formatSolde(e.solde) }} €
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else-if="!loading" class="empty">🕊️ Aucune opération comptable trouvée.</p>
        <p class="tip">💡 Un solde positif signifie un crédit (bonus), négatif un débit.</p>
      </div>

      <div v-if="view === 'nouveau'">
        <h2>➕ Saisir un nouvel étudiant</h2>
        <form @submit.prevent="submitNewStudent">
          <label for="nom">Nom complet :</label>
          <input type="text" id="nom" v-model="newStudent.nom" required autocomplete="family-name">

          <label for="prenom">Prénom :</label>
          <input type="text" id="prenom" v-model="newStudent.prenom" required autocomplete="given-name">

          <button type="submit" class="btn">✅ Enregistrer l'étudiant</button>
        </form>
      </div>
      
      <div v-if="view === 'bonus'">
        <h2>🎁 Attribuer un bonus (+1.00 €)</h2>
        <form @submit.prevent="submitBonus">
          <label for="etu_num_b">Numéro d'étudiant :</label>
          <input type="number" id="etu_num_b" v-model.number="bonusData.etu_num" required min="1" placeholder="Ex: 42">

          <label for="commentaire_b">Commentaire (motif du bonus) :</label>
          <input type="text" id="commentaire_b" v-model="bonusData.commentaire" required maxlength="100" 
                placeholder="Ex: Projet avec Pr Tournesol">

          <button type="submit" class="btn">✨ Ajouter le bonus</button>
        </form>
      </div>

      <div v-if="message" :class="['message', message.type]">
        {{ message.text }}
      </div>

      <a v-if="view !== 'menu'" href="#" @click.prevent="setView('menu')" class="back-link">Retour au menu principal</a>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

// URL de base de notre backend Express
const API_BASE_URL = 'http://192.168.1.29:5000/api';

export default {
  name: 'RodelikaWeb',
  data() {
    return {
      view: 'menu',
      loading: false,
      message: null,
      etudiants: [],
      soldes: [],
      newStudent: { nom: '', prenom: '' },
      bonusData: { etu_num: null, commentaire: '' }
    };
  },
  mounted() {
    // Charge la liste des étudiants et des soldes dès le montage
    this.loadEtudiants();
  },
  methods: {
    // --- Gestion de la vue et des messages ---
    setView(viewName) {
      this.view = viewName;
      this.message = null; // Réinitialiser le message lors du changement de vue
      if (viewName === 'liste') {
        this.loadEtudiants();
      }
    },
    showMessage(text, type = 'success') {
      this.message = { text, type };
      setTimeout(() => {
        this.message = null;
      }, 5000);
    },

    // --- Requêtes API ---

    // Récupère la liste des étudiants (pour la vue 'liste' et la validation du bonus)
    async loadEtudiants() {
        this.loading = true;
        try {
            const response = await axios.get(`${API_BASE_URL}/etudiants`);
            this.etudiants = response.data;
        } catch (error) {
            this.showMessage(`Erreur lors du chargement des étudiants: ${error.response?.data.erreur || error.message}`, 'error');
        } finally {
            this.loading = false;
        }
    },

    // Récupère les soldes et passe à la vue 'soldes'
    async loadSoldes() {
        this.setView('soldes');
        this.loading = true;
        try {
            const response = await axios.get(`${API_BASE_URL}/soldes`);
            this.soldes = response.data;
        } catch (error) {
            this.showMessage(`Erreur lors du chargement des soldes: ${error.response?.data.erreur || error.message}`, 'error');
        } finally {
            this.loading = false;
        }
    },

    // Ajout d'un nouvel étudiant (POST /api/etudiant/nouveau)
    async submitNewStudent() {
      try {
        const response = await axios.post(`${API_BASE_URL}/etudiant/nouveau`, this.newStudent);
        this.showMessage(response.data.message);
        this.newStudent = { nom: '', prenom: '' }; // Réinitialiser le formulaire
        this.loadEtudiants(); // Rafraîchir la liste
      } catch (error) {
        this.showMessage(`Erreur: ${error.response?.data.erreur || error.message}`, 'error');
      }
    },

    // Ajout d'un bonus (POST /api/bonus)
    async submitBonus() {
      try {
        const response = await axios.post(`${API_BASE_URL}/bonus`, this.bonusData);
        this.showMessage(response.data.message);
        this.bonusData = { etu_num: null, commentaire: '' }; // Réinitialiser le formulaire
        this.loadSoldes(); // Rafraîchir les soldes
      } catch (error) {
        this.showMessage(`Erreur: ${error.response?.data.erreur || error.message}`, 'error');
      }
    },

    // --- Utilitaires ---
    formatSolde(solde) {
        return (solde / 1).toFixed(2);
    }
  }
};
</script>

<style>
/* === Structure Générale === */
.container { max-width: 900px; margin: 0 auto; padding: 20px; }
.card {
    background: #ffffff; border-radius: 16px; box-shadow: 0 10px 30px rgba(106, 13, 173, 0.12);
    padding: 2rem; margin-bottom: 2rem;
}
h1 { font-size: 2.4rem; color: #2e1a47; text-align: center; margin-bottom: 1.5rem; }
h2 { font-size: 1.8rem; color: #4b2e83; margin: 1.2rem 0; }
.subtitle { text-align: center; color: #5a4a66; margin-bottom: 2rem; font-size: 1.1rem; }
.tip { text-align: center; color: #5a4a66; margin-top: 1rem; font-size: 0.95rem; font-style: italic; }

/* === Menu et Liens === */
.main-menu { list-style: none; padding: 0; }
.main-menu li { margin: 1rem 0; position: relative; padding-left: 1.5rem; }
.main-menu a { color: #6a0dad; text-decoration: none; font-weight: 600; font-size: 1.1rem; }
.main-menu li:before { content: "●"; color: #6a0dad; position: absolute; left: 0; font-weight: bold; }
.back-link { display: inline-flex; align-items: center; font-weight: 600; margin-top: 1.5rem; color: #6a0dad; }
.back-link:before { content: "←"; margin-right: 8px; font-weight: bold; }

/* === Messages === */
.message { padding: 12px 20px; border-radius: 10px; margin: 1.5rem 0; font-weight: 500; }
.message.success { background: #e6f4ea; border-left: 4px solid #28a745; color: #155724; }
.message.error { background: #fde9e9; border-left: 4px solid #dc3545; color: #721c24; }

/* === Formulaires === */
label { display: block; margin: 1.2rem 0 0.5rem; font-weight: 600; color: #2e1a47; }
input[type="text"], input[type="number"] {
    width: 100%; max-width: 400px; padding: 14px; border: 2px solid #e0d0eb; border-radius: 12px;
    font-size: 1rem;
}
.btn {
    display: block; width: 100%; max-width: 400px; background: #6a0dad; color: white; padding: 12px 24px;
    border: none; border-radius: 12px; font-weight: 600; font-size: 1rem; cursor: pointer; margin-top: 20px;
}

/* === Tables === */
.table-responsive { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; margin: 1.5rem 0; border-radius: 12px; overflow: hidden; }
th, td { padding: 14px 18px; text-align: left; border-bottom: 1px solid #e0d0eb; }
th { background: #6a0dad; color: white; font-weight: 600; }
tr:nth-child(even) { background-color: #faf7ff; }
.success-text { color: #28a745; font-weight: 600; }
.danger-text { color: #dc3545; font-weight: 600; }

/* Autres styles d'état */
.loading, .empty { text-align: center; color: #5a4a66; font-style: italic; padding: 20px; }

</style>
