# UniRide - Changelog (Degisim Gunlugu)

> Bu belge, UniRide projesinin tum gelisim surecinde yapilan degisiklikleri detayli bir sekilde belgelemektedir.
> Tum oturumlar, tarih/saat ve yazar bilgisi ile listelenmistir.

---

## Session 1: Ilk Kod Incelemesi (Initial Code Review)

**Tarih:** 2026-06-01 | **Yazar:** Z.ai Code | **Tur:** Code Review

### Yapilan Degisiklikler

- **Proje dosyalari temizlendi** - Onceki tum proje dosyalari silindi, temiz bir baslangic yapildi
- **UniRide.zip cikarildi** - 1196 dosya, ~30.500 satir kod iceren arsiv proje dizinine cikarildi
- **4 paralel kod inceleme ajanı baslatildi** - Farkli modulleri incelemek uzere paralel calisan 4 AI ajanı kullanildi
- **CODE_REVIEW_REPORT.md olusturuldu** - Kapsamli kod inceleme raporu derlendi:
  - **12 KRITIK** bulgu (CRITICAL)
  - **22 YUKSEK** bulgu (HIGH)
  - **30 ORTA** bulgu (MEDIUM)
  - **16 DUSUK** bulgu (LOW)
  - Toplamda **80+ bulgu** tespit edildi

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `CODE_REVIEW_REPORT.md` | Yeni - 80+ bulgu iceren kod inceleme raporu |
| `*` (tum proje dosyalari) | UniRide.zip'ten cikarildi |

---

## Session 2: Roadmap Olusturma

**Tarih:** 2026-06-01 | **Yazar:** Z.ai Code | **Tur:** Planlama

### Yapilan Degisiklikler

- **Python optimizer API derinlemesine incelendi** - API yapisi, endpoint'ler ve veri akisi analiz edildi
- **CVRPTW time windows sorunu tespit edildi** - Time window parametrelerinin backend'e bagli olmadigi (not wired) belirlendi
- **Benchmark Python endpoint'leri analizi** - Frontend tarafinda tuketilmeyen Python benchmark endpoint'leri tespit edildi
- **5-fazlik ROADMAP.md olusturuldu** - Proje gelisimi icin kapsamli yol haritasi hazirlandi:
  - **Faz 1:** Kritik Bug Fixleri
  - **Faz 2:** Benchmark Suite UI
  - **Faz 3:** CVRPTW Time Windows Entegrasyonu
  - **Faz 4:** Gelistirilmis Optimizasyon
  - **Faz 5:** Production Hazirlik

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `ROADMAP.md` | Yeni - 5-fazlik gelisim yol haritasi |

---

## Session 3: Kritik Bug Fixleri + Benchmark Suite UI

**Tarih:** 2026-06-02 | **Yazar:** Z.ai Code | **Tur:** Bug Fix + UI Development

### Kritik Bug Fixleri

- **`benchmark_state.py`:** Eksik `from enum import Enum` importu eklendi, `results` alani tanimlandi
- **`benchmark_runner.py`:** Sonuclarin `state_manager` icinde saklanmasi saglandi
- **`main.py`:** Sözdizimi hatalari (syntax errors) duzeltildi, `get_benchmark_results` bos liste donduruyor sorunu cozuldu
- **`utils/tsplib_parser.py`:** Eksik kapanis parantezi (closing bracket) eklendi
- **`strategies/base_strategy.py`:** Varolmayan modulden import hatasi duzeltildi
- **`utils/patterns.py`:** Eksik `SingletonMeta` sinifi olusturuldu
- **`benchmark-service.ts`:** `run_id` query parameter olarak gecirildi
- **`package.json`:** Gelistirme portu 9002 → 3000 olarak degistirildi

### Benchmark Suite UI

- **`src/app/page.tsx` olusturuldu** - Tam kapsamli Benchmark Suite arayuzu:
  - 1352 satir kod
  - Problem secimi, strateji secimi, benchmark calistirma
  - Sonuc goruntuleme, tablo ve grafik gosterimi
  - Gercek zamanli ilerleme takibi

### Altyapi

- **Python optimizer API** port 8000'de baslatildi (sonradan 8099'a tasindi)

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `optimizer_api/benchmark_state.py` | Bug fix - import + results alani |
| `optimizer_api/benchmark_runner.py` | Bug fix - state_manager entegrasyonu |
| `optimizer_api/main.py` | Bug fix - sözdizimi + endpoint duzeltmeleri |
| `optimizer_api/utils/tsplib_parser.py` | Bug fix - kapanis parantezi |
| `optimizer_api/strategies/base_strategy.py` | Bug fix - import yolu duzeltme |
| `optimizer_api/utils/patterns.py` | Yeni - SingletonMeta sinifi |
| `src/services/benchmark-service.ts` | Bug fix - run_id query param |
| `package.json` | Port 9002 → 3000 |
| `src/app/page.tsx` | Yeni - Benchmark Suite UI (1352 satir) |

---

## Session 4: TSPLIB Benchmark Duzeltmeleri D1-D4

**Tarih:** 2026-06-02 | **Yazar:** Z.ai Code | **Tur:** Benchmark Fixes

### D1: BenchmarkRunner Euclidean Mesafe Hesaplama

- **BenchmarkRunner** artik TSPLIB koordinatlarindan euclidean tur mesafesi hesapliyor
- Mesafe hesaplamasi `tsplib_parser.py` icinde `tsplib_euc_2d_distance` fonksiyonu ile yapildi

### D2: Strateji Dosyalari Koordinat Gecisi

- **16 strateji dosyasi** duzeltildi - tumu koordinatlari `get_submatrix()` fonksiyonuna gecirmeye basladi
- Her strateji dosyasinda coordinates parametresi eklendi

### D3: Mesafe Hesaplama Duzeltmeleri

- **`pyvrp_strategy.py`:** `distance=0.0` sabit degeri `_dist()` helper fonksiyonu ile degistirildi
- **`vroom_strategy.py`:** `distance=0.0` sabit degeri `_dist()` helper fonksiyonu ile degistirildi
- Artik gercek euclidean mesafeler kullaniliyor

### D4: Otomatik Indirme Mekanizmasi

- TSPLIB veri dosyalari icin otomatik indirme mekanizmasi dogrulandi (auto-download)

### Port Duzeltmesi

- **Frontend XTransformPort:** 8000 → 8099 olarak tum dosyalarda guncellendi

### Dogrulama Sonuclari (Verification)

| Algoritma | Problem | Tur Mesafesi | GAP |
|-----------|---------|-------------|-----|
| greedy | eil51 | 513.61 | 20.57% |
| two_opt | eil51 | 452.71 | 6.27% |

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `optimizer_api/benchmark_runner.py` | Euclidean mesafe hesaplama |
| `optimizer_api/strategies/*.py` (16 dosya) | Coordinates parametresi eklendi |
| `optimizer_api/strategies/pyvrp_strategy.py` | `_dist()` helper |
| `optimizer_api/strategies/vroom_strategy.py` | `_dist()` helper |
| Frontend dosyalari (port guncelleme) | XTransformPort 8000 → 8099 |

---

## Session 5: Faz 1-2 Dogrulama + Port Fix

**Tarih:** 2026-06-03 | **Yazar:** Z.ai Code | **Tur:** Verification + Bug Fix

### Faz 1 Dogrulama (Items 1.1 - 1.8)

- Tum Faz 1 maddelerinin tamamlandigi dogrulandi:
  - [x] 1.1 - Critical bug fixleri
  - [x] 1.2 - Import hatalari
  - [x] 1.3 - Syntax hatalari
  - [x] 1.4 - Singleton implementasyonu
  - [x] 1.5 - Benchmark state yonetimi
  - [x] 1.6 - TSPLIB parser duzeltmeleri
  - [x] 1.7 - Port yapisilandirmasi
  - [x] 1.8 - Benchmark service duzeltmeleri

### Faz 2 Dogrulama (Items 2.1 - 2.5)

- Tum Faz 2 maddelerinin tamamlandigi dogrulandi:
  - [x] 2.1 - Benchmark Suite UI
  - [x] 2.2 - Problem secimi
  - [x] 2.3 - Strateji secimi
  - [x] 2.4 - Sonuc goruntuleme
  - [x] 2.5 - Gercek zamanli ilerleme

### Bug Fixleri

- **`utils/patterns.py`:** Singleton thread-safety sorunu duzeltildi
- **`optimizer_api/main.py`:** Port uyumsuzlugu giderildi - 8000 → 8099
- **`ROADMAP.md`:** v3 olarak guncellendi

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `optimizer_api/utils/patterns.py` | Thread-safe Singleton |
| `optimizer_api/main.py` | Port 8000 → 8099 |
| `ROADMAP.md` | v3 guncelleme |

---

## Session 6: Kapsamli Faz 1 Incelemesi + Guvenlik + TSPLIB NINT

**Tarih:** 2026-06-03 | **Yazar:** Z.ai Code | **Tur:** Security + Verification

### Guvenlik Duzeltmesi

- **NEXT_PUBLIC_DEV_RESET_SECRET exposure removed from forgot-password** - `forgot-password` sayfasindan guvenlik sifresi cikarildi, hassas veri sızıntısı onlendi

### TSPLIB EUC_2D NINT Yuvarlama

- **TSPLIB EUC_2D NINT rounding eklendi** - `tsplib_euc_2d_distance` fonksiyonuna NINT (nearest integer) yuvarlama eklendi
- Bu, TSPLIB standart mesafe hesaplama formatina uygunluk sagladi

### Import Duzeltmesi

- **`cvrptw_wrapper.py`:** `import logging` eklendi

### Faz 1 Detayli Dogrulama

- Tum Faz 1 itemleri detayli tablo ile dogrulandi

### NINT Sonrasi Sonuclar

| Algoritma | Problem | Tur Mesafesi | GAP |
|-----------|---------|-------------|-----|
| greedy | eil51 | 511 | 19.95% |
| two_opt | eil51 | 453 | 6.34% |

> NINT yuvarlamasi sonrasi greedy sonucu 513.61 → 511'e dustu (daha dogru TSPLIB uyumu)

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `src/app/(auth)/forgot-password/page.tsx` | Guvenlik sifresi cikarildi |
| `optimizer_api/utils/tsplib_parser.py` | NINT rounding eklendi |
| `optimizer_api/strategies/cvrptw_wrapper.py` | `import logging` eklendi |

---

## Session 7: CLI → Web Import Koprusu

**Tarih:** 2026-06-04 | **Yazar:** Z.ai Code | **Tur:** Feature Development

### Yeni API Endpoint'leri

- **`optimizer_api/main.py`** icinde 3 yeni endpoint eklendi:
  - `GET /api/v1/benchmark/cli/files` - CLI benchmark dosyalarini listeler
  - `POST /api/v1/benchmark/cli/import` - CLI verilerini web formatina donusturup importer
  - `GET /api/v1/benchmark/cli/preview` - Import ongoruntusu (preview) saglar

### Format Donusumu (Format Conversion)

- CLI → Web veri donusumu mekanizmasi olusturuldu:
  - `strategy` → `algorithm` alani eslestirmesi
  - `avg_gap` / `best_gap` → `gap_percent` alani eslestirmesi
  - Tum alan isimleri ve veri tipleri web formatina uygun hale getirildi

### Test Sonuclari

- **7 CLI JSON dosyasi** basariyla islendi
- **30 CLI record** → **90 web record** olarak donusturuldu

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `optimizer_api/main.py` | 3 yeni endpoint eklendi |

---

## Session 8: Sandbox IE Fix, Kmeans Arsivleme, Env Temizlik

**Tarih:** 2026-06-04 | **Yazar:** Copilot AI | **Tur:** Cleanup + Bug Fix

### Sandbox IE Endpoint Temizligi

- **`/api/v1/ie/analyze` endpoint kaldirildi** - Sandbox'taki gereksiz endpoint silindi
- Bunun yerine `result.ie_data` verisi dogrudan kullaniliyor

### Kmeans Arsivleme

- **`kmeans_tsp.py` arsivlendi** - `optimizer_api/strategies/_archived/kmeans_tsp.py` konumuna tasindi
- Arsiv klasorune README.md eklendi

### Environment Degisken Temizligi

- **Supabase env var bos string fallback kaldirildi** - Bos string fallback degerleri temizlendi, daha guvenli konfigürasyon saglandi

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `optimizer_api/main.py` | `/api/v1/ie/analyze` endpoint kaldirildi |
| `optimizer_api/strategies/_archived/kmeans_tsp.py` | Arsivlendi |
| `optimizer_api/strategies/_archived/README.md` | Yeni - arsiv aciklamasi |
| `optimizer_api/strategies/kmeans_tsp.py` | Silindi (arsivlendi) |
| Supabase konfigürasyon dosyalari | Bos string fallback temizligi |

---

## Session 9: `as any` Temizligi

**Tarih:** 2026-06-04 | **Yazar:** Copilot AI | **Tur:** TypeScript Cleanup

### Tip Guvenligi Iyilestirmeleri

- **`DbUserRow` arayuzu olusturuldu** - `src/types/db.ts` icinde yeni interface tanimlandi
- **Database tip tanimlari guncellendi:**
  - `Database.users.Row` → `DbUserRow`
  - `Database.users.Insert` → `DbUserRow`
  - `Database.users.Update` → `DbUserRow`
- **`(adminClient as any)` kaldirildi** - `src/app/api/admin/users/route.ts` dosyasindan unsafe type assertion silindi
- **TypeScript hata sayisi: 0** - Tum tip guvenligi kontrolleri basariyla gecti

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `src/types/db.ts` | Yeni - `DbUserRow` interface |
| `src/app/api/admin/users/route.ts` | `(adminClient as any)` kaldirildi |

---

## Session 10: Statik Analiz + Kod Duzeltmeleri

**Tarih:** 2026-06-05 | **Yazar:** Copilot AI | **Tur:** Static Analysis + Security

### Statik Analiz Sonuclari

- **11 sorunu** tespit edildi ve duzeltildi

### Guvenlik Duzeltmeleri

- **`requireAdmin` eklendi** - `POST /api/calculate-vehicles` endpoint'ine admin yetkilendirme kontrolu eklendi
- **`ALLOWED_ORIGINS` env var eklendi** - CORS icin izinli origin'ler ortam degiskeni ile yonetilmeye baslandi

### Tip ve Alan Duzeltmeleri

- **`total_time_window_violations` alani eklendi** - `OptimizationResponse` tipine yeni alan tanimlandi
- **`config.ts`:** `RATE_LIMIT_REQUESTS_PER_MINUTE` temizligi yapildi

### Sandbox Route Duzeltmeleri

- **`src/app/api/sandbox/route.ts`:**
  - `strategy` → `algorithm` alani isim degisikligi
  - `max_tour_time` → `max_travel_time` alani isim degisikligi

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `src/app/api/calculate-vehicles/route.ts` | `requireAdmin` middleware eklendi |
| `src/types/index.ts` | `total_time_window_violations` alani |
| `src/app/api/sandbox/route.ts` | Alan isimleri guncellendi |
| `src/lib/config.ts` | Rate limit temizligi |
| CORS konfigürasyonu | `ALLOWED_ORIGINS` env var |

---

## Session 11: Sandbox IE Endpoint Tam Duzeltme

**Tarih:** 2026-06-05 | **Yazar:** Copilot AI | **Tur:** Bug Fix + Data Transformation

### Depot Nesnesi Eklenti

- **Depot object sandbox'a eklendi** - IE analizinde kullanilmak uzere depot (depo) bilgisi eklendi

### Veri Donusumu (Data Transformation)

- **Vehicle/student alan donusumu:**
  - camelCase → snake_case donusumu uygulandı
  - Frontend ve backend arasinda tutarli veri yapisi saglandi

### transformIEData Helper

- **`transformIEData` helper fonksiyonu eklendi** - IE verilerinin frontend'e dogru formatla gonderilmesini saglayan donusum fonksiyonu

### result.ie_data Eşleştirmesi

- **`result.ie_data` duzgun sekilde frontend'e eslestirildi** - Sandbox sonucundaki IE verileri artik dogru formatta map ediliyor

### Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `src/app/api/sandbox/route.ts` | Depot nesnesi + alan donusumleri |
| `src/services/sandbox-api.ts` | `transformIEData` helper |
| Frontend IE bilesenleri | `result.ie_data` eslestirmesi |

---

## Ozet (Summary)

| Metric | Deger |
|--------|------|
| **Toplam Oturum** | 11 |
| **Yeni Endpoint'ler** | 6+ |
| **Duzeltilen Bug** | 30+ |
| **Yeni Dosyalar** | 10+ |
| **Degisen Dosya** | 50+ |
| **TypeScript Hata** | 0 |
| **Guvenlik Duzeltmesi** | 3 |
| **Kritik Bulgu (Session 1)** | 12 |
| **Yuksek Bulgu (Session 1)** | 22 |

---

> *Son guncelleme: Session 11 - 2026-06-05*
