# Güçlü bilgisayar: D-10 temel commit'inde tam test koşusu ve ön kontroller

Bu dosya, güçlü bilgisayardaki Claude oturumuna verilecek istemdir. Aşağıdaki "İstem" bölümünün tamamını kopyalayıp yeni bir oturuma yapıştırın. Önce o bilgisayarda ana kopyayı güncelleyin: `git pull --ff-only origin WIP`.

Bu koşunun sonucu, iki koşu planının (Bildiri, YAEM) son boş alanını doldurur. Ardından planlar sahibin onayına gider. Temel commit ile onay commit'i arasında `WIP`'e hiçbir şey eklenmez.

---

## İstem

Sen UniRide projesinde, sahibin güçlü bilgisayarında çalışan bir doğrulama oturumusun. `WIP` dalına yalnızca dizüstündeki şef oturumu birleştirir. Senin işin: makale kampanyasının temel commit'inde (base commit) tam test koşusunu temiz ayrı bir kopyada yapmak, kampanya ön kontrollerinden bugün yapılabilenleri denemek ve sonuçları kendi dalına yazmak. Kod, profil ya da belge değiştirmezsin.

### Kurallar (hiçbirini çiğneme)
- **Python (Windows):** etkileşimli Python açma. Çıplak `python`/`py`, `python -i`, `python -`, heredoc ya da stdin ile Python, `python -c` yasak. Gerekirse kodu `C:\wt\d10-base\` altında bir `.py` dosyasına yaz ve `.venv-jit\Scripts\python.exe dosya.py` ile çalıştır. Uzun komutlara zaman sınırı koy, çıktıyı dosyaya yönlendir, `tail`/`grep` ile oku. `_pyrepl`, `getheightwidth`, `WinError 123` ya da tekrarlanan aynı traceback görürsen süreci durdur ve sahibe bildir.
- Dosyaları heredoc, `cat >`, `echo >` ya da `sed -i` ile yazma; yalnızca Write/Edit araçlarıyla yaz. Yönlendirme yalnızca komut çıktısını `C:\wt\d10-base\` ya da `C:\wt\gated\` altına almak için.
- `taskkill /IM` yok; yalnızca kendi başlattığın süreçlerin PID'ini durdur. Sahibin onayı olmadan `pip`/`npm install` yok.
- Git: `WIP`'e commit ya da push yok, birleştirme yok, `git stash` yok, `git config` değişikliği yok, ana kopyada `git checkout`/`git switch` yok. Kaydı yalnızca kendi dalında commit edip yalnızca o dalı gönder.
- `academic_benchmark/tsplib_data/tsplib.db*` dosyalarını okuma, kopyalama, silme (testler kendileri okur). AMPL/Gurobi çalıştırma yok; pytest her zaman `-m "not requires_ampl"` ile. `docs/paper/results` altına hiçbir şey yazma. Lisans metni, `.env` değerleri, kullanıcı adı ya da e-posta yazdırma.
- **Tehlike:** `academic_benchmark.studies.run --mode paper` komutunu hiçbir yerde çalıştırma. Bu oturum kampanyayı başlatmaz.
- Aynı anda en fazla 2 pytest süreci çalıştır.
- Commit mesajının sonuna şu satırı ekle: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

### Adım 1: temel commit'i belirle (değiştirmeden)
1. Ana kopyada `git fetch origin`, `git status --short`, `git rev-parse --abbrev-ref HEAD`, `git log --oneline -1 origin/WIP` çalıştır. Ana kopya `WIP` dalında ve `origin/WIP` ile aynı olmalı (izlenmeyen `archive/docs/` dosyaları beklenir). Değilse dur ve sahibe `git pull --ff-only origin WIP` yapmasını söyle.
2. `origin/WIP` başındaki commit'in mesajı `docs: D-10 base commit` ile başlamalı. Bu commit temel commit'tir; tam hash'ini kayda yaz (aşağıda `<base>`). Mesaj böyle başlamıyorsa dur ve sahibe sor.
3. `powercfg /getactivescheme` komutunu doğrudan PowerShell'de çalıştır. Çıktıda `8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c` ("Yüksek performans") olmalı. Değilse sahibe söyle ve bekle. Tarayıcı gibi ağır bir program açıksa sahibe kapatmasını öner.

### Adım 2: temiz ayrı kopyada tam test koşusu
1. `git worktree add C:\wt\d10-base-ck <base> --detach` ile temiz bir kopya aç (`$CK = "C:\wt\d10-base-ck"`). `git -C $CK status --short` boş olmalı.
2. `docs/superpowers/plans/2026-10-23-gate-d-analysis-documentation-publication.md` dosyasının 102–128. satırlarındaki komut bloğunu, ilk satırda `<checkout>` yerine `$CK` koyarak ve `git` komutlarını `$CK` içinde çalışacak şekilde (`Start-Process` için `-WorkingDirectory $CK` ekle) çalıştır. Smoke çıktıları `C:\wt\gated\` altına gider. Python yolu: `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe` bu bilgisayarda farklıysa, ana kopyadaki `.venv-jit\Scripts\python.exe` yolunu kullan ve kayda yaz. `$env:PYTHONPATH = $CK` olmalı (venv ana kopyaya `pip install -e` ile kurulu; `PYTHONPATH` olmadan ana kopyanın kodu çalışır).
3. Her satırın `OK`/`FAIL` sonucunu, pytest özet satırlarını, sürelerini ve atlanan testlerin nedenlerini (`-rs` ile ayrı bir koşu gerekmez; özet satırındaki skip sayısı ve `--tb=short` çıktısı yeter; neden gerekiyorsa ilgili dosyayı `-rs` ile yeniden koşabilirsin) topla. Temiz kopyada `tsplib.db` yoktur; veritabanı testleri orada atlanır, bu beklenir.
4. Veritabanı testleri için ana kopyada (aynı `<base>` commit'inde, `PYTHONPATH` boş) bir kez daha çalıştır, en fazla 40 dakika her biri:
   `.venv-jit\Scripts\python.exe -m pytest academic_benchmark/tests uniride_core/tests -m "not requires_ampl" -q -p no:cacheprovider -rs`
   Özet satırını ve atlama nedenlerini kayda yaz.
5. Başarısız test varsa düzeltmeye çalışma. Adını, hata mesajının ilk satırlarını ve olası nedeni (ortam mı kod mu) kayda yaz.

### Adım 3: bugün yapılabilen ön kontroller (koşu planı bölüm 7, C5–C7)
Koşu planları `origin/docs/d10-run-plans-v2` dalında: `git show origin/docs/d10-run-plans-v2:docs/run_plans/bildiri2026-2026-10-28.md` ile oku (dosyayı ana kopyaya yazma). `$CK` üzerinde:
- **C5:** `test_analysis_environment.py` koşusu, `pip check`, numpy/llvmlite/numba sürümleri (komutlar planda).
- **C6:** `C:\wt\d10-base\which_package.py` adında iki satırlık bir betik yaz; `academic_benchmark.__file__` ve `uniride_core.__file__` yazdırsın. `$env:PYTHONPATH = $CK` ile çalıştır; iki yol da `$CK` ile başlamalı.
- **C7:** planın bölüm 9'daki commit listesi için `git merge-base --is-ancestor <commit> <base>` döngüsü; hepsi exit 0 olmalı.
C1–C4 kampanya başında, onay commit'inde yapılır; bugün yapma.

### Adım 4: kayıt ve teslim
1. Ayrı bir çalışma kopyası aç: `git worktree add C:\wt\d10-base-kayit -b results/d10-base-suite <base>`.
2. Orada tek bir yeni dosya yaz: `docs/superpowers/plans/2026-10-28-d10-base-suite-strong-pc.md`. İçinde: `<base>` tam hash'i ve mesajı; güç planı satırı; Python yolu ve `PYTHONPATH`; komut bloğunun her satırının sonucu, süresi ve pytest özet satırları; ana kopyadaki veritabanı koşusunun özet satırı ve atlama nedenleri; başarısız testler (varsa); C5, C6, C7 sonuçları; `git -C $CK status --short` çıktısının koşulardan sonra boş olduğu. Yorum ya da öneri ekleme, yalnızca ölçülenleri yaz.
3. Commit et ve yalnızca bu dalı gönder: `git push -u origin results/d10-base-suite`. Bu dal kampanyadan önce `WIP`'e birleştirilmez; şef sayıları onay kaydına aktarır.
4. `C:\wt\d10-base-ck` kopyasını silme; kampanya için şef yeni talimat verecek.
5. Sahibe kısa bir Türkçe özet ver: her takımın özet satırı, başarısız test varsa adı, C5–C7 sonucu. `DECISION_LOG.md` ve `DURUM.md` dosyalarına dokunma.

### Durma koşulları
Temel commit beklenenden farklıysa, güç planı yanlışsa, bir komut zaman sınırını aşarsa ya da bir talimat kurallarla çelişirse işi bırak ve sahibe sor.
