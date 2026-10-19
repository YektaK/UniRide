# UniRide akademik TSP/ATSP hattı: hızlı yerel arama (fast_ls), ILS-fast ve PX-ILS prototipi

Tarih: 2026-10-14. Planın ilgili maddeleri: Faz 0.1 (O1 hızlı LS), 0.4'ün GPX kısmı (O3), karar deneyi D1 ve §5 Ö1 (EB-PXILS) için ilk prototip. Depoda hiçbir dosya değiştirilmedi ve git işlemi yapılmadı; bütün kod ve sonuçlar çalışma dizininde.

## 0. Özet

- **fast_ls (Numba)** dizi tabanlı turla çalışıyor: konum indeksi, K=10 aday listesi, don't-look-bit kuyruğu ve kesin delta. Simetrik örneklerde 2-opt (kısa taraf ters çevrilir), iki yönlü Or-opt (1–3) ve isteğe bağlı or-3opt kullanılıyor. Yönlü örneklerde yönü koruyan Or-opt ile or-3opt kullanılıyor. Simetri matristen otomatik algılanıyor.
- **Sözleşme testleri:** 51/51 geçti.
- **D1 kararı: KISMEN SAĞLANDI.**
  - Hız ölçütü (≥50× kick/s) her üç örnekte açık farkla sağlandı: 23 672× (a280), 100 330× (pr439), ≈1,7·10⁶× (pr1002).
  - Kalite ölçütü (±%0,5) K=10 yapılandırmasında yalnız rastgele başlangıçlarda sağlandı (a280: −%0,96, fast daha iyi, %95 GA [−2,18; +0,26]). Kick'lenmiş yerel optimumlardan sağlanmadı (a280: +%1,91, %95 GA [+0,11; +3,71]). K=20 bu açığı kapatıyor (a280: −%0,04; pr1002: −%0,24).
- **Ana kıyas (10 örnek × 5 tohum × 30 s):**
  - ILS-fast 50 koşunun 36'sında optimum buldu (ortalama açık %0,058).
  - Deponun ILS'i 40 koşunun 15'inde optimum buldu (%2,02).
  - LKH (elkai, runs=10) 50/50 optimum buldu.
  - ILS-fast–repo-ILS: 25 kazanç/15 beraberlik/0 kayıp, Wilcoxon p=1,22·10⁻⁵ (Holm 2,45·10⁻⁵).
  - ILS-fast–LKH: 0/36/14, p=9,67·10⁻⁴ (Holm 9,67·10⁻⁴). LKH daha iyi.
- **ATSP (ft53):**
  - ILS-fast 10/10 tohumda optimum buldu (6905). Optimuma ulaşma süresi en çok 0,185 s; hiç ters çevirme uygulanmadı.
  - elkai asimetrik matrisi kendiliğinden `TYPE: ATSP` olarak çözüyor (3/3 optimum). 2n dönüşümü de 6905 verdi.
- **PX-ILS / GPX ablasyonu (4 örnek × 5 tohum × 30 s):** GPX'in katkısı gösterilemedi. GPX açık–kapalı: 7/5/8, p=0,776 (Holm 1,0). GPX havuz çeşitliliğini %24–55 azaltıyor; pr1002'de açık kol daha kötü.

## 1. Veri ve ortam (önemli yerine koyma)

Oturum yeniden başladıktan sonra depo kökü okunabiliyordu ama `academic_benchmark/` alt ağacı `PermissionError` vermeye başladı. İzin iki kez yeniden istendi (depo kökü ve `academic_benchmark`); yeni süreçlerde de erişim reddedildi. Bunun üzerine kanonik **TSPLIB95** dosyaları, depodaki `ft53.json`'ın kaynak olarak gösterdiği `comopt.ifi.uni-heidelberg.de` adresinden indirildi:

- `ft53.atsp` dosyasının SHA-256'sı depo kaydıyla **birebir aynı** (692ae545…2634).
- `.tsp` dosyaları depoya karşı doğrulanamadı, çünkü depo okunamıyordu.
- Optimumlar, erişim kesilmeden önce bu oturumda `tsplib.db`'den okunan değerlerdir ([inst.py]({{artifact:2c1acf1e-fb74-4331-97d2-fe62846cbf54}}) içinde `OPT`).
- Mesafe yapımı `bench_common.load_instance` ile aynıdır (EUC_2D, nint).
- Deponun kodu (`uniride_core`) okunabilir durumdaydı; repo-ILS kolu `bench_common.ils`'i değiştirilmeden çağırıyor.

Makinede başka bir iş hattı CPU kullanıyordu ve bizim tarafımızda en fazla 3 süreç aynı anda çalıştı. Bu yüzden süreye bağlı ölçümler yük altında alındı. Örneğin LKH a280'de 13,6 s sürdü; önceki oturumda ≤280 düğümde ortalama 3,3 s idi. Sandbox `multiprocessing` borularına izin vermediği için kıyas yürütücüsü bağımsız işçi süreçleriyle ve atomik "claim" dosyalarıyla çalışıyor.

## 2. Yöntem

### 2.1 fast_ls ([fast_ls.py]({{artifact:21a30d74-fcf7-479e-89ea-33146a8d75d4}}))
- **Gösterim:** `tour[pos]` ve `pos[city]` (int32). `succ`/`pred` O(1).
- **Adaylar:** Satır başına en yakın K komşu. Yönlü durumda çıkış listesi (i→j ucuz) ve giriş listesi (j→i ucuz) ayrı tutuluyor.
- **Kuyruk:** FIFO etkin düğüm kuyruğu. Don't-look biti, düğümün kuyrukta olmaması demek. Bir hamleden sonra değişen kenarların uçları kuyruğa geri alınıyor.
- **Hamleler** (ilk iyileştirme, kısmi kazanç budaması, kesin tamsayı delta):
  - simetrik: 2-opt (kısa taraf ters çevrilir); Or-opt, segment 1–3, her iki yönde, aday çevresinde dört ekleme biçimi; isteğe bağlı or-3opt;
  - yönlü: yönü koruyan Or-opt (ters çevirme yok, x→s1 giriş listesi ve s2→y çıkış listesi); or-3opt segment değişimi A B C → A C B, ileri ve ayna aramayla.
- **Uygulama:** Bütün yön koruyan hamleler "bitişik iki bloğu takas et" ilkeline indirgeniyor. Üç eşdeğer döngüsel takastan en ucuzu seçiliyor (maliyet n − en büyük blok). 2-opt kısa tarafı ters çeviriyor. Ters çevirme sayacı (`ST_REV`) tutuluyor.
- **Tam LS** (`optimize`, `ls_full`): Kuyruk boşaldığında bir doğrulama taraması yapılıyor ve hâlâ iyileştiren aday hamlesi olan düğümler yeniden etkinleştiriliyor. Bu tarama, DLB'nin tek başına garanti etmediği aday-komşuluk yerel optimumluğunu sağlıyor; ilk smoke testinde d493/u724'te 1–2 düğüm kalıyordu. ILS içinde yalnız kuyruk LS'i çalışıyor; tarama yapılmıyor.

### 2.2 ILS-fast ([ils_fast.py]({{artifact:5defbdf9-5b9d-4e79-9717-31d67929303f}}))
- **Kick:** Segment-yerel double-bridge. Rastgele bir konumdan başlayan ardışık B, C, D segmentleri (her biri 1..Lmax) A B C D → A D C B olarak yeniden diziliyor. Dört kenar değişiyor, segmentlerin yönü korunuyor; bu yüzden kick ATSP için de geçerli.
- **LS:** Kick sonrasında yalnız değişen 8 uç kuyruğa alınıyor; diğer düğümlerin DLB'si açık kalıyor.
- **Kabul:** Mevcut turdan kötü değilse kabul ediliyor, kötüyse geri alınıyor.
- **Rastgelelik ve süre:** Kendi xorshift64* üreteci kullanılıyor. Sabit kick bütçesinde ve aynı tohumda sonuç tamamen belirlenimci. Süre denetimi ≈10 ms'lik toplu çağrılar arasında yapılıyor (aşım ≤0,12 s).
- **Telemetri:** kick, iyileşen kick, kabul, eşit kabul, yeni en iyi, LS hamle sayıları, ters çevirme sayısı.
- **Kıyas yapılandırması:** K=10, Lmax=100 ve simetrikte or-3opt açık. Ayar kıyas dışı pr299/d493/u724 üzerinde yapıldı (2 tohum × 3 s ve 10 s; [tuning_raw.csv]({{artifact:e68538e0-9bf7-4432-a44e-87349f79d4ee}})). En iyi ortalama açık %0,069 oldu. Spesifikasyondaki yalın 2-opt+Or-opt varyantı `use_or3=False` ile çalıştırılabilir ve D1'de ölçüldü.

### 2.3 PX-ILS ve GPX ([px_ils.py]({{artifact:04d2e421-9d48-4994-87a9-704e0816f7e8}}))
- **Basit GPX (simetrik):**
  - İki ebeveynin birleşik grafiğinden ortak kenarlar çıkarılıyor; kalan fark grafiğinin bağlı bileşenleri union-find ile bulunuyor.
  - Bileşen dışındaki düğümlerden geçen ortak yollar vekil (surrogate) kenara daraltılıyor.
  - Sınırı tam 2 vekil/ortak kenarın geçtiği bileşen "uygulanabilir" sayılıyor. Böyle bir bileşende her iki ebeveyn aynı iki kapı arasında tek bir Hamilton yolu izliyor; o bileşende kısa yol hangi ebeveyndeyse o seçiliyor.
  - Diğer her şey daha iyi ebeveynden alınıyor. Böylece çocuk ≤ min(ebeveynler) oluyor ve ortak kenarların %100'ü korunuyor.
  - Çocuk Hamilton döngüsü olarak yeniden doğrulanıyor; değilse taban ebeveyne dönülüyor.
  - İlk sürümde vekil-kenar daraltması yoktu. Örneğin 2-opt farkının ters çevrilmiş ortak yolu dış sayılıyor, bileşen 4 geçişli görünüyor ve neredeyse hiç geçiş yapılmıyordu. Bu, kıyas dışı d493/u724 pilotunda telemetriden görüldü ve ablasyondan önce düzeltildi; sözleşme testleri düzeltilmiş sürümle koşuldu.
- **Havuz:** m=8 ILS-fast yörüngesi var. Her epokta (yörünge başına n/2 kick) her yörünge rastgele bir eşle GPX'leniyor.
  - Çocuk, kapı düğümlerinden kuyruk LS'inden geçiriyor.
  - Çocuk kötü ebeveynden kesin daha iyiyse ve iyi ebeveynin klonu değilse kötü ebeveynin yerine geçiyor.
  - `use_gpx=False` aynı m yörüngeyi GPX olmadan çalıştırıyor; bu, eşit süreli kontrol kolu.
  - Entropi denetimi ve LAHC (planın Ö1'i) bu prototipte yok.

## 3. Sözleşme testleri ([test_contracts.py]({{artifact:9524d46b-54af-4177-9dfb-fda557866dca}}), çıktı [test_contracts_output.txt]({{artifact:5c9a8e06-242c-4ace-976f-30995b289764}}))

| ID | Sözleşme |
|---|---|
| C0 | Simetrik matris yönsüz, asimetrik matris yönlü algılanıyor |
| C1 | Her hamleden sonra tur bir permütasyon ve `pos` tutarlı |
| C2 | Her hamleden sonra ve 20 000 kick'lik ILS sonunda artımlı maliyet = yeniden hesaplanan maliyet |
| C3 | ATSP'de ters çevirme sayacı 0; her hamle en çok 3, kick en çok 4 yeni yönlü yay ekliyor (ters çevrilmiş segment olsaydı iç yaylar da yeni görünürdü). Simetrik hamle en çok 3 kenar değiştiriyor |
| C4 | Aynı tohum aynı tur (a280, ft53; 5000 kick); farklı tohum farklı tur |
| C5 | `optimize` sonrasında tüm düğümlerin kuru tarama (dry-run) taramasında iyileştiren aday hamle sayısı 0 (5 başlangıç; simetrik, simetrik+or3, ATSP) |
| C5b | K=n−1'de bağımsız kaba kuvvet 2-opt hiçbir iyileştirme bulmuyor (aday listeli 2-opt'un tamlığı) |
| C7 | GPX çocuğu geçerli, en iyi ebeveynden kötü değil, ortak kenarların %100'ünü içeriyor (a280, pr439, rastgele 120; 30'ar çift); GPX(T, döndür(ters(T))) = T |

Bilgi notu: K=n−1'de kaba kuvvetle tam Or-opt taraması rand_euc120'de 2, rd100'de 3 iyileştiren hamle buldu. Bunun nedeni kısmi kazanç budaması; tasarım gereği ve sözleşme değil. ft53'te yönlü Or-opt kaba kuvvet taraması 0 buldu.

```
PASS C0 symmetry detection (sym->undirected, asym->directed)
PASS C1 tour validity after every move [rand_euc120]  | moves=243 (2opt=198, or=45, or3=0)
PASS C2 incremental cost == recomputed after every move [rand_euc120]
PASS C3' symmetric: each move changes <= 3 undirected edges [rand_euc120]  | max_new_und=3
PASS C1 tour validity after every move [rd100]  | moves=215 (2opt=178, or=37, or3=0)
PASS C2 incremental cost == recomputed after every move [rd100]
PASS C3' symmetric: each move changes <= 3 undirected edges [rd100]  | max_new_und=3
PASS C1 tour validity after every move [a280]  | moves=562 (2opt=472, or=90, or3=0)
PASS C2 incremental cost == recomputed after every move [a280]
PASS C3' symmetric: each move changes <= 3 undirected edges [a280]  | max_new_und=3
PASS C1 tour validity after every move [ft53]  | moves=110 (2opt=0, or=86, or3=24)
PASS C2 incremental cost == recomputed after every move [ft53]
PASS C3 ATSP: no reversal applied (reversal counter == 0) [ft53]  | rev=0
PASS C3 ATSP: each move adds <= 3 new directed arcs (orientation kept) [ft53]  | max_new_dir=3
PASS C1 tour validity after every move [rand_asym150]  | moves=288 (2opt=0, or=220, or3=68)
PASS C2 incremental cost == recomputed after every move [rand_asym150]
PASS C3 ATSP: no reversal applied (reversal counter == 0) [rand_asym150]  | rev=0
PASS C3 ATSP: each move adds <= 3 new directed arcs (orientation kept) [rand_asym150]  | max_new_dir=3
PASS C1 tour validity after every move [rand_euc120+or3]  | moves=235 (2opt=208, or=19, or3=8)
PASS C2 incremental cost == recomputed after every move [rand_euc120+or3]
PASS C3' symmetric: each move changes <= 3 undirected edges [rand_euc120+or3]  | max_new_und=3
PASS C1 tour validity after every move [rd100+or3]  | moves=207 (2opt=156, or=37, or3=14)
PASS C2 incremental cost == recomputed after every move [rd100+or3]
PASS C3' symmetric: each move changes <= 3 undirected edges [rd100+or3]  | max_new_und=3
PASS C1 tour validity after every move [a280+or3]  | moves=588 (2opt=481, or=83, or3=24)
PASS C2 incremental cost == recomputed after every move [a280+or3]
PASS C3' symmetric: each move changes <= 3 undirected edges [a280+or3]  | max_new_und=3
PASS C3 kick: exact delta, valid, <= 4 new directed arcs [ft53]  | max_new_arcs=4
PASS C3 kick: exact delta, valid, <= 4 new directed arcs [rand_asym150]  | max_new_arcs=4
PASS C3 kick: exact delta, valid, <= 4 new directed arcs [a280]  | max_new_arcs=4
PASS C2 ILS (20000 kicks): valid tour, incremental == recomputed [ft53]  | cost=6905 incr=6905 kicks=20000
PASS C3 ILS on ATSP applies no reversal [ft53]  | rev=0
PASS C2 ILS (20000 kicks): valid tour, incremental == recomputed [rand_asym150]  | cost=21542 incr=21542 kicks=20000
PASS C3 ILS on ATSP applies no reversal [rand_asym150]  | rev=0
PASS C2 ILS (20000 kicks): valid tour, incremental == recomputed [rd100]  | cost=7910 incr=7910 kicks=20000
PASS C4 same seed -> same tour [a280]  | seed42 cost=2579/2579; seed43 differs=True
PASS C4 same seed -> same tour [ft53]  | seed42 cost=6905/6905; seed43 differs=True
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rand_euc120]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rd100]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [a280]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [ft53]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rand_asym150]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rand_euc120+or3]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rd100+or3]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [a280+or3]  | max cities with improving move=0
PASS C5b K=n-1: brute-force full 2-opt finds no improving move [rand_euc120]  | brute 2-opt improving=0; info: brute full Or-opt improving=2
PASS C5b K=n-1: brute-force full 2-opt finds no improving move [rd100]  | brute 2-opt improving=0; info: brute full Or-opt improving=3
INFO K=n-1 ATSP [ft53]: brute-force full directed Or-opt improving moves = 0
PASS C7 GPX child valid, <= best parent, keeps 100% common edges (30 pairs) [a280]  | feasible comps total=61, pairs with strict gain=0
PASS C7 GPX child valid, <= best parent, keeps 100% common edges (30 pairs) [rand_euc120]  | feasible comps total=0, pairs with strict gain=0
PASS C7 GPX child valid, <= best parent, keeps 100% common edges (30 pairs) [pr439]  | feasible comps total=0, pairs with strict gain=0
PASS C7 GPX(T, rotate(reverse(T))) == T (no components)
SUMMARY: 51/51 contracts passed, 0 failed (45.0 s)
PASS C0 symmetry detection (sym->undirected, asym->directed)
PASS C1 tour validity after every move [rand_euc120]  | moves=243 (2opt=198, or=45, or3=0)
PASS C2 incremental cost == recomputed after every move [rand_euc120]
PASS C3' symmetric: each move changes <= 3 undirected edges [rand_euc120]  | max_new_und=3
PASS C1 tour validity after every move [rd100]  | moves=215 (2opt=178, or=37, or3=0)
PASS C2 incremental cost == recomputed after every move [rd100]
PASS C3' symmetric: each move changes <= 3 undirected edges [rd100]  | max_new_und=3
PASS C1 tour validity after every move [a280]  | moves=562 (2opt=472, or=90, or3=0)
PASS C2 incremental cost == recomputed after every move [a280]
PASS C3' symmetric: each move changes <= 3 undirected edges [a280]  | max_new_und=3
PASS C1 tour validity after every move [ft53]  | moves=110 (2opt=0, or=86, or3=24)
PASS C2 incremental cost == recomputed after every move [ft53]
PASS C3 ATSP: no reversal applied (reversal counter == 0) [ft53]  | rev=0
PASS C3 ATSP: each move adds <= 3 new directed arcs (orientation kept) [ft53]  | max_new_dir=3
PASS C1 tour validity after every move [rand_asym150]  | moves=288 (2opt=0, or=220, or3=68)
PASS C2 incremental cost == recomputed after every move [rand_asym150]
PASS C3 ATSP: no reversal applied (reversal counter == 0) [rand_asym150]  | rev=0
PASS C3 ATSP: each move adds <= 3 new directed arcs (orientation kept) [rand_asym150]  | max_new_dir=3
PASS C1 tour validity after every move [rand_euc120+or3]  | moves=235 (2opt=208, or=19, or3=8)
PASS C2 incremental cost == recomputed after every move [rand_euc120+or3]
PASS C3' symmetric: each move changes <= 3 undirected edges [rand_euc120+or3]  | max_new_und=3
PASS C1 tour validity after every move [rd100+or3]  | moves=207 (2opt=156, or=37, or3=14)
PASS C2 incremental cost == recomputed after every move [rd100+or3]
PASS C3' symmetric: each move changes <= 3 undirected edges [rd100+or3]  | max_new_und=3
PASS C1 tour validity after every move [a280+or3]  | moves=588 (2opt=481, or=83, or3=24)
PASS C2 incremental cost == recomputed after every move [a280+or3]
PASS C3' symmetric: each move changes <= 3 undirected edges [a280+or3]  | max_new_und=3
PASS C3 kick: exact delta, valid, <= 4 new directed arcs [ft53]  | max_new_arcs=4
PASS C3 kick: exact delta, valid, <= 4 new directed arcs [rand_asym150]  | max_new_arcs=4
PASS C3 kick: exact delta, valid, <= 4 new directed arcs [a280]  | max_new_arcs=4
PASS C2 ILS (20000 kicks): valid tour, incremental == recomputed [ft53]  | cost=6905 incr=6905 kicks=20000
PASS C3 ILS on ATSP applies no reversal [ft53]  | rev=0
PASS C2 ILS (20000 kicks): valid tour, incremental == recomputed [rand_asym150]  | cost=21542 incr=21542 kicks=20000
PASS C3 ILS on ATSP applies no reversal [rand_asym150]  | rev=0
PASS C2 ILS (20000 kicks): valid tour, incremental == recomputed [rd100]  | cost=7910 incr=7910 kicks=20000
PASS C4 same seed -> same tour [a280]  | seed42 cost=2579/2579; seed43 differs=True
PASS C4 same seed -> same tour [ft53]  | seed42 cost=6905/6905; seed43 differs=True
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rand_euc120]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rd100]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [a280]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [ft53]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rand_asym150]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rand_euc120+or3]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [rd100+or3]  | max cities with improving move=0
PASS C5 local optimum: 0 improving candidate moves (5 starts, full scan) [a280+or3]  | max cities with improving move=0
PASS C5b K=n-1: brute-force full 2-opt finds no improving move [rand_euc120]  | brute 2-opt improving=0; info: brute full Or-opt improving=2
PASS C5b K=n-1: brute-force full 2-opt finds no improving move [rd100]  | brute 2-opt improving=0; info: brute full Or-opt improving=3
INFO K=n-1 ATSP [ft53]: brute-force full directed Or-opt improving moves = 0
PASS C7 GPX child valid, <= best parent, keeps 100% common edges (30 pairs) [a280]  | feasible comps total=92, pairs with strict gain=1
PASS C7 GPX child valid, <= best parent, keeps 100% common edges (30 pairs) [rand_euc120]  | feasible comps total=0, pairs with strict gain=0
PASS C7 GPX child valid, <= best parent, keeps 100% common edges (30 pairs) [pr439]  | feasible comps total=10, pairs with strict gain=3
PASS C7 GPX(T, rotate(reverse(T))) == T (no components)
SUMMARY: 51/51 contracts passed, 0 failed (61.6 s)
```

## 4. Karar deneyi D1 ([d1_experiment.py]({{artifact:92726e6c-eb4d-47f7-b00a-23278b246fa6}}), [d1_analysis.py]({{artifact:3cd6d1bd-36a1-4f00-a0b8-c28bf3991849}}); veriler [D1_results.csv]({{artifact:7c2c7071-6bf4-476f-94f5-279f1b597b08}}), [D1_summary.csv]({{artifact:45b9f8fe-e3e3-4407-8daa-81cd9e00c1a4}}))

**Tasarım:**
- **(a) Rastgele başlangıç:** Aynı rastgele başlangıç turlarından deponun `ls_moderate` LS'i (bench_common'ın her kick'te kullandığı çağrı, iyileşme durana dek tekrarlı) ile fast LS karşılaştırıldı.
- **(a2) Kick'lenmiş başlangıç:** Aynı kick'lenmiş yerel optimumdan karşılaştırıldı (fast-LS yerel optimumu + bench_common'ın global A C B D kick'i); bu, ILS içindeki gerçek çalışma noktası.
- **(b) Kick hızı:** Her motor kendi ILS döngüsüyle ölçüldü (ilk LS hariç).

Başlangıç sayıları: a280 için 30 rastgele + 10 kick'lenmiş; pr439 için 5 + 3; pr1002 için yalnız 3 kick'lenmiş (bkz. sapmalar). Fark = (fast − repo)/repo; negatif değer fast lehine.

| Örnek | Başlangıç türü | Varyant | n | Ort. fark % (fast − repo)/repo | %95 GA | Repo LS s (ort.) | Fast LS s (ort.) | |fark| ≤ 0,5 (nokta) |
|---|---|---|---|---|---|---|---|---|
| a280 | rastgele | fast_k10_or3 | 30 | -0.96 | [-2.18; +0.26] | 4.72 | 0.0044 | hayır |
| a280 | rastgele | fast_k10_2o | 30 | -0.40 | [-1.81; +1.02] | 4.72 | 0.0044 | evet |
| a280 | rastgele | fast_k20_or3 | 30 | -2.51 | [-3.63; -1.40] | 4.72 | 0.0044 | hayır |
| a280 | kick’lenmiş yerel opt. | fast_k10_or3 | 10 | +1.91 | [+0.11; +3.71] | 1.87 | 0.0019 | hayır |
| a280 | kick’lenmiş yerel opt. | fast_k10_2o | 10 | +2.49 | [+0.63; +4.35] | 1.87 | 0.0019 | hayır |
| a280 | kick’lenmiş yerel opt. | fast_k20_or3 | 10 | -0.04 | [-1.16; +1.08] | 1.87 | 0.0019 | evet |
| pr1002 | kick’lenmiş yerel opt. | fast_k10_or3 | 3 | +4.20 | [-2.34; +10.73] | 203.02 | 0.0055 | hayır |
| pr1002 | kick’lenmiş yerel opt. | fast_k10_2o | 3 | +5.32 | [+0.23; +10.40] | 203.02 | 0.0055 | hayır |
| pr1002 | kick’lenmiş yerel opt. | fast_k20_or3 | 3 | -0.24 | [-2.43; +1.94] | 203.02 | 0.0055 | evet |
| pr439 | rastgele | fast_k10_or3 | 5 | +0.34 | [-3.90; +4.58] | 39.48 | 0.0101 | evet |
| pr439 | rastgele | fast_k10_2o | 5 | +0.95 | [-2.72; +4.63] | 39.48 | 0.0101 | hayır |
| pr439 | rastgele | fast_k20_or3 | 5 | -1.03 | [-4.08; +2.02] | 39.48 | 0.0101 | hayır |
| pr439 | kick’lenmiş yerel opt. | fast_k10_or3 | 3 | +1.76 | [-8.11; +11.64] | 11.43 | 0.0033 | hayır |
| pr439 | kick’lenmiş yerel opt. | fast_k10_2o | 3 | +1.79 | [-8.01; +11.60] | 11.43 | 0.0033 | hayır |
| pr439 | kick’lenmiş yerel opt. | fast_k20_or3 | 3 | +1.01 | [-6.40; +8.43] | 11.43 | 0.0033 | hayır |

| Örnek | Repo kick/s | ILS-fast kick/s | Hızlanma | ≥50× | Repo ölçüm kaynağı | Fast ölçüm kaynağı |
|---|---|---|---|---|---|---|
| a280 | 0.5293 | 12531 | 23,672× | evet | kick loop from repo local optimum, 3 starts x ~20 s | ILS-fast 3 starts x 5 s |
| pr439 | 0.1358 | 13623 | 100,330× | evet | kick loop from repo local optimum, 3 starts x ~20 s | ILS-fast 3 starts x 5 s |
| pr1002 | 0.004926 | 8308 | 1,686,600× | evet | 3 repo LS calls on kicked tours (1/mean time) | main benchmark ILS-fast, 5 runs x 30 s |

**Karar:**
- **Hız ölçütü SAĞLANDI.** Fark 4–6 büyüklük mertebesi.
- **Kalite ölçütü (±%0,5) K=10 ile SAĞLANMADI.**
  - Rastgele başlangıçlarda fast LS deponunkinden kötü değil (a280'de daha iyi; GA üst sınırı +0,26 < 0,5).
  - ILS'in asıl çalışma noktası olan kick'lenmiş yerel optimumlardan ise deponun tam komşuluklu 2-opt'u, K=10 aday listesinin göremediği iyileştirmeleri buluyor (a280 +%1,91, GA sıfırı dışlıyor).
  - K=20 + or3 bu farkı nokta tahmini olarak kapatıyor (a280 −%0,04, pr1002 −%0,24). GA'lar geniş olduğu için ±%0,5 içinde olduğu kanıtlanmış değil.
- **ILS düzeyinde sonuç:** Hız farkı LS başına kalite kaybını fazlasıyla telafi ediyor (§5: a280'de ILS-fast 5/5 optimum, repo-ILS 0/5).
- **Planın D1 kuralına göre:** Hız kazancı küçük olmadığı için "LKH'yi LS motoru yapma" seçeneğine gerek yok.
- **Öneri:** G0 öncesinde K=16–20 ILS düzeyinde denenmeli.

## 5. Ana kıyas ([make_tasks.py]({{artifact:58c92dab-40ef-48f5-a55d-280bf582abd4}}), [bench_runner.py]({{artifact:995373fe-80d2-47aa-9d8d-517a7ce31c0f}}), [analysis.py]({{artifact:239010f8-1c31-44d9-ac45-7bd6ab0fcde0}}); ham [main_raw.csv]({{artifact:155f0a4e-4d3a-4b54-9f21-64796e20d586}}), özet [main_summary.csv]({{artifact:e5c482aa-1883-4063-a2a5-d7bb47f55a66}}), istatistik [main_wilcoxon.csv]({{artifact:4cecb171-fd97-48f7-844e-e081ffaaa7bd}}))

10 örnek × 5 tohum (0–4) × 30 s duvar saati. ILS-fast ve repo-ILS rastgele başlangıçtan başlıyor. LKH = `bench_common.lkh` (elkai, runs=10, süre sınırı yok). elkai tohum almadığı için LKH belirlenimci: 5 "tohum", aynı koşunun tekrarı.

| Örnek | ILS-fast açık % | ILS-fast opt | ILS-fast kick | Repo-ILS açık % | Repo-ILS opt | Repo-ILS iter | Repo-ILS süre s | LKH açık % | LKH opt | LKH süre s |
|---|---|---|---|---|---|---|---|---|---|---|
| rd100 | 0.000 | 5/5 | 401491 | 0.000 | 5/5 | 370.2 | 30.0 | 0.000 | 5/5 | 0.8 |
| eil101 | 0.000 | 5/5 | 448166 | 0.509 | 1/5 | 448.8 | 30.1 | 0.000 | 5/5 | 0.3 |
| lin105 | 0.000 | 5/5 | 400864 | 0.000 | 5/5 | 366.6 | 30.1 | 0.000 | 5/5 | 0.2 |
| pr136 | 0.000 | 5/5 | 375005 | 0.128 | 3/5 | 190.4 | 30.0 | 0.000 | 5/5 | 5.0 |
| pr152 | 0.000 | 5/5 | 396648 | 0.239 | 1/5 | 90.2 | 30.2 | 0.000 | 5/5 | 6.9 |
| a280 | 0.000 | 5/5 | 420971 | 4.482 | 0/5 | 18.6 | 30.9 | 0.000 | 5/5 | 13.6 |
| lin318 | 0.163 | 2/5 | 300101 | 3.277 | 0/5 | 9.0 | 31.7 | 0.000 | 5/5 | 22.1 |
| pr439 | 0.016 | 3/5 | 305790 | 7.553 | 0/5 | 0.6 | 37.8 | 0.000 | 5/5 | 51.8 |
| rat783 | 0.120 | 1/5 | 297814 | – | koşulmadı | – | – | 0.000 | 5/5 | 65.3 |
| pr1002 | 0.277 | 0/5 | 247101 | – | koşulmadı | – | – | 0.000 | 5/5 | 43.8 |
| **Toplam** | 0.0576 | 36/50 | | 2.0235 | 15/40 | | 31.4 | 0.0000 | 50/50 | 21.0 |

Eşleştirilmiş Wilcoxon işaretli sıra testi, (örnek, tohum) çiftleri üzerinde yapıldı: iki taraflı, sıfır farklar düşürüldü, 2 test için Holm düzeltmesi uygulandı. Örnek bazında 5 tohumla ulaşılabilecek en küçük p 0,0625 olduğundan örnek bazında yalnız K/B/K veriliyor (CSV'de).

| Karşılaştırma | Çift | Sıfır olmayan | Kazanç/Beraberlik/Kayıp (ILS-fast) | Ort. fark (açık %) | W | p | p (Holm) |
|---|---|---|---|---|---|---|---|
| ils_fast vs repo_ils | 40 | 25 | 25/15/0 | -2.0011 | 0 | 1.22e-05 | 2.45e-05 |
| ils_fast vs lkh | 50 | 14 | 0/36/14 | +0.0576 | 0 | 0.000967 | 0.000967 |

Yorum:
- ILS-fast deponun ILS'inden anlamlı biçimde iyi; hiçbir eşleştirmede kaybetmiyor.
- Repo-ILS a280'de 30 s'de ortalama 18,6, pr439'da 0,6 iterasyon yapabildi. pr439'da 30 s, çoğu koşuda rastgele başlangıçtan ilk LS'i bitirmeye bile yetmiyor (ortalama süre 37,8 s, en çok 44,8 s).
- LKH, ILS-fast'tan anlamlı biçimde iyi. ILS-fast'ın kaybettiği 14 çiftin tümü n≥318 örneklerde. LKH'nin süresi n≥439'da 30 s'yi aşıyor (43,8–65,3 s); bu nedenle kıyas eşit süreli değil, LKH lehine.

ILS-fast telemetrisi ([main_ils_fast_telemetry.csv]({{artifact:32b7f2cb-708c-4a0a-a587-825926b19d43}})):

| Örnek | kick (ort.) | kick/s | iyileşen kick oranı | kabul oranı | yeni en iyi (ort.) | en iyiye ulaşma s | başlangıç LS s |
|---|---|---|---|---|---|---|---|
| rd100 | 401490 | 13380 | 0.00001 | 0.760 | 4.4 | 0.02 | 0.004 |
| eil101 | 448170 | 14936 | 0.00001 | 0.776 | 6.6 | 0.07 | 0.004 |
| lin105 | 400860 | 13361 | 0.00001 | 0.895 | 2.2 | 0.01 | 0.003 |
| pr136 | 375000 | 12498 | 0.00002 | 0.753 | 8.4 | 0.02 | 0.005 |
| pr152 | 396650 | 13224 | 0.00002 | 0.851 | 6.8 | 0.12 | 0.008 |
| a280 | 420970 | 14040 | 0.00003 | 0.850 | 11.2 | 1.00 | 0.028 |
| lin318 | 300100 | 10008 | 0.00007 | 0.816 | 20.6 | 4.12 | 0.026 |
| pr439 | 305790 | 10209 | 0.00012 | 0.844 | 36.2 | 11.01 | 0.057 |
| rat783 | 297810 | 9964 | 0.00019 | 0.822 | 56.2 | 14.95 | 0.138 |
| pr1002 | 247100 | 8308 | 0.00047 | 0.786 | 102.6 | 13.74 | 0.326 |

Kabul oranının yüksek (0,75–0,90), iyileşen kick oranının çok düşük (≤5·10⁻⁴) olması, yerel kick'lerin LS tarafından çoğunlukla aynı ya da eş maliyetli yerel optimuma onarıldığını gösteriyor. Büyük örneklerde en iyiye ulaşma süresi 11–15 s; bu, 30 s içinde durağanlaşma demek. Kötü değilse kabul kuralı ve küçük kick'ler bu durağanlığın olası nedeni.

## 6. ATSP: ft53 ([atsp_raw.csv]({{artifact:f235e237-5ca6-4ed8-82f7-e98055902c85}}), [atsp_summary.csv]({{artifact:938db332-7cf6-489f-9734-e197d0c6beef}}))

ILS-fast yalnız yönlü hamleleri kullandı: Or-opt ve or-3opt, ters çevirme sayacı 0. 10 tohum × 10 s koşuldu. LKH için elkai'nin `DistanceMatrix.solve_tsp` kaynak kodu okundu: matris simetrik değilse LKH'ye `TYPE : ATSP` yazıyor, yani asimetrik destek doğal (dönüşümü LKH kendi içinde yapıyor). Bu davranış denemeyle doğrulandı (3 tekrar). Ek kontrol olarak standart 2n dönüşümü elle uygulandı: (i, j') = c(i,j)+M ve (i, i') = 0 kenarları, diğer kenarlar büyük ceza; M=8336.

| Kol | Koşu | Optimum | Ort. açık % | Ort. süre s | Ort./maks. optimuma ulaşma s | kick/s (ort.) | Ters çevirme |
|---|---|---|---|---|---|---|---|
| ils_fast | 10 | 10/10 | 0.000 | 10.009 | 0.078 / 0.185 | 6542 | 0 |
| lkh_atsp_2n | 1 | 1/1 | 0.000 | 0.362 | – / – | – | – |
| lkh_atsp_native | 3 | 3/3 | 0.000 | 0.388 | – / – | – | – |

## 7. PX-ILS / GPX ablasyonu ([gpx_raw.csv]({{artifact:8a6ac782-1cbf-47ac-ae22-fef2ba889e8a}}), [gpx_summary.csv]({{artifact:d592a154-ce2a-48c0-8a94-72be94ac4ea8}}), [gpx_wilcoxon.csv]({{artifact:7b0537c0-d1da-4d81-a4ce-50ad8af179ba}}), [gpx_telemetry.csv]({{artifact:d97ff305-901a-4263-a9af-9b7812101b12}}))

pr439, rat783, pr1002 ve pcb1173 üzerinde 5 tohum × 30 s, eşit süre. Kollar: PX-ILS GPX açık (m=8), PX-ILS GPX kapalı (aynı 8 yörünge, GPX yok) ve tek yörüngeli ILS-fast.

| Örnek | PX-ILS GPX açık: açık % (opt) | PX-ILS GPX kapalı | Tek yörünge ILS-fast |
|---|---|---|---|
| pr439 | 0.0082 (4/5) | 0.0082 (4/5) | 0.0164 (3/5) |
| rat783 | 0.0659 (1/5) | 0.0591 (2/5) | 0.1476 (1/5) |
| pr1002 | 0.3752 (0/5) | 0.2243 (0/5) | 0.2769 (0/5) |
| pcb1173 | 0.3842 (0/5) | 0.4486 (0/5) | 0.3357 (0/5) |
| **Toplam (20 koşu)** | 0.2084 (5/20) | 0.1850 (6/20) | 0.1942 (4/20) |

| Karşılaştırma | Çift | Sıfır olmayan | K/B/K (ilk kol) | Ort. fark (açık %) | W | p | p (Holm, 3 test) |
|---|---|---|---|---|---|---|---|
| px_on vs px_off | 20 | 15 | 7/5/8 | +0.0234 | 55 | 0.776 | 1 |
| px_on vs ils_fast | 20 | 15 | 7/5/8 | +0.0142 | 54 | 0.733 | 1 |
| px_off vs ils_fast | 20 | 15 | 9/5/6 | -0.0091 | 57 | 0.865 | 1 |

GPX telemetrisi (koşu başına ortalama, GPX açık kol):

| Örnek | GPX çağrısı | ≥1 uygulanabilir bileşenli çağrı | uygulanabilir bileşen (toplam) | tüm bileşenler | geçiş yapılan çağrı (çocuk < en iyi ebeveyn) | geçirilen bileşen | GPX kazancı (toplam, LS öncesi) | GPX sonrası LS kazancı | yer değiştirme | epok | son ort. bozuk-çift mesafesi (açık / kapalı) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pr439 | 1529.6 | 26.8 | 33.6 | 3050.6 | 6.8 | 8.0 | 732.4 | 2.2 | 6.8 | 192.4 | 0.064 / 0.084 |
| rat783 | 793.6 | 707.2 | 1835.4 | 5751.8 | 10.8 | 11.2 | 31.2 | 0.4 | 10.8 | 100.2 | 0.086 / 0.117 |
| pr1002 | 521.6 | 88.6 | 131.6 | 2644.8 | 23.0 | 31.0 | 2079.4 | 0.0 | 23.0 | 66.2 | 0.067 / 0.140 |
| pcb1173 | 494.4 | 399.6 | 816.6 | 3543.4 | 23.4 | 26.0 | 180.2 | 0.0 | 23.4 | 62.8 | 0.058 / 0.129 |

Yorum:
- GPX uygulanabilir bileşen buluyor (rat783 ve pcb1173'te çağrıların çoğunda). Ancak çoğu bileşende iki ebeveynin iç yol maliyeti eşit; kötü değilse kabul kuralı eş maliyetli platolarda dolaşmaya izin veriyor.
- Çocuğun en iyi ebeveynden kesin daha iyi olduğu çağrılar koşu başına 6,8–23,4 tane.
- Yer değiştirmeler havuzu daraltıyor: son ortalama bozuk-çift mesafesi GPX açıkken %24–55 daha düşük (pr439 %24, rat783 %27, pr1002 %52, pcb1173 %55).
- Üç karşılaştırmanın hiçbiri anlamlı değil (Holm p=1,0). pr1002'de GPX açık kol, kapalı koldan kötü (%0,375'e karşı %0,224).
- Planın beklentisi (n≥1000'de GPX2 kazancı) bu basit GPX ve 30 s bütçeyle **desteklenmedi**. Planın "organ kira ödemeli" kuralına göre bu biçimiyle GPX kazanç göstermiyor. Sonraki adım için öneriler: GPX2'nin füzyon adımları, klon/çeşitlilik koruyan yer değiştirme, entropi denetimi, daha büyük örnekler ve daha uzun bütçe.

## 8. Sınırlar
- **Veri:** TSPLIB örnekleri kanonik kaynaktan alındı (§1). ft53 dışındaki dosyalar depo kopyasına karşı doğrulanamadı.
- **CPU paylaşımı:** Süreye bağlı bütün ölçümler başka bir iş hattıyla paylaşılan CPU'da, 2–3 paralel süreçle alındı. kick/s değerleri tek süreçte ≈1,5–2 kat daha yüksekti (smoke testinde ≈17–22 bin/s; kıyasta 8,3–14,9 bin/s).
- **Repo-ILS:**
  - rat783 ve pr1002'de koşulmadı. Deponun 2-opt katmanı pr1002'de iyileştiren iterasyon başına ≈1,9–2,1 s sürüyor; kick'lenmiş tek bir LS 128–324 s ölçüldü. Rastgele başlangıçtan tek bir `ls_moderate` çağrısı 13 dakikada bitmedi.
  - ILS-fast–repo testi 8 örnek / 40 çift üzerinde.
  - Repo-ILS'te süre denetimi yalnız iterasyonlar arasında; lin318/pr439'da bütçe aşıldı. Bu, repo kolunun lehine bir sapma.
- **LKH:** Süre sınırı yok; LKH yalnız runs=10 ile koşuldu, eşit süreli değil.
- **İstatistik:** Birleşik Wilcoxon testinde aynı örneğin tohumları bağımsız çift sayılıyor (yalancı tekrar riski). Örnek bazında güç yok.
- **Ayar bütçesi:** Küçük (3 kıyas dışı örnek × 2 tohum). Deponun ILS'i ayarlanmadı.
- **Kapsam dışı kalanlar:** GPX yalnız simetrik; ATSP için GPX (2n) uygulanmadı. PX-ILS'te entropi denetimi ve LAHC yok. Bütçe "değerlendirme sayısı" para birimiyle (Faz 0.2) tutulmadı; yalnız duvar saati ve kick sayısı var.

## 9. Dosyalar
- Kod: [fast_ls.py]({{artifact:21a30d74-fcf7-479e-89ea-33146a8d75d4}}), [ils_fast.py]({{artifact:5defbdf9-5b9d-4e79-9717-31d67929303f}}), [px_ils.py]({{artifact:04d2e421-9d48-4994-87a9-704e0816f7e8}}), [inst.py]({{artifact:2c1acf1e-fb74-4331-97d2-fe62846cbf54}}), [test_contracts.py]({{artifact:9524d46b-54af-4177-9dfb-fda557866dca}}), [bench_runner.py]({{artifact:995373fe-80d2-47aa-9d8d-517a7ce31c0f}}), [make_tasks.py]({{artifact:58c92dab-40ef-48f5-a55d-280bf582abd4}}), [analysis.py]({{artifact:239010f8-1c31-44d9-ac45-7bd6ab0fcde0}}), [d1_experiment.py]({{artifact:92726e6c-eb4d-47f7-b00a-23278b246fa6}}), [d1_analysis.py]({{artifact:3cd6d1bd-36a1-4f00-a0b8-c28bf3991849}})
- Sonuçlar: [test_contracts_output.txt]({{artifact:5c9a8e06-242c-4ace-976f-30995b289764}}), [D1_results.csv]({{artifact:7c2c7071-6bf4-476f-94f5-279f1b597b08}}), [D1_summary.csv]({{artifact:45b9f8fe-e3e3-4407-8daa-81cd9e00c1a4}}), [main_raw.csv]({{artifact:155f0a4e-4d3a-4b54-9f21-64796e20d586}}), [main_summary.csv]({{artifact:e5c482aa-1883-4063-a2a5-d7bb47f55a66}}), [main_wilcoxon.csv]({{artifact:4cecb171-fd97-48f7-844e-e081ffaaa7bd}}), [main_ils_fast_telemetry.csv]({{artifact:32b7f2cb-708c-4a0a-a587-825926b19d43}}), [atsp_raw.csv]({{artifact:f235e237-5ca6-4ed8-82f7-e98055902c85}}), [atsp_summary.csv]({{artifact:938db332-7cf6-489f-9734-e197d0c6beef}}), [gpx_raw.csv]({{artifact:8a6ac782-1cbf-47ac-ae22-fef2ba889e8a}}), [gpx_summary.csv]({{artifact:d592a154-ce2a-48c0-8a94-72be94ac4ea8}}), [gpx_wilcoxon.csv]({{artifact:7b0537c0-d1da-4d81-a4ce-50ad8af179ba}}), [gpx_telemetry.csv]({{artifact:d97ff305-901a-4263-a9af-9b7812101b12}}), [tuning_raw.csv]({{artifact:e68538e0-9bf7-4432-a44e-87349f79d4ee}})
