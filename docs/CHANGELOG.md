# 📝 UniRide Değişiklik Günlüğü (Changelog)

> Her anlamlı değişiklik sonrasında bu dosyaya kayıt eklenmeli.  
> Format: `[Tarih] [Geliştirici/AI] — Açıklama`

---

## 2026-03-28

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
