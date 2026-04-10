# UniRide — Kod Kalitesi ve Güvenlik Düzeltme Yol Haritası

> **Tarih:** 09.04.2026 (09.04.2026 - Ekleyen: Copilot AI)
> **Kaynak:** `docs/09_04_2026_Codebase_Analysis_Report.md`
> **Hedef:** Her sorunu öncelik sırasına göre adım adım düzeltmek; paralel geliştirme yapılabilecek noktaları işaretlemek.

---

## Paralel Çalışma Notu

> Birden fazla geliştirici eş zamanlı çalışabilir. `[PARALEL ✅]` etiketi taşıyan görevler birbiriyle çakışmaz.
> Birleştirme sırasında `schemas.py` veya ortak dosyalara dokunuyorsanız merge conflict'e dikkat edin.

---

## 🔴 Faz A — Güvenlik ve Kritik Bug Düzeltmeleri

Bu fazı tamamlamadan production'a deploy etme.

### A-1: `POST /api/calculate-vehicles` Auth Guard Ekle [PARALEL ✅]
- **Öncelik:** KRİTİK
- **Dosya:** `src/app/api/calculate-vehicles/route.ts:145`
- **Bağlam:** Bu endpoint şu an kimliği doğrulanmamış herkese açık. Pahalı Python optimizasyonu tetikleniyor.
- **Yapılacak:**
  1. Dosyanın başına `import { requireAdmin } from "@/lib/admin-auth";` ekle
  2. `export async function POST(...)` gövdesinin ilk satırına `await requireAdmin(request);` ekle
- **Test:** İzinsiz çağrıda 401/403 alınmalı; adminle çağrıda optimizasyon çalışmalı.
- **Commit mesajı önerisi:** `security: add requireAdmin guard to POST /api/calculate-vehicles`

### A-2: CORS Wildcard'ı Env-Tabanlı Yapılandırmaya Çevir [PARALEL ✅]
- **Öncelik:** YÜKSEK
- **Dosya:** `optimizer_api/main.py:91`
- **Bağlam:** `allow_origins=["*"]` production'da tüm domain'lere kapıyı açıyor.
- **Yapılacak:**
  1. `import os` (zaten var mı kontrol et)
  2. `ALLOWED_ORIGINS` env var'ı oku; yoksa `["http://localhost:9002"]` varsayılanı kullan
  3. `allow_origins=[...]` güncelle
- **Örnek:**
  ```python
  _origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:9002").split(",")
  app.add_middleware(CORSMiddleware, allow_origins=_origins, ...)
  ```
- **Commit mesajı önerisi:** `security: make CORS allow_origins configurable via ALLOWED_ORIGINS env var`

### A-3: Sandbox IE — Eksik Endpoint'i Belgele veya Düzelt [PARALEL ✅]
- **Öncelik:** YÜKSEK (işlev bozuk)
- **Dosya:** `src/app/api/sandbox/route.ts:95`
- **Seçenek 1 (hızlı):** Sandbox'ın `/api/v1/optimize` yanıtındaki `ie_data` alanını kullan, ayrı fetch'i kaldır.
- **Seçenek 2 (tam):** `optimizer_api/main.py`'ye `/api/v1/ie/analyze` endpoint'ini ekle (kaynak: `resource_profiler.py`).
- **Commit mesajı önerisi:** `fix: remove broken /api/v1/ie/analyze call in sandbox, use ie_data from optimize response`

---

## 🟡 Faz B — Fonksiyonel Bug Düzeltmeleri

### B-1: `total_time_window_violations` Pydantic Modeline Ekle [PARALEL ✅]
- **Öncelik:** ORTA-YÜKSEK
- **Dosya:** `optimizer_api/models/schemas.py:128`
- **Bağlam:** GA-Split, PSO-Split, GWO-Split, HHO-Split stratejileri bu alanı `OptimizationResponse`'a geçiriyor ama model onu tanımlamıyor.
- **Yapılacak:** `OptimizationResponse` sınıfına ekle:
  ```python
  total_time_window_violations: Optional[int] = None
  ```
- **Commit mesajı önerisi:** `fix: add total_time_window_violations field to OptimizationResponse Pydantic model`

### B-2: `strategy` → `algorithm` Alan Adı Düzelt (Sandbox) [PARALEL ✅]
- **Öncelik:** ORTA-YÜKSEK
- **Dosya:** `src/app/api/sandbox/route.ts:80`
- **Sorun:** Fetch gövdesinde `strategy` gönderiliyor, Python API `algorithm` bekliyor.
- **Yapılacak:** `strategy,` → `algorithm: strategy,` olarak değiştir (veya destructure'ı düzelt).
- **Commit mesajı önerisi:** `fix: send algorithm field (not strategy) in sandbox fetch body`

### B-3: `strategy` → `algorithm` Alan Adı Düzelt (Calculate-Vehicles) [PARALEL ✅]
- **Öncelik:** ORTA-YÜKSEK
- **Dosya:** `src/app/api/calculate-vehicles/route.ts:79`
- **Sorun:** Aynı sorun — `strategy` yerine `algorithm` gönder.
- **Commit mesajı önerisi:** `fix: send algorithm field (not strategy) in calculate-vehicles fetch body`

### B-4: `max_tour_time` → `max_travel_time` Düzelt (Sandbox) [PARALEL ✅]
- **Öncelik:** ORTA
- **Dosya:** `src/app/api/sandbox/route.ts:78`
- **Sorun:** `max_tour_time` gönderiliyor; Python API `max_travel_time` bekliyor. Sandbox her zaman 120 dk varsayılanı kullanıyor.
- **Commit mesajı önerisi:** `fix: correct field name max_tour_time → max_travel_time in sandbox`

---

## 🟢 Faz C — Teknik Borç ve İyileştirme

Bu fazı diğer geliştiricilerle paralel bölebilirsiniz.

### C-1: `RATE_LIMIT_REQUESTS_PER_MINUTE` — TODO Ekle veya Kullan [PARALEL ✅]
- **Dosya:** `src/lib/config.ts:29`
- **Yapılacak:** Kullanılmayan export'a yorum ekle: `// TODO: connect to middleware rate limiter`
- **Commit mesajı önerisi:** `chore: document unused RATE_LIMIT_REQUESTS_PER_MINUTE constant`

### C-2: `kmeans_tsp.py` Ölü Kodu Temizle veya Kaydet [PARALEL ✅]
- **Dosya:** `optimizer_api/strategies/kmeans_tsp.py` ve `__init__.py`
- **Yapılacak:** Ya `__init__.py`'ye `"kmeans_tsp": KmeansTSPStrategy()` ekle ya da dosyayı arşive taşı.
- **Commit mesajı önerisi:** `chore: register or remove orphan kmeans_tsp strategy`

### C-3: `as any` Kullanımlarını Azalt [BAĞIMSIZ — kısmi]
- **Dosyalar:** `src/app/api/admin/users/route.ts:86,144` (en öncelikli)
- **Açıklama:** `getSupabaseAdmin()` zaten `SupabaseClient<Database>` döndürüyor. `as any`'ye ihtiyaç kalmaz; ancak önce neden eklendiği analiz edilmeli.

### C-4: Supabase Env Var Doğrulama [PARALEL ✅]
- **Dosya:** `src/lib/config.ts:13-15`
- **Yapılacak:** Boş string fallback yerine startup'ta kontrol ekle:
  ```ts
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) throw new Error("NEXT_PUBLIC_SUPABASE_URL missing");
  ```

---

## 📋 Görev Takip Tablosu

| ID | Görev | Öncelik | Paralel? | Durum |
|---|---|---|---|---|
| A-1 | Auth guard — calculate-vehicles | 🔴 KRİTİK | ✅ | ✅ TAMAMLANDI (09.04.2026) |
| A-2 | CORS env-tabanlı yapılandırma | 🔴 YÜKSEK | ✅ | ✅ TAMAMLANDI (09.04.2026) |
| A-3 | Sandbox IE endpoint düzeltme | 🔴 YÜKSEK | ✅ | ⬜ Bekliyor |
| B-1 | `total_time_window_violations` modele ekle | 🟡 ORTA | ✅ | ✅ TAMAMLANDI (09.04.2026) |
| B-2 | `strategy`→`algorithm` (sandbox) | 🟡 ORTA | ✅ | ✅ TAMAMLANDI (09.04.2026) |
| B-3 | `strategy`→`algorithm` (calc-vehicles) | 🟡 ORTA | ✅ | ✅ GEREK YOK — zaten doğru (`optimizeRoutes` servisi üzerinden) |
| B-4 | `max_tour_time`→`max_travel_time` (sandbox) | 🟡 ORTA | ✅ | ✅ TAMAMLANDI (09.04.2026) |
| C-1 | Kullanılmayan RATE_LIMIT sabiti | 🟢 DÜŞÜK | ✅ | ✅ TAMAMLANDI (09.04.2026) |
| C-2 | kmeans_tsp.py ölü kod | 🟢 DÜŞÜK | ✅ | ⬜ Bekliyor |
| C-3 | `as any` azalt | 🟢 DÜŞÜK | kısmi | ✅ TAMAMLANDI (10.04.2026) — `admin/users/route.ts:86,144` temizlendi; `DbUserRow` eklendi; bonus: `auth/hint/route.ts:78` baseline hata da düzeltildi |
| C-4 | Supabase env doğrulama | 🟢 DÜŞÜK | ✅ | ⬜ Bekliyor |

---

## 🔭 Uzun Vadeli İyileştirmeler (Faz D — Gelecek Oturumlar)

1. **Rate Limiter → Redis:** `auth/hint/route.ts:10`'daki in-process Map'i Redis ile değiştir (CR-10).
2. **FastAPI async:** `/api/v1/optimize` endpoint'ini `async def` + `asyncio.run_in_executor` ile yeniden yaz (CR-13).
3. **Zod Şeması — calculate-vehicles:** Ham cast yerine `zod.parse` kullan (CR-14).
4. **Test Coverage Artır:** `resource_profiler`'a ek olarak split stratejiler, clustering, local search için test ekle.
5. **`/api/v1/ie/analyze` Endpoint Ekle:** Sandbox IE analizini tam olarak hayata geçir.
