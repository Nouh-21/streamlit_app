import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

# Configuration de l'application
st.set_page_config(
    page_title="Dashboard Contributions Financières",
    page_icon="💶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cache pour les données volumineuses
@st.cache_data(ttl=3600, show_spinner="Chargement des données...")
def load_data(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, parse_dates=['date_virement'])
        else:
            df = pd.read_excel(uploaded_file, parse_dates=['date_virement'])
        
        # Validation des données
        required_columns = {'telephone', 'montant', 'date_virement'}
        if not required_columns.issubset(df.columns):
            raise ValueError("Colonnes manquantes dans le fichier")
            
        # Nettoyage des données
        df = df.dropna(subset=['date_virement', 'montant'])
        df['montant'] = pd.to_numeric(df['montant'], errors='coerce')
        df = df[df['montant'] > 0]
        df = df.sort_values('date_virement', ascending=False)
        
        return df
    
    except Exception as e:
        st.error(f"Erreur de chargement : {str(e)}")
        return None

# Interface utilisateur
st.title("💶 Dashboard de Gestion des Contributions")

# Téléchargement de fichier
uploaded_file = st.sidebar.file_uploader(
    "📤 Importer des transactions",
    type=['csv', 'xlsx'],
    help="Format requis : telephone, montant, date_virement"
)

# Chargement des données
df = load_data(uploaded_file) if uploaded_file else None

# Message d'information initial
if df is None:
    st.info("Veuillez importer un fichier CSV/Excel pour commencer")
    st.stop()

# Gestion des dates
min_date = df['date_virement'].min().date()
max_date = df['date_virement'].max().date()

# Widgets de filtrage
with st.sidebar.expander("⚙️ Filtres", expanded=True):
    # Sélection de période
    date_range = st.date_input(
        "Période",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    # Filtre rapide par période prédéfinie
    preset = st.radio("Période prédéfinie", ["Personnalisée", "7 derniers jours", "30 derniers jours"])
    
    if preset == "7 derniers jours":
        date_range = [max_date - timedelta(days=7), max_date]
    elif preset == "30 derniers jours":
        date_range = [max_date - timedelta(days=30), max_date]

    # Filtre par montant
    min_amount, max_amount = st.slider(
        "Fourchette de montants (€)",
        min_value=float(df['montant'].min()),
        max_value=float(df['montant'].max()),
        value=(float(df['montant'].min()), float(df['montant'].max()))
    )

# Filtrage des données
filtered_df = df[
    (df['date_virement'].dt.date >= date_range[0]) &
    (df['date_virement'].dt.date <= date_range[1]) &
    (df['montant'] >= min_amount) &
    (df['montant'] <= max_amount)
]

# KPI Principaux
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Budget Total", f"{filtered_df['montant'].sum():,.2f} €")
with col2:
    st.metric("Moyenne Journalière", f"{filtered_df['montant'].mean():,.2f} €/j")
with col3:
    st.metric("Nombre de Transactions", len(filtered_df))

# Visualisation temporelle
st.subheader("Évolution des Contributions")
tab1, tab2 = st.tabs(["Courbe Chronologique", "Répartition par Montant"])

with tab1:
    time_agg = st.selectbox("Périodicité", ["Journalière", "Hebdomadaire", "Mensuelle"])
    
    freq_map = {
        "Journalière": "D",
        "Hebdomadaire": "W",
        "Mensuelle": "M"
    }
    
    resampled_df = filtered_df.set_index('date_virement').resample(freq_map[time_agg]).agg({
        'montant': 'sum',
        'telephone': 'count'
    }).reset_index()
    
    fig = px.area(
        resampled_df,
        x='date_virement',
        y='montant',
        title="Montant des Contributions",
        labels={'montant': 'Montant (€)', 'date_virement': 'Date'},
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig = px.histogram(
        filtered_df,
        x='montant',
        nbins=20,
        title="Distribution des Montants",
        labels={'montant': 'Montant (€)'},
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

# Détail des transactions
st.subheader("Dernières Transactions")
st.dataframe(
    filtered_df.rename(columns={
        'telephone': '📱 Téléphone',
        'montant': '💶 Montant',
        'date_virement': '📅 Date'
    }),
    column_config={
        "📱 Téléphone": st.column_config.TextColumn(width="medium"),
        "💶 Montant": st.column_config.NumberColumn(format="€ %.2f"),
        "📅 Date": st.column_config.DateColumn(format="DD/MM/YYYY")
    },
    use_container_width=True,
    hide_index=True,
    height=400
)

# Optimisations supplémentaires
st.sidebar.markdown("---")
st.sidebar.download_button(
    "📥 Exporter les données filtrées",
    filtered_df.to_csv(index=False).encode('utf-8'),
    "transactions_filtrees.csv"
)

# Gestion des erreurs
if filtered_df.empty:
    st.warning("Aucune transaction trouvée avec les filtres actuels")

# Style personnalisé
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        color: #2ecc71;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
    }
    .stDataFrame {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)
