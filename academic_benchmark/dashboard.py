import streamlit as st
import pandas as pd
import plotly.express as px
import os
from pathlib import Path

# Sayfa yapılandırması
st.set_page_config(page_title="UniRide Academic Dashboard", page_icon="🎓", layout="wide")

# Proje kökünü güvenli şekilde bul
_DASHBOARD_DIR = Path(__file__).resolve().parent

# Veri dizinlerini tanımla
RESULT_DIRS = [
    str(_DASHBOARD_DIR / "results"),
    str(_DASHBOARD_DIR / "numba_results"),
    str(_DASHBOARD_DIR / "sota_results"),
]

# Veri yükleme (Önbellekli - Caching)
@st.cache_data
def load_data():
    all_summary = []
    all_progress = []
    all_tuning = []
    
    for d in RESULT_DIRS:
        summary_path = os.path.join(d, "benchmark_summary.csv")
        progress_path = os.path.join(d, "benchmark_progress.csv")
        tuning_path = os.path.join(d, "tuning_progress.csv")
        
        if os.path.exists(summary_path):
            all_summary.append(pd.read_csv(summary_path))
        if os.path.exists(progress_path):
            all_progress.append(pd.read_csv(progress_path))
        if os.path.exists(tuning_path):
            all_tuning.append(pd.read_csv(tuning_path))
            
    summary_df = pd.concat(all_summary, ignore_index=True) if all_summary else pd.DataFrame()
    progress_df = pd.concat(all_progress, ignore_index=True) if all_progress else pd.DataFrame()
    tuning_df = pd.concat(all_tuning, ignore_index=True) if all_tuning else pd.DataFrame()
    
    # Eger summary_df bos ama progress_df doluysa, progress_df'den ozet uret
    if summary_df.empty and not progress_df.empty:
        summary_df = progress_df.groupby(['problem', 'strategy']).agg({
            'avg_length': 'mean',
            'avg_gap': 'mean',
            'avg_time_ms': 'mean',
            'n_runs': 'max'
        }).reset_index()
    
    return summary_df, progress_df, tuning_df

summary_df, progress_df, tuning_df = load_data()

st.title("🎓 UniRide Academic TSP Benchmark Dashboard")

if summary_df.empty and progress_df.empty and tuning_df.empty:
    st.warning("⚠️ No benchmark results found in the 'results/' directory. Please run the Master Engine first.")
    st.stop()

# --- SIDEBAR (Filtreler) ---
st.sidebar.header("🛠️ Data Filters")
all_probs = [p for p in summary_df['problem'].unique() if pd.notna(p)] if not summary_df.empty else []
all_algos = [a for a in summary_df['strategy'].unique() if pd.notna(a)] if not summary_df.empty else []

selected_probs = st.sidebar.multiselect("Select TSP Problems", all_probs, default=all_probs)
selected_algos = st.sidebar.multiselect("Select Algorithms", all_algos, default=all_algos)

# Verileri Filtrele
filtered_summary = pd.DataFrame()
filtered_progress = pd.DataFrame()

if not summary_df.empty:
    filtered_summary = summary_df[summary_df['problem'].isin(selected_probs) & summary_df['strategy'].isin(selected_algos)]
if not progress_df.empty:
    filtered_progress = progress_df[progress_df['problem'].isin(selected_probs) & progress_df['strategy'].isin(selected_algos)]

# --- SEKMELER (TABS) ---
tab1, tab2, tab3 = st.tabs(["🏆 Leaderboard & LaTeX", "📊 Statistical Robustness", "🎛️ DoE Parameter Analysis"])

# SEKME 1: Liderlik Tablosu ve LaTeX
with tab1:
    st.subheader("Performance Summary (Aggregated)")
    st.markdown("Averaged metrics across all independent runs. Highlights the best performing algorithms.")
    
    if not filtered_summary.empty:
        # Her problem bazında en iyi (min) değerleri hesapla ve renklendir
        def highlight_best_per_problem(df):
            # Bos bir stil DataFrame'i olustur
            style_df = pd.DataFrame('', index=df.index, columns=df.columns)
            
            # Her bir problem icin ayri ayri en iyileri bul
            for prob in df['problem'].unique():
                prob_idx = df[df['problem'] == prob].index
                for col in ['avg_gap', 'avg_time_ms']:
                    if col in df.columns:
                        min_val = df.loc[prob_idx, col].min()
                        # En iyi degeri yesil yap
                        best_mask = (df.loc[prob_idx, col] == min_val)
                        style_df.loc[prob_idx[best_mask], col] = 'background-color: rgba(0, 255, 0, 0.2); font-weight: bold'
            return style_df

        st.dataframe(
            filtered_summary.style.apply(highlight_best_per_problem, axis=None),
            use_container_width=True
        )
        
        st.markdown("### 📜 Export as LaTeX Table")
        st.markdown("This version **bolds** the best values for each problem (academic standard).")
        
        if st.button("Generate Academic LaTeX Code"):
            # LaTeX icin best degerleri bold yapacak bir kopya olustur
            latex_df = filtered_summary.copy()
            for prob in latex_df['problem'].unique():
                prob_mask = (latex_df['problem'] == prob)
                for col in ['avg_gap', 'avg_time_ms']:
                    min_val = latex_df.loc[prob_mask, col].min()
                    latex_df.loc[prob_mask & (latex_df[col] == min_val), col] = \
                        latex_df.loc[prob_mask & (latex_df[col] == min_val), col].apply(lambda x: f"\\textbf{{{x:.4f}}}")
            
            latex_code = latex_df.to_latex(index=False, escape=False)
            st.code(latex_code, language='latex')
    else:
        st.info("Please select at least one problem and one algorithm from the sidebar.")

# SEKME 2: İstatistiksel Sağlamlık (Box Plots)
with tab2:
    st.subheader("Algorithm Robustness & Variance Analysis")
    st.markdown("Box-and-whisker plots generated from multi-run raw data. Analyzes stochastic variance.")
    
    if not filtered_progress.empty:
        col1, col2 = st.columns([1, 3])
        with col1:
            metric = st.radio("Select Evaluation Metric:", ["avg_gap", "avg_time_ms", "avg_length"])
        
        with col2:
            fig = px.box(
                filtered_progress, 
                x="problem", 
                y=metric, 
                color="strategy", 
                title=f"Statistical Distribution of {metric.replace('_', ' ').title()}",
                points="all", # Bütün noktaları göster
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            # Grafik düzenlemeleri (Makale formatı için temiz arkaplan)
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", boxmode='group')
            fig.update_xaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgrey')
            fig.update_yaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgrey')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No raw multi-run data available. Ensure `benchmark_progress.csv` contains data.")

# SEKME 3: Parametre Optimizasyonu (DoE Tuning)
with tab3:
    st.subheader("Design of Experiments (DoE) Parameter Tuning")
    st.markdown("Visualizes hyperparameter sensitivity during the tuning phase.")
    
    if not tuning_df.empty:
        sel_algo_tune = st.selectbox("Select Algorithm for Tuning Analysis", tuning_df['strategy'].unique())
        tune_data = tuning_df[tuning_df['strategy'] == sel_algo_tune]
        
        if not tune_data.empty:
            fig2 = px.scatter(
                tune_data, 
                x="combo_idx", 
                y="avg_gap", 
                color="problem", 
                size="avg_time_ms",
                hover_data=["params_json"],
                title=f"Parameter Configuration Grid Search vs Optimality Gap ({sel_algo_tune})"
            )
            fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white")
            fig2.update_xaxes(showgrid=True, gridcolor='lightgrey')
            fig2.update_yaxes(showgrid=True, gridcolor='lightgrey')
            st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("### Tuning Configurations (Ranked by Gap)")
            st.dataframe(tune_data[['problem', 'combo_idx', 'avg_gap', 'params_json']].sort_values('avg_gap'))
    else:
        st.info("No tuning data found. You must run the engine in 'TUNING' mode first.")
