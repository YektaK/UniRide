# E2BSO, R2DMA ve P-AOEA: kod, davranış ve performans değerlendirmesi

Tarih: 2026-10-13. Kapsam: `uniride_core/algorithms/sota_tsp/` altındaki `e2bso_tsp.py`, `r2dma_tsp.py`, `paoea_tsp.py` ve paylaştıkları `ls_engine.py`, `destroy_ops.py`, `repair_ops.py`, `utils.compute_population_diversity`. Depo dosyalarında değişiklik yapılmadı; ölçümler kodun bellekte kopyalanıp günlük satırı eklenmiş sürümleriyle alındı.

## Kısa yanıt

Üç algoritma da çalışan ve geçerli tur üreten kodlardır; ama hiçbiri kendi açıklamasında anlatılan mekanizmayla çalışmıyor. Hepsinde imza mekanizması ya ölçek hatası yüzünden devre dışı kalıyor ya da etkisiz bir sabite indirgeniyor:

- **E2BSO:** Entropi tabanlı üç fazlı denetim fiilen sabit bir takvime dönüşüyor. Zorlanan kenarların yarısı sessizce düşüyor.
- **R2DMA:** Rezonansa dayalı çaprazlama kararların yalnızca %0,08'inde devreye giriyor. Kalan %99,9'u tek rastgele takastan ibaret.
- **P-AOEA:** Operatör genomu evrimi ilk elitleri kalıcı olarak kilitliyor. Kapatıldığında sonuç değişmiyor.

Eşit sürede, aynı yerel arama bileşenlerini kullanan basit bir yinelemeli yerel arama (ILS), E2BSO'yu (p=0,006) ve P-AOEA'yı (p=0,0004) istatistiksel olarak geçiyor; R2DMA ise ondan çok daha kötü. LKH, 30 koşunun 30'unda optimumu ortalama 3,3 saniyede buluyor. Bu nedenle üçü de akademik anlamda "state of the art" sayılamaz. Doğru sınıflandırma, depoya özgü ve henüz doğrulanmamış hibrit memetik/ALNS varyantlarıdır.

## 1. Yöntem

1. **Kod incelemesi:** Her mekanizma, açıklamasındaki iddia ve literatürdeki karşılığıyla satır satır karşılaştırıldı.
2. **Enstrümantasyon:** `_solve` gövdesine günlük satırları eklendi. Koşular: berlin52, varsayılan ayarlar (500 iterasyon), tohum 1; rd100, üretim sarmalayıcısı ayarları (pop 24, 200 iterasyon), tohum 1. Tek tohumlu koşular mekanizmanın çalışıp çalışmadığını gösterir; performans tahmini değildir.
3. **İzole tanılar:** Rezonans ölçüsü, constructive çaprazlama, entropi tabanı ve çeşitlilik ölçüsü; berlin52 (20 yerel optimum), rd100 (20) ve pr226 (12) üzerinde.
4. **Kıyas:** Optimumu bilinen TSPLIB örnekleri: rd100, eil101, lin105, pr136, pr152, a280. Her biri 5 tohumla, koşu başına 30 s bütçeyle.
   - Kontrol kolu: SOTA ailesiyle aynı yerel arama çekirdeklerini (deponun Numba 2-opt + Or-opt `MultiLayerLS 'moderate'`) ve double-bridge sarsımını kullanan, "kötü değilse kabul" kurallı bir ILS ([Lourenço, Martin & Stützle, *Handbook of Metaheuristics*](https://doi.org/10.1007/0-306-48056-5_11)).
   - Referans kollar: LKH (elkai, `runs=10`) ve OR-Tools GLS.
   - E2BSO ve P-AOEA bütçeyi aştığı için ILS, her örnek ve tohumda bir kez E2BSO'nun, bir kez de P-AOEA'nın kullandığı süreyle yeniden koşturuldu (eşit süre kolları). R2DMA ≈30 s kullandığından 30 s'lik ILS ile kıyaslandı.
   - İstatistik: eşleştirilmiş Wilcoxon işaretli sıra testi ve Holm düzeltmesi, ayrıca Friedman testi ([Derrac vd. 2011](https://doi.org/10.1016/j.swevo.2011.02.002); [LaTorre vd. 2021](https://doi.org/10.1016/j.swevo.2021.100973)).

## 2. Algoritma bazında bulgular

### 2.1 E2BSO

**İddia.** Kenar tabanlı Shannon entropisiyle ölçülen çeşitliliğe göre üç faz: düşük entropide INJECT, normalde NORMAL, yüksek entropide COMPRESS. Bu fazlara "sürü" güncellemesi, ALNS enjeksiyonu, çok katmanlı yerel arama ve LAHC kabulü eşlik ediyor.

**Kodda bulunan sorunlar ve ölçülen etkileri:**

1. **Entropi normalizasyonu yanlış ölçekte** (`e2bso_tsp.py:131`). Entropi `log2(P·n)` ile bölünüyor. Tüm turlar özdeş olduğunda bile değer `log2 n / log2(P·n)` altına inemiyor.
   - Ölçülen taban, P=40'ta 0,517 (berlin52), 0,555 (rd100) ve 0,595 (pr226); formülle birebir aynı.
   - Birbirinden farklı yerel optimumlardan oluşan bir popülasyon ise yalnızca 0,593, 0,631 ve 0,630 veriyor. Kullanılabilir aralık ≈0,08 birim.
   - Öğrenme döneminden sonra eşikler `h_min = 0,4·target` ve `h_max = 1,4·target` (`:275-276`), yani 0,08–1,12 aralığında. h_min hiçbir zaman entropi tabanına ulaşamıyor.
2. **Faz denetimi fiilen sabit bir takvim** (ölçüm).
   - berlin52: ilk 100 iterasyonun (öğrenme dönemi) 91'i INJECT. Entropi yalnızca 10 iterasyonda bir yeniden hesaplanıyor (`:262`). Öğrenilen eşik `h_min = EMA − 0,05` (`:270`) popülasyon yakınsadıkça entropinin üstünde kalıyor; bayat değerle her iterasyon INJECT seçiliyor. INJECT fazında sürü güncellemesi yapılmıyor, yalnızca en kötü %20 yeniden kuruluyor. Bu yüzden en iyi çözüm iyileşmiyor, eşik güncellenmiyor ve döngü kendini kilitliyor.
   - Öğrenme döneminden sonra: INJECT 0, NORMAL 365, COMPRESS 35. COMPRESS yalnızca hedef eşiğin entropi tabanının altına indiği son ≈%9'luk dilimde (35/400 iterasyon) görülüyor.
   - Üretim ayarında (rd100, 200 iterasyon) öğrenme dönemi koşunun yarısı. Bu dönemin 91'i INJECT.
   - Sonuç: faz kararı popülasyon durumuna değil, iterasyon sayısına bağlı.
3. **Zorlanan kenarların yarısı düşüyor** (`:194`). Hedef kenar `(a,b)` yalnızca `index(a) < index(b)` ise 2-opt ters çevirmesiyle ekleniyor; aksi durumda hiçbir şey yapılmıyor. Atlanan oran berlin52'de %51,6 (7647/14834), rd100'de %51,8.
4. **"Sürü" güncellemesi bir sürü güncellemesi değil.** Hız, eylemsizlik ya da konum güncellemesi yok. Mekanizma, pbest/gbest'ten seçilen birkaç kenarı 2-opt hareketiyle ekleyen rehberli bir harekettir. Literatürdeki karşılığı path relinking'e benzeyen bir rehberli kenar enjeksiyonu, ya da EAX/GPX gibi kenar kalıtımlı çaprazlamaların ilkel bir biçimidir ([Nagata & Kobayashi 2013](https://doi.org/10.1287/ijoc.1120.0506); [Whitley vd. 2009](https://doi.org/10.1145/1569901.1570026)).
5. **LAHC, Burke-Bykov LAHC'si değil** ([Burke & Bykov 2017](https://doi.org/10.1016/j.ejor.2016.07.012)). Geçmiş dizisi bireyin kendi maliyetiyle değil, tüm popülasyona ortak `gbest_cost` ile dolduruluyor (`:313`). Dizi ∞ ile başladığı için ilk `lahc_history=200` iterasyonda her aday kabul ediliyor (`:89`).
   - Ölçülen kabul oranı: berlin52'de %72,4.
   - Üretim ayarında (200 iterasyon) geçmiş hiç dolmuyor; kabul oranı %100,0, yani üretimde E2BSO her adayı kabul ediyor.
6. **CPSO varyantı:** `rng.random() < c1` (`:430`) ifadesinde c1=1,5 olduğundan koşul her zaman doğru. Olasılık olarak tasarlanan parametre etkisiz.
7. **Çeşitlilik tetikleyicisi popülasyonu değil, dizin sırasını ölçüyor.** `compute_population_diversity` popülasyondan rastgele örnek değil, ilk `int(√P)+1` bireyi alıyor (`utils.py:12`). Aynı popülasyon, ilk 7 birey özdeş olacak biçimde sıralandığında 0,000, karıştırıldığında 0,328 çeşitlilik veriyor.

**Literatür karşılığı.** Entropi tabanlı popülasyon çeşitliliği EAX hattında tanımlı ve sınanmış bir bileşendir ([Nagata 2006](https://doi.org/10.1007/11730095_15); [Nagata 2020](https://doi.org/10.1162/evco_a_00268)). Doğru ölçeklenmiş bir entropi `(H − H_min)/(H_max − H_min)` biçiminde ya da Nagata'nın kenar entropisiyle kurulmalıdır.

### 2.2 R2DMA

**İddia.** Altı boyutlu bir rezonans ölçüsüne göre üç çaprazlama modu: constructive (R≥0,7), moderate (0,3≤R<0,7) ve destructive (R<0,3). Bunlara SA kabulü, dissonance filtresi, uyarlanabilir θ ve çeşitlilik darbesi eşlik ediyor.

**Kodda bulunan sorunlar ve ölçülen etkileri:**

1. **Rezonans ölçüsü tur gösterimine bağlı.** Altı bileşenin dördü tur gösterimine duyarlı. Mesafe profili ve ortak alt dizi hem döndürmeye hem yöne duyarlı (`r2dma_tsp.py:175-181, 200-209`). Konum eşleşmesi tüm döndürmeleri denediği için döndürmeye değil, yalnız yöne duyarlı (`:166-167`). Ortak segment ise büyük ölçüde döndürmeden bağımsız ama yöne duyarlı (`:189-196`). n>200'de konum eşleşmesi 0 döndürüyor (`:69, :81`).
   - Aynı tur ters yönde yazıldığında 0,429 (berlin52), 0,456 (rd100), 0,396 (pr226) alıyor. Bu, bağımsız iki yerel optimumun ortalamasıyla (0,430) aynı.
   - pr226'da özdeş tur bile 0,850 alıyor.
   - Rastgele tur çiftleri ≈0,289 alıyor. 2-opt yerel optimum çiftlerinde 0,3 altı hiç görülmedi (en düşük 0,330).
2. **Mod seçimi neredeyse tamamen "perturb"** (ölçüm). Rezonans θ'nın altındaysa (`:360`), çocuk yerel aramasız tek bir rastgele takasla üretiliyor (`:361`).
   - berlin52'de ortalama rezonans 0,301, θ ise 0,45–0,50. 30 000 kararın 29977'i (%99,9) perturb; moderate 20, constructive 3, destructive 0.
   - rd100 üretim ayarında 4788/4800 perturb.
   - Destructive mod için R<0,3 ve R≥θ gerekiyor; θ bu koşularda 0,45'in altına inmediği için bu koşul sağlanamıyor. Kod θ'nın 0,2'ye kadar inmesine izin veriyor, ama bu yalnızca constructive başarı oranı 0,6'yı aştığında oluyor.
   - Yerel arama uygulanmadığı için popülasyon rastgele turlara benzer kalıyor, rezonans düşük kalıyor ve döngü kendini besliyor.
3. **Constructive çaprazlama ortak kenarları korumuyor** (`:291-299`).
   - Ortak kenarların uç düğümleri rastgele sırayla ekleniyor; bir düğüm daha önce kullanıldıysa kenarın bitişikliği bozuluyor. Kurulan `adj` sözlüğü hiç kullanılmıyor (`:296`), kalan şehirler rastgele karıştırılıyor (`:299`).
   - Ölçülen koruma oranı: %54,7 (berlin52), %54,2 (rd100), %44,3 (pr226).
   - Yerel aramadan önce çocuğun maliyeti, kötü ebeveynin 2,63, 4,41 ve 13,10 katı; yani neredeyse rastgele bir tur.
   - Yerel aramadan sonraki oran (0,964 / 0,944 / 0,969), rastgele yeniden başlatma + aynı yerel aramayla (0,955 / 0,941 / 0,968) aynı. Kalıtım katkısı ölçülemiyor.
   - Doğru bir ortak kenar koruyucu çaprazlama GPX ya da EAX türü olmalıdır ([Whitley vd. 2009](https://doi.org/10.1145/1569901.1570026); [Nagata & Kobayashi 2013](https://doi.org/10.1287/ijoc.1120.0506)).
4. **SA sıcaklığı ölçeksiz.** T₀ = 0,4·maliyet (`:111, :334`), soğuma iterasyon başına 0,9995. Ölçülen T/maliyet oranı berlin52'de 0,40'dan 0,316'e, rd100'de 0,362'e iniyor. Bu sıcaklıkta SA kötüleşen hamlelerin çoğunu kabul ediyor; berlin52'de kötüleşen çocukların %62,7'i kabul edildi. Asıl seçiciliği "çocuk, kötü ebeveynin %2 fazlasından kötü değilse" kuralı (`:392`) sağlıyor; bu bir eşik kabulüdür, SA değildir ([Kirkpatrick vd. 1983](https://doi.org/10.1126/science.220.4598.671)).

**Literatür karşılığı.** Benzerliğe göre eş seçimi (assortative mating) ve HGS'deki çeşitlilik katkılı uygunluk ([Vidal vd. 2012](https://doi.org/10.1287/opre.1120.1048)) tanımlı yaklaşımlardır. Ancak R2DMA'da bu katman kararların %0,1'inden azını etkiliyor. Algoritma fiilen "tek rastgele takas + eşik kabulü" yapan bağımsız yürüyüşlerden oluşan bir popülasyon.

### 2.3 P-AOEA

**İddia.** Her birey yok-et/onar/kabul operatörlerini kodlayan bir genom taşıyor; genomlar turnuva, çaprazlama ve mutasyonla evriliyor.

**Kodda bulunan sorunlar ve ölçülen etkileri:**

1. **Kredi sönümlenmiyor.** Genom uygunluğu, başarılı denemelerin birikimli sayısı (`paoea_tsp.py:49`). Bu sayı sıfırlanmıyor ve elitler kendi sayımlarını taşıyor (`:193-194`). Her turda üretilen yeni genomlar 0'dan başladığı için seçilme şansları olmuyor.
   - Ölçülen: berlin52'de aynı 3 genom 10 evrim turunun hepsinde hayatta kaldı. Son turdaki en yüksek uygunluklar 530, 326, 321, dördüncüsü 10.
   - rd100 üretim ayarında da 3 genom 4 turun hepsinde kaldı.
   - Literatürdeki uyarlanabilir operatör seçimi (olasılık eşleme, bandit) oran temelli ya da kayan pencereli kredi kullanır ([Fialho vd. 2010](https://doi.org/10.1007/s10472-010-9213-y); [Eiben vd. 1999](https://doi.org/10.1109/4235.771166)).
2. **Genom içi ağırlıklar öğrenilmiyor.** `destroy_weights` ve `repair_weights` (`:35`) hiçbir yerde güncellenmiyor; yalnızca başlangıçta rastgele atanıyor ya da çaprazlamada 1,0 yapılıyor. Bu, ALNS'nin uyarlanabilir ağırlık mantığından da zayıf ([Ropke & Pisinger 2006](https://doi.org/10.1287/trsc.1050.0135)).
3. **Kabul geni seçime tabi değil.** Başarı kredisi kabul kararından bağımsız hesaplanıyor (`:268-269`). Kabul türünün evrimi rastgele sürüklenmeden ibaret: son turdaki dağılım berlin52'de çoğunlukla SA, rd100'de çoğunlukla LAHC.
4. **SA rastgele yürüyüşe dönüşüyor.** T₀ = 0,4·maliyet (`:250`). Ölçülen kötüleşen aday kabulü berlin52'de %98,8 (1946/1970), rd100'de %100,0. LAHC tüm popülasyona ortak; geçmişi `min(pop_costs)` ile dolduruluyor (`:252, :275`) ve ilk 100 iterasyonda her adayı kabul ediyor.
5. **Evrim bütçe içinde tetiklenmiyor.** `meta_evolution_interval=50` (`:83`), oysa 30 s bütçede n≥100 için P-AOEA ortalama en fazla 15 iterasyon yapabildi. Evrim hiç çalışmadı; evrimsiz sürümle 30 çiftin 30'unda sonuçlar birebir aynı.
6. **Evrim çalıştığında da fark yok.** Üretim ayarlarında (pop 24, 200 iterasyon; eil76 ve rd100, 5'er tohum) evrimli ve evrimsiz sürümler arasında anlamlı fark yok: 1 iyi / 7 eşit / 2 kötü, p=1,0. Bu sınamanın gücü düşük (n=10).

**Literatür karşılığı.** Öz-uyarlamalı operatör oranları ([Gómez 2004](https://doi.org/10.1007/978-3-540-24854-5_113)) ve seçim hiper-sezgiselleri. Bu yaklaşımlarda bile uyarlanabilir katmanın ortalama katkısı küçüktür ([Turkeš vd. 2021](https://doi.org/10.1016/j.ejor.2020.10.045)).

### 2.4 Ortak sorunlar

- **Sonlandırma ve bütçe.** Sonlandırma duvar saati süresine (`time_limit`, `ls_time_limit`) bağlı ve süre yalnızca iterasyon sonunda kontrol ediliyor.
  - a280'de E2BSO 30 s bütçeyle 119 s, P-AOEA 102 s çalıştı; ikisi de yalnızca 1 iterasyon yaptı.
  - Sonuçlar makine yüküne bağlı ve aynı tohumla tekrarlanabilir değil.
  - Deponun amaç-değerlendirme bütçesi muhasebesini (`ObjectiveEvaluationBudget`) kullanmıyorlar; akademik hatta "kataloğa alınmamış" listesinde duruyorlar (`academic_benchmark/engine_core.py:18`).
- **Yönsüz varsayımlar.** Kenar kümeleri yönsüz `(min, max)` olarak tutuluyor ve hareketler segment ters çevirmeye dayanıyor. Üretimde kullanılan yönlü süre matrislerinde (ATSP) bu temsiller tutarsız kalıyor. Bu kıyasta ATSP sınanmadı.
- **Sözde sürüler.** Her üç algoritmanın da asıl iş yükü aynı 2-opt/Or-opt yerel aramasında. Metafor katmanları bu çekirdeğe ölçülebilir bir katkı eklemiyor.

## 3. Performans kıyası

![Optimuma açık, örnek başına 5 tohum]({{artifact:0cc141d2-85ea-4695-88f9-cd05bbec73ed}})

*Şekil: Her nokta bir tohum, siyah çizgi medyan. Her 'SOTA' kolunun kendi süre kontrolü var: E2BSO için "ILS (E2BSO süresi)", P-AOEA için "ILS (P-AOEA süresi)", R2DMA için "ILS (30 s)" (R2DMA ≈30 s kullandı). Eşit süre kollarının süresi a280'de ≈103–119 s, diğer örneklerde 30–35 s. LKH 0,1–10 s'de bitti. P-AOEA'nın genom evrimi kapalı kolu, ana kolla birebir aynı olduğu için çizilmedi.*

**Optimuma ortalama açık (%) ve optimum bulma sayısı (5 tohumdan):**

| Örnek (n) | LKH | ILS, 30 s | ILS, E2BSO süresi | ILS, P-AOEA süresi | E2BSO | P-AOEA | R2DMA | OR-Tools GLS |
|---|---|---|---|---|---|---|---|---|
| rd100 (100) | 0,00 (5/5) | 0,09 (4/5) | 0,09 | 0,00 | 0,29 (1/5) | 0,00 (5/5) | 2,86 (0/5) | 2,40 (0/5) |
| eil101 (101) | 0,00 (5/5) | 0,64 (0/5) | 0,64 | 0,64 | 0,79 (0/5) | 1,49 (0/5) | 2,29 (0/5) | 1,43 (0/5) |
| lin105 (105) | 0,00 (5/5) | 0,00 (5/5) | 0,00 | 0,00 | 0,00 (5/5) | 0,00 (5/5) | 0,68 (1/5) | 2,27 (0/5) |
| pr136 (136) | 0,00 (5/5) | 0,05 (3/5) | 0,05 | 0,05 | 0,97 (0/5) | 1,24 (0/5) | 3,71 (0/5) | 4,37 (0/5) |
| pr152 (152) | 0,00 (5/5) | 0,28 (0/5) | 0,24 | 0,24 | 0,17 (2/5) | 0,43 (0/5) | 1,02 (0/5) | 3,55 (0/5) |
| a280 (280) | 0,00 (5/5) | 4,27 (0/5) | 1,68 | 1,92 | 2,47 (0/5) | 4,61 (0/5) | 4,72 (0/5) | 1,94 (0/5) |
| **Ortalama (30 koşu)** | **0,00** | **0,89** | **0,45** | **0,48** | **0,78** | **1,30** | **2,55** | **2,66** |

**Gerçek süre ve tamamlanan iterasyon (ortalama):**

| Örnek | E2BSO süre (s) / iterasyon | P-AOEA süre / iterasyon | R2DMA süre / iterasyon | ILS süre / iterasyon | LKH süre (s) |
|---|---|---|---|---|---|
| rd100 | 30,1 / 148 | 31,2 / 15 | 30,3 / 41 | 30,0 / 520 | 0,5 |
| eil101 | 30,1 / 143 | 31,0 / 13 | 30,3 / 42 | 30,0 / 543 | 0,2 |
| lin105 | 30,2 / 131 | 31,4 / 13 | 30,3 / 38 | 30,1 / 375 | 0,1 |
| pr136 | 32,2 / 6 | 33,2 / 6 | 30,7 / 27 | 30,1 / 227 | 3,5 |
| pr152 | 34,9 / 4 | 33,4 / 5 | 30,5 / 22 | 30,0 / 122 | 5,8 |
| a280 | 118,6 / 1 | 102,5 / 1 | 30,6 / 43 | 30,8 / 21 | 9,7 |

**Eşleştirilmiş testler:**

| Karşılaştırma (30 eşleşmiş koşu) | A daha iyi / eşit / B daha iyi | Wilcoxon p |
|---|---|---|
| E2BSO ↔ ILS (E2BSO ile aynı süre) | 5 / 6 / 19 | 0,0058 |
| P-AOEA ↔ ILS (P-AOEA ile aynı süre) | 1 / 13 / 16 | 0,0004 |
| R2DMA ↔ ILS (30 s, R2DMA ≈30 s) | 2 / 1 / 27 | <0,001 (Holm 0,00016) |
| E2BSO ↔ LKH | 0 / 8 / 22 | <0,001 (Holm 0,00011) |
| P-AOEA ↔ LKH | 0 / 10 / 20 | <0,001 (Holm 0,00018) |
| R2DMA ↔ LKH | 0 / 1 / 29 | <0,001 (Holm <0,001) |
| P-AOEA ↔ P-AOEA evrimsiz (30 s) | 0 / 30 / 0 | 1,0 (evrim hiç tetiklenmedi) |
| P-AOEA ↔ evrimsiz, üretim ayarı 200 iterasyon (eil76, rd100; 10 çift) | 1 / 7 / 2 | 1,0 |

Friedman testi (7 kol, 30 blok): p = 7.0e-19. Ortalama sıralar: LKH 1,68, ILS 3,10, E2BSO 3,45, P-AOEA 4,05, OR-Tools GLS 5,62, R2DMA 6,05.

**Yorum:**

- 30 s'lik kıyasta E2BSO ile ILS arasında anlamlı fark görünmüyordu (Holm p=1,0). Ancak bu görüntü, E2BSO'nun ortalama 46 s kullanmasından kaynaklanıyordu.
- Eşit sürede ILS, E2BSO'yu 19'a 5 (6 eşit), P-AOEA'yı 16'ya 1 (13 eşit) koşuda geçiyor.
- R2DMA, 30 koşunun 27'sinde ILS'ten kötü ve OR-Tools GLS düzeyinde.
- LKH, 30/30 optimum ile tartışmasız referans ([Helsgaun 2000](https://doi.org/10.1016/s0377-2217%2899%2900284-2); [Helsgaun 2009](https://doi.org/10.1007/s12532-009-0004-6)).

## 4. "State of the art" sayılabilirler mi?

Hayır. Akademik açıdan SOTA iddiasının olağan koşullarının hiçbiri sağlanmıyor:

1. **Yenilik ve atıf.** Bu adlarla yayın kaydı yok. Bileşenler (EAX tarzı entropi, LAHC, ALNS operatörleri, benzerliğe göre eş seçimi, öz-uyarlamalı operatörler) bilinen tekniklerdir. "Yeni bileşim" iddiası ancak bileşen ablasyonuyla kurulabilir ([Camacho‐Villalón vd. 2022](https://doi.org/10.1111/itor.13176); [Aranha vd. 2021](https://doi.org/10.1007/s11721-021-00202-9)).
2. **Mekanizmanın doğruluğu.** Üç algoritmada da imza mekanizması ya ölçek hatası nedeniyle devre dışı (E2BSO entropi fazları, R2DMA rezonans modları) ya da kredi atama hatası nedeniyle etkisiz (P-AOEA evrimi).
3. **Deneysel üstünlük.** Eşit süre ve aynı yerel aramayla basit bir ILS'i geçemiyorlar. TSP'nin kabul gören referansları LKH ve EAX'e karşı ise %0,8–2,5 ortalama açıkla geride kalıyorlar ([Nagata & Kobayashi 2013](https://doi.org/10.1287/ijoc.1120.0506); [Zheng vd. 2023](https://doi.org/10.1016/j.cor.2023.106249)).
4. **Tekrarlanabilirlik ve adil bütçe.** Duvar saatine bağlı sonlandırma ve bütçe aşımı nedeniyle sonuçlar tekrarlanamıyor; deponun kendi adil karşılaştırma protokolüne de dahil değiller.
5. **Örnek ölçeği.** Yalnızca küçük-orta örneklerde koşturuldular. SOTA iddiası TSPLIB'in 1000–85 900 düğümlü örneklerinde, büyük ulusal TSP'lerde ve DIMACS örneklerinde LKH/EAX ile kıyas gerektirir ([Kerschke vd. 2018](https://doi.org/10.1162/evco_a_00215)).

## 5. Öneriler

- **Adlandırma:** "SOTA" önekini kaldırın ve betimleyici ad kullanın:
  - E2BSO → "entropi denetimli memetik ALNS"
  - R2DMA → "benzerlik tabanlı eş seçimli memetik LNS"
  - P-AOEA → "öz-uyarlamalı operatörlü ALNS"
- **E2BSO düzeltmeleri:**
  - Entropiyi `(H − log2 n)/(log2(min(P·n, n(n−1)/2)) − log2 n)` ile yeniden ölçekleyin.
  - INJECT'ten sonra entropiyi hemen yeniden hesaplayın.
  - `ia > ib` durumunda da kenarı ekleyin.
  - LAHC'yi birey başına, bireyin kendi maliyetiyle ve geçmişi başlangıç maliyetiyle doldurarak kurun.
- **R2DMA düzeltmeleri:**
  - Rezonansı yalnızca yön ve döndürmeden bağımsız kenar ölçüleriyle (ör. Jaccard) tanımlayın ve n>200 kesimini kaldırın.
  - Constructive çaprazlamayı ortak kenar parçalarını koruyan bir yapıya (GPX/EAX) dönüştürün.
  - Perturb moduna yerel arama ekleyin ya da bu modu kaldırın.
  - SA sıcaklığını tipik Δ'ya göre kalibre edin ve θ'yı gözlenen rezonans dağılımına göre ayarlayın.
- **P-AOEA düzeltmeleri:**
  - Krediyi oran ya da kayan pencere biçiminde hesaplayın ve dönem başında sıfırlayın.
  - Genom içi ağırlıkları ALNS tarzı güncelleyin.
  - Kabul genini krediye dahil edin ya da çıkarın.
  - Evrim aralığını bütçeye göre ölçekleyin.
- **Ortak düzeltmeler:**
  - Değerlendirme bütçesi muhasebesine geçin ve süreyi iterasyon içinde kontrol edin.
  - Çeşitlilik ölçüsünde rastgele örnekleme kullanın.
- **Yayın hedefleniyorsa:**
  - Bileşen tabanlı ablasyon yapın: aynı yerel aramayla ILS/ALNS kontrol kolları ve her mekanizma için aç/kapa kolu ([Franzin & Stützle 2019](https://doi.org/10.1016/j.cor.2018.12.015)).
  - LKH ve EAX'i referans kol olarak ekleyin.
  - Eşit amaç-değerlendirme ya da eşit süre bütçesi, ≥10 tohum ve eşleştirilmiş istatistik kullanın.

## 6. Sınırlar

- **Örnek ve tohum sayısı:** 6 simetrik EUC_2D örnek (100–280 düğüm), örnek başına 5 tohum, koşu başına 30 s bütçe. ATSP ve büyük örnekler sınanmadı.
- **Makine yükü:** Kıyas, ≈3 boş çekirdekli yüklü bir makinede 3 paralel işçiyle koşturuldu. Duvar saati bütçeleri bu yükten etkilenmiş olabilir; kolların rastgele karıştırılarak koşturulması bu etkiyi kollar arasında dengelemeyi amaçlıyor.
- **Ayarlama:** Algoritmalar depo varsayılanlarıyla, ILS ise ayarlanmadan koşturuldu. LKH `runs=10` ile kullanıldı.
- **Tek tohumlu enstrümantasyon:** Mekanizma sayımları tek tohumlu koşulardan geliyor ve davranışın varlığını gösteriyor; oranlar tohuma göre değişebilir.
- **Düşük güçlü ablasyon:** P-AOEA ablasyonunda n=10.
- **Replika:** E2BSO'daki kenar zorlama sayacı, orijinal mantığın birebir kopyası olan bir replikayla ölçüldü.

## 7. Çapraz kontrol sonrası eklemeler

Bu bölüm, ikinci bir incelemeyle ([CODEX_E2BSO_R2DMA_PAOEA_AKADEMIK_INCELEME_2026-10-13.md]({{artifact:ba1cef37-7832-4d57-9f55-b7a4fc37b604}})) yapılan çapraz kontrolden sonra eklendi. Ayrıntılar: [CROSS_CHECK_CODEX_VS_SCIENCE_2026-10-13.md]({{artifact:4d1041ab-0d89-46e9-ac22-f77497e402de}}).

- **En iyi çözüm kaybı.** Üç algoritmada da en iyi çözüm güncellendikten sonra çeşitlilik enjeksiyonu yapılıyor (`e2bso_tsp.py:307-319`, `r2dma_tsp.py:407-429`, `paoea_tsp.py:277-289`). Bu yüzden enjeksiyonla bulunan daha iyi bir tur kaybolabilir. Üretim ayarındaki 45 koşunun (berlin52, eil76, rd100; 5 tohum) 0'ında kayıp görüldü ([injection_loss_probe.csv]({{artifact:62a5bdf5-5ed0-49c5-8679-bde17c1c97d7}})). Açık gerçek, ama bu ayarlarda pratikte ortaya çıkmadı.
- **P-AOEA'da etkisiz ayarlar.**
  - `tournament_size`, `genome_injection_rate` ve `remove_ratio_range` yalnız tanımlı; kodda okunmuyor.
  - Yıkım oranı sabit bir çizelge izliyor (`:259`).
  - Seçim turnuva değil, sıralama (`:193-197`).
  - RTR uygulanmamış: SA dışındaki her tür LAHC'ye gidiyor (`:264-267`).
  - `success_rate()` tanımlı ama kullanılmıyor.
- **Kayıt katmanı.** Bilimsel protokol modunda (`fair_comparison` / `native_comparison`) yalnız ALNS-TSP kabul ediliyor; üçlü bu modda reddediliyor (`registry_setup.py:473-477`).
- **Üretim adaptörü.**
  - Matris mesafeyle kuruluyor; yedek yol süre tabanlı en yakın komşu kullanıyor; her hata sessizce yedeğe düşüyor (`sota_tsp_strategy_adapter.py:12-67`).
  - Depo matrise dahil değil. Çözücü yalnız öğrencilerden oluşan kapalı bir çevrimi optimize ediyor ve dönen sıra depoya göre döndürülmüyor.
  - Bu nedenle üretimde dönen rota, depoya bağlı gerçek amaç için optimize edilmiş değil. Etkinin büyüklüğü ölçülmedi.
- **İfade düzeltmesi.** §2.2'deki rezonans maddesi netleştirildi: konum eşleşmesi döndürmeye değil, yalnız yöne duyarlı.

## Kaynaklar

DOI'ler önceki turda CrossRef/doi.org üzerinden doğrulanan kaynakçadan alındı. Whitley vd. 2009, Eiben vd. 1999 ve Lourenço vd. (ILS) bu turda CrossRef'te doğrulandı; ILS bölümünün kaydında yıl alanı bulunmuyor.

- Aranha; Camacho Villalón; Campelo et al. (2021). Metaphor-based metaheuristics, a call for action: the elephant in the room. *Swarm Intelligence*. https://doi.org/10.1007/s11721-021-00202-9
- Burke; Bykov (2017). The late acceptance Hill-Climbing heuristic. *European Journal of Operational Research*. https://doi.org/10.1016/j.ejor.2016.07.012
- Camacho‐Villalón; Dorigo; Stützle (2022). Exposing the grey wolf, moth‐flame, whale, firefly, bat, and antlion algorithms: six misleading optimization techniques inspired by<i>bestial</i>metaphors. *International Transactions in Operational Research*. https://doi.org/10.1111/itor.13176
- Derrac; García; Molina et al. (2011). A practical tutorial on the use of nonparametric statistical tests as a methodology for comparing evolutionary and swarm intelligence algorithms. *Swarm and Evolutionary Computation*. https://doi.org/10.1016/j.swevo.2011.02.002
- Eiben; Hinterding; Michalewicz (1999). Parameter control in evolutionary algorithms. *IEEE Transactions on Evolutionary Computation*. https://doi.org/10.1109/4235.771166
- Fialho; Da Costa; Schoenauer et al. (2010). Analyzing bandit-based adaptive operator selection mechanisms. *Annals of Mathematics and Artificial Intelligence*. https://doi.org/10.1007/s10472-010-9213-y
- Franzin; Stützle (2019). Revisiting simulated annealing: A component-based analysis. *Computers & Operations Research*. https://doi.org/10.1016/j.cor.2018.12.015
- Gomez (2004). Self Adaptation of Operator Rates in Evolutionary Algorithms. *Lecture Notes in Computer Science*. https://doi.org/10.1007/978-3-540-24854-5_113
- Helsgaun (2000). An effective implementation of the Lin–Kernighan traveling salesman heuristic. *European Journal of Operational Research*. https://doi.org/10.1016/s0377-2217%2899%2900284-2
- Helsgaun (2009). General k-opt submoves for the Lin–Kernighan TSP heuristic. *Mathematical Programming Computation*. https://doi.org/10.1007/s12532-009-0004-6
- Kerschke; Kotthoff; Bossek et al. (2018). Leveraging TSP Solver Complementarity through Machine Learning. *Evolutionary Computation*. https://doi.org/10.1162/evco_a_00215
- Kirkpatrick; Gelatt; Vecchi (1983). Optimization by Simulated Annealing. *Science*. https://doi.org/10.1126/science.220.4598.671
- LaTorre; Molina; Osaba et al. (2021). A prescription of methodological guidelines for comparing bio-inspired optimization algorithms. *Swarm and Evolutionary Computation*. https://doi.org/10.1016/j.swevo.2021.100973
- Lourenço; Martin; Stützle (yıl kayıtta yok). Iterated Local Search. *Handbook of Metaheuristics*. https://doi.org/10.1007/0-306-48056-5_11
- Nagata; Kobayashi (2013). A Powerful Genetic Algorithm Using Edge Assembly Crossover for the Traveling Salesman Problem. *INFORMS Journal on Computing*. https://doi.org/10.1287/ijoc.1120.0506
- Nagata (2006). Fast EAX Algorithm Considering Population Diversity for Traveling Salesman Problems. *Lecture Notes in Computer Science*. https://doi.org/10.1007/11730095_15
- Nagata (2020). High-Order Entropy-Based Population Diversity Measures in the Traveling Salesman Problem. *Evolutionary Computation*. https://doi.org/10.1162/evco_a_00268
- Ropke; Pisinger (2006). An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time Windows. *Transportation Science*. https://doi.org/10.1287/trsc.1050.0135
- Turkeš; Sörensen; Hvattum (2021). Meta-analysis of metaheuristics: Quantifying the effect of adaptiveness in adaptive large neighborhood search. *European Journal of Operational Research*. https://doi.org/10.1016/j.ejor.2020.10.045
- Vidal; Crainic; Gendreau et al. (2012). A Hybrid Genetic Algorithm for Multidepot and Periodic Vehicle Routing Problems. *Operations Research*. https://doi.org/10.1287/opre.1120.1048
- Whitley; Hains; Howe (2009). Tunneling between optima: partition crossover for the traveling salesman problem. *Proceedings of GECCO 2009*. https://doi.org/10.1145/1569901.1570026
- Zheng; Zhong; Chen et al. (2023). A reinforced hybrid genetic algorithm for the traveling salesman problem. *Computers & Operations Research*. https://doi.org/10.1016/j.cor.2023.106249
