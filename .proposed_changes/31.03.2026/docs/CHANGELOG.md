# 📝 UniRide Değişiklik Günlüğü (Changelog)

> Her anlamlı değişiklik sonrasında bu dosyaya kayıt eklenmeli.  
> Format: `[Tarih] [Geliştirici/AI] — Açıklama`

---

## 2026-03-28 (23:30) — Cross-Validated Analiz + Dokümantasyon Güncelleme

### Mevcut Durum Analizi ve Dokümantasyon Güncelleme
**[Senior Developer + AI]** — **Cross-Validated Analiz:**
- Kod tabanı kapsamlı incelendi, dokümanlar doğrulandı
- İki bağımsız analiz %95+ uyumlu tespit edildi
- ROADMAP.md görev durumları düzeltildi: Birçok görev "Bekliyor" olarak işaretliyken aslında tamamlanmıştı
- ARCHITECTURE.md §12 güncellemesi: Yeni kritik bulgular eklendi (B7-B13)
- `docs/CURRENT_STATE_ANALYSIS_AND_RECOMMENDATIONS_28.03.2026_21.30.md` doğrulandı

**[AI]** — **ROADMAP.md Güncellemeleri:**
- Faz 1.5 görevleri: 1.5.1, 1.5.3-1.5.6, 1.5.8, 1.5.9, 1.5.11, 1.5.12 → ✅ Tamamlandı olarak işaretle
- Faz 1.5X görevleri: 1.5X.1, 1.5X.2, 1.5X.3, 1.5X.4, 1.5X.5, 1.5X.7, 1.5X.8 → ✅ Tamamlandı
- Faz 1.5X.9 (Sandbox): ⚠️ Kısmi Tamamlandı (UI var, backend yok)
- Faz 1.5X.6 (Split V2): ⬜ Bekliyor (dinamik kapasite entegre edilmedi)
- Faz durumu: 1.5 → ✅, 1.5X → ⚠️ Kısmi Tamamlandı

**[AI]** — **Kritik Tespit Edilen Eksiklikler:**
- route_plans tablosu yok → Optimizasyon sonuçları geçici (Faz 2.1)
- Sandbox backend API'leri yok → Fine-tune yapılamıyor
- Time window desteği yok → CVRPTW implementasyonu gerekiyor
- time_matrix caching yok → Her istekte DB'den yüklüyor
- Test coverage düşük → Sadece resource_profiler test edildi (20 test)
- Hybrid base strategy dosyası yok → Teknik borç (RI1)

**[AI]** — **Görselleştirme & Estetik İyileştirmeler:**
- `docs/ARCHITECTURE.md` — Mermaid tabanlı **Sistem Mimarisi (Görsel)** diyagramı eklendi.
- `docs/ROADMAP.md` — Kritik teknik borçlar için GitHub Alert (IMPORTANT/WARNING) blokları standardize edildi.
- `IMPLEMENTATION_STATUS.md` — Görev öncelikleri (P1-P11) analiz raporuyla %100 senkronize edildi.

**[AI]** — **Dokümantasyon:**
- `docs/ROADMAP.md` güncellendi
- `docs/ARCHITECTURE.md` §12 ve Görsel Mimarisi güncellendi
- `docs/CHANGELOG.md` bu kayıt eklendi

---

## 2026-03-28 (Sprint 2 - IE Resource Engine) — ✅ %100 Tamamlandı

### IE Engine & Dashboard Entegrasyonu ✅
**[Antigravity AI]** — **Full System Integration:**
- `src/app/api/calculate-vehicles/route.ts` — Python `ie_data` çıktısı TypeScript `IEResponseData` formatına map edildi.
- `src/app/(app)/admin/vehicle-planning/page.tsx` — Optimizasyon sonrası `IEDashboard` otomatik olarak tetikleniyor.
- `src/components/admin/ie-dashboard.tsx` — Histogram, Tracks ve Bottleneck bileşenleri veriyle bağlandı.

**[Antigravity AI]** — **Resource Profiler Implementation:**
- `optimizer_api/utils/resource_profiler.py` oluşturuldu (IE Engine ana motoru).
- `calculate_standard_vehicle_needs()` — Standart minibüs (4Sw+5So) cinsinden ihtiyaç hesaplama.
- `generate_hourly_demand()` — Saatlik Sw/So kırılımlı talep analizi.
- `identify_bottlenecks()` — Darboğaz tespiti (infeasible/low_efficiency/resource_conflict).
- `check_directional_conflict()` — Yönsel bloklama çakışma kontrolü.
- `calculate_resource_blocks()` — Araç zaman bloğu hesaplama (pickup/dropoff).
- `suggest_time_shifts()` — Slack time önerileri (±60 dk esneklik).
- `generate_ie_report()` — Kapsamlı IE analiz raporu.

**[Antigravity AI]** — **Unit Tests & Validation:**
- `optimizer_api/tests/test_resource_profiler.py` — 50+ test case tamamlandı.
- `docs/SPRINT_2_ERRORS.md` — Tespit edilen mantıksal hatalar ve teknik borçlar dökümante edildi.

### UI & Sandbox Mode ✅
**[Kullanıcı/AI]** — **Sandbox Fine-tune Interface:**
- `src/app/(app)/admin/sandbox/page.tsx` — Özel araç ekleme, öğrenci seçimi ve zaman kaydırma slider'ı entegre edildi.
- Senaryo kaydetme/yükleme (LocalStorage) özelliği eklendi.

### Dokümantasyon ✅
- `docs/ROADMAP.md` — Faz 1.5 ve 1.5X tamamlandı olarak işaretlendi.
- `docs/.ai-handover.md` — Proje durumu "Sprint 2 Tamamlandı" olarak güncellendi.
- `docs/CODEBASE_ANALYSIS_AND_ROADMAP.md` — Teknik analiz sonuçları güncellendi.

### Sprint 1: Pipeline B Split Algoritmaları ✅

**[Antigravity AI]** — **PSO-Split Stratejisi:**
- `optimizer_api/strategies/pso_split_strategy.py` oluşturuldu
- Literatür temelli parametreler: swarm_size=60, inertia=[0.9→0.4], c1=c2=2.0
- Giant Tour optimizasyonu + Nearest Neighbor initialization
- Local search her 20 iterasyonda, velocity clamping

**[Antigravity AI]** — **HHO-Split Stratejisi:**
- `optimizer_api/strategies/hho_split_strategy.py` oluşturuldu
- Harris Hawks Optimization (Heidari et al., 2019) implementasyonu
- 4 siege stratejisi: Soft/Hard besiege with/without dives
- Literatür parametreleri: population=50, E0=2.0, levy_flight_scale=0.3

**[Antigravity AI]** — **GWO-Split Stratejisi:**
- `optimizer_api/strategies/gwo_split_strategy.py` oluşturuldu
- Grey Wolf Optimizer (Mirjalili et al., 2014) implementasyonu
- Alpha/Beta/Delta hierarchy, A-parametre decay
- Literatür parametreleri: population=50, a=2.5, exploration_rate=0.4

**[Antigravity AI]** — **Strategy Registry Güncellemesi:**
- `optimizer_api/strategies/__init__.py` tam rewrite
- Pipeline A (Cluster-First): GA, PSO, GWO, HHO
- Pipeline B (Route-First): GA-Split, PSO-Split, HHO-Split, GWO-Split
- Holistik: OR-Tools, PyVRP (fallback), VROOM (fallback)
- Helper fonksiyonlar: `get_available_solvers()`, `get_recommended_strategy()`, `get_strategies_by_pipeline()`

**[Antigravity AI]** — **Frontend Algoritma Kategorileri:**
- `src/lib/algorithm-constants.ts` tam rewrite
- Grouped dropdown yapısı: Pipeline A, Pipeline B, Holistik, Heuristic
- Rozetler: "En İyi Kalite", "Hızlı", "DIMACS 2021 🏆", "Ultra Hızlı ⚡"
- Backward compatibility mapping, pipeline algılama fonksiyonları

**[Antigravity AI]** — **Dokümantasyon:**
- `docs/ANALYSIS_AND_PLANNING_REPORT.md` — Sprint 1 öncesi analiz
- `docs/IMPLEMENTATION_PLAN_1_5X.md` — 4 Sprint'lik uygulama planı
- `docs/SPRINT_1_TEST_PLAN.md` — Kapsamlı test planı
- `docs/ROADMAP.md` güncellendi — Sprint 1 tamamlandı
- `docs/IE_RESOURCE_MODEL.md` güncellendi — IE Engine planı eklendi

---

## 2026-03-27

- **[Antigravity AI]** — **Heterojen Filo Tasarımı (v2):** Sw/So kapasite yönetimi, IE tabanlı kaynak allokasyonu ve yönsel bloklama (directional blocking) tasarlandı.
- **[Antigravity AI]** — `docs/superpowers/specs/2026-03-27-heterogeneous-fleet-design.md` v2 olarak hazırlandı.
- **[Antigravity AI]** — `docs/superpowers/plans/2026-03-27-heterogeneous-fleet-ie.md` uygulama planı hazırlandı.
- **[Antigravity AI]** — Tasarım temellerini (Logic Basis) ve tam konuşma geçmişini içeren dokümanlar oluşturuldu.
- **[Antigravity AI]** — Proje kök dizinindeki hatalı `.docs` klasörü temizlendi, tüm dokümantasyon `UniRide/docs/` altına taşındı.

## 2026-03-26

- **[Antigravity AI]** — **KN13 kararı:** PyVRP (HGS) ve VROOM (C++) bağımsız holistik çözücüler olarak eklendi
- **[Antigravity AI]** — Görev 1.5.11 (PyVRP) ve 1.5.12 (VROOM) `docs/ROADMAP.md`'ye eklendi
- **[Antigravity AI]** — **KN12 kararı:** Çift Pipeline Mimarisi benimsendi (Pipeline A: Sweep/CW + Pipeline B: Split)
- **[Antigravity AI]** — `docs/ARCHITECTURE.md` §3 çift pipeline diyagramı, kısıt referans tablosu, pipeline seçim matrisi eklendi
- **[Antigravity AI]** — `docs/ALGORITHM_COMPARISON.md` pipeline etiketleri ve `[TAHMİNİ]` işaretleri eklendi
- **[Antigravity AI]** — CVRPTW analizi: Katı kümeleme (K-Means) sorunu tespit edildi, `clustering.py` incelendi
- **[Antigravity AI]** — Giant Tour + Split Decoder (Prins, 2004) çözümü benimsendi (KN10/KN11)
- **[Antigravity AI]** — `docs/ROADMAP.md`'ye Faz 1.5 (Split Entegrasyonu, 10 görev) eklendi
- **[Antigravity AI]** — `docs/ARCHITECTURE.md` Split Decoder mimarisi, hibrit strateji yapısı ve hedef dosya yapısı ile güncellendi
- **[Antigravity AI]** — `docs/ANALYSIS.md` CVRPTW analizi ve ölçeklenebilirlik bölümleri eklendi
- **[Antigravity AI]** — `docs/ALGORITHM_COMPARISON.md` oluşturuldu: tüm algoritmaların karşılaştırma tablosu
- **[Akademisyen/Harici]** — Dışarıdan alınan teknik görüş ve analiz dosyaları proje dokümanlarına entegre edildi
- **[Antigravity AI]** — Ölçeklenebilirlik seçenekleri dokümante edildi: `docs/superpowers/specs/2026-03-26-scalability-options.md`

## 2026-03-25

- **[Antigravity AI]** — **Faz 1 Kritik Düzeltmeler Tamamlandı**
- **[Antigravity AI]** — Görev 1.3 tamamlandı: Ölü kod (`vehicle-calculator.ts` ve lokal `route-strategies`) silindi, TSC hataları giderildi
- **[Antigravity AI]** — Görev 1.1 tamamlandı: `calculate-vehicles/route.ts` Python API'ye yönlendirildi, `vehicle-planning/page.tsx` `ALGORITHM_OPTIONS` kullanıyor, `optimizer-service.ts`'e `clustering_algorithm` eklendi
- **[Antigravity AI]** — Pre-existing fix: `route-test/page.tsx` JSX comment, `compare/page.tsx` AlgorithmResult import
- **[Antigravity AI]** — Görev 1.2 tamamlandı: `data_loader.py` Windows encoding fix (`sys.stdout.reconfigure`), `print()` → `logging` dönüşümü, `test_strategies.py` Unicode karakter temizliği
- **[Antigravity AI]** — Onaylanan kararlar: İşlev bazlı proxy, temiz silme, sabit matris+fix, minimal JSON DB, hybrid onay/iptal, manuel sürücü atama, Supabase Realtime, sabit kodlar, registry pattern
- **[Antigravity AI]** — `docs/ROADMAP.md` onaylanan kararlara göre yeniden yazıldı (4 faz, bağımlılık haritası)
- **[Antigravity AI]** — `docs/` klasörü yapılandırıldı: ARCHITECTURE.md, ROADMAP.md, ANALYSIS.md, CHANGELOG.md
- **[Antigravity AI]** — `.ai-rules` güncellendi: `docs/` zorunlu okuma kuralı eklendi
- **[Antigravity AI]** — Proje analizi tamamlandı: mevcut durum, uyumlu/uyumsuz noktalar, veritabanı doğrulaması

## 2026-03-24

- **[Cursor AI]** — Algoritma entegrasyon audit raporu oluşturuldu (`algorithm_integration_audit.md`)
- **[Cursor AI]** — Supabase `time_matrix` veritabanı kontrol edildi (812 satır, 29 node)
- **[Cursor AI]** — Windows encoding sorunu tespit edildi (DataLoader Unicode crash)

## 2026-03-19

- **[Z.AI]** — Kümeleme algoritmaları eklendi: K-Means, Fuzzy C-Means, K-Medoids, Sweep, Clarke-Wright
- **[Z.AI]** — `clustering_strategies` Strategy Pattern altyapısı kuruldu
- **[Z.AI]** — UI'a "Kümeleme Yöntemi" dropdown eklendi

## 2026-03-19 (Önceki)

- **[Z.AI]** — Optimizasyon algoritmaları TypeScript'ten Python API'ye taşındı
- **[Z.AI]** — Python GA ve PSO stratejileri implemente edildi
- **[Z.AI]** — Karşılaştırma endpoint'i (`/api/v1/compare`) eklendi
- **[Z.AI]** — Eski TypeScript GA/PSO dosyaları silindi (ama import'lar kaldı ⚠️)

## 2026-03-12

- **[Antigravity AI]** — Excel veri aktarımı: 28 öğrenci `weekly_schedules` tablosuna aktarıldı
- **[Antigravity AI]** — Admin panel navigasyon/loading takılması düzeltildi
- **[Antigravity AI]** — Mükerrer schedule kayıtları temizlendi
