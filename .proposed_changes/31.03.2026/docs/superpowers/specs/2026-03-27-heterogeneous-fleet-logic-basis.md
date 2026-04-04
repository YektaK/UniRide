# UniRide Heterogeneous Fleet: Tasarım Dayanağı ve Mantıksal Temeller

> **Tarih:** 27 Mart 2026  
> **Konu:** Heterojen Filo Yönetimi, Endüstri Mühendisliği Kaynak Allokasyonu ve Dinamik Planlama

Bu doküman, UniRide projesindeki "Heterojen Filo" ve "Karar Destek Sistemi" özelliklerinin geliştirilmesi sürecindeki kullanıcı görüşmeleri, tasarım kararları ve Endüstri Mühendisliği prensiplerini özetler.

## 1. Problem Tanımı ve Evrim
Başlangıçta UniRide, tüm araçların 9 kapasiteli (4 Tekerlekli Sandalye + 5 Diğer) olduğu statik bir yapıya sahipti. Ancak gerçek operasyonda farklı kapasitelerde (Minibüs, Otobüs, Binek Araç) araçların bulunduğu ve talebin gün içinde (sabah/öğle/akşam) büyük dalgalanmalar gösterdiği tespit edilmiştir.

### Temel Sorunlar:
-   **Kapasite İsrafı**: Talebin az olduğu saatlerde büyük araçların (Bus) boşa çıkması.
-   **Darboğazlar**: Pik saatlerde (örn: 12:00) eldeki araçların yetmemesi ve çözümün "Infeasible" (imkansız) kalması.
-   **Ad-hoc Talepler**: Öğrencilerin ders programı dışındaki anlık ulaşım ihtiyaçları.

## 2. Endüstri Mühendisliği (IE) Yaklaşımı
Kullanıcının (Industrial Engineer perspektifi) yönlendirmesiyle, sistem basit bir "rota çizici"den bir **"Kaynak Allokasyon ve Seviyeleme" (Resource Allocation & Leveling)** sistemine dönüştürülmüştür.

### 2.1. Standart Araç Benchmark (Kıyaslama)
-   **Mantık**: Sistem, eldeki gerçek araçlara bakmadan önce "İdeal Senaryo"da kaç adet **Standart Minibüs (4 Sw + 5 So)** gerektiğini hesaplar.
-   **Amaç**: Adminin, toplam ihtiyacın ne olduğunu ve operasyonel verimliliğin "İdeal"e ne kadar uzak olduğunu görmesini sağlamak.

### 2.2. Yönsel Bloklama ve Kaynak Çakışması (Directional Blocking)
-   **Mantık**: Araçlar "Geliş" (Okula) ve "Gidiş" (Evlere) için ayrı zaman blokları halinde rezerve edilir.
-   **Kural**: Saat 10:00 - 12:00 arası Geliş rotası çizen bir araç, eşzamanlı olarak 11:00 Gidiş rotasında kullanılamaz.
-   **Cooldown**: Rotalar arası 15 dakikalık "geçiş ve temizlik" süresi koda dahil edilmiştir.

### 2.3. Slack Time (Esneklik Payı) ve Yük Dengeleme
-   **Mantık**: Öğrenci taleplerini (ders programını bozmadan) ±60 dakika esneterek kaynak ihtiyacını minimize etme.
-   **Fayda**: Pik saatteki yığılmayı (Peak) azaltarak toplam araç sayısını düşürmek.

## 3. Karar Destek ve Dashboard Tasarımı
Adminin bir "Sandbox" (Kum havuzu) ortamında rotalarla oynamasına imkan tanıyan görsel bir arayüz kurgulanmıştır:
-   **Hassasiyet Analizi**: Her saat dilimindeki talebin Sw (Sandalyeli) ve So (Diğer) kırılımı.
-   **Histogram-Gantt Hizalaması**: Saatlik talep ile araç kullanım bloklarının aynı zaman ekseninde hizalanması.
-   **Müdahale Seçenekleri**: Araç tipini değiştirme, sanal araç ekleme veya öğrenci saatini kaydırarak "Eksik Kaynak" uyarısını yok etme.

## 4. Teknik Altyapı Kararları
-   **Çözücüler**: Heterojen kapasite desteği için **VROOM** (hız odaklı) ve **PyVRP** (kalite odaklı) seçilmiştir.
-   **Split Decoder**: Mevcut genetik algoritmaların ürettiği rotaları heterojen araçlara en uygun (optimal) şekilde bölmek için güncellenmiştir.
