# Çapraz kontrol: Codex incelemesi ile bu oturumun bulguları

Tarih: 2026-10-13. Karşılaştırılan belgeler:
- [CODEX_E2BSO_R2DMA_PAOEA_AKADEMIK_INCELEME_2026-10-13.md]({{artifact:ba1cef37-7832-4d57-9f55-b7a4fc37b604}}) (Codex)
- [SOTA_FAMILY_EVALUATION_2026-10-13.md]({{artifact:4ed00078-1667-48d7-b3be-512698a7e2c8}}) (bu oturumun raporu)

**Kod sürümü.** Codex `de608fd4…` commit'ini incelemiş; deponun şu anki HEAD'i `4cfce242…`. İkisi arasında `uniride_core/algorithms/sota_tsp/` ve `uniride_core/algorithms/utils.py` için `git diff` boş, çalışma ağacında da bu dosyalarda kaydedilmemiş değişiklik yok. İki inceleme aynı kodu ele alıyor.

**Yöntem.** Codex'in her iddiası kaynak koddan satır satır yeniden okundu. Yeni olan iki iddia ölçüldü:
- son enjeksiyonda en iyi çözümün kaybolup kaybolmadığı;
- üretim adaptörünün davranışı.

Codex'in verdiği kaynaklar CrossRef ve arXiv'de kontrol edildi. Codex'in koşturduğu 40 test bu oturumda yeniden koşturulmadı.

## Kısa sonuç

- **Ana yargıda tam uyum var.** Üç yöntem de deneysel hibrittir; SOTA kanıtı yoktur; adlarını veren mekanizmalar tarif edildiği gibi çalışmıyor.
- **Codex'in 13 iddiasından 12'si kodda doğrulandı.** Kalan tek iddia (40 testin geçtiği) bu oturumda yeniden koşturulmadığı için doğrulanmadı. Hiçbiri bu oturumun ölçümleriyle çelişmiyor.
- **Dört bulgu bu oturumun raporunda yoktu; hepsi doğrulandı:**
  - S1 en iyi çözüm kaybı;
  - P-AOEA'nın etkisiz ayarları ve uygulanmamış RTR;
  - kayıt katmanının bilimsel protokol modunda bu üçlüyü reddetmesi;
  - üretim adaptörünün mesafe matrisi ve sessiz yedek yolu.
- **S1'in pratik sıklığı ölçüldü.** Üretim ayarında (popülasyon 24, 200 iterasyon; berlin52, eil76, rd100; 5 tohum) 45 koşunun **0**'ında kayıp görüldü. P-AOEA'da enjeksiyonun o anki en iyi çözümü geçtiği olay sayısı **0**. E2BSO'da enjekte edilen turların hiçbiri nihai sonuçtan iyi değildi. E2BSO ve R2DMA için enjeksiyon anındaki en iyi değer kaydedilmedi; bu iki algoritmada ölçüt nihai sonuçla kıyas. Hata gerçek bir sözleşme açığı, ama bu ayarlarda pratikte ortaya çıkmadı.
- **Kanıt türleri birbirini tamamlıyor.**
  - Codex: kod okuma, kontrollü problar, 7 düğümlü örnekler.
  - Bu oturum: enstrümantasyon, 52–280 düğümlü örnekler, LKH/ILS/OR-Tools kıyası.

  Codex büyük örneklerde bütçe aşımını ve performansı ölçmedi; bu oturum ölçtü. Bu oturum ise yapılandırma alanlarının ve kayıt ile üretim katmanlarının kodla bağlantısını incelememişti; Codex inceledi.
- **Bu oturumun raporunda bir ifade düzeltmesi gerekiyor.** R2DMA'nın konum eşleşmesi terimi tüm döndürmeleri denediği için döndürmeye değil, yalnız yöne duyarlı. Codex bu konuda haklı. Raporun yeni sürümünde ifade düzeltildi.
- **İki raporda da olmayan yeni bir bulgu var.** Üretim adaptörü depoyu matrise almıyor ve yalnız öğrencilerden oluşan kapalı bir çevrimi optimize ediyor (§3).

## 1. Codex bulgularının tek tek doğrulanması

| # | Codex bulgusu | Kod kontrolü | Bu oturumun kanıtıyla ilişkisi | Durum |
|---|---|---|---|---|
| 1 | **Son enjeksiyonda en iyi çözüm kaybı (S1)** | `e2bso_tsp.py:307-310` en iyiyi günceller, `:316-319` sonra enjekte eder. Aynı sıra `r2dma_tsp.py:407-410 → 422-429` ve `paoea_tsp.py:277-280 → 286-289` için de geçerli. Döngü `:321 / :432 / :292`'de bitebilir; enjekte edilen tur o noktada hiç değerlendirilmez. | Yeni ölçüm ([loss_probe.py]({{artifact:0e998442-4de9-4101-8848-97461f95acd7}}), [injection_loss_probe.csv]({{artifact:62a5bdf5-5ed0-49c5-8679-bde17c1c97d7}})): 45 koşuda kayıp 0. E2BSO çeşitlilik tetikleyicisi 12 koşuda 33 kez çalıştı; enjekte edilen en iyi tur nihai sonuçtan iyi değildi (en yakın durumda eşit). P-AOEA tetikleyicisi 1 koşuda 2 kez çalıştı. R2DMA darbesi 0 kez çalıştı. | **Doğrulandı** (kod). Bu ayarlarda pratikte gözlenmedi. P-AOEA'da SA kötüleşen adayların %98,8–100'ünü kabul ettiği için, şanslı bir enjeksiyon bir sonraki iterasyonda büyük olasılıkla ezilir. |
| 2 | **E2BSO entropi ölçeği** (özdeş turlarda log n / log(P·n)) | `:131-132` `log2(total_edges)` ile normalize ediyor. `:253` başlangıç eşiği h_min = 0,5·h_start = 0,4 (`:35` h_start = 0,8). | Bu oturum: taban 0,517 / 0,555 / 0,595. Öğrenme döneminde 100 iterasyonun 91'i INJECT; dönem sonrasında 0. | **Uyumlu.** Codex ilk kontrolü (eşik 0,4 < taban, yani INJECT yok) inceliyor; bu oturum öğrenilen eşiği (EMA−0,05 > entropi, yani INJECT kilidi) inceliyor. İkisi farklı anlara ait ve birlikte doğru. |
| 3 | **Kenar zorlama `ia<ib`; ATSP'de yönün kaybı** | `:193-195`; kenarlar `(min,max)` ile tutuluyor (`:176-183`). | Bu oturum: atlanan oran %51,6 / %51,8. ATSP bu oturumda sınanmadı. | **Doğrulandı.** Codex'in kontrollü ATSP probu (ileri tur 5, ters tur 500) ek kanıt. |
| 4 | **R2DMA destructive dalı θ ile gölgeleniyor** | `:360` perturb koşulu önce kontrol ediliyor; θ_base = 0,5 (`:103`); θ yalnız constructive sonuçlarıyla güncelleniyor (`:399, :414-420`). | Bu oturum: 30 000 kararın 0'ı destructive, %99,9'u perturb. | **Uyumlu.** Ek: θ yalnız constructive kararlarının başarısından öğreniyor; constructive kararların payı ≈%0,01 (3/30 000) olduğu için θ fiilen sabit kalıyor. Codex'in "en erken 250. iterasyon" hesabı alt sınır olarak doğru; pratikte bu sınıra ulaşılmıyor. |
| 5 | **P-AOEA'da etkisiz ayarlar ve RTR** | `tournament_size` (`:84`), `genome_injection_rate` (`:87`) ve `remove_ratio_range` (`:93`) yalnız tanımlı, hiçbir yerde okunmuyor. `:259` sabit 0,30→0,10 çizelgesi; `:193-197` sıralama ve üst yarıdan rastgele ebeveyn; `:264-267` SA dışındaki her tür LAHC'ye gidiyor; RTR yalnız docstring'de (`:13`) geçiyor. | Bu oturumun raporunda yoktu. | **Doğrulandı (yeni).** |
| 6 | **Rezonansın tur gösterimine bağlılığı; constructive çaprazlama** | `:69-70, :81-82` n>200'de konum terimi 0 ve ağırlıklar yeniden normalize edilmiyor. `:166-167` konum terimi tüm döndürmeleri deniyor. Mesafe profili (`:175-181`) ve ortak alt dizi (`:200-209`) indeks sırasına bağlı. `:271-301` `adj` sözlüğü kullanılmıyor. | Bu oturum: ters tur ≈0,43; pr226'da özdeş tur 0,85; ortak kenar koruma %44–55. | **Uyumlu.** Bu oturumun raporundaki "konum eşleşmesi tur başlangıcına duyarlı" ifadesi düzeltildi: konum terimi döndürmeye değil, yalnız yöne duyarlı. |
| 7 | **P-AOEA uygunluğu kaliteyle maruziyeti karıştırıyor** | `:49` `fitness += 1`; `:42` `success_rate()` tanımlı ama hiçbir yerde kullanılmıyor; `:194` elitler kopyalanmadan aynı nesneler olarak taşınıyor. | Bu oturum: aynı 3 genom 10 turun 10'unda hayatta kaldı. | **Uyumlu.** Codex'in ek ayrıntısı: `success_rate()` var ama kullanılmıyor. |
| 8 | **LAHC, standart LAHC değil** | E2BSO `:87-103, :252, :313`; P-AOEA `:108-122, :252, :275` | Bu oturum: kabul oranı %72,4 (varsayılan ayar) ve %100 (üretim ayarı). | **Uyumlu.** |
| 9 | **Süre denetimi gevşek; kayıt katmanı reddediyor** | `ls_engine.py:216` süreyi yalnız katmanlar arasında kontrol ediyor. `registry_setup.py:473-477` bilimsel protokol modunda yalnız ALNS-TSP'ye izin veriyor. | Bu oturum: a280'de 30 s bütçeyle E2BSO 118,6 s, P-AOEA 102,5 s çalıştı (Codex aşımı ölçmedi). | **Doğrulandı.** Kayıt katmanı reddi bu oturumda yoktu; aşım miktarı Codex'te yoktu. |
| 10 | **Literatürde bu adlarla kayıt yok** | — | Bu oturumun 1. turu: aynı sonuç. | **Uyumlu.** |
| 11 | **Üretim adaptörü: mesafe matrisi, süre tabanlı yedek, yalnız sıra döndürme** | `sota_tsp_strategy_adapter.py:12-23` mesafe×1000 tamsayı matrisi; `:26-42` süre tabanlı en yakın komşu yedeği; `:61-67` `except Exception` her hatayı sessizce yedeğe yönlendiriyor. | Bu oturumda incelenmemişti. | **Doğrulandı ve genişletildi** (§3). |
| 12 | **`SOTA-*` + routing → `core-greedy-routing`** | `registry_setup.py:489-490` | — | **Doğrulandı.** |
| 13 | **Mevcut 40 test geçiyor** | — | Yeniden koşturulmadı. | **Doğrulanmadı.** |

## 2. Bu oturumda olup Codex raporunda bulunmayanlar

**E2BSO**
- Öğrenme döneminde INJECT kilidi: 100 iterasyonun 91'i INJECT. Dönem sonrasında INJECT 0, NORMAL 365, COMPRESS 35; faz kararı popülasyon durumuna değil iterasyon sayısına bağlı.
- CPSO dalında c1 = 1,5 (`:81`) olduğundan `rng.random() < c1` (`:430`) koşulu her zaman doğru. Codex CPSO'yu kapsam dışı bırakmıştı.

**R2DMA**
- Perturb modunda yerel arama hiç yok (`:378-389` yalnız diğer üç modda çağırıyor). Kararların %99,9'u bu modda.
- Constructive çaprazlamadan sonra yerel aramayla ulaşılan sonuç, rastgele yeniden başlatma + aynı yerel aramayla aynı.
- SA ölçeksiz: T₀ = 0,4·maliyet; kötüleşen çocukların %62,7'si kabul ediliyor; asıl seçiciliği %2'lik eşik sağlıyor.

**P-AOEA**
- Genom içi ağırlıklar hiç güncellenmiyor ve kabul geni krediye girmiyor.
- 30 s bütçede evrim hiç tetiklenmedi; evrimsiz kolla 30 koşunun 30'unda sonuç birebir aynı.
- Üretim ayarındaki ablasyonda evrimin etkisi yok: 1 / 7 / 2, p = 1,0.

**Ortak**
- `compute_population_diversity` yalnız ilk ⌊√P⌋+1 bireyi örnekliyor (`utils.py:12`). Aynı popülasyon sıralamaya göre 0,000 ya da 0,328 veriyor. Codex bu fonksiyonun yalnız yönsüz kenar kullandığına değinmişti.
- 100–280 düğümlü 6 örnekte kıyas: LKH, ILS (eşit süre), OR-Tools GLS ve istatistik. ILS, E2BSO'yu (5/6/19, p = 0,006) ve P-AOEA'yı (1/13/16, p = 0,0004) geçiyor. R2DMA ILS'ten 30 koşunun 27'sinde kötü.

## 3. Yeni ek bulgu: üretim adaptörünün problem modeli

Codex'in 11. bulgusu genişletildiğinde, üretimdeki E2BSO/R2DMA/P-AOEA stratejileri (`optimizer_api/strategies/ebso_strategy.py:95-112` ve R2DMA/P-AOEA karşılıkları) aşağıdaki problemi çözüyor:

1. **Depo matriste yok.** Matris yalnız `student_ids` üzerinden kuruluyor (`sota_tsp_strategy_adapter.py:12-23`). `depot_id` yalnız yedek yolda kullanılıyor (`:26-42`).
2. **Model rotayla uyuşmuyor.** Çözücü öğrenciler arasında kapalı bir çevrimi optimize ediyor; son öğrenciden ilk öğrenciye dönüş maliyeti amaca dahil. Gerçek rota ise depodan başlayan açık bir yol. Depo bacakları amaçta yok, döngüyü kapatan bacak ise gereksiz yere var.
3. **Dönen sıra döndürülmüyor.** Çevrimin kesileceği nokta depoya göre seçilmiyor (`:65`); çözücünün başlangıç noktası kullanılıyor.
4. **Kapasite ve çok araç modellenmiyor.** Stratejinin docstring'ine göre (`ebso_strategy.py:71-74`) çok araçlı durumda da tek rota döndürülüyor.

**Sonuç.** Üretimde dönen rota, çözücünün iyi optimize ettiği durumda bile depoya bağlı gerçek amaç için optimum değil. Bu bulgu kod okumayla belirlendi; etkisinin büyüklüğü ölçülmedi.

## 4. Codex'in kaynaklarının kontrolü

| Kaynak | Kontrol | Durum |
|---|---|---|
| Ammann, Ostermann, Stiller, de Wolff (2026). A speed-up for Helsgaun's TSP heuristic by relaxing the positive gain criterion. *Computers & OR*. https://doi.org/10.1016/j.cor.2026.107443 | CrossRef | ✓ |
| Heins, Whitley, Kerschke (2025). To Repair or Not to Repair? Investigating the Importance of AB-Cycles for the State-of-the-Art TSP Heuristic EAX. arXiv:2505.00803 | arXiv API | ✓ (ön baskı) |
| Kanellakis, Papadimitriou (1980). Local Search for the Asymmetric Traveling Salesman Problem. *Operations Research*. https://doi.org/10.1287/opre.28.5.1086 | CrossRef | ✓ |
| Kendall vd. (2016). Good Laboratory Practice for optimization research. *J. Operational Research Society*. https://doi.org/10.1057/jors.2015.77 | CrossRef (Codex PDF bağlantısı vermişti) | ✓ |
| Nagata & Kobayashi 2013; Ropke & Pisinger 2006; Fialho vd. 2010; Burke & Bykov 2017 | Bu oturumda doğrulanmıştı | ✓ |

## 5. Yorum farkları

- **"Temel arama çalışıyor" ifadesi.** 7 düğümlü örneklerde doğru: her yöntem optimuma ulaşıyor. 100–280 düğümde ise R2DMA'nın arama gücü OR-Tools GLS düzeyinde kalıyor (ortalama açık %2,55). Bu yüzden "çalışıyor" ifadesi, R2DMA için yalnız geçerli tur üretmek anlamında okunmalı.
- **"Genom havuzu gerçekten evriliyor" ifadesi.** Seçim, çaprazlama ve mutasyon kodu gerçekten var ve iterasyon sayısı ≥50 olduğunda çalışıyor. Ancak birikimli kredi nedeniyle aynı elitler kalıyor ve ablasyonda ölçülebilir etki yok. Doğru ifade: "sözdizimsel olarak evriliyor, etkili biçimde öğrenmiyor".
- **E2BSO INJECT davranışı.** İki rapor farklı anları anlatıyor (bkz. tablo #2); çelişki yok.

## 6. Yeniden tasarım planına etkisi

[REDESIGN_WORK_PLAN_2026-10-13.md]({{artifact:7fc7357d-8682-4559-95d9-7914690ad5be}}) için şu eklemeler gerekli; planın yeni sürümüne işlendi:

1. **Yeni sözleşme testleri:**
   - En iyi çözüm arşivi, enjeksiyon dahil her popülasyon değişikliğinden sonra güncellenir.
   - Her yapılandırma alanı en az bir kod yolunu etkiler: alanı değiştirmek davranışı değiştirmeli; değiştirmiyorsa alan kaldırılmalı.
   - Belgede adı geçen her operatör (RTR gibi) kayıtta uygulanmış olmalı.
2. **Protokol:** Yeni algoritmalar `registry_setup.py:473-477`'deki bilimsel protokol kapısından ancak kesin amaç-değerlendirme muhasebesiyle geçebilir. Bu kapı Faz 0'ın kabul ölçütüne eklendi.
3. **ATSP yerel araması:** Kanellakis–Papadimitriou (1980) dayanak olarak eklendi.
4. **Güncel referanslar:** Ammann vd. (2026) LKH hızlandırması ve Heins vd. (2025) EAX analizi, referans kol seçiminde göz önünde tutulmalı.
5. **Üretim (Faz 4):**
   - Depo matrise alınmalı ve depoya bağlı açık yol amacı kullanılmalı.
   - Sessiz yedek yol telemetriyle raporlanmalı.
   - Mesafe ile süre tutarlı kullanılmalı.
6. **Deney uygulaması:** Kendall vd. (2016) iyi uygulama kılavuzu Faz 3 protokolüne eklendi.
