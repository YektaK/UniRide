import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import numpy as np
from pathlib import Path
from datetime import datetime
from dashboard_utils import derive_filter_options

# Sayfa yapılandırması
st.set_page_config(page_title="UniRide Academic Dashboard", page_icon="🎓", layout="wide")

# Proje kökünü güvenli şekilde bul
_DASHBOARD_DIR = Path(__file__).resolve().parent

# Veri dizinlerini tanımla
RESULT_DIRS = [
    str(_DASHBOARD_DIR / "sota_results"),
    str(_DASHBOARD_DIR / "numba_results"),
]

# Veri yükleme (Önbellekli - Caching)
@st.cache_data(ttl=60)
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
            try:
                df = pd.read_csv(progress_path)
            except pd.errors.ParserError:
                # Handle inconsistent column counts (e.g. result_type added mid-file)
                import csv, io
                with open(progress_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                if rows:
                    header = rows[0]
                    ncols = len(header)
                    # Detect if any row has more columns — if so, expand header
                    max_cols = max(len(r) for r in rows)
                    if max_cols > ncols:
                        # Insert missing column names (result_type, etc.)
                        extra = max_cols - ncols
                        # Insert before params_json (last column)
                        insert_at = ncols - 1
                        for i in range(extra):
                            header.insert(insert_at + i, f"extra_col_{i}")
                        ncols = len(header)
                    # Pad or trim each row to match header length
                    fixed = [header]
                    for row in rows[1:]:
                        if len(row) != ncols:
                            row = (row + [""] * ncols)[:ncols]
                        fixed.append(row)
                    buf = io.StringIO()
                    writer = csv.writer(buf)
                    for row in fixed:
                        writer.writerow(row)
                    buf.seek(0)
                    df = pd.read_csv(buf)
                else:
                    df = pd.DataFrame()
            all_progress.append(df)
            loaded_sources["progress"].append(progress_path)
        for tuning_path in glob.glob(os.path.join(d, "**", "tuning_progress.csv"), recursive=True):
            all_tuning.append(pd.read_csv(tuning_path))
            loaded_sources["tuning"].append(tuning_path)

    summary_df = pd.concat(all_summary, ignore_index=True) if all_summary else pd.DataFrame()
    progress_df = pd.concat(all_progress, ignore_index=True) if all_progress else pd.DataFrame()
    tuning_df = pd.concat(all_tuning, ignore_index=True) if all_tuning else pd.DataFrame()

    # Coerce numeric columns (handles schema mismatches from CSV normalization)
    for col in ['avg_length', 'avg_gap', 'avg_time_ms', 'n_runs']:
        if col in progress_df.columns:
            progress_df[col] = pd.to_numeric(progress_df[col], errors='coerce')
    for col in ['avg_length', 'avg_gap', 'avg_time_ms', 'n_runs']:
        if col in summary_df.columns:
            summary_df[col] = pd.to_numeric(summary_df[col], errors='coerce')

    # Load history for convergence curves
    history_dfs = []
    history_dir = os.path.join(str(_DASHBOARD_DIR), "benchmark_db", "history")
    if os.path.isdir(history_dir):
        for hist_path in glob.glob(os.path.join(history_dir, "smart_*.csv"), recursive=True):
            try:
                history_dfs.append(pd.read_csv(hist_path))
            except Exception:
                pass
        for hist_path in glob.glob(os.path.join(history_dir, "interrupted_smart_*.csv"), recursive=True):
            try:
                history_dfs.append(pd.read_csv(hist_path))
            except Exception:
                pass

    history_df = pd.concat(history_dfs, ignore_index=True) if history_dfs else pd.DataFrame()

    return summary_df, progress_df, tuning_df, history_df, loaded_sources

summary_df, progress_df, tuning_df, history_df, loaded_sources = load_data()

st.title("🎓 UniRide Academic TSP Benchmark Dashboard")

# Last updated timestamp
st.caption(f"🕒 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if summary_df.empty and progress_df.empty and tuning_df.empty:
    st.warning("⚠️ No benchmark results found. Please run the Master Engine first.")
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

# Auto-refresh button
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Verileri Filtrele
filtered_summary = pd.DataFrame()
filtered_progress = pd.DataFrame()

if not summary_df.empty:
    filtered_summary = summary_df[summary_df['problem'].isin(selected_probs) & summary_df['strategy'].isin(selected_algos)]
if not progress_df.empty:
    raw_progress = progress_df[progress_df['result_type'] == 'raw'] if 'result_type' in progress_df.columns else progress_df
    filtered_progress = raw_progress[raw_progress['problem'].isin(selected_probs) & raw_progress['strategy'].isin(selected_algos)]

# --- SEKMELER (TABS) ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏆 Leaderboard & LaTeX",
    "📊 Statistical Robustness",
    "🎛️ DoE Parameter Analysis",
    "🔬 Statistical Significance (Wilcoxon)",
    "📉 Convergence Curves",
    "⚔️ Algorithm Comparison",
    "🔥 Edge Frequency Heatmap"
])

# SEKME 1: Liderlik Tablosu ve LaTeX
with tab1:
    st.subheader("Performance Summary (Aggregated)")
    st.markdown("Averaged metrics across all independent runs. Highlights the best performing algorithms.")

    if not filtered_summary.empty:
        def highlight_best_per_problem(df):
            style_df = pd.DataFrame('', index=df.index, columns=df.columns)
            for prob in df['problem'].unique():
                prob_idx = df[df['problem'] == prob].index
                for col in ['avg_gap', 'avg_time_ms']:
                    if col in df.columns:
                        min_val = df.loc[prob_idx, col].min()
                        best_mask = (df.loc[prob_idx, col] == min_val)
                        style_df.loc[prob_idx[best_mask], col] = 'background-color: rgba(0, 255, 0, 0.2); font-weight: bold'
            return style_df

        st.dataframe(
            filtered_summary.style.apply(highlight_best_per_problem, axis=None),
            use_container_width=True
        )

        st.markdown("### 📜 Export as LaTeX Table")
        st.markdown("Generates a **paper-ready** LaTeX table with best values in bold.")

        col_latex_type, col_latex_btn = st.columns([1, 1])
        with col_latex_type:
            latex_format = st.selectbox("LaTeX Target", ["booktabs (journal)", "longtable (many rows)"], index=0)

        with col_latex_btn:
            st.markdown("&nbsp;")
            if st.button("Generate Academic LaTeX Code"):
                latex_df = filtered_summary.copy()
                fmt_cols = [c for c in ['avg_gap', 'avg_time_ms'] if c in latex_df.columns]

                for col in fmt_cols:
                    latex_df[col] = latex_df[col].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "N/A")

                # Add BSF gap notation for unknown-optimal problems
                if 'gap_type' in latex_df.columns:
                    latex_df['gap_note'] = latex_df['gap_type'].apply(
                        lambda gt: r'\textsuperscript{\textdagger}' if gt == 'bsf' else ''
                    )

                for prob in latex_df['problem'].unique():
                    prob_mask = (latex_df['problem'] == prob)
                    orig = filtered_summary[prob_mask]
                    for col in fmt_cols:
                        min_val = orig[col].min()
                        cell_mask = prob_mask & (orig[col] == min_val)
                        for idx in latex_df[cell_mask].index:
                            raw = latex_df.at[idx, col]
                            latex_df.at[idx, col] = f"\\textbf{{{raw}}}"

                # Add footnote for BSF gaps
                has_bsf = 'gap_type' in latex_df.columns and (latex_df['gap_type'] == 'bsf').any()
                footnote = r"\textsuperscript{\textdagger} Best-So-Far gap (unknown optimal)" if has_bsf else ""

                if latex_format == "longtable (many rows)":
                    latex_code = latex_df.to_latex(
                        index=False, escape=False, longtable=True,
                        column_format="l" + "c" * (len(latex_df.columns) - 1)
                    )
                else:
                    latex_code = latex_df.to_latex(
                        index=False, escape=False,
                        column_format="l" + "c" * (len(latex_df.columns) - 1)
                    )
                if footnote:
                    latex_code += f"\n\n% Note: {footnote}"
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
                points="all",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
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

                        st.markdown("### LaTeX Summary")
                        st.code(
                            f"\\textbf{{{algo_B}}} significantly outperforms {algo_A} "
                            f"on {wins}/{len(results)} instances "
                            f"(Wilcoxon $p < 0.05$), with {ties} ties.",
                            language="latex"
                        )

                        st.markdown("### Full LaTeX Table")
                        sig_table = sig_df.copy()
                        sig_table['p-value'] = sig_table['p-value'].apply(
                            lambda p: f"$<0.001$" if p < 0.001 else f"${p:.4f}$"
                        )
                        latex_wilcoxon = sig_table.to_latex(
                            index=False, escape=False,
                            column_format="lrrrrl"
                        )
                        st.code(latex_wilcoxon, language="latex")
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
                except Exception:
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

# SEKME 6: Algorithm Comparison Matrix (NEW)
with tab6:
    st.subheader("Pairwise Algorithm Comparison Matrix")
    st.markdown("Gap difference between algorithm pairs per problem. "
                "**Negative** = Row algorithm better, **Positive** = Column algorithm better.")

    if not filtered_summary.empty and len(selected_algos) >= 2:
        # Build comparison matrix
        comparison_data = []
        for i, algo_a in enumerate(selected_algos):
            for algo_b in selected_algos[i+1:]:
                for prob in selected_probs:
                    row_a = filtered_summary[(filtered_summary['problem'] == prob) & (filtered_summary['strategy'] == algo_a)]
                    row_b = filtered_summary[(filtered_summary['problem'] == prob) & (filtered_summary['strategy'] == algo_b)]
                    if not row_a.empty and not row_b.empty:
                        gap_a = row_a['avg_gap'].values[0]
                        gap_b = row_b['avg_gap'].values[0]
                        if pd.notna(gap_a) and pd.notna(gap_b):
                            diff = gap_a - gap_b
                            comparison_data.append({
                                "Problem": prob,
                                "Algorithm A": algo_a,
                                "Algorithm B": algo_b,
                                "Gap A": round(gap_a, 4),
                                "Gap B": round(gap_b, 4),
                                "Difference (A-B)": round(diff, 4),
                                "Better": algo_a if diff < 0 else algo_b
                            })

        if comparison_data:
            comp_df = pd.DataFrame(comparison_data)
            st.dataframe(comp_df, use_container_width=True)

            # Heatmap visualization
            st.markdown("### Heatmap: Gap Difference (A vs B)")
            pivot = comp_df.pivot_table(
                index="Algorithm A", columns="Problem", values="Difference (A-B)", aggfunc="mean"
            )
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=pivot.columns,
                y=pivot.index,
                colorscale="RdYlGn_r",
                text=np.round(pivot.values, 2),
                texttemplate="%{text}",
                colorbar=dict(title="Gap Diff"),
                zmid=0
            ))
            fig_heatmap.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis_title="Problem", yaxis_title="Algorithm A vs B"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("Not enough data to build comparison matrix.")
    else:
        st.info("Select at least 2 algorithms and run benchmarks to see comparisons.")

# SEKME 7: Edge Frequency Heatmap (NEW)
with tab7:
    st.subheader("Edge Frequency Analysis")
    st.markdown("Shows how often each edge appears across top solutions. "
                "High-frequency edges (>70%) indicate consensus structural patterns.")

    if not filtered_summary.empty:
        prob_edge = st.selectbox("Select Problem for Edge Analysis", filtered_summary['problem'].unique())
        prob_summary = filtered_summary[filtered_summary['problem'] == prob_edge]

        # Find best algorithms for this problem
        if 'avg_gap' in prob_summary.columns:
            best_algos = prob_summary.nsmallest(3, 'avg_gap')['strategy'].tolist()
        else:
            best_algos = prob_summary['strategy'].tolist()[:3]

        st.markdown(f"Analyzing edges from top {len(best_algos)} algorithms: **{', '.join(best_algos)}**")

        # Try to load tour data from progress CSV
        if not filtered_progress.empty:
            prob_progress = filtered_progress[
                (filtered_progress['problem'] == prob_edge) &
                (filtered_progress['strategy'].isin(best_algos))
            ]

            if not prob_progress.empty and 'tour' in prob_progress.columns:
                import ast
                edge_counts = {}
                total_tours = 0

                for _, row in prob_progress.iterrows():
                    try:
                        tour_str = row['tour']
                        if isinstance(tour_str, str):
                            tour = ast.literal_eval(tour_str)
                        elif isinstance(tour_str, list):
                            tour = tour_str
                        else:
                            continue

                        n = len(tour)
                        for i in range(n):
                            a, b = tour[i], tour[(i + 1) % n]
                            edge = (min(a, b), max(a, b))
                            edge_counts[edge] = edge_counts.get(edge, 0) + 1
                        total_tours += 1
                    except Exception:
                        pass

                if edge_counts and total_tours > 0:
                    # Build edge frequency matrix
                    nodes = sorted(set(n for edge in edge_counts for n in edge))
                    n_nodes = len(nodes)
                    node_idx = {n: i for i, n in enumerate(nodes)}
                    freq_matrix = np.zeros((n_nodes, n_nodes))

                    for (a, b), count in edge_counts.items():
                        freq = count / total_tours
                        freq_matrix[node_idx[a], node_idx[b]] = freq
                        freq_matrix[node_idx[b], node_idx[a]] = freq

                    # Heatmap
                    fig_edge = go.Figure(data=go.Heatmap(
                        z=freq_matrix,
                        x=nodes,
                        y=nodes,
                        colorscale="YlOrRd",
                        text=np.round(freq_matrix, 2),
                        texttemplate="%{text}",
                        colorbar=dict(title="Frequency"),
                        zmin=0, zmax=1
                    ))
                    fig_edge.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white",
                        xaxis_title="Node", yaxis_title="Node",
                        title=f"Edge Frequency Matrix - {prob_edge} ({total_tours} tours)"
                    )
                    st.plotly_chart(fig_edge, use_container_width=True)

                    # Consensus edges (>70%)
                    consensus = [(a, b) for (a, b), count in edge_counts.items()
                                 if count / total_tours > 0.7]
                    if consensus:
                        st.markdown(f"### 🔗 Consensus Edges (>{70}%)")
                        st.markdown(f"Found **{len(consensus)}** high-frequency edges:")
                        consensus_df = pd.DataFrame([
                            {"Edge": f"{a} ↔ {b}", "Frequency": f"{edge_counts[(a,b)]/total_tours:.1%}"}
                            for a, b in sorted(consensus)
                        ])
                        st.dataframe(consensus_df, use_container_width=True)
                else:
                    st.info("No valid tour data found for edge analysis.")
            else:
                st.info("Tour data not available in progress CSV. "
                        "Ensure engines save tour information to enable edge analysis.")
        else:
            st.info("No progress data available for edge analysis.")
    else:
        st.info("Select at least one problem to analyze edge frequencies.")
