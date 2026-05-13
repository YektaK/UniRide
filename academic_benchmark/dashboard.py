import streamlit as st
import pandas as pd
import plotly.express as px
import os
import glob
from pathlib import Path
from academic_benchmark.dashboard_utils import derive_filter_options

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
@st.cache_data(ttl=3600)
def load_data():
    all_summary = []
    all_progress = []
    all_tuning = []
    loaded_sources = {"summary": [], "progress": [], "tuning": []}

    for d in RESULT_DIRS:
        summary_path = os.path.join(d, "benchmark_summary.csv")
        progress_path = os.path.join(d, "benchmark_progress.csv")
        if os.path.exists(summary_path):
            all_summary.append(pd.read_csv(summary_path))
            loaded_sources["summary"].append(summary_path)
        if os.path.exists(progress_path):
            all_progress.append(pd.read_csv(progress_path))
            loaded_sources["progress"].append(progress_path)
        for tuning_path in glob.glob(os.path.join(d, "**", "tuning_progress.csv"), recursive=True):
            all_tuning.append(pd.read_csv(tuning_path))
            loaded_sources["tuning"].append(tuning_path)

    summary_df = pd.concat(all_summary, ignore_index=True) if all_summary else pd.DataFrame()
    progress_df = pd.concat(all_progress, ignore_index=True) if all_progress else pd.DataFrame()
    tuning_df = pd.concat(all_tuning, ignore_index=True) if all_tuning else pd.DataFrame()

    # Load history for convergence curves (Task 4.3)
    history_dfs = []
    for d in RESULT_DIRS:
        for hist_path in glob.glob(os.path.join(d, "**", "smart_*.csv"), recursive=True):
            try:
                history_dfs.append(pd.read_csv(hist_path))
            except:
                pass
        # Also check benchmark_db/history
        history_dir = os.path.join(str(_DASHBOARD_DIR), "benchmark_db", "history")
        for hist_path in glob.glob(os.path.join(history_dir, "interrupted_smart_*.csv"), recursive=True):
            try:
                history_dfs.append(pd.read_csv(hist_path))
            except:
                pass
                
    history_df = pd.concat(history_dfs, ignore_index=True) if history_dfs else pd.DataFrame()

    return summary_df, progress_df, tuning_df, history_df, loaded_sources

summary_df, progress_df, tuning_df, history_df, loaded_sources = load_data()

st.title("🎓 UniRide Academic TSP Benchmark Dashboard")

if summary_df.empty and progress_df.empty and tuning_df.empty:
    st.warning("⚠️ No benchmark results found in the 'results/' directory. Please run the Master Engine first.")
    st.stop()

# --- SIDEBAR (Filtreler) ---
st.sidebar.header("🛠️ Data Filters")
all_probs, all_algos = derive_filter_options(summary_df, progress_df)

selected_probs = st.sidebar.multiselect("Select TSP Problems", all_probs, default=all_probs)
selected_algos = st.sidebar.multiselect("Select Algorithms", all_algos, default=all_algos)

with st.sidebar.expander("📁 Source Diagnostics"):
    st.markdown(f"**Summary files:** {len(loaded_sources['summary'])}")
    for s in loaded_sources['summary']:
        st.code(s, language="")
    st.markdown(f"**Progress files (raw):** {len(loaded_sources['progress'])}")
    for s in loaded_sources['progress']:
        st.code(s, language="")
    st.markdown(f"**Tuning files:** {len(loaded_sources['tuning'])}")
    for s in loaded_sources['tuning']:
        st.code(s, language="")
    if not progress_df.empty:
        st.markdown(f"**Progress rows:** {len(progress_df)}")
        if 'result_type' in progress_df.columns:
            raw_count = len(progress_df[progress_df['result_type'] == 'raw'])
            agg_count = len(progress_df[progress_df['result_type'] == 'aggregate'])
            st.markdown(f"**Raw:** {raw_count} | **Aggregate:** {agg_count}")

# Verileri Filtrele
filtered_summary = pd.DataFrame()
filtered_progress = pd.DataFrame()

if not summary_df.empty:
    filtered_summary = summary_df[summary_df['problem'].isin(selected_probs) & summary_df['strategy'].isin(selected_algos)]
if not progress_df.empty:
    raw_progress = progress_df[progress_df['result_type'] == 'raw'] if 'result_type' in progress_df.columns else progress_df
    filtered_progress = raw_progress[raw_progress['problem'].isin(selected_probs) & raw_progress['strategy'].isin(selected_algos)]

# --- SEKMELER (TABS) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏆 Leaderboard & LaTeX", "📊 Statistical Robustness", "🎛️ DoE Parameter Analysis", "🔬 Statistical Significance (Wilcoxon)", "📉 Convergence Curves"])

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

# SEKME 4: Statistical Significance (Wilcoxon Test)
with tab4:
    st.subheader("Wilcoxon Signed-Rank Test (Academic Proof)")
    st.markdown("Automated pairwise statistical testing of algorithm performance.")
    
    if not filtered_progress.empty:
        if len(selected_algos) >= 2:
            algo_A = st.selectbox("Select Algorithm A (Baseline)", selected_algos, index=0)
            algo_B = st.selectbox("Select Algorithm B (Proposed)", selected_algos, index=1)
            
            if algo_A != algo_B:
                st.markdown(f"Comparing **{algo_A}** vs **{algo_B}** across selected problems.")
                try:
                    from scipy.stats import wilcoxon
                    
                    results = []
                    for prob in selected_probs:
                        data_A = filtered_progress[(filtered_progress['problem'] == prob) & (filtered_progress['strategy'] == algo_A)]['avg_gap'].values
                        data_B = filtered_progress[(filtered_progress['problem'] == prob) & (filtered_progress['strategy'] == algo_B)]['avg_gap'].values
                        
                        if len(data_A) > 0 and len(data_B) > 0 and len(data_A) == len(data_B):
                            # Wilcoxon test
                            stat, p_val = wilcoxon(data_A, data_B, zero_method='zsplit')
                            winner = algo_A if data_A.mean() < data_B.mean() else algo_B
                            sig = "Yes" if p_val < 0.05 else "No"
                            results.append({
                                "Problem": prob,
                                "Mean A": data_A.mean(),
                                "Mean B": data_B.mean(),
                                "p-value": p_val,
                                "Significant?": sig,
                                "Winner": winner if sig == "Yes" else "Tie"
                            })
                            
                    if results:
                        sig_df = pd.DataFrame(results)
                        st.dataframe(sig_df)
                        
                        wins = len(sig_df[sig_df['Winner'] == algo_B])
                        ties = len(sig_df[sig_df['Winner'] == 'Tie'])
                        losses = len(sig_df[sig_df['Winner'] == algo_A])
                        
                        st.markdown(f"### LaTeX Automated Statement")
                        st.code(f"\\textbf{{{algo_B}}} statistically significantly outperforms {algo_A} on {wins} out of {len(results)} instances (Wilcoxon Signed-Rank, $p < 0.05$), with {ties} statistical ties.", language="latex")
                    else:
                        st.warning("Not enough matched multi-run data to perform Wilcoxon test.")
                except ImportError:
                    st.error("Please install scipy (`pip install scipy`) to use the statistical testing features.")
        else:
            st.info("Select at least 2 algorithms to compare.")
    else:
        st.info("No raw data available for statistical testing.")

# SEKME 5: Convergence Curves
with tab5:
    st.subheader("Convergence Analysis (Exploration vs Exploitation)")
    if not history_df.empty and 'convergence_profile' in history_df.columns:
        filtered_hist = history_df[history_df['problem'].isin(selected_probs) & history_df['algorithm'].isin(selected_algos)]
        if not filtered_hist.empty:
            prob_to_plot = st.selectbox("Select Problem to View", filtered_hist['problem'].unique())
            plot_data = filtered_hist[filtered_hist['problem'] == prob_to_plot]
            
            import ast
            plot_records = []
            for _, row in plot_data.iterrows():
                try:
                    profile = ast.literal_eval(row['convergence_profile'])
                    if isinstance(profile, list):
                        for i, val in enumerate(profile):
                            plot_records.append({
                                "Algorithm": row['algorithm'],
                                "Run": row['run'],
                                "Iteration": i,
                                "Cost": val
                            })
                except:
                    pass
                    
            if plot_records:
                curve_df = pd.DataFrame(plot_records)
                fig3 = px.line(
                    curve_df, 
                    x="Iteration", 
                    y="Cost", 
                    color="Algorithm", 
                    line_group="Run", 
                    title=f"Convergence Curve - {prob_to_plot}",
                    hover_name="Algorithm"
                )
                fig3.update_layout(plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No valid convergence profiles found for this problem.")
    else:
        st.info("No convergence profile data available.")
