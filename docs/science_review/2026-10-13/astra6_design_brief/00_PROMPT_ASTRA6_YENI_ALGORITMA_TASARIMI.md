# Codex görevi (Astra 6): UniRide için yeni hibrit algoritma tasarımları

**Bu bir tasarım araştırmasıdır, kod incelemesi değildir.** Kod yazma, kodu değiştirme ve mevcut çözücülerin kaynak kodunu yeniden inceleme. Tek çıktın, §8'de tanımlanan yeni bir Markdown raporudur.

Paket klasörü: `docs/science_review/2026-10-13/astra6_design_brief/`. Bu istemde kısaca `BRIEF/` diye anılır.

## 0. Görevin özü

UniRide'da daha önce başka bir yapay zekâyla üç "Frankenstein" algoritma tasarlandı: E2BSO, R2DMA ve P-AOEA. Hepsi, başarılı TSP sezgisellerinin özelliklerini birleştirme fikrine dayanıyordu.

İki bağımsız inceleme (BRIEF/01, BRIEF/02, BRIEF/10) iki şey gösterdi:
- Bu algoritmaların imza mekanizmaları tarif edildiği gibi çalışmıyor.
- Üçü de aynı yerel aramayı kullanan basit bir ILS'e eşit sürede yeniliyor.

Senden istenen, aynı "başarılı bileşenleri birleştirme" fikrini **doğru bileşenlerle ve doğru aktarımla** yeniden ele almak. Bunun sonucunda UniRide'ın ihtiyaç duyduğu problem tiplerinde (§4) başarılı olması beklenen **yeni algoritma tasarımları** önereceksin. Her tasarım şunları taşımalı:
- uygulanabilir ayrıntı;
- sınanabilir hipotezler;
- dürüst bir yenilik değerlendirmesi.

## 1. Kesin sınırlar

1. **Kod incelemesi yok.** `uniride_core/`, `optimizer_api/`, `academic_benchmark/` ve `src/` altındaki kaynak kod dosyalarını açma.
   - E2BSO, R2DMA, P-AOEA ve diğer algoritmalar hakkındaki bulgular, BRIEF/01, BRIEF/02 ve BRIEF/10'da doğrulanmış olgu olarak kabul edilir; onları yeniden denetleme.
   - Gerekli arayüz bilgisi §5'te verildi. Bir arayüz ayrıntısı eksikse onu "Açık soru" olarak yaz; kodu açarak tamamlamaya çalışma.
2. **Okunacak depo belgeleri:** Yalnız §2'deki belgeler (problem sözleşmeleri ve protokoller).
3. **Tek çıktı:** Kod yazma, dosya değiştirme, test ya da benchmark koşturma yok. Oluşturacağın tek dosya `BRIEF/ASTRA6_YENI_ALGORITMA_TASARIMLARI.md`.
4. **SOTA iddiası yok.** Hiçbir tasarım için "SOTA" ya da üstünlük iddiası kurma. Beklenen performansı yalnız **hipotez** olarak yaz; her hipotezde yön, güven düzeyi ve yanlışlama ölçütü bulunsun.
5. **Metafor yok.** Sürü, kurt, şahin, rezonans gibi metaforlara dayanan güncelleme denklemleri kullanma. Her mekanizmayı bileşen terimleriyle anlat ([Sörensen](https://doi.org/10.1111/itor.12001); [Camacho-Villalón vd. 2022](https://doi.org/10.1111/itor.13176)).
6. **Uydurma yok.** Kaynak, DOI, yazar, yıl ya da sayı uydurma (ayrıntı §9'da).
7. **Git:** Commit ya da push yapma. Ana checkout'ta `git checkout` veya `git switch` çalıştırma. Başka hiçbir dosyaya dokunma.

## 2. Okuma sırası

| Sıra | Dosya | İçerik | Güven düzeyi | Nasıl kullanılacak |
|---|---|---|---|---|
| 1 | `BRIEF/03_REDESIGN_WORK_PLAN_2026-10-13.md` | Başarı bileşenleri (O1–O7), tasarım ilkeleri, beş başlangıç önerisi, eski bileşenlerin akıbeti, fazlar ve geçiş kapıları | Öneri (henüz ölçülmedi) | Çıkış noktası; eleştir, geliştir ya da değiştir |
| 2 | `BRIEF/01_SOTA_FAMILY_EVALUATION_2026-10-13.md` | Üçlünün ölçülmüş arızaları, kıyas ve istatistik, §7 çapraz kontrol ekleri | Ölçüm (enstrümantasyon ve 30 koşu) | §3'teki olguların ayrıntısı |
| 3 | `BRIEF/02_CROSS_CHECK_CODEX_VS_SCIENCE_2026-10-13.md` | İki incelemenin birleşik olgu listesi ve üretim adaptörü bulgusu | Kodda doğrulandı | Olgu kaynağı |
| 4 | `docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md` §1–§4 (depo belgesi) | Üretim problem sözleşmesi | Belge | §4 P5–P7'nin dayanağı |
| 5 | `BRIEF/09_ALGORITHM_INVENTORY_FOR_SCIENCE_2026-10-13.md` §1 ve §2 | Problem aileleri, amaçlar, protokol, algoritma tablosu | Kod okumasıyla hazırlanmış envanter | Mevcut bileşenlerin listesi |
| 6 | `BRIEF/04_ALGORITHM_LITERATURE_SOTA_2026-10-13.md`, `BRIEF/05_algorithm_literature_table.csv` | Kart başına literatür karşılığı, güncel SOTA ve standart kıyas yöntemleri | Kaynaklı (OpenAlex ve CrossRef) | Problem → başarılı bileşen eşlemesi |
| 7 | `BRIEF/06_kaynakca.csv` (201 DOI) ve `BRIEF/07_kaynakca_ek_2026-10-13.csv` (20 kaynak) | Doğrulanmış kaynakça | Künyeler CrossRef/arXiv/OpenAlex'te doğrulandı | Önce bu kaynakları kullan |
| 8 | `ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md` ve `ACADEMIC_STUDY_UNIFICATION_DESIGN.md` (bölümler: "Hybrid composition semantics", "Experimental Protocol", "Statistical Protocol") | Bütçe tanımı, atomik üst sınır, eşleştirilmiş tohum, hibrit bileşim kuralları | Depo tasarım belgesi | Bütçe muhasebesi ve deney planı |
| 9 | `docs/CODEX_TASK_ARCHITECTURE_RESEARCH.md` §2; varsa `docs/research/ARCHITECTURE_RESEARCH_2026-10.md` (özet, RQ1, RQ3) | Sahibin hedefleri (G1–G3), ölçek, ölçeklenen algoritmalar | Belge | P8 ve ölçek varsayımları |
| 10 | `AGENTS.md` "Required Academic Boundaries" | Akademik sınırlar | Kural | Uyum |
| İsteğe bağlı | `BRIEF/08_dogrulanmadi_yanitlari.csv`, `BRIEF/10_CODEX_…md`, `BRIEF/11`–`BRIEF/17` (CSV ve şekil); `docs/DECISION_LOG.md` (yalnız O03, O05, H01–H04, A02, A04, T01, E01) | Ek ayrıntı ve ham sayılar | — | Gerekirse |

## 3. Kabul edilmiş olgular (yeniden doğrulama)

**Ölçülmüş arızalar** (ayrıntı BRIEF/01 ve BRIEF/02'de):

| Algoritma | Olgu |
|---|---|
| E2BSO | Entropi `log2(P·n)` ile normalize ediliyor. Özdeş popülasyonun tabanı 0,517 / 0,555 / 0,595; farklı yerel optimumlardan oluşan popülasyon ise 0,593 / 0,631 / 0,630 (berlin52 / rd100 / pr226). Öğrenme döneminin 100 iterasyonunun 91'i INJECT; sonrasında INJECT 0, NORMAL 365, COMPRESS 35. Zorlanan kenarların %51,6'sı atlanıyor. Ortak LAHC kabul oranı %72,4 (varsayılan) ve %100 (üretim ayarı). |
| R2DMA | 30 000 kararın 29 977'si yerel aramasız tek rastgele takas (perturb); destructive 0. Aynı turun ters yönü 0,429 / 0,456 / 0,396 puan alıyor (berlin52 / rd100 / pr226); bu, bağımsız yerel optimumların ortalamasıyla (0,430) aynı düzeyde. Constructive çaprazlama ortak kenarların %44–55'ini koruyor ve yerel aramadan sonra rastgele yeniden başlatmaya eşdeğer. SA, kötüleşen çocukların %62,7'sini kabul ediyor. |
| P-AOEA | Birikimli kredi yüzünden aynı 3 genom 10 turun 10'unda hayatta kaldı. SA kötüleşen adayların %98,8–100'ünü kabul ediyor. 30 s bütçede evrim hiç tetiklenmedi; evrimsiz kolla 30/30 aynı sonuç. Üretim ayarındaki ablasyon 1/7/2, p=1,0. `tournament_size`, `genome_injection_rate` ve `remove_ratio_range` hiç okunmuyor; RTR uygulanmamış. |
| Ortak | a280'de 30 s bütçeyle E2BSO 118,6 s, P-AOEA 102,5 s çalıştı; ikisi de 1 iterasyon yaptı. Aynı yerel aramayla ILS 30,8 s'de yalnız 21 iterasyon yaptı. Enjeksiyon, en iyi çözüm güncellendikten sonra yapılıyor; üretim ayarındaki 45 koşuda 0 kayıp ölçüldü. Bilimsel protokol kapısı bu üçlüyü reddediyor. |
| Üretim adaptörü | Matris yalnız öğrencilerden mesafeyle kuruluyor; depo yok. Kapalı çevrim optimize ediliyor ve sıra depoya göre döndürülmüyor. Her hata sessizce süre tabanlı en yakın komşu yedeğine düşüyor. |
| Diğer (1. tur kod denetimi) | PSO/GWO/HHO-Split `max_ride_time`'ı çözümleyiciye iletmiyor. Çözümleyicide `is_asymmetric=False` varsayılanı yüzünden eksik yönlü yay sessizce ters yaya düşüyor. GA-Split uygunluğu zaman penceresiz çözümleyiciyle hesaplanıyor; varsayılan ayarla çeşitlendirme hiç tetiklenmiyor (25 < 30). Split karmaşıklığı CVRP'de O(n·L), toplama-TW modunda O(n·L²). |

**Kıyas** (6 TSPLIB örneği, 100–280 düğüm, 5 tohum, 30 s; `BRIEF/11_bench_summary_overall.csv`):

| Kol | Ortalama açık (%) | Medyan açık (%) | Bulunan optimum | Ortalama süre (s) |
|---|---|---|---|---|
| E2BSO | 0.782 | 0.505 | 8/30 | 46.0 |
| R2DMA | 2.545 | 2.358 | 1/30 | 30.5 |
| P-AOEA | 1.296 | 0.607 | 10/30 | 43.8 |
| P-AOEA, evrimsiz | 1.296 | 0.607 | 10/30 | 43.1 |
| ILS (30 s) | 0.886 | 0.185 | 12/30 | 30.2 |
| OR-Tools GLS | 2.661 | 2.338 | 0/30 | 30.0 |
| LKH (elkai) | 0.000 | 0.000 | 30/30 | 3.3 |

Eşleştirilmiş Wilcoxon sonuçları:
- E2BSO ↔ ILS (E2BSO'nun süresi): 5 / 6 / 19, p=0,0058.
- P-AOEA ↔ ILS (P-AOEA'nın süresi): 1 / 13 / 16, p=0,0004.
- R2DMA ↔ ILS (30 s): 2 / 1 / 27, Holm p=0,00016.

Friedman testi p=7,0e-19. Ortalama sıralar: LKH 1,68, ILS 3,10, E2BSO 3,45, P-AOEA 4,05, GLS 5,62, R2DMA 6,05. Şekil: `BRIEF/17_sota_family_benchmark.png`.

**Dersler** (tasarımda zorunlu karşılık bekleniyor):

| # | Ders |
|---|---|
| L1 | Arızaların hepsi sessizdi. Her bileşen için sözleşme testi ve telemetri zorunlu. |
| L2 | En büyük kaldıraç yerel arama hızı. Depoda aday listesi ve don't-look bit yok. |
| L3 | Mesafe ve çeşitlilik ölçüleri gösterimden bağımsız olmalı: döndürme, yön ve sıralama değişmezliği. |
| L4 | Kredi ataması oran temelli ya da kayan pencereli olmalı ve uniform kola karşı sınanmalı. |
| L5 | Kabul eşikleri kötüleşme (Δ) dağılımına göre kalibre edilmeli. |
| L6 | Kesin değerlendirme muhasebesi gerekli ve süre döngü içinde denetlenmeli. |
| L7 | En iyi çözüm arşivi her popülasyon değişikliğinden sonra güncellenmeli. |
| L8 | Okunmayan yapılandırma alanı olmamalı; belgelenen her operatör uygulanmış olmalı. |
| L9 | Kısıtlar, uygunluk hesabında kullanılan çözümleyicide uygulanmalı. Yönlü matriste ters yaya sessiz düşüş olmamalı. |
| L10 | Üretim amacı depoya bağlı olmalı; TSP çevrimi rota amacının yerine konmamalı. |

## 4. Problem sözleşmeleri

Tasarımlar bu sözleşmelere göre yapılmalı.

| Kod | Problem | Tanım ve amaç | Veri ve ölçek | Doğrulama sözleşmesi |
|---|---|---|---|---|
| P1 | TSP (simetrik, akademik) | Kapalı Hamilton çevrimi; amaç, son-ilk kenar dahil matris maliyeti. Bir "değerlendirme" bir tam aday tur hesabıdır. | TSPLIB arşivi: 111 simetrik örnek ve 32 optimum tur | Hamilton çevrimi doğrulaması |
| P2 | ATSP (akademik ve üretim matrisleri) | Yönlü matris, c(i,j) ≠ c(j,i). Üretim matrisleri metrik değil: üçgen eşitsizliği varsayılmaz. | Depoda yalnız ft53 var; TSPLIB ATSP kümesinin içe aktarılması gerekiyor | Yönlü maliyet korunmalı |
| P3 | CVRP | Tek kapasite. Split tabanlı sözlüksel amaç: olurluluk > araç sayısı > maliyet. | CVRPLIB (8 ham dosya; veritabanına henüz yüklenmedi) | Çok rotalı doğrulama |
| P4 | CVRPTW | Zaman pencereli CVRP | Solomon (56 ham dosya; veritabanına henüz yüklenmedi) | Çok rotalı doğrulama |
| P5 | **UniRide dalga rotalaması** (üretim) | Ayrıntılar tablonun altında | Ayrıntılar tablonun altında | Bağımsız olurluluk sertifikası |
| P6 | **Heterojen filo** (üretim) | Ayrıntılar tablonun altında | Ayrıntılar tablonun altında | Tip bazlı sertifika |
| P7 | **Gün düzeyi** (üretim) | Ayrıntılar tablonun altında | Ayrıntılar tablonun altında | Kanıt etiketleri |
| P8 | **Belediye ölçeğinde paratransit** (hedef G2) | Ayrıntılar tablonun altında | Ayrıntılar tablonun altında | — |

**P5 UniRide dalga rotalaması.**

Tanım:
- Tek depo (kampüs) D vardır. Bir dalga, aynı yönü (toplama ya da bırakma) ve aynı çapa zamanını paylaşan taleplerden oluşur.
  - Toplama çapası: ilk ders başlangıcından 15 dk önce kampüse varış.
  - Bırakma çapası: son ders bitişinden 15 dk sonra kampüsten kalkış.
- Talep birimi yolcu ayağıdır: bir öğrenci günde iki ayak üretebilir ve aynı durakta birden çok ayak olabilir.

Kısıtlar:
- Yönlü süre matrisi kullanılır (centi-dakika ızgarası, `time_scale=100`). Matris metrik değildir; doğrudan depo–durak süresi alt sınır sayılamaz.
- İki ayrı kapasite havuzu vardır: **Sw** (tekerlekli sandalye) ve **So** (oturan). Boş bir So yeri Sw'nin yerine geçemez. Varsayılan şablon 4 Sw / 5 So.
- Tur süresi, boş çıkış ve dönüş dahil tüm yönlü yayların toplamıdır ve T'yi aşamaz (varsayılan 150 dk; 30–300 aralığı).
- Yolculuk süresinin tanımı yöne özgüdür ve her yolcu için en fazla R olabilir (varsayılan 90 dk; 15–240 aralığı):
  - toplamada vi'den D'ye kadar olan yaylar sayılır; ilk boş yolculuk hariç;
  - bırakmada D'den vi'ye kadar olan yaylar sayılır; dönüş hariç.
- Biniş ve bekleme süresi şu an hesaba katılmıyor. Dalga içinde bireysel zaman penceresi yok.

Amaç ve doğrulama:
- Sözlüksel amaç: olurluluk > rota sayısı > toplam süre.
- Her çıktı, çözücüden bağımsız olurluluk sertifikasından geçmeli. Sertifika kapsamayı, sürekliliği, depo kapanışını, Sw/So'yu, T'yi ve yöne özgü R'yi kontrol eder.
- Koltuk alt sınırı: Lseat = max(⌈nSw/qSw⌉, ⌈nSo/qSo⌉).

Ölçek:
- Dalga başına ≈2–20 yolcu.
- Günde 19–27 öğrenci; arşivlenmiş haftada 226 yolcu ayağı.
- Matriste 29 konum; günde 3–6 araç.

Mevcut yöntem: GA + Split ([Prins 2004](https://doi.org/10.1016/S0305-0548%2803%2900158-8)).

**P6 Heterojen filo.**
- Her araç tipinin kendi Sw/So kapasitesi, isteğe bağlı ortak toplam koltuk sınırı ve 10 dk soğuma süresi var.
- Büyük araç için kota menüsü kullanılıyor: q=0..3 ve "tümü büyük" seçeneği.
- Örnek tipler: minibüs (4 Sw / 5 So), sedan (0 Sw / 4 So), Doblò.
- Amaç: (olursuzluk, ödünç alınan tipin rota sayısı, maliyet).

**P7 Gün düzeyi.**
- Her rota bir zaman aralığına dönüşür: toplamada [a−t, a], bırakmada [a, a+t].
- Bir araç, iki havuz da yetiyorsa ve bir sonraki rota "önceki bitiş + soğuma" anından sonra başlıyorsa yeniden kullanılabilir.
- Filo en küçüklemesi dal-sınır yöntemiyle yapılıyor (50 000 düğüm bütçesi). Kanıt etiketleri: kanıtlanmış en küçük, kanıtsız tanık, eksiklik.
- Dalga menüleri arasından CP-SAT ile seçim yapılıyor. Sözlüksel amaç: (1) araç tepe eşzamanlılığı, (2) araç-dakikası, (3) toplam araç-dakikası, (4) seçenek indeks toplamı.
- ε-kısıt ile Pareto analizi yapılıyor: sahip olunan minibüs sayısı, en büyük günlük ödünç araç sayısı, haftalık ödünç saat.
- **Rotalama ve atama şu an ardışık.** Sonuç, sezgisel rotalamaya koşullu bir filo minimumu; ortak minimum değil.
- Kesin referans planlanmış ama kodu yok: olurlu rotaların tam sayımı ve iki aşamalı küme bölümleme (AMPL).

**P8 Belediye ölçeğinde paratransit (G2).**
- Kapıdan kapıya hizmet, isteğe bağlı ya da önceden rezervasyon.
- Zaman pencereleri, büyük heterojen filo, gerçek zamanlı süreler (Google Maps, tam sayı saniye).
- Günde yüzlerce ila binlerce talep; DARP benzeri bir problem.
- Henüz kodu yok; tasarımlar bu yöne genişleyebilir olmalı.

**Protokol** (P1–P4 akademik):
- Birincil protokol: sabit amaç-değerlendirme bütçesi (`atomic_upper_bound_v1`).
- İkincil protokol: algoritmaya özgü sonlanma. Ayrı etiketlenir ve birincil sonuçlarla havuzlanmaz.
- Tohumlar, örnek kimliği + tekrar indeksinden SHA-256 ile türetilir.
- Bilimsel protokol modunda kayıt katmanı, kesin değerlendirme muhasebesi olmayan algoritmayı reddeder.

## 5. Mevcut yapı taşları

Bu bölüm yalnız ad ve sözleşme düzeyindedir; kodu açma.

| Bileşen (depo adı) | Ne sağlıyor | Not |
|---|---|---|
| `objective_budget.py`: `ObjectiveEvaluationBudget`, `improve_two_opt_budgeted`, `improve_or_opt_budgeted` | Kesin değerlendirme sayacı; bütçeli 2-opt ve Or-opt (TSP ve yönlü ATSP) | Aday listesi ve don't-look bit yok |
| `three_opt.py`: `improve_three_opt` | Simetrikte 7 yeniden bağlama; yönlüde segment yönü korunur | Bütçeli denetleyici `fairness.py`'de |
| `sota_tsp/alns_tsp.py`: `ALNS_TSP` | Ropke–Pisinger segment ağırlıkları doğru uygulanmış | SA başlangıç sıcaklığı mutlak (100); kalibre edilmeli |
| `sota_tsp/destroy_ops.py`, `repair_ops.py` | Random, Worst, Shaw ve Related removal; Greedy, Regret-2 ve Regret-3 insertion | — |
| `string_split_decoder.py`: `SplitDecoder` | Sw/So, TW modları ve `max_ride_time` ile Split | CVRP'de O(n·L), toplama-TW'de O(n·L²) |
| `linear_split_decoder.py`, `typed_split_decoder.py` | Yumuşak cezalı sınırlı Split; tipli (heterojen) Split | — |
| `ga_split_engine.py` (`ga_split`), `ga_split_typed_engine.py` (`ga_split_hf`, `solve_typed_menu`) | Üretim varsayılanı GA-Split; kota menüsü | Kontrol kolu |
| `feasibility_certificate.py`, `objective_rank.py` | Bağımsız sertifika; sözlüksel sıra | Her tasarım bunları kullanmalı |
| `planning/typed_day_selection.py` | CP-SAT ile gün seçimi | — |
| `typed-fleet-assignment.ts`, `assignPhysicalVehicles` | Sabit rotalar için filo en küçükleme (dal-sınır) | TypeScript |
| `pyvrp_cvrp_engine.py` (PyVRP/HGS), `ortools_cvrp_engine.py`, `vroom_cvrp_engine.py` | Harici çözücü adaptörleri | PyVRP'nin Sw/So'yu çok boyutlu yük olarak modelleyip modelleyemediği DOĞRULANMADI |
| `exact/wave_instance.py`; `docs/designs/EXACT_SOLVER_AMPL_DESIGN.md` | Kesin referansın veri sözleşmesi ve tasarımı | Çözücü kodu yok |
| `academic_benchmark/fairness.py` (`FairComparisonManifest`), `native_protocol.py`, `capabilities.py` (VERIFIED/CANDIDATE/PLANNED) | Adil protokol, kayıt kapısı, katalog yaşam döngüsü | — |
| elkai (LKH), LKH-3 ikilisi (`RECOMBINATION = GPX2`), GA-EAX (açık kaynak) | Harici referanslar | Lisanslar §9'a göre belirtilmeli |

**Depoda olmayanlar:** aday listeleri ve don't-look bitleri; GPX/GPX2/EAX; SWAP* ve granüler komşuluklar; rota havuzu ve küme bölümleme (yalnız planlı); DARP olurluluk denetimi.

## 6. Tasarım kuralları (zorunlu)

1. Bileşen ödünç al, metafor alma. Her bileşen için kaynak göster.
2. Her bileşenin bir sözleşme testi olsun. Örnekler: GPX çocuğu tüm ortak kenarları içerir ve en iyi ebeveynden kötü olamaz; mesafe ölçüsü döndürmeye ve yöne göre değişmez; özdeş popülasyonun entropisi 0; LAHC yörüngeye özgüdür; arşiv sözleşmesi tutar.
3. Telemetri: Her mod, operatör ve kabul kararının sayacı tutulsun. İmza mekanizması kararların %5'inden azında çalışıyorsa uyarı üretilsin.
4. Tek bütçe para birimi kullanılsın. "Bir değerlendirme"nin tanımını yap ve süreyi döngü içinde denetle; bütçe aşımı en fazla %5 olabilir. Aynı tohum aynı sonucu vermeli.
5. Her mekanizmanın açık/kapalı ablasyon kolu olsun. Katkısı gösterilemeyen mekanizma çıkarılır.
6. Güçlü kontrol kolu kullanılsın: aynı yerel aramayı kullanan ILS; VRP'de PyVRP/HGS ve mevcut GA-Split.
7. ATSP'ye uygun tasarla. Ya yönü koruyan hamleler kullan ya da yönlü delta hesapla. Simetrik operatörler yalnız 2n dönüşümüyle kullanılabilir. Metrik olmayan matriste "uzun segment ihlal eder" varsayımı yapılmaz.
8. Kısıtlar uygunluk hesabında kullanılan çözümleyicide uygulanmalı. Olursuzluk yönetimini açıkça seç: sert kısıt, uyarlanabilir ceza ya da onarım.
9. Üretim tasarımları depoya bağlı amacı ve sertifikayı kullanmalı.
10. Eşit ayar bütçesi (irace) kullanılsın. Geliştirme ve test örnekleri ayrı tutulsun.

## 7. Başlangıç fikirleri (bağlayıcı değil)

BRIEF/03 §5'teki beş öneriyi eleştir. Korunmaya değer olanları geliştir, değmeyenleri gerekçesiyle ele.

| Öneri | Özet |
|---|---|
| EB-PXILS | E2BSO'nun ardılı: çoklu ILS, GPX2 ve doğru normalize entropiyle rekombinasyon/sarsım dengesi; yörünge başına LAHC |
| DAR-MA | R2DMA'nın ardılı: ebeveynler arası bozuk-çift mesafesine göre GPX2 / EAX / kick / BB-Merge arasında bandit ile seçim; HGS tarzı yanlı uygunluk. Hipotez H1, D2 arazi taramasıyla sınanır. En yakın önceki çalışma [Varadarajan & Whitley 2021](https://doi.org/10.1145/3449639.3459281). |
| BA-LNS | P-AOEA'nın ardılı: SISR + regret/blink onarım + FRR-MAB; CVRPTW'ye aktarım |
| BB-Merge | Elitlerin ortak kenarlarını sabitleyip kalan problemi yoğun biçimde yeniden optimize etme |
| EAX-MA | GA-EAX'in sarmalanması; tavan kolu |

**Değerlendirmen beklenen ek yönler.** Her birini kaynakla değerlendir; kabul ya da ret gerekçesini yaz.
- **D1, UniRide için HGS ailesi** ([Vidal vd. 2012](https://doi.org/10.1287/opre.1120.1048); [Vidal 2022](https://doi.org/10.1016/j.cor.2021.105643); [Wouda vd. 2024](https://doi.org/10.1287/ijoc.2023.0055)). İki boyutlu (Sw/So) yük, yöne özgü R ve T için uyarlanabilir cezalar, dev tur + yönlü Split, granüler komşuluk. PyVRP'nin yeniden kullanılıp kullanılamayacağını ve uzatma sınırını değerlendir.
- **D2, rota havuzu + küme bölümleme matheuristic'i.** Birden çok sezgiselin ürettiği olurlu rotalar havuzlanır ve CP-SAT ya da MIP ile seçilir. Küçük dalgalarda tam rota sayımıyla (planlanan kesin referans) ve gün düzeyi menü üretimiyle doğal biçimde bağlanır.
- **D3, gün düzeyi bütünleşik arama.** Dalga rotalaması ile araç yeniden kullanımı ortak bir amaçla çözülür (çok seferli VRP). Dalgalar arası LNS ve CP-SAT alt problemleri.
- **D4, belediye ölçeği için SISR/ALNS** ([Christiaens & Vanden Berghe 2020](https://doi.org/10.1287/trsc.2019.0914)). Önceden hesaplanmış birikimli sürelerle sabit zamanlı olurluluk denetimi. Bu tekniklerin kaynaklarını sen bul ve doğrula.
- **D5, ATSP'ye özgü bileşenler.** Yönü koruyan Or-opt ve or-3opt + aday listeleri ([Kanellakis & Papadimitriou 1980](https://doi.org/10.1287/opre.28.5.1086)); EAX-ATSP ([Nagata & Soler 2012](https://doi.org/10.1016/j.eswa.2012.02.029)); 2n dönüşümüyle LKH-3; metrik olmayan matrisler.
- **D6, öğrenme destekli bileşenler.** Yalnız ölçülebilir katkı ve ablasyonla: bandit tabanlı operatör seçimi, aday kenar öğrenimi (Wang vd. 2025 ön baskıları; hakemsiz oldukları ayrıca işaretlenmeli).

## 8. İstenen çıktı

Tek dosya: `BRIEF/ASTRA6_YENI_ALGORITMA_TASARIMLARI.md`. Dil Türkçe; teknik terimler İngilizce kalabilir. Yapı:

1. **Özet** (en fazla 15 madde).
2. **Kaynak bulgu tablosu** (R1, R2, …). Sütunlar: no | iddia | kaynak (tam künye + DOI/URL) | kaynak türü (hakemli / ön baskı / belge) | güven | DOĞRULANDI? Kaynağı açıp iddiayı gördüysen "DOĞRULANDI", görmediysen "DOĞRULANMADI" yaz. BRIEF/06 ve BRIEF/07'de künyeler doğrulandı; içerik iddiası için kaynağı yine aç ya da "BRIEF raporuna dayanarak" yaz.
3. **Problem → bileşen eşlemesi.** P1–P8'in her biri için literatürde başarıyı sağlayan bileşenler ve referans çözücüler (kısa tablo).
4. **Algoritma portföyü:** 5–8 tasarım, her biri §8.1 kartıyla. Kapsam koşulları:
   - P1 TSP için en az 1 tasarım;
   - P2 için en az 1 ATSP'ye özgü tasarım (yönlü, metrik olmayan);
   - P5 için en az 2 tasarım: biri bugünkü ölçek (2–20 yolcu/dalga), biri P8 belediye ölçeği;
   - P3/P4 için en az 1 tasarım (P6'ya genişleyebilir);
   - P7 için en az 1 tasarım.

   Bir tasarım birden çok problemi kapsayabilir. Her düzey (TSP / dalga / gün) için bir "birincil öneri" işaretle.
5. **Portföy karşılaştırma tablosu.** Sütunlar: tasarım | problemler | kontrol koluna göre beklenti | referansa göre beklenti | güven | yenilik | efor | üretim değeri | risk.
6. **Deney ve ablasyon planı.** Örnek kümeleri (geliştirme ve test ayrı), bütçe (birincil sabit değerlendirme; ikincil native, havuzlanmaz), tohum sayısı, ayar (eşit irace bütçesi) ve istatistik (Wilcoxon+Holm, Friedman, etki büyüklüğü, performans profilleri; [Derrac vd. 2011](https://doi.org/10.1016/j.swevo.2011.02.002); [Kendall vd. 2016](https://doi.org/10.1057/jors.2015.77)). Kontrol ve referans kollar:
   - TSP: aynı hızlı yerel aramalı ILS, LKH-3, GA-EAX, ALNS-TSP, OR-Tools GLS.
   - ATSP: 2n dönüşümüyle LKH-3, Or-opt/3-opt ILS; varsa EAX-ATSP.
   - CVRP/CVRPTW: PyVRP (HGS), OR-Tools, VROOM, mevcut GA-Split; BKS değerleri.
   - UniRide: `ga_split` ve `ga_split_hf`; Sw/So modellenebiliyorsa PyVRP; küçük dalgalarda kesin referansa (rota sayımı + küme bölümleme) göre optimum açığı.

   Her tasarımın ablasyon kollarını ve yanlışlama ölçütünü yaz.
7. **Uygulama yol haritası.** Önce ortak altyapı (hızlı yerel arama, GPX2, sözleşme testleri, telemetri). Sonra tasarım başına sıra, bağımlılıklar ve kişi-gün tahmini. İlk iki haftanın adımları ve BRIEF/03'teki G0–G2 kapılarıyla uyumlu kabul kapıları.
8. **Riskler ve sahibin vermesi gereken kararlar.**
9. **Arama günlüğü:** ana sorgular; reddedilen kaynaklar ve ret nedeni.

### 8.1 Tasarım kartı şablonu

Her tasarım için bütün alanlar zorunlu.

| Alan | İçerik |
|---|---|
| Ad ve önerilen kimlik | Betimleyici bir ad ve depo düzenine uygun kimlik (ör. `Core-XXXX-TSP`, `Core-XXXX-CVRPTW`); "SOTA" kullanılmaz |
| Hedef problemler ve düzey | P1–P8 ve düzey (TSP / dalga / gün) |
| Soy ağacı | Hangi başarılı algoritmadan hangi bileşenin alındığı, kaynaklarıyla |
| Eski fikirle bağ | Sürdürdüğü eski fikir (E2BSO / R2DMA / P-AOEA, varsa) ve eski hatanın (L1–L10) bu tasarımda nasıl önlendiği |
| Temsil | Temsil ve arama uzayı |
| Olurluluk yönetimi | Sw/So, T, yöne özgü R, TW ve tip/kota için sert kısıt mı, uyarlanabilir ceza mı, onarım mı; hangi çözümleyicide |
| Sözde kod | En fazla 25 satır |
| Bileşen tablosu | bileşen \| kaynak \| sözleşme testi \| telemetri sayacı \| ablasyon kolu |
| Bütçe muhasebesi | "Bir değerlendirme" bu tasarımda neye karşılık geliyor; atomik üst sınıra nasıl uyuyor; süre denetimi nerede |
| Karmaşıklık | Hamle değerlendirme ve olurluluk denetimi maliyeti (n ve L cinsinden) |
| Yönlü ve metrik olmayan matris | Tasarımın bu durumda nasıl davrandığı |
| Neden başarılı olması bekleniyor | "Kaynaklar ne diyor" (R-numaralarıyla) ve ayrı bir "Bizim yorumumuz" |
| Performans hipotezi | Kontrol koluna ve referansa göre yön; güven (düşük / orta / yüksek); yanlışlama ölçütü (hangi sonuç tasarımı çürütür) |
| Yenilik | En yakın 2–3 çalışma, fark ve doğrulama durumu. Yenilik yoksa açıkça "yok" yaz |
| Uygulama | Yeniden kullanılacak depo bileşenleri (§5'teki adlarla), yeni yazılacaklar, kişi-gün, bağımlılıklar |
| Riskler ve açık sorular | — |
| Kabul kapısı | Hangi ölçüt sağlanınca kataloğa (CANDIDATE → VERIFIED) ya da üretime alınır |

## 9. Kalite kuralları

- **Kaynaklar:** Önce BRIEF/06 ve BRIEF/07'yi kullan. Yeni kaynakta DOI ya da URL ver ve doğrulama durumunu yaz. DOI, yazar, yıl ya da sayı uydurma; kaynak bulamazsan bunu açıkça söyle.
- **Sayılar:** Sayılar yalnız kaynaktan ya da BRIEF ekinden gelir. Ekten alınan sayılarda dosya adını belirt. Beklenen kazanç için sayı uydurma; yön ve güven düzeyi yaz.
- **Ayrım:** "Kaynaklar ne diyor" ile "Bizim yorumumuz" ayrı tutulsun. Hakemsiz ön baskıları (arXiv) ayrıca işaretle.
- **Lisanslar:** LKH, GA-EAX, PyVRP, OR-Tools ve VROOM kullanımı önerirken lisansı belirt; bilinmiyorsa "DOĞRULANMADI" yaz.
- **Biçim:** Tablo kullan. Kapsam önemli, ama doğruluk her şeyden önce gelir. Rapor kullanılmadan önce kaynaklarına karşı denetlenecek.

## 10. Bilinen açık sorular

Bunları çözmen beklenmiyor; tasarımda hesaba kat ve gerekirse çözüm yolu öner.

- GPX2'nin 2n dönüşümüyle ATSP'de verimi DOĞRULANMADI.
- elkai'nin `RECOMBINATION` parametresini açıp açmadığı DOĞRULANMADI; açmıyorsa LKH-3 ikilisi gerekir.
- GA-EAX'in lisansı ve yönlü örnek desteği DOĞRULANMADI.
- PyVRP'nin Sw/So'yu çok boyutlu yük olarak modelleyip modelleyemediği DOĞRULANMADI.
- DAR-MA'nın yeniliği yayından önce odaklı bir taramayla doğrulanmalı.
- Üretimde dalgalar küçük (2–20 yolcu). TSP düzeyindeki kazancın üretimdeki değeri sınırlı; üretim kazancı büyük olasılıkla dalga ve gün düzeyinden gelir. Bunu portföy önceliğinde dikkate al.
