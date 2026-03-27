# UniRide Tam Sistem Tasarım Dokümanı

> **Tarih:** 25 Mart 2026  
> **Kapsam:** Faz 1-4 tüm karar noktaları, her biri için 2-3 seçenek  
> **Amaç:** Mevcut hedeflere ulaşmak ve gelecek geliştirmelere açık olacak şekilde sistemi yeniden yapılandırmak

---

## Karar Noktası 1: API Katmanı Mimarisi

> Rota optimizasyonu istekleri frontend → Python API'ye nasıl iletilmeli?

### Seçenek A: İşlev Bazlı Next.js Proxy (Mevcut yapıyı düzelt) ⭐ ÖNERİLEN

```
Frontend → /api/optimize-route        → optimizer-service.ts → Python
Frontend → /api/calculate-vehicles     → optimizer-service.ts → Python  (YENİ)
Frontend → /api/compare-algorithms     → optimizer-service.ts → Python
```

Her endpoint kendi amacına odaklı kalır. `calculate-vehicles` düzeltilip Python'a bağlanır.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Mevcut yapıya minimum müdahale | 3 farklı endpoint'te benzer auth + error handling tekrarı |
| Her endpoint SRP'ye uygun | optimizer-service.ts büyüyebilir |
| Frontend'de değişiklik minimum | Her yeni Python endpoint için Next.js route da gerekir |
| Auth/CORS Next.js tarafında yönetilir | Proxy katmanı gecikme ekler (~10-20ms) |

---

### Seçenek B: Tekil Gateway Endpoint

```
Frontend → /api/optimizer (POST)  → body.action ile yönlendirme → Python
  body: { action: "optimize" | "compare" | "calculate", ... }
```

Tek endpoint, `action` parametresine göre Python'daki farklı endpoint'leri çağırır.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Tek bakım noktası, auth/error DRY | Endpoint büyür, SRP ihlali |
| Yeni Python özelliği eklemek kolay (yeni action) | Type safety zorlaşır (union types) |
| Frontend'de tek fetch URL | Swagger/OpenAPI belgeleme zorlaşır |

---

### Seçenek C: Frontend → Doğrudan Python API (Next.js proxy'siz)

```
Frontend → http://localhost:8000/api/v1/optimize  (doğrudan)
Next.js API → sadece auth token verify endpoint
```

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Aracı katman yok, minimum gecikme | Python'a auth middleware eklenmeli |
| Next.js API route bakımı yok | CORS konfigürasyonu gerekir |
| Python API bağımsız scale edilebilir | Production'da ayrı domain/port yönetimi |
| | Frontend environment variable karmaşıklığı |
| | Supabase JWT doğrulama Python'da yapılmalı |

---

## Karar Noktası 2: Ölü Kod Stratejisi

> `vehicle-calculator.ts`, `doubus/route-strategies/` ve eski TypeScript optimizasyon koduyla ne yapmalı?

### Seçenek A: Temiz Silme (Tek seferde) ⭐ ÖNERİLEN

Faz 1.1 tamamlandıktan hemen sonra: `vehicle-calculator.ts` ve `doubus/route-strategies/` tamamen silinir.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Temiz codebase, kafa karışıklığı yok | Geri dönüş isterse git history'den çıkarmak gerekir |
| Yeni geliştirici eski kodu yanlışlıkla kullanamaz | Bir seferde çok dosya silmek riski |
| Bundle size küçülür | |

---

### Seçenek B: Deprecation → Planlı Silme (2 aşamalı)

1. Aşama: Dosyaların başına `@deprecated` + büyük yorum, import'ları kır
2. Aşama: 1 hafta sonra tamamen sil

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Geçiş süreci var, diğer dev'ler bilgilendirilir | 1 hafta boyunca ölü kod tutulur |
| Kod review'da fark edilir | Biri yanlışlıkla deprecate edilmiş kodu kullanabilir |
| Git blame'de neden silindiği anlaşılır | Ekstra commit/PR gerekir |

---

### Seçenek C: Fallback Olarak Tut

Python API erişilemezse TypeScript kodu devreye girer.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Python sunucusu çökerse sistem çalışmaya devam eder | İki farklı algoritma kodu bakımı (çok pahalı) |
| | TypeScript tarafında GA/PSO dosyaları yok (zaten crash) |
| | Farklı sonuçlar veren iki sistem = güvenilmezlik |
| | time_matrix TypeScript'te kullanılmıyor |

---

## Karar Noktası 3: Time Matrix Yönetimi

> Sürüş süreleri nasıl yönetilmeli? Şu an 29 sabit nokta var, yeni nokta eklenebilir mi?

### Seçenek A: Sabit Matris + Encoding Fix (Mevcut yapıyı düzelt) ⭐ ŞİMDİLİK ÖNERİLEN

Mevcut 29 nokta yeterli. DataLoader encoding sorunu fix edilir, matris Supabase'den sorunsuz yüklenir.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Minimum değişiklik, hızlı düzeltme | Yeni mahalle/nokta eklemek SQL işi gerektirir |
| Veri doğerulanmış, güvenilir | 29 nokta yetersiz kalabilir |
| Ekstra API maliyeti yok | Gerçek trafik verisi yansımıyor |

---

### Seçenek B: Dinamik Matris (Google Distance Matrix API)

Yeni öğrenci/adres eklenince API'den gerçek süreler çekilip `time_matrix`'e eklenir.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Yeni nokta otomatik eklenir | Google API maliyeti ($5/1000 element) |
| Gerçek trafik verisine daha yakın | API quota yönetimi gerekir |
| Ölçeklenebilir | Hesaplama: 30 yeni nokta = 30×29 = 870 API çağrısı (pahalı olabilir) |

---

### Seçenek C: Hybrid (Sabit + İsteğe Bağlı Güncelleme)

29 sabit nokta korunur. Admin panelden "Matrisi Güncelle" butonuyla Google API çağrılıp Supabase güncellenir. Sadece ihtiyaç olduğunda yapılır.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Kontrollü maliyet (sadece gerektiğinde) | Admin'in ne zaman güncelleyeceğini bilmesi gerekir |
| Mevcut yapıyla uyumlu | Güncelleme sırasında eski verilerle çalışılabilir |
| Yeni nokta eklemek mümkün ama zorunlu değil | Admin UI'a güncelleme butonu eklenmeli |

---

## Karar Noktası 4: Veritabanı Şeması (Rota Planı Kalıcılığı)

> Optimizasyon sonuçları nasıl kaydedilmeli?

### Seçenek A: Minimal JSON (Hızlı başlangıç) ⭐ ÖNERİLEN

```sql
route_plans (
  id UUID PRIMARY KEY,
  plan_date DATE NOT NULL,
  direction TEXT CHECK (direction IN ('pickup', 'dropoff')),
  algorithm_used TEXT,
  clustering_used TEXT,
  total_vehicles INT,
  total_duration_minutes FLOAT,
  execution_time_seconds FLOAT,
  status TEXT DEFAULT 'draft',  -- draft / confirmed / active / completed
  routes JSONB NOT NULL,        -- Tüm rota detayları JSON olarak
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);
```

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Hızlı implementasyon, tek tablo | Rota içi arama/filtreleme zor (JSON parse) |
| Python API response'u doğrudan kaydedilir | Öğrenci bazlı sorgu yapmak karmaşık |
| Schema değişikliği az | Supabase RLS politikaları JSON içine uygulanamaz |
| İlişki yönetimi yok, basit | |

---

### Seçenek B: Normalize Edilmiş (Tam İlişkisel)

```sql
route_plans (id, plan_date, direction, algorithm, status, created_by)
route_vehicles (id, plan_id FK, vehicle_id, total_duration, sw_count, so_count)
route_stops (id, vehicle_id FK, stop_order, location_code, arrival_minutes)
route_student_assignments (id, vehicle_id FK, student_id FK, location_code)
```

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| "Öğrenci X hangi araçta?" tek sorguyla bulunur | 4 tablo, migration karmaşık |
| Supabase RLS her tablo seviyesinde çalışır | Python response'u parse edip 4 tabloya yazmak gerekir |
| Raporlama ve istatistik kolaylaşır | Daha fazla JOIN, biraz daha yavaş |
| İleride sürücü ataması bu yapıya entegre olur | |

---

### Seçenek C: Event Sourcing (İz takipli)

```sql
route_events (
  id UUID, plan_id UUID, event_type TEXT, event_data JSONB, created_at, created_by
)
-- event_type: 'created', 'confirmed', 'driver_assigned', 'student_cancelled', 'completed'
```

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Tam geçmiş takibi: kim, ne zaman, ne yaptı | Karmaşık implementasyon |
| Geri alma (undo) kolay | Mevcut durumu hesaplamak events replay gerektirir |
| Audit trail otomatik | Performans sorunu olabilir (çok event) |
| | Bu projede şu an overkill |

---

## Karar Noktası 5: Onay/İptal Mekanizması

> Öğrenciler ertesi günkü servis talebini nasıl onaylayacak/iptal edecek?

### Seçenek A: Otomatik Schedule + İptal (Opt-out) ⭐ ÖNERİLEN

Ders programından otomatik servis talebi oluşturulur. Öğrenci sadece iptal ederse çıkar.

```
Her gece 00:00 → schedule'dan yarınki ride_requests üretilir
Öğrenci 22:00'a kadar iptal edebilir
İptal etmezse → "onaylı" sayılır
```

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Öğrenci için minimum efor (varsayılan: binecek) | Gerçekte gelmeyecek öğrenciler boşuna planlanır |
| Cron job basit, güvenilir | Öğrenci uygulamayı açmazsa habersiz planlanır |
| "İptal" tek aksiyon, UI basit | Ders dışı talepler ayrı akışla yönetilmeli |

---

### Seçenek B: Aktif Onay (Opt-in)

Öğrenci her gün uygulamayı açıp yarınki servisi aktif olarak onaylamalı.

```
Her gece 00:00 → schedule'dan "bekleyen" ride_requests üretilir
Öğrenci 22:00'a kadar onaylamalı
Onaylamadıysa → taşınmaz
```

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Sadece gerçekten binecekler planlanır | Öğrenci unutursa servisten kalır |
| Gerçekçi talep tahmini | Her gün uygulama açma zorlaması |
| | Push notification altyapısı şart (hatırlatma) |

---

### Seçenek C: Hybrid (Varsayılan onaylı + düzeltme penceresi)

Ders saatlerindeki talepler otomatik onaylı. Öğrenci istisnai durumda (hasta, izinli) iptal eder. Ders dışı talepler ise aktif onay gerektirir.

```
Ders içi → Otomatik onaylı, iptal penceresi var
Ders dışı → Öğrenci talep oluşturmalı + onaylamalı
Akşam 22:00 → Tüm onaylılar rota planlamasına alınır
```

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| En mantıklı kullanıcı deneyimi | İki farklı akış → daha karmaşık UI |
| Ders programı otomasyonu korunur | Ders dışı talep akışı ayrıca geliştirilmeli |
| Gerçekten iptal edenler ayrılır | Deadline yönetimi iki akış için ayrı |

---

## Karar Noktası 6: Sürücü Atama ve Bildirim

> Optimizasyon sonrası araçlara sürücü nasıl atanacak?

### Seçenek A: Manuel Atama (Admin seçer) ⭐ ŞİMDİLİK ÖNERİLEN

Admin rota planladıktan sonra her araca sürücüyü dropdown'dan seçer.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Basit implementasyon | Admin'in sürücü müsaitliğini bilmesi gerekir |
| Admin tam kontrolde | Büyük filolarda zaman alıcı |
| Sürücü tercihleri dikkate alınabilir | Otomasyon yok |

---

### Seçenek B: Otomatik Atama (Müsaitlik bazlı)

Sürücüler müsaitlik bildirir. Sistem en uygun eşleşmeyi yapar.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Hızlı, otomasyon | Müsaitlik yönetimi ek tablo/UI gerektirir |
| Sürücü workload dengesi otomatik | Karmaşık matching algoritması |
| | "Uygun sürücü yok" senaryosu yönetimi |

---

### Seçenek C: Öneri + Onay (Hybrid)

Sistem sürücü önerir, admin onaylar/değiştirir.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Otomasyon + insan kontrolü dengesi | Hem öneri algoritması hem onay UI gerekir |
| Admin hızlı onaylayabilir | Önerinin kalitesi müsaitlik verisine bağlı |
| Kötü eşleşme riski düşük | İki adımlı süreç |

---

## Karar Noktası 7: Gerçek Zamanlı Özellikler (Canlı Takip)

> Servis sırasında sürücü konumu ve ETA nasıl takip edilecek?

### Seçenek A: Supabase Realtime ⭐ ÖNERİLEN (mevcut altyapıyla uyum)

```sql
driver_locations (driver_id, lat, lng, updated_at, route_plan_id)
```
Sürücü uygulaması konum günceller → Supabase realtime → Öğrenci/Admin dinler.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Supabase zaten mevcut, ekstra altyapı yok | Supabase realtime free tier limiti var |
| Next.js'te `@supabase/realtime-js` hazır | Yüksek frekans update'ler DB'yi yorabilir |
| RLS ile güvenlik otomatik | Supabase'e bağımlılık artıyor |
| Konum geçmişi otomatik tabloda | |

---

### Seçenek B: Ayrı WebSocket Sunucusu (Socket.io / ws)

Dedicated WS server → konum broadcast, ETA hesaplama.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Düşük gecikme, yüksek frekans | Ekstra sunucu kurulumu ve deploy |
| Ölçeklenebilir | Auth/session yönetimi ayrıca yapılmalı |
| Supabase'den bağımsız | Deployment karmaşıklığı artar |

---

### Seçenek C: HTTP Polling (Her 15-30 saniye)

Frontend düzenli aralıkla konum sorgular.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| En basit implementasyon | 15-30 sn gecikme — "canlı" hissi yok |
| Altyapı ihtiyacı yok | Çok kullanıcıda sunucu yükü |
| Firewall/proxy sorunları yok | Batarya/bandwidth israfı |

---

## Karar Noktası 8: Konum/Adres Sistemi

> Öğrenci konumları sabit kodlar mı olacak, serbest adres mi girecek?

### Seçenek A: Sabit Lokasyon Kodları (Mevcut) ⭐ ŞİMDİLİK ÖNERİLEN

Sw1-Sw9, So1-So19, D.Kampus — her öğrenci bir koda atanır.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| time_matrix hazır ve doğrulanmış | Yeni bölge eklemek SQL gerektirir |
| Basit, tahmin edilebilir | Öğrenci tam evinden alınamaz |
| Algoritma performansı tutarlı | Gerçek adresten en yakın koda mapping gerekir |

---

### Seçenek B: Serbest Adres + Otomatik En Yakın Kod Eşleme

Öğrenci adresini girer/haritadan seçer. Sistem en yakın Sw/So kodunu bulur.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Kullanıcı dostu, gerçek adres | Geocoding API gerekir |
| Mevcut time_matrix kullanılabilir | "En yakın kod" bazen uzak olabilir |
| Esnek, yeni öğrenci kolayca eklenir | Hatalı adres girişi riski |

---

### Seçenek C: Dinamik Cluster Bölgeleri

Şehir bölgelere ayrılır. Öğrenci adresine göre otomatik bölgeye atanır. Her bölge time_matrix'te bir node.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Ölçeklenebilir: yeni bölge = yeni node | Bölge sınırlarını belirleme zor |
| Dinamik + time_matrix uyumu | Bölge sınırında kalan öğrenciler sorunu |
| Yeni öğrenci otomatik atanır | time_matrix'e yeni satırlar eklenmeli |

---

## Karar Noktası 9: Algoritma Pipeline'ı

> Algoritmalar nasıl konfigüre ve çalıştırılmalı?

### Seçenek A: Mevcut Yapıyı Koru (Registry Pattern) ⭐ ÖNERİLEN

Python `STRATEGY_REGISTRY` + `algorithm-constants.ts` → mevcut pattern iyi çalışıyor.

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Zaten implemente, test edilmiş | Yeni algoritma → 2 dosya değişikliği (Python + TS) |
| Strategy Pattern, genişletilebilir ama sabit | Algoritma config UI'ı minimal |
| Her strateji bağımsız | |

---

### Seçenek B: Plugin Sistemi (Dinamik strateji yükleme)

```python
# optimizer_api/strategies/ altına .py dosyası at → otomatik register
import importlib, pkgutil
for _, name, _ in pkgutil.iter_modules(["strategies"]):
    importlib.import_module(f"strategies.{name}")
```

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Yeni algoritma = 1 dosya, kayıt gerekmez | Debug zorlaşır |
| Hot-reload mümkün olabilir | Python dosya yapısı kuralları sıkılaşır |
| | `algorithm-constants.ts` otomatik güncellenemez |

---

### Seçenek C: Config-Driven (JSON/DB bazlı konfigürasyon)

Algoritma parametreleri Supabase'deki bir tabloda tutulur. Admin UI'dan değiştirilebilir.

```sql
algorithm_configs (algorithm_key, param_name, param_value, param_type)
```

| ✅ Olumlu | ❌ Olumsuz |
|---|---|
| Admin deploy olmadan parametre değiştirebilir | Karmaşık config yönetimi |
| A/B testing kolaylaşır | Type safety zorlaşır |
| | Config validation gerekir |
| | Şu an için overkill |

---

## Özet: Önerilen Seçenekler Tablosu

| # | Karar Noktası | Önerilen | Alternatif |
|---|---|---|---|
| 1 | API Katmanı | **A: İşlev Bazlı Proxy** | B: Gateway (ileride düşünülebilir) |
| 2 | Ölü Kod | **A: Temiz Silme** | B: Deprecation (ekip büyükse) |
| 3 | Time Matrix | **A: Sabit + Encoding Fix** | C: Hybrid (Faz 4'te) |
| 4 | DB Şeması | **A: Minimal JSON** | B: Normalized (Faz 3 sonrası) |
| 5 | Onay/İptal | **C: Hybrid** | A: Otomatik (MVP için) |
| 6 | Sürücü Atama | **A: Manuel** | C: Öneri+Onay (ileride) |
| 7 | Canlı Takip | **A: Supabase Realtime** | C: Polling (MVP için) |
| 8 | Konum Sistemi | **A: Sabit Kodlar** | B: En Yakın Kod Eşleme (Faz 4) |
| 9 | Algoritma Pipeline | **A: Registry Pattern** | C: Config-Driven (ileride) |

---

## Evrimsel Yol Haritası (Seçeneklerin Fazlara Dağılımı)

```
Faz 1 (Şimdi):
  KN1-A: İşlev bazlı proxy düzelt (vehicle-planning → Python)
  KN2-A: Ölü kodu sil
  KN3-A: Encoding fix + sabit matris
  KN9-A: Registry Pattern koru

Faz 2 (1-2 hafta sonra):
  KN4-A: Minimal JSON ile rota kaydı
  KN6-A: Manuel sürücü ataması

Faz 3 (3-4 hafta sonra):
  KN5-C: Hybrid onay/iptal mekanizması
  KN4-B: Gerekirse normalized schema'ya geç

Faz 4 (1-2 ay sonra):
  KN3-C: Hybrid time matrix (isteğe bağlı güncelleme)
  KN7-A: Supabase Realtime ile canlı takip
  KN8-B: En yakın kod eşleme
  KN6-C: Sürücü öneri + onay
```

> [!IMPORTANT]
> Bu doküman bir karar çerçevesidir. Her karar noktasında tercih yapıldıktan sonra `docs/ROADMAP.md` güncellenmelidir.
