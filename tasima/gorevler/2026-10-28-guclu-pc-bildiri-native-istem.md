# Güçlü bilgisayar: Bildiri native tahmininin 10 algoritmayla yeniden ölçülmesi

Bu dosya, güçlü bilgisayardaki Claude oturumuna verilecek istemdir. Aşağıdaki "İstem" bölümünün tamamını kopyalayıp yeni bir oturuma yapıştırın. Şef oturumu `WIP`'e ön-onay dalını birleştirdiğini bildirmeden başlatmayın; istem bunu ayrıca kontrol eder.

---

## İstem

Sen UniRide projesinde, sahibin güçlü bilgisayarında çalışan bir ölçüm oturumusun. `WIP` dalına yalnızca dizüstündeki şef oturumu birleştirir. Senin işin tek: D-04b2 tahmininin Bildiri bölümünü, native protokoldeki 10 algoritmanın hepsiyle yeniden ölçmek. Kod, profil ya da belge değiştirmezsin; yalnızca ölçüm kaydını kendi dalına yazarsın.

### Arka plan
- İlk D-04b2 ölçümünde Bildiri profilinin native listesinde yalnızca 2 algoritma vardı (Core-GWO-TSP-Pure, Core-HHO-TSP-Pure), bu yüzden "Bildiri native 0,01 sa" çıktı. Sahibin kararı (DECISION_LOG A18, OQ-4 cevabı, 2026-10-26) bütün çalışma algoritmalarının native protokole girmesiydi. Ön-onay dalı bu listeyi 10 algoritmaya genişletti; dizüstündeki kontrol tahmini 2100 native koşu, yaklaşık 4,3 saat.
- Kayıt dosyası: `docs/superpowers/plans/2026-10-27-d04b2-strong-pc-measurement.md` (önceki üç koşu). Şefin kuralı (A18, 2026-10-28): ölçüm ve kampanya "Yüksek performans" güç planında, yük kaydedilerek yapılır.

### Kurallar (hiçbirini çiğneme)
- **Python (Windows):** etkileşimli Python açma; çıplak `python`/`py`, `python -i`, `python -`, heredoc ya da stdin ile Python, `python -c` yasak. Gerekirse kodu `C:\wt\d04b2-native\` altında bir `.py` dosyasına yaz ve `.venv-jit\Scripts\python.exe dosya.py` ile çalıştır. Uzun komutlara zaman sınırı koy, çıktıyı dosyaya yönlendir, `tail`/`grep` ile oku. `_pyrepl`, `getheightwidth`, `WinError 123` ya da tekrarlanan aynı traceback görürsen süreci durdur ve sahibe bildir.
- Dosyaları heredoc, `cat >`, `echo >` ya da `sed -i` ile yazma; yalnızca Write/Edit araçlarıyla yaz. Yönlendirme yalnızca komut çıktısını `C:\wt\d04b2-native\` altındaki kayıt dosyalarına almak için.
- `taskkill /IM` yok; yalnızca kendi başlattığın süreçlerin PID'ini durdur. Sahibin onayı olmadan `pip`/`npm install` yok.
- Git: `WIP`'e commit ya da push yok, birleştirme yok, `git stash` yok, `git config` değişikliği yok. Kaydı yalnızca kendi dalında commit edip yalnızca o dalı gönder.
- `academic_benchmark/tsplib_data/tsplib.db*` dosyalarını okuma, kopyalama, silme. AMPL/Gurobi çalıştırma yok. `docs/paper/results` altına hiçbir şey yazma. Lisans metni, `.env` değerleri, kullanıcı adı ya da e-posta yazdırma.
- Commit mesajının sonuna şu satırı ekle: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

### Adım 1: ön koşulları kontrol et (değiştirmeden)
1. `git status` temiz ve ana kopya `WIP` dalında olmalı. `git fetch origin` ve `git log --oneline -1 origin/WIP` çalıştır; ana kopya `origin/WIP` ile aynı değilse sahibe `git pull --ff-only origin WIP` yapmasını söyle ve bekle.
2. `git log --oneline -15` içinde "pre-approval" ya da "preapproval" geçen bir birleştirme commit'i olmalı. `academic_benchmark/studies/bildiri2026/study.json` içinde `secondary_protocol.algorithm_ids` 10 kimlik içermeli ve `secondary_protocol.termination` `{"max_iterations": 1000}` olmalı. Bunlardan biri tutmazsa dur ve sahibe "ön-onay dalı henüz birleşmemiş" de; ölçüme başlama.
3. Aktif güç planı "Yüksek performans" olmalı (`powercfg /getactivescheme`). Değilse sahibe söyle ve bekle. Ağır başka bir program (tarayıcı vb.) açıksa sahibe kapatmasını öner.

### Adım 2: ölçüm
Yükü 15 saniyede bir kaydet (önceki koşudaki yöntemle: Windows `LoadPercentage` ve süreç başına CPU zamanı; örnekleyiciyi `C:\wt\d04b2-native\` altında bir dosyaya yaz) ve şu komutu zaman sınırıyla (4 saat) çalıştır:
```
.venv-jit\Scripts\python.exe -m academic_benchmark.studies.estimate --study academic_benchmark/studies/bildiri2026/study.json --out C:\wt\d04b2-native\bildiri --run-count 30 --native-global-iterations 1000 --native-polish-iterations 1000
```
Çıktı klasörü boş olmalı. Komut sabit bütçeyi de yeniden fiyatlar; bu beklenen bir şey. YAEM'i yeniden ölçme (YAEM'in native listesi zaten tamdı).

### Adım 3: kayıt ve teslim
1. Ayrı bir çalışma kopyası aç: `git worktree add C:\wt\d04b2-native-kayit -b results/d04b2-bildiri-native WIP`.
2. Orada `docs/superpowers/plans/2026-10-27-d04b2-strong-pc-measurement.md` dosyasının sonuna "### Fourth run: Bildiri native with all 10 algorithms (2026-10-28)" başlıklı bir bölüm ekle. İçinde: ölçülen commit ve `dirty` durumu; güç planı ve yük özeti (median, min, max); komut, başlangıç, süre, çıkış kodu; Bildiri sabit bütçe toplamı ve native toplamı (koşu sayısı, saat); native için algoritma başına satırlar (eil51 ve kroa100 koşu süresi, yineleme sayısı, durma nedeni, tahmin aracının yazdığı gibi); önceki koşu 3 ile Bildiri sabit bütçe karşılaştırması; tahmin aracının "PROVISIONAL" etiketleri olduğu gibi; "planlama sayıları, kanıt değil" notu. Yorum ya da öneri ekleme, yalnızca ölçülenleri yaz.
3. Commit et ve yalnızca bu dalı gönder: `git push -u origin results/d04b2-bildiri-native`.
4. Sahibe kısa bir Türkçe özet ver: Bildiri native toplam süresi, Bildiri sabit bütçe toplamı, beklenmedik bir şey varsa o. `DECISION_LOG.md` ve `DURUM.md` dosyalarına dokunma.

### Durma koşulları
Ön koşullardan biri tutmazsa, komut zaman sınırını aşarsa ya da bir talimat kurallarla çelişirse işi bırak ve sahibe sor.
