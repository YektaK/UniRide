# UniRide algoritma çalışması: nihai birleşik bulgular ve yol haritası

Hazırlayan: **Claude Science**. Tarih: **2026-10-17**. **Sürüm 2** (aynı gün): yeniden üretim sonuçları eklendi (§11); U1'deki çözüm yöntemi ve O2'deki yuvarlama düzeltildi (§7, 24–27).

**Durum.** Bu belge, Claude Science'ın bu çalışmadaki **tek geçerli bulgu ve karar belgesidir**. Şunları birleştirir:
- 2026-10-14 ile 2026-10-17 arasındaki bütün Claude Science belgeleri;
- Codex'in 2026-10-16 bütünsel değerlendirmesi;
- benim 2026-10-17 yanıtım.

Eski belgeler değiştirilmedi; tarihsel kayıt olarak duruyor. Bir ifade ya da sayı eski bir belgeyle çelişirse **bu belge geçerlidir**. Düzeltmelerin tamamı §7'de.

**Kanıt.** Bu belgedeki bütün sayılar 2026-10-17'de ham sonuç dosyalarından yeniden hesaplandı; özetlerden aktarılmadı. Dosyalar SHA-256 özetleriyle [nihai_kanit_arsivi_2026-10-17/](nihai_kanit_arsivi_2026-10-17/README.md) altında. Ana hatlar ayrıca [yeniden_uretim_paketi_2026-10-17/](yeniden_uretim_paketi_2026-10-17/README.md) ile yeniden koşturuldu ve arşivle karşılaştırıldı (§11).

## 0. Neden tek belge

- Bulgular on bir belgeye dağılmıştı: iki özgün tasarım, iki revizyon, revizyonların birebir kopyaları, dört rapor, Codex'in değerlendirmesi ve benim yanıtım. Eski belgeleri tek tek düzeltmek üçüncü bir revizyon katmanı (`…_ClaudeScience2.md`) eklerdi; okuyucu yine üç katmanı karşılaştırmak zorunda kalırdı.
- Akademik çalışma, hakem ve Codex için tek bir iddia tabanı gerekiyor: hangi sonuç kanıtlı, hangisi ölçülmüş, hangisi gösterilemedi.
- Düzeltmeler kaybolmuyor. §7, eski belgelerdeki her düzeltilmiş ifadeyi yeri, eski hali ve geçerli haliyle birlikte listeliyor.

### 0.1 Birleştirilen belgeler

| Kısaltma | Belge | Bu belge karşısındaki durumu |
|---|---|---|
| A | [ASTRA6_YENI_ALGORITMA_TASARIMLARI.md](ASTRA6_YENI_ALGORITMA_TASARIMLARI.md) (Astra, özgün) | Değiştirilmedi; tasarım kaynağı |
| B | [CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14.md](CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14.md) (özgün) | Değiştirilmedi; tasarım kaynağı |
| CS1 | `ALGORITHM_DEVELOPMENT_RESULTS_2026-10-14.md` (arşivde: [raporlar_ilk_surum/](nihai_kanit_arsivi_2026-10-17/raporlar_ilk_surum/)) | Yöntem ayrıntısı için başvuru; sayılar bu belgede |
| CS2 | `TSP_FAST_LS_REPORT.md` (arşivde) | Aynı |
| CS3 | [ASTRA_DEGERLENDIRME_2026-10-15.md](ASTRA_DEGERLENDIRME_2026-10-15.md), [astra_issues.csv](astra_issues.csv) | 48 maddenin durumu için Codex'in §6'sı ve bu belgenin §7–§8'i geçerli |
| CS4 | [SCIENCE_OGRENILMIS_ORUNTU_CALISMASI_2026-10-15.md](SCIENCE_OGRENILMIS_ORUNTU_CALISMASI_2026-10-15.md) | Yöntem ayrıntısı için başvuru |
| L | [ML_ROTA_LITERATUR_2026-10-15.md](ML_ROTA_LITERATUR_2026-10-15.md), [ml_rota_kaynakca.csv](ml_rota_kaynakca.csv) | Kaynak taraması; düzeltmeler §7 |
| AR | [ASTRA6_YENI_ALGORITMA_TASARIMLARI_ClaudeScience.md](ASTRA6_YENI_ALGORITMA_TASARIMLARI_ClaudeScience.md) (`…1.md` birebir kopya) | İddia düzeyinde bu belgeyle değiştirildi |
| BR | [CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14_ClaudeScience.md](CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14_ClaudeScience.md) (`…1.md` birebir kopya) | Aynı |
| K | [CODEX_BUTUNSEL_DEGERLENDIRME_VE_AKADEMIK_KATKI_2026-10-16.md](CODEX_BUTUNSEL_DEGERLENDIRME_VE_AKADEMIK_KATKI_2026-10-16.md) | Codex'in değerlendirmesi; F01–F24 ve M1–M8 bu belgede işlendi |
| Y | [CLAUDE_SCIENCE_YANIT_BUTUNSEL_DEGERLENDIRME_2026-10-17.md](CLAUDE_SCIENCE_YANIT_BUTUNSEL_DEGERLENDIRME_2026-10-17.md) | Görüş belgesi; düzeltme listesi bu belgenin §7'sine taşındı ve genişletildi |
| 01–17 | 2026-10-13 belgeleri (E2BSO/R2DMA/P-AOEA değerlendirmesi, literatür, kıyas CSV'leri) | Değiştirilmedi; ilgili sonuçlar §4'te |

### 0.2 Kanıt etiketleri ve raporlama kuralları

| Etiket | Anlamı |
|---|---|
| **[KANIT]** | Matematiksel kanıt ya da çözücü optimallik sertifikası (`OPTIMAL`). Hangi hedef aşaması için geçerli olduğu yazılır. |
| **[ÖLÇÜM]** | Belirtilen veri ve bütçede yapılmış ölçüm. Genelleme değildir. |
| **[GÖSTERİLEMEDİ]** | Bu deneyde fark ya da katkı gösterilemedi. Eşitlik ya da katkısızlık kanıtı değildir. |
| **[ÖNERİ]** | Tasarım ya da öncelik önerisi. |
| **[AÇIK]** | Yapılmamış ya da kapanmamış iş. |

Kurallar:
1. Dalga sonuçları "hücre (temel dalga)" biçiminde raporlanır. 228 hücre = 57 temel dalga × 4 R değeridir; R kopyaları bağımsız örnek değildir.
2. Tohumlar bağımsız problem sayılmaz. p-değerinin yanında örnek düzeyi kazanç/beraberlik/kayıp sayımı verilir.
3. Kesin optimum iddiası, kanıtlanan hedef aşamasıyla birlikte yazılır: filo, rota sayısı ya da dakika.
4. "SOTA", "yeni yöntem" ve "üretime hazır" ifadeleri kullanılmaz (K, M8).

## 1. Problem sözleşmeleri

| Kod | Tanım |
|---|---|
| **P5 — dalga** | Sabit çapa zamanlı tek dalga. Toplama rotası ilk yolcudan kampüse (D.Kampus), dağıtım rotası kampüsten son yolcuya gider. Rota süresi ≤ T = 150 dk. Her yolcunun araç içi süresi ≤ R, R ∈ {50, 60, 70, 90} dk. İki kapasite havuzu vardır (Sw/So, araç başına `lseat`). Süre matrisi yönlü, metrik olmayan, tamsayı dakikadır. Amaç sözlükseldir: olurluluk → rota sayısı → toplam dakika. |
| **P6 — tipli dalga** | P5 + heterojen araç tipleri (büyük araç / sedan). |
| **P7 — gün** | Bir günün bütün dalgaları birlikte. Rotalar araçlara atanır; araç meşguliyet aralıkları depo konvansiyonunu izler (`run_day_joint.py`; depodaki filo sayılarını 20/20 hücrede yeniden üretir). Amaç üç aşamalı sözlükseldir: (1) filo K, (2) K sabitken toplam rota, (3) rota sabitken toplam dakika. |
| **P7-tipli** | Büyük araç sayısı L sabit; sedan sayısı en küçüklenir. |
| **P1/P2 — TSP/ATSP** | Akademik hat; TSPLIB örnekleri. |
| **P8 — eşlenik talep** | Toplama-dağıtım çiftleri. Ayrı model, decoder ve doğrulayıcı ister. Bu çalışmada veri ve kod yok. |

## 2. Veri ve bağımsızlık birimleri

| Olgu | Değer | Kaynak |
|---|---|---|
| Dönem | Tek hafta: 2026-10-05 (Pazartesi) – 2026-10-09 (Cuma), 5 gün | `docs/paper/results/week-2026-10-05-4sw5so/` |
| Yolcu bacağı | Her R için 226 | `wave_summary_by_R.csv` |
| Durak | 28 durak + D.Kampus | depo girdisi |
| Dalga hücresi | 228 = 57 temel dalga × 4 R. **57/57 temel dalgada 4 R değerinin yolcu kümesi aynı.** | `wave_exact_vs_ga.csv` |
| Zor hücreler (n ≥ 6) | 36 hücre = **9 temel dalga**; hepsinde n ≤ 20 | aynı |
| Gün hücresi | 20 = 5 gün × 4 R | `day_level_4sw5so.csv` |
| Matris | Örnek dosya 756 yay; `duration_minutes` hepsi tamsayı; en büyük 57 dk. Tek matris içerik özeti (`matrix_sha` bfb2dd85…dd31e5) | depo girdisi, sonuç kayıtları |

**Sonuç:** Bütün üretim hattı bulguları tek haftaya ve 9 zor temel dalgaya dayanır. Bu, akademik genelleme için en büyük sınırdır (§10).

## 3. Üretim hattı bulguları (P5–P7)

| No | Bulgu | Etiket | Kanıt dosyası |
|---|---|---|---|
| U1 | **WAVE-EXACT** (alt küme DP + sözlüksel küme bölümleme): **228/228 hücre `OPTIMAL`**. 226 hücre tek aşamalı ağırlıklı amaçla (W·rota + dakika, W = 10 000; S3 ile sözlükselle eşdeğer) HiGHS'te, 2 hücre iki aşamalı HiGHS'te çözüldü; bağımsız sertifika ihlali 0. Sayım süresi en çok 8,64 s (n = 20), en büyük kolon sayısı 45 170. CS1'de n = 20 için bellek ≈100 MB olarak ölçüldü; bellek 2ⁿ·n ile büyür. | [KANIT] (rota + dakika) | `wave_exact_vs_ga.csv` |
| U1-not | 2026-10-05 08:45 toplama dalgasının R=50 ve R=70 hücreleri ilk koşuda yalnız `FEASIBLE` kaldı (ağırlıklı HiGHS kanıtlayamadı, CP-SAT geri dönüşü). İki aşamalı HiGHS ile yeniden çözüldü; aynı rota sayısı ve dakikayla `OPTIMAL`. 2026-10-17 yeniden koşusunda aynı davranış görüldü: iki aşamalı HiGHS bu hücreleri 2,8 s ve 44,3 s'de kanıtladı. En büyük hücrede (R=90, 45 170 kolon) ise 2026-10-15 budama deneyinde iki aşamalı biçimin 1. aşaması 120 s'de bitmedi; ağırlıklı biçim ≈80 s'de çözmüştü. İki biçimden hiçbiri her hücrede üstün değil. Ham ilk kayıt `wave_exact_4sw5so.jsonl` içinde duruyor; yeniden çözüm artık `resolve_two_stage.py` ile betikleşti. | kayıt notu | arşiv README §1; §11 |
| U2 | **Depodaki GA-Split'in açığı:** 19 hücre (7 temel dalga) suboptimal; hepsi n ≥ 6. 4 hücrede fazla rota var; bunlar 2 temel dalgadan geliyor (05.10 ve 07.10, 08:45 toplama). 15 hücrede rota sayısı aynı, süre daha uzun. Haftalık toplamda her R için 1 fazla rota; dakika farkı R=50/60/70/90 için 19/81/25/49 dk (%0,28/1,27/0,41/0,84). | [ÖLÇÜM] (kesin referansa karşı) | `wave_exact_vs_ga.csv`, `wave_summary_by_R.csv` |
| U3 | **ESN-SP v2** gerçek dalgalarda 227/228 hücrede optimum. Kalan hücre (05.10 08:45 toplama, R=90): rota sayısı aynı (3), 332 dk ile optimumdan 3 dk fazla. İhlal 0; ortanca süre 0,05 s, en çok 43,6 s. | [ÖLÇÜM] | `esn_real_v2.jsonl` |
| U4 | **ESN-SP v3, ölçek örnekleri** (S1: 19–27, S2: 38–54, S3: 76–108 yolcu; S3 bir günün iki katı alınarak üretildi). Eşit süreli GA'ya karşı birinci koşu: S1 3/1/1, S2 5/0/0, S3 3/0/2 (kazanç/beraberlik/kayıp). Aynı yapılandırmanın ikinci koşusunda 15 örneğin 3'ünde sonuç değişti (10-08 S2: 451→476 dk; 10-07 S2: 437→443; 10-05 S3: 906→909). Bu koşuda S2 4/0/1 oldu. Bütçe duvar saatine bağlı; tek koşu kıyasları gösterge niteliğindedir. | [ÖLÇÜM], düşük güven | `scale_esn_vs_ga.csv`, `esn_learned_vs_geo.csv` |
| U5 | **Sıralı kesin planlama**, yani her dalgayı kesin çözüp sonra araç atamak, GA tabanlı arşiv planına göre 2 gün hücresinde bir araç azaltıyor: Pazartesi R=60 (5→4) ve R=90 (4→3). | [ÖLÇÜM] | `day_level_4sw5so.csv` |
| U6 | **DAY-JOINT** (ortak gün modeli). Haftalık filo (günlerin en büyüğü), R=50/60/70/90 için: GA planı 6/6/6/4, sıralı kesin plan 6/6/6/4, ortak model **6/5/5/4**. Günlük: ortak model sıralı kesin plana göre **9/20 hücrede** bir araç azaltıyor; GA tabanlı plana göre 11/20 hücrede (fark U5'ten geliyor). | 19 hücre [KANIT] (filo + rota + dakika); Pazartesi R=90 [KANIT] yalnız filo | `day_joint_4sw5so.jsonl`, `day_level_4sw5so.csv`, `weekly_fleet_4sw5so.csv` |
| U6-not | Pazartesi R=90'da 1. aşama süre sınırına takıldı; 2. ve 3. aşama koşmadı. Filo = 3, sıralı planın LB0'a eşitliğiyle kanıtlı. Bu hücrenin rota ve dakika değerleri kanıtsız. En uzun kanıtlı çözüm 399,5 s sürdü (Pazartesi R=70). | kayıt notu | aynı |
| U7 | **Ortak modelin bedeli:** filo öncelikli amaç, dalga başına "önce en az rota" önceliğinden vazgeçiyor. Kanıtlı 19 hücrede sıralı plana göre toplam +3/+1/+4/+2 rota ve +47/+30/+86/+31 dk (R=50/60/70/90). Haftalık dakika: sıralı 6803/6369/6028/5813, ortak 6850/6399/6114/5844. Pazartesi R=90 için ortak sütunda sıralı değer kullanıldı. | [ÖLÇÜM]; politika kararı [AÇIK] | aynı |
| U8 | **LB0** (rotalamadan bağımsız filo alt sınırı): her dalga en az K*_w rota ister ve bu rotalar çapa çevresindeki meşguliyet penceresinde eşzamanlıdır. LB0, bu eşzamanlı ihtiyaçların zaman içindeki en büyük toplamıdır. Sıralı plan 4 hücrede, ortak plan 6 hücrede LB0'a eşit. LB0 yalnız filo aşaması için alt sınırdır; rota ve dakika aşamalarını kanıtlamaz. | [KANIT] (filo) | `day_level_4sw5so.csv` |
| U9 | **DAY-TYPED.** L = 3 büyük araçla haftalık sedan sayısı: kesin model **3/2/2/1**, depo kampanyası 4/3/3/1 (R=50/60/70/90). L = 1 bütün R'lerde olursuz. L = 2 haftası bütün R'lerde kanıtlı olursuz; R=90'da bir gün ayrıca çözülemedi. | [KANIT]/[ÖLÇÜM] | `weekly_typed_vs_campaign.csv`, `day_typed_vs_campaign.csv` |

## 4. TSP hattı bulguları (P1/P2)

| No | Bulgu | Etiket | Kanıt dosyası |
|---|---|---|---|
| T1 | **E2BSO, R2DMA ve P-AOEA kıyası** (6 TSPLIB örneği × 5 tohum = 30 çift). R2DMA, ILS'ten 27/30 çiftte kötü (Holm p = 1,6·10⁻⁴). E2BSO ile ILS arasında fark gösterilemedi (8/6/16; Holm p = 1,0). P-AOEA ile evrim bileşeni kapalı P-AOEA 30/30 çiftte aynı sonucu verdi; evrim bileşeninin bu ayarda etkisi yok. LKH 30/30 optimum. p-değerleri tohumları bağımsız sayıyor. | [ÖLÇÜM] | `bench_wilcoxon.csv`, `bench_summary_overall.csv` |
| T2 | **ILS-fast** (Numba; 2-opt + Or-opt + or-3opt; K = 10 aday): 10 örnek × 5 tohum × 30 s. ILS-fast 36/50 koşuda optimum, ortalama açık %0,058. Depodaki ILS 8 örnekte 15/40 koşuda optimum, ortalama açık %2,02. LKH (elkai) 50/50. Koşu düzeyinde ILS-fast deponun ILS'inden 25/15/0 (Holm p = 2,4·10⁻⁵). Örnek düzeyinde 8 örneğin 6'sında daha iyi, 2'sinde eşit. ILS-fast'ın LKH'ye kaybettiği 14 koşunun hepsi n ≥ 318 örneklerde. Kıyas eşit süreli değil: n ≥ 439'da LKH 43,8–65,3 s sürüyor ve elkai tohum almıyor. | [ÖLÇÜM] | `main_summary.csv`, `main_wilcoxon.csv` |
| T3 | **ATSP (ft53):** ILS-fast 10/10 koşuda optimum (10 s); LKH doğal ATSP modu 3/3. Tek örnek. | [ÖLÇÜM] | `atsp_summary.csv` |
| T4 | **K = 10 kalite ölçütü** (hızlı yerel arama, depodaki tam komşuluklu yerel aramadan en çok %0,5 kötü olmalı): rastgele başlangıçlarda ILS-fast kötü değil (a280: −%0,96). ILS'in asıl çalışma noktası olan kick'lenmiş yerel optimumlarda ölçüt sağlanmadı (a280: +%1,91, %95 GA [+0,11; +3,71]). K = 20 + or-3opt farkı nokta tahmini olarak kapatıyor. | [ÖLÇÜM] | `D1_summary.csv` |
| T5 | **Basit GPX (PX-ILS):** 4 örnek (pr439, rat783, pr1002, pcb1173) × 5 tohum. GPX açık–kapalı 7/5/8, p = 0,776. Örnek düzeyinde 1 iyi, 1 kötü, 1 eşit, 1 karışık. GPX2 test edilmedi. | [GÖSTERİLEMEDİ] | `gpx_wilcoxon.csv` |
| T6 | **Öğrenilmiş aday listesi** (elit birleşimi + 3 en yakın komşu), K = 10'a karşı, 4 örnek × 5 tohum: 11/1/8. Açık ölçeğinde Wilcoxon p = 0,79. Örnek düzeyinde 2 iyi, 2 kötü. K = 5 belirgin kötü (4/1/15; p = 0,001). | [GÖSTERİLEMEDİ] | `tsp_learned_cands.csv` |
| T7 | **Arazi analizi** (rd100, pr136, a280, lin318; 1000 yerel optimum + 100 ILS koşusu). En iyi 100 çözümün kenar birleşimi 1,81–2,63 kenar/düğüm ile optimum turun kenarlarının %100'ünü içeriyor. Bütün elitlerde ortak olan kenarların (44, 27, 42, 133 kenar) hepsi optimumda. Fazla maliyet ile optimuma uzaklık arasındaki korelasyon r = 0,24–0,59. | [ÖLÇÜM] | `landscape.json`, CS4 §3 |

## 5. Öğrenme bulguları

Model ayarları test katlarına bakılmadan baştan sabitlendi: GBM 200 ağaç, öğrenme hızı 0,05, 15 yaprak; LR C = 1. Ayar araması yapılmadı. Bölme gün bazlı (LODO). Aynı temel dalganın R kopyaları aynı katta kaldığı için sızıntı yok. Ancak etkin örnek sayısı 9 zor temel dalgadır.

| No | Bulgu | Etiket | Kanıt dosyası |
|---|---|---|---|
| O1 | **Ardıl yay tahmini** (n ≥ 6, LODO). AUC değerleri: GBM-geo 0,909; LR-geo 0,893; MUTUAL-RANK 0,855; DETOUR 0,807; GEO 0,764; FREQ 0,714. Recall@5 (270 ardıl): MUTUAL-RANK 0,956; GBM-geo 0,944; GEO 0,896. "Aynı rotada" hedefi için AUC: GBM-geo 0,812, GEO 0,719. | [ÖLÇÜM] | `lodo_metrics.csv`, `recall_at_k.csv` |
| O2 | **İleriye zincirleme** (yalnız geometrik özellikler, önceki günlerle eğitim): GBM-geo ardıl yay AUC 0,863–0,921. 4/4 günde GEO ve MUTUAL-RANK'tan yüksek. | [ÖLÇÜM] | `forward_chaining_auc.csv` |
| O3 | **Öncelik (sıra) doğruluğu**, n ≥ 6: LR-geo %77,9; RADIAL %72,0; FREQ %62,0. | [ÖLÇÜM] | `lodo_metrics.csv` |
| O4 | **Öğrenilmiş tasarruf yapıcısı:** yeniden sıralamayla 36 hücrede 9 fazla rota; Clarke–Wright'ta 3. | [ÖLÇÜM], olumsuz | `construct_learned_vs_cw.csv` |
| O5 | **Öğrenilmiş yay budama** (GBM-geo, k = 4; her düğümde ilk 4 giriş ve çıkış yayının birleşimi). Rota sayısı 36/36 hücrede korunuyor. Optimum dakika 30/36 hücrede korunuyor; temel dalga düzeyinde 9 dalganın 5'inde bütün R'lerde. Kaçırılan hücrelerde fark 1–5 dk, toplam 13 dk. Kolon payı %22. Geometrik budama (GEO, k = 4): kolon payı %32, optimum 27/36, rota sayısı 34/36. Bu kanıtsız bir elemedir; yalnız sezgisel modda kullanılabilir. | [ÖLÇÜM] | `prune_learned_arcs_summary.csv`, `prune_learned_arcs_all.csv` |
| O6 | **ESN-SP v3L** (öğrenilmiş komşuluk), v3'e (geometrik) karşı 15 örnekte 5/5/5 (CS4'te p = 0,95). Bütçe parametresi aynı, gerçekleşen süreler farklı. Komşuluk ve birleşim sırası birlikte değişti; tek faktörlü ablasyon yapılmadı. | [GÖSTERİLEMEDİ] | `esn_learned_vs_geo.csv` |
| O7 | **Genel sonuç:** Kenar tahmini başarılı, ama bu veride rota kalitesine dönüşmedi (O4–O6). P5'te rota içi sıra kesin ve ucuz çözüldüğü için orada öğrenmenin kalite katkısı mantıksal olarak sıfırdır (S6). Öğrenmenin olası değeri büyük örneklerde aday/kolon üretimi ve gün düzeyinde aday değeridir. Bu iki kol çok haftalık veri olmadan sınanamaz. | [ÖNERİ] | — |

## 6. Yapısal sonuçlar

| No | Sonuç | Etiket |
|---|---|---|
| S1 | **Alt küme ile dizi sayısı:** n = 20 ve rota başına en çok 9 yolcu için 431 909 alt küme, 66 449 027 200 sıralı dizi vardır (oran 153 850). Kesin model (alt küme, tip) üzerinden kurulmalıdır. | [KANIT] (aritmetik) |
| S2 | **Sonek olurluluğu:** Olurlu bir rotanın her soneki R ve kapasite bakımından olurludur; T bakımından olmayabilir. WAVE-EXACT R ve kapasiteyi DP içinde budar. T'yi aynı alt küme için en küçük kapalı süreye uygular; T bu toplamın üst sınırı olduğundan kontrol kesindir. | [KANIT] |
| S3 | **Ağırlıklı tek aşamanın sözlükselle eşdeğerliği:** Her rota ≤ T ve rota sayısı ≤ n olduğundan toplam dakika [0, n·T] aralığındadır. W > n·T ise ağırlıklı amaç W·rota + dakika, sözlüksel sıralamayla aynı sıralamayı verir. Bu veride n ≤ 20, T = 150, tamsayı dakika: n·T = 3 000 < W = 10 000. Koşul birime bağlıdır; saniyede n·T = 180 000 olur. Kodda `assert W > n_max·T` zorunlu olmalı. Eşdeğerlik ayrıca aynı süre sınırının ve aşama başına durum ile sınır kaydının tutulmasını ister. | [KANIT] (bu veri birimiyle) |
| S4 | **LB0'ın kapsamı:** LB0 yalnız filo aşamasının alt sınırıdır. Sıralı plan LB0'a eşitse filo optimumdur; rota ve dakika aşamaları için ayrıca sertifika gerekir. | [KANIT] |
| S5 | **Tek sıra sıkıştırması:** DP her (alt küme, tip) için tek bir en kısa sırayı saklar; eşit maliyetli alternatifler kaybolur. Üçüncü bir amaç eklenecekse (örneğin plan kararlılığı) DP eşit sıraları tutmalı ya da üçüncü aşama ayrı kolonlarla kurulmalı. | [KANIT] |
| S6 | **Rota içi sıra öğrenmesi (B-02):** P5'te bir rota en çok 9 yolcu taşır. Rota içi sıra Held–Karp ile kesin ve yaklaşık 2⁹·9² ≈ 4·10⁴ işlemle çözülür. Bu alt problemde öğrenmenin kalite kazancı olamaz; hız kazancının üst sınırı da bu küçük maliyettir. Hüküm yalnız bu alt problem içindir. | [KANIT] |
| S7 | **Kalite ve kararlılık:** Σ log p (öğrenilmiş olasılık) bir plan kararlılığı garantisi değildir. Etiketler çözücüden geldiği için öğrenilen şey çözücü davranışıdır. Kararlılık, önceki plana açık bir uzaklıkla tanımlanmalıdır (değişen yolcu–araç eşleşmesi, değişen kenar) ve öğrenmesiz kontrolle karşılaştırılmalıdır. | [KANIT] (mantıksal) |

## 7. Düzeltme tablosu

Eski belgelerdeki aşağıdaki ifadeler bu belgeyle düzeltildi. Satır numaraları ilgili dosyadadır. 1–14 numaralı kalemler Y §5'ten gelir. 15–19 numaralı kalemler bu belge için yapılan yeniden hesapta bulundu. 20–23 numaralı kalemler açık kalan düşük önemli denetim bulgularıdır. 24–27 numaralı kalemler yeniden üretim sırasında bulundu (Sürüm 2).

| # | Yer | Eski ifade | Geçerli ifade | Dayanak |
|---|---|---|---|---|
| 1 | AR:194 | "Olurlu rotanın her soneki olurludur" | R ve kapasite bakımından olurludur; T bakımından olmayabilir | S2; K F02 |
| 2 | AR:456, 644, 682, gün kartı | "Ortak gün optimumu" | Hedef başına durum: 19/20 hücrede filo + rota + dakika kanıtlı; Pazartesi R=90'da yalnız filo kanıtlı | U6; K F07 |
| 3 | AR, gün kartı | Gün amacı "önce araç sayısı, sonra araç-dakika" | Üç aşama: filo → toplam rota → dakika (özgün ifadede rota aşaması eksikti) | §1 P7 |
| 4 | AR:235, 635, 641, revizyon günlüğü; CS3:48, 60; CS1:35, 255 | "GPX katkısız / katkısı yok / fark yok" | Basit GPX ile katkı gösterilemedi (p = 0,776); GPX2 test edilmedi | T5; K F09, F16 |
| 5 | AR:77, 516, 640 | A6'nın P5 profili "çıkarıldı" | Küçük P5'te gereksiz; büyük P5 (n > 20) ve P8 için ertelendi | §8; K F09 |
| 6 | AR:379, 643, 788 | "n > 25'te uygulanamaz" | Ölçülen: n = 20'de sayım ≤ 8,64 s, bellek ≈100 MB; bellek 2ⁿ·n ile büyür; evrensel eşik yok | U1; K F12 |
| 7 | AR:368, 378 | "Bütçe yalnız süre raporudur" | Bütün aşamalar kapandığında yalnız süre raporudur | K F14 |
| 8 | AR:386, 391, 418–421 | Ağırlıklı geri dönüş, kanıtsız | S3 kanıtı ve `assert W > n_max·T` koşulu | S3; K F13 |
| 9 | CS4:15 ve ESN/TSP paragrafları | "Fark yok" | Fark gösterilemedi. ESN için: aynı bütçe parametresi, gerçekleşen süreler farklı | O6; K F16, F17 |
| 10 | CS4:327 (LAP) | "Kesin mod: hiç eleme yok" | Öğrenilmiş skora dayalı kanıtsız eleme yok; kanıtlı baskınlık ve alt sınır elemesi serbest. Kararlılık maddesi S7'ye göre yeniden yazılır | S5, S7; K F20, F21 |
| 11 | CS3, CS4, AR, BR | "36 dalga"; "GA 19 dalgada suboptimal" | "36 hücre (9 temel dalga)"; "19 hücre (7 temel dalga)" | §2, U2; K F15 |
| 12 | BR (S3/P8 geçen yerler) | "S3/P8" birlikte | S3 büyük sentetik P5'tir; P8 ayrı modeldir | §1; K F11 |
| 13 | BR:313 | "`_build_trips` kapasite aşımında ve eksik yayda `break`" | Ana bölümde kapasitede `break`, T ve R'de `continue`. Eksik yay için açık `break` yalnız zaman pencereli bölümde; orada da T/R `continue` | K F24 |
| 14 | L:215, 183, 209 | "LKH hem hızlı hem kesin"; "gerekir"; geniş genellemeler | LKH sezgiseldir ("bu deneylerde bilinen optimuma ulaştı"); "seçeneklerden biri"; genellemeler incelenen deneylerle sınırlı | K F08, F22 |
| 15 | CS1:20; CS3:62, 117; AR:73; Y:90 | "20 hücrenin 11'inde bir araç azaldı" (karşılaştırma tabanı yazılmamış) | GA tabanlı arşiv planına göre 11/20. Bunun 2'si sıralı kesin rotalamadan geliyor (U5). Ortak planlamaya atfedilebilen kısım, sıralı kesin plana göre **9/20** | U5, U6 |
| 16 | CS1, CS3, CS4, AR, BR'deki "228/228 kanıtlı optimum" | — | Doğru; ancak iki hücrenin ilk koşu kaydı ve yeniden çözüm notu (U1-not) birlikte verilmeli | U1 |
| 17 | CS1:240 ve dayanan ifadeler | "v3, S2'de 5/5 iyi" | Tek koşu. Aynı yapılandırmanın ikinci koşusunda 15 örneğin 3'ü değişti ve S2 4/0/1 oldu | U4 |
| 18 | CS1, CS2, CS3:60, AR:69 (TSP kıyasları) | Koşu düzeyi p-değerleri; "LKH 50/50" | Örnek düzeyi sayım eklenmeli (T1, T2). LKH kıyası eşit süreli değil: n ≥ 439'da 43,8–65,3 s; elkai tohum almaz | T1, T2; K F16 |
| 19 | CS4:10, 27; AR:616; BR:77 | TSP aday listesi "p = 0,78" | Açık ölçeğinde yeniden hesap p = 0,79; sonuç değişmez | T6 |
| 20 | 04_ALGORITHM_LITERATURE_SOTA:70; 05_algorithm_literature_table.csv:16 (K7) | Liao 2012 ve Feng & Liao 2014 "özetlerinde FCM + TSP geçer" | [DOĞRULANMADI]: özetler erişilemedi; bu iki kaynağın FCM + TSP içeriği tam metinle doğrulanmalı | denetim bulgusu |
| 21 | 02_CROSS_CHECK_CODEX_VS_SCIENCE:24 | "45 koşunun 0'ında kayıp görüldü" (pratikte olmuyor) | Bu düşük güçlü sondada gözlenmedi. E2BSO ve P-AOEA berlin52 ile rd100'de optimuma ulaştığı için kayıp orada görülemez; bilgilendirici örnek esas olarak eil76'dır | denetim bulgusu |
| 22 | 07_kaynakca_ek_2026-10-13.csv; CS4 ve L'deki ilgili künyeler | Etiket ve yıl uyuşmazlıkları | CrossRef'le doğrulandı (2026-10-17): Tinós, Whitley & Ochoa **2020**, *Evol. Comput.* 28 ("Tinos2018" etiketi yanlış); Ochoa & Veerapen **2018**, *J. Heuristics* 24 (çevrimiçi 2017); Stützle & López-Ibáñez **2019** (çevrimiçi 2018); Sun vd. **2021**, *OR Spectrum* 43 (çevrimiçi 2020). Kural: cilt yılı, parantezde çevrimiçi yıl | denetim bulgusu |
| 23 | BR §0.1, Rev-CS-B26 satırı | Kaçışsız `\|` karakteri tabloyu bozuyor | Biçim hatası; içerik bu belgede geçerli | denetim bulgusu |
| 24 | Bu belgenin 1. sürümü, U1 | "Alt küme DP + iki aşamalı sözlüksel küme bölümleme" | 226 hücre tek aşamalı ağırlıklı amaçla (S3 ile sözlükselle eşdeğer), 2 hücre iki aşamalı çözüldü. Optimallik iddiası doğrudan S3'e dayanır | `run_waves.py` incelemesi |
| 25 | Bu belgenin 1. sürümü, O2 | "0,862–0,921" | 0,863–0,921 (en küçük değer 0,8627) | `dogrula.py` |
| 26 | Bu belgenin 1. sürümü, §9, §11 | "Temiz ortamda yeniden çalıştırma yapılmadı"; "TSPLIB dosyalarından yalnız ft53 doğrulandı" | Ana hatlar yeniden koşturuldu (§11). 15/15 TSPLIB dosyası depo kopyasıyla SHA-256 düzeyinde aynı | yeniden üretim |
| 27 | CS4 ve CS1 yeniden üretilebilirliği | Öğrenme tablolarının sürücüsü, `prune_in.pkl` ve gün tablosunun kodu yalnız çekirdekteydi | Arşivlenmiş konuşmadan birebir aktarılıp `run_lodo.py` ve `gun_duzeyi.py` olarak betikleşti; çıktılar arşivle aynı (§11) | yeniden üretim |

## 8. Birleşik tasarım kararları

| Konu | Nihai karar | Dayanak |
|---|---|---|
| P5 dalga (A4 CRP) | **WAVE-EXACT birincil kesin referans** (bu veride n ≤ 20). Daha büyük n'de ya da süre aşımında kısıtlı havuz / ESN-SP sezgisel olarak kullanılır. Kesin modda öğrenilmiş kanıtsız eleme yapılmaz. Küme bölümleme aynı süre bütçesiyle iki biçimde denenir (ağırlıklı tek aşama ve iki aşama; biri ötekinin geri dönüşü) ve aşama başına durum kaydedilir. | U1, U1-not, S1–S3; K M3 |
| P7 gün (A5 ADRPLNS) | **DAY-JOINT / DAY-TYPED + LB0 birincil.** Hedef başına durum alanları tutulur (`fleet_optimal`, `routes_optimal`, `minutes_optimal`). LNS yalnız ölçek profilinde. Filo mu rota mı önceliği sahibin kararıdır. | U5–U9; K M3 |
| TSP (A1 CPILS) | **ILS-fast + FE muhasebesi.** K = 16–20 ILS düzeyinde denenir. GPX2 ertelendi: basit GPX sonucundan GPX2 hakkında hüküm çıkarılmaz; ayrı test ister. | T2, T4, T5; K F09 |
| ATSP (A2 DCILS) | Korunur: ILS-fast yönlü modu. elkai doğal ATSP yalnız akademik referans (lisans). | T3 |
| A3 VHGS-Split | Üretim P5/P6'da ertelendi; yoğun ve büyük ölçekte (S3) korunur. | U4 |
| A6 PRALNS | Küçük P5'te gereksiz; büyük P5 (n > 20) ve P8 için ertelendi. | K F09, M7 |
| A7 DCRM, ERPL operatör seçimi | Sınırlı pilot; nötr ya da olumsuz sonuçta durdurulur. | K M6, §7.5 |
| ERPL M0/M1 | Yoğun ve büyük dalgalar ile P8 için kolon üreteci. Küçük örneklerde WAVE-EXACT oracle'ı ile yalnız sağlık kontrolü. | K F10 |
| ERPL M2/M3 (rota içi sıra öğrenme) | P5'te kaldırıldı (S6). P8/PDP'de yeniden değerlendirilebilir. | S6 |
| Öğrenme, örnekler arası aşama | Çok haftalık veri gelene kadar ertelendi. | O7; K M5 |
| P8 | Ayrı model, decoder ve doğrulayıcı tamamlanmadan sonuç yazılmaz. | K M7 |
| İddia dili | "Araştırma adayı / dış prototip bildirimi". | K M8 |
| Codex M1–M8 | M1, M2, M3, M6, M7, M8 kabul. M5 veri koşuluyla kabul. M4 (P5 indirgeme araştırması) gün düzeyi çalışmasından sonraya alındı. | Y §4 |

## 9. Açık konular ve kapatma işleri

| Konu | Durum | Kapatan iş |
|---|---|---|
| Filo mu rota mı önceliği (U7) | Sahibin kararı | İki politikanın haftalık maliyeti U7'de hazır |
| Pazartesi R=90 rota/dakika | Kanıtsız | Daha uzun süre sınırı ya da güçlendirilmiş model; aşama durumlarının kaydı |
| Akademik öncelik (Codex: önce P5 indirgeme; Claude Science: önce gün düzeyi) | Ayrışma sürüyor | Gün düzeyi yenilik taraması (tam metin) ve P5'te sade DP'ye karşı durum sayısı ölçümü. İkisinin sonucuna göre sıra kararı |
| Küçük P5'te ERPL (F10) | Kısmi katılım | Yalnız oracle parite testi; düşük öncelik |
| Çok haftalık veri | Yok | Birkaç haftalık gerçek veri ya da gerçek veriden kalibre edilmiş üreteç |
| Yeniden üretim paketi | Ana hatlar yapıldı (§11) | Kalan: yay budama, ESN-SP koşuları, TSP kıyasları, arazi analizi; üç küçük öğrenme tablosunun sürücüsü |
| GPX2; K = 16–20 | Ertelendi | ILS-fast + FE muhasebesinden sonra |
| TSPLIB dosyalarının depo kopyasıyla doğrulanması | **Kapandı:** 15/15 dosya SHA-256 düzeyinde aynı | — |
| Makine belleği | Çalışma sırasında 1–3 GiB boş bellek; en zor HiGHS çözümleri `MemoryError` verebiliyor | Büyük hücreleri tek başına çalıştırmak; bellek korumalı sarmalayıcı (paket README) |
| ESN-SP tekrarlanabilirliği | Duvar saati bütçeli | İterasyon ya da FE bütçesi; çoklu koşu |

## 10. Akademik yol haritası

### 10.1 Ana çalışma: tek ve bütünlüklü

**Çalışma sorusu.** Ortam: sabit çapa zamanlı dalgalar, iki kapasite havuzu, yönlü ve metrik olmayan süreler, gün içinde yeniden kullanılan araçlar. Bu ortamda her dalgayı ayrı ayrı en iyi planlamak ile günü ortak planlamak arasındaki fark ("sıralı planlamanın bedeli") ne kadardır ve hangi koşullarda ortaya çıkar?

**Bileşenler:**
1. P5 kesin dalga çözücüsü: alt küme DP + iki aşamalı küme bölümleme (S1–S3).
2. Olay-noktası eşzamanlılık modeli ve LB0 (S4).
3. Üç aşamalı sözlüksel gün modeli ve tipli filo (U6, U9).
4. Gerçek veri analizi; R ve araç tipi duyarlılığı.
5. Filo–rota ödünleşimi (U7).

**Mevcut kanıt:** U1, U5–U9; tek hafta.

**Hakemin soracağı eksikler:**
- **Veri.** Tek hafta ve 9 zor temel dalga yetmez. Birkaç haftalık gerçek veri ya da gerçek veriden kalibre edilmiş bir örnek ailesi gerekir. Bu, ana çalışmanın kritik yoludur.
- **Yenilik.** Mingozzi, Roberti & Toth (2013) çok seferli VRP için kesin yöntem sunar. Okul servisi çizelgeleme literatürü de yakın öncüldür (Fügenschuh 2009; Park & Kim 2010; Ellegood vd. 2020). Bunlar tam metinle karşılaştırılmalı. "Rotaları gün boyunca birlikte seçtik" tek başına yenilik değildir (K §7.3). Katkı; problem sınıfı, kesin model, LB0 ve sıralı planlamanın bedelinin ölçümü üzerinden kurulmalıdır.
- **Doğrulama.** Çalıştırılabilir yeniden üretim paketi (§11) ve ikinci bir referans olarak genel MIP/CP modeli.

Yayın kabulü garanti değildir.

### 10.2 Ana çalışmayı tekrar etmeyen ek çıktılar

- **Proje önerisi.** Açık sorular ayrı iş paketleri olarak ele alınabilir: çok haftalık veri toplama, gün düzeyi öğrenme kolu (M5) ve P8. Öneri ana makalenin sonuçlarını yeniden sunmaz; onları başlangıç noktası olarak anar.
- **İkinci makale yalnız şu koşullardan biri gerçekleşirse yazılır:**
  - P5 için öncüllerden farklı, kanıtlı ve hesaplama katkısı ölçülmüş yeni bir indirgeme kuralı bulunursa (M4);
  - gün düzeyi öğrenme, ayrılmış test haftalarında öğrenmesiz kontrolü geçerse.
- **TSP hattı.** Şu an yayın katkısı taşımıyor. ILS-fast bir mühendislik kazanımıdır. E2BSO/R2DMA/P-AOEA bulguları (T1) depo içi karar girdisidir.

### 10.3 Parçalı yayını önleme kuralı

1. Her çıktının kendi araştırma sorusu ve kendi kanıtı olmalı.
2. Aynı tablo iki çıktıda ana sonuç olarak yer almamalı.
3. Ana çalışma tamamlanmadan ikinci makale yazılmamalı.

## 11. Yeniden üretim durumu

İki katman var:
- [nihai_kanit_arsivi_2026-10-17/](nihai_kanit_arsivi_2026-10-17/README.md): ilk koşuların kodu ve ham sonuçları, SHA-256 özetleriyle (88 dosya + 48 depo girdisi).
- [yeniden_uretim_paketi_2026-10-17/](yeniden_uretim_paketi_2026-10-17/README.md): göreli yollarla çalışan betikler, tek giriş noktası (`surucu/calistir.py`), sayı doğrulama (`dogrula.py`) ve arşiv karşılaştırması (`karsilastir.py`).

2026-10-17 yeniden koşusunun sonuçları (aynı makine ve ortam):

| Hat | Sonuç |
|---|---|
| Belgedeki sayılar (`dogrula.py`) | 61 kontrolün 61'i geçiyor (O2 düzeltmesinden sonra) |
| TSPLIB girdileri | 15/15 dosya depo kopyasıyla SHA-256 düzeyinde aynı |
| Dalga, WAVE-EXACT | 228/228 hücre yeniden çözüldü; rota sayısı ve dakika 228/228 aynı; hepsi `OPTIMAL` (225 ağırlıklı HiGHS, 2 iki aşamalı HiGHS, 1 CP-SAT); sertifika ihlali 0 |
| Gün, DAY-JOINT | 19/20 hücrede filo, rota, dakika ve üç aşama durumu aynı. Pazartesi R=90 iki koşuda da çözülemedi (arşivde süre sınırı, yeni koşuda bellek) |
| Gün tablosu (GA filosu, sıralı plan, LB0, bağımsız plan denetimi) | 12 sütun 20/20 hücrede aynı; haftalık filo tablosu birebir aynı. Pazartesi R=90 filosu iki koşuda da sıralı plan = LB0 = 3 ile kanıtlı |
| Öğrenme (LODO) | `lodo_metrics.csv` 42/42 satır, en büyük mutlak fark 0,0; `recall_at_k.csv` fark 0,0; yapıcı tablosu 1840/1840 satır aynı |

**Yeniden koşturulmayanlar:** yay budama (`prune_exp.py`; girdisi `prune_in.pkl` yeniden üretildi), ESN-SP koşuları (duvar saatine bağlı; U4), TSP kıyasları, arazi analizi, E2BSO/R2DMA/P-AOEA kıyası. `lodo_auc_by_day.csv`, `forward_chaining_auc.csv` ve öznitelik önemi tablosunun sürücüleri yeniden kurulmadı.

**Ortam notları:**
- Korumalı Windows ortamında joblib iş parçacığı havuzu açılamıyor. `run_lodo.py` HistGBM kutulamasını tek işçiyle çalıştırır; sonuç değişmez (öğrenme satırı).
- Bu makinede en zor HiGHS çözümleri bellek yetmediğinde düşebiliyor. Pazartesi R=70 ve 09.10 R=90 gün hücreleri ancak tek başına çalıştırıldığında çözüldü.

## 12. Sıradaki işler (öncelik sırası)

1. Yeniden üretim paketinin kalan hatları: yay budama, ESN-SP (FE ya da iterasyon bütçesiyle, çoklu koşu), TSP kıyasları; üç küçük öğrenme tablosunun sürücüsü.
2. Kodda hedef başına durum alanları, `assert W > n_max·T` ve iki biçimli küme bölümleme (U1-not); Pazartesi R=90 aşamalarının kapatılması.
3. Çok haftalık veri ya da kalibre edilmiş üreteç.
4. Gün düzeyi yenilik taraması (tam metin).
5. Üretim: WAVE-EXACT ve DAY-JOINT/TYPED'ın sözleşme testleriyle `uniride_core`'a alınması; filo politikasının sahip tarafından seçilmesi.
6. M4: P5 indirgeme araştırması.
7. Koşullu: ERPL/A7 sınırlı pilot; GPX2.

## 13. Temel kaynaklar

DOI'ler CrossRef'te doğrulandı (2026-10-15 – 2026-10-17).

- Held, M. & Karp, R. M. (1962). *J. SIAM* 10(1). doi:10.1137/0110015
- Mingozzi, A., Roberti, R. & Toth, P. (2013). *INFORMS J. Comput.* doi:10.1287/ijoc.1110.0495
- Prins, C., Labadi, N. & Reghioui, M. (2009; çevrimiçi 2008). *Int. J. Prod. Res.* doi:10.1080/00207540802426599
- Morabit, M., Desaulniers, G. & Lodi, A. (2021). *Transp. Sci.* doi:10.1287/trsc.2021.1045
- Morabit, M., Desaulniers, G. & Lodi, A. (2023). *INFORMS J. Optim.* doi:10.1287/ijoo.2022.0082
- Fügenschuh, A. (2009). *EJOR*. doi:10.1016/j.ejor.2007.10.055
- Park, J. & Kim, B.-I. (2010). *EJOR*. doi:10.1016/j.ejor.2009.05.017
- Ellegood, W. A. vd. (2020). *Omega*. doi:10.1016/j.omega.2019.03.014
- Cordeau, J.-F. & Laporte, G. (2003). *Transp. Res. B*. doi:10.1016/S0191-2615(02)00045-0
- Gschwind, T. & Irnich, S. (2015). *Transp. Sci.* doi:10.1287/trsc.2014.0531
- Boese, K. D., Kahng, A. B. & Muddu, S. (1994). *Oper. Res. Lett.* doi:10.1016/0167-6377(94)90065-5
- Ochoa, G. & Veerapen, N. (2018; çevrimiçi 2017). *J. Heuristics* 24. doi:10.1007/s10732-017-9334-0
- Tinós, R., Whitley, D. & Ochoa, G. (2020). *Evol. Comput.* 28. doi:10.1162/evco_a_00254
- Wasserstein, R. L. & Lazar, N. A. (2016). *Am. Stat.* doi:10.1080/00031305.2016.1154108

Ropke & Pisinger (2006, ALNS) ve Reijnen vd. (2024, DR-ALNS) için K'deki künyeler kullanıldı; bu belgede ayrıca doğrulanmadı.
