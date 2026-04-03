# 03 - Developer Task Checklists & Prompts (Best Practices)

> **Oluşturulma Tarihi:** 01 Nisan 2026, 15:40  
> **Konum:** `UniRide/docs/sota_framework_plan_2026/03_Developer_Tasks.md`

Bu doküman projeye dahil olacak diğer yazılımcılar/AI ajanları için, herhangi bir "Uzun brief/açıklama" vermeden hedefe ulaştırmak amaciyla **AI Best-Practices** standartlarında hazırlanmış iş emri (Prompt) şablonlarıdır. Herhangi birine "Bunu yap" dendiğinde sıfır hatayla uygulamasını sağlar.

---

## Task A: Faz 2 - ALNS Operatörlerinin Uygulanması
**Yazılımcıya İletilecek İhtiyaç Bildirimi (Task Prompt):**

```text
# Görev (Task)
`optimizer_api/strategies/alns_operators.py` dosyasını oluşturup CVRPTW için Adaptive Large Neighborhood Search (ALNS) operatörlerini dahil etmen gerekiyor.

# Bağlam (Context) & Dosyalar
- Kullanacağın veri modelleri: `optimizer_api/models/schemas.py`
- Mevcut Decoder mantığı: `optimizer_api/utils/linear_split_decoder.py` üzerinden geçiyor. Öğrencileri (`StudentNode`) dev-tur (giant_tour) diziliminde değerlendiriyoruz.

# Kısıtlamalar (Constraints) - KESİNLİKLE UYULACAK
1. Hiçbir dış kütüphane kullanma (sadece Python Standard Library ve `random`, `math`, `numpy` opsiyonel).
2. Algoritmaların sadece dev-tur (List[str] formatındaki string listesi) üzerinde sökme ve takma işlemi yapmasını sağla, araç yönetimiyle uğraşma; onu LinearSplitDecoder halledecek.

# Beklenen Çıktılar (Implementation)
1. **Destroy (Sökme):** `random_removal()`, `worst_removal()`, `shaw_related_removal()` class fonksiyonları.
2. **Repair (Takma):** `greedy_insertion()`, `regret_k_insertion(k=2)` class fonksiyonları.
3. **Adaptive Roulette:** Bu operatörleri başarıya göre çağıran bir olasılık motoru (Roulette Wheel).

# Doğrulama (Verification)
1. Kodu tamamladıktan sonra `test_alns_logic.py` yaz.
2. Basit 10 elemanlı bir lokasyon array'inde Shaw Removal'ın coğrafik olarak en yakın 3 lokasyonu söktüğünü, Regret-2'nin onları geri taktığını Assert/Test et. 
3. Başarılı olduğunu konsol loguyla kanıtla.
```

---

## Task B: Faz 3 - Hibrid Sürü Stratejisi (MO-HHO-ALNS)
**Yazılımcıya İletilecek İhtiyaç Bildirimi (Task Prompt):**

```text
# Görev (Task)
HHO (Harris Hawks Optimization) algoritmasını, ALNS operatörleri ile birleştirerek `mo_hho_alns_strategy.py` adında yeni bir strateji yaz.

# Bağlam (Context)
- `optimizer_api/strategies/base_strategy.py` yapısından miras (inherit) alınacak.
- Az evvel yazılan `alns_operators.py` kullanılacak.

# Yapılacak Mantık Değişimi
Klasik HHO iterasyonlarında Şahinlerin konumunu (X vektörünü) matematiksel olarak kaydırırız. Bu kez yapman gereken: 
- X vektörünü ALNS'nin parametre uzayı (Örn: Hangi removal operatörünün ağırlığı ne olacak? Regret derecesi ne?) olarak hayal et.
- Sürü zekasını (HHO), "En optimal operatörü seçmek" için kullan.
- Vektör kararına göre seçilen ALNS operatörü üzerinden yeni dev-turu (giant_tour) üret ve `LinearSplitDecoder`'a at.

# Doğrulama (Verification)
Stratejiyi mevcut CompareRequest uç noktasına (API) bağla ve algoritmanın Postman veya `run_all_tests.py` üzerinden başarıyla total_cost dönebildiğinden emin ol (Loglarda exception fırlatmasın).
```

---

> Diğer yazılımcılar/Ajanlar sadece yukarıdaki Markdown kutularını (Workflow Prompt) okuyarak projeyi sıfır kafa karışıklığı ve 0 kısıt ihlaliyle mükemmel şekilde SOTA yapısına kavuşturabilirler.
