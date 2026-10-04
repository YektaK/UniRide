# UniRide Demo Yol Haritası: Günlük Plan ve Minimum Araç Sayısı (2026-10-04)

- **Durum:** PLANNED. Bu belge yalnızca plandır, kod değiştirmez.
- **Temel commit:** `d18bf2b` (`WIP`).
- **İlgili belgeler:** `AGENTS.md`, `ACTIVE_ROADMAP.md` (Dudullu Package 2), `docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md` v1.1 (bulgu kimlikleri: C1, H2, H4, H5, M1, QW1–QW3, QW10).
- **Kanıt kuralı:** Aşağıdaki dosya ve satır atıfları `d18bf2b` üzerinde doğrulandı. "Varsayım" diye işaretlenen maddeler doğrulanmadı.

## 1. Amaç, kapsam, kapsam dışı

**Amaç.** Yönetici bir gün seçer. O günün sabah kampüse toplama (`pickup`) ve öğleden sonra/akşam eve bırakma (`dropoff`) rotalarını görür. Ayrıca o gün için gereken **minimum araç sayısını** görür. Çözücünün hızı ve optimalliği önemli değildir. Amaç ürünün nasıl çalışacağını göstermektir.

**Kapsam.**
- Yerel çalıştırma (`npm run dev:dudullu`), sahibinin canlı Supabase projesi ve oradaki gerçek öğrenci verisi.
- Mevcut Dudullu önizleme backend'i: `src/app/api/admin/dudullu-preview/route.ts`, `src/services/daily-planning.ts`, `src/services/dudullu-preview.ts`.
- Yeni bir yönetici sayfası.
- Canlı veriye karşı **salt okuma**. Her canlı yazma adımı "**sahip yetkisi gerekir**" diye işaretlidir.

**Kapsam dışı.**
- Dağıtım (deploy). Dağıtım QW1 (C1, C1.b) ve QW2 (C4, H1) güvenlik düzeltmelerinden sonra yapılabilir.
- Yayınlama (Package 3), öğrenci onay akışları (Package 4) ve canlı veriye yazma.
- Çözücü kalitesi ve optimalliği (H2, H4, M26).
- Denetimin Faz 0 maddelerinin geneli. Yalnızca demoyu engelleyen H5 kapsamdadır.
- Eski `/admin/vehicle-planning` sayfası (H15 orada, demo onu kullanmaz).
- Öğrenci tohumlama (seed).

## 2. Doğrulanmış durum ve araştırma notlarına göre farklar

| # | Bulgu | Kanıt |
|---|---|---|
| F1 | Önizleme route'unu çağıran bir UI yok. `adminApi` içinde yalnızca `readiness.getDudullu` var. Kenar çubuğunda bağlantı yok. | `src/lib/admin-api.ts:243-246`, `src/components/layout/app-sidebar.tsx:53-67` |
| F2 | Yanıtta açık bir araç sayısı alanı yok. `assignments[].physicalVehicleId` var. | `src/services/dudullu-preview.ts:124-136`, `:665-677` |
| F3 | **Yeni ve demoyu engelliyor.** Fiziksel atama DFS'sinde alt sınır ve simetri kırma yok. Optimum bulunsa bile arama 50.000 düğüm bütçesini tüketip `indeterminate` döner. | `dudullu-preview.ts:6`, `:554-584`, `:595`. Yerel deney ve tablosu aşağıda. |
| F4 | Kabul yalnızca o tarih ve yön için bir `student_leg_decisions` satırıyla olur. Satır yoksa durum `pending_student_confirmation` olur. | `daily-planning.ts:377-413`, `route.ts:287` |
| F5 | **Fark.** `student_leg_decisions` tablosu canlıda yoksa sorgu hata verir. `selectRows` bu hatayı fırlatır ve yanıt genel **503 `PREVIEW_UNAVAILABLE`** olur. Açık bir neden kodu dönmez. | `route.ts:69-75`, `:216-221`, `:404-408` |
| F6 | Tek bir bozuk öğrenci kaydı bütün günü engeller. `scheduleDataInvalid` ise `admitted = []` olur. Örnek: Dudullu dersi olan ama `location_code` ya da `disability_type` eksik bir kayıt. | `route.ts:195-201`, `:287` |
| F7 | `decided_at` her INSERT'te `clock_timestamp()` olur. Bugün ya da geçmiş tarih için bugün eklenen onay, 22:00 kesimini geçtiği için `pending_admin_approval` olur. Yani geçmiş tarihli demo, satır ekleyerek açılamaz. | `supabase/migrations/20260929_create_student_leg_decisions.sql:12-33`, `daily-planning.ts:404-412` |
| F8 | H5 demo ortamında **gerçekten tetiklenir**. `main.py` router'ları `optimization`, ..., `readiness` sırasıyla import eder. Optimizasyon router'ı `utils.data_loader` modülünü yükler. Readiness router'ı ise önce `optimizer_api.utils.data_loader` modülünü dener. `.venv-jit`'te `optimizer_api`'yi eşleyen editable kurulum olduğu için bu deneme başarılı olur. Böylece aynı modül iki farklı adla yüklenir ve iki ayrı singleton oluşur. | `optimizer_api/main.py:18`, `optimizer_api/routers/readiness.py:10-17`, `optimization.py:56`, `:123-127`. `.venv-jit/Lib/site-packages/__editable___uniride_3_1_0_finder.py` |
| F9 | Editable finder ana checkout'u gösterir (`...\UniRide\optimizer_api`). Launcher `cwd=optimizer_api` ile `python main.py` çalıştırır (`scripts/start-dudullu-local.mjs:83-85`, `:312-317`). Bu nedenle bir worktree'den başlatılan optimizer, `optimizer_api.*` modüllerini **ana checkout'tan** okur. Demo merge'den sonra ana checkout'tan çalıştırılmalıdır. | yukarıdaki dosyalar |
| F10 | M1: Her (yön, anchor) çağrısında rota sayısı aktif araç sayısını geçerse sertifika `fleet_size_violation` verir. Önizleme bunu `OPTIMIZATION_NOT_SUCCESSFUL` olarak gösterir ve bütün gün engellenir. | `optimizer_api/verification/response_certifier.py:134-193`, `route.ts:367-373` |
| F11 | Launcher sırasıyla `UNIRIDE_PYTHON`, `.venv` ve PATH'e bakar, `.venv-jit`'e bakmaz. Ana checkout'ta `.venv` yok, yalnızca `.venv-jit` var. | `scripts/start-dudullu-local.mjs:170-198` |
| F12 | Readiness sayfası `cooldown_minutes`, `student_leg_decisions` ve yönetici hesabını kontrol etmez. Öğrenci, takvim, filo ve matris sayımlarını verir. | `src/app/api/admin/dudullu-readiness/route.ts:127-129`, `src/app/(app)/admin/readiness/page.tsx:21-64` |
| F13 | Bağlı (snapshot-bound) çağrılar matris eksikse fail-closed davranır: tek bir eksik arc `MATRIX_UNAVAILABLE` verir. C2'deki fail-open bu yolu etkilemez. | `optimizer_api/utils/matrix_repository.py:444-455`, `route.ts:318-332` |
| F14 | Admin sayfaları `next-intl` (`useTranslations`) ve shadcn `Card`/`Button` kullanır. Mesajlar `messages/tr.json` ve `messages/en.json` dosyalarında `page.admin.*` altındadır. | `readiness/page.tsx:4-6`, `:16`, `messages/tr.json:228` |

**F3 deney kanıtı.** Bu oturumda `assignPhysicalVehicles` geçici olarak dışa açıldı ve scratchpad'de `tsx` ile çalıştırıldı. Repoya dokunulmadı. Kurulum: aynı tip araçlar (Sw 2 / So 8 / cooldown 10), dalgalar sırayla pickup ve dropoff, rota süresi 50 dk.

| Dalga | Dalga başına rota | Filo | Sonuç | Kullanılan araç |
|---|---|---|---|---|
| 2 | 3 | 5 | `preview_ready` | 3 |
| 4 | 4 | 8 | `indeterminate` | 8 (alt sınır da 8) |
| 8 | 6 | 15 | `indeterminate` | 12 (alt sınır da 12) |
| 10 | 8 | 8 | `indeterminate` | atama yok (aslında yetersiz filo) |

Sonuç: gerçekçi bir günde ekranda "minimum araç" yerine "belirsiz" görünür.

## 3. Kilometre taşları

Genel kurallar:
- Dosya değiştiren her ajan kendi worktree'sinde ve kendi dalında çalışır.
- Ana dala yalnızca lider birleştirir: testler geçtikten sonra `merge --no-ff` ile.
- Python testleri ana checkout'taki ortamla çalışır. PowerShell örneği:

```powershell
$env:PYTHON_DOTENV_DISABLED="1"; $env:SUPABASE_URL=""; $env:SUPABASE_SERVICE_ROLE_KEY=""
& "C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe" -B -m pytest <dosyalar> -q
```

Testi bir worktree'nin kökünden `-m pytest` ile çalıştırın: o zaman worktree kodu, editable finder'dan önce gelir (F9).

### D0 — Ortam ve canlı veri hazırlığı

- **Amaç:** Yığını yerelde ayağa kaldırmak, canlı veriyi **salt okuma** ile envanterlemek ve devam/dur kararı vermek.
- **Değişecek dosyalar:** Varsayılan yol kod değiştirmez. İsteğe bağlı XS launcher düzeltmesi: `scripts/start-dudullu-local.mjs` (`resolvePythonBin`, `.venv` adaylarının ardından `.venv-jit` eklenir) ve `scripts/start-dudullu-local.test.mjs:149`.
- **Adımlar:**
  1. Sahip Supabase projesini yeniden etkinleştirir (**sahip işlemi**).
  2. `.env.local` dosyasında `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` ve `SUPABASE_SERVICE_ROLE_KEY` bulunur. `optimizer_api/.env` dosyasında `SUPABASE_URL` ve `SUPABASE_SERVICE_ROLE_KEY` bulunur (`optimizer_api/utils/data_loader.py:54-55`). Değerler yazdırılmaz.
  3. Python seçimi için `UNIRIDE_PYTHON` **mutlak yol** olarak ayarlanır, örneğin `$env:UNIRIDE_PYTHON="C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe"`. Göreli yol `rootDir` ile birleştirilir (`scripts/start-dudullu-local.mjs:171-178`). Bir worktree'den çalıştırıldığında bu yolda `.venv-jit` bulunmaz. Launcher bu durumda uyarı vermeden PATH'teki Python'a döner, o Python'da da fastapi yoktur. Ardından `node scripts/start-dudullu-local.mjs --check-only` çalıştırılır. Yorumlayıcı satırında `.venv-jit` yolunun göründüğü doğrulanır.
  4. Yığın `npm run dev:dudullu` ile başlatılır. Adres `http://127.0.0.1:9002`.
  5. Yönetici hesabı kontrol edilir: bir Auth kullanıcısı ve `public.users.role = 'admin'` olan satırı gerekir (`src/lib/admin-auth.ts:86-133`). Hesap yoksa sahip bunu Supabase panelinden oluşturur (**sahip yetkisi gerekir**). Kayıt formu ile admin oluşturulmaz: bu C1 açığını kullanmak olur.
  6. `/admin/readiness` sayfasındaki sayımlar not edilir: öğrenciler (`dudulluTarget` ile `completeTargetProfiles`), takvimler (`malformed`), aktif ve kullanılabilir araç sayısı, matris (`validArcCount` ile `expectedArcCount`).
  7. Sahip, Supabase SQL editöründe yalnızca SELECT ile şunları kontrol eder:
     - `to_regclass('public.student_leg_decisions')`;
     - aktif araçlarda `wheelchair_capacity`, `seating_capacity` ve `cooldown_minutes` sütunlarının NULL olmayan tamsayı olduğu;
     - Dudullu takvim girişlerinin haftanın günlerine dağılımı.
  8. Önizleme route'u `/optimize` çağrılarını anchor başına **sırayla** yapar (`route.ts:342-379`). Politika gereği her çözüm 60 sn'ye, bir istek ise 120 sn'ye kadar sürebilir (`optimizer_api/compute_policy.py:32-33`). `src/lib/optimizer-server.ts` içinde zaman aşımı yoktur. Bu yüzden D1 sonrasında aday günler için tam günlük önizleme süresi ölçülür. Ölçüm, salt okuma bir çağrıyla, ya D2 sayfasından ya da admin bearer token ile doğrudan route'a yapılır. Bulunan süreye göre D2'nin istemci zaman aşımı ayarlanır.
- **Kabul ölçütleri:**
  - `/health` ve `/admin/readiness` yanıt verir.
  - Tam gün önizleme süresi (anchor sayısı ve toplam saniye) ölçülmüş ve lider notuna yazılmıştır. D2'deki istemci zaman aşımı bu ölçüme göre belirlenir, örneğin ölçülen en uzun süre × 1,5. 120 sn bir varsayımdır, ölçülmüş bir değer değildir.
    - **Ölçüldü (2026-10-04, yerel çalıştırma):** tam gün önizleme (27 öğrenci, 12 dalga) uçtan uca **17,7 sn**. İstemci zaman aşımı yaklaşık 3 katı olarak 60 sn'ye ayarlandı (`DAILY_PLAN_TIMEOUT_MS`, `src/lib/admin-api.ts`).
  - Envanter tablosu (yalnızca sayımlar, kişisel veri yok) lider notuna yazılır.
  - Devam/dur kararı yazılıdır. Devam için şunların hepsi gerekir:
    - en az 1 kullanılabilir aktif araç;
    - matris eksik arc sayısı 0;
    - `dudulluTarget == completeTargetProfiles`, ya da K1'deki bozuk kayıt kuralı;
    - bir admin hesabı.
- **Testler (launcher düzeltilirse):** `node --test scripts/start-dudullu-local.test.mjs`
- **Boyut:** XS. **Ajan:** sahip ve lider. Launcher düzeltmesi: `gelistirici`/haiku.

### D1a — H5: tek DataLoader kökü

- **Amaç:** Matrise bağlı `/optimize` çağrılarının "matrix snapshot unavailable or changed" hatası vermemesi.
- **Dosyalar:**
  - `optimizer_api/routers/readiness.py:10-17`: `DataLoader`, `MatrixSnapshotError` ve `require_internal_api_key` aynı kökten (`utils.*` / `auth`) yüklenir.
  - `optimizer_api/routers/optimization.py:123-127`: `_matrix_snapshot_for_request` içinde bağlama kontrolünden önce `loader.refresh()` çağrılır.
  - Yeni sınır testi: `optimizer_api/tests/test_single_data_loader_root.py`.
  - Denetim izleyicisi: `docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md` Appendix J, H5 satırı.
- **Adımlar:**
  1. Kırmızı test yazılır: `import main` sonrasında `sys.modules` içinde `utils.data_loader` ve `optimizer_api.utils.data_loader` modüllerinden yalnızca biri bulunmalı. Her iki router da aynı `DataLoader` sınıfını görmeli.
  2. Import'lar düzeltilir.
  3. Refresh çağrısı eklenir.
  4. Appendix H.4 betiği çevrimdışı tekrar çalıştırılır.
- **Kabul:**
  - Yeni test geçer.
  - H.4'ün 4. adımı `True` basar, 6. ve 9. adımlar başarılı olur.
  - Bu iki dosya kullanılarak mevcut testler geçer: `optimizer_api/tests/test_optimization_matrix_binding.py`, `optimizer_api/tests/test_dudullu_matrix_readiness.py`.
  - Appendix J'de H5 satırı `FIXED` olarak güncellenir. Bu satır QW3'ün yalnızca H5 kısmını kapatır; C2 açık kalır.
- **Boyut:** S. **Ajan:** `python-pro`/sonnet. Denetçi: `denetci`/sonnet.

### D1b — Araç özeti ve atama aramasının dürüst sonlanması

- **Amaç:** Yanıtta açık bir "bu rotalar için gereken araç" alanı olması ve gerçekçi günlerde `indeterminate` yerine kanıtlı sonuç dönmesi (F2, F3).
- **Dosyalar:** `src/services/dudullu-preview.ts` (`assignPhysicalVehicles` `:513-605`, `DudulluPreviewResult` `:124-136`, `buildDudulluPreview` `:607-678`) ve `src/services/dudullu-preview.test.ts`.
- **Adımlar:**
  1. **Alt sınır:** Rota aralıkları en küçük cooldown kadar uzatılır. Aynı anda çakışan en fazla aralık sayısı `lowerBound` olur.
     - `lowerBound > filo` ise arama yapılmadan `shortage` döner.
     - `bestVehicleCount === lowerBound` olduğunda arama durur ve sonuç kanıtlı sayılır.
  2. **Simetri kırma:** Henüz kullanılmamış araçlar arasında, her (`swCapacity`, `soCapacity`, `cooldownMinutes`) imzasından yalnızca ilk araç denenir.
  3. Sonuca `vehicleSummary` eklenir:
     ```ts
     vehicleSummary: {
       minimumVehicles: number | null;   // farklı physicalVehicleId; best yoksa null
       minimumProven: boolean;           // sabit rotalar için atama minimal kanıtlandı
                                         // (arama tükenmeden bitti ya da best == lowerBound)
       lowerBound: number;               // cooldown dahil tepe eşzamanlı rota
       activeFleetSize: number;
       routesPerJob: { jobId: string; direction: TripDirection; anchorMinutes: number;
                       routeCount: number; studentCount: number }[];
     }
     ```
     `makeBlockedResult` bu alanı `null` olarak döndürür ve tip buna göre güncellenir.
     `minimumProven` şu anlama gelir: **çözücünün ürettiği sabit rotalar için** fiziksel araç ataması minimaldir. Rota sayısının kendisi minimal değildir; bu yüzden değer bir günlük "gerçek minimum araç" sayısı olarak sunulmaz.
- **Kabul:**
  - F3 deneyindeki 4/4/8 ve 8/6/15 senaryoları test olarak eklenir; ikisi de `preview_ready` ve `minimumProven=true` sonucunu verir.
  - 10/8/8 senaryosu `shortage` verir.
  - `:539` testi ("chooses the minimum distinct physical fleet") değişmeden geçer.
  - **Davranış değişikliği (varsayılan, ayrı karar gerektirmez):** `:567` testi şu anda 9 eşzamanlı rota ile 8 araçta `indeterminate` bekliyor; değişiklikten sonra sonuç `shortage` olur. Test bilerek güncellenir. Bütçe tükenme dalı, bütçe parametreleştirilerek ayrı bir testle korunur.
- **Testler:** `npx vitest run src/services/dudullu-preview.test.ts`
- **Boyut:** S. **Ajan:** `typescript-pro`/sonnet. Denetçi: `denetci`/opus, çünkü filo doğruluğu sözleşmesi değişiyor.

### D1c — Demo kabul modu, sanal filo, açık hata kodları

- **Amaç:**
  - Canlı DB'ye yazmadan "herkes geliyor" varsayımıyla önizleme almak (F4, F7).
  - Gerçek filodan bağımsız olarak, bu rotalar için gereken araç sayısını bulmak (F10).
  - Eksik tablo ve bozuk kayıtları açıkça raporlamak (F5, F6).
- **Dosyalar:**
  - `src/app/api/admin/dudullu-preview/route.ts` (`SERVICE_DATE_SCHEMA` `:20-22`, `loadBlockedPreview` `:124-381`, `POST` `:383-409`);
  - `src/services/dudullu-preview.ts` (`PreviewReasonCode` `:73-96`);
  - `src/app/api/admin/dudullu-preview/route.test.ts`.
- **İstek sözleşmesi:**
  - `{ serviceDate, admissionMode?: "recorded" | "assume_confirmed", fleetMode?: "live" | "virtual" }`.
  - Varsayılan `recorded`/`live`. Bu durumda mevcut davranış ve mevcut testler değişmez.
  - `:329` testi bilinmeyen alanları reddetmeye devam eder; yalnızca bu iki alan eklenir.
- **Yanıt sözleşmesi:**
  - `admissionMode` ve `fleetMode` yanıtta geri döner.
  - Varsayılan dışı bir mod seçildiyse `hypothetical: true` döner.
  - `publishable: false` her zaman sabittir.
  - Sayım tabanlı bir `candidateSummary` eklenir; kimlik içermez: `{ dudulluStudents, legsByAdmission, invalidStudentRecords }`.
- **`assume_confirmed` kuralları:**
  - Satırı olmayan bacak ve `pending_admin_approval` olan bacak `confirmed` sayılır.
  - Kayıtlı `cancelled` iptal olarak kalır.
  - Eski `ride_requests` engelleri ve bozuk öğrenci kayıtları K1'deki kurala göre işlenir.
  - Yeni bilgi kodu `ADMISSION_ASSUMED` eklenir.
  - Dönüşüm yalnızca route içinde, `buildScheduleDemands` çıktısı üzerinde yapılır. `daily-planning.ts` içindeki saf alan mantığına dokunulmaz.
- **Eksik tablo:** Supabase hatasında tablo yok kodu (`PGRST205` veya `42P01`) yakalanır.
  - `recorded` modunda 200 + `blocked_data` + `LEG_DECISIONS_UNAVAILABLE` döner.
  - `assume_confirmed` modunda karar olmadan devam edilir ve aynı kod bilgi olarak eklenir.
  - Diğer okuma hataları sabit 503 olarak kalır.
- **Sanal filo (`virtual`):**
  - **Sahip kararı K2 (2026-10-04) ile güncellendi:** tek bir şablon tipinden N özdeş kopya üretilir (şablon seçimi için §4'e bakın). Karışık tipli filoların atama aramasını tükettiği ölçülmüştür; özdeş filolar hızlı kanıtlanır. Aşağıdaki "her tipten" ifadesi bu karardan önceki taslaktır.
  - Canlı aktif araçların farklı (Sw, So, cooldown) tipleri alınır.
  - Her tipten N kopya üretilir; N, kabul edilen bacak sayısıdır. Kimlikler `virtual:<tip>:<n>` biçimindedir. **Bu tam sanal filo yalnızca DFS atamasına verilir.**
  - `/optimize` çağrısına tam filo gönderilmez. `OptimizationRequest`, `len(vehicles) > policy.max_vehicles` olan istekleri reddeder (varsayılan 50; `optimizer_api/compute_policy.py:29`, `optimizer_api/models/schemas.py:311-312`). Red durumunda route `OPTIMIZATION_NOT_SUCCESSFUL` döner (`route.ts`, `/optimize` çağrısının `catch` dalı, ~`:461-488`).
  - Her dalgada `/optimize` çağrısına en fazla `min(dalgadaki bacak sayısı, 50)` özdeş sanal araç gönderilir (filonun ilk `min(...)` kopyası). Sınır route'ta tek bir sabit olarak (`OPTIMIZER_MAX_VEHICLES`) tutulur ve yorumda `UNIRIDE_COMPUTE_MAX_VEHICLES` ile bağı belirtilir.
  - Bir rota, tek bir tipin karşılamadığı bir Sw/So birleşimi isterse sertifika yine reddedebilir. Bu, M1'in kalıntısıdır ve bilinen bir sınır olarak kabul edilir.
  - Aktif araç yoksa: `live` modunda `FLEET_SHORTAGE` döner; `virtual` modunda varsayılan şablon (Sw 4 / So 10 / cooldown 10) kullanılır (K2).
  - **K2 ile güncellendi:** `vehicleSummary.activeFleetSize`, atamada gerçekten kullanılan filodur (sanal modda N). Gerçek aktif filo ayrıca üst düzey `fleet.liveActiveFleetSize` alanındadır. UI eksik araç sayısını şöyle hesaplar: `minimumVehicles - fleet.liveActiveFleetSize`.
- **Temiz eksik filo raporu (`live`):** Optimizer `success=false` döndürür ve sertifikada `fleet_size_violation` varsa sonuç `OPTIMIZATION_NOT_SUCCESSFUL` yerine `shortage` + `FLEET_SHORTAGE` olur (M1'in demodaki etkisi). Bu iş S boyutunu aşarsa ertelenir ve belgelenir.
- **Kabul:**
  - Testler şunları doğrular:
    - her iki modda da Supabase istemcisinde yalnızca `select` çağrıldığı;
    - `insert`, `update`, `upsert`, `delete` ve `rpc` için spy sayısının 0 olduğu;
    - satırı olmayan ama planlanmış bacağın `assume_confirmed` modunda rotaya girdiği;
    - kayıtlı iptalin girmediği;
    - eksik tablonun iki moddaki davranışı;
    - sanal filoda 2 araçlık canlı filo ile 3 rotalık bir dalganın `preview_ready` ve `minimumVehicles=3` verdiği;
    - 60 kabul edilen bacaklı bir dalgada mock'lanmış `/optimize` gövdesindeki `vehicles.length` değerinin ≤ 50 olduğu, DFS'ye verilen sanal filonun ise ≥ 60 olduğu;
    - kimlik doğrulamasının gövdeden önce kalmaya devam ettiği (`:302`).
- **Testler:** `npx vitest run src/app/api/admin/dudullu-preview/route.test.ts src/services/dudullu-preview.test.ts src/services/daily-planning.test.ts`, ardından `npm run typecheck`.
- **Boyut:** M. **Ajan:** `typescript-pro`/sonnet. Denetçi: `denetci`/opus (onay çıkarımı ve canlı okuma yolu).

### D2 — Günlük plan sayfası (UI)

- **Amaç:** Yöneticinin tek ekranda günü, rotaları ve bu rotalar için gereken araç sayısını görmesi.
- **Dosyalar:**
  - yeni `src/app/(app)/admin/daily-plan/page.tsx` ve `page.test.tsx`;
  - yeni `src/services/daily-plan-view.ts` ve testi (saf görünüm modeli);
  - `src/lib/admin-api.ts` (`adminApi.preview.run`, readiness desenine benzer: `:211-239`);
  - `src/components/layout/app-sidebar.tsx:53-67` (`/admin/daily-plan`, `labelKey: "dailyPlan"`);
  - `messages/tr.json` ve `messages/en.json` (`common.sidebar.dailyPlan`, `page.admin.dailyPlan.*`).
- **Görünüm modeli (`daily-plan-view.ts`):**
  - `jobs`, yöne ve `anchorMinutes` değerine göre dalgalara gruplanır.
  - Düğüm adları `location1`/`location2` konum koduna çevrilir; `#occurrence` son eki atılır.
  - Durak saatleri hesaplanır: pickup için başlangıç `anchor - toplam`, dropoff için `anchor`; adımların süreleri eklenerek ilerlenir.
  - Araç zaman çizelgesi `assignments` verisinden hesaplanır: araç başına sıralı rota aralıkları.
  - Sanal araç kimlikleri "Araç 1..K" olarak gösterilir.
- **Sayfa:**
  - tarih seçici (`calendar` ve `popover`);
  - "Herkes onayladı say" anahtarı (`switch`, `assume_confirmed`);
  - "Sanal filo ile minimum" anahtarı (`fleetMode`);
  - Çalıştır düğmesi; yükleniyor, boş ve hata durumları;
  - istemci zaman aşımı D0'daki süre ölçümüne göre belirlenir (bkz. D0 adım 8);
  - özet kartları:
    - **"Bu rotalar için gereken araç"**: `minimumVehicles`. `minimumProven=false` ise "en fazla" etiketi eklenir. Kart "gerçek minimum" diye adlandırılmaz.
    - öğrenci, rota, durum, aktif filo ve eksik araç;
  - dalga bölümleri: "08:45 varış — Toplama", her rota için sıralı duraklar, süre ve Sw/So sayıları;
  - araç tablosu;
  - neden kodlarının sade Türkçe karşılıkları;
  - kalıcı "Taslak — yayınlanamaz" ve `hypothetical` rozetleri.
- **Kabul:**
  - Kenar çubuğundan sayfa açılır.
  - Mock'lanmış `preview_ready`, `shortage`, `blocked_data` ve 503 yanıtları doğru kartları ve metinleri gösterir.
  - Hiçbir yanıtta yayınla/kaydet düğmesi yoktur.
  - Öğrenci adı yerine K4'e göre etiket görünür.
  - Araç kartının başlığı "Bu rotalar için gereken araç" olur ve testte doğrulanır.
- **Testler:** `npx vitest run "src/app/(app)/admin/daily-plan/page.test.tsx" src/services/daily-plan-view.test.ts`, ardından `npm run typecheck` ve `npm run lint`.
- **Boyut:** M. **Ajan:** `gelistirici`/sonnet; düzen taslağı istenirse önce `tasarimci`/opus. Denetçi: `denetci`/sonnet.

### D3 — Demo cilası ve çalıştırma kılavuzu

- **Amaç:** Sınırların dürüstçe görünmesi ve demonun tekrarlanabilir olması.
- **Dosyalar:** `src/app/(app)/admin/daily-plan/page.tsx`, `messages/*.json`, `docs/DUDULLU_RUNTIME_READINESS.md` (yeni "Demo çalıştırma" bölümü).
- **Adımlar:**
  1. Sayfaya sabit bir bilgi kutusu eklenir: "Çözücü optimal değildir; rota sayısı gerçek minimum değildir (yalnızca araç ataması kanıtlanır). Zaman modeli basittir: her dalga tek varış/çıkış saatine bağlıdır (`use_time_windows: false`). Bekleme ve kampüse dönüş kontrolü yapılmaz (H2, H4)."
  2. Kılavuz yazılır: D0'daki adım 2–4, giriş, sayfa, tarih seçimi ve beklenen kartlar.
  3. Uçtan uca elle kontrol listesi çalıştırılır (bölüm 6).
- **Kabul:**
  - Kontrol listesinin tüm satırları işaretlidir.
  - Ekran görüntüsü lider notuna eklenir; kişisel veri görünmez.
- **H15:** H15 yalnızca eski sayfadadır (`src/app/(app)/admin/vehicle-planning/page.tsx`) ve demo onu kullanmaz. QW10'da kalır.
- **Boyut:** S. **Ajan:** `gelistirici`/haiku (metin), elle demo lider ve sahip.

### R1/R2 — Öğrenci araçta kalma süresi sınırı (sahip kararı K5, 2026-10-04)

- **Sahip kararı K5:** "En fazla seyahat süresi", bir **öğrencinin araçta kaldığı süredir**. Demo varsayılanı **90 dakikadır** ve demo ekranından ayarlanır. Aracın tur sınırı (`max_travel_time`, depo -> duraklar -> depo) için varsayılan **üst sınır 150 dakikadır** ve o da ayarlanır. (Önceki sabit `max_travel_time: 120` kaldırıldı.)
- **R1 (optimizer):** `max_ride_time` alanı (1–600 dk). Tanım: pickup'ta öğrencinin durağından kampüse kadar (kapanış yayı dahil), dropoff'ta kampüsten ayrılıştan öğrencinin durağına kadar. Sertifika ihlali `ride_time_violation` olarak reddeder. Bekleme süresi sertifikada görünmez (H2).
- **R2 (Next.js):**
  - İstek: `maxRideTimeMinutes` (tam sayı 15–240, varsayılan 90) ve `maxTourMinutes` (tam sayı 30–300, varsayılan 150). Hatalı değer `400 INVALID_LIMIT`. Her `/optimize` çağrısına `max_ride_time` ve `max_travel_time` olarak iletilir.
  - Yanıt: `limits: { maxRideTimeMinutes, maxTourMinutes, minimumFeasibleRideMinutes }`. Her yanıtta (engellenenler dahil) bulunur.
  - Bir öğrencinin kendi doğrudan yolculuğu (dalganın yönünde kampüs yayı: pickup'ta durak -> kampüs, dropoff'ta kampüs -> durak) sınırı aşarsa çözücü çağrılmadan `RIDE_TIME_LIMIT_INFEASIBLE` (`blocked_data`) döner; `minimumFeasibleRideMinutes` en büyük doğrudan yayın yukarı yuvarlanmış halidir. Çözücü sertifikasında `ride_time_violation` çıkarsa aynı kod döner (minimum `null`).
  - Rota başına en uzun öğrenci yolculuğu (`maxRideMinutes`) ve günün en büyüğü görünüm modelinde `route_details`'ten hesaplanır: pickup'ta toplam - ilk yay, dropoff'ta toplam - kapanış yayı.
  - Arayüz: iki sayı alanı ("Öğrenci en fazla araçta (dk)" 90, "Araç turu en fazla (dk)" 150), kullanılan sınırlar önizleme başlığında, her rotada "En uzun öğrenci yolculuğu: X dk".
- **Kısıt:** Doğrudan yolculuk ön kontrolü yalnızca alt sınırdır; çözücü, paylaşılan rotalarda sınırı tutturamazsa yine `RIDE_TIME_LIMIT_INFEASIBLE` (sertifikadan) ya da `OPTIMIZATION_NOT_SUCCESSFUL` döner. Bu bir sonuç kalitesi iddiası değildir.
- **Canlı çalıştırma notu (2026-10-04):** Pazartesi 2026-10-05 için 90 dk öğrenci / 150 dk tur sınırı ve sanal filoyla (özdeş 4 Sw / 10 So araç) canlı çalıştırma: **3 araç**, 27 öğrenci, 54 yolculuk, 16 rota, 12 dalga; en uzun öğrenci yolculuğu 89 dk (sınır 90). En yoğun dalga 08:45 varış: 20 öğrenci (5 Sw, 15 So). Sw ve So öğrencileri yalnızca kendi koltuklarını kullanır ve ikisi ayrı denetlenir; bu yüzden yalnızca kapasite alt sınırı max(ceil(5/4), ceil(15/10)) = **2** araçtır. Üçüncü araç kapasiteden değil, öğrencinin araçta kalma (90 dk) ve araç turu (150 dk) sınırlarının rotaları bölmesinden gelir. Sonuç veriye bağlıdır, bir hata değildir. R3 bu açıklamayı sayfada "Neden N araç?" bloğu olarak gösterir.

## 4. Sahip için karar noktaları

**Sahip kararları (2026-10-04):**
- **K5 onaylandı:** öğrencinin araçta kalma süresi sınırı, varsayılan 90 dk, ayarlanabilir; araç turu üst sınırı varsayılan 150 dk, ayarlanabilir (bkz. R1/R2).
- **K1 onaylandı:** `assume_confirmed` demo modu, bu bölümdeki (a), (b) ve (c) önerileriyle. `ACTIVE_ROADMAP.md`'nin "onay çıkarımı yapma" kuralına **bilinçli, sahip onaylı bir istisnadır**: yalnızca önizleme içindir, DB'ye hiçbir şey yazmaz ve yayınlanamaz (`publishable: false`).
- **K2 onaylandı:** demoda `fleetMode: "virtual"` (sanal filo) varsayılandır; `live` da desteklenir. Sahibin onayladığı yalnızca budur.
  - **Geliştirici varsayılanı (koordinatör brifi), sahip kararı değildir:** sanal filo, tek bir şablon tipinin N özdeş kopyasıdır. Şablon: tüm aktif araçlar aynı (Sw, So, cooldown) imzasındaysa o tip; değilse en yaygın imza (eşitlikte toplam kapasitesi en büyük olan); aktif araç yoksa Sw 4 / So 10 / cooldown 10. N, o günün kabul edilen bacak sayısıdır.
  - API'nin kendi varsayılanı `live` olarak kalır (mevcut sözleşme ve testler değişmez); demo arayüzü (D2) `virtual` gönderir.
- **K3:** demo tarihini sahip demo sırasında seçer.
- **K4 onaylandı:** yanıtta öğrenci adı yoktur. Not: canlı DB'deki öğrenci adları kod benzeri değildir; bu yüzden gösterim etiketi olarak konum kodu (`So1`, `Sw3` gibi) kullanılır. Yanıtta bunun için `occurrenceLabels` (occurrenceId -> konum kodu) bulunur.
- D0 (2026-10-04): veri GO: 28 öğrenci, 812/812 matris arkı, 1 aktif araç, `student_leg_decisions` tablosu yok. Kaynak: D0 salt-okur envanteri, 2026-10-04, Supabase MCP SELECT sorguları.

**Belirlenmiş varsayılanlar (ayrı karar gerektirmez):**
- Pickup ve dropoff birlikte planlanır. Fiziksel araç ataması zaten günü bütün olarak ele alır (`dudullu-preview.ts:654`). UI'da yön filtresi olur.
- D1b'de `:567` testi `indeterminate` yerine kanıtlı `shortage` bekleyecek şekilde güncellenir. Bütçe tükenme dalı ayrı bir testle korunur.
- Canlı yazma gerektiren her adım D0'da ve bölüm 5'te "**sahip yetkisi gerekir**" olarak işaretlidir ve tek tek onaylanır.

- **KARAR K1 — `assume_confirmed` demo modu.** Bu karar tek pakettir ve üç parçadan oluşur:
  - (a) **Kabul:**
    - Öneri: istek bayrağı `admissionMode: "assume_confirmed"`. Yalnızca admin kullanır ve DB'ye yazmaz. Yanıtta `hypothetical` ve `ADMISSION_ASSUMED` ile etiketlenir. Kayıtlı iptaller korunur.
    - Alternatif: canlıya `student_leg_decisions` satırı eklemek (**sahip yetkisi gerekir**). F7 nedeniyle yalnızca gelecek tarihlerde ve önceki gün 22:00'den önce işe yarar. Önerilmez.
  - (b) **Eski `ride_requests` engelleri** (`route.ts:250-256`, `:271-275`):
    - Öneri: bu modda öğrenci dahil edilir ve `LEGACY_AMBIGUOUS_CONFIRMATION` bilgi olarak kalır.
    - Alternatif: öğrenci dışarıda bırakılır ve sayısı gösterilir.
  - (c) **Bozuk öğrenci kayıtları** (F6):
    - Öneri: yalnızca bu modda, profil düzeyindeki hatalı kayıtlar dışarıda bırakılır. Sayısı `candidateSummary.invalidStudentRecords` ile gösterilir.
    - Kopya kimlik gibi bütünlük hataları yine bütün günü engeller.
  - Not: `ACTIVE_ROADMAP.md` "onay çıkarımı yapma" der. Bu mod bilinçli bir istisnadır: yalnızca önizleme içindir ve yayınlanamaz. Sahip onayı kayda geçirilmelidir.
- **KARAR K2 — "Gereken araç" tanımı.**
  - Öneri: demoda varsayılan `fleetMode: "virtual"`. Böylece gereken araç sayısı gerçek filodan bağımsız ölçülür ve gerçek filo ile arasındaki fark gösterilir.
  - `live` modu ise "mevcut filo yetiyor mu?" sorusunu yanıtlar.
  - Her iki modda da sayı, çözücünün ürettiği sabit rotalar için geçerlidir.
- **KARAR K3 — Demo tarihi.**
  - Öneri: D1 bittikten sonra Pazartesi–Cuma için salt okuma önizleme alınır ve en dolu hafta içi günü seçilir.
  - Tarihin yalnızca haftanın günü önemlidir (`daily-planning.ts:148`). Geçmiş ya da gelecek tarih fark etmez.
- **KARAR K4 — Öğrenci kimliği.**
  - Öneri: ekran paylaşımı için varsayılan olarak "Öğrenci 1..N" ve konum kodu gösterilir.
  - İsim göstermek yanıta ek bir kişisel veri alanı eklemek demektir; bu ayrıca onaylanmalıdır.

## 5. Riskler ve D0'da veri eksik çıkarsa

| Risk / durum | Belirti | Seçenekler (öneri önce) |
|---|---|---|
| Supabase duraklatılmış ya da kota dolmuş | readiness 503 | Sahip etkinleştirir. Demo öncesi 1 saat içinde yeniden kontrol edilir. |
| `student_leg_decisions` canlıda yok | şu an 503 (F5) | (a) D1c + `assume_confirmed`, migration gerekmez. (b) Migration uygulanır (**sahip yetkisi gerekir**; QW1'deki RLS incelemesiyle birlikte). |
| Matriste eksik arc ya da `D.Kampus` yok | `MATRIX_UNAVAILABLE` (F13) | (a) Eksik konumu olmayan bir gün seçilir (K3). (b) Sahip mevcut yöntemiyle `time_matrix` tablosunu doldurur (**sahip yetkisi gerekir**; bu depoda doğrulanmış bir doldurma aracı bulunmadı). (c) Öğrenciyi sessizce düşürmek: **önerilmez**. |
| Aktif araç yok ya da sütun NULL | `FLEET_SHORTAGE` / `FLEET_INVALID` | Sahip araç ekler ya da düzeltir (**sahip yetkisi gerekir**). Sanal filo için en az bir geçerli tip gerekir. |
| Öğrenci profili eksik | `SCHEDULE_DATA_INVALID`, gün boş | K1(c). Ya da sahip profilleri düzeltir (**sahip yetkisi gerekir**). |
| Admin hesabı yok | 401/403 | Sahip panelden oluşturur (**sahip yetkisi gerekir**). C1 yolu kullanılmaz. |
| H5 düzeltilmedi | `OPTIMIZATION_NOT_SUCCESSFUL` | D1a demonun ön koşuludur. |
| Dalga başına rota sayısı filodan büyük (M1) | `OPTIMIZATION_NOT_SUCCESSFUL` | K2 sanal filo. Ya da D1c'deki temiz eksik filo raporu. |
| Uzun çözüm süresi (anchor başına sıralı çağrı, her çözüm ≤ 60 sn) | UI bekler ya da zaman aşımına düşer | D0 adım 8'deki ölçüm yapılır ve zaman aşımı ona göre ayarlanır. Anchor sayısı az bir gün seçilir. |
| Worktree'den başlatma (F9) | eski kod çalışır | Demo merge'den sonra ana checkout'tan başlatılır. |
| Rota sayısı optimal değil, zaman modeli basit | yanlış beklenti | D3 etiketleri; "tasarruf" iddiası yapılmaz (`ACTIVE_ROADMAP.md`). |
| Ekran paylaşımında kişisel veri | gizlilik | K4 anonim etiketler; konsol ve log'da kimlik basılmaz. |

## 6. Uçtan uca elle demo kontrol listesi (D3)

1. Ana checkout `WIP` dalında ve D0–D2 birleştirilmiş durumda. Launcher `.venv-jit`'i kendisi bulur (`UNIRIDE_PYTHON` yalnızca geçersiz kılmak içindir). `npm run dev:dudullu` iki sürecin de hazır olduğunu basar.
2. Admin olarak giriş yapılır. Kenar çubuğunda "Günlük Plan" görünür.
3. `/admin/readiness` sayfasında matris eksik arc sayısı 0'dır.
4. K3 tarihi seçilir (Pazartesi en çok öğrenciye sahiptir), iki anahtar açılır, "Planı oluştur"a basılır. D0'da ölçülen süre içinde (yaklaşık 18 sn; zaman aşımı 60 sn) `preview_ready` görünür.
5. Kartlar kontrol edilir:
   - "Bu rotalar için gereken araç" kartında `minimumProven` doğrudur, yani "en fazla" etiketi yoktur;
   - öğrenci ve rota sayıları `candidateSummary` ile tutarlıdır;
   - aktif filo ve eksik araç sayısı görünür.
6. Her dalgada duraklar sıralıdır. Saatler pickup'ta anchor'da biter, dropoff'ta anchor'da başlar.
7. Araç tablosunda aynı araçtaki rotalar çakışmaz ve aralarında cooldown kadar boşluk vardır.
8. Anahtarlar kapatılıp tekrar çalıştırılır. Beklenen sonuç `PENDING_STUDENT_CONFIRMATION` ile boş gündür (kayıt yoksa). Bu, canlı veriye hiçbir şey yazılmadığını gösterir.
9. "Yayınlanamaz" başlığı ve sabit "Bilinen sınırlamalar" kutusu görünür. İki anahtar ve "Planı oluştur" düğmesi belirgin görünür (anahtarlar iki durumda da ayırt edilir, düğme dolgulu birincil renktedir). Ekran görüntülerinde öğrenci adı yoktur.

## 7. İzleyici

| ID | Başlık | Durum | Önerilen dal | Bağımlılık |
|---|---|---|---|---|
| D0 | Ortam, canlı veri envanteri ve devam/dur kararı (+ isteğe bağlı launcher `.venv-jit`) | Launcher düzeltmesi DONE (merge `0dc2616`); canlı envanter tamamlandı (bkz. §4) | `chore/demo-d0-launcher-venv-jit` (yalnızca kod gerekirse) | sahip |
| D1a | H5 tek DataLoader kökü ve refresh | DONE (merge `5796d93`) | `fix/demo-d1a-h5-single-loader` | D0 |
| D1b | `vehicleSummary`, alt sınır ve simetri kırma | DONE (merge `b9f6655`) | `feat/demo-d1b-vehicle-summary` | — |
| D1c | `assume_confirmed`, sanal filo, `LEG_DECISIONS_UNAVAILABLE`, temiz eksik filo raporu | DONE (merge `d05e7fd` ve `23ec2b5`; K1, K2, K4 sahip kararı 2026-10-04) | `feat/demo-d1c-admission-fleet-modes` | D1b, K1, K2 |
| D2 | `/admin/daily-plan` sayfası, görünüm modeli, `adminApi.preview`, kenar çubuğu, i18n | DONE (merge `ab92691`) | `feat/demo-d2-daily-plan-page` | D1b, D1c |
| D3 | Sınırlama etiketleri, kılavuz ve elle demo | DONE (merge `70c0e1c`: sabit sınırlama kutusu, çalıştırma kılavuzu, tema renk düzeltmesi, 60 sn zaman aşımı). Bölüm 6'daki elle kontrol listesi henüz işaretlenmedi: sahip/koordinatör canlı veriyle çalıştırır | `feat/d3-demo-polish` | D0–D2, K3, K4 |
| R1 | Optimizer `max_ride_time` alanı, sertifika kontrolü (`ride_time_violation`), `ga_split` bağlantısı | DONE (merge `5881570` ve `45cedd2`) | `worktree-agent-ad53deffb25237cba` | K5 |
| R2 | Önizleme rotası, görünüm modeli ve günlük plan arayüzünde ride-time sınırı (`maxRideTimeMinutes`, `maxTourMinutes`, `limits`, `RIDE_TIME_LIMIT_INFEASIBLE`, rota başına en uzun yolculuk), belgeler | DONE (merge `be74961`) | `worktree-agent-a39bee331766c35a7` | R1, D3, K5 |
| R3 | "Neden N araç?" açıklaması (`fleet.maxCapacity`, kapasite alt sınırı `computeCapacityFloor`, sayfa bloğu tr/en); ulaşılamaz sınır ipucu (240 dk üstü); `ROUTE_OUTSIDE_SERVICE_DAY` biçim düzeltmesi; `admin-api` oturum zaman aşımı (10 sn, hızlı hata) | IMPLEMENTED, birleştirme bekliyor | `worktree-agent-aeb2b5df07dcf1902` | R2 |

D1a ve D1b paralel ilerleyebilir; D1c, D1b'nin tipleri üzerine kurulur. Her birleştirmeden önce odaklı testler çalıştırılır ve ardından `npm run typecheck` ile `npm run lint` geçmelidir. Atlanan kontroller birleştirme notunda açıkça yazılır.
