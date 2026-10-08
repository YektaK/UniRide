# Öğrenci Servisi İçin Kaç Araç Gerekir? Yönetim Özeti

Dönem: 5-9 Ekim 2026 haftası, mevcut öğrencilerin ders programına göre (günde 19-27 öğrenci, gidiş ve dönüş). Bu bir karar destek hesabıdır; maliyet içermez.

## Soru

Mevcut öğrencileri haftalık ders programlarına göre taşımak için kaç araç gerekir, ve bu araçlar yeni erişilebilir minibüslerden mi, yoksa mevcut minibüs ile ödünç alınan binek araçlardan (sedan) mı oluşmalıdır?

Her öğrencinin araçta geçireceği süre için bir üst sınır koyduk. Ana değerlendirme 60 dakikadır; 50, 70 ve 90 dakika da hesaplandı. Minibüs 4 tekerlekli sandalye ve 5 oturan yolcu alır. Sedan 4 oturan yolcu alır; tekerlekli sandalye kullanan öğrenci taşıyamadığını varsaydık. Araçlar her seferden sonra 10 dakika dinlenir.

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

## Sedanlar ne zaman gerekir? (D senaryosu, 60 dakika)

| Gün | Sedan | Kullanım saatleri |
|---|---|---|
| Pazartesi | 2 | 07:12-16:50 ve 07:43-08:45 |
| Salı | 1 | 07:23-13:36 |
| Çarşamba | 3 | 11:15-13:07 arasında üçü birlikte |
| Perşembe | 1 | 13:15-16:49 |
| Cuma | 2 | 07:37-17:28 ve 13:02-13:45 |

Saatler bir sedanın ilk seferinin başı ile son seferinin sonu arasıdır; araç bu sürede sürekli kullanılmaz. Gerçek sürüş süresi, günlük toplam olarak yalnızca 75 ile 290 dakika arasındadır.

## Neden B (1 minibüs) yeterli değil?

Sedan tekerlekli sandalye kullanan öğrenciyi taşıyamadığı için onların tüm seferlerini minibüs yapmak zorundadır. Günde 4 ile 8 arasında öğrenci tekerlekli sandalye kullanmaktadır (Pzt-Cum: 8, 7, 7, 8 ve 4). Aynı saat diliminde bu öğrencilerin sayısı 5'e kadar çıkar (Pazartesi ve Perşembe; bir minibüs 4 sandalye alır). Salı günü en kalabalık saat diliminde 3 sandalyeli öğrenci vardır, ancak 60 dakika sınırı içinde tek minibüs hepsini alamaz. Çarşamba günü ise komşu saat dilimlerindeki seferler üst üste biner. 5 gün ve 4 süre sınırının oluşturduğu 20 kombinasyonun hepsinde B yapılamamıştır: 15'inde tek bir saat diliminde birden fazla minibüs gerekir, 5'inde farklı saat dilimlerinin seferleri çakışır.

## Dikkat edilmesi gerekenler

- Programda dersi olan her öğrencinin o gün geleceği varsayıldı. Gerçek katılım daha düşükse ihtiyaç azalabilir.
- Sedanın tekerlekli sandalye taşıyıp taşıyamadığı bilinmiyor; taşıyamadığı varsayıldı. Bu varsayım B ve C'nin yapılamamasının nedenidir. Taşıyabiliyorsa sonuçlar değişir.
- Rotaları bir bilgisayar yöntemi üretti. "En az sedan" yalnızca üretilen rotalar arasında kanıtlanmıştır; farklı bir rota planı daha az araçla çalışabilir.
- Maliyet verisi yoktur: kiralama, şoför ve yakıt dahil edilmedi. Hangi senaryonun daha ucuz olduğu bilinmiyor.
- Tek bir haftanın programı ve sabit yolculuk süreleri kullanıldı; trafik, biniş süreleri ve sürücü atamaları yoktur.
- Tüm oturan öğrencilerin sedana binebildiği varsayıldı.

## Sonraki adımlar

1. Bir sedanın tekerlekli sandalye kullanan öğrenciyi taşıyıp taşıyamayacağını ölçmek. Sonuç, B ve C senaryolarını doğrudan etkiler.
2. Öğrencilerin gerçek katılımını doğrulamak (hangi gün kim kullanacak).
3. Maliyet verisini toplamak: yeni minibüs, sedan kirası ve sürücü giderleri.

Ayrıntılı tablolar, grafikler ve doğrulama sonuçları bu klasördeki `weekly_summary.md`, `fleet_verification.md` ve `figures/index.html` dosyalarındadır.
