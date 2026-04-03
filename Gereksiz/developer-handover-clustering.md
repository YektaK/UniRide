# Gelişmiş Kümeleme (Advanced Clustering) Yazılımcı Devir Notları

Bu belge, UniRide Araç Planlama sistemine eklenen çoklu kümeleme (clustering) algoritmalarının mimarisini ve kod tabanına nasıl entegre edildiğini diğer yazılımcılara açıklamak amacıyla yazılmıştır.

## Mimari Değişim (Strategy Pattern)

Eski sistemde `VehicleCalculator` sadece K-Means üzerinden basit bir kümeleme yapıyordu. Yeni yapıda ise "Strategy Pattern" uygulanarak kümeleme mantığı tamamen ayrıştırıldı.
İlgili paket dizini: `optimizer_api/utils/clustering_strategies/`

Bu dizinde şunlar yer alır:
- `base.py`: Diğer tüm algoritmaların miras aldığı soyut sınıf (`BaseClusteringStrategy`). Kapasite aşımında kümeleri otomatik bölen `_split_cluster` gibi utility fonksiyonlarını içerir.
- `__init__.py`: Factory fonksiyonu olan `get_clustering_strategy(name)`'i barındırır. Yeni bir kümeleme yöntemi eklendiğinde buradan dışa aktarılır (register edilir).

### Mevcut Kümeleme Yöntemleri
1. **K-Means (`kmeans.py`)**: Geleneksel coğrafi enlem/boylam kümelemesi (eski kodun modernize edilmiş hali).
2. **Fuzzy C-Means (`fuzzy_cmeans.py`)**: Yumuşak (soft) kümeleme. Üyelik derecelerine (membership matrix) bakarak en muhtemel kümeye atama yapar.
3. **K-Medoids (`k_medoids.py`)**: Coğrafi uzaklık yerine **Time Matrix** (Seyahat Süresi Matrisi) bazlı çalışan PAM (Partitioning Around Medoids) varyasyonudur. Trafik veya yol yapısına dayalı gerçek sürelere göre optimum kümeler bulur. Hata payını en aza indirmek için K-Medoids kullanılması önerilir.
4. **Sweep Algoritması (`sweep.py`)**: Depoyu (Kampüs) merkez kabul edip açısal (polar) dolaşım mantığıyla dilimleme (Sweep-line) yapar. Çok hızlı çalışır.
5. **Clarke-Wright Savings (`clarke_wright.py`)**: Rotalama algoritması olan CVRP (Savings) algoritmasının sadece gruplama/kümeleme yapacak şekilde uyarlanmış halidir. Mesafe tasarruflarına (savings) göre hiyerarşik birleştirme yapar.

## Python Backend Entegrasyonu

- `optimizer_api/utils/clustering.py` dosyasındaki `VehicleCalculator.cluster_students` metodu artık sadece bir Proxy (Elçi) görevi görmektedir. Hangi algoritmanın çalışacağını payload'dan `self.clustering_algorithm` değerine bakarak seçer.
- Optimizasyon Stratejileri (`ga_strategy.py`, `pso_strategy.py` ve `permutation_tsp.py`), ilgili algoritmaya özgü payload ile birlikte tetiklenirken `VehicleCalculator(..., clustering_algorithm=request.clustering_algorithm)` şeklinde uyarılır.

## Next.js (TypeScript) Frontend Entegrasyonu

- `OptimizationOptions`, `/api/calculate-vehicles/route.ts`, vs. tüm request yapılarına `clustering_algorithm` key parametresi eklendi.
- **`VehiclePlanningPage`** (`admin/vehicle-planning/page.tsx`) içerisindeki parametreler kutusunda `Kümeleme Yöntemi` dropdown eklendi.
- **`AlgorithmComparisonPage`** (`admin/compare/page.tsx`) içerisine algoritmaları yarıştırdığımız kısımda veri setine uygulanacak temel kümeleme yöntemini de yine dropdown'dan seçebilme özelliği eklendi.
- Hangi test çağrısını yaparsanız yapın, frontend seçilen dropdown değerini python'a serialize dip `algorithm` yanında `clustering_algorithm` bağımsız parametresiyle iletekcektir.

## Eklerken Nelere Dikkat Edilmeli?
Yeni bir kümeleme yöntemi geliştirmek sterseniz:
1. `clustering_strategies` klasöründe yeni bir `.py` dosyası oluşturup `BaseClusteringStrategy`'den inherit edin.
2. Sınıf içerisinde `cluster()` metodunu override edin ve çıktı olarak `List[List[Point]]` dönün.
3. `clustering_strategies/__init__.py` içerisindeki factory lüle kaydını ekleyin.
4. UI tarafındaki `strategies` lüle ismini (`name`) karşılık gelen bir seçenek olarak (`page.tsx`) dosyalarına tanımlayın.

*Hazırlayan: Antigravity AI*
