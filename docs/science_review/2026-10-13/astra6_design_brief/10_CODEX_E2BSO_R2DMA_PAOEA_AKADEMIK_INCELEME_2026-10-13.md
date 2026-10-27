# E2BSO, R2DMA ve P-AOEA: kod ve akademik geçerlilik incelemesi

Yazar: **Codex**. İnceleme tarihi: **13 Ekim 2026**. İncelenen commit: `de608fd48f13502d5011066cc8d7e86cfe6e6d44`.

## Karar

**Bu üç yöntem şu an akademik olarak “kanıtlanmış SOTA” diye sunulamaz.** Üçü de çalıştırılabilir, bilinen arama bileşenlerini birleştiren deneysel yöntemlerdir. Küçük örneklerde geçerli tur ve doğru maliyet üretmeleri doğrulandı; fakat isimlerini veren mekanizmaların bazıları tarif edildiği biçimde çalışmıyor. Ayrıca güçlü literatür karşılaştırmaları, bileşen katkı deneyleri ve bilimsel bütçe muhasebesi olmadan performans üstünlüğü çıkarılamaz.

| Yöntem | Gerçekte uygulanan yaklaşım | Mantık/uygulama değerlendirmesi | Akademik konumlandırma |
|---|---|---|---|
| E2BSO | Kenar temelli yönlendirme, entropi eşikleri, destroy/repair, yerel arama ve geçmiş eşikli kabul içeren popülasyon sezgiseli | Temel arama çalışıyor; çeşitlilik normalizasyonu, kenar zorlama ve ATSP yön bilgisi sorunlu | Entropi kontrollü **deneysel memetik sezgisel**; SOTA kanıtı yok |
| R2DMA | Altı bileşenli benzerlikle eş seçimi, eşikli çaprazlama/pertürbasyon, yerel arama ve SA | Temel arama çalışıyor; düşük benzerlik dalı varsayılan eşikle gölgeleniyor; benzerlik ve yapıcı çaprazlama tasarımı gerekçelendirilmemiş | Benzerlik güdümlü **deneysel evrimsel/LNS hibriti**; SOTA kanıtı yok |
| P-AOEA | Rotalardan ayrı bir operatör-genomu havuzu, kalıtım/mutasyon, destroy/repair ve yerel arama | Genom havuzu gerçekten evriliyor; ancak bazı ayarlar etkisiz, turnuva seçimi uygulanmıyor, biriken başarı sayısı maruziyetle karışıyor | **Deneysel operatör seçimi hiper-sezgiseli**; SOTA kanıtı yok |

“SOTA kanıtı yok” ifadesi “kesinlikle kötü sonuç verir” veya “özgün katkı mümkün değil” anlamına gelmez. Buradaki olumsuz karar, mevcut mekanizma ve kanıtların bu güçlü iddiayı taşımamasına ilişkindir.

## Kapsam ve yöntem

`AGENTS.md`, bilimsel adalet/birleştirme sözleşmeleri, üç çekirdek dosya, ortak yerel arama, kayıt/yürütme yolu, üretim adaptörü ve ilgili testler incelendi. CodeGraph indeksi güncellendi. Değerlendirme kod düzeltmesi içermiyor; mevcut başka yazar raporları bağımsız kanıt sayılmadı. E2BSO-CPSO ayrı bir varyanttır: aşağıdaki kenar-zorlama bulguları ona otomatik olarak aktarılmamalıdır.

İki tür doğrulama yapıldı:

1. Kurulu Numba ortamında mevcut dört test dosyası: **40 passed in 11.99s**.
2. Mekanizma odaklı Python fallback probları ve küçük, gerçek çözücü çalıştırmaları. Bazı problarda yalnız belirli kontrol akışını izole etmek için operatörler kontrollü olarak değiştirildi; bunlar performans deneyi değildir. Ayrıca değiştirilmemiş çözücüler iki adet 7 düğümlü matris üzerinde üç tohumla, her yapılandırma iki kez çalıştırıldı: **18 yapılandırma, 36 solve çağrısı**.

Tekrarlanabilir prob: [probe.py](science_review/2026-10-13/codex_trio_evidence/probe.py). Tam gözlemler: [probe-results.json](science_review/2026-10-13/codex_trio_evidence/probe-results.json). Bu prob kaynak kodunu değiştirmez; mekanizma incelemesinde Numba importunu bilinçli olarak kapatır. Numba doğrulaması ayrı mevcut test koşusudur.

## Önce düzeltilmesi gereken doğrulanmış davranışlar

### 1. Üç yöntem de son çeşitlilik enjeksiyonunda bulduğu daha iyi çözümü kaybedebiliyor

Üç döngüde de `gbest` güncellemesi, periyodik çeşitlilik enjeksiyonundan **önce** yapılıyor. Enjeksiyon daha ucuz bir tur üretirse ve bu son iterasyonsa, yeni maliyet tekrar en iyi çözümle karşılaştırılmıyor. Son cilalama da eski `gbest` üzerinde çalışıyor; enjeksiyonla bulunan çözümü geri kazanma garantisi yok.

Kanıt: `uniride_core/algorithms/sota_tsp/e2bso_tsp.py:307-319`, `r2dma_tsp.py:407-429`, `paoea_tsp.py:277-289`.

Kontrollü `S1_last_injection_lost` probunda, üç yöntemde de mevcut tur maliyeti **302**, enjeksiyonun ürettiği tur **5**, döndürülen sonuç **302** oldu. Prob diğer arama hamlelerini etkisizleştirip son enjeksiyonu izole eder; gerçek problemde bu hatanın sıklığını ölçmez. Sorun yalnız son turda da değildir: daha iyi enjekte edilmiş birey sonraki turda bozulursa, hiç arşivlenmeden kaybolabilir.

**En küçük düzeltme:** Enjeksiyon dahil her popülasyon değişiminden sonra en iyi çözüm arşivini güncellemek; E2BSO'da bireysel en iyileri de tutarlı güncellemek. “Bulunan en iyi çözüm döndürülür” sözleşmesi için regresyon testi eklemek.

### 2. E2BSO entropisi, çökmüş popülasyonu düşük çeşitlilik olarak tanımayabiliyor

Kod, bütün popülasyondaki yönsüz kenar frekanslarını `P*n` toplamına bölüyor, Shannon entropisini hesaplıyor ve `log2(P*n)` ile normalize ediyor. Bu geçerli bir kenar-dağılımı entropisidir; fakat popülasyonlar arası çeşitlilik için kullanılan eşiklerin ölçeği uygun değildir.

`n>=3` için aynı turun `P` kopyasında hesaplanan değer:

`H_identical = log(n) / log(P*n)`.

| Tamamen aynı turlar | Ölçülen entropi |
|---|---:|
| n=50, P=40 | 0.5146787538 |
| n=1000, P=40 | 0.6518819845 |
| n=50, P=80 | 0.4716662156 |

Varsayılan ilk düşük-entropi eşiği `h_start*0.5 = 0.4`. Dolayısıyla ilk iki tamamen tekdüze popülasyon ilk kontrolde INJECT'e girmiyor. Aynı popülasyonun kopya sayısını değiştirmek de ölçüyü değiştiriyor. Öğrenme döneminden sonra eşikler soğutulurken bu taban entropisi ayrıca önem kazanıyor.

Kanıt: `e2bso_tsp.py:112-132, 252-280`; prob `E1_identical_entropy`. Ayrı `compute_population_diversity` kontrolü her 50 iterasyonda enjeksiyon yapabildiği için “hiç çeşitlilik enjeksiyonu yok” demek yanlış olur (`:316-319`).

**En küçük düzeltme:** Önce ölçünün beklenen değişmezlerini tanımlamak: özdeş turlarda sıfır, kopyalama ile değişmeme, problem boyutları arasında anlamlı ölçek. Kenar görülme olasılığı veya uygun taban/maksimum normalizasyonu seçip eşikleri yeniden kalibre etmek. Yalnız eşik sayısını değiştirmek genel çözüm değildir.

### 3. E2BSO kenar zorlama işlemi eksik; ATSP'de iyi turun ters yönünü ayırt etmiyor

İlk sorun `ia < ib` koşulu: seçilen, henüz mevcut olmayan `(a,b)` kenarında `a` turda `b`'den sonra geliyorsa hiçbir hamle yapılmıyor. Örneğin `[3,2,1,0,4]` turuna `(0,2)` kenarı zorlandığında tur aynı kalıyor. Bu, kenar-zorlama işleminin bazı geçerli durumlarda etkisiz olduğunu gösterir; bütün swarm adımlarının etkisiz olduğu anlamına gelmez.

İkinci sorun, hem hedef hem birey kenarlarının `(min(a,b),max(a,b))` biçiminde tutulması. Yönlü bir çevrim ile tersi aynı kenar kümesi sayılıyor. Kontrollü ATSP'de ileri tur maliyeti **5**, ters tur maliyeti **500** iken doğrudan iyi hedefe yönlendirme ters turu hiç değiştirmedi. Ortak yerel arama yine iyileştirebilir; sorun maliyet hesabında değil, swarm bilgisinin yönü kaybetmesinde.

Kanıt: `e2bso_tsp.py:176-198`; problar `E2_force_edge_02`, `E3_ATSP_direction`. Ortak çeşitlilik yardımcı fonksiyonu da yönsüz kenar kullanır: `uniride_core/algorithms/utils.py:26-32`.

**En küçük düzeltme:** Konumların iki sırası için de doğru kenar ekleme hamlesi; ATSP'de yönlü yay kümeleri ve yönü koruyan yeniden bağlama. STSP ve ATSP davranışını ayrı test etmek.

### 4. R2DMA'nın düşük rezonanslı destroy/repair dalı varsayılan eşikle gölgeleniyor

Belge `R<0.3` için DESTRUCTIVE der. Kod önce `best_resonance < theta` koşulunu kontrol edip `perturb` yapıyor; `theta_base=0.5`. Bu nedenle başlangıçta `R<0.3` olan bütün çiftler destroy/repair yerine takasa gidiyor. Ana döngüde destructive dalına ulaşmak için `theta<0.3` ve `theta<=R<0.3` gerekir.

Varsayılan `segment_size=50`, adım `0.05` ve başlangıç `0.5` ile, her uygun güncelleme eşiği düşürse bile beş azaltım gerekir; en erken 250. iterasyon sonrasında bu aralık açılır. Başarı şartı sağlanmazsa daha geç açılır veya hiç açılmaz. Bu hesap periyodik çeşitlilik darbesini kapsamaz: o yol ayrıca destroy/repair çağırabilir.

`R4_low_resonance_branch` probunda `R=0.1`, `theta=0.5`, dört birey ve bir iterasyon için **4 perturb, 0 destructive** çağrısı görüldü.

Kanıt: `r2dma_tsp.py:15-20, 103-104, 346-374, 414-429`.

**En küçük düzeltme:** Tasarımın gerçekten üç rezonans bölgesi mi, yoksa önce eş seçimini reddeden ayrı bir filtre mi olduğunu belirlemek; koşul sırasını veya bilimsel tanımı buna uydurmak. Her dalın ziyaret sayısını raporlamak. Mevcut `destructive` sayacı çeşitlilik darbelerini saymadığından toplam destroy/repair kullanımı olarak okunmamalı.

### 5. P-AOEA'nın bazı ayarları ve tarif edilen mekanizmaları uygulamayla uyuşmuyor

| Alan/iddia | Gerçek durum | Kanıt |
|---|---|---|
| `remove_ratio_range` | Config'te var; çözüm döngüsü sabit `0.30 → 0.10` çizelgesi kullanıyor | `paoea_tsp.py:93, 257-259` |
| `tournament_size` ve “tournament selection” | Config/docstring'te var; evrim fitness sıralaması ve üst yarıdan rastgele iki ebeveyn seçimi yapıyor | `:10, 84, 190-215` |
| `genome_injection_rate` | Tanımlı; genom evriminde kullanılmıyor | `:87, 190-215` |
| SA/LAHC/**RTR** | Varsayılan türler SA/LAHC; çalıştırıcıda SA dışındaki her değer LAHC koluna gidiyor; ayrı RTR yok | `:13, 90, 264-267` |

`remove_ratio_range=(0.8,0.9)` verilerek yapılan iki iterasyonlu probda uygulanan oranlar yine **0.2 ve 0.1** oldu (`P1_ignored_remove_range`). Etkisiz parametreler üzerinde tuning yapmak bilimsel olarak farklı algoritma ayarlarını karşılaştırmış olmaz.

**En küçük düzeltme:** Desteklenen ayarları gerçekten kullanmak veya etkisiz alanları deney alanından kaldırmak; seçimin adını doğru vermek; RTR'yi uygulanmadığı halde destekleniyor göstermemek. Burada genom evrimi tümden yok değildir: seçme, çaprazlama ve mutasyon kodu vardır.

## Tasarım ve akademik tanım açısından düzeltilmesi gereken noktalar

### 6. R2DMA rezonansı aynı çevrime değişken puan veriyor; yapıcı işlem ortak yapıyı tam korumuyor

Pozisyon terimi `n>200` olduğunda sıfıra kesiliyor. Bir turun kendisiyle rezonansı, birim maliyetli örneklerde `n=200` için **1.0**, `n=201` için **0.85**. Diğer beş terimin ağırlıkları yeniden normalize edilmiyor. Ayrıca yalnız pozisyon bileşeni rotasyona göre normalize edilmiş: mesafe profili ve sıralama yaklaşımı tüm skorun rotasyon değişmezliğini sağlamıyor. Altı düğümlü aynı maliyetli çevrim/rotasyonu için skor **1.0 → 0.904375**, her iki maliyet **96** çıktı.

Kanıt: `r2dma_tsp.py:67-96, 169-226`; problar `R2_identity_score_cutoff`, `R3_rotation`.

Yapıcı çaprazlama ortak kenarları karıştırıp uçlarını listeye ekliyor; oluşturulan komşuluk sözlüğü daha sonra izlenmiyor. On düğümlü **özdeş iki ebeveyn** ve seed 42 için çocuk ortak on kenarın yalnız **yedisini** korudu (`R1_identical_parent_crossover`; `:271-301`). Bu geçerli bir permütasyondur; tek başına hatalı çözüm değildir. Ancak “yapıcı birleşim, ortak iyi parçaları koruyor” şeklindeki güçlü bir yorum desteklenmez.

**Öneri:** Yönlü/yönsüz problem için uygun standart kenar uzaklığıyla karşılaştırmak; bileşenleri ve ağırlıkları ablation ile sınamak; rotasyon ve boyut eşiği davranışlarını açık tanımlamak. Çaprazlamanın ortak parçaları koruması hedefleniyorsa adjacency bilgisini gerçekten kullanan bir birleştirme gerekir.

### 7. P-AOEA fitness'ı, operatör kalitesi ile kaç kez denendiğini karıştırıyor

Her iyileştirme `fitness += 1` yapıyor. `success_rate()` mevcut olduğu halde genom sıralamasında kullanılmıyor. Elit genom nesneleri kopyalanmadan yeni havuza taşındığı için biriken fitness ve deneme sayıları sıfırlanmıyor; yeni çocuklar sıfırdan başlıyor. Bireylere genom ataması rastgele olduğundan deneme sayıları da eşit olmak zorunda değil.

Probda 100 denemede 10 başarı sağlayan genom, 10 denemede 9 başarı sağlayanın önüne geçti; evrimden sonra eski 100 deneme ve 10 fitness korundu. Kanıt: `paoea_tsp.py:38-49, 190-215, 255-284`; `P2_fitness_lifetime`.

Bu seçim matematiksel olarak tanımlıdır; fakat “başarılı operatörleri uyarlamalı öğrenme” iddiasını tek başına karşılamaz. Yaşam boyu toplam başarı, güncel koşullu başarı, iyileştirme büyüklüğü ve harcanan süre farklı hedeflerdir. Hangi hedefin optimize edildiği açıklanmalı; eşit denemeli veya kayan pencereli kredi atamasıyla karşılaştırılmalıdır. İlgili literatür: [Fialho ve ark., adaptif operatör seçimi](https://doi.org/10.1007/s10472-010-9213-y).

### 8. LAHC etiketi, popülasyon için değiştirilmiş kabul kuralı olarak açıklanmalı

E2BSO geçmişi sonsuz değerlerle başlatıyor ve her iterasyonda global en iyi maliyeti yazıyor; P-AOEA da ortak geçmişe popülasyon minimumunu yazıyor. Bireyin kendi önceki maliyet izi tutulmuyor. Dolu olmayan geçmiş yuvalarında kötüleşen adaylar da kabul edilebiliyor.

Kanıt: `e2bso_tsp.py:87-103, 252, 298-313`; `paoea_tsp.py:108-122, 252, 264-275`. Literatürde LAHC, adayın aramanın geçmiş maliyetiyle karşılaştırılması üzerinden tanımlanır. Bu popülasyon uyarlaması ayrıca açıklanıp sınanmalıdır; standart LAHC'nin birebir uygulanışı diye aktarılmamalıdır. [Burke ve Bykov, 2017](https://www.sciencedirect.com/science/article/pii/S0377221716305495).

### 9. Zaman ve bütçe sınırları bilimsel karşılaştırma için yeterli değil

Üç çözücü süreyi başlatmadan sonra her neslin sonunda kontrol ediyor. Ortak `MultiLayerLS` süreyi katmanlar arasında kontrol ediyor; başlayan bir katmanın iç taramasını aynı son tarihle kesmiyor. Dolayısıyla süre parametresi katı, kesintisiz bir duvar saati üst sınırı gibi yorumlanamaz. Bu incelemede büyük örnekler için aşım miktarı ölçülmedi.

Kanıt: `e2bso_tsp.py:243, 290-322`; `r2dma_tsp.py:327, 342-433`; `paoea_tsp.py:242, 257-293`; `ls_engine.py:205-230`. Son cilalama kalan süreyle sınırlandırılmıştır; bu önceki evrelerin zaman muhasebesini tek başına düzeltmez.

Daha belirleyici olan kayıt katmanıdır: **üçü de exact objective accounting sağlamadığı için hem `fair_comparison` hem bilimsel `native_comparison` manifestinde reddediliyor.** `academic_benchmark/core/registry_setup.py:469-476`. Düz/native benzeri eski bir koşu yapılabilmesi, onaylı `uniride-native-tsp-v1` protokolüne uygunluk değildir. Aynı iterasyon veya aynı seed, aynı hesaplama emeği anlamına gelmez.

## Literatürdeki karşılıkları ve SOTA değerlendirmesi

OpenAlex taraması 13 Ekim 2026 kesim tarihiyle, tam adlar ve kısaltmalarla yapıldı. Tam adların her biri için sonuç sayısı **0**; `E2BSO` **0**, `R2DMA` **0**, `P-AOEA` **4** ve bulunan dört kayıt bu algoritmayı tanımlamıyordu. Bu sınırlı indeks aramasıdır: yayımlanmamış teknik rapor, indeks dışı yayın veya farklı adla çalışma bulunmadığını kanıtlamaz. DOI/yazar/yıl verilmeden bu isimleri yerleşik literatür algoritması gibi atfetmek uygun değildir. Güncel depo metodolojisi de onları deneysel depo içi tasarımlar olarak adlandırıyor: `academic_benchmark/SOTA_PAPER_METHODOLOGY.md:3, 90`.

| İncelenen fikir | Literatürdeki karşılığı | Akademik sonuç |
|---|---|---|
| E2BSO'nun çeşitlilik kontrolü ve elit hedefler | Popülasyon çeşitliliği yönetimi, memetik arama ve kenar temsili; güçlü TSP örneği [Nagata–Kobayashi EAX-GA](https://pubsonline.informs.org/doi/10.1287/ijoc.1120.0506) | Entropi + eşik eklemek tek başına yeni algoritma ailesi veya üstünlük kanıtı değildir; kontrolün katkısı ölçülmeli |
| Üçlüdeki destroy/repair | LNS ve [Ropke–Pisinger ALNS](https://pubsonline.informs.org/doi/10.1287/trsc.1050.0135) | Yalnız birden fazla operatörü rastgele seçmek, tarihsel performansa göre operatör kullanımını uyarlayan ALNS ile aynı değildir |
| R2DMA'nın “rezonans” fikri | Tur benzerliği, eş seçimi, kenar rekombinasyonu ve perturbasyon | Fiziksel rezonansın matematiksel modeli gösterilmiş değil; burada adı verilen şey ağırlıklı benzerlik skoru. Bileşenlerin açıklayıcı/yararlı olduğu deneyle gösterilmeli |
| P-AOEA genomları | Adaptif operatör seçimi ve hiper-sezgiseller; [Fialho ve ark.](https://doi.org/10.1007/s10472-010-9213-y) | Operatörlerden oluşan bir politika uzayını araması araştırılabilir bir fikir; uygun kredi ataması ve sabit/rastgele seçim karşılaştırması gerekir |
| Geçmişe bağlı kabul | [LAHC](https://www.sciencedirect.com/science/article/pii/S0377221716305495) ve SA | Bu bileşenlerin literatürde bulunması, buradaki birleşimin SOTA olduğu anlamına gelmez |

13 Ekim 2026 itibarıyla pratik STSP karşılaştırmasında EAX ve LKH ailesini dışarıda bırakan yalnız GA/PSO/GWO/HHO karşılaştırması yeterince güçlü değildir. EAX üzerinde [Heins–Whitley–Kerschke'nin 2025 çalışması](https://arxiv.org/abs/2505.00803) ve LKH için [2026 positive-gain çalışması](https://doi.org/10.1016/j.cor.2026.107443) güncel geliştirmeler bulunduğunu gösterir. Bu kaynakların kendi örneklerindeki sonuçları, bütün TSP/ATSP türleri için tek bir evrensel kazanan belirlemez. [Concorde](https://www.math.uwaterloo.ca/tsp/concorde.html) ise uygun simetrik örneklerde optimum referansı sağlamak için ayrı değerlendirilmelidir.

ATSP için yönlü maliyet hesabı ve doğrulama ayrı tutulmalı; simetrik EAX sonuçları doğrudan ATSP üstünlüğü olarak aktarılmamalıdır. ATSP yerel aramasının doğrudan literatür dayanaklarından biri [Kanellakis–Papadimitriou](https://pubsonline.informs.org/doi/10.1287/opre.28.5.1086)'dur. Baseline seçimi, uygulanabilir güncel LKH/ATSP sürümü ve aynı problem sözleşmesiyle yapılmalıdır.

## “SOTA adayı” iddiasından önce gereken asgari deney

Bu bölüm öneridir; deneylerin yapıldığı iddia edilmemektedir. Öneriler [Good Laboratory Practice for Optimization Research](https://www.graham-kendall.com/papers/ketal2016.pdf) ile deponun `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md:46-62` ve `ACADEMIC_STUDY_UNIFICATION_DESIGN.md:277-327` sözleşmelerine dayanır.

| Soru | Gerekli karşılaştırma/ölçüm |
|---|---|
| Sonucu asıl yerel arama mı sağlıyor? | Aynı başlatma, restart ve aynı yerel arama bütçeli temel ILS/memetik kontrol; başlangıç, global arama ve final cila kazanımlarını ayrı ölçme |
| E2BSO entropi kontrolü katkı sağlıyor mu? | Kontrol kapalı, sabit faz, düzeltilmiş entropi ve yalnız standart çeşitlilik kontrolü; INJECT/NORMAL/COMPRESS ziyaret sayıları |
| R2DMA rezonansı katkı sağlıyor mu? | Rastgele eş, yalnız yönlü/yönsüz kenar uzaklığı, altı bileşen, her bileşeni çıkarma; theta filtresi ve üç mod için ayrı deney |
| P-AOEA evrim gerçekten öğreniyor mu? | Sabit genom, rastgele seçim, temel ALNS operatör ağırlıkları ve evrilen genom; eşit deneme/kayan pencere kredisi; genom başına deneme ve kazanç |
| Güçlü çözücülere göre konumu ne? | STSP ve ATSP ayrı veri blokları; uygun EAX/LKH, ALNS, ILS ve mevcut çekirdek baseline'lar; önceden ayrılmış tuning/test örnekleri |
| Karşılaştırma adil mi? | Başlatma ve tüm cilalamalar dahil gerçek amaç-değerlendirme sayısı; ayrıca aynı donanım/süre protokolüyle ayrı pratik karşılaştırma; karışık protokolleri havuzlamama |
| Sonuç güvenilir mi? | Çoklu tohum, örnek başına dağılım ve güven aralığı, etki büyüklüğü, uygun çoklu karşılaştırma düzeltmesi; eşleştirmeyi yalnız seed eşitliğine dayandırmama |

“Düzeltildi ve birkaç örnekte optimum bulundu” ancak doğruluk basamağıdır. “SOTA” için tanımlı problem ailesi, veri dağılımı, bütçe ve güçlü rakipler karşısında tekrarlanabilir sonuç gerekir. Burada bunun yerine getirildiğine dair doğrulanmış bir kampanya sunulmadı.

## Üretimde “bu algoritma çalıştı” demenin sınırı

Üretim sarmalayıcısı öğrenci-öğrenci **mesafe** matrisini TSP çözücüsüne veriyor; hata olduğunda **süre** tabanlı en yakın komşu sırasına dönüyor. Fonksiyon yalnız ziyaret sırası döndürüyor. Bu yüzden arayüzde bir rota bulunması tek başına E2BSO/R2DMA/P-AOEA'nın başarıyla yürütüldüğünün kanıtı değildir. Kanıt: `uniride_core/adapters/sota_tsp_strategy_adapter.py:12-23, 45-67`.

Ayrıca `SOTA-*` akademik girişine routing türü verilirse bu giriş doğrudan `core-greedy-routing` yoluna gider (`academic_benchmark/core/registry_setup.py:489-490`); bu bulgu bütün farklı `CVRP-SOTA-*` kayıtları için genellenmemiştir. TSP çevrimi başarısı, zaman pencereli çok rotalı öğrenci taşıma başarısı olarak aktarılmamalıdır.

## Çalıştırılan kontroller ve sınırlar

Python **3.14.6**, NumPy **2.4.6**, Numba **0.66.0**, pytest **9.1.1**. OpenBLAS başlangıçta bellek ayırma hatası verdi; yalnız bu test süreçlerinde iş parçacığı sayısı bire sınırlandıktan sonra koşu başarılı oldu. Paket kurulmadı, başka süreç sonlandırılmadı.

PowerShell ile yeniden çalıştırma:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:NUMBA_NUM_THREADS = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = Join-Path $env:TEMP 'codex-trio-numba'
$repoPath = 'C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide'
Set-Location -LiteralPath $repoPath
& "$repoPath\.venv-jit\Scripts\python.exe" -m pytest -q -p no:cacheprovider `
  "$repoPath\uniride_core\tests\sota_tsp\test_sota_algorithms.py" `
  "$repoPath\academic_benchmark\tests\test_sota_e2e.py" `
  "$repoPath\academic_benchmark\tests\test_atsp_integration.py" `
  "$repoPath\academic_benchmark\tests\test_sota_parity.py"
& "$repoPath\.venv-jit\Scripts\python.exe" "$repoPath\docs\science_review\2026-10-13\codex_trio_evidence\probe.py"
```

Küçük matrisler `Random(2718)` ile 1..80 tamsayı maliyetlerinden üretildi; STSP'de matris simetrikleştirildi. Her ikisinde de 0 düğümü sabitlenip kalan permütasyonlar taranarak referans optimum hesaplandı. Popülasyon 6, iterasyon 5, tohumlar 11/42/73. STSP optimumu **99**, ATSP optimumu **36**; üç yöntem her bu koşuda bu değerlere ulaştı, yeniden hesaplanan maliyetler ve turların tekrarlanabilirliği geçti. Bu kolay ve küçük örnekler, global arama mekanizmalarının katkısını veya büyük örnek başarısını göstermez.

Kaynak kod düzeltmesi, tam TSPLIB kampanyası, tuning, kapsamlı ablation, bütün üretim API testleri veya canlı servis denemesi yapılmadı. SOTA performans sıralaması çıkarılmadı. Commit/push/merge yapılmadı; başka çalışma dosyaları değiştirilmedi.
