# Yeniden tasarım iş planı: E2BSO, R2DMA, P-AOEA ve yeni birleşim önerileri

Tarih: 2026-10-13. Dayanak: [SOTA_FAMILY_EVALUATION_2026-10-13.md]({{artifact:0df09bf6-0dde-4b32-b976-95b195659dd0}}) (mekanizma ölçümleri ve kıyas). Depo dosyalarında değişiklik yapılmadı; bu belge bir plandır.

## Kısa özet

- **"Frankenstein" yaklaşımı meşru bir tasarım yöntemidir.** Literatürde bileşen tabanlı ve otomatik algoritma tasarımı olarak geçer ([Stützle & López-Ibáñez](https://doi.org/10.1007/978-3-319-91086-4_17)). Yöntem üç koşulla çalışır: doğru organı seçmek, onu doğru nakletmek ve her organın işe yaradığını ablasyonla göstermek. Üçlüde ikinci ve üçüncü koşul hiç sağlanmamış, birincisi de kısmen.
- **Asıl başarı organları başka yerde.** LKH, EAX, Chained-LK ve HGS'yi başarılı kılan şeyler şunlar: hızlı ve aday listeli yerel arama; büyük vadi (big valley) yapısına uygun, ortak kenarı koruyan rekombinasyon; çeşitliliğin faz değiştirmeyle değil seçimle yönetilmesi; ve kalibre edilmiş kabul. Metafor güncelleme denklemleri bu organlardan biri değil.
- **En büyük kaldıraç yerel arama hızı.** Aynı yerel aramayı kullanan ILS kontrolü bile a280'de 30 s'de yalnızca 21 iterasyon yaptı; E2BSO 118,6 s'de 1 iterasyon. Aday listesi ve don't-look bit olmadan hiçbir üst katman kendini gösteremiyor. Depoda ikisi de yok.
- **Plan beş fazdan oluşuyor:**
  - (0) Altyapı ve karar deneyleri
  - (1) Üçlünün minimum onarımı ve ablasyonu
  - (2) Yeni birleşimler
  - (3) Değerlendirme protokolü
  - (4) Entegrasyon ve adlandırma

  Her fazın sonunda ölçülebilir bir geçiş kapısı var.
- **Beş yeni birleşim öneriyorum** ve her birini eski algoritmalardan birinin "doğru yapılmış" ardılı olarak kurguluyorum:
  - EB-PXILS (E2BSO'nun ardılı)
  - DAR-MA (R2DMA'nın ardılı; yenilik potansiyeli en yüksek olan)
  - BA-LNS (P-AOEA'nın ardılı; üretim VRP hattına en kolay aktarılan)
  - BB-Merge (yoğunlaştırma modülü)
  - EAX-MA (referans düzeyinde üst sınır kolu)
- **Beklenti dürüstçe şu:** Python/Numba ile yazılan hiçbir birleşimin TSPLIB'de eşit duvar saati süresinde LKH-3 veya GA-EAX'i geçmesi beklenmiyor. Gerçekçi hedef üç başlık:
  - aynı yerel aramalı güçlü ILS kontrolünü anlamlı biçimde geçmek;
  - bileşen katkılarını ATSP dahil dürüst biçimde ölçmek;
  - DAR-MA'nın mesafe koşullu operatör seçimi gibi sınanabilir yeni bir mekanizma önermek.

## 1. Teşhis: ödünç alınan özellikler ve asıl başarı nedenleri

| Ödünç alınan özellik (algoritma) | Kaynağı | Kaynakta başarıyı sağlayan asıl şey | Depodaki uygulama ve ölçülen sonuç | Doğru aktarım |
|---|---|---|---|---|
| Kenar entropisi (E2BSO) | EAX ([Nagata 2006](https://doi.org/10.1007/11730095_15); [Nagata & Kobayashi 2013](https://doi.org/10.1287/ijoc.1120.0506); [Nagata 2020](https://doi.org/10.1162/evco_a_00268)) | Entropi, **hayatta kalan seçiminde** kullanılır: ebeveynin yerine uzunluk kazancını entropi kaybına oranlayan çocuk seçilir. Asıl güç AB-döngülü EAX çaprazlamasından gelir. | Entropi faz değiştirmek için kullanılıyor ve `log2(P·n)` ile yanlış ölçekleniyor. Fazlar sabit bir takvime dönüşüyor. | Doğru normalize edilmiş entropi, seçimde ya da rekombinasyon/sarsım oranını denetlemek için kullanılmalı. |
| "Sürü" rehberli kenar enjeksiyonu (E2BSO) | PSO; path relinking | TSP'de etkili olan, iyi optimumların ortak kenarlarını koruyan ve farklı kısımlarını en iyi biçimde birleştiren rekombinasyondur: GPX/GPX2 ([Whitley vd. 2009](https://doi.org/10.1145/1569901.1570026); [Tinós vd. 2020](https://doi.org/10.1162/evco_a_00254)). | Hedef kenarlar 2-opt ters çevirmesiyle zorlanıyor; `ia<ib` koşulu yüzünden %52'si atlanıyor. | GPX2: 2^k çocuğun en iyisi O(n)'de bulunuyor ve çocuk ebeveynlerden kötü olamıyor. |
| LAHC (E2BSO, P-AOEA) | [Burke & Bykov 2017](https://doi.org/10.1016/j.ejor.2016.07.012) | Her yörüngenin kendi maliyet geçmişi vardır; tek parametresi L'dir; geçmiş başlangıç maliyetiyle doldurulur. | Geçmiş popülasyona ortak, `gbest_cost` ile dolduruluyor ve ∞ ile başlıyor. Üretim ayarında kabul oranı %100. | Yörünge başına LAHC. |
| Benzerliğe göre eşleştirme (R2DMA) | HGS çeşitlilik yönetimi ([Vidal vd. 2012](https://doi.org/10.1287/opre.1120.1048)) | Bozuk çift (broken-pairs) mesafesi ve çeşitlilik katkılı yanlı uygunluk; klonlar ayıklanır. | 6 boyutlu rezonans tur gösterimine bağlı (ters tur ≈0,43 alıyor). Kararların %99,9'u yerel aramasız tek rastgele takas. | Döndürme ve yönden bağımsız kenar mesafesi, yanlı uygunluk ve her çocuğa yerel arama. |
| Constructive çaprazlama (R2DMA) | Büyük vadi ([Boese vd. 1994](https://doi.org/10.1016/0167-6377%2894%2990065-5); [Hains vd. 2011](https://doi.org/10.1057/jors.2010.116)); tur birleştirme ([Cook & Seymour 2003](https://doi.org/10.1287/ijoc.15.3.233.16078)) | İyi optimumlar kenarlarının çoğunu paylaşır. Ortak kenarlar sabitlenip yalnızca farklı bölge yeniden optimize edilir. | Ortak kenarların yalnızca %44–55'i korunuyor; yerel aramadan sonra sonuç rastgele yeniden başlatmayla aynı. | GPX2 ya da backbone sabitleyip yeniden optimize etme (BB-Merge). |
| SA kabulü (R2DMA, P-AOEA) | [Kirkpatrick vd. 1983](https://doi.org/10.1126/science.220.4598.671); [Franzin & Stützle 2019](https://doi.org/10.1016/j.cor.2018.12.015) | Sıcaklık, tipik kötüleşme (Δ) dağılımına göre ayarlanır. | T₀ = 0,4·maliyet; kötüleşen adayların %63–100'ü kabul ediliyor. | T₀, medyan Δ için başlangıç kabul olasılığı 0,3–0,5 olacak biçimde kalibre edilmeli. |
| Operatör genomu evrimi (P-AOEA) | Öz-uyarlama ([Gómez 2004](https://doi.org/10.1007/978-3-540-24854-5_113)); uyarlanabilir operatör seçimi ([Fialho vd. 2010](https://doi.org/10.1007/s10472-010-9213-y); [Li vd. 2014](https://doi.org/10.1109/tevc.2013.2239648)); ALNS ([Ropke & Pisinger 2006](https://doi.org/10.1287/trsc.1050.0135)) | Oran temelli, kayan pencereli ya da sönümlü kredi ve keşif terimi. Uyarlamanın ortalama katkısı küçüktür ([Turkeš vd. 2021](https://doi.org/10.1016/j.ejor.2020.10.045)). | Birikimli sayaç; ilk 3 genom kilitleniyor. Ağırlıklar güncellenmiyor; 30 s'de evrim hiç tetiklenmiyor. | Bandit tabanlı operatör seçimi. Depodaki `ALNS_TSP._apply_weights` (`alns_tsp.py:156-175`) zaten doğru bir Ropke–Pisinger güncellemesi yapıyor. |

**Ortak ders:** Üç arızanın üçü de sessizdi; kod hata vermeden çalıştı ve geçerli tur üretti. Mekanizma telemetrisi (faz, mod ve kabul sayaçları) ile bileşen sözleşme testleri olmadan bu tür organ reddi fark edilmiyor. Planın her fazı bu iki unsuru zorunlu tutuyor.

## 2. Başarılı TSP sezgisellerinin gerçek "organları"

| # | Organ | Nerede kanıtlandı | Depodaki durumu |
|---|---|---|---|
| O1 | **Hızlı yerel arama:** aday (komşu) listeleri, don't-look bitleri ya da aktif kuyruk, O(1) delta değerlendirmesi | [Lin & Kernighan 1973](https://doi.org/10.1287/opre.21.2.498); [Bentley 1992](https://doi.org/10.1287/ijoc.4.4.387); [Johnson 1990](https://doi.org/10.1007/bfb0032050); [Helsgaun 2000](https://doi.org/10.1016/s0377-2217%2899%2900284-2) | **Yok.** `ls_engine.py` her geçişte tüm çiftleri tarıyor. Üretim tarafında `models.py` içinde bir KNN maskesi var; TSP çekirdeklerinde kullanılmıyor. |
| O2 | **Yerel ve küçük sarsım:** segment double-bridge, coğrafi kick'ler | [Lourenço vd., ILS](https://doi.org/10.1007/0-306-48056-5_11); [Applegate vd. 2003](https://doi.org/10.1287/ijoc.15.1.82.15157) | Kısmen var (E2BSO içinde double-bridge). Ancak her kick'ten sonra tüm tur yeniden taranıyor. |
| O3 | **Ortak kenarı koruyan rekombinasyon:** EAX, GPX/GPX2, IPT, tur birleştirme | [Nagata & Kobayashi 2013](https://doi.org/10.1287/ijoc.1120.0506); [Whitley vd. 2009](https://doi.org/10.1145/1569901.1570026), [2010](https://doi.org/10.1007/978-3-642-15844-5_57); [Tinós vd. 2020](https://doi.org/10.1162/evco_a_00254); [Sanches vd. 2017](https://doi.org/10.1145/3071178.3071305) | **Yok.** Depoda GPX ya da EAX bulunmuyor; yalnızca OX var (`ga_operators.py:11`). |
| O4 | **Seçimde çeşitlilik yönetimi:** entropi korumalı seçim, yanlı uygunluk | [Nagata & Kobayashi 2013](https://doi.org/10.1287/ijoc.1120.0506); [Vidal vd. 2012](https://doi.org/10.1287/opre.1120.1048); çok hunili yapı ([Ochoa & Veerapen](https://doi.org/10.1007/s10732-017-9334-0)) | Yanlış biçimde var (faz değiştirme, rezonans). |
| O5 | **Kalibre edilmiş kabul:** yörünge başına LAHC, Δ'ya göre SA, "kötü değilse kabul" | [Burke & Bykov 2017](https://doi.org/10.1016/j.ejor.2016.07.012); [Franzin & Stützle 2019](https://doi.org/10.1016/j.cor.2018.12.015) | Yanlış biçimde var. |
| O6 | **Uyarlanabilir operatör seçimi** (küçük ama ölçülebilir katkı) | [Ropke & Pisinger 2006](https://doi.org/10.1287/trsc.1050.0135); [Li vd. 2014](https://doi.org/10.1109/tevc.2013.2239648); [Turkeš vd. 2021](https://doi.org/10.1016/j.ejor.2020.10.045) | `alns_tsp.py` içinde doğru biçimde var; P-AOEA'da yanlış. |
| O7 | **VRP'ye özgü:** string removal ve blink insertion, Split, SWAP*, ceza tabanlı uygunsuzluk yönetimi | [Christiaens & Vanden Berghe 2020](https://doi.org/10.1287/trsc.2019.0914); [Vidal 2022](https://doi.org/10.1016/j.cor.2021.105643); [Wouda vd. 2024](https://doi.org/10.1287/ijoc.2023.0055) | PyVRP stratejisi üretimde (`pyvrp_strategy.py`) bulunuyor. |

**Organ olmayanlar:** Metaforlardan türetilmiş konum ve hız güncellemeleri, "rezonans" ya da "sürü" katmanları performansa ölçülebilir bir katkı vermiyor ([Sörensen](https://doi.org/10.1111/itor.12001); [Camacho‐Villalón vd. 2022](https://doi.org/10.1111/itor.13176); [Aranha vd. 2021](https://doi.org/10.1007/s11721-021-00202-9)). Bizim ölçümlerimiz de aynı yöne işaret ediyor: üç algoritmada da asıl işi 2-opt/Or-opt çekirdeği yapıyor.

## 3. Organ nakli kuralları (tasarım ilkeleri)

1. **Sözleşme testi:** Her bileşenin matematiksel bir sözleşmesi ve onu sınayan bir birim testi olmalı. Örnek sözleşmeler: mesafe(T, döndür(T)) = 0; mesafe(T, ters(T)) = 0 (simetrik durumda); özdeş popülasyonun entropisi 0; GPX çocuğu tüm ortak kenarları içerir ve maliyeti iki ebeveynin en iyisinden büyük olamaz; LAHC geçmişi yörüngeye özgüdür.
2. **Telemetri:** Her mod, faz ve operatörün seçilme payı, başarı oranı ve kabul oranı varsayılan çıktı olmalı. İmza mekanizması kararların %5'inden azında çalışıyorsa bu otomatik olarak uyarı üretmeli.
3. **Tek bütçe para birimi:** Amaç ya da delta değerlendirmesi sayımı `ObjectiveEvaluationBudget` (`objective_budget.py:16`) ile tutulmalı; duvar saati de raporlanmalı. Süre kontrolü iterasyon sonunda değil, yerel arama döngüsünün içinde yapılmalı. Bütçe aşımı en fazla %5 olabilir.
4. **Belirlenimcilik:** Tek iş parçacığında aynı tohum aynı turu üretmeli.
5. **Her organ "kira ödemeli":** Her mekanizmanın açık/kapalı ablasyon kolu olmalı. Holm düzeltmeli eşleştirilmiş testte katkısı gösterilemeyen mekanizma çıkarılmalı.
6. **Güçlü kontrol kolu:** Aynı hızlı yerel aramayı kullanan ILS olmalı. Böylece kazanç, yerel arama hızına değil üst katmana atfedilebilir.
7. **ATSP'ye uygun tasarım:** Üretimdeki süre matrisleri yönlü. Hareketler ya yönü korumalı (Or-opt, or-3opt) ya da yönlü delta ile hesaplanmalı. Simetrik operatörler (2-opt, GPX2) ATSP'de ancak standart 2n dönüşümüyle kullanılabilir. Depodaki `three_opt.py` simetrik ve yönlü yeniden bağlamayı zaten ayırıyor.
8. **Eşit ayar:** Bütün kollar aynı ayar bütçesiyle ayarlanmalı ([irace, López-Ibáñez vd. 2016](https://doi.org/10.1016/j.orp.2016.09.002)).

## 4. İş planı

Çaba tahminleri kaba ve tek geliştirici içindir.

### Faz 0: Altyapı ve karar deneyleri (≈2 hafta)

| ID | İş | Depo konumu (öneri) | Kabul ölçütü |
|---|---|---|---|
| 0.1 | **Hızlı yerel arama çekirdeği** (Numba): K-en yakın aday listesi (K=8–10), don't-look bit kuyruğu, 2-opt (yalnızca simetrik), Or-opt (her ikisi), or-3opt segment taşıma (yönlü). İsteğe bağlı bütçe kancası. | `uniride_core/algorithms/hybrid_tsp/fast_ls.py` | a280'de `MultiLayerLS('moderate')` ile aynı yerel optimum kalitesi (±%0,5) ve ≥50 kat daha fazla kick/s. Tur geçerliliği; artımlı maliyet, yeniden hesaplanan maliyete eşit; ATSP'de yönlü maliyet korunuyor (`test_canonical_three_opt_integration.py` kalıbı). |
| 0.2 | **Bütçe ve sonlandırma:** değerlendirme sayacı ve döngü içi süre kontrolü | `objective_budget.py` yeniden kullanılacak | Aşım ≤%5; değerlendirme sayısı tam; aynı tohum aynı tur. |
| 0.3 | **Ortak ölçüler:** bozuk çift mesafesi (yönlü/yönsüz), normalize kenar entropisi H_norm = (H − log2 n)/log2 m (m tur, m·n ≤ n(n−1)/2 iken), yanlı uygunluk, tüm çiftler ya da rastgele örnekle çeşitlilik | `hybrid_tsp/diversity.py` | §3 madde 1'deki sözleşme testleri. |
| 0.4 | **Rekombinasyon kitaplığı:** GPX2 (simetrik), OX ile yerel arama (yedek), backbone sabitleme | `hybrid_tsp/recombination.py` | GPX2 sözleşmesi: ortak kenarlar %100 korunuyor, çocuk ≤ en iyi ebeveyn. Bileşen sayısı raporlanıyor. |
| 0.5 | **Kabul ve operatör seçimi:** yörünge başına LAHC, Δ'ya göre kalibre SA, RRT; roulette (Ropke–Pisinger), FRR-MAB, uniform | `hybrid_tsp/acceptance.py`, `hybrid_tsp/aos.py` | LAHC kabul oranı zamanla düşüyor; SA başlangıç kabulü hedefe ±0,05 yakın. |
| 0.6 | **Kıyas düzeneği:** bu oturumdaki betikler genişletilecek ([bench_common.py]({{artifact:8ab73c5a-c873-44e5-af4b-17fd5d7ed6bd}}), [bench_run.py]({{artifact:fbeda935-9d44-47ce-83df-06fd1e5fd722}}), [analysis.py]({{artifact:352fb02e-4552-4a22-8dce-7e46a2cd5f5b}}), [instrument.py]({{artifact:843ea5e4-0205-4c20-9ab7-1a2abd014937}}), [diag_mech.py]({{artifact:5ca01b77-dbd4-45d4-b722-5f3eb4e08688}})). `FairComparisonManifest` ve `NativeComparisonManifest`'e (`fairness.py:145`, `native_protocol.py:24`) bağlanacak. Referans kollar: LKH-3 ikilisi, GA-EAX, OR-Tools. | `academic_benchmark/` | Kollar katalog kapsamında koşuyor; sonuçlar sözleşme doğrulamasından geçiyor. |
| 0.7 | **Veri:** TSPLIB ATSP örnekleri (depoda yalnızca ft53 var), 1000–20 000 düğümlü simetrik örnekler, üretimden anonimleştirilmiş yönlü süre matrisleri | `academic_benchmark/tsplib_data` | Geliştirme ve test kümeleri ayrı tutuluyor. |
| 0.8 | **Ek sözleşme testleri** (çapraz kontrolden): (a) en iyi çözüm arşivi, enjeksiyon dahil her popülasyon değişikliğinden sonra güncellenir; (b) her yapılandırma alanı en az bir kod yolunu etkiler, etkilemiyorsa alan kaldırılır; (c) belgelenen her operatör (ör. RTR) uygulanmış ve kayıtlı. | `hybrid_tsp/tests/` | Üç test de CI'da geçiyor. Yeni kollar `registry_setup.py:473-477`'deki bilimsel protokol kapısından kesin amaç-değerlendirme muhasebesiyle geçiyor. |

**Karar deneyleri** (Faz 2'nin yönünü bunlar belirler):

- **D1 Yerel arama hızı:** 0.1'in kabul ölçütü. Hız kazancı küçük çıkarsa, Python katmanına geçmeden önce LKH'yi (elkai ya da LKH-3 ikilisi) yerel arama motoru olarak kullanma seçeneği değerlendirilir.
- **D2 Arazi taraması:** Örnek başına 50 ILS yerel optimumu üretilir. Ölçülecekler: çiftler arası bozuk çift mesafesi dağılımı; mesafeye karşı GPX2 bileşen sayısı ve GPX2 kazancı; mesafeye karşı OX+yerel arama ve kick+yerel arama kazancı. DAR-MA'nın hipotezi (H1, operatör başarısının mesafeye bağlı olması) burada sınanır. Etkileşim yoksa DAR-MA basitleştirilir.
- **D3 Δ dağılımı:** Kötüleşen hamlelerin Δ/maliyet dağılımı ölçülür; SA ve RRT eşikleri bununla kalibre edilir.

**Geçiş kapısı G0:** Tüm sözleşme testleri (0.8 dahil) geçiyor, D1 kabul ölçütü sağlanıyor, aşım ≤%5, sonuçlar belirlenimci ve kollar bilimsel protokol modunda kabul ediliyor.

### Faz 1: Üçlünün minimum onarımı ve ablasyonu (≈1,5 hafta)

Amaç bilimsel bir kapanış: orijinal fikir doğru uygulandığında bir değeri var mı? Onarılmış sürümler `v1.1` olarak hızlı yerel arama çekirdeğiyle koşturulur. Eski `SOTA-*` kimlikleri, geçmiş sonuçların yeniden üretilebilmesi için dondurulur.

- **E2BSO v1.1:**
  - entropiyi H_norm ile ölçekle;
  - INJECT'ten hemen sonra entropiyi yeniden hesapla;
  - `ia>ib` durumunda da kenarı ekle (`e2bso_tsp.py:194`);
  - LAHC'yi yörünge başına kur (`:89`, `:313`);
  - CPSO dalını kaldır (`:430`).
  - Ablasyon kolları: faz denetimi açık/kapalı; kenar zorlama ile GPX2 karşılaştırması.
- **R2DMA v1.1:**
  - rezonansın yerine bozuk çift mesafesi (n>200 kesimi kaldırılır, `r2dma_tsp.py:69, :81`);
  - mod eşiklerini D2'deki mesafe çeyreklerine göre belirle;
  - constructive modu GPX2 yap (`:291-299`);
  - perturb moduna yerel arama ekle (`:361`);
  - SA'yı D3'e göre kalibre et (`:111, :334`).
  - Ablasyon kolları: mod seçimi açık / rastgele mod.
- **P-AOEA v1.1:**
  - krediyi kayan pencereli oran yap (`paoea_tsp.py:49`);
  - ağırlıkları `ALNS_TSP._apply_weights` mantığıyla güncelle;
  - kabul genini krediye dahil et ya da çıkar;
  - evrim aralığını bütçenin %5'i yap (`:83`).
  - Ablasyon kolları: genom evrimi / bandit / uniform.

**Geçiş kapısı G1** (her algoritma için ayrı):

- (a) İmza mekanizması telemetride kararların ≥%5'inde aktif.
- (b) Mekanizma açık kol, kapalı koldan Holm-p<0,05 ile iyi.
- (c) Hızlı yerel aramalı ILS kontrolüne eşit sürede yenilmiyor.

(b) sağlanmazsa mekanizma Faz 2'ye taşınmaz.

### Faz 2: Yeni birleşimler (≈5 hafta; ayrıntılar §5'te)

Önerilen sıra:

1. EB-PXILS (1–1,5 hafta)
2. BB-Merge modülü (0,5 hafta)
3. DAR-MA (2 hafta; D2 olumluysa)
4. BA-LNS (1,5 hafta; TSP sürümü ve CVRPTW aktarımı)

EAX-MA ilk aşamada açık kaynak GA-EAX'in sarmalanmasıyla yalnızca referans kol olarak eklenir (1–2 gün). Yeniden yazımı ancak yayın hedefi gerektirirse yapılır (3–4 hafta).

**Geçiş kapısı G2:** Her yeni birleşim geliştirme kümesinde ILS kontrolünü eşit bütçede Holm-p<0,05 ile geçmeli. Her bileşen kendi ablasyonunda katkı göstermeli.

### Faz 3: Değerlendirme protokolü (≈1,5 hafta hesap süresi)

- **Örnekler:**
  - Geliştirme ve ayar kümesi: TSPLIB'den 100–1000 düğümlü ≈15 örnek.
  - Test kümesi: 1000–20 000 düğümlü ≈20 örnek ve bir alt küme National TSP.
  - TSPLIB ATSP örnekleri ve üretimden yönlü matrisler.
  - Ölçek eğrisi için üretilmiş düzgün ve kümeli örnekler.
- **Bütçe:**
  - Değerlendirme tabanlı bütçe (asıl sonuç) ve n'ye ölçekli duvar saati bütçesi (ikincil sonuç).
  - Her iki eksende anytime eğrileri: açık–değerlendirme ve açık–zaman.
- **Tohum:** Örnek başına ≥10 tohum; küçük örneklerde ≥20.
- **Ayar:** Bütün kollar, ILS kontrolü dahil, aynı irace bütçesiyle ayarlanır.
- **İstatistik:**
  - Eşleştirilmiş Wilcoxon + Holm, Friedman ve etki büyüklüğü ([Derrac vd. 2011](https://doi.org/10.1016/j.swevo.2011.02.002)).
  - Performans profilleri.
- **Deney uygulaması:** [Kendall vd. 2016](https://doi.org/10.1057/jors.2015.77) iyi uygulama kılavuzu izlenir.
  - Örnek özelliklerine göre alt grup analizi ([Kerschke vd. 2018](https://doi.org/10.1162/evco_a_00215)).
- **Referans kollar:**
  - LKH-3: sabit RUNS; ayrıca `RECOMBINATION = GPX2` koşusu.
  - GA-EAX: varsayılan p=300, r=30.
  - OR-Tools GLS.
  - Hızlı yerel aramalı ILS.

### Faz 4: Entegrasyon, adlandırma, yayın (≈1 hafta)

- **Adlandırma:** Yeni kimliklerde depo düzeni izlenir (örn. `Core-EBPXILS-TSP`, `Core-DARMA-TSP`, `Core-BALNS-TSP`); "SOTA" öneki kullanılmaz. `engine_core.py:16-21` içindeki kataloğa alınmamış liste yerine, kimlikler sözleşme doğrulamasıyla birlikte yönetilen kimlikler arasına (`registry_setup.py`) eklenir.
- **Üretim adaptörü:** Depo matrise alınmalı ve depoya bağlı açık yol amacı kullanılmalı. Sessiz yedek yol telemetriyle raporlanmalı. Mesafe ve süre tutarlı kullanılmalı (`sota_tsp_strategy_adapter.py:12-67`; ayrıntılar: [çapraz kontrol]({XC}) §3).
- **Yayın çerçevesi:** Mekanizmalar bileşen terimleriyle anlatılır ([Camacho‐Villalón vd. 2022](https://doi.org/10.1111/itor.13176)). Katkı iddiası bileşen ablasyonu ve ATSP sonuçlarına dayanır.

**Toplam:** ≈11–12 hafta. Faz 0 ve Faz 1 kendi başına yayımlanabilir bir "bileşen analizi" sonucu üretir.

## 5. Yeni birleşim önerileri

### Ö1: EB-PXILS (Entropi Dengeli, Bölüm Çaprazlamalı ILS), E2BSO'nun ardılı

**Fikir.** E2BSO'nun iki ana fikri korunuyor ama doğru organlarla: entropiyle dengeleme ve iyi çözümlerden kenar aktarma. Bir elit havuzun ve k bağımsız ILS yörüngesinin üzerinde çalışıyor:

```
her yörünge t: başlangıç turu (NN/greedy) + fast_LS
E ← elit havuz (m çözüm, klon yok)
bütçe bitene dek, her t için:
    eğer H_norm(E) ≥ h* ve rastgele < p_rec:
        c ← GPX2(t.mevcut, elit_seç(E))        # rekombinasyon
    değilse:
        c ← fast_LS(segment_double_bridge(t.mevcut))  # sarsım
    t.mevcut ← LAHC_t(c)                       # yörüngeye özgü geçmiş
    E ← güncelle(E, c)                          # klon reddi, en kötüyü çıkar
    eğer H_norm(E) < h_min: en kötü yarıyı yeniden başlat
```

**Neden işe yaraması bekleniyor:**
- Çekirdek, güçlü bir ILS (O1 + O2).
- GPX2'nin LK ya da LKH yerel optimumlarını iyileştirdiği gösterildi; anlamlı iyileşmeler büyük (n>5000) örneklerde belgelendi ([Tinós vd. 2020](https://doi.org/10.1162/evco_a_00254)). GPX ile LK hibriti GA da kanıtlanmış bir yapı ([Whitley vd. 2010](https://doi.org/10.1007/978-3-642-15844-5_57)).
- LKH aynı organı `RECOMBINATION = GPX2` seçeneğiyle sunuyor.

**Beklenti:**
- Küçük n'de ILS kontrolüne yakın, n≥1000'de daha iyi (orta güven).
- LKH'nin altında.

**Yenilik:** Düşük–orta. Entropiyle denetlenen rekombinasyon/sarsım dengesi küçük bir katkı.

**Ablasyon kolları:** GPX2 açık/kapalı; entropi denetimi ile sabit p_rec; LAHC ile "kötü değilse kabul".

**ATSP:** Or-opt ve or-3opt çekirdeği yönlü çalışır. GPX2 için 2n dönüşümü gerekir [DOĞRULANMADI: GPX2'nin ATSP üzerinde bu dönüşümle verimi].

### Ö2: EAX-MA (EAX memetik, entropi korumalı seçim), E2BSO entropisinin asıl yeri

**Fikir.** GA-EAX'in kendisi:
- 2-opt ile başlangıç popülasyonu;
- birinci aşamada EAX-Single, ikinci aşamada Block2;
- entropi korumalı hayatta kalan seçimi ([Nagata & Kobayashi 2013](https://doi.org/10.1287/ijoc.1120.0506)).

ATSP için EAX sürümü var ([Nagata & Soler 2012](https://doi.org/10.1016/j.eswa.2012.02.029)). EAX ile GPX2'yi birleştiren bir çalışma da mevcut ([Sanches vd. 2017](https://doi.org/10.1145/3071178.3071305)).

**Uygulama yolu:**
- Önce açık kaynak C++ kodunun sarmalanması: Nagata'nın GA-EAX deposu ve Apache 2.0 lisanslı GA-EAX-restart.
- Bu, değerlendirmede tavan kolu işlevi görür.
- Lisans ve yönlü örnek desteği kontrol edilmeli [DOĞRULANMADI].

**Beklenti:**
- Sadık bir uygulama EAX düzeyindedir.
- Yenilik yok.
- Üretim TSP alt problemleri küçükse üretim değeri düşük.

### Ö3: DAR-MA (Mesafe Uyarlamalı Rekombinasyonlu Memetik), R2DMA'nın ardılı ve en özgün aday

**Fikir.** R2DMA'nın "ebeveynlerin benzerliğine göre çaprazlama modu seç" fikri doğru ölçüyle ve doğru operatörlerle yeniden kuruluyor:

```
popülasyon ← fast_LS yerel optimumları
tekrarla:
    pA, pB ← yanlı uygunlukla ikili turnuva           (Vidal vd. 2012)
    d ← bozuk_çift_mesafesi(pA, pB)                  # döndürme/yön bağımsız
    b ← d_kutusu(d)                                  # D2'de bulunan çeyrekler, çevrimiçi güncellenir
    op ← bandit[b].seç({GPX2, EAX-Single | OX+LS, kick+LS, BB-Merge})
    c ← fast_LS(op(pA, pB))
    bandit[b].ödül(göreli iyileşme: c'nin en iyi ebeveyne göre kazancı)
    hayatta kalan seçimi: yanlı uygunluk, klon ayıklama
```

**Hipotez H1:** Operatör başarısı ebeveyn mesafesine bağlıdır. Beklenen örüntü şu:
- yakın ebeveynlerde GPX2 az bileşen bulur, kick ya da BB-Merge daha iyidir;
- orta mesafede GPX2 en verimlidir;
- uzak ebeveynlerde EAX ya da OX+yerel arama daha iyidir.

H1, D2'de inşaattan önce sınanır.

**Neden işe yaraması bekleniyor:**
- TSP arazisinin çok hunili yapısı ([Ochoa & Veerapen](https://doi.org/10.1007/s10732-017-9334-0); [Hains vd. 2011](https://doi.org/10.1057/jors.2010.116)), tek bir rekombinasyonun her mesafede eşit derecede yararlı olmayacağına işaret ediyor.
- GPX tabanlı karıştırmalı GA ile EAX'i bir toplulukta birleştirmenin zor örneklerde iyi çalıştığı gösterildi ([Varadarajan & Whitley 2021](https://doi.org/10.1145/3449639.3459281)).

**Yenilik:** En yakın önceki çalışmalar şunlar:
- MGA/GPX ile EAX topluluğu ([Varadarajan & Whitley 2021](https://doi.org/10.1145/3449639.3459281));
- yerel optimum korelasyonuna dayalı operatör seçimi ([Pei vd. 2023](https://doi.org/10.1145/3583131.3590399));
- GPX'in genelleştirilmesi olan DPX ([Chicano vd. 2021](https://doi.org/10.1162/evco_a_00305)).

Bu oturumdaki OpenAlex taramasında, ebeveyn mesafesini bağlam alan bir bandit ile GPX2, EAX ve sarsım arasında seçim yapan bir çalışma görülmedi. Yine de yenilik iddiası yayından önce odaklı bir literatür taramasıyla doğrulanmalı [DOĞRULANMADI].

**Beklenti:** H1 doğrulanırsa EB-PXILS'ten iyi olması beklenir (düşük–orta güven). H1 doğrulanmazsa algoritma "GPX2 + yanlı uygunluk memetiği"ne indirgenir.

### Ö4: BA-LNS (Bandit Uyarlamalı LNS), P-AOEA'nın ardılı ve üretime en kolay aktarılan

**Bileşenler:**
- Yok etme: rastgele, en kötü, ilişkili (Shaw), string removal ([SISR](https://doi.org/10.1287/trsc.2019.0914)).
- Onarma: açgözlü, regret-2/3, blink açgözlü.
- Her onarımdan sonra hızlı yerel arama.
- Kabul: D3'e göre kalibre SA ya da RRT.
- Operatör seçimi: FRR-MAB, Ropke–Pisinger roulette ve uniform kolları birbiriyle yarışır.
- Genom popülasyonu yalnızca operatör seçimi uniform'u geçerse eklenir.

**Neden işe yaraması bekleniyor:**
- TSP'de ALNS k-opt yerel aramadan zayıf. Bu yüzden TSP'de beklenti ILS düzeyi.
- Asıl değeri VRP'de: SISR kapasite ve zaman penceresi kısıtlı VRP'lerde güçlü sonuçlar veriyor ([Christiaens & Vanden Berghe 2020](https://doi.org/10.1287/trsc.2019.0914)).
- Uyarlamanın katkısı küçük beklenmeli ([Turkeš vd. 2021](https://doi.org/10.1016/j.ejor.2020.10.045)); plan bunu uniform kolla zaten sınıyor.

**Üretim aktarımı:**
- Aynı operatörler, Sw/So havuz kapasiteleri ve heterojen filo ile CVRPTW'ye taşınır.
- Kıyas, depodaki PyVRP (HGS) stratejisine karşı yapılır ([Wouda vd. 2024](https://doi.org/10.1287/ijoc.2023.0055); [Vidal 2022](https://doi.org/10.1016/j.cor.2021.105643)).
- PyVRP'nin çok boyutlu yükle Sw/So havuzlarını doğrudan modelleyip modelleyemediği kontrol edilmeli [DOĞRULANMADI].

### Ö5: BB-Merge (backbone sabitleme ve yoğun yeniden optimizasyon), R2DMA "constructive" modunun doğru biçimi

**Fikir:**
1. Elit havuzdaki çözümlerin hepsinde ortak olan kenarlar sabitlenir.
2. Sabit zincirler daraltılarak küçük bir problem elde edilir.
3. Bu küçük problem yoğun bir yerel aramayla yeniden optimize edilir: or-3opt, depodaki yönlü/simetrik `three_opt.py` ya da LKH.

**Dayanaklar:**
- Bu, LKH'nin tur birleştirme fikrinin ve Cook–Seymour yaklaşımının hafif bir sürümü ([Cook & Seymour 2003](https://doi.org/10.1287/ijoc.15.3.233.16078)).
- Yakın tarihli bir ön baskı, MAB ve dinamik backbone bilgisinin LKH'yi iyileştirdiğini bildiriyor (Wang vd. 2025, arXiv:2501.04072; hakemli değil).

**Kullanım:** Ö1 ve Ö3 içinde yoğunlaştırma modülü olarak, kendi ablasyon koluyla.

### Beklenti tablosu

| Tasarım | Eşit bütçede ILS kontrolüne göre beklenti | LKH/EAX'e göre beklenti | Yenilik | Çaba | Üretim değeri |
|---|---|---|---|---|---|
| EB-PXILS | Küçük n'de ≈, n≥1000'de iyi (orta güven) | Altında | Düşük–orta | 1–1,5 hafta | Orta |
| EAX-MA | Belirgin biçimde iyi (yüksek güven) | Tasarım gereği EAX düzeyi | Yok | 1–2 gün (sarmalama) / 3–4 hafta (yazım) | Düşük |
| DAR-MA | H1 doğrulanırsa EB-PXILS'ten iyi (düşük–orta güven) | Altında olması muhtemel | En yüksek | 2 hafta | Orta |
| BA-LNS | TSP'de ≈ | Altında | Düşük | 1,5 hafta | **Yüksek** (CVRPTW) |
| BB-Merge | Modül olarak büyük n'de katkı (orta güven) | n/a | Düşük | 0,5 hafta | Orta |

## 6. Eski bileşenlerin akıbeti

| Bileşen | Karar | Nereye |
|---|---|---|
| E2BSO entropisi (`log2(P·n)`) | Düzelt | H_norm; EB-PXILS denetimi |
| E2BSO üç fazlı denetim | v1.1 ablasyonuna bağlı | Katkı yoksa entropi korumalı seçimle değiştirilir |
| E2BSO kenar zorlama ("sürü") | Değiştir | GPX2 |
| E2BSO CPSO dalı | Kaldır | — |
| Ortak LAHC (E2BSO, P-AOEA) | Düzelt | Yörünge başına LAHC |
| R2DMA 6 boyutlu rezonans | Değiştir | Bozuk çift mesafesi |
| R2DMA constructive çaprazlama | Değiştir | GPX2 / BB-Merge |
| R2DMA yerel aramasız perturb modu | Kaldır | kick + yerel arama |
| R2DMA OX (moderate) | Koru | DAR-MA'da yedek operatör (OX + yerel arama) |
| R2DMA ve P-AOEA SA (T₀=0,4·C) | Kalibre et | D3 |
| P-AOEA genom evrimi | Değiştir | Bandit operatör seçimi (genom yalnızca uniform'u geçerse) |
| P-AOEA yok etme/onarma ağırlıkları | Düzelt | `ALNS_TSP._apply_weights` mantığı |
| `utils.compute_population_diversity` | Düzelt | Rastgele örnek ya da tüm çiftler |
| `ls_engine.MultiLayerLS` | Referans olarak koru | `fast_ls.py` |

## 7. Riskler ve açık sorular

- **ATSP:** GPX2 simetrik TSP için tanımlı; ATSP'de 2n dönüşümüyle verimi doğrulanmalı [DOĞRULANMADI]. Bu doğrulanana kadar ATSP'de rekombinasyon olarak EAX (Nagata & Soler 2012) ya da BB-Merge kullanılabilir.
- **LKH erişimi:** elkai, LKH parametrelerinin hepsini açmıyor olabilir [DOĞRULANMADI]. `RECOMBINATION = GPX2` için LKH-3 ikilisi gerekebilir.
- **Numba:** Windows'ta derleme süresi ve önbellek davranışı ölçülmeli (bu oturumda `NUMBA_CACHE_DIR` ile çalışıldı).
- **Üretim önceliği:** Üretimde araç başına durak sayısı küçükse (onlarca), TSP alt problemleri LKH/elkai ile milisaniyede optimuma yakın çözülür. Bu durumda TSP hattındaki yenilik akademik değer taşır; üretim kazancı VRP düzeyinden (BA-LNS, PyVRP) gelir. Bu, üretim rota boyutu dağılımıyla doğrulanmalı.
- **Güncel referanslar:** LKH hızlandırması ([Ammann vd. 2026](https://doi.org/10.1016/j.cor.2026.107443)) ve EAX'te AB-döngü analizi (Heins, Whitley, Kerschke 2025, arXiv:2505.00803) referans kol seçiminde dikkate alınmalı. ATSP yerel araması için [Kanellakis & Papadimitriou 1980](https://doi.org/10.1287/opre.28.5.1086) dayanak alınmalı.
- **Yenilik:** DAR-MA ve EB-PXILS için yayın öncesinde odaklı bir literatür kontrolü gerekli.

## 8. İlk iki hafta için somut adımlar

1. `hybrid_tsp/` iskeletini ve sözleşme testlerini yaz; testler başta başarısız olabilir.
2. `fast_ls.py`: aday listesi, don't-look bit, 2-opt ve Or-opt. Ardından or-3opt'u yönlü olarak ekle.
3. ILS kontrolünü `fast_ls` ile yeniden kur; D1'i a280 ve pr1002 üzerinde ölç.
4. `diversity.py` ve GPX2'yi yaz; GPX2 sözleşme testlerini geçir.
5. D2 ve D3'ü 6 geliştirme örneğinde koştur ve H1 kararını ver.
6. G0 raporunu yaz; Faz 1 ile Faz 2 sırasını kesinleştir.

## Kaynaklar

DOI'lerin hepsi bu oturumda CrossRef'te çözümlendi. arXiv ön baskıları ayrıca belirtildi.

- Applegate, Cook, Rohe (2003). Chained Lin-Kernighan for Large Traveling Salesman Problems. *INFORMS J. Computing*. https://doi.org/10.1287/ijoc.15.1.82.15157
- Aranha vd. (2021). Metaphor-based metaheuristics, a call for action: the elephant in the room. *Swarm Intelligence*. https://doi.org/10.1007/s11721-021-00202-9
- Bentley (1992). Fast Algorithms for Geometric Traveling Salesman Problems. *ORSA J. Computing*. https://doi.org/10.1287/ijoc.4.4.387
- Boese, Kahng, Muddu (1994). A new adaptive multi-start technique for combinatorial global optimizations. *Operations Research Letters*. https://doi.org/10.1016/0167-6377%2894%2990065-5
- Burke, Bykov (2017). The late acceptance Hill-Climbing heuristic. *EJOR*. https://doi.org/10.1016/j.ejor.2016.07.012
- Camacho‐Villalón, Dorigo, Stützle (2022). Exposing the grey wolf, moth‐flame, whale, firefly, bat, and antlion algorithms. *ITOR*. https://doi.org/10.1111/itor.13176
- Chicano, Ochoa, Whitley, Tinós (2021). Dynastic Potential Crossover Operator. *Evolutionary Computation*. https://doi.org/10.1162/evco_a_00305
- Christiaens, Vanden Berghe (2020). Slack Induction by String Removals for Vehicle Routing Problems. *Transportation Science*. https://doi.org/10.1287/trsc.2019.0914
- Cook, Seymour (2003). Tour Merging via Branch-Decomposition. *INFORMS J. Computing*. https://doi.org/10.1287/ijoc.15.3.233.16078
- Derrac vd. (2011). A practical tutorial on the use of nonparametric statistical tests... *Swarm and Evolutionary Computation*. https://doi.org/10.1016/j.swevo.2011.02.002
- Fialho vd. (2010). Analyzing bandit-based adaptive operator selection mechanisms. *Annals of Mathematics and AI*. https://doi.org/10.1007/s10472-010-9213-y
- Franzin, Stützle (2019). Revisiting simulated annealing: A component-based analysis. *Computers & OR*. https://doi.org/10.1016/j.cor.2018.12.015
- Gómez (2004). Self Adaptation of Operator Rates in Evolutionary Algorithms. *LNCS*. https://doi.org/10.1007/978-3-540-24854-5_113
- Hains, Whitley, Howe (2011). Revisiting the big valley search space structure in the TSP. *J. Operational Research Society*. https://doi.org/10.1057/jors.2010.116
- Helsgaun (2000). An effective implementation of the Lin–Kernighan traveling salesman heuristic. *EJOR*. https://doi.org/10.1016/s0377-2217%2899%2900284-2
- Helsgaun (2009). General k-opt submoves for the Lin–Kernighan TSP heuristic. *Math. Programming Computation*. https://doi.org/10.1007/s12532-009-0004-6
- Johnson (1990). Local optimization and the Traveling Salesman Problem. *LNCS (ICALP)*. https://doi.org/10.1007/bfb0032050
- Kerschke vd. (2018). Leveraging TSP Solver Complementarity through Machine Learning. *Evolutionary Computation*. https://doi.org/10.1162/evco_a_00215
- Kirkpatrick, Gelatt, Vecchi (1983). Optimization by Simulated Annealing. *Science*. https://doi.org/10.1126/science.220.4598.671
- Li, Fialho, Kwong, Zhang (2014). Adaptive Operator Selection With Bandits for a Multiobjective Evolutionary Algorithm Based on Decomposition. *IEEE TEVC*. https://doi.org/10.1109/tevc.2013.2239648
- Lin, Kernighan (1973). An Effective Heuristic Algorithm for the Traveling-Salesman Problem. *Operations Research*. https://doi.org/10.1287/opre.21.2.498
- López-Ibáñez vd. (2016). The irace package: Iterated racing for automatic algorithm configuration. *Operations Research Perspectives*. https://doi.org/10.1016/j.orp.2016.09.002
- Lourenço, Martin, Stützle. Iterated Local Search. *Handbook of Metaheuristics*. https://doi.org/10.1007/0-306-48056-5_11
- Nagata (2006). Fast EAX Algorithm Considering Population Diversity for TSPs. *LNCS*. https://doi.org/10.1007/11730095_15
- Nagata, Soler (2012). A new genetic algorithm for the asymmetric traveling salesman problem. *Expert Systems with Applications*. https://doi.org/10.1016/j.eswa.2012.02.029
- Nagata, Kobayashi (2013). A Powerful Genetic Algorithm Using Edge Assembly Crossover for the TSP. *INFORMS J. Computing*. https://doi.org/10.1287/ijoc.1120.0506
- Nagata (2020). High-Order Entropy-Based Population Diversity Measures in the TSP. *Evolutionary Computation*. https://doi.org/10.1162/evco_a_00268
- Ochoa, Veerapen (CrossRef: 2017). Mapping the global structure of TSP fitness landscapes. *J. Heuristics*. https://doi.org/10.1007/s10732-017-9334-0
- Pei vd. (2023). Local Optima Correlation Assisted Adaptive Operator Selection. *GECCO*. https://doi.org/10.1145/3583131.3590399
- Ropke, Pisinger (2006). An Adaptive Large Neighborhood Search Heuristic for the PDPTW. *Transportation Science*. https://doi.org/10.1287/trsc.1050.0135
- Sanches, Whitley, Tinós (2017). Building a better heuristic for the TSP: combining edge assembly crossover and partition crossover. *GECCO*. https://doi.org/10.1145/3071178.3071305
- Sörensen (CrossRef: 2013). Metaheuristics—the metaphor exposed. *ITOR*. https://doi.org/10.1111/itor.12001
- Stützle, López-Ibáñez (CrossRef: 2018). Automated Design of Metaheuristic Algorithms. *Handbook of Metaheuristics*. https://doi.org/10.1007/978-3-319-91086-4_17
- Tinós, Whitley, Ochoa (2020). A New Generalized Partition Crossover for the TSP: Tunneling Between Local Optima. *Evolutionary Computation*. https://doi.org/10.1162/evco_a_00254
- Turkeš, Sörensen, Hvattum (2021). Meta-analysis of metaheuristics: Quantifying the effect of adaptiveness in ALNS. *EJOR*. https://doi.org/10.1016/j.ejor.2020.10.045
- Varadarajan, Whitley (2021). A parallel ensemble genetic algorithm for the traveling salesman problem. *GECCO*. https://doi.org/10.1145/3449639.3459281
- Vidal vd. (2012). A Hybrid Genetic Algorithm for Multidepot and Periodic VRPs. *Operations Research*. https://doi.org/10.1287/opre.1120.1048
- Vidal (2022). Hybrid genetic search for the CVRP: Open-source implementation and SWAP* neighborhood. *Computers & OR*. https://doi.org/10.1016/j.cor.2021.105643
- Wang, Zheng, Xiong, He (2025). Multi-armed Bandit and Backbone boost Lin-Kernighan-Helsgaun Algorithm for the TSP. arXiv:2501.04072 (ön baskı). https://doi.org/10.48550/arxiv.2501.04072
- Whitley, Hains, Howe (2009). Tunneling between optima: partition crossover for the TSP. *GECCO*. https://doi.org/10.1145/1569901.1570026
- Whitley, Hains, Howe (2010). A Hybrid Genetic Algorithm for the TSP Using Generalized Partition Crossover. *PPSN XI*. https://doi.org/10.1007/978-3-642-15844-5_57
- Wouda, Lan, Kool (2024). PyVRP: A High-Performance VRP Solver Package. *INFORMS J. Computing*. https://doi.org/10.1287/ijoc.2023.0055

- Ammann, Ostermann, Stiller, de Wolff (2026). A speed-up for Helsgaun's TSP heuristic by relaxing the positive gain criterion. *Computers & OR*. https://doi.org/10.1016/j.cor.2026.107443
- Heins, Whitley, Kerschke (2025). To Repair or Not to Repair? Investigating the Importance of AB-Cycles for the State-of-the-Art TSP Heuristic EAX. arXiv:2505.00803 (ön baskı).
- Kanellakis, Papadimitriou (1980). Local Search for the Asymmetric Traveling Salesman Problem. *Operations Research*. https://doi.org/10.1287/opre.28.5.1086
- Kendall vd. (2016). Good Laboratory Practice for optimization research. *J. Operational Research Society*. https://doi.org/10.1057/jors.2015.77

**Yazılım:**
- LKH-2/LKH-3, Keld Helsgaun: http://akira.ruc.dk/~keld/research/LKH/ ve http://akira.ruc.dk/~keld/research/LKH-3/
- GA-EAX: https://github.com/nagata-yuichi/GA-EAX
- GA-EAX-restart (Apache 2.0): https://github.com/senshineL/GA-EAX-restart
