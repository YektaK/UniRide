# UniRide Ölçeklenebilirlik ve VRP Çözüm Stratejileri (N ≥ 300)

**Tarih:** 26 Mart 2026
**Bağlam:** Öğrenci sayısının (N) 30.0'lardan 300 aralığına ve ötesine çıkması durumunda, tam rotalama (VRP) algoritmalarının eksponansiyel zaman karmaşıklığına ($O(N!)$ veya $O(N^2)$) girmesini engellemek hedeflenmektedir. Orijinal "önce kümele" mantığının (Divide and Conquer) çıkış noktası, "böl ve yönet" ile uzak noktaların birbirine bağlanmaya çalışılıp çözüm süresinin boşa harcanmasını önlemektir. 

Ancak mevcut K-Means yaklaşımı, kümeler arası geçişe izin vermediği için kısıt ihlallerinde tek öğrencilik verimsiz araçlar oluşturmaktadır. Bu belge, hem bu esnekliği sağlayan hem de N=300 ölçeğinde performansı koruyan mimari seçenekleri listeler.

---

## Seçenek 1: Clarke-Wright Savings (Tasarruf) Algoritması (Akıllı Kümeleme)
*Önerilen Yaklaşım*

**Nasıl Çalışır?**
"Böl ve Yönet" yaklaşımının en lojistik odaklı versiyonudur. Öğrencileri kuş uçuşu mesafeye göre rastgele bölmek yerine (K-Means), gerçek `time_matrix`'i kullanarak "A ve B öğrencilerini aynı araca koyarsak toplam yoldan ne kadar zaman tasarruf ederiz?" hesabını yapar. En çok tasarruf sağlayanları birleştirir, araç kapasitesi veya 45 dk sınırı dolduğunda o aracı kapatıp yenisine geçer.

**Avantajları:**
- Algoritma baştan sona **zaman matrisi** üzerinden çalışır, haritada birbirine uzak olan noktaların tasarruf değeri negatif çıkacağı için algoritma bunları aynı araca koymayı denemez bile. Vakit kaybı sıfırdır.
- Sonuçlanan kümeler (araç grupları) doğrudan 45 dk kısıtına uyar, sonradan "kısıt aşıldı araç ekle" döngüsüne girilmez.
- 300 noktalı bir problemde bile Savings matrisi saniyeler içinde hesaplanır.
- Sonrasında ortaya çıkan 15-20 kişilik küçük rotalara GA/PSO/TSP uygulanarak rotalar mükemmelleştirilir.

**Uygulama Zorluğu:** Orta. (Zaten `clustering_strategies` altına altyapısı eklendi).

---

## Seçenek 2: Sweep (Süpürme) Algoritması + Sınır Kaydırma
*Bölge Bazlı Yaklaşım*

**Nasıl Çalışır?**
Depoyu (Kampüs) haritanın merkezine koyar ve bir saat yelkovanı gibi 0 dereceden 360 dereceye doğru etrafı tarar. Tararken kapasite veya zaman sınırı dolduğunda bir kesik atar (pasta dilimi oluşturur). K-Means'in aksine, sınırlar rastgele değil açısal olarak coğrafi bir düzen izler.
Eğer dilim sınırındaki bir öğrenci, yandaki dilimin aracına daha rahat sığıyorsa (zaman kısıtı kurtarıyorsa) sınır o öğrenciyi kapsayacak şekilde esnetilir (Re-insertion).

**Avantajları:**
- Tamamen birbirine uzak (örn: Kuzey ve Güney) noktaların denenmesini donanımsal olarak engeller.
- 300, hatta 3000 nokta için $O(N \log N)$ sürede çalışır (Açısal sıralama).
- Araçların bölgeleri görsel olarak da mantıklı (kesişmeyen) olur.

**Uygulama Zorluğu:** Düşük-Orta. Kesişim noktalarındaki öğrencileri kaydırmak için ekstra "post-optimization" adımı gerekir.

---

## Seçenek 3: Google OR-Tools "Time-Limit" Bütünsel Yaklaşımı
*Kara Kutu Çözüm*

**Nasıl Çalışır?**
Hiçbir kümeleme yapılmaz. 300 öğrenci doğrudan `ortools_cvrp.py`'ye gönderilir. Ancak sistemin sonsuza kadar arama yapmasını (`exponansiyel ` patlamayı) önlemek için OR-Tools'a katı bir süre sınırı (`search_parameters.time_limit.seconds = 5`) konur.

**Avantajları:**
- OR-Tools kendi içinde "Guided Local Search" kullandığı için, uzak noktaları birbirine bağlamak gibi saçma hamleleri zaten (kendi C++ motorunda) budar ve es geçer.
- Bizim ekstra bir bölme mantığı yazmamıza gerek kalmaz.
- Süre kesin olarak sınırlanır (Örn: "En fazla 5 saniye düşün ve o ana kadar bulduğun en iyi sonucu ver").

**Dezavantajları:**
- Sistemin nasıl böldüğü konusunda kontrolümüz olmaz (Tamamen OR-Tools inisiyatifi).

---

## Seçenek 4: Dinamik Uzay Bölme (Quad-Tree / Geofencing)
*Büyük Ölçekli Parçalama*

**Nasıl Çalışır?**
N ≥ 300 olduğunda harita sabit coğrafi bölgelere (Kuzeybatı Kampüs, Güney Lojmanlar vb.) veya Quad-Tree ile 4 ana hücreye bölünür.
Her hücre **kendi içinde** bağımsız bir VRP problemi olarak (örneğin 300/4 = hücre başı 75 kişi) ele alınır ve farklı thread'lerde paralelde optimize edilir.

**Avantajları:**
- Sistem sonsuz ölçeklenebilir (N büyüdükçe bölge sayısı artırılır).
- Kesişim sıfırdır.
**Uygulama Zorluğu:** Yüksek. (Şu aşamada UniRide için "Over-engineering" olabilir).

---

## Sonuç ve Öneri

Kullanıcının *"uzak noktaların boşuna denenmesini istemiyorum"* ve *"eksponansiyel patlamayı önlemek istiyorum"* amaçları **kesinlikle doğru bir sistem mimarisi refleksidir.**

Şu anki "K-Means + Araç Sayısını Artır" döngüsü bu amaca tam hizmet edememektedir çünkü K-Means zaman sınırını umursamaz.

**Önerilen Yol:**
1. Projede hali hazırda entegre edilen **Clarke-Wright Savings** veya **Sweep** mantığını, K-Means'in yerine "Divide and Conquer" motoru olarak geçirmek. 
2. Bu sayede N=300 olsa bile, Savings algoritması öğrencileri zaman sınırını asla aşmayacak **"katı olmayan, trafiğe/zamana duyarlı"** 15-20 kişilik alt kümelere milisaniyeler içinde bölecektir.
3. GA, PSO, veya Optimal (TSP) çözücüler, sadece bu 15-20 kişilik küçük (ve zaten birbirine yakın) alt gruplar içinde çalıştırılacak ve patlama riski sıfıra inecektir.
