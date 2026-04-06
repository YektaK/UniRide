**UniRide CVRP Optimizasyon Sistemi**

Developer Handover Dokümanı

Algoritma ve Local Search Güncellemeleri

Versiyon 3.0.0

Tarih: 24 Mart 2026

Hazırlayan: Z.ai Development Team

İçindekiler

1\. Özet 1

> 1.1 Yapılan Değişiklikler 1

2\. Backend Değişiklikleri (Python) 2

> 2.1 Yeni Dosyalar 2
>
> 2.2 Güncellenen Dosyalar 2
>
> 2.3 Local Search Type Seçenekleri 3

3\. Frontend Değişiklikleri (TypeScript/React) 4

> 3.1 Güncellenen Dosyalar 4
>
> 3.2 algorithm-constants.ts Yeni Fonksiyonlar 4

4\. API Değişiklikleri 5

> 4.1 POST /api/v1/optimize 5
>
> 4.2 Algoritma Destek Matrisi 5

5\. Kurulum ve Dağıtım 6

> 5.1 Backend Kurulumu 6
>
> 5.2 Frontend Kurulumu 6

6\. Test ve Doğrulama 7

> 6.1 Backend Testi 7
>
> 6.2 Frontend Testi 7

7\. Sonraki Adımlar ve Öneriler 8

> 7.1 Önerilen İyileştirmeler 8
>
> 7.2 Bilinen Sorunlar 8

8\. İletişim ve Destek 8

Not: İçindekiler alan kodları ile oluşturulmuştur. Sayfa numaralarını
güncellemek için sağ tıklayıp \"Alanı Güncelle\" seçeneğini kullanın.

1\. Özet

Bu doküman, UniRide CVRP (Capacitated Vehicle Routing Problem)
optimizasyon sisteminde yapılan önemli güncellemeleri belgelemektedir.
Güncellemeler, backend (Python) ve frontend (TypeScript/React)
katmanlarını kapsamakta olup, sistemin algoritma seçeneklerini
genişletmekte ve kod kalitesini artırmaktadır.

1.1 Yapılan Değişiklikler

-   GWO (Grey Wolf Optimizer) algoritması eklendi

-   HHO (Harris Hawks Optimization) algoritması eklendi

-   Two-Opt standalone stratejisi eklendi

-   Local Search Type parametresi tüm meta-sezgisel algoritmalara
    eklendi (2-opt, 3-opt, Or-opt, Hybrid)

-   2-opt kod tekrarı merkezi local_search modülüne taşındı

-   Frontend UI güncellendi: Yerel Arama dropdown\'ı eklendi

2\. Backend Değişiklikleri (Python)

2.1 Yeni Dosyalar

  -----------------------------------------------------------------------------
  **Dosya Yolu**                   **Açıklama**
  -------------------------------- --------------------------------------------
  utils/local_search.py            Merkezi local search modülü (2-opt, 3-opt,
                                   Or-opt, Hybrid)

  strategies/gwo_strategy.py       Grey Wolf Optimizer implementasyonu

  strategies/hho_strategy.py       Harris Hawks Optimization implementasyonu

  strategies/two_opt_strategy.py   Standalone Two-Opt stratejisi (multi-start
                                   desteği)
  -----------------------------------------------------------------------------

2.2 Güncellenen Dosyalar

1.  strategies/\_\_init\_\_.py - STRATEGY_REGISTRY güncellendi, GWO, HHO
    ve Two-Opt eklendi

2.  strategies/ga_strategy.py - local_search_type parametresi eklendi,
    merkezi local_search modülü kullanımı

3.  strategies/pso_strategy.py - local_search_type parametresi eklendi,
    merkezi local_search modülü kullanımı

4.  models/schemas.py - LocalSearchType enum eklendi, GWO ve HHO config
    şemaları

5.  main.py - API v3.0.0, GWO/HHO endpoint\'leri, compareAllAlgorithms
    güncellendi

2.3 Local Search Type Seçenekleri

  ------------------------------------------------------------------------
  **Değer**       **Görünen Ad**             **Açıklama**
  --------------- -------------------------- -----------------------------
  none            Yok                        Yerel arama uygulanmaz

  two_opt         2-Opt (Klasik)             Kenar değiştirme ile
                                             iyileştirme

  three_opt       3-Opt (Yüksek Kalite)      3 kenar değiştirme, daha
                                             kaliteli

  or_opt          Or-Opt (Kümeleme)          Alt tur yeniden konumlandırma

  hybrid          Hibrit (Kombine)           2-opt + 3-opt + Or-opt
                                             kombine
  ------------------------------------------------------------------------

3\. Frontend Değişiklikleri (TypeScript/React)

3.1 Güncellenen Dosyalar

  ------------------------------------------------------------------------------------
  **Dosya Yolu**                                  **Değişiklik**
  ----------------------------------------------- ------------------------------------
  src/lib/algorithm-constants.ts                  Two-Opt algoritması, Local Search
                                                  sabitleri, helper fonksiyonlar

  src/services/vehicle-calculator.ts              local_search_type parametresi
                                                  eklendi

  src/app/api/calculate-vehicles/route.ts         local_search_type parametresi,
                                                  default genetic_algorithm

  src/app/(app)/admin/route-test/page.tsx         Yerel Arama dropdown\'ı eklendi

  src/app/(app)/admin/vehicle-planning/page.tsx   Yerel Arama dropdown\'ı eklendi
  ------------------------------------------------------------------------------------

3.2 algorithm-constants.ts Yeni Fonksiyonlar

1.  algorithmSupportsLocalSearch(algorithm) - Algoritmanın local search
    destekleyip desteklemediğini kontrol eder

2.  getLocalSearchDisplayName(type) - Local search type için görünen ad
    döndürür

3.  LOCAL_SEARCH_OPTIONS - UI dropdown için hazır options array

4\. API Değişiklikleri

4.1 POST /api/v1/optimize

Yeni opsiyonel parametreler:

1.  local_search_type: \"none\" \| \"two_opt\" \| \"three_opt\" \|
    \"or_opt\" \| \"hybrid\"

2.  gwo_config: { population_size, max_iterations, initial_a,
    exploration_rate, local_search_type }

3.  hho_config: { population_size, max_iterations, initial_energy,
    jump_probability, local_search_type }

4.  two_opt_config: { max_iterations, multi_start, num_starts }

4.2 Algoritma Destek Matrisi

  ---------------------------------------------------------------------------
  **Algoritma**          **Önerilen**    **Local Search**   **Karmaşıklık**
  ---------------------- --------------- ------------------ -----------------
  Genetik Algoritma (GA) ✓               ✓                  O(g×p×n²)

  PSO                    ✓               ✓                  O(i×s×n²)

  Gri Kurt (GWO)         ✓               ✓                  O(i×p×n²)

  Harris Hawks (HHO)     ✓               ✓                  O(i×h×n²)

  Two-Opt Local Search   ---             ---                O(n²)

  Greedy                 ---             ---                O(n²)
  ---------------------------------------------------------------------------

5\. Kurulum ve Dağıtım

5.1 Backend Kurulumu

1.  optimizer_api/utils/local_search.py dosyasını oluşturun

2.  optimizer_api/strategies/ altına gwo_strategy.py, hho_strategy.py,
    two_opt_strategy.py ekleyin

3.  strategies/\_\_init\_\_.py dosyasını güncelleyin

4.  ga_strategy.py ve pso_strategy.py dosyalarını güncelleyin

5.  models/schemas.py dosyasını güncelleyin

6.  main.py dosyasını güncelleyin

7.  Python API\'yi yeniden başlatın: uvicorn main:app \--reload

5.2 Frontend Kurulumu

-   src/lib/algorithm-constants.ts dosyasını güncelleyin

-   src/services/vehicle-calculator.ts dosyasını güncelleyin

-   src/app/api/calculate-vehicles/route.ts dosyasını güncelleyin

-   src/app/(app)/admin/route-test/page.tsx dosyasını güncelleyin

-   src/app/(app)/admin/vehicle-planning/page.tsx dosyasını güncelleyin

-   npm run dev veya npm run build çalıştırın

6\. Test ve Doğrulama

6.1 Backend Testi

Python API\'yi test etmek için:

\# Health check curl http://localhost:8000/health \# GWO ile
optimizasyon curl -X POST http://localhost:8000/api/v1/optimize \\ -H
\"Content-Type: application/json\" \\ -d \'{\"algorithm\": \"gwo\",
\"students\": \[\...\], \"depot\": {\...}}\' \# Algoritma karşılaştırma
curl -X POST http://localhost:8000/api/v1/compare \\ -H \"Content-Type:
application/json\" \\ -d \'{\"students\": \[\...\], \"depot\": {\...}}\'

6.2 Frontend Testi

-   /admin/route-test sayfasına gidin

-   Algoritma dropdown\'ından GWO veya HHO seçin

-   Yerel Arama dropdown\'ından bir seçenek belirleyin

-   Noktalar seçip \"Optimize Et\" butonuna tıklayın

-   Sonuçların doğru döndüğünü doğrulayın

7\. Sonraki Adımlar ve Öneriler

7.1 Önerilen İyileştirmeler

-   Algoritma performans karşılaştırma dashboard\'u eklenmesi

-   Hyperparameter tuning için otomatik optimizasyon

-   Sonuçların veritabanında saklanması ve geçmiş sorgulama

-   Real-time optimizasyon ilerleme göstergesi (WebSocket)

7.2 Bilinen Sorunlar

-   Permütasyon algoritması 10+ nokta için çok yavaş çalışıyor (UI\'da
    uyarı var)

-   OR-Tools CVRP ekstra bağımlılık gerektiriyor (google-ortools)

8\. İletişim ve Destek

Bu dokümantasyon ile ilgili sorularınız için Z.ai Development Team ile
iletişime geçebilirsiniz. Teknik detaylar ve kod örnekleri için ilgili
dosyalardaki yorum satırlarını inceleyebilirsiniz.

--- Doküman Sonu ---
