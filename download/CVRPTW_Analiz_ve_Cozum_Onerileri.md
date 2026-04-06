# CVRPTW: Ölçeklenebilirlik ve Kümeleme Sezgiselleri

## Akademik Araştırma ve Çözüm Önerileri Raporu

**UniRide Projesi | Mart 2026**

---

## İçindekiler

1. [Yönetici Özeti](#1-yönetici-özeti)
2. [Proje Durumu ve Hedefleri](#2-proje-durumu-ve-hedefleri)
3. [Problem Tanımı](#3-problem-tanımi)
4. [Akademik Literatür Araştırması](#4-akademik-literatür-arastirmasi)
5. [Strateji Karşılaştırması](#5-strateji-karsilastirmasi)
6. [Proje Odaklı Çözüm Önerileri](#6-proje-odakli-çözüm-onerileri)
7. [Akademik Yayın Potansiyeli](#7-akademik-yayin-potansiyeli)
8. [Implementasyon Yol Haritası](#8-implementasyon-yol-haritası)
9. [Sonuç](#9-sonuç)
10. [Kaynaklar](#10-kaynaklar)

---

## 1. Yönetici Özeti

Bu rapor, UniRide projesi kapsamında karşılaşılan **Capacitated Vehicle Routing Problem with Time Windows (CVRPTW)** probleminin ölçeklenebilirlik sorunlarını ele almaktadır. Proje, fiziksel engelli öğrencilerin üniversite servisleri ile taşınmasını amaçlamaktadır.

### Mevcut Durum
- **Faz 1 (Tamamlandı):** Python API entegrasyonu, ölü kod temizliği, encoding düzeltmeleri
- **Faz 2-4 (Bekliyor):** Veri kalıcılığı, iş akışı otomasyonu, ileri özellikler
- **Mevcut Ölçek:** N≈30 öğrenci
- **Hedef Ölçek:** N≥300 öğrenci

### Temel Bulgular

1. **PyVRP** ve **VROOM**, mevcut "Cluster-First, Route-Second" yaklaşımının katı yapısını ortadan kaldırarak N≥300 ölçeğinde doğrudan çözüm sunmaktadır.

2. **Clarke-Wright Savings** algoritması, projede halihazırda implemente edilmiş olup, time_matrix duyarlı kümeleme için ideal bir geçiş çözümüdür.

3. Proje, **akademik yayın potansiyeli yüksek** bir konuma sahiptir: engelli öğrenci taşımıcılığı için özel heterojen kapasiteli CVRPTW varyantı literatürde yeterince çalışılmamıştır.

---

## 2. Proje Durumu ve Hedefleri

### 2.1 Onaylanan Mimari Kararlar

| # | Karar | Seçim | Durum |
|---|---|---|---|
| KN1 | API Katmanı | İşlev bazlı Next.js proxy | ✅ Tamamlandı |
| KN2 | Ölü Kod | Temiz silme | ✅ Tamamlandı |
| KN3 | Time Matrix | Sabit matris + encoding fix | ✅ Tamamlandı |
| KN4 | DB Şeması | Minimal JSON (`route_plans`) | ⬜ Bekliyor |
| KN5 | Onay/İptal | Hybrid (ders=otomatik, dışı=talep) | ⬜ Bekliyor |
| KN6 | Sürücü Atama | Manuel atama | ⬜ Bekliyor |
| KN7 | Canlı Takip | Supabase Realtime | ⬜ Bekliyor |
| KN8 | Konum Sistemi | Sabit kodlar (şimdilik) | Mevcut |
| KN9 | Algoritma Pipeline | Registry Pattern | Mevcut |

### 2.2 Faz Durumu

| Faz | Durum | Açıklama |
|---|---|---|
| **Faz 1: Kritik Düzeltmeler** | ✅ Tamamlandı | Sistem çalışır hale geldi |
| **Faz 2: Veri Kalıcılığı + Atama** | ⬜ Bekliyor | Rota kaydı + sürücü ataması |
| **Faz 3: İş Akışı Otomasyonu** | ⬜ Bekliyor | Onay/iptal + bildirim |
| **Faz 4: İleri Özellikler** | ⬜ Bekliyor | Canlı takip + dinamik matris |

### 2.3 Mevcut Algoritmalar

| Algoritma | Python Key | Durum |
|-----------|------------|-------|
| Genetik Algoritma | `genetic_algorithm` | ✅ Aktif |
| Parçacık Sürü Optimizasyonu | `pso` | ✅ Aktif |
| Gri Kurt Optimizasyonu | `gwo` | ✅ Aktif |
| Harris Hawks Optimizasyonu | `hho` | ✅ Aktif |
| Two-Opt Local Search | `two_opt` | ✅ Aktif |
| Greedy / Nearest Neighbor | `greedy` | ✅ Aktif |
| Permutation TSP (Optimal) | `permutation_tsp` | ✅ Aktif |
| Google OR-Tools | `ortools_cvrp` | ✅ Aktif |

---

## 3. Problem Tanımı

### 3.1 Proje Kapsamı

UniRide projesi, fiziksel engelli (**Sw** - tekerlekli sandalye) ve engeli bulunmayan (**So** - normal koltuk) üniversite öğrencilerinin belirli zaman dilimlerinde kampüs içi ve dışı noktalara taşınmasını amaçlamaktadır. Bu, klasik bir **Capacitated Vehicle Routing Problem with Time Windows (CVRPTW)** modelidir.

### 3.2 Kısıtlar (Constraints)

| Kısıt | Değer | Açıklama |
|-------|-------|----------|
| **Sw Kapasitesi** | 4 | Tekerlekli sandalyeli öğrenci |
| **So Kapasitesi** | 5 | Diğer engel tipleri |
| **Toplam Kapasite** | 9 | Cmax |
| **Max Tur Süresi** | 45-120 dk | Tmax |
| **Time Matrix** | 29 nokta | Supabase'te 812 satır |

### 3.3 Mevcut Sorun: Katı Kümeleme

Mevcut K-Means yaklaşımı şu sorunlara yol açmaktadır:

1. **Time matrix duyarsız:** K-Means coğrafi mesafeye bakar, gerçek sürüş süresini görmez
2. **Kısıt ihlalinde restart:** 2 dakika aştı diye tüm kümeleme baştan yapılıyor
3. **Tek öğrencilik rotalar:** Verimsiz araç kullanımı
4. **Kümeler arası geçiş yok:** Re-insertion mekanizması eksik

---

## 4. Akademik Literatür Araştırması

### 4.1 Büyük Ölçekli VRP Çözümleri (2024-2026)

| Yıl | Çalışma | Alıntı | Katkı |
|-----|---------|--------|-------|
| 2024 | Transportation Research Part E | 25+ | N≥300 için etkili sezgiseller |
| 2024 | arXiv:2402.00041 | 4+ | Decomposition + pruning stratejileri |
| 2025 | MDPI Sustainability | 4+ | CVRP + CO2 emisyon hesaplama |
| 2025 | ScienceDirect | 6+ | Hibrit algoritmalar CVRP için |
| 2025 | European Journal of Operational Research | 13+ | 50 yıllık VRP değerlendirmesi |
| 2026 | arXiv:2602.21761 | - | Neural routing solvers survey |

### 4.2 Hybrid Genetic Search (HGS) ve PyVRP

**HGS-CVRP** algoritması, Thibaut Vidal tarafından geliştirilmiş ve **402+ alıntı** almıştır.

**PyVRP** (2024), HGS'nin Python implementasyonu olup **108+ alıntı** almıştır.

| Özellik | PyVRP |
|---------|-------|
| CVRP | ✅ |
| VRPTW | ✅ |
| Heterojen Kapasite | ✅ Doğal |
| Asimetrik Matris | ✅ Doğal |
| N≥1000 Performansı | İyi |

### 4.3 VROOM - Vehicle Routing Open-source Optimization Machine

**VROOM**, C++20 ile yazılmış açık kaynaklı VRP çözücüdür.

| Özellik | VROOM |
|---------|-------|
| Dil | C++20 |
| Çözüm Hızı | **Milisaniyeler** |
| OSRM Entegrasyonu | ✅ Doğal |
| REST API | ✅ |
| Docker | ✅ |
| Python API | `pip install pyvroom` |

### 4.4 Projede Mevcut Kümeleme Stratejileri

Proje kapsamında `optimizer_api/utils/clustering_strategies/` altında implemente edilmiştir:

| Strateji | Dosya | Durum |
|----------|-------|-------|
| K-Means | `kmeans.py` | ✅ Aktif |
| K-Medoids | `k_medoids.py` | ✅ Aktif |
| Fuzzy C-Means | `fuzzy_cmeans.py` | ✅ Aktif |
| Sweep | `sweep.py` | ✅ Aktif |
| Clarke-Wright | `clarke_wright.py` | ✅ Aktif |

---

## 5. Strateji Karşılaştırması

### 5.1 Ana Stratejiler

| Kriter | PyVRP | VROOM | Clarke-Wright | OR-Tools |
|--------|-------|-------|---------------|----------|
| **N=300 Performansı** | Mükemmel | Mükemmel | İyi | İyi |
| **Çözüm Hızı** | Saniyeler | **Milisaniyeler** | Saniyeler | 10-30 sn |
| **Implementasyon** | `pip install` | `pip install pyvroom` | Mevcut | Mevcut |
| **Akademik Destek** | **402+ alıntı** | Aktif proje | Klasik | Endüstri |
| **Heterojen Kapasite** | ✅ Doğal | ✅ Doğal | Modifikasyon | ✅ |
| **Asimetrik Matris** | ✅ Doğal | ✅ Doğal | ✅ | ✅ |
| **Kümeleme Gereksinimi** | **Hayır** | **Hayır** | Evet | Hayır |

### 5.2 Proje Entegrasyon Zorluğu

| Strateji | Zorluk | Etkilenen Dosyalar |
|----------|--------|-------------------|
| PyVRP | Düşük | `strategies/pyvrp_strategy.py` (yeni), `__init__.py`, `algorithm-constants.ts` |
| VROOM | Düşük | `strategies/vroom_strategy.py` (yeni), `__init__.py`, `algorithm-constants.ts` |
| Clarke-Wright | Çok Düşük | Zaten mevcut, sadece varsayılan yapılmalı |
| OR-Tools Optimize | Minimal | Mevcut `ortools_cvrp.py` parametreleri |

---

## 6. Proje Odaklı Çözüm Önerileri

### 6.1 Birincil Öneri: PyVRP (HGS) Entegrasyonu

**Neden PyVRP?**

1. **Akademik Doğrulama:** 402+ alıntı ile kanıtlanmış performans
2. **Heterojen Kapasite:** Sw/So kapasitelerini doğal destekler
3. **Kümeleme Yok:** N=300 için doğrudan çözüm
4. **Mevcut Yapıya Uyum:** Strategy Pattern'a kolay entegrasyon

**Implementasyon Adımları:**

```python
# 1. strategies/pyvrp_strategy.py oluştur
from pyvrp import ProblemData, Solution, solve
from pyvrp.stop import MaxRuntime

class PyVRPStrategy(BaseRoutingStrategy):
    @property
    def name(self) -> str:
        return "pyvrp"
    
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        # Heterojen kapasite: [Sw_capacity, So_capacity]
        # ...
```

```typescript
// 2. algorithm-constants.ts'e ekle
export const ALGORITHM_KEYS = {
  // ... mevcutlar
  PYVRP: 'pyvrp',
} as const;
```

### 6.2 İkincil Öneri: VROOM Entegrasyonu

**VROOM ne zaman tercih edilmeli?**

1. **Gerçek zamanlı ihtiyaç:** Milisaniye çözüm süresi
2. **OSRM entegrasyonu:** Gerçek dünya rota verileri
3. **REST API:** Frontend'den doğrudan çağrı

### 6.3 Üçüncül Öneri: Clarke-Wright'ı Varsayılan Yap

**En hızlı çözüm:** Proje zaten Clarke-Wright'a sahip. Sadece:

1. `clustering_strategies/clarke_wright.py`'yi varsayılan kümeleme yap
2. Mevcut GA/PSO pipeline'ı koru
3. K-Means'in yerini Clarke-Wright alsın

**Avantajları:**
- **Sıfır yeni kod:** Zaten implemente
- **Time matrix duyarlı:** Savings hesabı gerçek süreleri kullanır
- **Kısıt aşımı yok:** Kapasite/süre sınırı sırasında kontrol edilir

### 6.4 Dördüncül Öneri: OR-Tools Time Limit

Mevcut `ortools_cvrp.py`'yi optimize et:

```python
# Mevcut: 30 saniye
search_parameters.time_limit.seconds = 30

# Önerilen: N=300 için 10-15 saniye yeterli
search_parameters.time_limit.seconds = 15
search_parameters.solution_limit = 100  # Çözüm sayısı limiti
```

---

## 7. Akademik Yayın Potansiyeli

### 7.1 Literatürdeki Boşluk

**"Engelli Öğrenci Taşımacılığı için Heterojen Kapasiteli CVRPTW"** konusu literatürde yeterince çalışılmamıştır.

| Araştırma Alanı | Literatür Durumu | UniRide Katkısı |
|-----------------|------------------|------------------|
| Standart CVRP | Çok fazla çalışma | - |
| VRPTW | Çok fazla çalışma | - |
| Heterojen Filo VRP | Orta düzey | ✅ Katkı |
| **Engelli Taşımacılığı VRP** | **Az çalışılmış** | ✅✅ **Özgün katkı** |
| **Sw/So Kapasite Kısıtları** | **Neredeyse yok** | ✅✅✅ **Yayın değeri yüksek** |

### 7.2 Önerilen Akademik Yayın Konuları

#### Konu 1: "CVRPTW for Disabled Student Transportation with Heterogeneous Capacity Constraints"

**Kapsam:**
- Sw (tekerlekli sandalye) ve So (diğer engeller) için ayrı kapasite kısıtları
- Gerçek dünya verisi ile benchmark (29 nokta, 812 edge)
- Hibrit kümeleme + meta-sezgisel yaklaşım

**Hedef Dergiler:**
- Transportation Research Part E
- Computers & Operations Research
- European Journal of Operational Research

#### Konu 2: "Comparison of Meta-heuristic Algorithms for Accessible Student Transportation"

**Kapsam:**
- GA, PSO, GWO, HHO performans karşılaştırması
- PyVRP vs VROOM vs OR-Tools benchmark
- N=30'dan N=300'e ölçeklenebilirlik analizi

**Hedef Dergiler:**
- Applied Soft Computing
- Expert Systems with Applications
- Journal of Heuristics

#### Konu 3: "Real-time Rerouting for Special Education Transportation Services"

**Kapsam:**
- Dinamik talep yönetimi (öğrenci iptal/ekleme)
- Canlı konum takibi ile ETA hesaplama
- Supabase Realtime implementasyonu

**Hedef Konferanslar:**
- IEEE Intelligent Transportation Systems Conference (ITSC)
- ACM SIGSPATIAL

### 7.3 Akademik Yayın Yol Haritası

```
Faz 1-2 Tamamlandıktan Sonra (1-2 Ay):
├── Veri setinin hazırlanması ve anonimleştirilmesi
├── Benchmark senaryolarının oluşturulması
└── İlk taslak yazımı

Faz 3 Tamamlandıktan Sonra (3-4 Ay):
├── Hibrit onay/iptal mekanizmasının modellenmesi
├── Performans metriklerinin toplanması
└── Karşılaştırmalı sonuçların analizi

Faz 4 Tamamlandıktan Sonra (5-8 Ay):
├── Real-time özelliklerin dahil edilmesi
├── Genişletilmiş deney seti
└── Nihai makale gönderimi
```

### 7.4 Metodoloji Önerisi

**Deneysel Tasarım:**

| Parametre | Değerler |
|-----------|----------|
| Öğrenci Sayısı (N) | 30, 50, 100, 200, 300 |
| Algoritmalar | GA, PSO, GWO, HHO, PyVRP, OR-Tools |
| Kümeleme | K-Means, Clarke-Wright, Sweep, Yok |
| Kapasite Senaryoları | Dengeli (4Sw+5So), Ağırlıklı Sw, Ağırlıklı So |
| Time Matrix | Gerçek (Supabase), Simetrik, Rastgele |

**Performans Metrikleri:**

1. **Çözüm Kalitesi:** Toplam tur süresi, araç sayısı
2. **Hesaplama Süresi:** Saniye cinsinden execution time
3. **Kısıt İhlali:** Kapasite/süre sınırı aşımı yüzdesi
4. **Ölçeklenebilirlik:** N arttıkça süre artış oranı

---

## 8. Implementasyon Yol Haritası

### 8.1 Kısa Vadeli (1-2 Hafta) - Faz 2 Öncesi Hazırlık

**PyVRP Entegrasyonu:**
```bash
pip install pyvrp
```

- [ ] `optimizer_api/strategies/pyvrp_strategy.py` oluştur
- [ ] `strategies/__init__.py`'ye kaydet
- [ ] `algorithm-constants.ts`'e ekle
- [ ] Basit test: N=30 ile karşılaştırma

**Clarke-Wright Varsayılan Yap:**
- [ ] `VehicleCalculator` varsayılan kümelemeyi değiştir
- [ ] K-Means → Clarke-Wright geçişi

### 8.2 Orta Vadeli (3-4 Hafta) - Faz 2 ile Paralel

- [ ] Faz 2 görevlerini tamamla (rota kaydı, sürücü ataması)
- [ ] PyVRP'yi karşılaştırma endpoint'ine ekle
- [ ] N=100, N=200, N=300 ölçek testleri
- [ ] Performans sonuçlarını logla

### 8.3 Uzun Vadeli (5-8 Hafta) - Faz 3-4 ile Entegrasyon

- [ ] VROOM değerlendirmesi (gerçek zamanlı ihtiyaç varsa)
- [ ] Akademik yayın için veri toplama
- [ ] Benchmark sonuçlarının görselleştirilmesi
- [ ] Makale taslağı hazırlama

---

## 9. Sonuç

### 9.1 Temel Bulgular

1. **Mevcut "Cluster-First, Route-Second" yaklaşımı**, K-Means'in time matrix duyarsızlığı nedeniyle N≥300 ölçeğinde verimsizdir.

2. **PyVRP** ve **VROOM**, kümeleme gerektirmeden N=300 ölçeğinde doğrudan çözüm sunmaktadır.

3. **Clarke-Wright Savings**, projede zaten mevcut olup, en hızlı entegre edilebilir çözümdür.

4. Proje, **engelli öğrenci taşımacılığı için heterojen kapasiteli CVRPTW** konusuyla literatürde özgün bir konuma sahiptir.

### 9.2 Önerilen Aksiyon

| Öncelik | Aksiyon | Zaman |
|---------|---------|-------|
| 1 | Clarke-Wright'ı varsayılan kümeleme yap | 1 gün |
| 2 | PyVRP stratejisi ekle | 1 hafta |
| 3 | Faz 2 görevlerini tamamla | 2-3 hafta |
| 4 | Akademik yayın için veri topla | Devam eden |

### 9.3 Sonuç

UniRide projesi, hem operasyonel ihtiyaçları karşılayacak güçlü bir VRP çözümü hem de akademik literatüre özgün katkı sağlayacak bir araştırma konusu sunmaktadır. PyVRP entegrasyonu ile ölçeklenebilirlik sorunu çözülecek, Clarke-Wright geçişi ile ise time matrix duyarlı kümeleme hızla elde edilecektir.

---

## 10. Kaynaklar

### Akademik Kaynaklar (2024-2026)

1. Chen, L. et al. (2024). *An efficient heuristic for very large-scale vehicle routing*. Transportation Research Part E. (25+ alıntı)

2. Vidal, T. (2020). *Hybrid Genetic Search for the CVRP*. Transportation Science. (402+ alıntı)

3. Wouda, N.A., Lan, L., Wiering, M.A. (2024). *PyVRP: A High-Performance VRP Solver Package*. INFORMS Journal on Computing. (108+ alıntı)

4. "Beyond fifty years of vehicle routing: Insights into the future" (2025). European Journal of Operational Research. (13+ alıntı)

5. "An overview of vehicle routing problems: A comprehensive" (2026). ScienceDirect.

6. "Survey on Neural Routing Solvers" (2026). arXiv:2602.21761.

7. "Solution of the Capacity-Constrained Vehicle Routing" (2025). MDPI Sustainability. (4+ alıntı)

8. "Innovative hybrid algorithm for efficient routing" (2025). ScienceDirect. (6+ alıntı)

### Proje Dokümanları

9. UniRide ROADMAP.md - Geliştirme Yol Haritası

10. UniRide ARCHITECTURE.md - Mimari Dokümanı

11. UniRide ANALYSIS.md - Mevcut Durum Analizi

12. UniRide 2026-03-25-full-system-design.md - Tam Sistem Tasarımı

13. UniRide 2026-03-26-scalability-options.md - Ölçeklenebilirlik Seçenekleri

### Açık Kaynak Projeler

14. PyVRP Documentation. https://pyvrp.org/

15. HGS-CVRP GitHub. https://github.com/vidalt/HGS-CVRP

16. VROOM GitHub. https://github.com/VROOM-Project/vroom

17. pyvroom PyPI. https://pypi.org/project/pyvroom

18. Google OR-Tools VRP Documentation.

---

*Rapor Tarihi: 26 Mart 2026*
*UniRide Projesi*
*Sürüm: 2.0 - Proje Entegreli ve Akademik Yayın Odaklı*
