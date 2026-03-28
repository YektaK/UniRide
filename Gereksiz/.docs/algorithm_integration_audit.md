# UniRide - Rota Optimizasyonu Algorithm Entegrasyon Audit Raporu

Tarih: 2026-03-23  
Hedef: UI tarafında seçilen `nearest-neighbor / permutation / two-opt / genetic_algorithm / pso` algoritma anahtarlarının **hem Next.js üzerinden Python optimizer’a doğru taşınması** hem de Python tarafında ilgili algoritmaların **gerçekten çalıştırılması**. Ayrıca `time_matrix` verisinin Supabase’ten yüklenip yüklenmediğinin doğrulanması.

---

## 1) Mevcut (hedeflenen) uçtan uca akış

### 1.1 Kullanıcı/Server tarafında veri akışı (yüksek seviye)
- Öğrenci schedule’ları ve/veya admin tarafından yapılan planlama üzerinden sistem “pickup/dropoff” taleplerini üretir.
- Admin geceleri (önceki gün) planlama/rota üretir.
- Admin araç kısıtlarını (Sw tekerlekli sandalye kapasitesi, So diğer engel kapasitesi) ve `max_travel_time` (örn. 120/180 dk) limitini vererek rotaları oluşturur.
- Seçilen algoritma ile (UI’den) çözüm üretilir.

### 1.2 Uygulamanın şu an kullandığı katmanlar
- Next.js (UI & API route’lar)
- Python FastAPI microservice (`optimizer_api`)
- Supabase (time matrix ve kullanıcı/durum verileri)

---

## 2) Algoritma anahtarı kopukluğu (UI -> Next.js -> Python)

### 2.1 UI’de seçilen strategy key’ler
`src/app/(app)/admin/vehicle-planning/page.tsx`
- `nearest-neighbor`
- `permutation`
- `two-opt`
- `genetic_algorithm`
- `pso`

### 2.2 Next.js `calculate-vehicles` endpoint’inin Python’a gönderdiği payload
`src/app/api/calculate-vehicles/route.ts`
- Request’te gelen `strategy` değeri python `algorithm` alanına mapleniyor:
  - `strategy === "two-opt"` ise `algorithm = "genetic_algorithm"`
  - aksi halde `algorithm = strategy`

### 2.3 Python strategy registry’de var olan anahtarlar
`optimizer_api/strategies/__init__.py`:
- `"genetic_algorithm"`
- `"pso"`
- `"greedy"`
- `"nearest_neighbor"` (alias)
- `"permutation_tsp"`
- `"ortools_cvrp"`

### 2.4 Sonuç: UI anahtarları Python anahtarlarıyla birebir uyuşmuyor
- UI `"nearest-neighbor"` -> Python’da `"nearest_neighbor"` var (dash vs underscore farkı kopukluk)
- UI `"permutation"` -> Python’da `"permutation_tsp"` var (kapsam kopuk)
- UI `"two-opt"` -> Python’da yok; ayrıca “two-opt” seçilince GA’ya zorla dönüştürülüyor (yanlış temsil)
- UI `"genetic_algorithm"`, `"pso"` büyük oranda uyuşuyor

**Olası etki:**
- Yanlış `algorithm` key gönderilince FastAPI `unknown algorithm` hatası oluşabilir.
- Ya da key eşleşse bile UI “two-opt” beklerken Python “GA” çalıştırır (yanlış davranış).

---

## 3) Time matrix (Supabase) kullanımı kritik sorunu

### 3.1 Python DataLoader davranışı
`optimizer_api/utils/data_loader.py`
- Supabase credential / yükleme başarısızsa:
  - `self._use_coordinates = True`
  - `time_matrix = None`
- `get_submatrix()` çağrıldığında:
  - Eğer `self._use_coordinates` == True veya `self.time_matrix is None` ise:
    - gerçek değer yerine **sıfır matrix** döndürülüyor (`[[0.0]*n ...]`)

### 3.2 Solver’ların süre/fitness hesaplarının sonucu
GA/PSO/Greedy/Permutation/ORTools hepsi `time_matrix` dict/list üzerinden süreyi alır.
- `_get_duration()` fonksiyonu:
  - `time_matrix` içinde değer varsa onu döndürür
  - Supabase yüklenmediyse `time_matrix` var gibi görünüp içi 0 olabilir

**Olası etki:**
- Fitness fonksiyonu (GA) 0 süre üzerinden bozulur.
- `max_travel_time` kısıtı fiilen anlamsızlaşır (her şey 0 olduğu için her rota “uyuyor” gibi olur).
- “Algoritmalar doğru çalışıyor mu?” teyidi pratikte imkansızlaşır.

---

## 4) Clustering tarafında road-time matrix kullanım garantisi zayıf

### 4.1 K-Means ve diğer clustering stratejileri
`optimizer_api/utils/clustering_strategies/*`
- K-Means: haversine (coğrafi lat/lng) kullanır.
- K-Medoids / Clarke-Wright: `time_matrix` beklense de:

### 4.2 VehicleCalculator tarafından kwargs aktarımı sorunu
`optimizer_api/utils/clustering.py`
- `VehicleCalculator.calculate()` içinde `cluster_students(points, num_vehicles)` çağrısı yapılıyor.
- `time_matrix` kwargs olarak çoğunlukla üretilip geçirilmiyor.
- Bu da time-matrix vaat eden clustering’lerin haversine/tahmine düşmesine veya eksik matrise rağmen çalışmasına yol açabilir.

---

## 5) “Algoritmalar doğru çalışıyor mu?” doğrulaması için gerekli kontroller

### 5.1 Supabase SQL kontrolleri (time_matrix)
Supabase SQL Editor’da şunlar yapılmalı:

1) Satır sayısı:
```sql
select count(*) from time_matrix;
```

2) origin_code bazında kapsama:
```sql
select origin_code, count(*) as cnt
from time_matrix
group by origin_code
order by cnt desc;
```

3) örnek bir edge var mı:
```sql
select *
from time_matrix
where origin_code='D.Kampus'
  and destination_code='Sw1'
limit 1;
```

4) Kolon adları doğrulaması:
DataLoader şu kolonları bekliyor:
- `origin_code`
- `destination_code`
- `duration_minutes`

Bu kolon adları Supabase şemasında birebir aynı olmalı.

### 5.2 Python tarafında time_matrix gerçekten yüklendi mi?
En güvenilir yöntem:
- Python server loglarında `DataLoader` yükleme mesajını görmek.
- Mesaj görünmüyorsa veya “fallback” logları dönüyorsa time_matrix verisi kullanılmıyor demektir.

---

## 6) “UI anahtarları ile Python’da aynı algoritmalar” hedefini gerçeğe çevirmek için gereken değişiklikler

1) UI strategy key’lerini canonical hale getir
- Python registry anahtarlarına birebir map:
  - `nearest-neighbor` -> `nearest_neighbor`
  - `permutation` -> `permutation_tsp`
  - `two-opt` -> (ya gerçek `two_opt` strategy ekle ya da UI label’ını GA/başka solver ile eşleştir)

2) Python tarafına `two-opt` strategy eklemek (önerilen)
- Şu an Python registry’de `two-opt` yok.
- En doğrusu, `two-opt` için bir strategy sınıfı yazıp `STRATEGY_REGISTRY`’ye eklemek.

3) Çoklu araç / time-slot rotalama tarafında payload uyumluluğunu düzeltmek
- `src/services/doubus/multi-vehicle-routing.ts` içindeki Python payload alanları Python `StudentNode` ile birebir uyumlu olmalı:
  - Python: `location_code`, `disability_type` bekler
  - TS: şu an `{id: locationCode, type: ...}` gönderebiliyor

4) Clustering time_matrix kwargs’larını garanti etmek
- K-Medoids / Clarke-Wright için `time_matrix` üretimi ve kwargs aktarımı “kesin” olmalı.

---

## 7) Net sonraki adım için sorular

1) Algoritma “kaynak of truth” hangisi olacak?
   - (a) Admin `vehicle-planning` ekranından üretilen rotalar mı
   - (b) Zaman slotu rotalama (DouBus) katmanı mı

2) Supabase `time_matrix` kolon adları kesin olarak şunlar mı?
   - `origin_code`, `destination_code`, `duration_minutes`

3) `time_matrix` tablo içeriğinin boyutu beklediğin gibi mi?
   - Node set beklentin: `D.Kampus` + `Sw1-9` + `So1-19` = 30 node mu?
   - Yoksa `time_matrix` sadece bir alt set mi içeriyor?

Yukarıdaki SQL kontrollerinin çıktısını paylaşırsan; bir sonraki adımda hem “time_matrix gerçekten yükleniyor mu” hem de “UI’den seçilen algoritma gerçekten Python’da aynı adıyla çalışıyor mu” doğrulamasını nokta atışı yapıp, gerekli mapping/strategy kod değişiklik planını çıkaracağım.

