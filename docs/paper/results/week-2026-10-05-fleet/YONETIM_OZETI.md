# Öğrenci Servisi İçin Kaç Araç Gerekir? Yönetim Özeti

Dönem: 5-9 Ekim 2026 haftası, mevcut öğrencilerin ders programına göre (günde 19-27 öğrenci, gidiş ve dönüş). Bu bir karar destek hesabıdır; maliyet içermez.

## Soru

Mevcut öğrencileri haftalık ders programlarına göre taşımak için kaç araç gerekir, ve bu araçlar yeni erişilebilir minibüslerden mi, yoksa mevcut minibüs ile ödünç alınan binek araçlardan (sedan) mı oluşmalıdır?

Her öğrencinin araçta geçireceği süre için bir üst sınır koyduk. Ana değerlendirme 60 dakikadır; 50, 70 ve 90 dakika da hesaplandı. Minibüs 4 tekerlekli sandalye ve 5 oturan yolcu alır. Sedan 4 oturan yolcu alır; tekerlekli sandalye kullanan öğrenci taşıyamadığını varsaydık. Araçlar her seferden sonra 10 dakika dinlenir.

Bu sürümde iki seçenek daha var: (1) 4 minibüs + sedan, (2) tekerlekli sandalyeli bir öğrenci ve 3 oturan yolcu alabilen erişilebilir minivan (Fiat Doblò türü). Minivanın 1 sandalye + 3 oturan kapasitesi bir **varsayımdır**; gerçek araca göre değişebilir ve ayrıca denenebilir (ör. 1 sandalye + 2 oturan; bu hesaplanmadı).

## Senaryolar

- **A:** Tümü yeni erişilebilir minibüs; sedan yok. En az kaç minibüs gerekir?
- **B:** Mevcut 1 minibüs + ödünç sedanlar.
- **C:** 2 minibüs + ödünç sedanlar.
- **D:** 3 minibüs + ödünç sedanlar.

B, C ve D için sedan sayısı en aza indirilmiştir. Haftalık araç sayısı, aynı araçların hafta boyunca kullanılması halinde en yoğun günün ihtiyacıdır.

## Ana sonuç: 60 dakika sınırı

| Senaryo | Haftalık araç | Günlük sedan (Pzt / Sal / Çar / Per / Cum) |
|---|---|---|
| A: yalnızca minibüs | 6 minibüs (günlere göre 5 / 4 / 6 / 4 / 5) | yok |
| B: 1 minibüs + sedan | Yapılamıyor (5 günün hiçbirinde) | - |
| C: 2 minibüs + sedan | Yapılamıyor: yalnızca Salı, Perşembe, Cuma mümkün | Sal 2, Per 2, Cum 3 |
| D: 3 minibüs + sedan | 3 minibüs + en çok 3 sedan = 6 araç | 2 / 1 / 3 / 1 / 2 |

Diğer yolculuk süresi sınırlarında haftalık toplam araç (minibüs + en çok günlük sedan):

| Senaryo | 50 dk | 60 dk | 70 dk | 90 dk |
|---|---|---|---|---|
| A | 6 | 6 | 6 | 4 |
| B | yapılamıyor | yapılamıyor | yapılamıyor | yapılamıyor |
| C | yapılamıyor (5 günün 2'si mümkün) | yapılamıyor (3'ü mümkün) | yapılamıyor (3'ü mümkün) | yapılamıyor (3'ü mümkün) |
| D | 3 + 4 = 7 | 3 + 3 = 6 | 3 + 3 = 6 | 3 + 1 = 4 |

Okuma: D senaryosunda toplam araç sayısı A ile aynıdır (50 dakikada bir fazla), ancak 6 minibüs yerine 3 minibüs ve ödünç sedan kullanılır. Haftalık toplam sürüş süresi A ile çok yakındır (60 dakikada 6.472 dakikaya karşılık 6.450 dakika). Sedanlar toplam sürüşün %14,4'ünü yapar (60 dakikada). Yolculuk süresi sınırı gevşedikçe sedan ihtiyacı azalır: günde en çok 4 (50 dk), 3 (60 ve 70 dk), 1 (90 dk).

## Neden B (1 minibüs) yeterli değil?

Sedan tekerlekli sandalye kullanan öğrenciyi taşıyamadığı için onların tüm seferlerini minibüs yapmak zorundadır. Günde 4 ile 8 arasında öğrenci tekerlekli sandalye kullanmaktadır (Pzt-Cum: 8, 7, 7, 8 ve 4). Aynı saat diliminde bu öğrencilerin sayısı 5'e kadar çıkar (Pazartesi ve Perşembe; bir minibüs 4 sandalye alır). Salı günü en kalabalık saat diliminde 3 sandalyeli öğrenci vardır, ancak 60 dakika sınırı içinde tek minibüs hepsini alamaz. Çarşamba günü ise komşu saat dilimlerindeki seferler üst üste biner. 5 gün ve 4 süre sınırının oluşturduğu 20 kombinasyonun hepsinde B yapılamamıştır: 15'inde tek bir saat diliminde birden fazla minibüs gerekir, 5'inde farklı saat dilimlerinin seferleri çakışır.

## Ödünç araç ne kadar ve ne zaman gerekir? Anahtar seçenekler (60 dakika)

Sedan yalnızca oturan öğrenci taşır; minivan ayrıca bir tekerlekli sandalyeyi de taşıyabilir. Bu yüzden sedan ancak yeterli minibüs sandalye seferlerini üstlenebiliyorsa kullanılabilir (en az 3 minibüs); minivan 0 minibüsle bile çalışır, ama çok daha fazla araç ve saat ister. "Araç-saat", ödünç bir aracın sürüşte ve her seferden sonraki 10 dakikalık dinlenmede geçirdiği toplam süredir; bir aracın ödünçte kaldığı süreden kısadır.

| Seçenek | Kendi minibüsümüz | Ödünç/kiralık araç (en yoğun gün) | Ödünç gün sayısı | Haftada ödünç araç-saat |
|---|---|---|---|---|
| A: yalnızca minibüs | 6 | yok | 0 | 0 |
| 4 minibüs + sedan | 4 | en çok 2 sedan | 3 gün | 4,2 |
| 3 minibüs + sedan | 3 | en çok 3 sedan | 5 gün | 18,2 |
| 2 minibüs + minivan | 2 | en çok 4 minivan | 5 gün | 43,0 |
| 1 minibüs + minivan | 1 | en çok 5 minivan | 5 gün | 82,5 |
| yalnızca minivan | 0 | en çok 6 minivan | 5 gün | 133,3 |

Bunların hepsi, başka hiçbir seçeneğin "hem daha az minibüs, hem daha az ödünç araç, hem daha az saat" ile geçemediği seçeneklerdir (çok amaçlı karşılaştırmada "elenmeyenler"). Aşağıdaki maddelerin her biri aynı soruyu yanıtlar: kaç minibüs bizim, kaç araç ödünç, hangi gün ve saatlerde, haftada kaç saat.

- **4 minibüs + sedan.** 4 minibüs bizim. Ödünç sedan yalnızca 3 günde gerekir: Pazartesi 1 sedan (07:43-08:45), Çarşamba 2 sedan (11:51-12:45 ve 12:15-13:07), Cuma 1 sedan (13:02-13:45). Salı ve Perşembe ödünç araç gerekmez. Haftada toplam 4,2 araç-saat. Her sedan günde tek bir sefer için, kısa süreliğine gerekir.
- **3 minibüs + sedan.** 3 minibüs bizim. Her gün 1 ila 3 sedan: Pazartesi 2 (07:12-16:50 ve 07:43-08:45), Salı 1 (07:23-13:36), Çarşamba 3 (11:15-13:07 arasında), Perşembe 1 (13:15-16:49), Cuma 2 (07:37-17:28 ve 13:02-13:45). Haftada 18,2 araç-saat; bunun %32'si saat 10:00'dan önce.
- **2 minibüs + minivan.** 2 minibüs bizim. Her gün kiralık/ödünç minivan gerekir: Pazartesi 3, Salı 2, Çarşamba 4, Perşembe 2, Cuma 3. En kalabalık an Çarşamba 12:15'tir (4 minivan aynı anda); Pazartesi sabah 07:53'te 3 minivan birlikte gerekir. Haftada 43,0 araç-saat; %29'u 10:00'dan önce.
- **1 minibüs + minivan ve yalnızca minivan.** Her gün 3-5 (1 minibüsle) ya da 5-6 (minibüssüz) minivan gerekir; haftada 82,5 ve 133,3 araç-saat. Bu seçenekler minibüs almaktan tamamen kaçınır, fakat ödünç yükü en yüksektir.
- **Melez (2 minibüs + hem sedan hem minivan).** Sedanın yeteceği günlerde sedan, yetmediği günlerde minivan: Salı, Perşembe ve Cuma sedan; yalnızca Pazartesi (3 araç) ve Çarşamba (4 araç) minivan. Haftada 44,8 araç-saat. Minivan yalnızca 2 günde gerekir (saf minivan seçeneğinde 5 gün), ama toplam saat 43,0'dan düşük değildir; yani bu seçenek saat ve araç sayısı açısından saf minivandan elenir, yalnızca minivan gün sayısını azaltır.

Kullanım oranı: Yalnızca minibüs seçeneğinde 6 minibüs, günlük hizmet süresinin yaklaşık %34'ünde meşguldür; ödünç alınan araç sayısı arttıkça kendi minibüslerimiz daha dolu çalışır (3 minibüste %58, 2 minibüste %66, 1 minibüste %72). Beş gün ödünç gereken seçeneklerde ödünç araçlar, ödünçte kaldıkları sürenin yaklaşık yarısında (%50-55) sürüşte ya da dinlenmededir; geri kalanı beklemedir. 4 minibüs + sedan seçeneğinde bu oran %100'dür: sedan yalnızca sefer süresince tutulur.

Diğer yolculuk süresi sınırlarında (en yoğun gün ödünç araç sayısı / haftada araç-saat):

| Seçenek | 50 dk | 60 dk | 70 dk | 90 dk |
|---|---|---|---|---|
| A: minibüs sayısı | 6 | 6 | 6 | 4 |
| 4 minibüs + sedan | 2 / 10,2 | 2 / 4,2 | 2 / 2,2 | 0 / 0 |
| 3 minibüs + sedan | 4 / 34,4 | 3 / 18,2 | 3 / 10,2 | 1 / 3,1 |
| 2 minibüs + minivan | 5 / 55,3 | 4 / 43,0 | 4 / 30,3 | 2 / 24,4 |

90 dakikada 4 minibüs hiç ödünç araç istemez (yalnızca-minibüs seçeneğiyle aynıdır). Ayrıntılı tablolar, grafikler ve yöntem: `pareto_analysis.md`, `pareto_options.csv` ve `figures/index.html` (bölüm e).

## Dikkat edilmesi gerekenler

- Programda dersi olan her öğrencinin o gün geleceği varsayıldı. Gerçek katılım daha düşükse ihtiyaç azalabilir.
- Sedanın tekerlekli sandalye taşıyıp taşıyamadığı bilinmiyor; taşıyamadığı varsayıldı. Bu varsayım B ve C'nin yapılamamasının nedenidir. Taşıyabiliyorsa sonuçlar değişir.
- Rotaları bir bilgisayar yöntemi üretti. "En az sedan" yalnızca üretilen rotalar arasında kanıtlanmıştır; farklı bir rota planı daha az araçla çalışabilir.
- Maliyet verisi yoktur: kiralama, şoför ve yakıt dahil edilmedi. Hangi senaryonun daha ucuz olduğu bilinmiyor.
- Tek bir haftanın programı ve sabit yolculuk süreleri kullanıldı; trafik, biniş süreleri ve sürücü atamaları yoktur.
- Tüm oturan öğrencilerin sedana binebildiği varsayıldı.
- Minivanın kapasitesi (1 sandalye + 3 oturan) bir varsayımdır. Gerçek araç farklıysa sonuçlar değişir.
- Ödünç araçların hangi gün ve saatte gerçekten boş olduğu bilinmiyor. Tablolardaki "araç-saat" yalnızca sürüş ve dinlenme süresidir; bir araç ilk seferinden son seferine kadar elde tutulacaksa gereken süre daha uzundur (saat aralıkları yukarıda verilmiştir).
- Karşılaştırma tek bir haftaya, tek bir rota üretimine dayanır; rotalar sezgisel yöntemle üretildiği için "en az araç" yalnızca üretilen rotalar arasında kanıtlanmıştır.

## Sonraki adımlar

1. Bir sedanın tekerlekli sandalye kullanan öğrenciyi taşıyıp taşıyamayacağını ölçmek. Sonuç, B ve C senaryolarını doğrudan etkiler.
2. Öğrencilerin gerçek katılımını doğrulamak (hangi gün kim kullanacak).
3. Maliyet verisini toplamak: yeni minibüs, sedan kirası, minivan kirası ve sürücü giderleri.
4. Hangi günlerde ve saatlerde kaç sedanın ödünç verilebileceğini üniversiteden öğrenmek; bu, yukarıdaki seçeneklerin hangisinin uygulanabilir olduğunu belirler.
5. Minivanın gerçek kapasitesini doğrulamak ve gerekirse 1 sandalye + 2 oturan olarak yeniden hesaplamak.

Ayrıntılı tablolar, grafikler ve doğrulama sonuçları bu klasördeki `weekly_summary.md`, `fleet_verification.md` ve `figures/index.html` dosyalarındadır.
