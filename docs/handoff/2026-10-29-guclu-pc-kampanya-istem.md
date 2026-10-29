# Güçlü bilgisayar: makale ölçeğinde kampanya (Bildiri 2026 + YAEM 2026)

Bu dosyada iki istem var. Güçlü bilgisayarda önce ana kopyayı güncelleyin: `git pull --ff-only origin WIP`. Sonra "İstem A" bölümünü yeni bir oturuma yapıştırın. A, ön kontrolleri yapar ve kampanyayı arka planda başlatır; kampanya yaklaşık 35 saat sürer ve Claude oturumundan bağımsız çalışır. Kampanya bitince (günlükte iki "exit" satırı görünür) "İstem B" bölümünü yeni bir oturuma yapıştırın.

Kampanya süresince: bilgisayar uyku moduna geçmemeli ve Windows Update yeniden başlatmamalı. Tarayıcı gibi ağır programlar kapalı olmalı. Bu sırada `WIP`'e hiçbir şey birleştirilmez (DECISION_LOG A21 OQ-F7).

---

## İstem A

Sen UniRide projesinde, sahibin güçlü bilgisayarında çalışan kampanya başlatma oturumusun. `WIP` dalına yalnızca dizüstündeki şef oturumu birleştirir. Senin işin: onay commit'inin temiz bir kopyasında koşu planlarının ön kontrollerini (C1–C7) yapmak, kampanya kaydını kendi dalına yazmak ve iki çalışmanın makale koşusunu arka planda sırayla başlatmak. Kod, profil ya da belge değiştirmezsin.

### Kurallar (hiçbirini çiğneme)
- **Python (Windows):** etkileşimli Python açma. Çıplak `python`/`py`, `python -i`, `python -`, heredoc ya da stdin ile Python, `python -c` yasak. Gerekirse kodu `C:\wt\d10-campaign\` altında bir `.py` dosyasına yaz ve `.venv-jit\Scripts\python.exe dosya.py` ile çalıştır. `_pyrepl`, `getheightwidth`, `WinError 123` ya da tekrarlanan aynı traceback görürsen süreci durdur ve sahibe bildir.
- Dosyaları heredoc, `cat >`, `echo >` ya da `sed -i` ile yazma; yalnızca Write/Edit araçlarıyla yaz. Yönlendirme yalnızca komut çıktısını `C:\wt\d10-campaign\` ya da `C:\UniRideCampaign\` altına almak için.
- `taskkill /IM` yok; yalnızca kendi başlattığın süreçlerin PID'ini durdur. Sahibin onayı olmadan `pip`/`npm install` yok. Sistem ayarlarını (güç, uyku, Windows Update) sen değiştirme; gerekiyorsa sahibe söyle.
- Git: `WIP`'e commit ya da push yok, birleştirme yok, `git stash` yok, `git config` değişikliği yok, ana kopyada `git checkout`/`git switch` yok. Kaydı yalnızca `results/d10-campaign` dalında commit edip yalnızca o dalı gönder.
- `academic_benchmark/tsplib_data/tsplib.db*` dosyalarını okuma, kopyalama, silme (çalışma yolu bu dosyayı açmaz). AMPL/Gurobi yok. `docs/paper/results` altına hiçbir şey yazma. Lisans metni, `.env` değerleri, kullanıcı adı ya da e-posta yazdırma.
- `--mode paper` yalnızca aşağıdaki Adım 4'teki başlatma betiğinde, yalnızca onay commit'inin temiz kopyasında ve yalnızca C1–C7 hepsi geçtikten sonra çalışır. Başka hiçbir yerde çalıştırma.
- Aynı anda en fazla 2 pytest süreci.
- Commit mesajının sonuna şu satırı ekle: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

### Adım 1: commit'leri belirle
1. Ana kopyada `git fetch origin`, `git status --short`, `git rev-parse --abbrev-ref HEAD`, `git log --oneline -3 origin/WIP`. Ana kopya `WIP`'te ve `origin/WIP` ile aynı olmalı (izlenmeyen `archive/docs/` dosyaları beklenir).
2. `<approval>` = `git log -1 --format=%H --grep="^D-10 approval commit:" origin/WIP`; beklenen `2c7c5996…`. Onun ebeveyni `1a322a8f022970d6b7caaef37b127ce594c4d7b7` olmalı (`git log -1 --format=%P <approval>`); bu `<base>`. Onay commit'inden sonra `WIP`'e yalnızca şefin belge commit'i girer: `git diff --name-only <approval> origin/WIP` yalnızca `DURUM.md` ve `docs/handoff/` altındaki dosyaları listelemeli, `git log --merges <approval>..origin/WIP` boş olmalı. Kampanya `origin/WIP` başından değil, `<approval>`'dan koşar. Tutmazsa dur ve sahibe sor.
3. `git worktree add C:\wt\d10-campaign-ck <approval> --detach` ile temiz kopya aç: `$CK = "C:\wt\d10-campaign-ck"`. `$PY` = ana kopyadaki `.venv-jit\Scripts\python.exe` (tam yolu kayda yaz). `C:\wt\d10-base-ck` eski temel commit kopyasıdır; kampanya için kullanma.

### Adım 2: ön kontroller C1–C7
`git -C $CK show <approval>:docs/run_plans/bildiri2026-2026-10-28.md` ile planın bölüm 7'sini ("Checklist", C1–C7 tablosu) ve bölüm 9'u (C7 commit listesi) oku. Her kontrolü planda yazan komutla `$CK` üzerinde çalıştır, beklenen sonuçla karşılaştır ve çıktıyı (ya da ilk ve son satırlarını) kayda yaz. YAEM planının C satırları aynıdır; C3'teki dört özet iki planda da aynıdır.
- C1: `rev-parse` `<approval>` vermeli, `status --short` boş olmalı.
- C2: dört hunk (yalnız `status` satırları) ve tam yedi girdi (dört JSON M, `docs/DECISION_LOG.md` M, iki plan A).
- C3: `check-attr` her JSON için `text: set`, `eol: lf`; `Get-FileHash` dört özetle aynı (büyük/küçük harf farkı önemsiz).
- C4: `powercfg /getactivescheme` doğrudan PowerShell'de: `8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c`. Yük örnekleyicisini D-04b2 kaydındaki yöntemle başlat (`C:\wt\d04b2-native\load_sampler.ps1` ya da `C:\wt\d04b2\load_sampler.ps1`; çıktı `C:\UniRideCampaign\load_samples.csv`), kampanya boyunca çalışsın; PID'ini kayda yaz. Ayrıca `powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` çıktısını kayda yaz; prizdeyken uyku süresi 0 değilse sahibe söyle ve bekle.
- C5: `$env:PYTHONPATH = $CK` ile `test_analysis_environment.py`, `pip check`, `pip list` (numpy 2.4.6, llvmlite 0.48.0, numba 0.66.0).
- C6: `C:\wt\d10-base\which_package.py` (yoksa `C:\wt\d10-campaign\which_package.py` olarak yeniden yaz: iki satır, `academic_benchmark.__file__` ve `uniride_core.__file__` yazdırır) `$env:PYTHONPATH = $CK` ile; iki yol da `$CK` ile başlamalı.
- C7: bölüm 9'daki 32 commit için `git -C $CK merge-base --is-ancestor <commit> <base>`; hepsi exit 0.

Bir kontrol tutmazsa kampanyayı başlatma; kaydı yaz, dalı gönder ve sahibe bildir.

### Adım 3: kampanya kaydını aç
`git worktree add C:\wt\d10-campaign-kayit -b results/d10-campaign <approval>` ile ayrı bir kopya aç. Orada tek yeni dosya: `docs/superpowers/plans/2026-10-29-d10-campaign-record.md`. İçinde: `<approval>` ve `<base>` tam hash'leri; `$CK` ve `$PY` yolları; C1–C7 komutları ve çıktıları; güç planı, uyku ayarı satırı, örnekleyici PID'i ve çıktı yolu; açık ağır programlar varsa adları. Yorum ya da öneri ekleme. Commit et ve `git push -u origin results/d10-campaign`.

### Adım 4: kampanyayı başlat (arka planda, sırayla)
1. `C:\UniRideCampaign\bildiri2026` ve `C:\UniRideCampaign\yaem2026` yoksa ya da boşsa devam et; dolu bir klasör varsa dur ve sahibe sor.
2. `C:\wt\d10-campaign\run_campaign.ps1` betiğini Write ile yaz. Betik: `$env:PYTHONPATH = $CK`, `$env:PYTHON_BASIC_REPL = "1"`, çalışma dizini `$CK`; önce
   `& $PY -m academic_benchmark.studies.run --study academic_benchmark/studies/bildiri2026/study.json --mode paper --out C:\UniRideCampaign\bildiri2026`
   sonra (ilkinin çıkış kodu ne olursa olsun)
   `& $PY -m academic_benchmark.studies.run --study academic_benchmark/studies/yaem2026/study.json --mode paper --out C:\UniRideCampaign\yaem2026`
   çalıştırır. Her komutun başlangıç zamanını, çıkış kodunu ve bitiş zamanını `C:\UniRideCampaign\campaign_log.txt` dosyasına ekler (`exit bildiri2026 <kod>` ve `exit yaem2026 <kod>` satırları); stdout/stderr `C:\UniRideCampaign\<study_id>.out.txt` ve `.err.txt` dosyalarına gider.
3. Betiği Claude oturumundan bağımsız başlat: `Start-Process pwsh -ArgumentList '-NoProfile','-File','C:\wt\d10-campaign\run_campaign.ps1' -WindowStyle Minimized -PassThru`. PID'ini al. Birkaç dakika sonra `campaign_log.txt` ile `bildiri2026.out.txt` dosyalarının ilk satırlarını oku ve bir hata görürsen sahibe bildir.
4. Kayda başlatma zamanını, betik yolunu ve PID'i ekle, commit et ve aynı dalı yeniden gönder.

### Adım 5: sahibe teslim
Sahibe kısa bir Türkçe özet ver: C1–C7 sonuçları, kampanyanın başladığı saat, betik ve örnekleyici PID'leri, günlük dosyasının yolu. Ayrıca şunu söyle: koşu yarıda keserse (elektrik, yeniden başlatma) betik aynı komutlara `--resume` eklenerek yeniden başlatılır. Yeniden başlatmayı şef onaylar; önce şefe sorulsun. `DECISION_LOG.md` ve `DURUM.md` dosyalarına dokunma.

### Durma koşulları
Commit'ler beklenenden farklıysa, C1–C7'den biri tutmazsa, çıktı klasörü doluysa ya da bir talimat kurallarla çelişirse işi bırak ve sahibe sor.

---

## İstem B (kampanya bittikten sonra)

Sen UniRide projesinde, güçlü bilgisayarda kampanya sonrası doğrulama oturumusun. İstem A'daki kuralların hepsi geçerli. `--mode paper` bu oturumda hiç çalışmaz.

1. `C:\UniRideCampaign\campaign_log.txt` dosyasında `exit bildiri2026 <kod>` ve `exit yaem2026 <kod>` satırları olmalı. Yoksa kampanya bitmemiştir; dur ve sahibe sor. Yük örnekleyicisi hâlâ çalışıyorsa kendi PID'iyle durdur.
2. `$CK = "C:\wt\d10-campaign-ck"`, `$env:PYTHONPATH = $CK`, çalışma dizini `$CK`. `git -C $CK status --short` boş olmalı. Her çalışma için:
   - `& $PY -m academic_benchmark.studies.verify_manifests C:\UniRideCampaign\<study_id> --repository-root $CK`. Çıktıda manifest sayısı ve profil/analiz planı özetlerinin eşleştiğini söyleyen NOTE olmalı. "Kontrol yapılmadı" NOTE'u başarı sayılmaz.
   - Doğrulama geçerse `& $PY -m academic_benchmark.analysis.campaign_report C:\UniRideCampaign\<study_id> --paper`. Çıkış kodları: 0 rapor yazıldı, 1 rapor başarısız koşularla yazıldı (başarısız hücreler dışarıda), 2 reddedildi (nedenini kayda yaz).
3. Kaydı güncelle: `C:\wt\d10-campaign-kayit` kopyasında `results/d10-campaign` dalını `git pull --ff-only` ile güncelle. `docs/superpowers/plans/2026-10-29-d10-campaign-record.md` dosyasına "After the run" bölümü ekle. İçinde her çalışma için şunlar olsun:
   - çıkış kodu, başlangıç, bitiş ve süre;
   - `index.status`, başarısız koşu sayısı ve listesi (varsa);
   - `verify_manifests` çıktısı;
   - `campaign_report` çıkış kodu, `paper_report.txt` ve `paper_report.json` yolları ve sha256'ları;
   - yük özeti (median, min, max).

   Sonuç sayılarını yorumlama, üstünlük iddiası yazma. Kampanya klasörlerini depoya kopyalama. Commit et ve yalnızca `results/d10-campaign` dalını gönder.
4. Sahibe kısa bir Türkçe özet ver: iki çalışmanın çıkış kodları, doğrulama ve rapor sonuçları, başarısız koşu varsa sayısı. `C:\UniRideCampaign\` ve `C:\wt\d10-campaign-ck` silinmez.
