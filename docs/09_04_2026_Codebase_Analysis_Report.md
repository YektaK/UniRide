# UniRide — Kapsamlı Kod Tabanı Analiz Raporu

> **Tarih:** 09.04.2026 (09.04.2026 - Ekleyen: Copilot AI)
> **Kapsam:** Tüm aktif kaynak kodu (`/src`, `/optimizer_api`), dokümantasyon (`/docs`), şema (`/supabase`)
> **Yöntem:** Statik kod analizi — her iddia dosya + satır numarasıyla desteklenmektedir.

---

## 1. Depo Yapısı (Gerçek)

```
UniRide/
├── src/                          # Next.js 16 web uygulaması (AKTİF)
│   ├── app/
│   │   ├── (app)/                # Kimlik doğrulamalı sayfalar (admin/driver/student)
│   │   ├── (auth)/               # Login/Register sayfaları
│   │   └── api/                  # 14 Next.js API route dosyası
│   ├── components/               # 80+ UI bileşeni (shadcn/ui + özel)
│   ├── lib/                      # Auth, Supabase client, config, utils
│   ├── services/                 # Optimizer proxy, Excel I/O, route services
│   └── types/                    # TypeScript tip tanımlamaları
├── optimizer_api/                # Python FastAPI mikroservisi (AKTİF)
│   ├── main.py                   # FastAPI uygulaması — 7 endpoint
│   ├── models/schemas.py         # Pydantic request/response modelleri
│   ├── strategies/               # 16 strateji dosyası + registry (29 anahtar)
│   └── utils/                    # Clustering, local search, split decoder, profiler
├── supabase/                     # SQL şema + 5 migration + RLS politikaları
├── academic_benchmark/           # Bağımsız TSPLib benchmark sistemi (Numba)
├── docs/                         # Mimari, changelog, roadmap, algoritma notları
├── .proposed_changes/            # Geçmiş AI oturumu anlık görüntüleri (KANONİK DEĞİL)
├── DOURide/, download/, uniride-fixed/  # Arşiv paketleri (aktif değil)
└── package.json                  # Next.js ^16.1.6 + React ^18.3.1 + Tailwind ^3.4.1
```

Aktif kod yalnızca `/src` ve `/optimizer_api` klasörlerindedir.

---

## 2. Teknoloji Sürümleri (Doğrulandı — package.json)

| Teknoloji | Belgelenen | Gerçek |
|---|---|---|
| Next.js | 16.x | ^16.1.6 ✅ |
| React | 19.x (docs/02_Architecture.md:68) | ^18.3.1 ❌ YANLIŞ DOC |
| Tailwind CSS | 4.x (docs/02_Architecture.md:67) | ^3.4.1 ❌ YANLIŞ DOC |
| TypeScript | 5.x | ^5.6.3 ✅ |
| shadcn/ui | latest | mevcut ✅ |
| Python | 3.11+ | 3.9+ hedefleniyor |

---

## 3. Optimizer API Endpoint'leri (Tam — optimizer_api/main.py)

| Method | Path | Satır | Açıklama |
|---|---|---|---|
| GET | `/health` | 101 | Sağlık kontrolü |
| GET | `/api/v1/strategies` | 113 | Kullanılabilir stratejiler |
| POST | `/api/v1/optimize` | 267 | Tek algoritmayla optimizasyon |
| POST | `/api/v1/extract-time-windows` | 413 | Haftalık programdan TW çıkar |
| POST | `/api/v1/schedule-to-students` | 463 | Program → öğrenci node listesi |
| POST | `/api/v1/compare` | 554 | Tüm algoritmaları karşılaştır |
| POST | `/api/v1/vehicle-calculator` | 652 | Araç hesaplama |

**Eksik endpoint:** `src/app/api/sandbox/route.ts:95` tarafından çağrılan `/api/v1/ie/analyze`
**main.py'de TANIMLI DEĞİL** — bu nedenle sandbox IE analizi her zaman null döner (hata sessizce yutulur).

---

## 4. Strateji Registry'si (optimizer_api/strategies/__init__.py:108-181)

29 anahtar, 16 strateji dosyası:

| Pipeline | Algoritmalar |
|---|---|
| **Pipeline A** (Cluster-First) | `genetic_algorithm`/`ga`, `pso`, `gwo`/`grey_wolf`, `hho`/`harris_hawks` |
| **Pipeline B** (Split Decoder) | `ga_split`/`ga-split`, `pso_split`, `gwo_split`, `hho_split` |
| **Holistic Solvers** | `ortools_cvrp`/`ortools`, `pyvrp`*/`hgs`, `vroom`* |
| **Heuristics** | `two_opt`/`2opt`, `greedy`/`nearest_neighbor`, `permutation_tsp` |

*PyVRP ve VROOM opsiyoneldir; kurulu değilse OR-Tools'a sessizce fallback olur.

### 4.1 Clustering Stratejileri (optimizer_api/utils/clustering_strategies/)

7 ayrı clustering algoritması:
`kmeans`, `fuzzy_cmeans`, `fuzzy_cmeans_enhanced`, `hierarchical_fcm`, `k_medoids`, `sweep` (varsayılan), `clarke_wright`

### 4.2 Local Search (optimizer_api/utils/local_search.py:31-41)

8 tip: `NONE`, `TWO_OPT`, `THREE_OPT`, `OR_OPT`, `SWAP`, `CROSS_EXCHANGE`, `TIME_WINDOW_AWARE`, `HYBRID`

Numba JIT hızlandırmalı varyant: `optimizer_api/utils/local_search_numba.py` (1142 satır) — belgelenmemiş.

---

## 5. Dokümantasyon Doğruluk Değerlendirmesi

| ID | Dosya | Satır | Mevcut İddia | Gerçek Durum |
|---|---|---|---|---|
| D-1 | `docs/02_Architecture.md` | 67 | Tailwind `4.x` | `package.json:69` → `^3.4.1` |
| D-2 | `docs/02_Architecture.md` | 68 | React `19.x` | `package.json` → `^18.3.1` |
| D-3 | `docs/02_Architecture.md` | 36-39 | Yalnızca GA/PSO/Greedy/OR-Tools | 15+ algoritma mevcut |
| D-4 | `docs/02_Architecture.md` | 303 | "Rate Limiting: 60 req/min per IP" | Yalnızca `/api/auth/hint`'te uygulanmış |
| D-5 | `docs/02_Architecture.md` | 124 | `kmeans_tsp.py` strateji listesinde | Registry'e kayıtlı değil, kullanılmıyor |
| D-6 | `docs/03_Roadmap.md` | 59-64 | GWO/HHO/TW desteği "⏳ Bekliyor" | Tamamlanmış (`gwo_strategy.py`, `hho_strategy.py` mevcut) |
| D-7 | `README.md` | 11 | GWO/HHO/split varyantları eksik | 15+ algoritma mevcut |
| D-8 | `README.md` | 112-117 | 5 endpoint listeleniyor | 7 endpoint mevcut |

---

## 6. Kod Sorunları — Öncelik Sıralı

### 🔴 Yüksek Öncelik (Güvenlik / Kritik Bug)

#### CR-1: `POST /api/calculate-vehicles` — Kimlik Doğrulama Eksik
- **Dosya:** `src/app/api/calculate-vehicles/route.ts:145`
- **Sorun:** İşleyici hiçbir auth kontrolü olmadan öğrenci dizisi alır ve Python optimizer'a iletir. Kimliği doğrulanmamış herhangi bir çağrıcı pahalı hesaplama tetikleyebilir.
- **Kanıt:** `grep -n "requireAdmin"` sonucu bu dosyada HİÇBİR SONUÇ vermedi.
- **Çözüm:** İşleyicinin başına `await requireAdmin(request)` ekle (bkz. `optimize-route/route.ts:79`).
- **Paralel çalışılabilir:** Evet — tek dosya değişikliği.

#### CR-2: Sandbox IE Analizi Çalışmıyor — Eksik Endpoint
- **Dosya:** `src/app/api/sandbox/route.ts:95`
- **Sorun:** `OPTIMIZER_API_URL + "/api/v1/ie/analyze"` çağrısı yapılıyor; bu endpoint `main.py`'de **tanımlı değil**. Hata `route.ts:109-111`'de sessizce yutulduğundan `ieData` her zaman `null` döner.
- **Çözüm:** Ya bu endpoint'i `main.py`'ye ekle ya da `/api/v1/optimize` yanıtındaki `ie_data` alanını kullan.
- **Paralel çalışılabilir:** Evet — yalnızca Python tarafı.

#### CR-3: Optimizer API'de Production CORS Wildcard
- **Dosya:** `optimizer_api/main.py:91` — `allow_origins=["*"]`
- **Sorun:** Kod yorumu "Configure for production" diyor ama ortam bazlı guard yok.
- **Çözüm:** `ALLOWED_ORIGINS` env var'ından oku; varsayılan `["http://localhost:9002"]`.
- **Paralel çalışılabilir:** Evet — tek satır değişikliği.

---

### 🟡 Orta Öncelik (Fonksiyonel Bug / Tip Güvensizliği)

#### CR-4: `total_time_window_violations` Pydantic Modelinde Tanımlı Değil
- **Dosya:** `optimizer_api/strategies/ga_split_strategy.py:630`, `pso_split_strategy.py:573`, `gwo_split_strategy.py:567`, `hho_split_strategy.py:636`
- **Sorun:** Split stratejiler `OptimizationResponse(..., total_time_window_violations=...)` çağrısı yapıyor. `schemas.py:128-138`'de bu alan tanımlı değil. Pydantic v2 strict modda bunu ya ValidationError olarak yükseltir ya da sessizce siler.
- **Çözüm:** `OptimizationResponse`'a `total_time_window_violations: Optional[int] = None` ekle.
- **Paralel çalışılabilir:** Evet — yalnızca schemas.py.

#### CR-8: `strategy` Alan Adı Yanlışlığı (Sandbox + Calculate-Vehicles)
- **Dosya 1:** `src/app/api/sandbox/route.ts:80` — `strategy` gönderiyor
- **Dosya 2:** `src/app/api/calculate-vehicles/route.ts:79-80` — `strategy` gönderiyor
- **Sorun:** Python API `OptimizationRequest.algorithm` alanını bekler, `strategy` değil. Sonuç: her zaman varsayılan `ga_split` kullanılır; kullanıcının seçimi görmezden gelinir.
- **Kanıt:** `optimizer_api/models/schemas.py:101` — `algorithm: str = "ga_split"`
- **Çözüm:** Her iki fetch gövdesinde `strategy` → `algorithm` olarak yeniden adlandır.
- **Paralel çalışılabilir:** Evet — iki bağımsız dosya.

---

### 🟢 Düşük Öncelik (Teknik Borç / İyileştirme)

#### CR-5: Admin Users Route'da `as any` Kullanımı (Gereksiz)
- **Dosya:** `src/app/api/admin/users/route.ts:86, 144`
- **Açıklama:** `supabase-admin.ts:15`'e bakılırsa `getSupabaseAdmin()` zaten `SupabaseClient<Database>` döndürüyor. `as any` büyük olasılıkla `users` tablosu için DB türü eksikliğinden kaynaklanıyor.
- **Paralel çalışılabilir:** Evet — ancak `Database` tipinin doğrulanması gerekir.

#### CR-6: `RATE_LIMIT_REQUESTS_PER_MINUTE` Sabiti Kullanılmıyor
- **Dosya:** `src/lib/config.ts:29`
- **Sorun:** Dışa aktarılmış ama hiçbir yerde import edilmemiş. Genel rate limiting uygulandığı gibi yanlış bir izlenim yaratıyor.
- **Çözüm:** Yoruma TODO ekle ya da middleware'e bağla.

#### CR-7: `kmeans_tsp.py` Ölü Kod
- **Dosya:** `optimizer_api/strategies/kmeans_tsp.py`
- **Sorun:** `__init__.py`'ye import edilmemiş, registry'e eklenmemiş.
- **Çözüm:** Registry'e kaydet veya kaldır.

#### CR-9: `max_tour_time` vs `max_travel_time` Alan Adı Uyuşmazlığı
- **Dosya:** `src/app/api/sandbox/route.ts:78` — `max_tour_time` gönderiyor
- **Sorun:** Python API `OptimizationRequest.max_travel_time` bekler. Bu nedenle sandbox her zaman varsayılan 120 dk'yı kullanır.
- **Çözüm:** `max_tour_time` → `max_travel_time` olarak değiştir.

#### CR-10: Rate Limiter Çok-Process Ortamında Yetersiz
- **Dosya:** `src/app/api/auth/hint/route.ts:10`
- **Sorun:** `rateLimitMap` modül-seviyesinde bir `Map`. Çok process'li deployment'larda her process kendi haritasına sahiptir; limit kolayca aşılabilir.
- **Öneri:** Production için Redis tabanlı limiter kullan.

#### CR-11: Supabase Env Var'lar Boş String'e Fallback Yapıyor
- **Dosya:** `src/lib/config.ts:13-15`
- **Sorun:** `SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ""` — eksik env var sessiz auth hatalarına yol açar.
- **Öneri:** Eksik env var'lar varsa startup'ta anlamlı hata fırlat.

---

## 7. Tip Güvenliği Durumu

`as any` kullanımı — 11 yer (grep sonucu doğrulandı):

```
src/components/student/profile-form.tsx:79
src/components/admin/add-user-dialog.tsx:107
src/components/admin/user-form-dialog.tsx:88
src/services/excel/import.ts:151, 157
src/app/(app)/admin/vehicle-planning/page.tsx:348, 370
src/app/(app)/admin/route-test/page.tsx:128
src/app/api/auth/dev-reset/route.ts:45
src/app/api/admin/users/route.ts:86, 144
```

Bilinen baseline typecheck hataları (bu rapordan önce mevcuttu, bu rapor kapsamı dışı):
- `src/components/admin/resource-tracks.tsx:53`
- `src/lib/algorithm-constants.ts:254`
- `src/app/api/auth/hint/route.ts:78` — `password_hint` key type mismatch

---

## 8. Belgelenmemiş Özellikler

| Özellik | Konum | Not |
|---|---|---|
| `/api/v1/vehicle-calculator` endpoint | `optimizer_api/main.py:652` | README'de yok |
| `/api/v1/schedule-to-students` endpoint | `optimizer_api/main.py:463` | README'de yok |
| Numba-hızlandırılmış local search | `optimizer_api/utils/local_search_numba.py` | Belgelenmemiş |
| Clarke-Wright, K-Medoids, FCM clustering | `optimizer_api/utils/clustering_strategies/` | Kısmen belgelenmiş |
| GWO/HHO algoritmaları | `strategies/gwo_strategy.py`, `hho_strategy.py` | README'de eksik |
| Split decoder pipeline | `strategies/*_split_strategy.py` (4 dosya) | README'de eksik |
| `KmeansTSPStrategy` | `optimizer_api/strategies/kmeans_tsp.py` | Registry'de yok |

---

## 9. Özet Öncelik Tablosu

| ID | Önem | Dosya(lar) | Durum |
|---|---|---|---|
| CR-1 | 🔴 GÜVENLİK | `calculate-vehicles/route.ts` | DÜZELTİLMELİ |
| CR-2 | 🔴 KRİTİK BUG | `sandbox/route.ts` + `main.py` | DÜZELTİLMELİ |
| CR-3 | 🔴 GÜVENLİK | `optimizer_api/main.py:91` | DÜZELTİLMELİ |
| CR-4 | 🟡 FONKSİYONEL | `schemas.py` | DÜZELTİLMELİ |
| CR-8 | 🟡 FONKSİYONEL | `sandbox/route.ts`, `calculate-vehicles/route.ts` | DÜZELTİLMELİ |
| CR-9 | 🟡 FONKSİYONEL | `sandbox/route.ts` | DÜZELTİLMELİ |
| CR-5 | 🟢 TEKNİK BORÇ | `admin/users/route.ts` | İYİLEŞTİRİLEBİLİR |
| CR-6 | 🟢 YANILTICI | `config.ts:29` | İYİLEŞTİRİLEBİLİR |
| CR-7 | 🟢 ÖLÜK KOD | `kmeans_tsp.py` | İYİLEŞTİRİLEBİLİR |
| CR-10 | 🟢 TEKNİK BORÇ | `auth/hint/route.ts` | BELGELENMELI |
| CR-11 | 🟢 GELİŞTİRME | `config.ts:13-15` | İYİLEŞTİRİLEBİLİR |

---

## 10. Detaylı Düzeltme Yol Haritası

Ayrıntılı düzeltme planı, öncelik sırası ve paralel çalışma rehberi için:
`docs/05_Code_Quality_Roadmap.md`
