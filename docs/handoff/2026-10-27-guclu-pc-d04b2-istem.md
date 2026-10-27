# Güçlü bilgisayar: D-04b2 kesin süre tahmini ve tam test koşusu

Bu dosya, güçlü bilgisayardaki Claude oturumuna verilecek istemdir. Aşağıdaki "İstem" bölümünün tamamını kopyalayıp o oturuma yapıştırın.

Paralel çalışma düzeni: dizüstü bilgisayardaki şef oturumu MT1 işine devam eder ve `WIP` dalına birleştirmeyi yalnızca o yapar. Güçlü bilgisayardaki oturum yalnızca ölçüm yapar, sonucunu kendi dalına (`results/d04b2-strong-pc`) yazar ve o dalı gönderir. `WIP` dalına hiçbir şey göndermez.

---

## İstem

Sen UniRide projesinde, sahibin ikinci (güçlü) bilgisayarında çalışan bir ölçüm oturumusun. Başka bir bilgisayarda şef oturumu paralel olarak çalışıyor; `WIP` dalına yalnızca o birleştirir. Senin işin tek bir iş paketi: **D-04b2** (kesin süre tahmini) ve bu makinede tam test koşusu. Kod, tasarım ya da çalışma profili değiştirmezsin.

### Önce oku
- `AGENTS.md`, `DURUM.md`.
- `docs/superpowers/plans/2026-10-23-gate-d-analysis-documentation-publication.md` içinde "D-04b: Cost estimator and calibration slices" bölümü (D-04b2 tanımı).
- `docs/DECISION_LOG.md` içinde A18 bölümündeki "D-04b1 measurement" ve "owner confirmations after the D-04b1 table" satırları, A19 bölümündeki "MT6-06 re-measure" satırı, A20 L1 ve L11. Sahibin kararları: hücre başına 30 koşu, sabit bütçe seviyeleri 50x ve 250x, native protokolde her algoritma, yerel arama ve cila aşamaları için güvenlik sınırı 1000 yineleme, GWO/HHO/GA/PSO ve bileşiklerin global aşaması 1000 yineleme.

### Kurallar (hiçbirini çiğneme)
- **Python (Windows):** etkileşimli Python açma. Çıplak `python`/`py`, `python -i`, `python -`, heredoc ya da stdin ile Python, `python -c` yasak. Gerekirse kodu `C:\wt\d04b2\` altında bir `.py` dosyasına yaz ve `.venv-jit\Scripts\python.exe dosya.py` ile çalıştır. Uzun komutlara zaman sınırı koy, çıktıyı dosyaya yönlendir, `tail`/`grep` ile oku. Çıktıda `_pyrepl`, `getheightwidth`, `WinError 123` ya da tekrarlanan aynı traceback görürsen süreci durdur ve sahibe bildir.
- `taskkill /IM` yok; yalnızca kendi başlattığın süreçlerin PID'ini durdur. Sahibin onayı olmadan `pip`/`npm install` yok.
- Git: `WIP` dalına commit ya da push yok, birleştirme yok, `git stash` yok, `git config` değişikliği yok. Ölçüm kaydını yalnızca `results/d04b2-strong-pc` dalında (ayrı bir çalışma kopyasında) commit edip yalnızca o dalı gönder.
- Ham ölçüm çıktıları depoya girmez: `C:\wt\d04b2\` altında kalır. `docs/paper/results` altına hiçbir şey yazma.
- `academic_benchmark/tsplib_data/tsplib.db*` dosyalarını okuma, kopyalama, silme. Testler bu dosyayı kendileri okur, sen dokunma.
- AMPL/Gurobi çalıştırma yok. Bütün pytest koşuları `-m "not requires_ampl"` ile. Lisans metni, `.env` değerleri, kullanıcı adı ya da e-posta yazdırma.
- Commit mesajının sonuna şu satırı ekle: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Ölçüm sırasında bilgisayarda başka ağır iş çalışmasın. Arka planda başka bir yük varsa kayıtta belirt; MT6-06 ölçümünde bu yüzden süreler şişmişti.

### Adım 1: ortam kontrolü (değiştirmeden)
1. `git status`, `git log --oneline -1` ve `git rev-parse --abbrev-ref HEAD` çalıştır. Ana kopya `WIP` dalında, temiz ve `origin/WIP` ile aynı olmalı. Değilse dur ve sahibe sor.
2. Makine bilgisi: işlemci modeli, mantıksal çekirdek sayısı, RAM, Windows sürümü.
3. `.venv-jit\Scripts\python.exe` sürümü ile numpy, numba, scipy ve statsmodels sürümleri. Beklenen: Python 3.14.x, numpy 2.4.6, numba 0.66.0, scipy 1.18.1, statsmodels 0.15.0. Bunun için `.venv-jit\Scripts\python.exe -m pip list` çıktısını bir dosyaya yaz ve oradan oku. Paket sürümleri farklıysa ya da paket eksikse dur ve sahibe hangi kurulum komutunun gerektiğini söyle. Kurulumu sahibin onayı olmadan yapma.
4. `academic_benchmark/tsplib_data/tsplib.db` dosyası var mı, yalnızca `Test-Path` ile bak. Yoksa sahibe söyle: bu dosya git'te yok, dizüstü bilgisayardan elle kopyalanması gerekiyor. Gerçek veritabanı testleri dosya olmadan atlanır.
5. `PYTHON_BASIC_REPL` ortam değişkeni `1` mi? Değilse sahibe söyle.

### Adım 2: ölçüm (D-04b2)
Ana kopyada, sahibin `pull` ettiği commit üzerinde çalıştır. Commit'i kayda yaz. Her komutu zaman sınırıyla çalıştır, çıktısını `C:\wt\d04b2\` altına yönlendir.
```
.venv-jit\Scripts\python.exe -m academic_benchmark.studies.estimate --study academic_benchmark/studies/bildiri2026/study.json --out C:\wt\d04b2\bildiri --run-count 30 --native-global-iterations 1000 --native-polish-iterations 1000
.venv-jit\Scripts\python.exe -m academic_benchmark.studies.estimate --study academic_benchmark/studies/yaem2026/study.json --out C:\wt\d04b2\yaem --run-count 30 --native-global-iterations 1000 --native-polish-iterations 1000
```
- İki komutu sırayla çalıştır, paralel değil (zamanlama ölçülüyor).
- Önce `--help` çıktısını `C:\wt\d04b2\help.txt` dosyasına yaz. Bayrak adları yukarıdakilerden farklıysa dur ve sor.
- Native 1000 sınırıyla kalibrasyon dilimi uzun sürebilir (dizüstünde native 3-opt yinelemesi kroA100'de yaklaşık 1,4 saniyeydi). Her komut için 3 saatlik bir zaman sınırı koy. Sınır dolarsa bunu kayda yaz ve sahibe sor.
- Tahmin aracının kendisinin yazdığı "PROVISIONAL" etiketlerini olduğu gibi aktar.

### Adım 3: tam test koşusu (bu makinede)
Her biri zaman sınırlı, çıktısı `C:\wt\d04b2\` altında:
```
.venv-jit\Scripts\python.exe -m academic_benchmark.contracts.export_schemas check
.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests uniride_core/tests optimizer_api/tests -m "not requires_ampl" -q -p no:cacheprovider -rs
```
Özet satırını, süreyi ve atlanan testlerin nedenlerini kayda yaz. Başarısız test varsa düzeltmeye çalışma; adını, hata mesajının ilk satırlarını ve olası nedeni (ortam mı kod mu) kayda yaz.

### Adım 4: kayıt ve teslim
1. Ayrı bir çalışma kopyası aç: `git worktree add C:\wt\d04b2-kayit -b results/d04b2-strong-pc WIP`.
2. Orada tek bir yeni dosya yaz: `docs/superpowers/plans/2026-10-27-d04b2-strong-pc-measurement.md`. İçinde:
   - makine bilgisi ve paket sürümleri;
   - ölçülen commit ve `dirty` durumu;
   - çalıştırılan komutlar ve her birinin süresi;
   - iki çalışma için tahmin aracının ürettiği tablo (algoritma bazında satırlar, toplam seri süre, sabit bütçe ve native ayrı ayrı);
   - dizüstü ölçümüyle (A19 MT6-06: Bildiri 16,7 sa, YAEM 11,5 sa sabit bütçe; o ölçümde CPU başka programla yüklüydü) yan yana bir karşılaştırma;
   - test özet satırları ve atlama nedenleri;
   - ölçüm sırasında makinedeki diğer yük;
   - "planlama sayıları, kanıt değil" notu.

   Bu dosyaya yorum ya da öneri ekleme, yalnızca ölçülenleri yaz.
3. Commit et ve yalnızca bu dalı gönder: `git push -u origin results/d04b2-strong-pc`.
4. Sahibe kısa bir Türkçe özet ver: iki çalışmanın toplam seri süresi (sabit bütçe ve native), test sonucu, beklenmedik bir şey varsa o. `DECISION_LOG.md` ve `DURUM.md` dosyalarına dokunma; onları dizüstündeki şef oturumu güncelleyecek.

### Durma koşulları
Aşağıdakilerden biri olursa işi bırak ve sahibe sor:
- depo durumu beklenenden farklı;
- paket sürümleri farklı;
- bir komut zaman sınırını aşıyor;
- bir talimat kurallarla çelişiyor.
