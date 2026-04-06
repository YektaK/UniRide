# 01 - UniRide SOTA Framework Architecture & Vision

> **Oluşturulma Tarihi:** 01 Nisan 2026, 15:40  
> **Sürüm:** 1.0.0  
> **Konu:** VRP (Araç Rotalama Problemi) Çözücü Motorunun Akademik "State-of-the-Art (SOTA)" Seviyesine Yükseltilmesi

## 1. Vizyon ve Amaç (Vision & Goal)
Mevcut UniRide optimizasyon motoru, kapasite kısıtlı araç rotalama problemini (CVRPTW) PSO, HHO, GWO gibi saf sürü zekası algoritmaları ve $O(N^2)$ zaman karmaşıklığına sahip standart bir Split-Decoder ile çözmektedir.

Planlanan **SOTA (State of the Art) Framework** dönüşümündeki amaç; güncel 2024-2026 VRP akademik makalelerinde kanıtlanmış "Lineer Bölme (Linear Split)", "Zaman Bükülmesi (Time-Warp)", ve "ALNS Destekli Hibrit Sürü" yaklaşımlarını sisteme entegre etmektir. Bu dönüşüm sayesinde sistem sadece rotalama yapan bir ticari yazılım olmaktan çıkacak; literatüre katkı sağlayabilecek yenilikçi (novel) bir akademik çatıya dönüşecektir.

## 2. Mimari Kararlar (Architectural Decisions)

Sistemi SOTA ilan etmemizi sağlayacak 4 temel mimari karar alınmıştır:

### A. Lineer Zamanlı ( $O(N)$ ) Split Algoritması
- **Neden?** Geleneksel Prins algoritması dev-turları (giant tours) alt rotalara bölerken $O(N^2)$ zaman harcar. Bu, 100+ öğrencilik rotalarda büyük darboğaz yaratır.
- **Karar:** Parçalama işlemi sırasında ileriye dönük durak sayısını mantıksal olarak sınırlayan (Bounded Forward Search) ve *Monotone Queue* mantığı ile işletilen $O(N)$ zamanlı bir dekoder yazılacaktır.

### B. Infeasibility Relaxation (Esnek Sınırlar ve Cezalar)
- **Neden?** Klasik algoritmalar kapasite veya zaman sınırı aşıldığında o rotayı çöpe atar. Bu, genetik çeşitliliği öldürür.
- **Karar:** Rota asla reddedilmeyecek. Bunun yerine rotaya **Time-Warp** (zamanı geriye sarma / gecikme) ve **Kapasite Taşması (Soft Capacity)** cezaları eklenecek. Çok kötü rotalar ağır ceza puanları alarak genetik havuzdan doğal seçilimle elenecek, esnek rotalar ise lokal minimumlardan kurtulmayı sağlayacaktır.

### C. ALNS Destekli Sürü (Swarm) Hibridizasyonu
- **Neden?** Sürü algoritmaları (PSO, HHO) sayısal/sürekli varyasyonlar için harikadır ama ayrık (discrete) rotalama problemlerinde ezbere çalışırlar. 
- **Karar:** Sadece sürü zekası kullanmak yerine, sürünün "Hangi onarma/yok etme operatörünün kullanılacağına" karar verdiği bir üst-yönetici (metaheuristic) hibrit model (MO-HHO-ALNS) kurulacaktır.

### D. Multi-Objective (Pareto Front) Optimizasyon
- **Neden?** Sadece "en ucuz maliyetli" rotayı dönmek modern lojistikte yetersizdir.
- **Karar:** Karar vericiye/kullanıcıya (Admin) birbiriyle çelişen amaçlar için (Minimum Araç Sayısı vs Minimum Öğrenci Gecikmesi) Non-dominated Sorting (NSGA-II) mantığıyla çoklu çözüm tepsisi (Pareto Front) sunulacaktır.

---
**Onaylar:** Mimarinin temel kodlama prensiplerinde Python Standart Kütüphaneleri ve Saf Numpy kullanılacak; performansı baltalayan şişkin dış kütüphanelerden kaçınılacaktır.
