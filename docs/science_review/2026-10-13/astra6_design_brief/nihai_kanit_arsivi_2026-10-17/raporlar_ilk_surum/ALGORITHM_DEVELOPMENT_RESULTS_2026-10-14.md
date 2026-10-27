# UniRide: yeni algoritmaların geliştirilmesi ve ölçümü

Tarih: 2026-10-14. Çerçeve: [yeniden tasarım planı]({{artifact:7fc7357d-8682-4559-95d9-7914690ad5be}}) ve [Astra 6 görev tanımı]({{artifact:f018302d-06cd-4fb2-a445-2afa5e78eb81}}) içindeki P1–P8 problem sözleşmeleri.

Bu çalışma iki hatta yürüdü:
- **Üretim hattı (P5–P7):** Bu oturumda doğrudan yürütüldü.
- **TSP/ATSP hattı (P1–P2):** Ayrı bir alt ajan yürüttü; ayrıntılı raporu [TSP_FAST_LS_REPORT.md]({{artifact:3183a1f1-7ee6-46fe-8a59-dbc75c72252f}}).

Depo dosyalarında değişiklik yapılmadı. Bütün kod ve sonuçlar artefakt olarak kaydedildi.

## Kısa özet

1. **Dalga için kesin çözücü (WAVE-EXACT).**
   - Arşivlenmiş haftanın 228 dalgasının **228'i kanıtlanmış optimumla** çözüldü (4 Sw/5 So, T=150, R ∈ {50, 60, 70, 90}).
   - Toplam çözüm süresi ≈ 4 dk, dalga başına medyan 0,014 s.
   - Mevcut üretim yöntemi GA-Split 19 dalgada optimum değil: 4 dalgada fazladan bir rota, 15 dalgada aynı rota sayısıyla daha uzun toplam süre.
   - Sapma yalnız büyük dalgalarda görülüyor: 6–10 yolculuk dalgaların 7/20'si, 11–20 yolculukların 12/16'sı. 1–5 yolculuk 192 dalgada GA hep optimal.
2. **Gün düzeyi ortak kesin model (DAY-JOINT).**
   - Rotalama ile araç atamasını birlikte çözüyor. Haftalık filo ihtiyacını R=60 ve R=70'te **6'dan 5'e** indiriyor. R=50 (6) ve R=90 (4) değişmiyor; bu değerler artık kanıtlı alt sınır.
   - Günlük filo 20 gün×R hücresinin 11'inde bir araç azalıyor.
   - Bedeli bazı günlerde 1–2 fazla rota ve daha fazla araç-dakikası; R=60'ta ise hem araç hem dakika azalıyor.
3. **Heterojen filo için tipli ortak model (DAY-TYPED).**
   - 3 büyük araç + sedan senaryosunda haftalık sedan ihtiyacı R=50/60/70'te **4/3/3'ten 3/2/2'ye** iniyor; R=90'da 1 aynı kalıyor.
   - Kampanyada "L için olursuz" etiketli 3 gün×R×L hücresinin olurlu olduğu sertifikalı planlarla gösterildi.
   - Olursuz kalan 26 hücrenin olursuzluğu artık tüm rotalamalar üzerinden kanıtlı.
4. **Ölçeklenen dalga sezgiseli (ESN-SP).** Komşuluklarda kesin rota sayımı + küme bölümleme + kesin onarımlı rota birleşimi LNS'i.
   - Gerçek dalgalarda 228'in 227'sinde optimum.
   - Ölçek testinde (19–108 yolcu) 19–54 yolculuk örneklerde eşit süreli GA-Split'i 10 örneğin 9'unda (v2) ya da 8'inde (v3) geçiyor.
   - 76–108 yolculuk yoğun örneklerde v2 5/5 geride. GA rotalarını havuza katan v3 5 örneğin 3'ünde GA'yı geçiyor, 2'sinde geride.
5. **TSP/ATSP: ILS-fast (alt ajan).** Aday listeli ve don't-look bitli Numba yerel arama.
   - Yerel arama 2,4·10⁴–1,7·10⁶ kat daha fazla kick/s yapıyor. 10 TSPLIB örneğinde 30 s'de 50 koşunun 36'sında optimum, ortalama açık %0,058.
   - Deponun ILS'i 40 koşunun 15'inde optimum, ortalama açık %2,02 (eşleştirilmiş Wilcoxon, Holm p=2,45·10⁻⁵).
   - LKH hâlâ daha iyi: 50/50 optimum, ama süre sınırsız (ortalama 21 s).
   - ATSP ft53'te 10/10 optimum.
6. **Olumsuz sonuç: GPX katkısı yok.** EB-PXILS'in ana hipotezi olan GPX rekombinasyonu basit prototipte ölçülebilir katkı vermedi (açık/kapalı p=0,78, Holm 1,0) ve havuz çeşitliliğini %24–55 azalttı.
7. **Ana ders.** Bugünkü üretim ölçeğinde (dalga başına ≤20 yolcu) sezgisele gerek yok; kesin yöntemler saniyeler içinde optimum veriyor. Asıl kazanç gün düzeyinde, yani rotalama ile filo atamasını birlikte çözmekte. Sezgisel tasarım (ESN-SP, ILS-fast) belediye ölçeği ve akademik TSP hattı için anlamlı.

![Günlük ve haftalık filo karşılaştırması]({{artifact:7e2760a9-40da-4c9c-a3a0-1f45b3f5ffc4}})

*Şekil:*
- *Sol: arşivdeki GA-Split + atama planlarının günlük araç sayısı ile ortak kesin modelin kanıtlanmış optimumu. Mavi hücreler bir araç azalan günler. Pazartesi R=90'ın optimumu, sıralı kesin planın rotalamadan bağımsız alt sınıra eşitliğiyle kanıtlandı; öteki 19 hücre ortak MIP ile.*
- *Sağ: 3 büyük araç (4 Sw/5 So) ile gereken ek sedan (0 Sw/4 So) sayısı, haftanın en kötü günü. Kampanya değerleri arşivdeki GA menüsü + CP-SAT sonuçları.*
- *Tek hafta (2026-10-05), 226 yolcu ayağı, 10 dk soğuma.*

## 1. Veri ve doğrulama

- **Veri:** `docs/paper/results/week-2026-10-05-4sw5so`: 5 gün × 4 R = 20 hücre, 228 dalga, en büyük dalga 20 yolcu. Gün başına bir yönlü süre matrisi var; matrisler asimetrik ve her gün 7–16 üçgen eşitsizliği ihlali içeriyor, yani metrik değiller. Heterojen kampanya (`week-2026-10-05-fleet`) aynı matrisi kullanıyor (sha256 `bfb2dd85…`, fark 0).
- **Harness'in arşivle tutarlılığı:**
  - Arşivdeki 358 GA rotasının süresi matristen 358/358 aynı hesaplandı.
  - Arşivdeki 20 hücrenin günlük filosu, rota aralıklarından 10 dk soğuma ile hesaplanan en büyük örtüşmeyle 20/20 aynı. Haftalık 6/6/6/4 ve araç-dakikası 6822/6450/6053/5862 yöntem belgesiyle aynı.
- **Bağımsız doğrulama:** Her çıktı deponun `feasibility_certificate` denetimlerinden geçirildi: kapsama, depo kapanışı, Sw/So kapasitesi, T, yöne özgü R. Tüm sonuç kümelerinde sertifika ihlali 0.
  - Gün düzeyi planlarda plan aralıklarından filo yeniden hesaplandı ve modelin K değeriyle karşılaştırıldı; 20/20 aynı.
  - Tipli planlarda bu kontrol tip başına yapıldı; kanıtlı 33 planın 33'ü (32 çözülmüş + Pazartesi R=90 L=3) eşit.
- **GA kontrol kolu:** Deponun `solve_ga_split` motoru varsayılan ayarla, yönlü matris ve `max_ride_time` ile çağrıldı. Arşivi birebir yeniden üretmedi: büyük 40 dalgada 20/40 aynı. Sebep, başlangıç popülasyonunun arşivde saklanmayan girdi sırasına bağlı olması. Bu yüzden ölçek testinde GA çok tohumla koşturuldu.

## 2. Geliştirilen algoritmalar

### A1. WAVE-EXACT: alt küme DP ile tam rota sayımı + sözlüksel küme bölümleme

**Problem:** P5 dalgası; tipli sürümüyle P6.

**Kod:** [wave_exact.py]({{artifact:ebfb8bda-6eba-4867-8e8e-78674538c48c}}), [run_waves.py]({{artifact:3c1a77ba-e17d-4896-8edc-657dd2678eeb}}).

**Yöntem:**
- **Rota sayımı (toplama):** Held–Karp türü alt küme DP ([Held & Karp 1962](https://doi.org/10.1137/0110015)). Toplama rotası depodan geriye doğru kuruluyor. Durum (S, f), f'den başlayıp S'yi dolaşarak depoya giden en kısa yol.
- **Bırakma:** Aynı DP, devrik matriste ve ters ziyaret sırasıyla çalışıyor.
- **Kesinlik argümanı:** Olurlu bir toplama rotasının her son parçası da olurlu, çünkü son parçadaki yolcuların yolculuk süresi değişmiyor. Bu yüzden değeri R'yi aşan durumları budamak metrik olmayan matriste bile kesin. T yalnız tamamlanmış rotada denetleniyor; budamada kullanılmıyor, çünkü T'nin monotonluğu matris metrik değilse geçerli değil.
- **Küme bölümleme:** Tüm olurlu rotalar üzerinde ([Balinski & Quandt 1964](https://doi.org/10.1287/opre.12.2.300)), HiGHS MIP ile ([Huangfu & Hall](https://doi.org/10.1007/s12532-017-0130-5)) iki aşamada çözülüyor: önce en az rota, sonra o sayıda en kısa toplam süre.

**Sözleşmeler:**
- DP süresi, rota yeniden hesaplanarak bulunan süreye eşit.
- Seçilen rotalar sertifikadan geçiyor.
- Sonuç hiçbir dalgada GA'dan kötü değil (sağlamlık kontrolü, 228/228).

**Teknik bulgu:** Tek ağırlıklı amaç (10 000·rota + dakika) iki büyük dalgada 600 s'de kanıt üretemedi (CP-SAT ve HiGHS). İki aşamalı sözlüksel çözüm aynı dalgaları 1,4 s ve 28,3 s'de kanıtladı. Kesin referans tasarımı (AMPL) için de iki aşamalı kurgu önerilir.

**Sınır:** Bellek 2ⁿ·n. n=20'de ≈100 MB ve 9 s; yaklaşık 22–25 yolcunun üzerinde pratik değil.

### A2. DAY-JOINT: gün düzeyinde ortak kesin model (homojen filo)

**Problem:** P7. **Kod:** [run_day_joint.py]({{artifact:c000e307-f3e1-443c-be9d-55551c8462e1}}).

**Yöntem:**
- Sütunlar her dalganın tüm olurlu rotaları. Her rotanın meşgul aralığı toplamada [a−d, a+10), bırakmada [a, a+d+10).
- Her dalga için tam bir bölümleme seçiliyor. Kısıt: her aralık başlangıç anında meşgul rota sayısı ≤ K.
- Özdeş araçlı aralık işlerinde en az araç sayısı en büyük örtüşmeye eşit; bu yüzden K doğrudan filo büyüklüğü.
- Sözlüksel amaç üç aşamada çözülüyor: K → rota sayısı → toplam dakika.
- Problem sınıfı çok seferli VRP ile filo boyutlandırması ([Cattaruzza vd. 2016](https://doi.org/10.1007/s10288-016-0306-2)).

**Alt sınır (LB0):** Her dalganın en az rota sayısı K*_w, çapa anında [a, a+10) aynı anda meşgul. Bu, rotalamadan bağımsız bir alt sınır verir. MIP zaman sınırına takılan Pazartesi R=90'ın optimumu bu alt sınırla kanıtlandı.

### A3. DAY-TYPED: tipli ortak model (heterojen filo)

**Problem:** P6 + P7. **Kod:** [run_day_typed.py]({{artifact:5ff66bcb-2435-42b4-b3d3-1792738f02b5}}).

**Yöntem:**
- Rotalar tip başına ayrı sayılıyor: büyük araç 4 Sw/5 So, sedan 0 Sw/4 So.
- Her rota bir tipe atanıyor ve tip başına eşzamanlılık ayrı tutuluyor: büyük araç ≤ L, sedan ≤ S.
- Amaç: önce S, sonra toplam dakika.

**Kesinlik:** Sütunlar tip başına eksiksiz olduğu için model olursuzsa, o gün L büyük araçla hiçbir rotalama yok demektir.

### A4. ESN-SP: kesin alt komşuluk sayımı + küme bölümleme + kesin onarımlı rota birleşimi LNS'i

**Problem:** P5 büyük dalgalar, P8 yönü. **Kod:** [esn_sp.py (v2)]({{artifact:3256f520-f222-48e1-bb75-ae498d22fdc5}}), [esn_sp_v3.py]({{artifact:b0dce88b-9fd7-4626-b205-808f91379385}}).

**Yöntem:**
1. Her yolcunun g=10 en yakın komşusu içindeki tüm olurlu rotalar A1'in DP'siyle sayılıyor.
2. Bu havuz üzerinde iki aşamalı küme bölümleme çözülüyor.
3. Mevcut çözümde birbirine en yakın rota çiftleri ve üçlüleri, yolcu sayısı ≤16 (v3'te ≤18) ise birleştiriliyor. Birleşimin tüm rotaları sayılıp yerel küme bölümleme kesin çözülüyor; sözlüksel olarak daha iyiyse çözüme alınıyor.

**v3'teki değişiklikler:**
- Komşuluklar farklı duraklara göre kuruluyor.
- İki GA-Split koşusunun rotaları havuza ekleniyor.
- En iyi GA çözümü başlangıç çözümü olarak tutuluyor; küme bölümleme sonucu ancak daha iyiyse kabul ediliyor.

**Literatür:** Rota havuzu + küme bölümleme ([Rochat & Taillard 1995](https://doi.org/10.1007/bf02430370); [Subramanian vd. 2013](https://doi.org/10.1016/j.cor.2013.01.013)), LNS ([Pisinger & Ropke 2007](https://doi.org/10.1016/j.cor.2005.09.012)).

**Yenilik:** "Kesin alt komşuluk sayımıyla havuz tohumlama" ve "rota birleşimini kesin sayım + küme bölümlemeyle onarma" bileşimi için odaklı bir literatür taraması yapılmadı [DOĞRULANMADI].

**Telemetri:** Havuz boyutu, denenen ve iyileşen birleşim sayısı, küme bölümleme durumları.

### A5. ILS-fast ve PX-ILS (TSP/ATSP; alt ajan)

**Problem:** P1, P2. **Kod:** [fast_ls.py]({{artifact:21a30d74-fcf7-479e-89ea-33146a8d75d4}}), [ils_fast.py]({{artifact:5defbdf9-5b9d-4e79-9717-31d67929303f}}), [px_ils.py]({{artifact:04d2e421-9d48-4994-87a9-704e0816f7e8}}). **Sözleşme testleri:** [51/51 geçti]({{artifact:5c9a8e06-242c-4ace-976f-30995b289764}}).

**Yöntem:**
- Dizi tabanlı tur, K=10 aday listesi, don't-look bit kuyruğu.
- Simetrik durumda 2-opt + Or-opt + or-3opt; yönlü durumda yalnız yönü koruyan Or-opt ve or-3opt (ters çevirme sayacı 0).
- Segment-yerel double-bridge sarsım ve "kötü değilse kabul".
- PX-ILS: basit GPX + elit havuz.

## 3. Sonuçlar

### 3.1 Dalga düzeyi: GA-Split ile kesin optimum

| R | Dalga | GA rota | Kesin rota | GA dk | Kesin dk | Dakika farkı | GA fazla rota | GA aynı rota, daha uzun |
|---|---|---|---|---|---|---|---|---|
| 50 | 57 | 109 | 108 | 6822 | 6803 | 19 (%0,28) | 1 | 3 |
| 60 | 57 | 94 | 93 | 6450 | 6369 | 81 (%1,27) | 1 | 6 |
| 70 | 57 | 82 | 81 | 6053 | 6028 | 25 (%0,41) | 1 | 3 |
| 90 | 57 | 73 | 72 | 5862 | 5813 | 49 (%0,84) | 1 | 3 |

GA'nın fazladan rota kullandığı 4 dalga, hepsi kampüse toplama:
- 05.10 08:45, R=60: 5 → 4 rota
- 05.10 08:45, R=90: 4 → 3 rota
- 07.10 08:45, R=50: 4 → 3 rota
- 07.10 08:45, R=70: 3 → 2 rota

Ayrıntı: [wave_ga_suboptimal.csv]({{artifact:37f76426-d508-4a31-9d71-b280243bd555}}), [wave_exact_vs_ga.csv]({{artifact:1ef63ad6-0f61-4d76-9c74-7b7562bff475}}).

### 3.2 Gün düzeyi: filo

**Günlük araç sayısı, GA-Split + atama → ortak kesin model** (kalın hücreler değişenler):

| | Pzt | Sal | Çar | Per | Cum | Hafta |
|---|---|---|---|---|---|---|
| R=50 | 6 | **5→4** | **6→5** | **5→4** | 6 | 6 → 6 |
| R=60 | **5→4** | 4 | **6→5** | 4 | 5 | 6 → 5 |
| R=70 | 4 | 4 | **6→5** | **4→3** | **5→4** | 6 → 5 |
| R=90 | **4→3** | 3 | 4 | **4→3** | **4→3** | 4 → 4 |

**Haftalık toplamlar** (Pazartesi R=90'da sıralı kesin plan kullanıldı):

| R | GA filo | Kesin filo | GA rota | Kesin rota | GA araç-dk | Kesin araç-dk |
|---|---|---|---|---|---|---|
| R=50 | 6 | 6 | 109 | 111 | 6822 | 6850 |
| R=60 | 6 | 5 | 94 | 94 | 6450 | 6399 |
| R=70 | 6 | 5 | 82 | 85 | 6053 | 6114 |
| R=90 | 4 | 4 | 73 | 74 | 5862 | 5844 |

**Yorum:**
- Sıralı yaklaşım (önce her dalgayı kesin çöz, sonra ata) haftalık filoyu değiştirmiyor; darboğaz Çarşamba 6 araçta kalıyor.
- Ortak model bazı dalgalarda en az rota sayısından fazla ya da daha uzun rota seçerek dalgalar arası örtüşmeyi azaltıyor. Çarşamba R=50–70'te filo böylece 5'e iniyor.
- Bu, mevcut planlayıcının "önce dalga başına rota sayısı" önceliğinden farklı bir politika. Hangi önceliğin geçerli olacağı sahibinin kararı.
- Ortak plan 5 hücrede arşivdeki en erken başlangıçtan 1–17 dk önce başlıyor. Hizmet günü penceresi bu çalışmada denetlenmedi.

Ayrıntı: [day_level_4sw5so.csv]({{artifact:eb91c967-9a96-488a-b874-f6ae2e9017ca}}), [day_joint_4sw5so.jsonl]({{artifact:8f770755-9ff6-43d2-af9f-382e43c166e1}}) (planlar).

### 3.3 Heterojen filo: kampanya ile tipli kesin model

**3 büyük araç ile haftalık sedan ihtiyacı:**

| R | Kampanya (GA menüsü + CP-SAT) | Tipli kesin | Kesin, günlük (Pzt–Cum) |
|---|---|---|---|
| R=50 | 4 | **3** | 3 / 1 / 3 / 1 / 3 |
| R=60 | 3 | **2** | 1 / 1 / 2 / 1 / 2 |
| R=70 | 3 | **2** | 1 / 1 / 2 / 0 / 1 |
| R=90 | 1 | **1** | 0 / 0 / 1 / 0 / 0 |

**60 gün×R×L hücresinin dökümü:**

| Durum | Hücre |
|---|---|
| İkisinde de olurlu | 29: kesin model 15'inde daha az sedan, 14'ünde eşit, hiçbirinde fazla değil |
| Kampanyada olursuz, kesin modelde olurlu | 3: Salı R=70 ve R=90 L=2 (`CROSS_WAVE_CONFLICT`), Pazartesi R=60 L=2 (`SW_DEMAND_EXCEEDS_LARGE_CAPACITY`). Kampanyanın bu etiketleri GA menüsüne koşulluydu |
| İkisinde de olursuz | 26: olursuzluk artık kanıtlı |
| Pazartesi R=90 L=3 | MIP zaman sınırına takıldı; homojen 3 araçlık kanıtlı plan S=0 veriyor |
| Pazartesi R=90 L=2 | Açık: S ∈ {1, 2}. Haftalık sonucu değiştirmiyor, çünkü Çarşamba L=2'de olursuz |

L=1 ve L=2 haftaları kampanyada olduğu gibi olursuz. Ayrıntı: [day_typed_vs_campaign.csv]({{artifact:912d5084-636e-4fed-9f7b-9dac97f0cd12}}), [weekly_typed_vs_campaign.csv]({{artifact:215cd3f7-64ff-4d00-9e23-ce994a6b5588}}).

### 3.4 ESN-SP: gerçek dalgalar ve ölçek testi

**Gerçek dalgalar:** v2, 228'in 227'sinde kesin optimuma ulaştı. Tek sapma 20 yolculuk R=90 dalgası: 3 rota / 332 dk, optimum 329 dk. Medyan süre 0,05 s, en uzun 44 s ([esn_real_v2.jsonl]({{artifact:e9839b0f-4324-471e-85fb-b16f16d8c759}})).

**Ölçek testi.** Kampanya dışı sentetik dalgalar, R=90, T=150, tümü toplama dalgası olarak modellendi:
- **S1:** Bir günün tüm toplama yolcuları (19–27 yolcu).
- **S2:** Günün tüm ayakları (38–54).
- **S3:** S2'nin her yolcusu aynı durakta ikiye çoğaltılmış hali (76–108).

**Kollar:**
- ESN-SP v2 (bütçe 120 s).
- ESN-SP v3 (iki GA koşusu dahil).
- Eşit süreli GA: varsayılan ayar, ESN-SP v2 süresi dolana kadar yeni tohumla yeniden başlatma.
- GA 5 tohum: toplam süresi ayrıca verildi.

Hücreler rota/dk biçiminde:

| Örnek | n | Koltuk alt sınırı | ESN-SP v2 | ESN-SP v3 | GA eşit süre | GA 5 tohum (en iyi; rota sayıları; toplam s) |
|---|---|---|---|---|---|---|
| S1 09.10 | 19 | 3 | 3/330 (30 s) | 3/330 (20 s) | 4/348 (8 koşu) | 4/352 (4,4,4,4,4; 12 s) |
| S1 06.10 | 21 | 3 | 3/310 (128 s) | 3/310 (133 s) | 3/315 (22 koşu) | 3/325 (4,3,3,4,3; 33 s) |
| S1 07.10 | 23 | 4 | 4/342 (126 s) | 4/347 (156 s) | 4/347 (30 koşu) | 4/352 (4,4,4,4,4; 24 s) |
| S1 08.10 | 23 | 3 | 4/354 (84 s) | 4/354 (133 s) | 4/365 (18 koşu) | 4/365 (4,4,4,4,4; 18 s) |
| S1 05.10 | 27 | 4 | 4/390 (140 s) | 4/427 (201 s) | 4/397 (40 koşu) | 4/414 (5,5,5,5,4; 25 s) |
| S2 09.10 | 38 | 6 | 6/421 (169 s) | 6/417 (128 s) | 6/437 (23 koşu) | 7/433 (7,7,7,7,7; 40 s) |
| S2 06.10 | 42 | 6 | 6/399 (144 s) | 6/404 (140 s) | 6/410 (8 koşu) | 6/421 (6,6,6,6,6; 83 s) |
| S2 07.10 | 46 | 7 | 7/458 (179 s) | 7/437 (187 s) | 7/452 (8 koşu) | 7/451 (7,7,7,7,7; 87 s) |
| S2 08.10 | 46 | 6 | 6/451 (160 s) | 6/451 (298 s) | 6/467 (9 koşu) | 6/483 (6,7,7,7,7; 82 s) |
| S2 05.10 | 54 | 8 | 8/513 (129 s) | 8/507 (160 s) | 8/530 (7 koşu) | 8/521 (8,8,8,8,8; 133 s) |
| S3 09.10 | 76 | 12 | 14/690 (136 s) | 13/665 (313 s) | 12/744 (4 koşu) | 13/671 (13,13,13,13,13; 174 s) |
| S3 06.10 | 84 | 12 | 17/822 (122 s) | 12/673 (130 s) | 12/720 (2 koşu) | 12/676 (13,12,12,12,12; 433 s) |
| S3 07.10 | 92 | 13 | 15/771 (160 s) | 14/778 (370 s) | 13/784 (2 koşu) | 13/815 (14,14,14,13,13; 340 s) |
| S3 08.10 | 92 | 12 | 16/833 (182 s) | 13/783 (220 s) | 13/825 (3 koşu) | 13/807 (13,13,13,13,14; 478 s) |
| S3 05.10 | 108 | 16 | 19/966 (190 s) | 16/906 (491 s) | 16/915 (2 koşu) | 16/901 (16,17,16,16,16; 564 s) |

**Özet:**
- **v2:** S1'de 5/5, S2'de 4/5 eşit süreli GA'dan iyi; S3'te 0/5.
- **v3, eşit süreli GA'ya karşı:** S1'de 3 iyi / 1 eşit / 1 kötü; S2'de 5/5 iyi; S3'te 3 iyi / 2 kötü.
- **v3, GA 5 tohuma karşı:** 15 örneğin 12'sinde iyi.
- Bütün kollarda sertifika ihlali 0.

**Yorum:** Yoğun örneklerde (aynı durakta birden çok yolcu, rota başına 6+ yolcu) kesin sayıma dayalı komşuluklar dar kalıyor. Bu durumda giant-tour + Split temsili (GA) daha iyi rota yapısı buluyor. v3'ün güvencesi yalnız havuza katılan GA koşularına göre geçerli; başka tohumlar 1 rota daha az bulabiliyor. Bütün süreler paylaşımlı CPU'da ölçüldü. Ayrıntı: [scale_esn_vs_ga.csv]({{artifact:2eda44bb-ecc1-4823-aefb-9f9c7e1cd977}}).

### 3.5 TSP/ATSP hattı (alt ajan sonuçları)

| Bulgu | Sonuç |
|---|---|
| Karar deneyi D1: hız (≥50× kick/s) | Sağlandı: a280'de 23 672×, pr439'da 100 330×, pr1002'de ≈1,7·10⁶× |
| D1: yerel optimum kalitesi (±%0,5) | Kısmen. Rastgele başlangıçtan kötü değil. Aynı sarsılmış başlangıçlardan K=10 ile %1,8–4,2 daha kötü; K=20 + or-3opt ile nokta tahminleri %0,5 içinde, ama güven aralıkları geniş |
| Ana kıyas: 10 örnek (100–1002 düğüm), 5 tohum, 30 s | ILS-fast 36/50 optimum, ortalama açık %0,058. Deponun ILS'i 15/40 optimum, %2,02. ILS-fast'in sonucu 25 koşuda daha iyi, 15'te eşit, hiçbirinde daha kötü değil (Holm p=2,45·10⁻⁵) |
| LKH (elkai, runs=10, süre sınırsız, ortalama 21 s) | 50/50 optimum. ILS-fast 36 koşuda eşit, 14 koşuda geride (hepsi n≥318); Holm p=9,7·10⁻⁴ |
| ATSP ft53 | ILS-fast yalnız yönlü hamlelerle 10/10 optimum, en iyiye ortalama 0,078 s. elkai ATSP'yi doğal destekliyor (açık soru kapandı) |
| GPX ablasyonu: pr439, rat783, pr1002, pcb1173; 5 tohum; eşit süre | Açık %0,208, kapalı %0,185, tek yörünge %0,194. Fark yok (p=0,78). GPX havuz çeşitliliğini %24–55 düşürdü |

Kaynak tablolar: [main_summary.csv]({{artifact:e5c482aa-1883-4063-a2a5-d7bb47f55a66}}), [main_wilcoxon.csv]({{artifact:4cecb171-fd97-48f7-844e-e081ffaaa7bd}}), [atsp_summary.csv]({{artifact:938db332-7cf6-489f-9734-e197d0c6beef}}), [gpx_summary.csv]({{artifact:d592a154-ce2a-48c0-8a94-72be94ac4ea8}}).

**Alt ajanın bildirdiği sapmalar:**
- Akademik veri klasörüne erişim oturum ortasında bozuldu; TSPLIB dosyaları resmi kaynaktan indirildi. ft53 sağlaması depoyla aynı; diğer 14 dosya depo kopyalarıyla karşılaştırılamadı.
- Deponun ILS'i rat783 ve pr1002'de koşturulamadı, çünkü bir yerel arama çağrısı 13 dk'da bitmedi.
- ILS-fast simetrik ayarına or-3opt eklendi; seçim 3 kıyas dışı örnekte yapıldı.
- LKH süre sınırsız koştu.
- Değerlendirme sayısı muhasebesi uygulanmadı; bütçe duvar saati ve kick sayısıyla tutuldu.

## 4. Plandaki hipotezlerin durumu

| Plan öğesi | Durum |
|---|---|
| Faz 0, D1: hızlı yerel arama ≥50× | Hız ölçütü sağlandı, kalite ölçütü kısmen. ILS-fast, ILS kontrol kolu ve sonraki tasarımlar için çekirdek olarak kullanılabilir |
| Ö1 EB-PXILS: GPX katkısı | Basit GPX prototipinde **desteklenmedi**. GPX2, entropi denetimi ve ATSP desteği olmadan bu tasarımın önceliği düşürülmeli; ancak GPX2 ile ve n≥5000 örneklerde yeniden sınanabilir |
| Ö3 DAR-MA, H1 | Sınanmadı (D2 arazi taraması yapılmadı) |
| Ö4 BA-LNS | Yapılmadı. Yerine kesin onarımlı LNS (ESN-SP) geliştirildi |
| Plan dışı yeni yön: kesin dalga ve gün modelleri | Bugünkü üretim ölçeğinde en büyük kazanç burada: haftalık filo −1 (R=60, 70), heterojen senaryoda sedan −1 (R=50/60/70) |

## 5. Sınırlar

- **Tek hafta.** Tek anlık görüntü, 226 yolcu ayağı, tüm talepler onaylı varsayıldı. Sonuçlar başka haftalara ya da belediye ölçeğine kendiliğinden genellenmez.
- **"Kanıtlı optimum"un kapsamı.** Kesinlik model varsayımlarına bağlı: dalga başına sabit çapa, yalnız seyahat süresi (biniş ve bekleme yok), özdeş sanal araçlar ya da iki tip, 10 dk soğuma, aralık modeli. Gün düzeyi model, deponun atama motorunun dal-sınır bütçesini ve hizmet günü pencere kurallarını içermiyor; arşivdeki 20 hücrede aynı filo sayısını verdiği doğrulandı.
- **Politika farkı.** Gün düzeyi optimum, dalga başına en az rota önceliğinden vazgeçiyor; araç-dakikası R=50'de 6822'den 6850'ye, R=70'te 6053'ten 6114'e çıkıyor. R=60'ta hem filo hem dakika azalıyor (6450 → 6399).
- **Ölçek testi verisi sentetik.** Gerçek demand birleşimi ve çoğaltma kullanıldı; belediye ölçeğinde ve gerçek zaman pencereli bir veri kümesi değil. Süreler paylaşımlı CPU'da ölçüldü; eşit süre karşılaştırmasında GA'ya ESN-SP v2'nin süresi verildi.
- **Ölçeklenme sınırları.** WAVE-EXACT yaklaşık 22–25 yolcunun üzerindeki dalgalarda uygulanamaz. Ortak gün modeli 45 bin sütunlu bir dalgada (Pazartesi R=90) 900 s'de çözülemedi.
- **Çözülmemiş hücre.** Pazartesi R=90 L=2 (tipli) çözülmedi.

## 6. Önerilen sonraki adımlar

1. **Üretim.** WAVE-EXACT, ≤20 yolculuk dalgalar için kesin referans ve doğrudan çözücü olarak, dal-sınır atamasıyla birlikte; GA-Split yalnız büyük dalgalar için. DAY-JOINT ise "filo öncelikli" bir planlama seçeneği olarak. İkisi de sertifika ve sözleşme testleriyle `uniride_core`'a alınmalı; kimlik önerileri `Core-WaveExact-SP` ve `Core-DayJoint-SP`.
2. **Kesin referans tasarımı.** AMPL planı iki aşamalı küme bölümlemeyi zaten öngörüyor. Bu çalışmadaki Python + HiGHS sürümü aynı işi görüyor ve doğrulama karşılaştırması olarak kullanılabilir.
3. **Belediye ölçeği (P8).** ESN-SP'nin zayıf olduğu yoğun örnekler için giant-tour + Split havuzunu çok tohumlu ve HGS türü bir aramayla zenginleştirmek. Gerçek boyutlu, zaman pencereli sentetik bir üretecin kurulması gerekiyor.
4. **CVRP/CVRPTW (P3/P4).** CVRPLIB ve Solomon dosyalarını veritabanına almak; ESN-SP'yi zaman penceresi olurluluk DP'siyle genişletip PyVRP'ye karşı ölçmek. Bu turda yapılmadı.
5. **TSP hattı.** ILS-fast'i değerlendirme sayısı muhasebesiyle katalog kapısından geçirmek; GPX2 ve EAX denemelerini n≥5000 örneklere ertelemek.

## Kaynaklar

DOI'lerin hepsi bu turda CrossRef'te doğrulandı.

- Balinski, Quandt (1964). On an Integer Program for a Delivery Problem. *Operations Research*. https://doi.org/10.1287/opre.12.2.300
- Cattaruzza, Absi, Feillet (2016). Vehicle routing problems with multiple trips. *4OR*. https://doi.org/10.1007/s10288-016-0306-2
- Desrochers, Desrosiers, Solomon (1992). A New Optimization Algorithm for the Vehicle Routing Problem with Time Windows. *Operations Research*. https://doi.org/10.1287/opre.40.2.342
- Held, Karp (1962). A Dynamic Programming Approach to Sequencing Problems. *J. SIAM*. https://doi.org/10.1137/0110015
- Huangfu, Hall (2018). Parallelizing the dual revised simplex method. *Mathematical Programming Computation*. https://doi.org/10.1007/s12532-017-0130-5
- Pisinger, Ropke (2007). A general heuristic for vehicle routing problems. *Computers & OR*. https://doi.org/10.1016/j.cor.2005.09.012
- Prins (2004). A simple and effective evolutionary algorithm for the vehicle routing problem. *Computers & OR*. https://doi.org/10.1016/s0305-0548(03)00158-8
- Rochat, Taillard (1995). Probabilistic diversification and intensification in local search for vehicle routing. *Journal of Heuristics*. https://doi.org/10.1007/bf02430370
- Subramanian, Uchoa, Ochi (2013). A hybrid algorithm for a class of vehicle routing problems. *Computers & OR*. https://doi.org/10.1016/j.cor.2013.01.013
- TSP hattının kaynakları alt ajan raporunda: [TSP_FAST_LS_REPORT.md]({{artifact:3183a1f1-7ee6-46fe-8a59-dbc75c72252f}}).

## Dosyalar

- **Kod:**
  - [wave_exact.py]({{artifact:ebfb8bda-6eba-4867-8e8e-78674538c48c}}), [run_waves.py]({{artifact:3c1a77ba-e17d-4896-8edc-657dd2678eeb}})
  - [run_day_joint.py]({{artifact:c000e307-f3e1-443c-be9d-55551c8462e1}}), [run_day_typed.py]({{artifact:5ff66bcb-2435-42b4-b3d3-1792738f02b5}})
  - [esn_sp.py]({{artifact:3256f520-f222-48e1-bb75-ae498d22fdc5}}), [esn_sp_v3.py]({{artifact:b0dce88b-9fd7-4626-b205-808f91379385}})
  - [run_esn.py]({{artifact:963f8f6a-bd49-401e-921b-cc8690fe532a}}), [run_esn_v3.py]({{artifact:de8eb984-b630-4756-a3cc-8f42563a1149}}), [run_ga_equal.py]({{artifact:ab27177f-845b-469c-b571-fd3588ce1c7d}})
- **Sonuçlar:**
  - [wave_exact_4sw5so.jsonl]({{artifact:41838ea0-3ccd-4df8-8b86-c8551b239089}}) (228 dalganın kesin rotaları), [wave_summary_by_R.csv]({{artifact:51fe97ec-8bf7-48e1-8243-de35865a9001}})
  - [day_level_4sw5so.csv]({{artifact:eb91c967-9a96-488a-b874-f6ae2e9017ca}}), [weekly_fleet_4sw5so.csv]({{artifact:4911ee26-e0c8-43b2-87e4-56f0ed1c12c1}})
  - [day_typed.jsonl]({{artifact:ac909b46-af06-412c-bad7-b4f0ecefb00a}}) (tipli planlar)
  - [scale_esn_vs_ga.csv]({{artifact:2eda44bb-ecc1-4823-aefb-9f9c7e1cd977}})
