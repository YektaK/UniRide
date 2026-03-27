# 📝 UniRide Değişiklik Günlüğü (Changelog)

> Her anlamlı değişiklik sonrasında bu dosyaya kayıt eklenmeli.  
> Format: `[Tarih] [Geliştirici/AI] — Açıklama`

---

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
