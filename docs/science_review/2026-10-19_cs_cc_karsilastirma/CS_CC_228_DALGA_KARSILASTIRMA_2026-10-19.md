# Claude Science ↔ Claude Code: 228 dalga kesin çözüm ve gün düzeyi karşılaştırması

**Tarih:** 2026-10-19 · **Kapsam:** salt okunur karşılaştırma (CC sonuçları `git show WIP:` ile okundu; WIP ucu `a3a5039e`, karşılaştırılan CC dosyaları çıkarıldıkları andan beri bayt düzeyinde değişmedi) · **Hafta:** 2026-10-05 haftası, filo `single_4sw5so`, R ∈ {50, 60, 70, 90}, T = 150

## Kısa hüküm

1. **Dalga düzeyi (228 dalga): berabere.** İki taraf her dalgada aynı optimumu buldu (K* ve D* 228/228 eşit). Aday rota sayıları da aynı (228/228, toplam 83.008). Bağımsız denetleyicide iki tarafın da ihlali 0. Farklı rota setleri yalnızca 7 dalgada var ve hepsi eş-optimal alternatif.
2. **Kanıt ve mühendislik kalitesi: Claude Code önde.** CC'nin sonuçları üretim kodundan geliyor. Çift çözücü kanıtı (Gurobi 13.0.3 + HiGHS 1.15.1, 228/228 uyum), TDD, inceleme kayıtları, kod-commit'li manifestler ve TS CLI ile bağımsız aralık denetimi var. CS sonuçları prototip betiklerden üretildi.
3. **Gün düzeyi: Claude Science önde.** CC, sahip kararı EQ3 gereği global gün modelini kapsam dışı bıraktı ve yalnızca menü-koşullu seçim yaptı. CS ise global ortak gün modelini çözdü.
   - Homojen filoda haftalık filo R60 ve R70'te 6 → 5 araca iniyor.
   - Tipli filoda (L = 3 büyük araç) haftalık sedan ihtiyacı R50/60/70'te 4/3/3 → 3/2/2.
   - CC'nin "uygunsuz" etiketlediği 2 hücre (Salı R70 ve R90, L = 2) aslında uygun.
   - Bu planların tamamı bağımsız denetimden hatasız geçti.
4. **Genel sonuç:** CC daha sağlam, CS daha ileri gidiyor. Makale ve tez için kanonik sayılar CC'den alınmalı. CS'in ortak gün modeli (LB0 + joint MIP) ise CC'ye yeni bir iş paketi olarak taşınmalı; ikisinin birleşimi tek başına her birinden daha güçlü.

## 1. Kaynaklar

| | Claude Code (CC) | Claude Science (CS) |
|---|---|---|
| Dalga sonuçları | `docs/paper/results/week-2026-10-05-exact/wp-e3-goal1-single/` (`wave_gaps.csv`, `exact_routes.json`), koşu commit'i `85481b07` | `docs/science_review/2026-10-13/astra6_design_brief/yeniden_uretim_paketi_2026-10-17/ciktilar/wave_exact_rerun_resolved.jsonl` |
| Dalga çözücüsü | AMPL + Gurobi 13.0.3; HiGHS 1.15.1 ile yeniden çözüm (228/228 uyum) | HiGHS (225 ağırlıklı tek aşama, 2 iki aşamalı), CP-SAT (1); lisans gerekmez |
| Gün düzeyi (tipli) | `wp-e4b-union-day/day_gaps.csv`: GA ∪ dalga-kesin menüleri üzerinde CP-SAT 9.15, kod commit'i `12c0f80`; kendi iddiası "global gün optimumu değildir" | `nihai_kanit_arsivi_2026-10-17/uretim_dalga_gun/sonuc/day_typed_vs_campaign.csv`, kod `run_day_typed.py`: sabit L için global en az sedan S |
| Gün düzeyi (homojen) | Yok (WP-E6 `day_sums.csv` yalnız dalga boşluklarını topluyor) | `yeniden_uretim_paketi_2026-10-17/ciktilar/gun/day_level_4sw5so.csv`, plan dosyası `day_joint_4sw5so.jsonl`, kod `run_day_joint.py` |
| Araç tipleri | büyük 4 Sw / 5 So, sedan 0 Sw / 4 So, cooldown 10 dk (DECISION_LOG) | aynı (`TYPES`, `COOL = 10`) |
| Meşguliyet aralığı | pickup [a − süre, a), dropoff [a, a + süre), meşgul sonu + 10 dk, yarı açık (`typed_day_selection.py`) | aynı kural |

CS kodu ve çıktıları `docs/science-review-2026-10` dalında (commit `74f28f5e`) bulunuyor.

## 2. Dalga düzeyi (228 dalga × R)

| Ölçüt | Sonuç |
|---|---|
| Eşleşen satır | 228/228 |
| K* (rota sayısı) eşit | 228/228 |
| D* (toplam süre, dk) eşit | 228/228 |
| Aday rota (kolon) sayısı eşit | 228/228 (toplam 83.008 / 83.008) |
| Aynı yolcu gruplaması | 221/228 |
| Aynı sıralı rotalar | 209/228 |
| Bağımsız denetleyici ihlali | CC 0 · CS 0 · GA 0 |
| Yeniden hesaplanan D = beyan edilen D | CC 228/228 · CS 228/228 · GA 228/228 |
| GA'nın alt-optimal olduğu dalga | 19 (4'ünde fazladan 1 rota) |

Bağımsız denetleyici kendi kodum. Arşivlenmiş `*.matrix.json` dosyalarını kullanıyor ve şunları kontrol ediyor: kapsama, ayrı Sw ≤ 4 ve So ≤ 5 kapasitesi, yayların varlığı, tur ≤ 150, binme ≤ R. Pickup'ta ilk bacaktan sonraki bacaklar, dropoff'ta son bacaktan önceki bacaklar sayılıyor.

R'ye göre toplamlar (CC = CS):

| R | ΣK* | ΣK_GA | ΣD* (dk) | ΣD_GA (dk) |
|---|---|---|---|---|
| 50 | 108 | 109 | 6803 | 6822 |
| 60 | 93 | 94 | 6369 | 6450 |
| 70 | 81 | 82 | 6028 | 6053 |
| 90 | 72 | 73 | 5813 | 5862 |

Rota setleri farklı olan 7 dalganın hepsi eş-optimal alternatif (aynı K ve D):
- `2026-10-05:pickup:525` (R50: 6 rota / 433 dk; R90: 3 / 329)
- `2026-10-06:dropoff:975` (R50: 2 / 142)
- `2026-10-06:pickup:525` (R50: 4 / 270)
- `2026-10-07:pickup:705` (R70: 2 / 161)
- `2026-10-08:dropoff:735` (R50: 2 / 116)
- `2026-10-09:pickup:525` (R90: 3 / 277)

**Yorum:** Çözüm kalitesinde fark yok. Aday rota sayılarının da birebir aynı çıkması, iki bağımsız uygulamanın aynı uygun rota kümesini tanımladığını gösteriyor; bu güçlü bir çapraz doğrulama. Çalışma süreleri karşılaştırılmadı, çünkü çözücüler ve makine yükü farklı.

## 3. Gün düzeyi — tipli filo (büyük + sedan, L = 1, 2, 3; 60 hücre)

| Kategori | Hücre |
|---|---|
| İkisi de uygunsuz | 26 |
| Eşit sedan sayısı | 19 |
| **CS daha az sedan (her birinde −1)** | **12** |
| **CS uygun, CC menüsü uygunsuz** | **2** (2026-10-06 R70 L2: S = 2, 1244 dk; 2026-10-06 R90 L2: S = 2, 1186 dk) |
| CS açık (S ∈ {1, 2}); CC menü sonucu 2 | 1 (2026-10-05 R90 L2) |
| CC daha az sedan | **0** |

Üç yöntemin de uygun olduğu 30 hücrede toplam sedan sayısı: GA menüsü 61, CC birleşik menü 57, CS global 45.

Haftalık sedan ihtiyacı (L = 3; diğer L'lerde en az bir gün uygunsuz):

| R | GA menüsü | CC birleşik menü | CS global |
|---|---|---|---|
| 50 | 4 | 4 | **3** |
| 60 | 3 | 3 | **2** |
| 70 | 3 | 3 | **2** |
| 90 | 1 | 1 | 1 |

**Bağımsız denetim:** CS'in 32 tipli gün planının tamamı 0 hatayla geçti. Kontrol edilenler:
- günün tüm dalgalarında kapsama;
- araç tipine göre kapasite (sedan 0 Sw);
- yaylar, tur ve binme sınırları;
- büyük araç tepe eşzamanlılığı ≤ L;
- sedan tepesi = S;
- dakika toplamları.

Aralık kuralı CC'nin `typed_day_selection.py` kuralıyla aynı. CC README'sine göre hiçbir kesin rota hizmet günü dışına taşmıyor; pencere dışı diye elenen seçenek sayısı 60 hücrenin hepsinde 0. Dolayısıyla CS'in kazancı farklı bir varsayımdan gelmiyor.

**Bedeli:** CS'in daha az sedan kullandığı 12 hücrede toplam süre 15.339 dk, CC'de 15.082 dk (+257 dk, %1,7). Eşit hücrelerde CS 22.198 dk, CC 22.213 dk.

**Yorum:** CC'nin `both_infeasible_for_L` etiketi menü-koşullu bir uygunsuzluk anlamına geliyor. Tez veya makale metninde "L = 2 ile uygunsuz" gibi bir cümle kurulmamalı: 2 hücrede uygun plan var. CS'in 26 uygunsuzluk kararı çözücü durumuna dayanıyor ve bağımsız bir uygunsuzluk sertifikası yok.

## 4. Gün düzeyi — homojen filo (`single_4sw5so`, 20 hücre)

CC'nin bu filo için bir gün modeli yok. Adil bir karşılık kurmak için her iki tarafın dalga-kesin rotalarını aynı aralık grafiğine yerleştirip **sıralı gün filosunu** hesapladım. Sonuç 20/20 hücrede CC = CS ve CS'in kayıtlı `seq_fleet` değeriyle de aynı.

| R | GA (arşiv) | Sıralı (CC = CS rotaları) | **CS ortak (joint)** | LB0 |
|---|---|---|---|---|
| 50 | 6 | 6 | 6 | 6 |
| 60 | 6 | 6 | **5** | 4 |
| 70 | 6 | 6 | **5** | 4 |
| 90 | 4 | 4 | 4 | 3 |

- Hücre düzeyinde ortak model GA'dan 11/20, sıralı plandan 9/20 hücrede 1 araç daha az kullanıyor. Toplam araç-gün: GA 94, sıralı 92, ortak 83, LB0 63.
- Kanıt durumu: 19 hücre "joint MIP optimal". 2026-10-05 R90 hücresinde MIP zaman sınırına takıldı; ancak sıralı plan K = 3 = LB0 olduğu için optimallik yine kanıtlı. Bu hücrenin K = 3 değerini iki tarafın rotalarından ben de yeniden hesapladım.
- Bağımsız denetim: CS'in 19 ortak planı 0 hatayla geçti (kapsama, kapasite, sınırlar, tepe = K, dakika toplamları, başlangıç/bitiş kuralı).
- Hiçbir dalga K*'tan az rota kullanmıyor; 10 dalga 1 fazla rota kullanıyor.
- Bedeli: 19 hücrede toplam süre 23.904 dk. Dalga optimumlarının toplamı 23.710 dk (+194 dk, %0,8), GA 23.849 dk.

**Yorum:** Dalga bazında optimum rotaları sabitleyip günü sonradan planlamak araç sayısını düşürmüyor (sıralı ≈ GA). Kazanç ancak rotaların gün düzeyinde ortak seçilmesiyle ortaya çıkıyor. Bu, bu karşılaştırmadaki en özgün bulgu: araç sayısında yaklaşık %12 düşüş (94 → 83), toplam sürede ise %1'in altında artış.

## 5. Boyut boyut kim daha iyi?

| Boyut | Önde | Gerekçe |
|---|---|---|
| Dalga çözüm kalitesi | Berabere | K*, D* ve aday rota sayıları 228/228 aynı |
| Dalga optimallik kanıtı | CC | Gurobi + HiGHS çift çözücü, üretim kodu, manifest |
| Gün düzeyi çözüm kalitesi | **CS** | Global ortak model; 12 + 2 hücrede daha iyi ya da uygun, hiçbir hücrede kötü değil |
| Gün düzeyi kapsamı | CC | CC Doblo (cap3) filosunu da çözdü (60 hücre, birleşik menü GA'dan 7 hücrede iyi); CS çözmedi |
| Yazılım mühendisliği ve tekrar üretilebilirlik | CC | TDD, inceleme, testler, kanonik veri yolu |
| Lisans ve erişim | CS | Yalnız açık kaynak çözücüler (HiGHS, CP-SAT) |
| Açık noktalar | CS'te 2 | Pazartesi R90 L2 tipli hücre açık; 26 uygunsuzluk kararı sertifikasız |

## 6. Öneriler

1. **CC'ye yeni iş paketi: global ortak gün modeli.** Kapsanacaklar: LB0 alt sınırı, homojen ve tipli joint MIP, Doblo cap3 dahil. Bu, EQ3 kararının yeniden açılması demek; karar sizin. Gerekçesi şu: makalede en yeni katkı olan 94 → 83 araç-gün ve haftalık 6 → 5 sonuçları ancak bu modelle elde ediliyor.
2. **Etiket dili:** CC çıktılarında `both_infeasible_for_L` ve `ga_menu_infeasible_for_L` etiketleri metinde "menü üzerinde uygunsuz" diye yazılmalı. Salı R70 L2 ve R90 L2 için uygun planlar var.
3. **Regresyon testi:** 7 eş-optimal dalga ile bu rapordaki bağımsız denetleyicinin mantığı, CC test setine "eş-optimal alternatif kabul" testi olarak eklenebilir.
4. **CS tarafında kapatılacaklar:** Pazartesi R90 L2 (S ∈ {1, 2}) hücresi; 26 uygunsuzluk kararı için basit bir sertifika (ör. zorunlu büyük araç tepe sayısı > L); tipli modelin Doblo cap3 için de çalıştırılması.
5. **Akademik kullanım:** Dalga düzeyindeki kesin ve GA boşluğu sonuçları CC'nin kanonik verisiyle raporlanmalı. Gün düzeyindeki ortak model ayrı bir yöntemsel katkı. Böylece iki makale salam dilimleme olmadan ayrışıyor: biri dalga kesin/sezgisel boşluğu, diğeri gün düzeyi filo optimizasyonu.

## 7. Sınırlar

- Tek hafta (2026-10-05), tek GA tohumu (42). Sonuçlar başka haftalar için genellenemez.
- Çalışma süreleri karşılaştırılmadı (farklı çözücüler ve makine yükü).
- CS'in uygunsuzluk ve optimallik kararları çözücü durumlarına dayanıyor. Bağımsız olarak denetlediğim şey planların uygunluğu; alt sınırların doğruluğunu ayrıca denetlemedim.
- Bağımsız denetleyici benim kodum, CC'nin üretim doğrulayıcısı değil.

## Ek: CC için köprü notu (kopyalanabilir)

> Claude Science, WP-E3 (228 dalga) ve WP-E4b sonuçlarını salt okunur olarak karşılaştırdı (WIP `a3a5039e`).
> - Dalga düzeyi: K*, D* ve kolon sayıları 228/228 aynı. 7 dalgada eş-optimal alternatif rota seti var (liste rapordaki §2).
> - Gün düzeyi: `docs/science-review-2026-10` dalındaki `run_day_joint.py` ve `run_day_typed.py` global ortak gün modelini çözüyor.
>   - large+sedan için CS, 12 hücrede birleşik menüden 1 sedan daha az buluyor.
>   - 2026-10-06 R70/R90 L2 hücreleri uygun.
>   - single_4sw5so için haftalık filo R60/R70'te 6 → 5.
>   - Planlar `day_typed.jsonl` ve `day_joint_4sw5so.jsonl` dosyalarında; aralık kuralı `typed_day_selection.py` ile aynı.
> - Öneri: EQ3'ü yeniden değerlendirmek için bir iş paketi (LB0 + joint MIP, üretim kodunda, HiGHS ile), etiket dilinin "menü üzerinde uygunsuz" olarak düzeltilmesi ve eş-optimal regresyon testi.

## Ekli tablolar

- [cs_cc_dalga_karsilastirma_228.csv](cs_cc_dalga_karsilastirma_228.csv): dalga × R, 228 satır
- [cs_cc_gun_tipli_large_sedan_60.csv](cs_cc_gun_tipli_large_sedan_60.csv): tarih × R × L, 60 satır
- [cs_cc_gun_homojen_4sw5so_20.csv](cs_cc_gun_homojen_4sw5so_20.csv): tarih × R, 20 satır
