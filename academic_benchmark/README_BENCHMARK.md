# UniRide Academic Benchmark Framework

[Türkçe Sürüm İçin Aşağıya Kaydırın](#uniride-akademik-benchmark-altyapısı-türkçe)

## 1. Introduction
The UniRide Academic Benchmark Framework is a state-of-the-art computational environment designed for rigorous testing and evaluation of Traveling Salesman Problem (TSP) algorithms. The framework adopts a **Consolidated Architecture**, unifying both modern cutting-edge algorithms and classical meta-heuristics under a single, highly parallelized, and reproducible environment.

The architecture is built upon two master engines:
*   **`master_sota_engine.py`**: Designed to run State-of-the-Art (SOTA) TSP solvers such as E²BSO, R²DMA, and P-AOEA.
*   **`master_numba_engine.py`**: Engineered for classical meta-heuristics (GA, PSO, GWO, HHO, etc.) utilizing **Numba** for Just-In-Time (JIT) compilation, bridging the gap between Python's flexibility and C++-level execution speed.

Both engines are powered by a unified backend (`benchmark_utils.py`), which provides shared metadata management, real-time ETA tracking (`ETATracker`), and Windows-safe parallel execution capabilities via `ProcessPoolExecutor`.

## 2. Installation
Ensure that your Python environment (Python 3.9+) is active. Install the required dependencies using `pip`:

```bash
pip install numpy numba tqdm
```
*(Note: Standard libraries like `multiprocessing`, `concurrent.futures`, `json`, and `csv` are built into Python).*

## 3. Execution Modes
The engines operate in two distinct modes to serve different academic research needs:

*   **`DEFAULT` Mode (Direct Benchmark):** 
    Executes the algorithms directly using adaptive or predefined default parameters. This mode is used for final performance evaluations, scalability tests, and generating the benchmark results for publications.
*   **`TUNING` Mode (Design of Experiments - DoE):** 
    Performs a systematic grid or fractional parameter search (Design of Experiments) to find the globally optimal hyperparameters for the selected algorithms before benchmarking. It prevents biased results by optimizing the parameter space automatically.

## 4. CLI Arguments
Both engines can be run interactively via menus or non-interactively via Command Line Interface (CLI) arguments. This is particularly useful for CI/CD pipelines or batch scripting.

| Argument | Description | Example |
| :--- | :--- | :--- |
| `--mode` | Sets the execution mode (`default` or `tuning`). | `--mode default` |
| `--algos` | Comma-separated list of algorithms to evaluate. | `--algos GA,PSO` |
| `--runs` | Number of independent repetitions for each algorithm. | `--runs 5` |
| `--size-limit` | Maximum dimension/size of the TSP problem to include. | `--size-limit 200` |

**Example Command:**
```bash
python academic_benchmark/master_numba_engine.py --mode default --algos GA,PSO --runs 3 --size-limit 150
```

## 5. Result Management
To guarantee data integrity and academic reproducibility, the framework uses a highly structured output hierarchy located in the `results/` folder:

*   **`benchmark_progress.csv` & `tuning_progress.csv`**: Raw, incremental logs of every single run. Prevents data loss during long execution times.
  * **Schema (`benchmark_progress.csv`):** `timestamp`, `problem`, `strategy`, `avg_length`, `avg_gap`, `avg_time_ms`, `n_runs`, `result_type`, `params_json`.
  * **`result_type` semantics:**
    - `"raw"` — SOTA engine: one row per independent run (`n_runs=1`). Feeds robustness box-plots.
    - `"aggregate"` — Numba engine: one row per parameter combo, averaged across all `n_runs`. Feeds leaderboard summary.
*   **`benchmark_summary.csv`**: The aggregated final results (average lengths, gaps, times) used directly for statistical analysis.
*   **`best_params.json`**: Stores the optimal hyperparameter sets discovered during the `TUNING` mode.
*   **`metadata.json`**: The global state tracker. It maintains caching hashes, resumes interrupted benchmarks, and ensures that redundant calculations are skipped.

## 6. Developer Notes
*   **Windows Multiprocessing Safety:** Python's native `multiprocessing.Pool` is notoriously unstable on Windows. This architecture leverages `concurrent.futures.ProcessPoolExecutor` combined with isolated memory spaces to prevent silent hangs, RAM overflow, and freezing. 
*   **Numba JIT Warm-up:** The `master_numba_engine.py` utilizes `@njit(nogil=True)` decorators. During the very first execution of an algorithm, Numba must compile the Python byte-code to machine code. This initial "warm-up" phase takes a few seconds and is excluded from the actual benchmarking time to ensure fair algorithmic comparison.

---
<br><br>

# UniRide Akademik Benchmark Altyapısı (Türkçe)

## 1. Giriş
UniRide Akademik Benchmark Altyapısı, Gezgin Satıcı Problemi (TSP) algoritmalarının titiz bir şekilde test edilmesi ve değerlendirilmesi için tasarlanmış modern bir hesaplama ortamıdır. Bu altyapı, en son teknoloji algoritmalar ile klasik meta-sezgiselleri **Konsolide Edilmiş Mimari (Consolidated Architecture)** altında, yüksek paralelliğe sahip ve tekrarlanabilir (reproducible) tek bir çatı altında birleştirir.

Mimari iki ana motor üzerine inşa edilmiştir:
*   **`master_sota_engine.py`**: E²BSO, R²DMA ve P-AOEA gibi literatürdeki en güncel (State-of-the-Art) TSP çözücülerini çalıştırmak için tasarlanmıştır.
*   **`master_numba_engine.py`**: Klasik meta-sezgiseller (GA, PSO, GWO, HHO vb.) için tasarlanmıştır. Python'ın esnekliğini C++ hızına ulaştıran **Numba JIT (Just-In-Time)** derleyicisinden güç alır.

Her iki motor da `benchmark_utils.py` üzerinden çalışır. Bu çekirdek yapı; ortak metadata yönetimi, gerçek zamanlı süre tahmini (`ETATracker`) ve `ProcessPoolExecutor` aracılığıyla Windows için tamamen güvenli (crash-free) çoklu çekirdek işleme yetenekleri sunar.

## 2. Kurulum
Python (3.9+) sanal ortamınızın aktif olduğundan emin olun. Gerekli kütüphaneleri `pip` kullanarak yükleyin:

```bash
pip install numpy numba tqdm
```
*(Not: `multiprocessing`, `concurrent.futures`, `json` ve `csv` gibi temel kütüphaneler Python'a dahili olarak gelir).*

## 3. Çalışma Modları
Motorlar, farklı akademik araştırma ihtiyaçlarına cevap vermek üzere iki ayrı modda çalışır:

*   **`DEFAULT` Modu (Doğrudan Benchmark):** 
    Algoritmaları doğrudan adaptif veya varsayılan (default) parametrelerle çalıştırır. Nihai performans değerlendirmeleri, ölçeklenebilirlik (scalability) testleri ve akademik makale tablolarının oluşturulması için kullanılır.
*   **`TUNING` Modu (Design of Experiments - DoE):** 
    Benchmark öncesinde seçilen algoritmalar için en optimal hiperparametreleri bulmak adına sistematik bir parametre uzayı taraması (Grid/Fractional) yapar. Parametre seçimindeki insan önyargısını (bias) ortadan kaldırarak sonuçların bilimsel geçerliliğini artırır.

## 4. CLI Argümanları
Her iki motor da interaktif bir menü ile veya Doğrudan Komut Satırı Arayüzü (CLI) argümanları verilerek çalıştırılabilir. CLI kullanımı, otomatik testler (CI/CD) için oldukça faydalıdır.

| Argüman | Açıklama | Örnek |
| :--- | :--- | :--- |
| `--mode` | Çalışma modunu belirler (`default` veya `tuning`). | `--mode default` |
| `--algos` | Test edilecek algoritmaların virgülle ayrılmış listesi. | `--algos GA,PSO` |
| `--runs` | Her algoritma/problem çifti için bağımsız tekrar sayısı. | `--runs 5` |
| `--size-limit` | Teste dahil edilecek TSP problemlerinin maksimum boyutu. | `--size-limit 200` |

**Örnek Komut:**
```bash
python academic_benchmark/master_numba_engine.py --mode default --algos GA,PSO --runs 3 --size-limit 150
```

## 5. Sonuç Yönetimi
Veri bütünlüğünü ve akademik tekrarlanabilirliği garanti altına almak için sistem, çıktıları `results/` klasörü altında oldukça yapısal bir hiyerarşide depolar:

*   **`benchmark_progress.csv` & `tuning_progress.csv`**: Her bir tekil testin artımlı (incremental) olarak anında kaydedildiği ham veri dosyalarıdır. İşlem uzun sürdüğünde elektrik kesintisi gibi durumlarda veri kaybını önler.
*   **`benchmark_summary.csv`**: Doğrudan istatistiksel analizlerde ve makalelerde kullanılan nihai ortalama sonuçların (süre, gap, uzunluk) bulunduğu özet tablo.
*   **`best_params.json`**: `TUNING` modu sırasında keşfedilen optimum algoritma parametrelerini kalıcı olarak saklar.
*   **`metadata.json`**: Küresel durum izleyicisidir. Hangi testlerin bittiğini önbellekler, yarım kalan benchmarkların kaldığı yerden devam etmesini sağlar ve gereksiz (tekrarlı) hesaplamaları engeller.

## 6. Geliştirici Notları
*   **Windows Multiprocessing Güvenliği:** Python'un varsayılan `multiprocessing.Pool` sınıfı Windows üzerinde "zombi process" veya "RAM sızıntısı" yaratmaya çok müsaittir. Bu mimari, bellekleri tamamen izole eden `concurrent.futures.ProcessPoolExecutor` yapısını kullanarak motorun çökmesini veya donmasını engeller.
*   **Numba JIT Isınma (Warm-up) Süresi:** `master_numba_engine.py` içerisinde algoritmalar `@njit(nogil=True)` ile sarmalanmıştır. Algoritma ilk çağrıldığında, Numba Python kodunu makine koduna (C hızına) derler. Bu ilk "ısınma" işlemi birkaç saniye sürer. Algoritmaların haksız rekabete uğramaması için bu derleme süresi benchmark süre ölçümlerinden tamamen hariç tutulmuştur.
