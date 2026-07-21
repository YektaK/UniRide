# 02 - SOTA Framework Implementation Roadmap & Phases

> **Oluşturulma Tarihi:** 01 Nisan 2026, 15:40  
> **Konum:** `UniRide/docs/sota_framework_plan_2026/02_Implementation_Phases.md`

Bu doküman projenin 4 ana fazda (Phase) nasıl devrileceğini ve mevcut ilerleyişi gösteren kuş bakışı yol haritasıdır.

## Mevcut Durum Özeti (Status)
- **Branch:** `feature/verified-integration`
- **Faz 1 Durumu:** TAMAMLANDI (Test Edildi ve Entegre Edildi)

---

## Tüm Fazların Detaylı İncelemesi

### [Faz 1] Core Engine: Lineer Split ve Zaman/Kapasite Cezaları
**Açıklama:** Rota bölen ana motorun performansının $O(N^2)$'den $O(N)$'e çekilmesi ve katı kısıtlamaların (strict bounds) dinamik cezalara (soft penalties) dönüştürülmesi.
**Durum:** `[X] Tamamlandı`
- **Geliştirilen Dosyalar:** `optimizer_api/utils/linear_split_decoder.py`, `cvrptw_wrapper.py`
- **Test Sonuç:** `test_linear_split_perf.py` ile 150 öğrencilik testte çalışma hızı **1.57 ms'den 0.80 ms'ye** (%50 kanıtlanmış artış) düşürüldü. Motor artık Time-Warp cezalarını destekliyor.

---

### [Faz 2] Sezgisel Operatörlerin Tasarımı (ALNS Development)
**Açıklama:** Sürü algoritmalarının kullanabileceği akıllı rota Değiştirme (Destroy) ve Tamir (Repair) mekanizmalarının algoritmik temellerinin atılması.
**Durum:** `[ ] Bekliyor`

**İhtiyaç Duyulan Modüller:**
1. **Destroy Operators:**
   - *Random Removal:* Rastgele N adet durağı siler. (Çeşitlilik sağlar)
   - *Worst Removal:* En çok ceza/maliyet yiyen rotadaki durakları siler.
   - *Shaw (Related) Removal:* Uzamsal ve zaman penceresi olarak birbirine yakın kümelenmiş çocukları topluca rotadan söker.
2. **Repair Operators:**
   - *Greedy Insertion:* Sökülen çocuğu anında en az maliyet yaratan yere takar.
   - *Regret-2 Insertion:* Bir çocuğu en iyi yere takmasıyla 2. en iyi yere takması arasındaki fark (pişmanlık) en büyük olanı önce yerleştirir. (SOTA'dır)

---

### [Faz 3] Hibridizasyon: Sürü + ALNS (Hybrid Metaheuristics)
**Açıklama:** Yazılan ALNS operatörlerinin, mevcut metaheuristic algoritmaların (HHO, PSO) ana güncelleme fonksiyonlarının içine zerk edilmesi. Algoritma artık vektör değiştirmek yerine ALNS operatör olasılıklarını (Roulette Wheel) güncelleyecek.
**Durum:** `[ ] Bekliyor`

**Nasıl Çalışacak?**
- `hho_split_strategy.py` veya yepyeni bir `mo_hho_alns_strategy.py` yaratılacak.
- Harris Hawks'ın "Avlanma" iterasyonu esnasında, Şahin (Hawk) pozisyonunu değiştirmek yerine ALNS'deki "Worst Removal" vs "Shaw Removal" operatörünün rastgelelik ağırlıklarını o nesil (generation) için güncelleyecek. Başarılı operatörler ödüllendirilecek (Adaptive mekanizma).

---

### [Faz 4] Çok Amaçlı Yapı (Pareto Front) ve API Çıkışı
**Açıklama:** Tüm sistemin sonucunda çıkan değerlerin Front-end'e "Çoklu Senaryo Tepsisi" olarak sunulması.
**Durum:** `[ ] Bekliyor`

**İş Akışı:**
- Optimizasyon çıktısı (Response Schema), `List[VehicleRoute]` yerine `List[Scenarios]` olarak değişecek.
- Senaryo 1: En Az Araç, Max Time-Warp (Sıkışık Rota)
- Senaryo 2: Opsiyonel Araç Sayısı, Sıfır Gecikme (Konfor Rotası)
- Arayüz Dashboard'u bu api değişikliklerini okuyabilmesi adına güncellenecektir.
