# TSPLIB Benchmark Sistemi - Detaylı Dokümantasyon

## 📋 İçindekiler

1. [Sistem Genel Bakış](#sistem-genel-bakış)
2. [Dosya Yapısı ve Sorumluluklar](#dosya-yapısı-ve-sorumluluklar)
3. [Özellikler](#özellikler)
4. [Yapılan Düzeltmeler](#yapılan-düzeltmeler)
5. [Çalışma Akışı](#çalışma-akışı)
6. [Kullanım Kılavuzu](#kullanım-kılavuzu)
7. [Güncelleme Yaparken Dikkat Edilmesi Gerekenler](#güncelleme-yaparken-dikkat-edilmesi-gerekenler)
8. [Sorun Giderme](#sorun-giderme)
9. [Genişletme Rehberi](#genişletme-rehberi)

---

## 🏗️ Sistem Genel Bakış

Bu benchmark sistemi, TSP (Traveling Salesman Problem) algoritmalarını TSPLIB problemleri üzerinde test etmek için tasarlanmıştır. Sistem şu özellikleri sağlar:

- **Gerçek TSPLIB Koordinatları**: GitHub'dan otomatik indirilen gerçek TSPLIB verileri
- **Çoklu Local Search Stratejileri**: 2-opt, 3-opt, Or-opt, Swap, Hybrid
- **Akıllı Önbellek**: İndirilen dosyalar ve test sonuçları önbelleğe alınır
- **Dosya Değişiklik Takibi**: Hash tabanlı değişiklik algılama
- **Kategorize Edilmiş Problemler**: Küçük (≤100), Orta (≤500), Büyük (≤2000) düğüm
- **Güvenli Çıkış**: Ctrl+C ile sonuçlar kaybolmadan çıkış
- **Anlık Kayıt**: Her algoritma sonucu hemen kaydedilir
- **Tahmini Süre**: Test öncesi süre tahmini

### Mimari Diyagramı

```
┌─────────────────────────────────────────────────────────────────────┐
│                    academic_benchmark/                               │
│                   run_smart_benchmark.py                             │
│                    (Ana Kontrol Merkezi)                            │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌───────────────────┐ ┌──────────────────┐ ┌───────────────────────────┐
│  dataset_loader   │ │ utils_benchmark  │ │ optimizer_api/utils/      │
│   (Veri Yükleme)  │ │  (Hash/Meta)     │ │ local_search.py (ALGORİTMA)│
└─────────┬─────────┘ └──────────────────┘ └───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│           optimizer_api/tests/                                       │
│           run_interactive_benchmark_v2.py                           │
│        (TSPLIB İndirme, Koordinat Parse, Test Çalıştırma)           │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  TSPLIB GitHub Repository                           │
│           https://raw.githubusercontent.com/mastqe/tsplib/          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Dosya Yapısı ve Sorumluluklar

### Proje Dizin Yapısı

```
FirebaseUniRide/UniRide/
├── optimizer_api/
│   ├── utils/
│   │   └── local_search.py          # Local Search algoritmaları (MERKEZİ)
│   ├── tests/
│   │   ├── run_interactive_benchmark_v2.py  # V2 benchmark (öncelikli)
│   │   ├── run_interactive_benchmark.py     # V1 benchmark (fallback)
│   │   ├── tsplib_data/             # TSPLIB cache
│   │   └── benchmark_results/       # JSON/CSV sonuçlar
│   └── strategies/
│       └── cvrptw_wrapper.py
└── academic_benchmark/
    ├── run_smart_benchmark.py       # Ana çalıştırma dosyası
    ├── dataset_loader.py            # Veri yükleyici
    ├── utils_benchmark.py           # Yardımcı fonksiyonlar
    ├── BENCHMARK_DOKUMANTASYON.md   # Bu dokümantasyon
    ├── benchmark_db/
    │   ├── latest_metadata.json     # Test sonuçları ve hash'ler
    │   └── history/                 # Geçmiş CSV logları
    └── tsplib_data/                 # TSPLIB cache (alternatif)
```

### Ana Dosyalar ve Sorumlulukları

| Dosya | Konum | Sorumluluk |
|-------|-------|------------|
| `local_search.py` | `optimizer_api/utils/` | Local Search algoritma implementasyonları (MERKEZİ) |
| `run_smart_benchmark.py` | `academic_benchmark/` | Ana kontrol merkezi, menü sistemi, test koordinasyonu |
| `run_interactive_benchmark_v2.py` | `optimizer_api/tests/` | TSPLIB dosyası indirme, parse etme, test çalıştırma |
| `run_interactive_benchmark.py` | `optimizer_api/tests/` | V1 fallback (hardcoded koordinatlar) |
| `dataset_loader.py` | `academic_benchmark/` | Veri seti yükleme, .tsp/.opt.tour dosyası okuma |
| `utils_benchmark.py` | `academic_benchmark/` | Hash hesaplama, metadata yönetimi |

---

## ✨ Özellikler

### Temel Özellikler

| Özellik | Açıklama |
|---------|----------|
| **Ctrl+C Güvenli Çıkış** | Signal handler ile kesintide sonuçlar otomatik kaydedilir |
| **Incremental Save** | Her algoritma sonucu anında `latest_metadata.json`'a kaydedilir |
| **Tahmini Süre** | Test öncesi problem boyutu ve algoritma karmaşıklığına göre süre tahmini |
| **Test Öncesi Özet** | Onay ekranı ile problem/algoritma sayısı ve tahmini süre gösterimi |
| **Progress Gösterimi** | Kalan test sayısı ve tahmini kalan süre |
| **Çoklu Seçim** | İstenen problemler ve algoritmalar seçilebilir |
| **Algoritma Kataloğu** | Her algoritma için detaylı bilgi |

### Menü Seçenekleri

| Seçenek | Açıklama | Kullanım Senaryosu |
|---------|----------|-------------------|
| **A** | Değişen kodları test et | local_search.py güncellendiğinde |
| **B** | Eksik testleri tamamla | Yeni problem/strateji eklendiğinde |
| **C** | Hızlı mod | Hızlı doğrulama için |
| **D** | Kapsamlı test | Tam raporlama için |
| **E** | Özel seçim | Belirli testler için |
| **S** | Detay modu | Problem bazlı sonuç görüntüleme |
| **H** | Algoritma bilgileri | Algoritma detayları |
| **Q** | Çıkış | - |

---

## 🔧 Yapılan Düzeltmeler

### 1. IndexError Sorunu (Kritik)

**Sorun:** LIN105 ve diğer problemlerde `list index out of range` hatası

**Kök Neden:** TSPLIB 1-based indeksleme kullanırken, Python listeleri 0-based'dir. Bounds checking yoktu.

**Çözüm:** `compute_tour_length()` ve `calculate_tour_length()` fonksiyonlarına güvenli indeksleme eklendi:

```python
def safe_get_coord(idx: int):
    """Safe coordinate access with bounds checking"""
    real_idx = idx - 1 if idx > 0 else idx
    if 0 <= real_idx < n_coords:
        return coordinates[real_idx]
    return None
```

**Etkilenen Dosyalar:**
- `dataset_loader.py` (satır 92-152)
- `run_interactive_benchmark.py` (satır 453-495)
- `run_interactive_benchmark_v2.py` (satır 316-358)

### 2. Negatif GAP Değerleri Sorunu (Kritik)

**Sorun:** EIL76 için -16.17%, ST70 için -12.74% gibi imkansız negatif GAP değerleri

**Kök Neden:** 
- V1'de MEDIUM ve LARGE problemlerin koordinatları algoritmik olarak üretiliyordu
- Hardcoded optimal değerler bu üretilmiş koordinatlarla uyuşmuyordu
- Örnek: `PR226` için optimal=80369 ama koordinatlar `(i*100 + (i % 17) * 23, ...)` formülüyle üretiliyordu

**Çözüm:** V2 öncelikli kullanım - gerçek TSPLIB dosyaları GitHub'dan indiriliyor

```python
# run_smart_benchmark.py - V2 öncelikli import
try:
    from optimizer_api.tests.run_interactive_benchmark_v2 import (...)
    USE_V2 = True
except ImportError:
    from optimizer_api.tests.run_interactive_benchmark import (...)
    USE_V2 = False
```

**Etkilenen Dosyalar:**
- `run_smart_benchmark.py` (satır 15-35)
- `dataset_loader.py` (satır 10-35, 171-211)

### 3. Koordinat Tutarlılığı

**Sorun:** V1'de MEDIUM ve LARGE problemler gerçek TSPLIB koordinatlarını içermiyordu

**Çözüm:** `run_interactive_benchmark_v2.py` ile:
- TSPLIB dosyaları `https://raw.githubusercontent.com/mastqe/tsplib/master/` adresinden indiriliyor
- Dosyalar `tsplib_data/` klasörüne cache'leniyor
- Gerçek koordinatlar parse ediliyor

---

## 🔄 Çalışma Akışı

### Benchmark Çalıştırma Süreci

```
1. run_smart_benchmark.py başlatılır
           │
           ▼
2. Algoritma dosyalarının hash'leri kontrol edilir
   (local_search.py, split_decoder.py, vb.)
           │
           ▼
3. Problemler yüklenir (V2 öncelikli)
   - GitHub'dan TSPLIB .tsp dosyaları indirilir
   - Koordinatlar parse edilir
   - Optimal değerler atanır
           │
           ▼
4. Kullanıcı menüden seçim yapar
   [A] Değişen kodları test et
   [B] Eksik testleri tamamla
   [C] Hızlı mod (küçük problemler)
   [D] Kapsamlı test
   [E] Özel seçim
   [S] Detay modu
   [H] Algoritma bilgileri
   [Q] Çıkış
           │
           ▼
5. Test öncesi özet gösterilir
   - Problem/algoritma sayısı
   - Tahmini süre
   - Onay beklenir
           │
           ▼
6. Her problem için her strateji çalıştırılır
   - 3 farklı seed ile test
   - HER ALGORİTMA SONUCU ANINDA KAYDEDİLİR
   - Progress gösterilir
           │
           ▼
7. Sonuçlar kaydedilir
   - latest_metadata.json (önbellek)
   - history/smart_run_TIMESTAMP.csv (geçmiş)
```

### Ctrl+C ile Güvenli Çıkış Akışı

```
Kullanıcı Ctrl+C'e basar
           │
           ▼
signal_handler() tetiklenir
           │
           ▼
_shutdown_requested = True
           │
           ▼
Mevcut sonuçlar kaydedilir:
   - latest_metadata.json güncellenir
   - interrupted_TIMESTAMP.csv oluşturulur
           │
           ▼
"Güvenli çıkış yapıldı" mesajı
```

### TSPLIB Dosyası İndirme Akışı

```
load_tsplib_problem("berlin52", 7542, "small")
           │
           ▼
download_tsplib_file("berlin52")
           │
           ├── tsplib_data/berlin52.tsp var mı?
           │       │
           │       ├── EVET → Dosya yolunu döndür
           │       │
           │       └── HAYIR → İndir
           │               │
           │               ▼
           │       https://raw.githubusercontent.com/mastqe/tsplib/master/berlin52.tsp
           │               │
           │               ▼
           │       tsplib_data/berlin52.tsp olarak kaydet
           │
           ▼
parse_tsplib_file(filepath)
           │
           ├── NAME: berlin52
           ├── DIMENSION: 52
           ├── NODE_COORD_SECTION
           │       1 565.0 575.0
           │       2 25.0 185.0
           │       ...
           │
           ▼
TSPLIBProblem(
    name="berlin52",
    dimension=52,
    optimal=7542,
    coordinates=[(565,575), (25,185), ...],
    category="small",
    source="tsplib"
)
```

---

## 📖 Kullanım Kılavuzu

### Hızlı Başlangıç

```bash
# Proje dizinine git
cd /home/z/my-project/academic_benchmark

# Benchmark'ı çalıştır
python run_smart_benchmark.py
```

### Algoritma Durum Sembolleri

| Sembol | Durum | Anlam |
|--------|-------|-------|
| ✅ | GUNCEL | Dosya değişmedi, önbellek geçerli |
| ⚠️ | DEGISMIS | Dosya değişti, yeniden test önerilir |
| ✨ | YENI | Dosya yeni eklendi, test edilmemiş |
| ❌ | DOSYA_YOK | Dosya bulunamadı |

### Test Sonuç Durumu

| Sembol | GAP | Anlam |
|--------|-----|-------|
| ★ | ≤ 1% | Mükemmel (optimala çok yakın) |
| ✓ | ≤ 5% | İyi |
| ○ | ≤ 10% | Orta |
| ✗ | > 10% | Zayıf |

### Özel Seçim Modu [E]

Problem seçimi için:
- Tek seçim: `1, 3, 5`
- Aralık seçimi: `5-8` (5'ten 8'e kadar)
- Tümü: `all` veya `tüm`

Algoritma seçimi için:
- Sayı ile: `1, 2, 4`
- Tümü: `all` veya `tüm`

---

## ⚠️ Güncelleme Yaparken Dikkat Edilmesi Gerekenler

### 1. Yeni Problem Eklerken

**Dosya:** `run_interactive_benchmark_v2.py` - `TSPLIB_PROBLEMS` dict

```python
TSPLIB_PROBLEMS = {
    "small": [
        ("yeni_problem", 12345),  # (problem_adı, optimal_değer)
        ...
    ],
    ...
}
```

**Dikkat Edilmesi Gerekenler:**
- Problem adı TSPLIB'de var olmalı: https://github.com/mastqe/tsplib
- Optimal değer doğru olmalı (TSPLIB dokümantasyonundan doğrulayın)
- Kategori boyuta göre doğru seçilmeli (small ≤100, medium ≤500, large ≤2000)

### 2. Yeni Local Search Stratejisi Eklerken

**Dosyalar:**
1. `optimizer_api/utils/local_search.py` - Algoritma implementasyonu (MERKEZİ KONUM)
2. `optimizer_api/tests/run_interactive_benchmark_v2.py` - STRATEGIES listesi
3. `academic_benchmark/run_smart_benchmark.py` - ALGORITHM_INFO dict

**Adımlar:**

```python
# 1. optimizer_api/utils/local_search.py - Yeni sınıf ekle
class YeniLocalSearch(BaseLocalSearch):
    def improve(self, route, duration_func):
        # Implementasyon
        pass

# 2. optimizer_api/utils/local_search.py - LocalSearchType enum'a ekle
class LocalSearchType(str, Enum):
    YENI_ALGO = "yeni_algo"
    ...

# 3. optimizer_api/utils/local_search.py - get_local_search()'e ekle
ls_map = {
    LocalSearchType.YENI_ALGO: YeniLocalSearch,
    ...
}

# 4. optimizer_api/tests/run_interactive_benchmark_v2.py - STRATEGIES'e ekle
STRATEGIES = [
    ("Yeni-Algo", LocalSearchType.YENI_ALGO, 500),  # (isim, tip, max_iter)
    ...
]

# 5. academic_benchmark/run_smart_benchmark.py - ALGORITHM_INFO'ya ekle
ALGORITHM_INFO = {
    "Yeni-Algo": {
        "name": "Yeni-Algo",
        "description": "Açıklama",
        "complexity": "O(n²)",
        "best_for": "Kullanım senaryosu",
        "how_it_works": "Çalışma prensibi",
        "iterations": 500,
    },
    ...
}
```

**Önemli:** `local_search.py` dosyası `optimizer_api/utils/` klasöründe olmalıdır. Bu dosya merkezi konumdadır ve hem benchmark sistemi hem de diğer modüller tarafından kullanılır.

### 3. Dosya Yolu Değişikliklerinde

**ALGORITHMS_TO_CHECK** dict'i güncelleyin:

```python
# run_smart_benchmark.py
ALGORITHMS_TO_CHECK = {
    "LocalSearchEngine": "optimizer_api/utils/local_search.py",
    "SplitDecoder": "optimizer_api/utils/split_decoder.py",
    # Yeni dosya eklemek için:
    "YeniModul": "optimizer_api/utils/yeni_modul.py",
}
```

### 4. TSPLIB Kaynağı Değişikliği

**Dosya:** `run_interactive_benchmark_v2.py`

```python
TSPLIB_BASE_URL = "https://raw.githubusercontent.com/mastqe/tsplib/master/"
```

**Alternatif Kaynaklar:**
- http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/
- http://elib.zib.de/pub/mp-testdata/tsp/tsplib/tsp/

### 5. Test Sayısını Değiştirme

```python
# run_interactive_benchmark_v2.py
N_RUNS = 3  # Her problem için çalıştırma sayısı
```

### 6. Önbelleği Temizleme

```bash
# TSPLIB dosyalarını temizle
rm -rf optimizer_api/tests/tsplib_data/*

# Test sonuçlarını temizle
rm academic_benchmark/benchmark_db/latest_metadata.json

# Geçmişi temizle
rm -rf academic_benchmark/benchmark_db/history/*
```

---

## 🔍 Sorun Giderme

### IndexError: list index out of range

**Belirti:** LIN105 veya diğer problemlerde crash

**Çözüm:** 
- `calculate_tour_length()` fonksiyonunun güncel olduğundan emin olun
- Bounds checking ekli olmalı

### Negatif GAP Değerleri

**Belirti:** -10%, -20% gibi imkansız sonuçlar

**Çözüm:**
1. V2'nin kullanıldığından emin olun (`USE_V2 = True`)
2. TSPLIB dosyalarının doğru indirildiğini kontrol edin
3. `tsplib_data/` klasörünü temizleyip yeniden indirin

### ImportError

**Belirti:** Module not found hataları

**Çözüm:**
```bash
# Proje kök dizininden çalıştırın
cd /home/z/my-project
python academic_benchmark/run_smart_benchmark.py
```

### Ağ Bağlantı Hatası

**Belirti:** TSPLIB dosyaları indirilemiyor

**Çözüm:**
1. İnternet bağlantısını kontrol edin
2. GitHub erişilebilirliği kontrol edin
3. Proxy gerekiyorsa ayarlayın

### Sonuçlar Kayboldu

**Belirti:** Ctrl+C sonrası veya crash sonrası sonuçlar yok

**Çözüm:**
- Yeni versiyonda her algoritma sonucu anında kaydedilir
- `benchmark_db/history/` klasöründe `interrupted_*.csv` dosyasını kontrol edin

---

## 🚀 Genişletme Rehberi

### Yeni Kategori Ekleme

```python
# run_interactive_benchmark_v2.py
TSPLIB_PROBLEMS = {
    "small": [...],
    "medium": [...],
    "large": [...],
    "xlarge": [  # Yeni kategori
        ("d2103", 80450),
        ("u2319", 234256),
    ]
}

# Kategori belirleme fonksiyonunu güncelle
def determine_category(dimension):
    if dimension <= 100:
        return "small"
    elif dimension <= 500:
        return "medium"
    elif dimension <= 2000:
        return "large"
    else:
        return "xlarge"
```

### Özel Mesafe Fonksiyonu Ekleme

```python
def custom_distance(p1, p2):
    """Özel mesafe hesaplama (örn: Haversine)"""
    # Implementasyon
    return distance

def calculate_tour_length(tour, coordinates, distance_func=tsplib_distance):
    # distance_func parametresi eklendi
    ...
```

### Performans Metrikleri Ekleme

```python
# run_smart_benchmark.py - Sonuç dict'ine ekle
result = {
    ...
    "memory_usage_mb": memory_usage,
    "iterations": iterations,
    "convergence_rate": convergence_rate,
}
```

---

## 📊 Bilinen TSPLIB Optimal Değerleri

| Problem | Boyut | Optimal | Kategori |
|---------|-------|---------|----------|
| berlin52 | 52 | 7542 | small |
| eil51 | 51 | 426 | small |
| eil76 | 76 | 538 | small |
| st70 | 70 | 675 | small |
| kroA100 | 100 | 21282 | small |
| kroC100 | 100 | 20749 | small |
| eil101 | 101 | 629 | small |
| lin105 | 105 | 14379 | small |
| kroA150 | 150 | 26524 | medium |
| kroA200 | 200 | 29368 | medium |
| pr226 | 226 | 80369 | medium |
| pr439 | 439 | 107217 | medium |
| d493 | 493 | 35002 | large |
| u724 | 724 | 41910 | large |
| rat783 | 783 | 8806 | large |
| pr1002 | 1002 | 259045 | large |

---

## 📝 Versiyon Geçmişi

| Versiyon | Tarih | Değişiklikler |
|----------|-------|---------------|
| 3.0 | 2026-04-05 | [E] Özel seçim, [H] Algoritma bilgileri, Ctrl+C güvenli çıkış, incremental save, tahmini süre |
| 2.0 | 2026-04-03 | IndexError düzeltmesi, V2 entegrasyonu, negatif GAP düzeltmesi |
| 1.0 | - | İlk sürüm (hardcoded koordinatlar) |

---

## 📞 İletişim ve Destek

Sorunlar için:
1. Bu dokümantasyonu kontrol edin
2. `benchmark_db/latest_metadata.json` içeriğini inceleyin
3. `tsplib_data/` klasöründeki dosyaların bütünlüğünü doğrulayın
4. `benchmark_db/history/` klasöründeki CSV dosyalarını kontrol edin

---

*Bu dokümantasyon 2026-04-05 tarihinde güncellenmiştir.*
