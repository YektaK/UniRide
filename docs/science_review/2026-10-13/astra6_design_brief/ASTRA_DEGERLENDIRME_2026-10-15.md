# Astra 6 tasarım belgelerinin akademik ve teknik değerlendirmesi

Tarih: 2026-10-15. Değerlendirilen belgeler:
- **A:** [ASTRA6_YENI_ALGORITMA_TASARIMLARI.md](ASTRA6_YENI_ALGORITMA_TASARIMLARI.md) — 7 algoritma kartı (A1–A7), deney planı, yol haritası.
- **B:** [CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14.md](CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14.md) — ERPL-Split, öğrenilmiş rota örüntüleri.

Karşılaştırma kaynakları: [görev tanımı](00_PROMPT_ASTRA6_YENI_ALGORITMA_TASARIMI.md) (P1–P8 sözleşmeleri), ölçülmüş geliştirme sonuçları (Claude Science artefaktı `ALGORITHM_DEVELOPMENT_RESULTS_2026-10-14.md`), TSP hattı raporu (Claude Science artefaktı `TSP_FAST_LS_REPORT.md`), [eski üçlü değerlendirmesi](01_SOTA_FAMILY_EVALUATION_2026-10-13.md), [yeniden tasarım planı](03_REDESIGN_WORK_PLAN_2026-10-13.md) (A'da "R1").

Bulguların tamamı: [astra_issues.csv](astra_issues.csv) (48 satır). Bu raporda satır numaraları "s." ile, belge içi bölüm numaraları "§" ile verilir.

**Yöntem.** Her iki belge baştan sona okundu. Matematiksel iddialar elle türetildi; sayım karşılaştırması kodla hesaplandı. Ölçümle karşılaştırma, ölçüm raporlarındaki sayılarla yapıldı; ölçümler yeniden koşturulmadı. Kaynak denetimi şöyle yapıldı:
- DOI'ler CrossRef API ile çözüldü.
- arXiv kimlikleri arXiv API ile kontrol edildi.
- DOI'siz makaleler arXiv başlık aramasıyla bulundu.
- Yazılım lisansları GitHub API ile kontrol edildi.

Depoda yalnız ana checkout'taki `uniride_core/algorithms/string_split_decoder.py` salt-okunur açıldı; depoda hiçbir değişiklik yapılmadı.

## 1. Özet

- 48 bulgu kaydedildi. Kategori dağılımı:
  - a-HATA: 4
  - b-ÇELİŞKİ: 4
  - c-ÖLÇÜMLE-ÇELİŞEN: 6
  - c-ÖLÇÜMLE-DESTEKLENEN: 11
  - d-DOĞRULANMAMIŞ: 4
  - e-GELİŞTİRİLEBİLİR: 19
- Ciddiyet dağılımı: yüksek 7, orta 25, düşük 16.
- **Kaynak denetimi temiz.** Uydurma ya da yanlış eşleşen kaynak bulunmadı:
  - 32 CrossRef DOI'sinin 32'si çözüldü; başlık, yazar ve yıl iddiayla tutarlı.
  - 7 arXiv kimliğinin 7'si doğrulandı.
  - DOI'siz 5 NeurIPS/ICLR makalesinin 5'i doğrulandı.
  - Künye düzeyinde 4 küçük kusur var: bir başlık çevirisi, bir yanlış atıf, eksik iki DOI ve fazla temkinli bir tür etiketi.
- **Matematik büyük ölçüde doğru.** P5 segment formülleri, metrik olmayan matriste erken kesme uyarısı, entropi normalizasyonu, LAHC/SA kalibrasyonu ve B'nin olasılık modelleri sınandı ve doğru çıktı. Hatalar başka yerlerde:
  - A'daki 'tam sayım faktöriyel' karmaşıklık iddiası yanıltıcı;
  - B'deki örnekleme karmaşıklığı eksik yazılmış: O(n²) değil, O(n² log n);
  - A'da bir karmaşıklık bilgisi yanlış kaynağa (R1) atfedilmiş.
- **Astra'nın yön öngörüleri ölçümle büyük ölçüde doğrulandı.** Doğrulananlar: kesin dalga referansı, sözlüksel aşamalı master, kısıtlı havuz kanıt sınırı ve gün düzeyi ortak seçimin filoyu düşürmesi.
- **Ancak birincil önerilerin biçimi ölçümlerin gerisinde kaldı.** Bugünkü ölçekte (dalga başına ≤20 yolcu) kesin yöntemler optimumu veriyor. A4'ün çoklu üretici/kısıtlı havuz yapısı ve A5'in LNS + z_rv modeli bu ölçek için gereğinden karmaşık.
- **TSP birincil önerisi A1 zayıfladı.** GPX katkısı ölçülemedi; birincil öneri ILS-fast olmalı.
- **Belge B'nin ilk deney hedefi yanlış seçilmiş.** P5 dalgalarında kapatılacak optimum açığı yok. Önce/sonra (M2/M3) kolu, en fazla 9 yolculuk rotalarda kesin DP ile anlamsızlaşıyor.

## 2. En önemli 10 bulgu

1. **B'nin hedef problemi boş (B-01, yüksek).** ERPL-Split'in ilk deneyi bugünkü P5 dalgalarına konmuş. Oysa 228/228 dalga kanıtlı optimumla çözülüyor (medyan 0,014 s/dalga) ve GA-Split 209/228 dalgada zaten optimal. M0–M3 kolları en iyi durumda eşit çıkar; deney bilgi üretmez. Hedef, yoğun sentetik dalgalar (S3: 76–108 yolculuk) ve P8 olmalı.
2. **A4 sadeleşmeli: dalgada eksiksiz kesin sayım yeterli (A-07, A-04).** n≲20–22 için alt küme DP + iki aşamalı sözlüksel küme bölümleme (WAVE-EXACT) tüm dalgaları kanıtla çözüyor; GA tanığı, çoklu üretici ve kısıtlı havuza gerek yok. A'nın 'tam sayım faktöriyel' ifadesi yanıltıcı: rota alt kümeye bağlı. n=20, L=9 için sıralı dizi sayısı 6,6·10¹⁰, alt küme sayısı 431 909 (oran 1,5·10⁵).
3. **A5'in yönü doğru, formülasyonu değil (A-10, A-12, A-13, A-14).** Ortak gün modeli haftalık filoyu R=60/70'te 6'dan 5'e, tipli senaryoda sedanı 4/3/3'ten 3/2/2'ye indirdi. Ancak varsayılan olarak önerilen z_rv modeli ölçeklenmez: ikili çakışma kısıtları O(M²), 45 bin kolonlu bir dalgada ~10⁹ mertebesinde. Doğru varsayılan olay-noktası eşzamanlılık modeli artı rotalamadan bağımsız alt sınır LB0; LNS ölçek profili olarak ertelenmeli.
4. **A1 (GPX2) TSP birincil önerisi olmamalı (A-01, A-02).** Basit GPX'in katkısı yok (p=0,776) ve havuz çeşitliliğini %24–55 düşürüyor. Birincil öneri ILS-fast + kesin FE muhasebesi + K=16–20 olmalı; K=10 kalite ölçütünü sağlamadı. GPX2, n≥5000 örneklerde ertelenmiş bir ablasyon olarak kalmalı.
5. **Metrik olmayan matriste kesin budama mümkün (A-05).** A, toplamada R ihlalinde uzatmanın kesilemeyeceğini söylüyor; bu yalnız ileri uzatma için doğru. Rota depodan geriye kurulursa ilk yolcunun yolculuk süresi monoton artar ve R budaması kesinleşir. Split'te tarama yönü (toplamada i geriye, bırakmada j ileri) aynı nedenle güvenli kırılma verir.
6. **Baskınlık ve simetri kuralları eksik (A-06, A-28, B-05).** P7'nin aralık sözleşmesinde, aynı (alt küme, tip) içinde daha kısa olurlu sıra hem dalga hem gün amacı için baskındır. Dolayısıyla A'nın 'gün için değerli daha uzun rota' çekincesi bu durumda geçersiz. Ayrıca aynı durak ve aynı tipteki occurrence'lar ayırt edilemez: A4'te çokluk-küme sayımı, B'de tekilleştirme ve H birikimi buna göre kurulmalı.
7. **B'nin önce/sonra kolu (M2/M3) P5'te anlamsız (B-02, B-03).** Rota en çok 9 yolcu taşıyor; rota içi sıralama Held–Karp ile ≈4·10⁴ işlemde kesin çözülür. Ek olarak sonlanma ölçütü ('M(s) boşsa') iyi tanımlı değil, ve en-iyi-iyileşme yerel aramada deneme sırası sonucu değiştirmez.
8. **ATSP ve lisans açık soruları kapandı (A-17, A-19).** elkai ATSP'yi kendiliğinden TYPE: ATSP olarak çözüyor; 2n dönüşümü ön koşulu gereksiz. elkai'nin LICENSE dosyası LKH kısıtları nedeniyle yalnız akademik ve ticari olmayan kullanıma izin veriyor; ticari üretim yolunda kullanılamaz.
9. **A'da belge içi öncelik çelişkisi var (A-16).** §8 üretimde A4→A5 önceliğini öneriyor; §7.2'deki ilk iki hafta ise TSP altyapısına (C0-b, D1, GPX2, D2) ayrılmış. Ölçümler üretim kazancının gün düzeyinde olduğunu gösteriyor; takvim buna göre çevrilmeli.
10. **A'nın güvenlik kuralları ölçümle güçlü biçimde doğrulandı (A-08, A-09).** Tek ağırlıklı amaç iki büyük dalgada 600 s'de kanıt üretemedi; iki aşamalı sözlüksel çözüm aynı dalgaları 1,4 s ve 28,3 s'de kanıtladı. GA menüsüne koşullu 'olursuz' etiketli 3 hücre ise tüm rotalar üzerinde olurlu çıktı. Bu iki kural korunmalı.

## 3. Önceliklendirme: Astra'nın birincil önerileri hâlâ doğru mu?

| Düzey | Astra'nın birincil önerisi | Ölçülmüş durum | Değerlendirme | Önerilen birincil |
|---|---|---|---|---|
| TSP (P1/P2) | A1 Candidate Partition ILS (GPX2) | ILS-fast: 30 s'de 36/50 optimum, ortalama açık %0,058; deponun ILS'i: 15/40 optimum, %2,02. Basit GPX katkısız. LKH 50/50 optimum. ATSP ft53'te 10/10. | Yön (hızlı yerel arama + kontrol kolu) doğru; GPX2'yi birincil yapmak doğru değil. Üretim değeri düşük (istem §10 ile uyumlu). | ILS-fast + FE muhasebesi (catalog gate); A2 yönlü modu ile birleşik. GPX2/A7 ertelenir. |
| Dalga (P5/P6) | A4 Certified Route Pool | WAVE-EXACT 228/228 kanıtlı optimum; GA 19 dalgada suboptimal (hepsi ≥6 yolcu). | Yön doğru (eksiksiz sayım + lex SP); biçim gereğinden karmaşık. | WAVE-EXACT (alt küme DP + iki aşamalı lex SP), n≲20–22; üstünde kısıtlı havuz/ESN-SP. |
| Gün (P7) | A5 Anchored Day Route-Pool LNS | DAY-JOINT: haftalık filo R=60/70'te 6→5, 11/20 hücrede −1 araç; DAY-TYPED: sedan 4/3/3→3/2/2. | En yüksek üretim değeri doğru tespit edilmiş; LNS ve z_rv bu ölçekte gereksiz. | DAY-JOINT/DAY-TYPED kesin model (olay-noktası eşzamanlılık + LB0). Politika kararı sahibe: filo öncelikli mi, rota öncelikli mi? |
| P8 | A6 Paired-request SISR/ALNS | Veri ve kod yok. ESN-SP yoğun örneklerde zayıf; giant-tour + Split havuzu daha iyi. | Yön makul; P5 profili gereksiz; DARP denetleyicisi literatüre dayanmalı. | Önce gerçekçi P8 sentetik üreteci + yerleşik DARP rota değerlendirmesi; sonra A6/A3 karşılaştırması. |

**Önerilen sıra:**
1. WAVE-EXACT ve DAY-JOINT/TYPED'i sertifika ve sözleşme testleriyle `uniride_core`'a almak, ardından sahibin filo politikası kararı.
2. ILS-fast için FE muhasebesi ve TSPLIB ATSP ithalatı.
3. P8 üreteci ve DARP denetleyicisi.
4. Yoğun ölçekte A3 ve ERPL (kolon üreteci olarak).
5. GPX2/A7.

## 4. Belge A: bulgular

### 4.1 Matematik ve algoritma mantığı denetimi

| İddia (yer) | Sonuç | Gerekçe |
|---|---|---|
| P5 segment formülleri: Cij=c(D,vi)+Pij+c(vj,D); toplamada en uzun yolculuk Pij+c(vj,D); bırakmada c(D,vi)+Pij (§4.0, s.115) | ✓ doğru | P5 tanımıyla birebir uyumlu (toplama: ilk binen yolcudan depoya; bırakma: depodan son inen yolcuya). Depo Split'i de aynı formülü kullanıyor (string_split_decoder.py s.361–366). |
| Sabit i için Sw/So aşımı ve bırakma yolculuğu monoton; C ve toplama yolculuğu azalabilir; ilk ihlalde kesmek yanlış (s.117) | ✓ ileri uzatma için doğru; eksik | Negatif olmayan yaylarla doğru. Ancak geriye kurulumda toplama R'si monotondur ve kesin budama mümkündür (A-05). |
| Prefix güvenli alt sınır; doğrudan depo yayı değil (s.117) | ✓ | c(vj,D) ≥ 0 olduğundan c(D,vi)+Pij ≤ Cij. |
| Homojen Split O(nL); tipli + tek kota O(hQnL) (s.115, 238) | ✓ | O(1) segment testiyle DAG üzerinde Bellman; kota sayacı durum katsayısı. |
| Entropi normalizasyonu H_norm=(H−log n)/log(U/n), U=min(mn, M_edges) (s.109) | ✓ | Her turda n farklı kenar olduğundan H ≥ log n; eşitlik yalnız özdeş popülasyonda. H ≤ log U, dolayısıyla değer [0,1] aralığında. 1'in her zaman erişilemeyeceği de doğru belirtilmiş. |
| d(A,B)=1−|E(A)∩E(B)|/n; P1'de rotasyon/ters, P2'de yalnız rotasyon değişmez (s.107) | ✓ | Yönsüz/yönlü kenar kümeleri gösterimden bağımsız. |
| SA: T0=−median(Δ+)/ln p0 (s.111) | ✓ | exp(−Δ/T0)=p0 çözümü; medyan için tasarım kuralı olduğu doğru vurgulanmış. |
| Sade LAHC: geçmiş başlangıç maliyetiyle dolar; aday ≤ mevcut ya da ≤ geçmiş ise kabul; slot güncellenir; kabul oranının monoton düşmesi şart değil (s.111, 630) | ✓ | Burke & Bykov ailesiyle uyumlu; R1'in 'kabul oranı düşüyor' testinin teorem olmadığı itirazı haklı. |
| 'Tam sayım genel durumda faktöriyel; Σ n!/(n−l)!' (s.287) | ✗ yanıltıcı | Rota kolonu alt kümeye bağlı; Held–Karp alt küme DP kesin. n=20, L=9: 6,6·10¹⁰ sıralı dizi ve 431 909 alt küme (A-04). |
| SP NP-hard; '20 küçük olduğundan kolay' varsayımı yok (s.287) | ✓ genel olarak; ölçümde kolay | İki aşamalı lex SP büyük dalgalarda 1,4 s ve 28,3 s'de kanıtladı (A-08). |
| Lex ilk aşama kapatılmadan global lex ispatı yok (s.299) | ✓ | Ölçümle güçlü biçimde destekleniyor (A-08). |
| Kısıtlı havuz optimumu/olursuzluğu global değil (s.326) | ✓ | Ölçümde 3 'olursuz' hücre olurlu çıktı (A-09). |
| A5: O(MV) değişken, O(M²) ikili çakışma, O(VM²) (s.339) | ✓ aritmetik; ✗ ölçeklenebilirlik | Olay-noktası (clique) kısıtları kolon başına O(olay sayısı) (A-12). |
| A5: sonraki başlangıç ≥ önceki bitiş + soğuma; eşitlik uygun (s.349) | ✓ | P7 ile uyumlu; ölçüm harness'i yarı açık [·,·+10) aralıklarıyla arşiv filosunu 20/20 aynı üretti. |
| A6: Bellman–Ford fark-kısıtı denetimi O(L²); naive insertion O(L⁴) (s.400, 412) | ✓ aritmetik; literatür eksik | Yerleşik DARP rota değerlendirmesi anılmıyor (A-21). |
| A2: sabit uzunluklu yön koruyan Or-opt deltası O(1); iki adaylı or-3opt O(nK²) (s.190) | ✓ | Segment yönü korunduğu için iç yaylar değişmez; TSP raporunda ATSP'de ters çevirme sayacı 0 ve her hamlede ≤3 yeni yay ölçüldü. |
| A1: GPX2 R6 koşullarında O(n) (s.143) | künye ✓; içerik bu denetimde açılmadı | Basit GPX'in 'çocuk ≤ en iyi ebeveyn, ortak kenarlar %100' sözleşmesi ölçümde geçti (TSP raporu C7). |
| FE aşımı 0; yalnız süre ≤%5 (s.16, 101, 629) | ✓ (istemden daha sıkı, gerekçeli) | İstem §6.4 '%5 aşım' diyor; A bunu FE için 0, süre için %5 diye ayırıyor ve farkı açıkça belirtiyor. Çelişki değil, bilinçli sıkılaştırma. |

### 4.2 P5/P7 sözleşmesine uyum (kart bazında)

| Kart | Yöne özgü yolculuk süresi | Sw/So ayrı | T tüm yaylar | Metrik olmayan matris | Sözlüksel amaç | Not |
|---|---|---|---|---|---|---|
| A1 | — (yalnız P1) | — | — | Simetrik kimlik; ATSP'yi reddeder | — | Üretim örneğini reddetmesi doğru |
| A2 | — (rota içi LS olarak decoder altında) | — | — | ✓ yön korunur; ters yay yedeği yok | — | ✓ |
| A3 | ✓ (§4.0 formülleri) | ✓ ayrı ceza | ✓ | ✓ kör kırılma yok | ✓ rota→süre; P6 ödünç tip→süre | Ceza ölçeği lex önceliği bozabilir (A kendisi belirtiyor) |
| A4 | ✓ | ✓ sert | ✓ | ✓; ama budama gereğinden temkinli (A-05) | ✓ iki aşama | Baskınlık ve simetri eksik (A-06, A-28) |
| A5 | ✓ (kolon süresi yönlü matristen) | ✓ | ✓ | ✓ | P7 tuple'ından farklı iki profil; fark açıkça yazılmış | Formülasyon ölçeklenmez (A-12) |
| A6 | ✓ (P5 profili); P8 ayrı | ✓ | ✓ | ✓ | ✓ | P8 denetleyicisi literatüre dayanmalı (A-21) |
| A7 | — | — | — | P2'ye aktarım yasak | — | ✓ |

### 4.3 Ölçülmüş sonuçlarla karşılaştırma

| A'nın öngörüsü | Ölçüm | Durum |
|---|---|---|
| A4: kesin referansa göre lex iyileşme 'orta'; tam sayım küçük örneklerde kesin referans | 228/228 optimum; GA 19 dalgada geride (4 fazla rota, 15 daha uzun) | Destekleniyor (A-03) |
| A4/§8: 2–20 boyutta tam sayım her zaman kolay değil; faktöriyel | n=20'de ≈9 s, ≈100 MB; sınır ≈22–25 yolcu | Arşiv ölçeğinde çelişiyor (A-04) |
| A4: lex aşamaları ayrı kapatılmalı | Ağırlıklı amaç 600 s'de kanıtsız; iki aşama 1,4 s ve 28,3 s | Güçlü destek (A-08) |
| A4: kısıtlı havuz olursuzluğu kanıt değil | 3 'olursuz' hücre olurlu | Destek (A-09) |
| A5: ortak seçim filo tuple'ını iyileştirir 'orta' | Haftalık filo 6→5 (R=60/70); 11/20 hücre −1; sedan 4/3/3→3/2/2 | Destek (A-10) |
| A5: tam ortak gün referansı yok, yaklaşma 'düşük' | 19/20 hücre MIP ile, 1 hücre LB0 ile kanıtlı | Güncelliğini yitirdi (A-11) |
| A5: z_rv varsayılan; interval coloring ikincil | Olay-noktası eşzamanlılık modeli yeterli ve kesin | Çelişiyor (A-12) |
| A1: GPX2 katkısı 'orta' | Basit GPX p=0,776; çeşitlilik −%24–55 | Zayıflattı (A-01) |
| G0: K=8–10 | K=10 kalite ölçütünü sağlamadı; K=20 kapattı | Çelişiyor (A-02) |
| A2/§8: 2n dönüşümü ve elkai erişimi açık | elkai doğal ATSP; 2n ile de 6905 | Açık soru kapandı (A-17) |
| A6: büyük P5 dalgalarında LNS 'orta' | ESN-SP v2 yoğun S3'te 0/5; GA temsili daha iyi | Dolaylı çelişki (A-22) |
| A1 riskleri: DLB tam tükenme garantisi değil | K=n−1 kaba kuvvet Or-opt 2–3 iyileştirme buldu | Destek (A-29) |

### 4.4 Diğer önemli A bulguları

- **A-05** (e-GELİŞTİRİLEBİLİR, orta; §4.0 P5 segment hesabı (s.117); §4.4 Yönlü/metrik olmayan (s.288); §4.3 Karmaşıklık (s.238)): Toplamada R ve kapalı süre ihlalinde uzatma kesilemez (metrik olmayan matris). → Enumerator ve özel P5 Split'e yöne göre tarama yönü kuralı ekle; sözleşme testi: ileri/geri taramanın aynı segment kümesini vermesi.
- **A-06** (e-GELİŞTİRİLEBİLİR, orta; §4.4 Temsil (s.284), Yönlü (s.288); §4.5 bileşen tablosu dominance (s.385)): Kolon sıra ile anahtarlanır; baskın kolon eleme kısıtlı; 'gün için değerli daha uzun rotayı kör eleme yok'. → (alt küme, tip) → en kısa olurlu sıra baskınlığını kanıtlı kural yap; koşulları yaz (tip başına aynı matris, sabit çapa, servis günü penceresi yalnız başlangıç alt sınırı).
- **A-07** (e-GELİŞTİRİLEBİLİR, yüksek; §4.4 A4 Bütçe, sözde kod, bileşen tablosu (s.286, 304–316, 321)): A4: GA tanığı + çoklu üretici + kısıtlı havuz + native-only zaman zarfı; tam sayım yalnız 'yeterince küçük' örneklerde. → Dalga birincil öneri: WAVE-EXACT (alt küme DP + iki aşamalı lex SP), n≲20–22; kısıtlı havuz/çoklu üretici ve GA tanığı yalnız üstü için profil.
- **A-12** (e-GELİŞTİRİLEBİLİR, yüksek; §4.5 Gün master formülasyonu (s.349), Karmaşıklık (s.339), sadeleştirme notu (s.360)): Varsayılan açık z_rv atama modeli; ikili çakışma z_rv+z_sv≤1, O(M²)/O(VM²); interval coloring yalnız ikincil seçenek. → Varsayılanı tersine çevir: olay-noktası eşzamanlılık modeli (tip başına); z_rv yalnız araç-özel availability, sürücü, çok depo veya deadhead varsa.
- **A-13** (e-GELİŞTİRİLEBİLİR, orta; §4.5 sözde kod ve kritik-dalga LNS (s.364–378, 384)): Gün birincil önerisi kritik-dalga LNS + kolon zenginleştirme. → Gün birincil: DAY-JOINT/DAY-TYPED kesin model; LNS'i ölçek profili olarak ertele ve kesin referansa karşı ölç.
- **A-14** (e-GELİŞTİRİLEBİLİR, orta; §4.5 Lex ve kanıt yönetimi (s.386): eksik bileşen): Gün master'ında yalnız restricted-pool sınırı uyarısı var; rotalamadan bağımsız alt sınır tanımlı değil. → LB0'ı A5'in kanıt etiketlerine ve erken durdurma ölçütüne ekle.
- **A-16** (b-ÇELİŞKİ, orta; §7.2 İlk iki hafta (s.612–621) ↔ §8 öncelik (s.639)): §8 üretimde A4→A5 önceliği önerir; §7.2'nin iki haftası TSP altyapısına (C0-b, D1, GPX2, D2/H1) ayrılmış, A4/P7 yalnız 'tasarım düzeyinde sabitle'. → İlk iki haftayı WAVE-EXACT + DAY-JOINT/TYPED'in sertifikalı olarak uniride_core'a alınmasına ayır; TSP hattını paralel/düşük öncelik yap.
- **A-19** (d-DOĞRULANMAMIŞ, orta; §2.1 LKH/elkai (s.66); §8 (s.643)): 'LKH-3'ün seçilecek dağıtımının lisansı DOĞRULANMADI'. → elkai/LKH yalnız akademik referans; ticari üretim yolunda kullanılamaz. Sahip kararlarına ekle.
- **A-21** (e-GELİŞTİRİLEBİLİR, orta; §4.6 A6 O(1) sınırı ve kesin kontrol (s.410–412); §2 kaynak tablosu): P8 için kendi Bellman–Ford fark-kısıtı denetleyicisi O(L²); naive insertion O(L⁴)/rota/talep. → Yerleşik DARP rota değerlendirmesini oracle/başlangıç denetleyici yap; kendi BF tasarımını yalnız buna karşı parite testiyle kullan.
- **A-23** (e-GELİŞTİRİLEBİLİR, orta; §6.4 A4 ablasyonu (s.569); §6.1 P5/P6 (s.531)): Dalga ablasyonlarında birim tüm dalgalar. → Dalga boyutuna göre tabakala; ≥6 yolculuk alt kümesi ve büyüyen sentetik aileler birincil test birimi olsun.
- **A-27** (e-GELİŞTİRİLEBİLİR, orta; §4.3 A3 performans hipotezi ve öncelik (s.242, 515)): A3: ga_split/ga_split_hf'ye göre daha iyi lex çözüm 'orta'; P5/P6 dalga dahil. → P3/P4 akademik ve yoğun P5/P8 ölçeği için koru; üretim P5/P6 önceliğinden çıkar (ertele).
- **A-28** (e-GELİŞTİRİLEBİLİR, orta; §4.4 Temsil: aynı yerden farklı yolcular ayrı satır (s.284); §4.0 Gösterimler (s.95)): Occurrence kimliği korunur; aynı duraktaki yolcular ayrı kapsama satırı. → Enumerator'da (durak, tip) çokluk-kümesi sayımı; kimlik ataması yalnız sertifika aşamasında.

## 5. Belge B: bulgular

### 5.1 Matematik denetimi

| İddia (yer) | Sonuç | Gerekçe |
|---|---|---|
| h(i,j)=[α h₀+Σ I_s]/(α+m), h₀=1; E boşken 1 (§4.3, s.103) | ✓ | Σ I_s ≤ m olduğundan h ∈ [α/(α+m), 1]; log h ≤ 0 ve tanımlı. Softmax yalnız oranları kullanır: tüm elitlerde görülen/hiç görülmeyen oranı (α+m)/α. |
| p(i≺j)=[α/2+B]/[α+A]; p(i≺j)+p(j≺i)=1 (s.111–113) | ✓ | B(i,j)+B(j,i)=A(i,j) tekrarsız rotalarda geçerli. |
| §3.2 döngülü çoğunluk örneği (s.69–75) | ✓ | A≺B, B≺C, C≺A her biri 3 sıranın 2'sinde doğru; sert kısıta çevrilemez. |
| Pr(j|i,U)=(1−ε)softmax + ε/|U|; her üye ≥ ε/|U| (s.125) | ✓ | Toplam 1; keşif tabanı tam U üzerinde. |
| §5.1 metrik olmayan karşı örnek: D–A–D=11, D–A–B–D=3, T=5 (s.219–224) | ✓ | Aritmetik doğru; toplamada A'dan depoya süre 10'dan 2'ye iniyor. |
| P5 üç formül (s.228–232) | ✓ | A §4.0 ve depo Split'iyle aynı. |
| G(s) normalizasyonu; üyelik değiştirmeyen relocate (s.143–145) | ✓ | Aynı-rota çift sayısı sabit kaldığından ΔG tutarlı. |
| Sonlanma: 'M(s) boşsa yerel arama biter' (s.145) | ✗ iyi tanımlı değil | B-03. |
| 'Tam aday örnekleme O(n²)' (s.357) | ✗ eksik | Sıra hesabı yüzünden O(n² log n) (B-04). |
| Giant-tour yapay bağlantısı etiket üretmez (s.117) | ✓ | Rota sınırı doğru korunuyor. |

### 5.2 Ölçümle ve A ile karşılaştırma

- **B-01** (c-ÖLÇÜMLE-ÇELİŞEN, yüksek): ERPL-Split'in ilk hedefi ve ilk deneyi bugünkü P5 dalgası. — Kanıt: 228/228 dalga kanıtlı optimum (medyan 0,014 s/dalga); GA-Split 209/228 dalgada zaten optimal. Öğrenmenin kapatacağı açık yok; M0–M3 farkları en iyi durumda sıfır; deney bilgi üretmez. → **Öneri:** Hedefi yoğun/büyük sentetik dalgalara (S3: 76–108 yolculuk) ve P8'e taşı; WAVE-EXACT'i küçük örneklerde oracle olarak kullan.
- **B-02** (e-GELİŞTİRİLEBİLİR, yüksek): Önce/sonra bilgisi aynı rota içi relocate hamlelerinin deneme sırasını yönlendirir. — Kanıt: P5 rotası en çok 9 yolcu (4 Sw + 5 So); rota içi sıralama Held–Karp ile 2^9·9² ≈ 4,1·10^4 işlemde kesin çözülür (R, geriye kurulumla kesin budanır). Deneme sırası öğrenmesinin bu ölçekte kazanacağı bir şey yok. → **Öneri:** P5'te M2/M3'ü ele, rota içi kesin DP kullan; önce/sonra fikrini yalnız uzun rotalı P8/PDP'de yeniden değerlendir.
- **B-05** (e-GELİŞTİRİLEBİLİR, orta): Aynı durağın occurrence'ları ayrı düğüm; eşdeğer çözümler tekilleştirilir. — Kanıt: P5'te aynı durak/aynı tip occurrence'lar kısıtlar bakımından ayırt edilemez, aralarındaki yay 0. k özdeş occurrence k! eşdeğer etiketleme üretir: H kütlesi simetrik eşdeğerlere dağılır, tekilleştirme bunları ayrı çözüm sayar, arşiv çeşitliliği yapay şişer. Ölçek testi S3 bu durumu üretir. → **Öneri:** Eşdeğerlik sınıfına özdeş occurrence permütasyonunu ekle; H'yi (durak, tip) düzeyinde topla.
- **B-06** (e-GELİŞTİRİLEBİLİR, orta): Doğrudan karşılıklar: EHBSA, CE/EDA, ACO, NeuroLKH, okul servisi EDA. — Kanıt: Yerel optimumlardan dinamik 'backbone' kenar bilgisi çıkarıp LKH kenar kalitesini yönlendiren Wang vd. 2025 (arXiv:2501.04072; özet okundu; A'da R24) ve LKH backbone/tour-merging bileşenleri (A'da R5) ERPL'in TSP koluna en yakın öncüller; B'de yok. → **Öneri:** Yenilik tartışmasına ve TSP kontrol kollarına backbone güdümlü aday seçimini ekle.
- **B-07** (e-GELİŞTİRİLEBİLİR, orta): Problem özelliklerinden örnekler arası kenar modeli; gerekirse MatNet/RRNCO türü ağ. — Kanıt: Mevcut üretim verisi tek hafta: 226 yolcu ayağı, 228 dalga, gün başına bir matris, 29 konum. Grup bazlı bölmeyle eğitim/test için birkaç gün kalır. Optimum etiketler WAVE-EXACT ile üretilebilir ama dağılım çeşitliliği yok. → **Öneri:** Aşama 3'ü çok haftalık veri ya da gerçekçi sentetik üretici hazır olana dek ertele.
- **B-08** (b-ÇELİŞKİ, orta): B öğrenilmiş kenar tercihleri ve sonraki aşamada sinir ağı öneriyor. — Kanıt: A'nın D6 kararı: öğrenilmiş adaylar ilk sürümden çıkar; eğitim maliyeti ve OOD nonmetric test olmadan learned candidate önerilmez; NN geliştirme görevi açılmaz. B 'önceki tasarımlar değiştirilmedi' der ama bu kararla uzlaştırma yapmaz. → **Öneri:** B'ye D6 ile ilişki notu ekle: aşama 1 (aynı örnek, çevrimiçi) D6 kapsamı dışında; aşama 3 ancak D6 koşulları sağlanınca.
- **B-09** (b-ÇELİŞKİ, orta): ERPL ayrı deney; A4 havuzuna kolon üretebilir veya A3 kurucusu olabilir. — Kanıt: A, P5 için A4'ü birincil önerir; B aynı düzeyde ilk deneyini P5'e koyar, ama A4/A5'e göre önceliğini belirtmez. → **Öneri:** B'yi A4/A5 (kesin dalga ve gün) sonrasına, ölçek profili ve kolon üreteci olarak sırala.
- **B-10** (d-DOĞRULANMAMIŞ, düşük): 'Split'in kendisinde aynı güvensiz kırılma varsa sorun devam eder; decoder uyumu kontrol kapısıdır'. — Kanıt: Ana checkout uniride_core/algorithms/string_split_decoder.py, _build_trips: kapasite aşımında ve eksik yayda break (monoton/güvenli); T ve R ihlalinde continue (s.345–366). TW modunda da T/R için continue (s.449–458). Güvensiz kırılma yok. (Yalnız bu dosya okundu.) → **Öneri:** Kapıyı 'koddan doğrulandı (ana checkout, 2026-10-15)' olarak işaretle; bırakmada c(D,vi)+Pij>T için güvenli break verim için eklenebilir.
- **B-14** (c-ÖLÇÜMLE-DESTEKLENEN, orta): Giant-tour + Split ile örneklenen sıralar; A4 havuzuna kolon üretebilir. — Kanıt: Ölçek testinde yoğun örneklerde giant-tour + Split (GA) temsili, kesin sayım komşuluklarından daha iyi rota yapısı buldu; GA rotalarını havuza katan ESN-SP v3 S3'te eşit süreli GA'ya 3/5 önde. Yoğun rejimde giant-tour tabanlı çeşitli kolon üretimi değerli. → **Öneri:** ERPL'i yoğun rejimde ESN-SP/A4 havuzu için kolon üreteci olarak konumlandır; kontrol: çok tohumlu GA kolonları.

**B'nin güçlü yanları (koru):**
- Gerçek maliyet c ile öğrenilmiş tercih h ayrı tutuluyor.
- Öğrenilmiş çoğunluklardan sert kısıt üretilmiyor.
- TSP kolunda önce/sonra modeli kapalı.
- Farklı araçtaki çiftler eksik etiket sayılıyor.
- H birikimli değil, arşivden yeniden hesaplanıyor.
- Grup bazlı veri bölmesi ve eğitim maliyetinin bütçeye dahil edilmesi öngörülmüş.

## 6. Kart bazında karar tablosu

| Kart / öneri | Karar | Gerekçe (bulgu kimlikleri) |
|---|---|---|
| A1 CPILS (TSP) | **değiştir** | Birincil öneri ILS-fast + FE ledger + K=16–20 olsun; GPX2 n≥5000'de ertelenmiş modül (A-01, A-02, A-32) |
| A2 DCILS (ATSP) | **koru** | ILS-fast yönlü moduyla birleştir; referans elkai doğal ATSP; ATSP veri kümesi gerekli (A-17, A-18, A-31) |
| A3 VHGS-Split | **ertele (üretim P5/P6) / koru (P3–P4, yoğun ölçek)** | Bugünkü dalgalar kesin çözülüyor; yoğun ölçekte giant-tour+Split avantajı ölçüldü (A-27) |
| A4 CRP (dalga) | **değiştir** | WAVE-EXACT: alt küme DP + iki aşamalı lex SP; baskınlık ve simetri kuralları; havuz/üreticiler yalnız n≳22 (A-03…A-09, A-23, A-28) |
| A5 ADRPLNS (gün) | **değiştir** | DAY-JOINT/TYPED olay-noktası modeli + LB0 birincil; LNS ölçek profili; filo politikası sahibe (A-10…A-15) |
| A6 PRALNS (P5/P8) | **ertele** | P5 profili ele; P8 profili üreteç ve yerleşik DARP değerlendirmesiyle sonra (A-21, A-22) |
| A7 DCRM | **ertele** | GPX2 katkısı ve D2/H1 gösterilmeden efor yok (A-24) |
| BB-Merge (A kararı) | **ertele** | A ile aynı; ilk sürüm eforuna dahil değil |
| EAX-MA (referans) | **koru** | Referans kolu; GA-EAX MIT doğrulandı; ATSP desteği hâlâ açık |
| B ERPL-Split M0/M1 | **değiştir** | Hedefi yoğun/büyük dalgalar ve P8; A4/ESN-SP havuzu için kolon üreteci; küçük örneklerde WAVE-EXACT oracle (B-01, B-05, B-09, B-14) |
| B M2/M3 (önce/sonra) | **ele (P5)** | Rota içi kesin DP daha basit ve kesin; P8/PDP için yeniden değerlendirilebilir (B-02, B-03) |
| B aşama 3 (örnekler arası / NN) | **ertele** | Tek haftalık veri; A-D6 koşulları (B-07, B-08) |

## 7. Kaynak denetimi

**DOI'ler (CrossRef API, 32 benzersiz; A: 26, B: 6).** 32/32 çözüldü ve iddiayla eşleşti. Uydurma ya da yanlış eşleşen DOI yok.

| Belge | Kod | DOI | Belgedeki künye | CrossRef kaydı | Sonuç | Not |
|---|---|---|---|---|---|---|
| A | R5 | 10.1007/s12532-009-0004-6 | Helsgaun 2009, MPC 1:119–163 | General k-opt submoves for the Lin–Kernighan TSP heuristic — Helsgaun vd., 2009, Mathematical Programming Computation 1 (2-3) :119-163 | EŞLEŞTİ |  |
| A | R6 | 10.1162/evco_a_00254 | Tinós, Whitley, Ochoa 2020, EC 28(2):255–288 | A New Generalized Partition Crossover for the Traveling Salesman Problem: Tunneling between Loc — Tinós vd., 2020, Evolutionary Computation 28 (2) :255-288 | EŞLEŞTİ |  |
| A | R7 | 10.1287/ijoc.1120.0506 | Nagata & Kobayashi 2013, IJOC | A Powerful Genetic Algorithm Using Edge Assembly Crossover for the Traveling Salesman Problem — Nagata vd., 2013, INFORMS Journal on Computing 25 (2) :346-363 | EŞLEŞTİ | Cilt 25(2):346–363 (A cilt vermemiş) |
| A | R8 | 10.1287/opre.28.5.1086 | Kanellakis & Papadimitriou 1980, OR 28(5):1086–1099 | Local Search for the Asymmetric Traveling Salesman Problem — Kanellakis vd., 1980, Operations Research 28 (5) :1086-1099 | EŞLEŞTİ |  |
| A | R9 | 10.1016/j.eswa.2012.02.029 | Nagata & Soler 2012, ESWA 39(10):8947–8953 | A new genetic algorithm for the asymmetric traveling salesman problem — Nagata vd., 2012, Expert Systems with Applications 39 (10) :8947-8953 | EŞLEŞTİ |  |
| A | R10 | 10.1016/s0305-0548(03)00158-8 | Prins 2004, C&OR | A simple and effective evolutionary algorithm for the vehicle routing problem — Prins vd., 2004, Computers & Operations Research 31 (12) :1985-2002 | EŞLEŞTİ |  |
| A | R11 | 10.1287/opre.1120.1048 | Vidal, Crainic, Gendreau, Lahrichi, Rei 2012, OR | A Hybrid Genetic Algorithm for Multidepot and Periodic Vehicle Routing Problems — Vidal vd., 2012, Operations Research 60 (3) :611-624 | EŞLEŞTİ |  |
| A | R12 | 10.1016/j.ejor.2013.09.045 | Vidal, Crainic, Gendreau, Prins 2014, EJOR 234(3):658–673 | A unified solution framework for multi-attribute vehicle routing problems — Vidal vd., 2014, European Journal of Operational Research 234 (3) :658-673 | EŞLEŞTİ |  |
| A | R13 | 10.1016/j.cor.2021.105643 | Vidal 2022, C&OR 140:105643 | Hybrid genetic search for the CVRP: Open-source implementation and SWAP* neighborhood — Vidal vd., 2022, Computers & Operations Research 140 :105643 | EŞLEŞTİ |  |
| A | R14 | 10.1287/ijoc.2023.0055 | Wouda, Lan, Kool 2024, IJOC 36(4):943–955 | PyVRP: A High-Performance VRP Solver Package — Wouda vd., 2024, INFORMS Journal on Computing 36 (4) :943-955 | EŞLEŞTİ |  |
| A | R17 | 10.1287/trsc.2019.0914 | Christiaens & Vanden Berghe 2020, TS 54(2):417–433 | Slack Induction by String Removals for Vehicle Routing Problems — Christiaens vd., 2020, Transportation Science 54 (2) :417-433 | EŞLEŞTİ |  |
| A | R18 | 10.1287/trsc.1050.0135 | Ropke & Pisinger 2006, TS | An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time W — Ropke vd., 2006, Transportation Science 40 (4) :455-472 | EŞLEŞTİ |  |
| A | R19 | 10.1007/s10479-017-2642-9 | Penna, Subramanian, Ochi, Vidal, Prins (2017 çevrimiçi), AOR | A hybrid heuristic for a broad class of vehicle routing problems with heterogeneous fleet — Penna vd., 2019, Annals of Operations Research 273 (1-2) :5-74 | EŞLEŞTİ | Çevrimiçi 2017-11-09; basılı cilt 273 (2019) — A ifadesi tutarlı |
| A | R20 | 10.1016/j.orl.2010.11.004 | Firat & Woeginger 2011, ORL 39(1):32–35 | Analysis of the dial-a-ride problem of Hunsaker and Savelsbergh — Firat vd., 2011, Operations Research Letters 39 (1) :32-35 | EŞLEŞTİ |  |
| A | R21 | 10.1007/s10472-010-9213-y | Fialho, Da Costa, Schoenauer, Sebag 2010, AMAI 60:25–64 | Analyzing bandit-based adaptive operator selection mechanisms — Fialho vd., 2010, Annals of Mathematics and Artificial Intellig 60 (1-2) :25-64 | EŞLEŞTİ |  |
| A | R22 | 10.1145/3449639.3459281 | Varadarajan & Whitley 2021, GECCO | A parallel ensemble genetic algorithm for the traveling salesman problem — Varadarajan vd., 2021, Proceedings of the Genetic and Evolutionary C :636-643 | EŞLEŞTİ |  |
| A | R23 | 10.1145/3583131.3590399 | Pei, Tong, Liu, Mei, Yao 2023, GECCO | Local Optima Correlation Assisted Adaptive Operator Selection — Pei vd., 2023, Proceedings of the Genetic and Evolutionary C :339-347 | EŞLEŞTİ |  |
| A | R25 | 10.1016/j.ejor.2016.07.012 | Burke & Bykov 2017, EJOR 258(1):70–78 | The late acceptance Hill-Climbing heuristic — Burke vd., 2017, European Journal of Operational Research 258 (1) :70-78 | EŞLEŞTİ |  |
| A | R26 | 10.1016/j.orp.2016.09.002 | López-Ibáñez vd. 2016, ORP 3:43–58 | The irace package: Iterated racing for automatic algorithm configuration — López-Ibáñez vd., 2016, Operations Research Perspectives 3 :43-58 | EŞLEŞTİ |  |
| A | R27 | 10.1016/j.swevo.2011.02.002 | Derrac, García, Molina, Herrera 2011, SEC 1(1):3–18 | A practical tutorial on the use of nonparametric statistical tests as a methodology for compari — Derrac vd., 2011, Swarm and Evolutionary Computation 1 (1) :3-18 | EŞLEŞTİ |  |
| A | R28 | 10.1057/jors.2015.77 | Kendall vd. (13 yazar) 2016, JORS 67(4):676–689 | Good Laboratory Practice for optimization research — Kendall vd., 2016, Journal of the Operational Research Society 67 (4) :676-689 | EŞLEŞTİ |  |
| A | R29 | 10.1016/j.ejor.2013.06.012 | Cattaruzza, Absi, Feillet, Vidal 2014, EJOR 236(3):833–848 | A memetic algorithm for the Multi Trip Vehicle Routing Problem — Cattaruzza vd., 2014, European Journal of Operational Research 236 (3) :833-848 | EŞLEŞTİ |  |
| A | R31 | 10.1016/j.cor.2026.107443 | Ammann, Ostermann, Stiller, de Wolff 2026, C&OR | A speed-up for Helsgaun’s TSP heuristic by relaxing the positive gain criterion — Ammann vd., 2026, Computers & Operations Research 191 :107443 | EŞLEŞTİ |  |
| A | R32 | 10.1145/3712256.3726436 | Heins vd. ilgili ACM DOI | To Repair or Not to Repair? Investigating the Importance of AB-Cycles for the State-of-the-Art  — Heins vd., 2025, Proceedings of the Genetic and Evolutionary C :231-239 | EŞLEŞTİ | GECCO 2025 bildirisi, s. 231–239; A türü ön baskı diye bırakmış (A-25) |
| A | R33 | 10.1109/tevc.2013.2239648 | Li, Fialho, Kwong, Zhang 2014, IEEE TEVC | Adaptive Operator Selection With Bandits for a Multiobjective Evolutionary Algorithm Based on D — Li vd., 2014, IEEE Transactions on Evolutionary Computation 18 (1) :114-130 | EŞLEŞTİ |  |
| A | §9.1 | 10.1016/s0167-6377(02)00120-7 | Hunsaker & Savelsbergh 2002 | Efficient feasibility testing for dial-a-ride problems — Hunsaker vd., 2002, Operations Research Letters 30 (3) :169-173 | EŞLEŞTİ | A bu kaynağı içerik açılamadığı için reddetmiş; künye doğru |
| B | L1 | 10.3233/his-2006-3102 | Tsutsui, Pelikan, Ghosh 2006 | Edge histogram based sampling with local search for solving permutation problems — Tsutsui vd., 2006, International Journal of Hybrid Intelligent S 3 (1) :11-22 | EŞLEŞTİ |  |
| B | L2 | 10.1016/j.tcs.2017.10.012 | Wu, Möhring, Lai 2018, TCS | Stochastic runtime analysis of a Cross-Entropy algorithm for traveling salesman problems — Wu vd., 2018, Theoretical Computer Science 724 :69-86 | EŞLEŞTİ |  |
| B | L3 | 10.1109/3477.484436 | Dorigo, Maniezzo, Colorni 1996 | Ant system: optimization by a colony of cooperating agents — Dorigo vd., 1996, IEEE Transactions on Systems, Man, and Cybern 26 (1) :29-41 | EŞLEŞTİ |  |
| B | L4 | 10.1016/j.riai.2017.05.002 | Pérez-Rodríguez & Hernández-Aguirre 2017 (İngilizce başlık) | Un Algoritmo de Estimación de Distribuciones copulado con la Distribución Generalizada de Mallo — Pérez-Rodríguez vd., 2017, Revista Iberoamericana de Automática e Inform 14 (3) :288-298 | EŞLEŞTİ | Başlık özgün dilde İspanyolca; B İngilizce çeviri veriyor (B-11) |
| B | L5 | 10.1016/j.cie.2019.02.017 | Pérez-Rodríguez & Hernández-Aguirre 2019, CIE | A hybrid estimation of distribution algorithm for the vehicle routing problem with time windows — Pérez-Rodríguez vd., 2019, Computers & Industrial Engineering 130 :75-96 | EŞLEŞTİ |  |
| B | L12 | 10.1145/3583133.3590606 | Huang vd. 2023, GECCO Companion | Relational Bayesian Optimization for Permutation — Huang vd., 2023, Proceedings of the Companion Conference on Ge :471-474 | EŞLEŞTİ |  |

**DataCite DOI'leri:** 10.48550/arXiv.2501.04072 ve 10.48550/arXiv.2505.00803 CrossRef'te 404 döndü. Bu beklenen bir sonuçtur, çünkü arXiv DOI'leri DataCite'a kayıtlıdır. Her ikisi de arXiv API'de doğrulandı.

**arXiv kimlikleri (arXiv API):**

| Belge | Kimlik | arXiv kaydı | Sonuç |
|---|---|---|---|
| A | 2012.10384v2 | Hybrid Genetic Search for the CVRP: Open-Source Implementation and SWAP* Neighbo — Thibaut Vidal vd., 2020 ; journal_ref: Computers & Operations Research, Volume 140, 2022, 105643; DOI: 10.1016/j.cor.2021.105643 | EŞLEŞTİ |
| A | 1803.01930v1 | A Hybrid Heuristic for a Broad Class of Vehicle Routing Problems with Heterogene — Puca Huachi Vaz Penna vd., 2018 ; journal_ref: Annals of Operations Research, 2017; DOI: 10.1007/s1047 (arXiv kaydındaki DOI alanı kesik; A'nın verdiği 10.1007/s10479-017-2642-9 CrossRef'te doğru) | EŞLEŞTİ |
| A | 2305.02805v1 | Local Optima Correlation Assisted Adaptive Operator Selection — Jiyuan Pei vd., 2023  | EŞLEŞTİ |
| A | 2501.04072v1 | Multi-armed Bandit and Backbone boost Lin-Kernighan-Helsgaun Algorithm for the T — Long Wang vd., 2025  | EŞLEŞTİ |
| A | 2505.00803v1 | To Repair or Not to Repair? Investigating the Importance of AB-Cycles for the St — Jonathan Heins vd., 2025 ; DOI: 10.1145/3712256.3726436 | EŞLEŞTİ |
| B | 1612.06962v2 | Stochastic Runtime Analysis of a Cross Entropy Algorithm for Traveling Salesman  — Zijun Wu vd., 2016 ; journal_ref: Theoretical Computer Science, 2017; DOI: 10.1016/j.tcs.2017.10.012 | EŞLEŞTİ |
| B | 2503.16159v2 | RRNCO: Towards Real-World Routing with Neural Combinatorial Optimization — Jiwoo Son vd., 2025 ; Accepted at ICLR 2026. OpenReview: https://openreview.net/fo | EŞLEŞTİ |

**DOI'siz makaleler (B, arXiv başlık araması):**

| Kod | Belgedeki künye | arXiv kaydı | Sonuç |
|---|---|---|---|
| L6 | Kool 2019 | 1803.08475v3 — Attention, Learn to Solve Routing Problems!; Wouter Kool, Herke van Hoof, Max Welling; Accepted at ICLR 2019. 25 pages, 7 figures | EŞLEŞTİ |
| L7 | POMO 2020 | 2010.16011v3 — POMO: Policy Optimization with Multiple Optima for Reinforcement Learn; Yeong-Dae Kwon, Jinho Choo, Byoungjip Kim; Accepted at NeurIPS 2020 | EŞLEŞTİ |
| L8 | NeuroLKH 2021 | 2110.07983v1 — NeuroLKH: Combining Deep Learning Model with Lin-Kernighan-Helsgaun He; Liang Xin, Wen Song, Zhiguang Cao; Accepted at NeurIPS 2021 | EŞLEŞTİ |
| L9 | MatNet 2021 | 2106.11113v2 — Matrix Encoding Networks for Neural Combinatorial Optimization; Yeong-Dae Kwon, Jinho Choo, Iljoo Yoon; Accepted at NeurIPS 2021 | EŞLEŞTİ |
| L10 | DIFUSCO 2023 | 2302.08224v2 — DIFUSCO: Graph-based Diffusion Solvers for Combinatorial Optimization; Zhiqing Sun, Yiming Yang; Accepted at NeurIPS 2023 (Spotlight) | EŞLEŞTİ |

**İçerik iddiası kontrolleri (seçili):**
- B-L9 (MatNet: ATSP deneyleri üçgen eşitsizliğini sağlayan 'tmat' sınıfında): arXiv tam metninde doğrulandı.
- B-L11 (RRNCO, ICLR 2026 kabulü): arXiv yorum alanında görüldü. Asimetrik mesafe/süre modellemesi özette doğrulandı.
- A-R24 (Wang vd. 2025): özette backbone + α-değeri + MAB birleşimi görüldü.
- A-R15 (PyVRP v0.13.0: HGS'den ILS'e geçiş): GitHub sürüm notunda doğrulandı.
- A-R16 (çok boyutlu yük): `pyvrp/_pyvrp.pyi` kaynak kodunda (`capacity: list[int]`, `num_load_dimensions`) doğrulandı. readthedocs sayfası ağ izin listesi nedeniyle açılamadı.

**Lisanslar (GitHub API):**
- A'nın beyanları doğru: GA-EAX MIT, gpx2 GPL-3.0, PyVRP MIT, OR-Tools Apache-2.0, VROOM BSD-2-Clause.
- elkai: LICENSE metni yalnız akademik ve ticari olmayan kullanıma izin veriyor (LKH kısıtı). A'nın 'DOĞRULANMADI' maddesi böylece kapandı (A-19).

**Künye kusurları:**
- B-11: L4 başlığı özgünü İspanyolca olan bir makalenin çevirisi olarak verilmiş.
- A-20: O(nL²) bilgisi R1'e yanlış atfedilmiş.
- A-25: R32 aslında GECCO 2025 hakemli bildirisi.
- A-30: §9.1'deki iki kaynak DOI'siz bırakılmış. DOI'leri: Turkeš vd. 2021 10.1016/j.ejor.2020.10.045; Garaix & Skiredj 2024 10.1016/j.ejor.2023.11.037.

**Önerilerin dayanağı olarak ek çözülen DOI'ler:**
- Gschwind & Irnich 2015, 10.1287/trsc.2014.0531 (özet okundu)
- Cordeau & Laporte 2003, 10.1016/S0191-2615(02)00045-0 (yalnız künye)
- Held & Karp 1962, 10.1137/0110015 (yalnız künye)

## 8. Sınırlar

- **Tek hafta.** Ölçümle karşılaştırmalar tek snapshot haftasına (226 yolcu ayağı, 228 dalga) dayanıyor. 'Destekleniyor' ya da 'çelişiyor' etiketleri bu hafta için geçerli; genelleme iddiası değil.
- **Ölçümler yeniden koşturulmadı.** Sayılar ölçüm raporlarından alındı. Ölçülen çözücüler bu oturumun artefaktları; depoya alınmadı.
- **Makale içerikleri açılmadı.** Kaynak denetimi künye düzeyinde. Belgelerdeki yazar PDF'leri ve yayıncı sayfaları açılmadı. İçerik yalnız birkaç kaynakta kontrol edildi: MatNet tam metin; RRNCO, Pei vd. ve Wang vd. arXiv özetleri; Gschwind & Irnich CrossRef özeti.
- **Depo kontrolü tek dosya.** Yalnız ana checkout'taki `string_split_decoder.py` okundu; worktree'ler ve diğer modüller incelenmedi.
- **Açık kalanlar.** elkai'nin RECOMBINATION parametresi, GA-EAX'in ATSP desteği, GPX2'nin 2n verimi ve Google süre birimi bu denetimde kontrol edilmedi; A'daki açık durumları sürüyor.
- **Baskınlık ve simetri gerekçeleri kod ya da deneyle sınanmadı.** A-05, A-06 ve A-28'deki gerekçeler P5/P7 sözleşmesine dayalı matematiksel türetimlerdir. Uygulamadan önce sözleşme testiyle doğrulanmalı.

## 9. Dosyalar

- [astra_issues.csv](astra_issues.csv): 48 bulgu; sütunlar: id, belge, bölüm/satır, kategori, ciddiyet, iddia_özeti, kanıt, öneri.