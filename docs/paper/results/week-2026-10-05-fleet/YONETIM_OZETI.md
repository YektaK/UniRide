# Öğrenci Servisi İçin Kaç Araç Gerekir? Yönetim Özeti

Dönem: 5-9 Ekim 2026 haftası, mevcut öğrencilerin ders programına göre (günde 19-27 öğrenci, gidiş ve dönüş). Bu bir karar destek hesabıdır. Maliyet karşılaştırması yapılamaz; bu belge seçenekler arasında maliyet sıralaması vermez.

## Soru ve varsayımlar

Mevcut öğrencileri haftalık ders programlarına göre taşımak için kaç araç gerekir; bu araçlar yeni erişilebilir minibüslerden mi, yoksa mevcut minibüs ile ödünç alınan araçlardan mı oluşmalıdır?

- Bir öğrencinin araçta geçireceği süre için üst sınır koyduk. Ana değerlendirme 60 dakikadır; 50, 70 ve 90 dakika da hesaplandı (Ek).
- Minibüs 4 tekerlekli sandalye + 5 oturan yolcu alır. Sedan 4 oturan yolcu alır; tekerlekli sandalyeli öğrenci taşıyamadığı **varsayıldı**. Minivan (Fiat Doblò): toplam 3 yolcu; bunlardan en fazla 1'i tekerlekli sandalyeli öğrenci (sandalye bagaja konur, öğrenci koltukta oturur). Bu model bir **varsayımdır** ve gerçek araca göre değişebilir; daha küçük bir model hesaplanmadı.
- Araçlar her seferden sonra 10 dakika dinlenir.
- Bir aracın tek seferi en çok 150 dakika sürebilir.
- Rotaları bir bilgisayar yöntemi üretti (sezgisel yöntem: bilgisayarın ürettiği yaklaşık rotalar). "En az araç" yalnızca üretilen rotalar arasında kanıtlanmıştır; farklı bir rota planı daha az araçla çalışabilir.

Senaryolar: **A** tümü yeni minibüs, sedan yok. **B** mevcut 1 minibüs + ödünç sedanlar. **C** 2 minibüs + sedanlar. **D** 3 minibüs + sedanlar. B, C ve D'de sedan sayısı en aza indirilmiştir. Haftalık araç sayısı, aynı araçların hafta boyunca kullanılması halinde en yoğun günün ihtiyacıdır.

## Ana sonuç: 60 dakika sınırı

| Senaryo | Haftalık araç | Günlük sedan (Pzt / Sal / Çar / Per / Cum) |
|---|---|---|
| A: yalnızca minibüs | 6 minibüs (günlere göre 5 / 4 / 6 / 4 / 5) | yok |
| B: 1 minibüs + sedan | Yapılamıyor (5 günün hiçbirinde) | - |
| C: 2 minibüs + sedan | Yapılamıyor: yalnızca Salı, Perşembe, Cuma mümkün | Sal 2, Per 2, Cum 3 |
| D: 3 minibüs + sedan | 3 minibüs + en çok 3 sedan = 6 araç | 2 / 1 / 3 / 1 / 2 |

Okuma: D'de toplam araç sayısı A ile aynıdır, ancak 6 minibüs yerine 3 minibüs ve ödünç sedan kullanılır. Haftalık toplam sürüş süresi çok yakındır (A: 6.450 dakika, D: 6.472 dakika); sedanlar D'deki sürüşün %14,4'ünü yapar. Yolculuk süresi sınırı gevşedikçe sedan ihtiyacı azalır ya da aynı kalır (günde en çok 4, 3, 3 ve 1 sedan; 50, 60, 70 ve 90 dakika).

## Neden B ve C yapılamıyor?

Sedan tekerlekli sandalyeli öğrenciyi taşıyamadığı için bu öğrencilerin tüm rotaları minibüslere düşer. Günde 4 ile 8 öğrenci tekerlekli sandalye kullanır (Pzt-Cum: 8, 7, 7, 8 ve 4); aynı saat diliminde sayıları 5'e çıkabilir (Pazartesi ve Perşembe), oysa bir minibüs 4 sandalye alır. Neden kodları (`scenario_daily.csv`) iki ayrı sebep gösterir; sedan varsayımı tek başına açıklama değildir:

- **B (1 minibüs): 20 günlük hücrenin hepsi yapılamıyor.** 15'inde sandalyeli öğrencilerin talebi bir minibüsün kapasitesini aşar (`SW_DEMAND_EXCEEDS_LARGE_CAPACITY`); yani sandalyeli öğrencilerin rotaları süre sınırı içinde tek minibüse sığmaz (örneğin Salı günü, 60 dk). 5'inde yakın saat dilimlerinin seferleri çakışır (`CROSS_WAVE_CONFLICT`).
- **C (2 minibüs): 20 hücrenin 9'u yapılamıyor, ve çoğu çakışma yüzünden.** Yalnızca 2'si kapasite sorunudur (Pazartesi, 50 ve 60 dk). Diğer 7'si saat dilimi çakışmasıdır (50 dk: Çarşamba, Perşembe; 60 dk: Çarşamba; 70 dk: Salı, Çarşamba; 90 dk: Salı, Çarşamba).

Çakışma şu demektir: sedanlar sandalyeli öğrenci taşıyamadığı için sandalyeli öğrencilerin tüm rotaları minibüslere gitmek zorundadır ve yan yana saat dilimlerinin minibüs seferleri zaman olarak üst üste biner; iki minibüs bunları sırayla yetiştiremez. Sedan sandalye taşıyabilseydi sonuçlar değişebilirdi; bu durum hesaplanmadı.

## Ödünç araç ne kadar ve ne zaman gerekir? Anahtar seçenekler (60 dakika)

Sedan yalnızca oturan öğrenci taşır; minivan ayrıca bir sandalye de taşıyabilir. Bu yüzden sedan ancak yeterli minibüs sandalye seferlerini üstlenebiliyorsa kullanılabilir (bu hafta için en az 3 minibüs); minivan 0 minibüsle de çalışır, ama çok daha fazla araç ve saat ister. "Araç-saat", ödünç bir aracın sürüşte ve her seferden sonraki 10 dakikalık dinlenmede geçirdiği toplam süredir; aracın ödünçte kaldığı süreden kısa ya da ona eşittir.

| Seçenek | Kendi minibüsümüz | Ödünç araç (en yoğun gün) | Günler ve saatler | Haftada ödünç araç-saat |
|---|---|---|---|---|
| A: yalnızca minibüs | 1 mevcut + 5 yeni alım | yok | - | 0 |
| 4 minibüs + sedan | 1 mevcut + 3 yeni alım | en çok 2 sedan | Pzt 07:43-08:45; Çar 11:51-13:07; Cum 13:02-13:45 (Sal ve Per yok) | 4,2 |
| 3 minibüs + sedan | 1 mevcut + 2 yeni alım | en çok 3 sedan | Her gün, günde 1-3 sedan | 18,2 |
| 2 minibüs + minivan | 1 mevcut + 1 yeni alım | en çok 4 minivan | Her gün, günde 2-4 minivan; en yoğun an Çar 12:15 (4 minivan) | 42,5 |
| 1 minibüs + minivan | 1 mevcut | en çok 5 minivan | Her gün, günde 3-5 minivan | 83,6 |
| yalnızca minivan | 0 (mevcut minibüs kullanılmaz) | en çok 7 minivan | Her gün, günde 5-7 minivan | 135,5 |

Tablodaki seçeneklerin hepsi "Pareto/elenmeyen" seçenektir: başka bir seçenek, bu üç ölçütün (minibüs sayısı, en yoğun gün ödünç araç, haftalık araç-saat) hiçbirinde daha kötü değil ve en az birinde daha iyi ise o seçenek elenir; tablodakiler elenmeyenlerdir. Karşılaştırma aynı 60 dakika sınırı içindedir.

- **4 minibüs + sedan:** ödünç sedan yalnızca 3 günde ve kısa süreliğine gerekir: Pzt 1 sedan (07:43-08:45), Çar 2 sedan (11:51-12:45 ve 12:15-13:07), Cum 1 sedan (13:02-13:45).
- **3 minibüs + sedan:** Pzt 2, Sal 1, Çar 3, Per 1, Cum 2 sedan. Bazı sedanlar gün boyu (ör. Pzt 07:12-16:50, Cum 07:37-17:28) elde tutulmalıdır. Araç-saatlerin %32'si saat 10:00'dan önce.
- **2 minibüs + minivan:** Pzt 3, Sal 2, Çar 4, Per 2, Cum 3 minivan. Pazartesi 08:20'de 3 minivan birlikte gerekir. Araç-saatlerin %28'i 10:00'dan önce.
- **1 minibüs + minivan ve yalnızca minivan:** yeni minibüs almaktan kaçınır, fakat ödünç yükü en yüksektir.
- **Melez (2 minibüs + sedan ve minivan):** Sal, Per, Cum sedan; yalnızca Pzt (3 araç) ve Çar (4 araç) minivan. Haftada 44,5 araç-saat. Minivan 2 günde gerekir (saf minivanda 5 gün); ancak saf 2 minibüs + minivan seçeneği 42,5 araç-saat gerektirir, melez ise daha fazla (44,5 > 42,5; 60 dakikada) gerektirir. Bu yüzden melez seçenek, 2 minibüs + minivan seçeneği tarafından elenir (en yoğun gün araç sayısı aynı, araç-saat daha fazla). Melez yalnızca minivan gün sayısını azaltır.

Kullanım: Yalnızca minibüs seçeneğinde 6 minibüs günlük hizmet süresinin yaklaşık %34'ünde meşguldür; ödünç araç arttıkça kendi minibüslerimiz daha dolu çalışır (3 minibüste %58, 2'de %66, 1'de %72). Beş gün ödünç gereken seçeneklerde ödünç araçlar, ödünçte kaldıkları sürenin yaklaşık yarısında (%50-54) sürüşte ya da dinlenmededir; geri kalanı beklemedir. 4 minibüs + sedan seçeneğinde oran %100'dür.

## Dikkat edilmesi gerekenler

- **Minivan kapasitesi düzeltildi.** İlk hesapta minivan 1 sandalye + 3 oturan, yani 4 kişi almıştı; Doblò'nun kapasitesi toplam 3 yolcudur. Düzeltilmiş hesapta yalnızca "yalnızca minivan" seçeneğinde en yoğun gündeki araç sayısı 1 arttı (50, 60, 70 ve 90 dakikada 7, 6, 6, 6 yerine 8, 7, 7, 7). 1 ve 2 minibüs + minivan seçeneklerinde en yoğun gündeki araç sayısı değişmedi; haftalık araç-saatleri en çok 2,7 saat değişti; bazı seçeneklerde arttı, bazılarında azaldı (60 dakikada 1 minibüs + minivan 82,5 yerine 83,6; 2 minibüs + minivan 43,0 yerine 42,5). Sedan seçenekleri etkilenmedi.
- Programda dersi olan her öğrencinin o gün geleceği ve tüm oturan öğrencilerin sedana ya da minivana binebileceği varsayıldı; gerçek katılım düşükse ihtiyaç azalabilir.
- Sedanın sandalye taşıyıp taşıyamadığı ve minivanın gerçek kapasitesi (toplam 3 yolcu, en fazla 1'i sandalyeli) bilinmiyor; ikisi de varsayımdır ve sonuçları değiştirebilir (B ve C'nin yapılamamasında sedan varsayımı tek neden değildir, yukarıya bakın).
- Maliyet verisi yoktur (kiralama, şoför, yakıt); bu belge maliyet sıralaması vermez.
- Tek bir haftanın programı, tek rota üretimi ve sabit yolculuk süreleri kullanıldı; trafik, biniş süreleri ve sürücü atamaları yoktur.
- Ödünç araçların hangi gün ve saatte boş olduğu bilinmiyor. "Araç-saat" yalnızca sürüş ve dinlenmedir; bir araç ilk seferinden son seferine kadar elde tutulacaksa gereken süre daha uzun olabilir (60 dakikada 4 minibüs + sedan seçeneğinde eşittir; saat aralıkları yukarıda).

## Sonraki adımlar

1. Sedanın tekerlekli sandalyeli öğrenciyi taşıyıp taşıyamayacağını ölçmek (B ve C'yi doğrudan etkiler).
2. Öğrencilerin gerçek katılımını doğrulamak.
3. Maliyet verisini toplamak: yeni minibüs, sedan ve minivan kirası, sürücü giderleri.
4. Hangi gün ve saatlerde kaç aracın ödünç verilebileceğini üniversiteden öğrenmek.
5. Minivanın gerçek kapasitesini doğrulamak (şimdiki varsayım: toplam 3 yolcu, en fazla 1'i sandalyeli); farklıysa yeniden hesaplamak.

Ayrıntılar: `pareto_analysis.md`, `pareto_options.csv`, `weekly_summary.md`, `fleet_verification.md`, `figures/index.html`.

## Ek: diğer yolculuk süresi sınırları

Haftalık toplam araç (minibüs + en çok günlük sedan):

| Senaryo | 50 dk | 60 dk | 70 dk | 90 dk |
|---|---|---|---|---|
| A | 6 | 6 | 6 | 4 |
| B | yapılamıyor | yapılamıyor | yapılamıyor | yapılamıyor |
| C | yapılamıyor (5 günün 2'si mümkün) | yapılamıyor (3'ü mümkün) | yapılamıyor (3'ü mümkün) | yapılamıyor (3'ü mümkün) |
| D | 3 + 4 = 7 | 3 + 3 = 6 | 3 + 3 = 6 | 3 + 1 = 4 |

Ödünç seçenekler (en yoğun gün ödünç araç sayısı / haftada araç-saat):

| Seçenek | 50 dk | 60 dk | 70 dk | 90 dk |
|---|---|---|---|---|
| A: minibüs sayısı | 6 | 6 | 6 | 4 |
| 4 minibüs + sedan | 2 / 10,2 | 2 / 4,2 | 2 / 2,2 | 0 / 0 |
| 3 minibüs + sedan | 4 / 34,4 | 3 / 18,2 | 3 / 10,2 | 1 / 3,1 |
| 2 minibüs + minivan | 5 / 56,4 | 4 / 42,5 | 4 / 30,2 | 2 / 25,3 |

90 dakikada 4 minibüs hiç ödünç araç istemez (yalnızca-minibüs seçeneğiyle aynıdır).
