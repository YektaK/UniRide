UniRide CVRP Optimizasyon Sistemi

Developer Handover Dokümanı

Versiyon: 3.0.0

Tarih: 24 Mart 2026

Hazırlayan: Z.ai Development Team



İçindekiler

Özet

1.1 Yapılan Değişiklikler

Backend Değişiklikleri (Python)

2.1 Yeni Dosyalar

2.2 Güncellenen Dosyalar

2.3 Local Search Type Seçenekleri

Frontend Değişiklikleri (TypeScript/React)

3.1 Güncellenen Dosyalar

3.2 algorithm-constants.ts Yeni Fonksiyonlar

API Değişiklikleri

4.1 POST /api/v1/optimize

4.2 Algoritma Destek Matrisi

Kurulum ve Dağıtım

5.1 Backend Kurulumu

5.2 Frontend Kurulumu

Test ve Doğrulama

6.1 Backend Testi

6.2 Frontend Testi

Sonraki Adımlar ve Öneriler

İletişim ve Destek

1\. Özet

Bu doküman, UniRide CVRP (Capacitated Vehicle Routing Problem) optimizasyon sisteminde yapılan önemli güncellemeleri belgelemektedir. Güncellemeler, backend (Python) ve frontend (TypeScript/React) katmanlarını kapsamakta olup, sistemin algoritma seçeneklerini genişletmekte ve kod kalitesini artırmaktadır.



1.1 Yapılan Değişiklikler

✅ GWO (Grey Wolf Optimizer) algoritması eklendi

✅ HHO (Harris Hawks Optimization) algoritması eklendi

✅ Two-Opt standalone stratejisi eklendi

✅ Local Search Type parametresi tüm meta-sezgisel algoritmalara eklendi (2-opt, 3-opt, Or-opt, Hybrid)

✅ 2-opt kod tekrarı merkezi local\_search modülüne taşındı

✅ Frontend UI güncellendi: Yerel Arama dropdown'ı eklendi

2\. Backend Değişiklikleri (Python)

2.1 Yeni Dosyalar

Dosya Yolu

Açıklama

optimizer\_api/utils/local\_search.py	Merkezi local search modülü (2-opt, 3-opt, Or-opt, Hybrid)

optimizer\_api/strategies/gwo\_strategy.py	Grey Wolf Optimizer implementasyonu

optimizer\_api/strategies/hho\_strategy.py	Harris Hawks Optimization implementasyonu

optimizer\_api/strategies/two\_opt\_strategy.py	Standalone Two-Opt stratejisi (multi-start desteği)



2.2 Güncellenen Dosyalar

strategies/\_\_init\_\_.py - STRATEGY\_REGISTRY güncellendi, GWO, HHO ve Two-Opt eklendi

strategies/ga\_strategy.py - local\_search\_type parametresi eklendi, merkezi local\_search modülü kullanımı

strategies/pso\_strategy.py - local\_search\_type parametresi eklendi, merkezi local\_search modülü kullanımı

models/schemas.py - LocalSearchType enum eklendi, GWO ve HHO config şemaları

main.py - API v3.0.0, GWO/HHO endpoint'leri, compareAllAlgorithms güncellendi

2.3 Local Search Type Seçenekleri

Değer

Görünen Ad

Açıklama

none	Yok	Yerel arama uygulanmaz

two\_opt	2-Opt (Klasik)	Kenar değiştirme ile iyileştirme, hızlı ve etkili

three\_opt	3-Opt (Yüksek Kalite)	3 kenar değiştirme, daha güçlü iyileştirme

or\_opt	Or-Opt (Kümeleme)	Alt tur yeniden konumlandırma, kümeleme için etkili

hybrid	Hibrit (Kombine)	2-opt + 3-opt + Or-opt kombine, en iyi kalite



3\. Frontend Değişiklikleri (TypeScript/React)

3.1 Güncellenen Dosyalar

Dosya Yolu

Değişiklik

src/lib/algorithm-constants.ts	Two-Opt algoritması, Local Search sabitleri, helper fonksiyonlar

src/services/vehicle-calculator.ts	local\_search\_type parametresi eklendi

src/app/api/calculate-vehicles/route.ts	local\_search\_type parametresi, default genetic\_algorithm

src/app/(app)/admin/route-test/page.tsx	Yerel Arama dropdown'ı eklendi

src/app/(app)/admin/vehicle-planning/page.tsx	Yerel Arama dropdown'ı eklendi



3.2 algorithm-constants.ts Yeni Fonksiyonlar

typescript



// Algoritmanın local search destekleyip desteklemediğini kontrol eder

function algorithmSupportsLocalSearch(algorithm: string): boolean



// Local search type için görünen ad döndürür

function getLocalSearchDisplayName(type: LocalSearchType): string



// UI dropdown için hazır options array

const LOCAL\_SEARCH\_OPTIONS: Array<{key, label, description}>

Yeni Export'lar:



LOCAL\_SEARCH\_KEYS - Local search type sabitleri

LOCAL\_SEARCH\_DISPLAY\_NAMES - Görünen adlar

LOCAL\_SEARCH\_DESCRIPTIONS - Açıklamalar

LocalSearchType - Type tanımı

4\. API Değişiklikleri

4.1 POST /api/v1/optimize

Yeni opsiyonel parametreler:



json



{

&#x20; "algorithm": "gwo | hho | two\_opt | genetic\_algorithm | pso | ...",

&#x20; "local\_search\_type": "none | two\_opt | three\_opt | or\_opt | hybrid",

&#x20; 

&#x20; "gwo\_config": {

&#x20;   "population\_size": 30,

&#x20;   "max\_iterations": 100,

&#x20;   "initial\_a": 2.0,

&#x20;   "exploration\_rate": 0.5,

&#x20;   "local\_search\_type": "two\_opt"

&#x20; },

&#x20; 

&#x20; "hho\_config": {

&#x20;   "population\_size": 30,

&#x20;   "max\_iterations": 100,

&#x20;   "initial\_energy": 1.0,

&#x20;   "jump\_probability": 0.5,

&#x20;   "local\_search\_type": "two\_opt"

&#x20; },

&#x20; 

&#x20; "two\_opt\_config": {

&#x20;   "max\_iterations": 1000,

&#x20;   "multi\_start": true,

&#x20;   "num\_starts": 10

&#x20; }

}

4.2 Algoritma Destek Matrisi

Algoritma

Önerilen

Local Search

Karmaşıklık

Genetik Algoritma (GA)	✓	✓	O(g×p×n²)

PSO	✓	✓	O(i×s×n²)

Gri Kurt (GWO)	✓	✓	O(i×p×n²)

Harris Hawks (HHO)	✓	✓	O(i×h×n²)

Two-Opt Local Search	—	—	O(n²)

Greedy	—	—	O(n²)

Permütasyon TSP	—	—	O(n!)

OR-Tools CVRP	—	—	O(n³)



5\. Kurulum ve Dağıtım

5.1 Backend Kurulumu

optimizer\_api/utils/local\_search.py dosyasını oluşturun

optimizer\_api/strategies/ altına gwo\_strategy.py, hho\_strategy.py, two\_opt\_strategy.py ekleyin

strategies/\_\_init\_\_.py dosyasını güncelleyin

ga\_strategy.py ve pso\_strategy.py dosyalarını güncelleyin

models/schemas.py dosyasını güncelleyin

main.py dosyasını güncelleyin

Python API'yi yeniden başlatın:

bash



uvicorn main:app --reload

5.2 Frontend Kurulumu

src/lib/algorithm-constants.ts dosyasını güncelleyin

src/services/vehicle-calculator.ts dosyasını güncelleyin

src/app/api/calculate-vehicles/route.ts dosyasını güncelleyin

src/app/(app)/admin/route-test/page.tsx dosyasını güncelleyin

src/app/(app)/admin/vehicle-planning/page.tsx dosyasını güncelleyin

Uygulamayı yeniden başlatın:

bash



npm run dev

\# veya

npm run build \&\& npm start

6\. Test ve Doğrulama

6.1 Backend Testi

bash



\# Health check

curl http://localhost:8000/health



\# Mevcut algoritmaları listele

curl http://localhost:8000/api/v1/strategies



\# GWO ile optimizasyon

curl -X POST http://localhost:8000/api/v1/optimize \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{

&#x20;   "algorithm": "gwo",

&#x20;   "students": \[...],

&#x20;   "depot": {...},

&#x20;   "local\_search\_type": "two\_opt"

&#x20; }'



\# HHO ile optimizasyon

curl -X POST http://localhost:8000/api/v1/optimize \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{

&#x20;   "algorithm": "hho",

&#x20;   "students": \[...],

&#x20;   "depot": {...}

&#x20; }'



\# Algoritma karşılaştırma

curl -X POST http://localhost:8000/api/v1/compare \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{

&#x20;   "students": \[...],

&#x20;   "depot": {...},

&#x20;   "algorithms": \["genetic\_algorithm", "pso", "gwo", "hho"]

&#x20; }'

6.2 Frontend Testi

/admin/route-test sayfasına gidin

Algoritma dropdown'ından GWO veya HHO seçin

Yerel Arama dropdown'ından bir seçenek belirleyin

Noktalar seçip "Optimize Et" butonuna tıklayın

Sonuçların doğru döndüğünü doğrulayın

/admin/vehicle-planning sayfasında da aynı testleri yapın

7\. Sonraki Adımlar ve Öneriler

Önerilen İyileştirmeler

Algoritma performans karşılaştırma dashboard'u eklenmesi

Hyperparameter tuning için otomatik optimizasyon

Sonuçların veritabanında saklanması ve geçmiş sorgulama

Real-time optimizasyon ilerleme göstergesi (WebSocket)

Daha fazla local search yöntemi (Lin-Kernighan, etc.)

Bilinen Sorunlar

Permütasyon algoritması 10+ nokta için çok yavaş çalışıyor (UI'da uyarı var)

OR-Tools CVRP ekstra bağımlılık gerektiriyor (google-ortools)

Hybrid local search büyük problemlerde yavaş kalabilir

8\. İletişim ve Destek

Bu dokümantasyon ile ilgili sorularınız için Z.ai Development Team ile iletişime geçebilirsiniz. Teknik detaylar ve kod örnekleri için ilgili dosyalardaki yorum satırlarını inceleyebilirsiniz.



— Doküman Sonu —

