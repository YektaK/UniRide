# UniRide tasarımlarının bütünsel değerlendirmesi ve akademik katkı olasılığı

Hazırlayan: **Codex**  
Tarih: **2026-10-16**  
Durum: **Mutabakat için inceleme raporu — öneriler henüz kullanıcı tarafından onaylanmadı.**

Bu belge, 2026-10-16 tarihli bütünsel incelemeyi kalıcılaştırır ve kullanıcının “özgün sayılabilecek, başarılı bir çözücüyle akademik katkı sağlayabilir miyiz?” sorusunu değerlendirir. Kaynak tasarımları, çözücü kodunu veya kabul edilmiş proje sözleşmelerini değiştirmez. Buradaki araştırma yönleri uygulama talimatı veya tamamlanmış deney değildir.

## 1. Sonuç ve karar çerçevesi

**Evet, özgün ve başarılı bir yöntem geliştirme ihtimali var. Ancak mevcut belgeler özgünlük veya performans başarısını henüz kanıtlamıyor.** Başarı olasılığı için güvenilir bir yüzde verilemez. En savunulabilir yol, genel TSP'de bütün güçlü çözücüleri geçmeyi vaat etmek yerine, yönlü ve metrik olmayan matrisler, ayrı Sw/So kapasitesi, sabit çapa zamanları ve gün içi araç yeniden kullanımı arasındaki belirli bir etkileşimi çözmektir.

Claude Science değerlendirmesinin en güçlü katkısı, küçük P5 dalgalarında alt küme dinamik programlamasını ve P7'de ortak rota seçimi/eşzamanlılık modelini öne çıkarmasıdır. ERPL'nin öğrenme sinyalini gerçek rota başarısından ayıran deneyler de değerlidir. Buna karşılık başka algoritmalardaki sonuçları GPX2/ERPL/A6 için doğrudan hükme dönüştürmek, büyük p-değerini eşitlik kanıtı saymak ve yalnız filo alt sınırıyla bütün sözlüksel optimumu ilan etmek kabul edilemez.

Üç ayrı başarı hedefi karıştırılmamalıdır:

| Hedef | Ne gerekir? | Mevcut durum |
|---|---|---|
| Kullanışlı ve doğru çözücü | Doğru sözleşme, uygulanmış yöntem, bağımsız doğrulama, uygun süre/bellek | Matematiksel olarak güçlü adaylar var; dış prototiplerin yeniden üretimi eksik |
| Akademik katkı | Açık araştırma sorusu, en yakın öncüllerden belirgin fark, uygun kanıt veya deney | Olası dar katkı alanları var; yenilik araştırması kapanmadı |
| SOTA performansı | Açık problem sınıfı ve bütçe altında güçlü güncel referanslara karşı geniş, tekrar üretilebilir sonuç | Gösterilmiş değil |

Bir çözücü yeni olmayıp çok yararlı olabilir. Yeni bir fikir de iyi çalışmayabilir. Akademik katkı, yeni isim verilen bir bileşen toplamından daha fazlasını gerektirir; teorik sonuç, yöntemsel fark, açıklanabilir deney veya iyi belgelenmiş problem/model katkısı üzerinden kurulabilir. Yayın kabulü garanti değildir.

## 2. Kapsam, kaynak anahtarı ve kanıt düzeyleri

### 2.1 Yerel kaynaklar

Aşağıdaki kısaltmalar rapor boyunca kullanılır. Satır numaraları inceleme anındaki dosyalara aittir; dosyalar değiştirilirse kayabilir.

| Kod | Dosya |
|---|---|
| B0 | [Görev ve P1–P8 sözleşmeleri](00_PROMPT_ASTRA6_YENI_ALGORITMA_TASARIMI.md) |
| A | [Özgün yedi algoritma tasarımı](ASTRA6_YENI_ALGORITMA_TASARIMLARI.md) |
| AR | [Claude Science algoritma revizyonu](ASTRA6_YENI_ALGORITMA_TASARIMLARI_ClaudeScience.md) |
| B | [Özgün ERPL tasarımı](CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14.md) |
| BR | [Claude Science ERPL revizyonu](CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14_ClaudeScience.md) |
| D | [Astra değerlendirmesi](ASTRA_DEGERLENDIRME_2026-10-15.md) |
| I | [48 maddelik bulgu listesi](astra_issues.csv) |
| E | [Öğrenilmiş örüntü deneyleri](SCIENCE_OGRENILMIS_ORUNTU_CALISMASI_2026-10-15.md) |
| L | [Makine öğrenmesi literatür sentezi](ML_ROTA_LITERATUR_2026-10-15.md) |
| K | [87 satırlık kaynakça](ml_rota_kaynakca.csv) |

01–04 ve 09–10 numaralı eski incelemeler, yeniden tasarım planı ve eski kıyas CSV'leri bağlam olarak kullanıldı. Bu rapor, o dosyalardaki bütün eski kod ve performans iddialarının yeniden denetimi değildir. E'deki üç şekil görsel olarak incelendi; kaynak hesaplarını üreten ham veri mevcut olmadığından şekil değerleri bağımsız olarak yeniden hesaplanmadı.

AR ile AR'nin _ClaudeScience1 kopyası; BR ile BR'nin _ClaudeScience1 kopyası içerik olarak aynıdır. İki ayrı sürüm veya iki bağımsız onay sayılmamalıdır.

### 2.2 Kanıt etiketleri

- **Yerel doğrulama:** Bu incelemede okunan güncel dosya/veri veya çalıştırılan sınırlı kontrol.
- **Matematiksel değerlendirme:** Açık varsayımlar altında yapılan türetim. Bir üretim uygulamasının doğruluğunu tek başına kanıtlamaz.
- **Dış ölçüm bildirimi:** Claude Science metninde raporlanan fakat burada ham kayıt/kodla yeniden üretilmeyen sonuç.
- **Araştırma hipotezi:** Denenmeye değer öneri; yenilik, başarı veya üretim onayı değildir.

D, 48 maddeyi 4 hata, 4 çelişki, 6 ölçümle çelişen, 11 ölçümle desteklenen, 4 doğrulanmamış ve 19 geliştirilebilir olarak sınıflandırıyor. CSV sayımı bu dağılımı doğruladı. **48 bulgunun tamamı hata değildir.** Etiketler yazarın sınıflandırmasıdır; Codex'in tek tek görüşü §6'dadır.

### 2.3 Eksik yeniden üretim paketi

AR:849–851 ve E:357–376, temel kanıtları başka çalışma alanındaki artefaktlara bağlıyor. Verilen klasörde ve taranan docs ağacında şu dosyalar bulunmadı: ALGORITHM_DEVELOPMENT_RESULTS_2026-10-14.md, TSP_FAST_LS_REPORT.md, wave_exact.py, run_waves.py, run_day_joint.py, run_day_typed.py ve yeni öğrenme deneylerinin ham sonuç dosyaları. Bu, dosyaların hiçbir yerde bulunmadığı iddiası değildir.

Dolayısıyla 228/228 optimum, filo 6→5, ILS-fast 36/50 optimum, 51/51 test ve AUC 0,909 gibi değerler **dış ölçüm bildirimi** olarak aktarılır. Bunları uydurma saymak için kanıt yoktur; yerel olarak doğrulanmış kabul etmek için de yeterli paket yoktur.

Önerilen durum ifadesi: “Claude Science çalışma alanında uygulandığı ve ölçüldüğü raporlandı; depo entegrasyonu ve bağımsız yeniden üretim bekleniyor.” Önceki tasarımın o tarihte çalıştırılmamış olması, sonradan başka bir prototipin çalıştırılmasıyla geriye dönük bir hata haline gelmez.

## 3. Kabul edilen ve daraltılan düzeltmeler

### F01 — Alt küme DP, P5 için daha iyi bir kesin yöntem başlangıcıdır

**Karar: kabul; özgün karmaşıklık cümlesinin anlamı daraltılmalı.** A:287'deki toplam sıralı dizi sayısı aritmetik olarak yanlıştır denemez; yanlış yönlendiren kısım bunu problemin zorunlu çözüm maliyeti gibi sunmaktır. n=20, L=9 için doğrudan hesap:

- Sıralı diziler toplamı: 66.449.027.200.
- Boş olmayan, büyüklüğü en fazla 9 olan alt kümeler: 431.909.
- Oran yaklaşık 153.850.

DP bir alt kümeyi tek işlemle çözmez; uç düğüm durumları ve geçişler de vardır. Held–Karp türü tam alt küme DP için O(n² 2^n) zaman ve O(n 2^n) bellek üst sınırları uygundur. Kapasiteye bağlı kesilmiş ve seyrek gerçeklemeler farklı maliyet gösterebilir. “Her alt küme için en kısa OLURLU sıra” saklanmalıdır; önce kısıtsız en kısa sırayı seçip yalnız onu test etmek aynı yöntem değildir. [A:281–299; AR:376–380; I/A-04]

### F02 — Geriye R budaması doğru; genel sonek olurluluğu iddiası yanlış genişliktedir

**Karar: R budaması kabul; AR:194 cümlesi düzeltilmeli.** Toplamada ilk yolcudan depoya kalan süre r ise yeni yolcuyu başa eklemek c(v,f)+r verir. Negatif olmayan yaylarda bu değer azalmaz. R aşılmışsa bu yönde daha fazla genişletmek uygun çözüm üretemez.

Ancak “olurlu rotanın her soneki olurludur” bütün kısıtlar için söylenemez. Örnek: c(D,A)=1, c(A,B)=1, c(B,D)=1, c(D,B)=10 ve T=5 olsun. D–A–B–D toplam 3 ile uygundur; D–B–D toplam 11 ile uygun değildir. R açısından sonek güvenlidir, kapalı tur T'si açısından değildir. AR zaten T'yi yalnız kolon sonunda kontrol ediyor; açıklama da bu ayrımı korumalıdır. Dropoff için transpozisyon ve ters sıra eşlemesi özgün matris üzerinde doğrulanmalıdır. [AR:191–196, 414–420]

### F03 — Kısa rota baskınlığı ve olay-noktası modeli kabul

**Karar: belirtilen P7 varsayımları altında kabul.** Aynı dalga, yolcu kümesi, tip ve uygunlukta t1≤t2 ise toplamada [a−t1,a+c) uzun aralığın; bırakmada [a,a+t1+c) uzun aralığın alt kümesidir. Daha kısa uygun rota süreyi ve kaynak meşguliyetini artırmaz. Bu nedenle aynı kapsam/tip için uzun sırayı tutmak bu amaçlar bakımından gereksizdir.

Bu sonuç farklı yolcu bölümlemelerini karşılaştırmaz. Araç-özel uygunluk, farklı depo, aktarım/deadhead, kişisel hizmet penceresi veya yeni bir amaç eklenirse baskınlık yeniden kontrol edilmelidir. Aynı tipte özdeş araçlar ve sabit aralıklarla gereken araç sayısı en büyük eşzamanlılıktır; rota seçiminden sonra aralık boyama yeterlidir. Olay başına bir kısıt vardır; O(M×olay) daha çok kaba katsayı/kurulum maliyetini anlatır, doğrudan kısıt sayısını değil. [AR:380, 437–462, 480]

### F04 — Özdeş occurrence simetrisi gerçek bir eksik; yeni formül tamamlanmamış

**Karar: kabul, uygulama tanımı eksik.** Aynı dalga/durak/tipte ve aynı bireysel kısıtlarda kimlik permütasyonları yapay çeşitlilik üretmemeli. Çokluk durumu ile sayım ve sonradan kimlik ataması yararlı olabilir.

BR:194'teki “H, (durak, tip) düzeyinde toplansın” tek başına yeterli değildir. Bir çözümde aynı sınıf çifti birkaç defa geçebilir. H'nin en az bir kez görülmeyi mi, geçiş sayısını mı, fırsat başına oranı mı tuttuğu belirlenmeli. Sınıf içi geçişler, i≠j için verilen önsel ve occurrence düzeyinde geri örnekleme açıklanmalı. Kapasite, kapsama ve kişisel sertifika kaybolmamalıdır. [AR:171, 376; BR:182–200]

### F05 — Yerel arama sonlanması ve örnekleme karmaşıklığı açıklanmalı

**Karar: temel eleştiri kabul, iki mutlak ifade daraltılmalı.** Özgün B:145 deneme sınırı bulunduğunu söylüyor; bu nedenle doğrudan “sonsuz döngü var” denemez. Bununla birlikte yerel optimuma ulaşmak ile deneme bütçesinin bitmesi farklı durumlardır. Yerine koymadan deneme, hamle sonrası komşuluğun yeniden kurulması ve eşit maliyet kabulünün döngü politikası açık olmalıdır.

“En-iyi-iyileşmede M2≡M1” ancak aynı komşuluk bütünüyle taranır ve eşitlikler aynı çözülürse geçerlidir. Bütçede yarım kalan taramada sıralama sonucu değiştirebilir.

Her adımda yeniden sıralama O(n² log n) verir. Maliyet satırları bir kez sıralanıp ziyaret edilmemiş düğümler bu sırada taranırsa, O(n² log n) ön işlem ve örnek başına O(n²) elde edilebilir. Sıra önbilgisinden vazgeçmek zorunlu değildir. Önceki O(n²) ifadem ön işlemi açıklamıyordu. [B:119–149, 357; BR:232, 461]

### F06 — Takvim, kaynak atfı ve lisans düzeltmeleri

**Karar: kabul; birbirinden farklı ağırlıktaki konulardır.** A:614–619 TSP ağırlıklı iken üretim önceliği A4→A5'tir; takvimin hedefe göre ayrılması gerekir. Yanlış R1 karmaşıklık atfı düzeltilmeli. Künye/çeviri eksikleri algoritmayı geçersiz kılmaz.

elkai kaynak kodu asimetrik matris için TYPE: ATSP üretmektedir [P2]. Elle 2n dönüşümü bu arayüzü kullanmanın ön koşulu değildir. Lisans dosyası akademik ve ticari olmayan kullanım/dağıtım sınırını açıklar [P3]. Bu kaynak incelemesi, kurulu herhangi bir elkai sürümünün deneysel davranışını yeniden ölçmek değildir.

## 4. Revizyonlarda kalan önemli sorunlar

### F07 — LB0 yalnız ilk hedefi kanıtlayabilir

**Karar: yüksek güvenli düzeltme gerekli.** LB0 araç sayısına alt sınırdır. 5 araçlı tanık ve LB0=5, araç minimumunu kanıtlar. Aynı 5 araçla 100 yerine 80 dakika mümkün olabilir. Dolayısıyla AR:456, 644 ve 682'deki genel “ortak gün optimumu” anlatımı, son hücrede ikinci/sonraki amaçların da kapandığına dair kayıt yoksa fazla geniştir.

Her hedef için ayrı durum gerekir: fleet_optimal, borrowed_minutes_optimal, total_minutes_optimal gibi anlamı açık alanlar. Bunlar önerilen anlamlardır, mevcut API alanı iddiası değildir. [AR:506–508]

### F08 — LKH'nin kesin çözücü diye adlandırılması yanlış

**Karar: düzeltme gerekli.** L:215 “ATSP'de LKH3 hem hızlı hem kesindir” diyor. LKH sezgiseldir. Bilinen optimuma eşit değer bulmak ile algoritmanın optimalite kanıtı üretmesi aynı şey değildir. MatNet makalesindeki belli örneklerde raporlanan %0,00 açık, genel optimalite garantisi sağlamaz [P4]. “Bu deneyde referans optimum değerleri buldu” gibi kapsamlı bir ifade kullanılmalıdır.

### F09 — Başka yöntemlerin sonuçları doğrudan çürütme değildir

**Karar: öncelik değişikliği makul; çürütme ve doğrulama etiketleri fazla geniş.** Basit GPX, GPX2 değildir; GPX2'nin farklı rekombinasyon bileşenleri bulması makalenin temel özelliğidir [P1]. Elit birleşimini aday listesi yapmak ERPL dağılımından yeni tur örneklemek değildir. ESN-SP'nin başarısızlığı A6'yı; GA kolonlarının katkısı A3'ün bütün HGS mekanizmalarını sınamaz.

“Deneysel önceliği düşürüldü / ilgili bir prototipte katkı gösterilemedi” kabul edilebilir. “GPX2 katkısız”, “ERPL çalışmıyor” veya “A6 hipotezi çürütüldü” kabul edilemez. E:343 ve 355 ile BR:391 bu sınırı doğru açıklıyor; özetler de aynı dikkatle yazılmalı.

### F10 — Küçük P5'te deney bilgi üretebilir

**Karar: B-01'in öncelik önerisi kabul; gerekçesindeki mutlak sonuç reddediliyor.** Optimumdan daha iyi değer bulunamaz. Fakat M0 ve M1 optimuma aynı sıklıkta veya sürede ulaşmayabilir. Öğrenmenin etkisi; optimuma erişme olasılığı, gereken değerlendirme sayısı, uçtan uca süre ve doğruluk üzerinden incelenebilir. WAVE-EXACT ucuzsa üretimde yerini almak cazip olmayabilir; bu, kontrollü küçük deneyin değersiz olduğunu göstermez. [D:45, 160; BR:66]

### F11 — P5'ten P8'e yalnız hedef adı değiştirilerek geçilemez

**Karar: sözleşme boşluğu var.** S3 büyük bir sentetik P5 ailesidir. P8 ise eşlenik pickup–delivery, zaman pencereleri ve farklı hizmet kuralları içeren ayrı problemdir. Yolcu sayısı 25'i aşınca P8 olunmaz. BR:170, 391–402 ve 504'te hedef taşınmış; fakat örnekleme/Split akışı P5 mantığında kalmıştır. P8 için temsil, talep çifti korunumu, decoder/repair ve çizelge denetleyicisi ayrıca tanımlanmalıdır. [B0:154–158; E:330–333, 353]

### F12 — Kesin yöntem için evrensel boyut eşiği yok

**Karar: ölçüm kapsamı daraltılmalı.** n≈22–25 belirli prototip/donanım/veri için pratik gözlem olabilir. Kapasiteler, olurlu alt küme sayısı, tekrar eden duraklar, bellek temsili ve master zorluğu sonucu değiştirir. “n>25'te uygulanamaz” genel hükmü yerine süre/bellek limitleri ve eksiksizlik durumu kullanılmalıdır. [AR:379, 643, 788]

### F13 — Ağırlıklı geri dönüşün sözlüksel eşdeğerliği ayrıca ispatlanmalı

**Karar: eksik uygulama sözleşmesi.** İki aşamalı çözüm kapanmadığında M×rota+toplam_süre biçimine dönmek ancak M ikinci hedefin bütün olası değişimini baskılarsa aynı amacı verir. Birim/ölçek, araç tipi ve örnek büyüklüğü bu sınırı etkiler. Önceki aşamanın kanıtı yokken rastgele bir rota sayısını sabitlemek optimum kanıtı değildir. Fallback aynı toplam deadline içinde çalışmalı ve her aşamanın status/bound bilgisi saklanmalıdır. [AR:386, 391, 418–421]

### F14 — Kesin yöntem ve deterministik/bütçesiz yöntem aynı şey değildir

**Karar: ifadeler daraltılmalı.** Kesin algoritma zaman aşımına uğrayabilir. Kanıtlanmış optimum değer deterministiktir; döndürülen eşdeğer sıra, süre, kanıtı kapatma ve timeout tanığı her yürütmede aynı olmak zorunda değildir. “Bütçe yalnız süre raporudur” ifadesi, ancak tüm ilgili aşamalar gerçekten kapanmış sonuçları anlatırken kullanılabilir. [AR:368, 378; aynı dosyanın timeout örnekleri:386]

## 5. Deneyler, öğrenme ve literatür yorumları

### F15 — 228 ve 36 bağımsız saha örneği değildir

**Karar: yerel veriden doğrulandı.** docs/paper/results/week-2026-10-05-4sw5so altındaki 20 response JSON'unda 228 job hücresi ve 57 benzersiz job kimliği var. R∈{50,60,70,90} için aynı temel dalgalar tekrar çözülmüş. En az 6 yolculu 36 hücre, 9 benzersiz temel dalgadır. İncelenen bütün matrix JSON'ları aynı matris SHA'sını taşıyor: bfb2dd85087c1d5a4310ad23644f3b2ea53886db5c03dd5bf536912eb2dd31e5.

Günlük dosyalar farklı yay alt kümeleri içerir; dosya baytlarının aynı olduğu söylenmiyor. Ortak yayların sürelerinde uyuşmazlık bulunmadı. 228/228, kapsamı tanımlı deney hücresi başarısı olabilir; 228 bağımsız yeni talep örneği değildir. 36 hücreyi bağımsız örnek gibi kullanmak da uygun değildir. [E:118–125; L:213; AR:656]

### F16 — Anlamsız p-değeri eşitlik kanıtı değildir

**Karar: düzeltme gerekli.** p=0,95 veya p=0,78 “fark gösterilemedi” sonucunu destekler; “fark yok” veya “katkı sıfır” sonucunu değil. Eşdeğerlik/kötü-olmama için önceden belirlenmiş pratik marj ve buna uygun belirsizlik analizi gerekir [P5]. Düşük güç ve küçük örnek kümesi özellikle önemlidir.

E:311'de 4 TSP örneği × 5 tohum = 20 eşleşik koşu kullanılıyor. Bu, 20 bağımsız problem değildir. AR:705 aynı sorunu CS2 için kabul ediyor. Mevcut instance temelli analiz kuralıyla uyumlu yeniden analiz veya hiyerarşik bağımlılığı açık modelleyen önceden ilan edilmiş yöntem gerekir. Bu rapor ham kayıtlar olmadan p-değerlerini yeniden üretmedi. [E:10, 15, 291, 311; BR:90, 383]

### F17 — Gerçekleşen hesaplama maliyetleri eşit değil

**Karar: yerel tablodan doğrulandı; nedensel/üstünlük yorumu yapılamaz.** E:288'de aynı örnek için mesafe kolu 43,8 s, öğrenilmiş kol 299,3 s kullanmış. E:271 bütçe kontrolünün birleşimler arasında olduğunu; E:353 paralel yük bulunduğunu açıklıyor. Bu dürüst açıklamalar korunmalı, fakat “aynı bütçe verildi” ile “eşit maliyette karşılaştırıldı” ayrılmalıdır.

E6'da komşuluk ve birleşim sırası birlikte değişiyor (E:267–269). Olası kazancı bunlardan tek birine bağlamak mümkün değil. İki faktörün ayrı ve birlikte etkileri için uygun ablasyon gerekir. Ön eğitim, etiket üretimi ve model çıkarımı da gizlenmemeli. Süre sonuçları native olarak kalır; sabit FE sonuçlarıyla havuzlanmaz.

### F18 — LODO uygun başlangıç; güçlü genelleme kanıtı değil

**Karar: yöntem yönü olumlu, kapsam dar.** Gün dışarıda bırakma, satır bazlı rastgele bölmeden daha uygundur. İleriye zincirleme testin ayrıca raporlanması da değerlidir. Buna rağmen tek hafta, aynı temel matris ve büyük ölçüde tanıdık duraklar üzerinde yeni talep bileşimleri sınanmıştır. Yeni hafta, yeni ağ, yeni trafik matrisi veya gerçek P8 aktarımı gösterilmemiştir.

Model/özellik/hiperparametre seçiminin test katlarına bakılarak yapılıp yapılmadığı, ileriye zincirleme frekans özelliklerinin nasıl üretildiği ve eğitim maliyeti ham kodla kontrol edilmelidir. İç içe LODO yapıldığı bildirimi, bütün olası sızıntı yollarının kapandığını tek başına kanıtlamaz. [E:118–150, 350–355; BR:363]

### F19 — Tahmin başarısı ile rota başarısı ayrılmalı

**Karar: çalışmanın en değerli gözlemlerinden biri.** E:139–164'te GBM-geo ardıl AUC'si 0,909 iken MUTUAL-RANK 0,855. Buna karşılık recall@5 MUTUAL-RANK için 0,956, GBM-geo için 0,944. E:190 ve 194'te yeniden sıralamalı klasik savings 3 fazla rota/181 fazla dakika, öğrenilmiş GBM savings 9 fazla rota/419 fazla dakika veriyor. Sayılar dış deneyin tablosudur; burada yeniden üretilmedi.

Bu tabloya göre AUC iyileşmesi tek başına algoritmik katkı değildir. Son karar ölçütleri gerçek amaç tuple'ı, optimuma erişme oranı, süre, kullanılan bütçe ve kanıtı kapatma süresi olmalı. Öğrenilmiş sıcak başlangıç önerisi, klasik savings, mevcut tanık ve doğrudan önceki çözüm kontrollerini geçmeden varsayılan yapılmamalıdır. [E:325–338]

### F20 — Öğrenilmiş eleme, kanıtlı güvenli eleme değildir

**Karar: güvenlik ayrımı kabul.** GBM-geo k=4 satırında 36 hücrenin 30'unda optimum korunduğu, diğerlerinde süre kaybı olduğu raporlanıyor. Bütün uygun adayları korumayan öğrenilmiş filtre, yalnız sınıflandırma başarısı nedeniyle kesin sayılmaz. Ancak “kesin modda hiç eleme olamaz” da gereksiz geniştir: matematiksel olarak güvenli baskınlık, kaynak alt sınırı veya diğer kanıtlı eleme mümkündür. Yasaklanması gereken, yalnız öğrenilmiş skora dayanan kanıtsız elemedir.

Kısıtlı havuzda optimal durum elde etmek bütün problem için optimalite vermez. Kısıtlı havuzun olursuzluğu da genel olursuzluk değildir. Sonradan tam aramaya dönülürse kesinlik ancak gereken eksiksizlik ve kanıt koşulları gerçekten tamamlandığında geri gelir. [E:206–263; AR:433]

### F21 — LAP'deki plan kararlılığı garantisi ve tek-sıra sıkıştırması

**Karar: yeni katkı fikri makul, mevcut garanti geçersiz.** Σ log p enbüyüklemek modelin sık gördüğü örüntülere yakınlığı artırmayı hedefler. Dünkü gerçek plandan minimum değişiklik yaptığını garanti etmez. Etiketler mevcut raporda insan planlarından değil, tek bir matematiksel optimumdan üretilmiştir; gizli operasyonel tercihlerin öğrenildiği sonucu çıkarılamaz.

Kararlılık için değişen yolcu–araç eşleşmesi, rota kenarı, sürücü veya servis saati gibi açık bir ölçüt ve ortak yolcu kümesi üzerinde karşılaştırma gerekir. Doğrudan önceki plana uzaklık, öğrenmesiz güçlü kontrol olmalıdır.

A4'ün her (alt küme, tip) için tek en kısa sıra saklaması, eşit süreli başka sıraları atabilir. Sonradan eklenen benzerlik hedefinin global optimumunu aramak için DP'de uygun eşitlik çözümü veya gerekli alternatif sıralar korunmalıdır. Yeni hedef eklendiğinde eski baskınlık kuralı otomatik olarak yeterli kalmaz. [AR:376–380; E:320, 329; BR:385]

### F22 — Literatür doğrulama düzeyi ve genellemeler

**Karar: kaynak haritası yararlı; bütün içerik iddiaları doğrulanmış değil.** K CSV'sinde 87 kaynak satırı sayıldı. L:21 ve E:35–39 yalnız 7 tam metin, 59 yayımlanmış özet, 10 TLDR ve 11 özeti okunamamış kayıt bildiriyor. DOI'nin çözülmesi künye eşleşmesini destekler; makaleye bağlanan performans, teori veya yöntem iddiasını tek başına doğrulamaz.

L:209'daki “öğrenme LKH'yi ya LKH'nin içinde çalışarak geçiyor ya da hiç geçmiyor” gibi geniş ifadeler incelenen problem/deneylerle sınırlandırılmalı. Aynı dosya CVRP'de başka öğrenmeli yöntemlerin LKH3'ü kalite bakımından geçtiğini zaten anlatıyor (L:74); hesap maliyeti ve güçlü CVRP referansları ayrıca tartışılmalı.

L:183'te öncelik modellemek için Mallows/Plackett–Luce “gerekir” denmesi de fazla dar: ikili öncelik sınıflandırıcısı mümkündür; E:172–175 bunun bir örneğini raporlar. Bu iki model ailesi seçeneklerdir, zorunluluk değildir.

### F23 — Eski kapsam kararı ile yeni kullanıcı talebi birbirine aykırı sayılmamalı

**Karar: B-08/B-09 entegrasyon açıklığı gerektirir; doğrudan mantıksal hata değil.** A'da D6 ilk sürümden öğrenilmiş adayları çıkarmıştır. B ise kullanıcının daha sonra ayrıca istediği bağımsız öğrenme çalışmasıdır. Böyle bir araştırma açılması kendi başına önceki planın ihlali değildir. Üretim önceliği, araştırma dalı ve kabul kapıları açık ayrılırsa iki belge birlikte tutarlıdır. BR:339'daki uzlaştırma notu bu açıdan yararlıdır.

### F24 — Güncel Split kontrolünün sınırı

**Karar: T/R erken kesmesi hakkındaki olumlu sonuç güncel kodla destekleniyor.** İncelenen uniride_core/algorithms/string_split_decoder.py içinde _build_trips:358–366 T/R ihlallerinde continue kullanıyor. Pickup-TW bölümünde de 449–458 aynı davranış var.

BR:313'ün _build_trips için “eksik yayda break” ifadesi güncel kodun o bölümünü tam anlatmıyor: açık eksik-yay break'i TW bölümünde 430–432'de var. T/R güvenliği sonucu değişmiyor. Bu tek dosyanın kontrolü, bütün decoder amaç uyumunun, bütçe muhasebesinin veya bütün üretim yollarının doğrulandığı anlamına gelmez.

## 6. Dış değerlendirmedeki 48 madde için karşılık

Bu tablo **Codex'in görüşüdür**; kullanıcı mutabakatı değildir. “Kanıt bekliyor” matematiksel yöntemi reddetmek anlamına gelmez. Kaynak: I dosyasında kimlik sütunu; ilgili ayrıntılar yukarıdaki F maddelerinde.

| Dış ID | Codex değerlendirmesi | Gerekçe / kapanma koşulu |
|---|---|---|
| A-01 | Kısmi kabul | ILS'i öncelemek makul; GPX sonucu GPX2'yi çürütmez. F09, F16 |
| A-02 | Koşullu | K=10/20 ölçümü ham kayıtla doğrulanmalı; sabit evrensel K kararı değil |
| A-03 | Yön kabul, kanıt bekliyor | Küçük kesin referans doğru; 228 optimum paketi gerekli |
| A-04 | Kabul, anlamı daralt | Naif sıra sayısı doğru; daha iyi DP yaklaşımı eksikti. F01 |
| A-05 | Kabul | Geriye R budaması; bütün kısıtlara sonek garantisi verilmez. F02 |
| A-06 | Kabul, koşullu | Aynı kapsam/tip/sabit çapa altında kısa sıra baskın. F03/F21 |
| A-07 | Koşullu kabul | Küçük ölçek için exact önceliği; timeout/tanık ve bütçe gereksinimleri sürer |
| A-08 | İlke kabul | Lex kanıt ayrımı doğru; performans sayılarını yeniden üretmek gerekir |
| A-09 | İlke kabul | Havuz olursuzluğu global değildir; bildirilen 3 hücre ayrıca doğrulanmalı |
| A-10 | Kanıt bekliyor | Filo iyileşmesi mümkün; 6→5 sonuçları dış bildirim |
| A-11 | Durum güncellemesi koşullu | Sonraki dış prototip eski planı hata yapmaz; LB0 tüm tuple'ı kanıtlamaz |
| A-12 | Kabul, koşullu | Özdeş araç/sabit aralık için olay modeli. Kısıt/katsayı sayısını ayır |
| A-13 | Koşullu kabul | Eksiksiz havuz çözülebiliyorsa exact önce; LNS ölçek seçeneği |
| A-14 | Kabul, dar kapsam | LB0 yararlı; yalnız kapsadığı filo hedefini kanıtlar. F07 |
| A-15 | İlke kabul | Filo/rota amaç çatışması gerçek model meselesi; sayılar dış bildirim |
| A-16 | Kabul | Üretim önceliği ile takvim uyuşmalı. F06 |
| A-17 | Kabul | elkai ATSP girdisi kaynak koddan doğrulandı; deney sürümü ayrıca sabitlenmeli |
| A-18 | Kanıt bekliyor | ft53 10/10 geniş ATSP başarısı değildir |
| A-19 | Kabul | Resmi elkai lisans metninin sınırı doğrulandı |
| A-20 | Kabul | Yanlış belge atfı; algoritmik hata değil |
| A-21 | Kısmi kabul | Yerleşik DARP yöntemleriyle parity yararlı; BF matematiksel olarak yanlış değil |
| A-22 | Kısmi kabul | A6 ≠ ESN-SP; büyük P5 profili küçük P5 exact sonucu ile geçersizleşmez |
| A-23 | Kabul, tasarım dikkatli | Boyuta göre tabakalama; 36 hücre 9 temel dalga, seçim önceden belirlenmeli |
| A-24 | Öncelik kararı olarak kabul | A7 koşullu tutulur; GPX başarısızlığı tek başına bağlamsal seçimi çürütmez |
| A-25 | Bibliyografik takip | D'de bildirilen GECCO kaydı; bu turda tam makale yeniden denetlenmedi |
| A-26 | Kabul | Instance/seed bağımlılığı düzeltilmeli; doğru kural kusur sayılmaz |
| A-27 | Öncelik kararı olarak kabul | Küçük P5 exact önce; A3 başarısı henüz ölçülmüş değil |
| A-28 | Kabul, koşullu | Eşdeğer kaynak/kısıt altında çokluk simetrisi; kimlik sertifikası korunur |
| A-29 | İlke kabul | Kısıtlı adayda tükenme bütün komşulukta yerel optimum değildir |
| A-30 | Bibliyografik takip | DOI eklemek içerik doğrulaması yerine geçmez |
| A-31 | Kanıt bekliyor | Dış prototip elde edilmeden entegrasyon eforu güvenle azaltılamaz |
| A-32 | Kabul | FE ve native ayrımı korunmalı |
| B-01 | Kısmi kabul | Küçük P5 üretim önceliği zayıf olabilir; deney değersiz değildir. F10 |
| B-02 | Kısmi kabul | 9 yolculuk sıra için exact güçlü kontrol; öğrenmenin hiçbir faydası olamaz denmez |
| B-03 | Kabul, koşullu | Sonlanma açık olmalı; tam tarama/bütçe ve tie durumlarını ayır. F05 |
| B-04 | Kısmi kabul | Naif yeniden sıralama O(n² log n); ön işlemli örnekleme O(n²) mümkün |
| B-05 | Kabul, tanım eksik | Simetri gerekli; sınıf düzeyi H yeniden tanımlanmalı. F04 |
| B-06 | Kabul | Backbone/tour-merging öncülleri yenilik karşılaştırmasına eklenmeli |
| B-07 | Kabul | Tek hafta güçlü genelleme/NN yatırımı için sınırlı dayanak |
| B-08 | Çelişki etiketi daraltılmalı | Sonraki bağımsız kullanıcı araştırması D6'yı otomatik ihlal etmez |
| B-09 | Entegrasyon önerisi kabul | Üretim ve araştırma sırası açıklanmalı; başlı başına mantık hatası değil |
| B-10 | Çekirdek sonuç doğrulandı | T/R continue güncel kodda var; eksik-yay break ayrıntısı F24 |
| B-11 | Bibliyografik düzeltme kabul | Özgün/çeviri başlık açık verilmeli; matematiksel hata değil |
| B-12 | Düşük öncelikli kabul | Kaynak/“ders” kod adlarının karışması önlenebilir |
| B-13 | Deney önerisi | Kes skoru test edilmedi; olasılık ve Split etkileşimi tanımlanmalı |
| B-14 | İlgili ama dolaylı kanıt | GA kolon katkısı ERPL örneklemesinin katkısı değildir |
| B-15 | Kabul | Dalga etiketi gün amacıyla aynı değil; ölçüm sonuçları dış bildirim |
| S-01 | Kabul | Nonmetric matriste kör erken kesme geçersiz; F02 güvenli istisnayı açıklar |

Bu tablo kaynak makalelerin tümünü doğrulanmış ilan etmez. D'deki künye taraması ile bu raporun odaklı birincil kaynak kontrolü farklı kapsamlardır.

## 7. Özgün ve başarılı bir algoritma geliştirme ihtimali

### 7.1 Evet; fakat hangi özgünlük?

**Benim araştırma değerlendirmem: bu çalışmayı sürdürmek için yeterli gerekçe var. Mevcut paket için “özgün algoritma bulundu” veya “SOTA olacak” sonucuna varmak için yeterli kanıt yok.** Bu bir olasılık tahmin modeli değil, eldeki sözleşmeler ve yakın öncüller üzerinden verilen öncelik kararıdır.

En güçlü başlangıç avantajımız yeni bir meta-sezgisel adı değil; gerçek bir uygulama problemi, açık kısıtlar, doğrulanabilir küçük örnekler ve gün düzeyinde ölçülebilen bir amaçtır. En büyük riskimiz ise bir haftaya ve dolaylı kıyaslara dayanarak genel sonuç çıkarmak; bilinen bileşenlerin birleşimini özgün mekanizma sanmaktır.

### 7.2 Yakın literatür: hangi fikir zaten var?

Bu tablo odaklı bir öncül taramasıdır. Alanın 2026 tarihli bütün yayınlarını kapsayan sistematik yenilik/SOTA taraması değildir. Özellikle “ilk kez” iddiası için ileri/geri atıf takibi ve daha yakın problem varyantlarının tam metin incelemesi gerekir.

| Mevcut fikir | Doğrulanmış yakın öncül | Bizim için anlamı |
|---|---|---|
| Alt küme ve son/ilk düğüm üzerinden DP | Held ve Karp (1962), sıralama problemleri için dinamik programlama [P6] | Sıralamaları DP ile sıkıştırmak başlı başına yeni değildir. Katkı, doğru ve daha güçlü bir durum/baskınlık/alt sınır mekanizmasında aranmalı |
| Çok seferli araç kullanımı için rota/çizelge seçimi | Mingozzi, Roberti ve Toth (2013), rota ve çizelge tabanlı küme bölümleme benzeri formülasyonlar ve kesin çözüm [P7] | A5'in ortak gün seçimi mimarisi tek başına yenilik göstermez; UniRide'a özgü kısıt etkileşimi ve çözüm yöntemi karşılaştırılmalı |
| İyi çözümlerdeki kenar sıklığından örnekleme ve yerel arama | Tsutsui, Pelikan ve Ghosh (2006), kenar histogramıyla örnekleme + 2-opt/Lin–Kernighan [P8] | ERPL'nin genel öğren-örnekle-iyileştir döngüsünün güçlü bir öncülü var |
| Büyük turun uygun rotalara ayrılması | Prins, Labadi ve Reghioui (2009), tour splitting algoritmaları [P9] | Giant-tour + Split bir yenilik iddiasının kendisi olamaz |
| Geçmiş başarıya göre operatör ağırlığı | Ropke ve Pisinger (2006), ALNS [P10] | Başarılı operatöre daha fazla ağırlık verme bilinen mekanizmadır |
| Arama durumuna göre öğrenilmiş operatör/parametre seçimi | Reijnen vd. (2024), DR-ALNS [P11] | A7'de yalnız “bağlama göre seçiyoruz” demek özgünlük için yetersiz |
| Üretilen kolonlardan umut verenleri öğrenerek seçme | Morabit, Desaulniers ve Lodi (2021) [P12] | Öğrenilmiş rota/kolon seçimi zaten araştırılmıştır; hedef, etiket ve gün düzeyindeki fark gösterilmeli |
| Öğrenmeyle pricing ağını küçültme, gerektiğinde tam ağa dönme | Morabit, Desaulniers ve Lodi, 2022 ön baskısı; dergi sürümü [P13] | Güvenli geri dönüş fikri de yeni değil. Kaynak doğrusal gevşetme bağlamını açıkça kullanır; tam ağa dönüş otomatik tamsayılı optimum sertifikası değildir |

Bu öncüller araştırmayı değersizleştirmez. Hakemin soracağı soruyu netleştirir: **“Sizin mekanizmanız bunlardan hangi somut noktada farklı ve bu fark neyi mümkün kılıyor?”**

### 7.3 Öncelikli yön: P5'e özgü kanıtlanabilir azaltma, ardından gün düzeyi seçim

**Önerilen ilk araştırma sorusu:** Yönlü ve metrik olmayan yol süreleri, yolcunun araç içi süre sınırı, ayrı kapasite kaynakları ve sabit çapa zamanları altında, çözüm kümesini koruyan daha güçlü bir durum sıkıştırması, baskınlık kuralı veya alt sınır üretilebilir mi?

Bu sorunun cevabı henüz bulunmuş değildir. Alt küme DP, kısa rota baskınlığı ve eşdeğer yolcu simetrisi mevcut başlangıç bileşenleridir; bunlara yeni isim koymak akademik özgünlük sağlamaz. Araştırma değeri, örneğin mevcut etiketlerin hangilerini neden güvenle silebildiğimizi gösteren yeni ve öncüllerden farklı bir koşulda olabilir. Ek kaynaklar varsa sadece toplam maliyeti küçük olan etiketi tutmak yeterli olmayabilir; gelecekteki tüm uzatmalara etkisi korunmalıdır.

Başarı kanıtı iki parçalı olmalı:

1. **Doğruluk:** Kuralın varsayımları yazılmalı, kanıtı kurulmalı; küçük örneklerde bütün sıralamalarla karşılaştırılmalı. Üçgen eşitsizliğini bozan örnekler, sıfır süreli yaylar, heterojen kapasite ve eşdeğer yolcu kimlikleri özellikle sınanmalı.
2. **Hesaplama katkısı:** Aynı problem ve aynı amaçta sade DP'ye karşı durum sayısı, bellek, optimumu kanıtlama süresi ve zaman aşımındaki açık ölçülmeli. Her yeni kural ayrı kapatılabilmeli. Genel bir MIP/CP modeli mümkün olduğu ölçüde ikinci referans olmalı.

Özgün bir kural bulunamaz ama güvenilir hızlı bir çözücü elde edilirse bu hâlâ ürün açısından başarıdır; akademik iddia yöntem icadı yerine problem/modelleme, uygulama veya yeniden üretilebilir kıyas katkısına daraltılmalıdır.

Gün seçimi tarafında amaç, her dalganın kendi en iyi rotalarını seçmekle tüm günün en iyi araç kullanımının aynı olmadığını açıkça modellemektir. Bunun araştırılabilir değeri vardır; ancak çok seferli rotalama ve çizelgeleme öncülleri nedeniyle tek başına “rotaları gün boyunca birlikte seçtik” yeterli yenilik değildir. [P7]

### 7.4 İkinci yön: gün amacını öğrenen rota/kolon önerisi

**Araştırma hipotezi:** Yalnız bir dalgada sık görülen iyi kenarları taklit etmek yerine, rota adayının günün araç darboğazına katkısını öğrenmek daha yararlı olabilir.

Örneğin 10:00 civarında aynı araç havuzuna talep yığılırken birkaç dakika daha kısa rota, başka saatteki aynı kısalmadan daha değerli olabilir. Bu bir açıklama örneğidir; depodan ölçülmüş yeni bir sonuç değildir. Modelin özellikleri, etiketleri ve değerlendirmesi gün amacıyla eşleşmelidir. Bir kolon üretme formülasyonu kurulursa dual bilgiler aday seçiminde kullanılabilir; mevcut sonlu menü seçicisinin otomatik olarak böyle bir pricing sistemi olduğu varsayılmamalıdır.

Özgünlük adayı, genel “ML + kolon üretimi” değil; tanımlı UniRide kısıtları altında gün düzeyinde değeri temsil eden belirli mekanizma ve bunun önceki seçicilere göre gösterilmiş farkıdır. En yakın öncüller P12–P13 olduğundan bu fark açıkça karşılaştırılmalıdır.

En küçük ayırt edici deney, aynı başlangıç havuzu ve aynı gün seçicisi üzerinde şu seçenekleri karşılaştırır: öğrenmesiz seçim; basit süre/yoğunluk kuralı; dalga düzeyinde öğrenme; gün düzeyinde öğrenme. Eğitim maliyeti, öneri süresi ve geri dönüş maliyeti dâhil edilir. Test haftası/aileleri eğitimden ayrı tutulur. Önce küçük bir model ve basit özellikler yeterlidir; derin model gerekliliği ayrıca gösterilmelidir.

**Optimalite sınırı:** Öğrenme kalıcı olarak aday sildiğinde sonuç kısıtlı havuz üzerindedir. Tam ağa dönülüp pricing problemi kesin çözülürse, uygun varsayımlar altında kolon üretiminin LP alt sınırı kapatılabilir. Bundan tamsayılı küresel optimum çıkarmak için ayrıca branch-and-price gibi eksiksiz tamsayılı süreç, tam kolon kümesi üzerinde ispatlı çözüm veya eşdeğer bir sertifika gerekir. Zaman aşımı bu sertifikayı ayrıca sınırlar. Bu ayrım P13'ün §2 doğrusal gevşetme formülasyonuyla uyumludur.

### 7.5 Üçüncü yön: Split sonrasındaki katkıyı öğrenen operatör seçimi

A7/ERPL çevresinde sınırlı maliyetli bir deney yapılabilir: bir operatörün çıplak turda sağladığı kazanç ile Split, yerel arama ve gün seçimi sonrasındaki kazancı ayırmak. Ancak ALNS ve DR-ALNS öncülleri nedeniyle bunun akademik yenilik eşiği yüksektir. [P10–P11]

Gerekli karşılaştırmalar: sabit operatör karışımı, rastgele seçim, klasik başarı ağırlıkları, bağlama duyarlı seçim ve bağlam bilgisi karıştırılmış kontrol. Aynı iyileştirme aşamaları ve bütçeler korunmalı. Tek bir operatörün iyi çıkmasıyla öğrenmenin katkısı karıştırılmamalı. Bu yön, ilk iki yönün yerini alacak ana yatırım olarak değil, katkısı ölçülebilen koşullu araştırma olarak önerilir.

### 7.6 “Başarılı” ve “SOTA” için kabul ölçütleri

| İddia | Gerekli kanıt | Yetersiz kanıt |
|---|---|---|
| Doğru çözücü | Kısıt doğrulaması, sınır durumları, küçük exact/parite kontrolü | Yalnız geçerli görünen bir rota çıktısı |
| Daha iyi sezgisel | Aynı problem/amaç ve bütçede çoklu örnek, eşlenmiş deney, etki büyüklüğü ve belirsizlik | Tek hafta, tek seed, farklı sonlandırma bütçeleri |
| Daha hızlı kesin yöntem | Aynı optimum ve sertifika kapsamı, kanıta kadar süre/bellek, zaman aşımının raporlanması | Daha kısa sürede yalnız bir uygun çözüm bulmak |
| Özgün katkı | En yakın yöntemlerle mekanizma karşılaştırması, yeni sonuç/ayrım, ablasyon veya kanıt | Yeni kısaltma, bileşen listesi, farklı veri kümesi |
| Belirli sınıfta SOTA | İddia tarihinde güncel güçlü referanslar, doğru uyarlama, geniş açık kıyas ve yeniden üretim | Genel TSP/CVRP başarısını P5/P7'ye veya tersini taşımak |

Sezgisel karşılaştırmada depo kuralı gereği sabit amaç-değerlendirme bütçesi birincil, native sonlandırma ayrı ikincil protokoldür. Exact DP/MIP ile sezgiselin FE sayıları doğrudan aynı işi saymayabilir; FE'yi sessizce eşdeğer ilan etmek yerine muhasebe tanımı yazılmalı, ayrıca süre/bellek/sertifika raporlanmalıdır. Ön işleme, öğrenme ve gizli son iyileştirme maliyeti dışarıda bırakılamaz.

İstatistikte örnek ailesi/gün/hafta bağımlılığı korunmalı. Seed sayısını bağımsız problem sayısı gibi kullanmamak; yalnız p-değeri yerine eşlenmiş farkları ve belirsizliği göstermek gerekir. Yayımlanacak başarı eşiği ve durdurma kuralı sonuçlar görüldükten sonra seçilmemelidir.

## 8. Mutabakat için karar listesi

Aşağıdakiler **öneridir; henüz onaylanmış proje kararı değildir.** Yeni mimari kapılar açma veya mevcut iş paketi sırasını atlama yetkisi vermez.

| Karar | Önerim | Neden / kapanış kanıtı |
|---|---|---|
| M1 — Dış bulguların kabulü | §6'daki madde bazlı değerlendirmeyi temel al | 48 maddenin hepsini hata diye topluca kabul etme; düzeltme ve öncelik önerisini ayır |
| M2 — Önce hangi iş? | Dış prototip ve ham kayıtların yeniden üretim paketi | Kod, sürüm, girdi hash'i, komut, ortam, seed, bütçe, ham sonuç, sertifika olmadan performans hükmü kapanmaz |
| M3 — Ana teknik omurga | P5 kesin referans; P7 gün düzeyi ortak seçim | Güçlü temel kurar; hazır bileşen olduğu için yenilik iddiası ayrı sınanır |
| M4 — İlk özgünlük arayışı | P5'e özgü kanıtlanabilir azaltma / alt sınır | Doğruluk ve hesaplama katkısı ayrı ölçülebilir; yeni kural bulunacağı garanti değil |
| M5 — Öğrenmenin rolü | İkinci araştırma kolu: gün düzeyinde aday katkısı | Tek haftalık kenar taklidinden daha açık hedef; öncüllere göre fark gerekir |
| M6 — A7/ERPL yatırımı | Bounded pilot; nötr/olumsuz sonuçta durdurma seçeneği | Dolaylı GA/GPX sonuçlarıyla peşinen kabul veya ret yerine doğrudan ablasyon |
| M7 — P8 | Ayrı model/decoder/validator tamamlanmadan P8 sonucu yazma | n büyütmek pickup-delivery semantiği oluşturmaz |
| M8 — Mevcut iddia dili | “Araştırma adayı / dış prototip bildirimi” | “Yeni SOTA / bütün amaçlarda proven / üretime hazır” henüz desteklenmiyor |

Mutabakat sonrası makul sıra: önce kaynak paketini dondurmak ve bu rapordaki anlam değiştiren cümleleri düzeltmek; sonra mevcut depo kapılarına uygun ayrı uygulama planı; ardından küçük kesinlik/parite kontrolleri; en son önceden tanımlanmış kıyas ve özgünlük kararı. Bir teori/algoritma katkısı çıkmazsa uygulama katkısına dönmek başarısızlığı gizlemek değildir; iddiayı kanıtla eşleştirmektir.

## 9. Doğrulama kaydı ve açık sınırlar

Bu rapor kaynakların yerine geçmez. İncelemede yapılanlar:

- Ana tasarım, iki Claude Science revizyonu, değerlendirme, öğrenme deneyi, literatür sentezi ve CSV'ler okundu; kopya revizyonların eşitliği ve 48 bulgu/87 kaynak satırı sayıldı.
- Matematiksel sıra/alt küme sayıları doğrudan hesaplandı; sonek/T iddiası için F02 karşı örneği kuruldu.
- Önceki inceleme adımında, bellek içi küçük Node kontrolünde 25 yönlü matrisin iki yönünde toplam 3.150 alt küme karşılaştırması yapıldı. Her matriste n=6, rota kardinalitesi en çok 4; köşegen dışı yaylar 0–24, R 10–39, T 10–54 aralıklarında üretildi. Üreteç başlangıcı 7163; 32-bit LCG çarpanı 1664525, artışı 1013904223 idi. Tüm sıralama kontrolü, geriye araç-içi süre kontrolü ve sonunda T kontrolü yapan küçük DP ile eşleşti. Bu deney yalnız küçük matematiksel kontrol kapsamındadır; gerçek Sw/So, tüm zaman pencereleri, üretim çözücüsü veya dış prototip sertifikası değildir. Kalıcı benchmark paketi olarak sunulmaz.
- Yerel kampanya envanterinde 57 işin dört R koşuluyla 228 hücre oluşturduğu, 36 hücrelik zor alt grubun 9 işe karşılık geldiği kontrol edildi. Aynı matris kaynağı ile farklı boyutlu dalga alt matrisleri birbirinden ayrıldı; bu sayımlar dış algoritmanın sonuç değerlerini yeniden üretmez.
- Split'in ilgili güncel T/R kontrolü okunarak F24 sınırlandı. Önceki adımda CodeGraph indeksleme daemon hatası verdi; init mevcut indeks bildirdi. Bunun ardından ilgili dosya doğrudan okundu. Başarılı yeni CodeGraph taraması yapıldığı iddia edilmiyor.
- Birincil literatür kontrolünde yayıncı/yazar/kurum kaynakları kullanıldı. Bazı DOI açılışları erişim hatası verdi; erişilebilen yayıncı özeti veya kurum kopyasıyla yalnız desteklenen kapsam aktarıldı. GPT-5.6 Sol alt ajanı dar öncül araştırmasına katkı verdi; nihai sentez Codex'e aittir. Gemini/Qwen gibi erişilmeyen modellerden yeni görüş alınmadı.

**Yapılmayanlar:** Dış prototipleri çalıştırma; tüm eski benchmarkları yeniden koşma; 87 kaynağın tamamının tam metin denetimi; sistematik güncel SOTA taraması; üretim entegrasyonu; kaynak belgeleri düzeltme; kullanıcı adına yöntem seçimi; commit/merge/push. Bu rapor tek yeni dosya olarak oluşturulmuştur.

## 10. Birincil kaynaklar ve erişim kapsamı

Aşağıdaki kaynaklar belirli cümleleri destekler; bütün raporu veya UniRide sonuçlarını doğrulamaz. Kaynakça kaydının mevcut olması makalenin her sonucunun bağımsız tekrarlandığı anlamına gelmez.

- **P1 — GPX2:** [Üniversite arşivindeki çalışma](https://dspace.stir.ac.uk/handle/1893/28894?mode=simple). GPX/GPX2 ayrımının literatür bağlamı; depodaki belirli GPX gerçekleştirimine eşdeğerlik kanıtı değildir.
- **P2 — elkai matris/problem tipi:** [Resmî kaynak kodu](https://raw.githubusercontent.com/fikisipi/elkai/master/elkai/types.py). TSP/ATSP seçimi için uygulama kaynağı. Hareketli master bağlantısıdır; deney paketinde kullanılan sürüm ayrıca sabitlenmelidir.
- **P3 — elkai lisansı:** [Depo lisans metni](https://raw.githubusercontent.com/fikisipi/elkai/master/LICENSE). Kullanım koşullarının kaynağı; bütün bağımlılıkların genel lisans onayı değildir.
- **P4 — MatNet:** [Kwon vd., Matrix Encoding Networks for Neural Combinatorial Optimization](https://arxiv.org/html/2106.11113). Asimetrik maliyet matrisi öğrenme bağlamı; yalnız simetrik Öklidyen TSP üzerinden sınır çizilmemeli.
- **P5 — p-değeri yorumu:** [Wasserstein ve Lazar, The ASA Statement on p-Values: Context, Process, and Purpose (2016)](https://doi.org/10.1080/00031305.2016.1154108). Büyük p-değeri eşitliği kanıtlamaz.
- **P6 — Alt küme DP:** [Held ve Karp, A Dynamic Programming Approach to Sequencing Problems (1962)](https://doi.org/10.1137/0110015). Yayıncı kaydı ve temel yöntem.
- **P7 — Çok seferli kesin çözüm:** [Mingozzi, Roberti ve Toth, An Exact Algorithm for the Multitrip Vehicle Routing Problem (2013)](https://doi.org/10.1287/ijoc.1110.0495); [kurumsal tam metin](https://orbit.dtu.dk/files/102282745/An_Exact_Algorithm_for_the_Multitrip_Vehicle_Routing_Problem.pdf). Yayıncı özeti/formülasyon kapsamı kontrol edildi; UniRide varyantıyla eşit olduğu ileri sürülmedi.
- **P8 — Kenar histogramı öğrenmesi:** [Tsutsui, Pelikan ve Ghosh, Edge Histogram Based Sampling with Local Search for Solving Permutation Problems (2006)](https://doi.org/10.3233/HIS-2006-3102); [yazarın kurumundaki metin](https://www.isical.ac.in/~ash/ijhis-tsutsuiL.pdf). Yayıncı özeti ve örnekleme mekanizması.
- **P9 — Split:** [Prins, Labadi ve Reghioui, Tour Splitting Algorithms for Vehicle Routing Problems (2009)](https://doi.org/10.1080/00207540802426599). Split öncülü; UniRide nonmetric/T/R sözleşmesinin aynı olduğu iddia edilmedi.
- **P10 — ALNS:** [Ropke ve Pisinger, An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time Windows (2006)](https://doi.org/10.1287/trsc.1050.0135). Yayıncı özeti ve uyarlamalı yöntem tanımı.
- **P11 — Öğrenilmiş kontrol:** [Reijnen vd., Online Control of Adaptive Large Neighborhood Search Using Deep Reinforcement Learning (2024)](https://ojs.aaai.org/index.php/ICAPS/article/view/31507). Yayıncı özeti; çalışma durumuna bağlı operatör/parametre seçimi.
- **P12 — Kolon seçimi:** [Morabit, Desaulniers ve Lodi, Machine-Learning–Based Column Selection for Column Generation (2021)](https://pubsonline.informs.org/doi/10.1287/trsc.2021.1045). Yayıncı kaydı ve özet; öğrenilmiş umut veren kolon seçimi.
- **P13 — Yay seçimi ve tam ağa dönüş:** [Morabit, Desaulniers ve Lodi, Machine-Learning–Based Arc Selection for Constrained Shortest Path Problems in Column Generation](https://doi.org/10.1287/ijoo.2022.0082); [2022 ön baskısı, §2 ve Algoritma 2](https://arxiv.org/html/2201.02535v1). Tam metinde LP bağlamı ve tam ağ geri dönüşü kontrol edildi. Buradan koşulsuz tamsayılı optimalite iddiası çıkarılmadı.

**Mutabakat özeti:** Gerçek bir akademik katkı ihtimali var; en güçlü aday belirli problem yapısına ait, doğruluğu kanıtlanabilen ve katkısı ayrı ölçülen bir mekanizma. Mevcut iyi bileşenleri önce doğru kurmak, ardından yenilik ve performansı ayrı sınamak gerekir. Bu rapor o ayrımı korumak için hazırlanmıştır.
