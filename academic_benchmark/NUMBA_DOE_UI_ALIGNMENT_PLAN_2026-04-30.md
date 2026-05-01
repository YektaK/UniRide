# NUMBA DOE UI Alignment Plan (Bildiri2026 Referanslı)

Tarih: 2026-04-30
Kapsam: academic_benchmark/run_smart_benchmark_numba_doe.py
Amaç: NUMBA DOE seçim akışını bildiri2026 UI mantığıyla hizalamak ve problem seçiminde sınıf bazlı seçime ek olarak numaralı tekil seçim desteği eklemek.

---

## 1) Hedef ve Problem Tanımı

Mevcut NUMBA DOE akışında çalışma ayarları (profil, mod, run sayıları, worker) kapsam seçimlerinden önce soruluyor. Bu sıra kullanıcı açısından sezgisel değil.

Bildiri2026 tarafında ise akış daha doğal:
1. Ne çalıştırılacak? (model/config)
2. Hangi problem(ler)?
3. Kaç tekrar / hangi ayarlar?
4. Çalıştırma

Bu planın hedefi, NUMBA DOE tarafında aynı mantığı uygulamak ve seçim ekranlarını bildiri2026 ile uyumlu hale getirmektir.

---

## 2) Referans Akışlar (Karşılaştırma)

### 2.1 Bildiri2026 Akışı (Özet)
Kaynaklar:
- academic_benchmark/bildiri2026/1_generate_config.py
- academic_benchmark/bildiri2026/2_run_tuning.py
- academic_benchmark/bildiri2026/3_run_benchmark.py

Öne çıkan seçim özellikleri:
- Numara bazlı seçim: 1,3,5
- Toplu seçim: all
- Geçersiz seçimde temiz hata mesajı
- Önce kapsam, sonra çalışma ayarları

### 2.2 NUMBA DOE Mevcut Akış (Özet)
Kaynak:
- academic_benchmark/run_smart_benchmark_numba_doe.py

Mevcut sıra:
1. profile
2. problem scope (small/medium/large/all)
3. mode
4. tuning runs
5. final benchmark runs
6. max combinations
7. worker
8. ana menü (A/B/C/D/E/S/Q)
9. bazı dallarda algoritma seçimi

Sorunlar:
- Kapsam belirlenmeden çalışma ayarları soruluyor
- Özel seçimde algoritma seçimi çok geç geliyor
- Hızlı mod, önceden seçilen scope bilgisini override ediyor
- Sequential modda bile worker girdisi isteniyor

---

## 3) Gereksinimler

Bu geliştirme tamamlandığında aşağıdakiler sağlanmalı:

1. Problem seçimi iki yolla yapılabilmeli:
- Sınıf bazlı: small/medium/large/all
- Numara bazlı: problem listesinden 1,2,5 veya all

2. Bildiri2026 seçim opsiyonları NUMBA DOE tarafına taşınmalı:
- Çoklu numara seçimi (comma-separated)
- all desteği
- Geçersiz girişte hata + yeniden isteme

3. Akış sırası kapsam odaklı olmalı:
- Önce aksiyon/kapsam
- Sonra execution ayarları

4. Sequential modda worker sorusu sorulmamalı.

---

## 4) Hedef UI Akışı (Yeni)

### 4.1 Üst Seviye Akış
1. Ana menü: A/B/C/D/E/S/Q
2. Kapsam seçimi
- Problem seçimi (mode: class/index)
- Algoritma seçimi (numara veya all)
3. Cache/rerun davranışı
4. Çalışma ayarları
- profile
- mode (S/P)
- parallel ise worker
- tuning runs
- final benchmark runs
- max combinations
5. Test özeti + onay
6. Koşu

### 4.2 Menü Bazlı Davranış
- A: Seçilen kapsam için tam retune
- B: Sadece eksik (untuned) pairler
- C: Hızlı mod (küçük set varsayılanı korunur, ama kullanıcıya net gösterilir)
- D: Kapsamlı yeniden çalıştırma
- E: Özel seçim (algoritma ve problem numaralı seçim)
- S: Detay modu (mevcut davranış)
- Q: Çıkış

---

## 5) Fonksiyonel Tasarım (Kod Seviyesi)

Dosya: academic_benchmark/run_smart_benchmark_numba_doe.py

### 5.1 Yeni Yardımcılar
1. _parse_index_or_all_input(raw, item_count)
- Girdi: "1,3,5" veya "all"
- Çıktı: seçilen index listesi
- Geçersiz durumda None/detay hata

2. _select_problems_by_index(problems)
- Problem listesini numaralı gösterir
- "1,2,4" ve "all" kabul eder
- Seçilen problem listesi döner

3. _select_problem_mode_and_scope(all_problems)
- Seçim modu sorar:
  - class tabanlı
  - index tabanlı
- class modunda mevcut small/medium/large/all mantığını kullanır
- index modunda _select_problems_by_index kullanır

4. _select_algorithms_numbered(all_specs)
- Algoritmaları numaralı listeler
- "1,3" ve "all" kabul eder
- Deterministik seçim döner

### 5.2 Mevcut Fonksiyonlarda Güncelleme
1. _multi_select(...)
- Ya tamamen kaldırılacak ya da çağrısı _select_algorithms_numbered ile değiştirilecek

2. _select_worker_count()
- Sadece parallel modda çağrılacak

3. _show_test_summary(...)
- Seçim tipini de gösterecek (class/index)
- Seçilen problem adları kısa özet eklenecek

4. main()
- Akış sırası yeniden düzenlenecek:
  - önce ana aksiyon
  - sonra kapsam
  - sonra execution ayarları
- C modu override davranışı daha açık hale getirilecek

---

## 6) UI Eşleştirme Matrisi (Bildiri2026 -> NUMBA DOE)

1. Problem numarası ile seçim
- Bildiri2026: var
- NUMBA DOE hedef: eklenecek

2. Algoritma numarası ile seçim
- Bildiri2026: var
- NUMBA DOE hedef: standart hale getirilecek

3. all ile toplu seçim
- Bildiri2026: var
- NUMBA DOE hedef: problem + algoritma için tutarlı destek

4. Geçersiz girişte hata
- Bildiri2026: var
- NUMBA DOE hedef: her seçim adımında tutarlı hata mesajı

5. Sıra mantığı (kapsam -> ayar)
- Bildiri2026: var
- NUMBA DOE hedef: ana akış buna çevrilecek

---

## 7) Doğrulama Planı

### 7.1 Pozitif Senaryolar
1. Problem class seçimi: small + all algoritma
2. Problem index seçimi: 1,3,5 + algoritma 2,4
3. all problem + all algoritma
4. E (özel seçim) ile index tabanlı problem + index tabanlı algoritma
5. Sequential akışta worker sorusunun hiç gelmemesi
6. Parallel akışta worker sorulması

### 7.2 Negatif Senaryolar
1. Problem seçiminde aralık dışı index
2. Problem seçiminde bozuk format: 1,,a
3. Algoritma seçiminde bozuk format: q,9
4. Boş seçim sonrası varsayılan fallback davranışı

### 7.3 Smoke Run
1. Tiny run:
- 1 algoritma
- 1 problem (index ile)
- tuning 1
- final 1
- sequential
2. Summary ekranında seçimlerin doğru yansıdığı doğrulanacak

---

## 8) Geriye Uyumluluk ve Riskler

1. Risk: Akış yeniden sıralaması mevcut alışkanlığı etkileyebilir
- Önlem: Menü metinleri açık ve kısa tutulacak

2. Risk: C hızlı mod ile yeni seçim modeli çakışabilir
- Önlem: C için deterministic override + ekranda net bilgilendirme

3. Risk: Eski metadata/cache akışında davranış farkı
- Önlem: cache anahtar üretiminde değişiklik yapılmayacak

---

## 9) Tamamlanma Kriterleri

1. Kullanıcı problem seçimini hem sınıf hem numara bazlı yapabiliyor
2. all ve comma seçimleri problem/algoritma için çalışıyor
3. Akış sırası kapsamdan ayara doğru ilerliyor
4. Sequential modda worker prompt yok
5. Tiny run başarıyla tamamlanıyor ve summary hatasız basılıyor

---

## 10) Uygulama Adımları (İcra Sırası)

1. Yeni parser ve seçim yardımcılarını ekle
2. main akışını yeni sıraya taşı
3. E menüsünü numaralı seçim modeliyle birleştir
4. worker prompt koşulunu parallel ile sınırla
5. summary ekranını yeni seçim bilgileriyle güncelle
6. tiny smoke run ile doğrula
7. gerekiyorsa metin/yardım mesajlarını sadeleştir

---

## 11) Not

Bu doküman tasarım ve uygulama planıdır. Kod değişiklikleri ayrı adımda uygulanacaktır.