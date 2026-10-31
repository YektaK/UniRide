# Güçlü bilgisayar: D-10 kampanya raporlarını taşıma klasörüne kopyalama

Önce ana kopyayı güncelleyin: `git pull --ff-only origin WIP`. Sonra aşağıdaki "İstem" bölümünü yeni bir oturuma yapıştırın. Koşu yok; yalnızca dosya kopyalama, sha256 karşılaştırması ve bir commit. Birkaç dakika sürer.

---

## İstem

Sen UniRide projesinde, sahibin güçlü bilgisayarında çalışan bir kopyalama oturumusun. `WIP` dalına yalnızca dizüstündeki şef oturumu birleştirir. Senin işin: D-10 kampanyasının makale raporlarını ve koşu dizinlerini `C:\UniRideCampaign\` altından deponun `tasima/sonuclar/d10-campaign/` klasörüne, ayrı bir çalışma kopyasında ve kendi dalında, bayt bayt kopyalamak; sha256 değerlerini kayıtla karşılaştırmak; dalı göndermek. Kod, profil ya da belge değiştirmezsin.

### Kurallar (hiçbirini çiğneme)
- **Python (Windows):** Python gerekmez, çalıştırma. Etkileşimli Python (çıplak `python`/`py`, `python -i`, `python -`, heredoc ya da stdin ile Python, `python -c`) kesinlikle yasak.
- Dosyaları heredoc, `cat >`, `echo >` ya da `sed -i` ile yazma. Raporları yalnızca `Copy-Item` ile kopyala; içeriklerini açıp yeniden yazma, satır sonlarını değiştirme.
- `taskkill /IM` yok. Sahibin onayı olmadan `pip`/`npm install` yok.
- Git: `WIP`'e commit ya da push yok, birleştirme yok, `git stash` yok, `git config` değişikliği yok, ana kopyada `git checkout`/`git switch` yok. Yalnızca `results/d10-reports` dalına commit et ve yalnızca o dalı gönder.
- `C:\UniRideCampaign\` altında hiçbir şeyi silme, taşıma ya da değiştirme; yalnızca oku ve kopyala. `C:\wt\d10-campaign-ck` kopyasına dokunma.
- `academic_benchmark/tsplib_data/tsplib.db*` dosyalarını okuma, kopyalama, silme. `docs/paper/results` altına hiçbir şey yazma. Lisans metni, `.env` değerleri, kullanıcı adı ya da e-posta yazdırma.
- Commit mesajının sonuna şu satırı ekle: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

### Adım 1: çalışma kopyası
1. Ana kopyada `git fetch origin`, `git log --oneline -3 origin/WIP`. `origin/WIP` içinde `tasima/README.md` ve `.gitattributes` içinde `tasima/sonuclar/** -text` satırı olmalı (`git show origin/WIP:.gitattributes`). Yoksa dur ve sahibe söyle.
2. `git worktree add C:\wt\d10-reports -b results/d10-reports origin/WIP`. Sonraki bütün işler bu kopyada: `$W = "C:\wt\d10-reports"`.

### Adım 2: kopyala ve karşılaştır
Her `<study>` için (`bildiri2026`, `yaem2026`) şu üç dosyayı `C:\UniRideCampaign\<study>\` altından `$W\tasima\sonuclar\d10-campaign\<study>\` altına kopyala: `paper_report.txt`, `paper_report.json`, `run_index.json`. Kopyalamadan önce her dosyanın boyutunu yaz; herhangi biri 20 MB'tan büyükse kopyalama, dur ve sahibe bildir.

Kopyadan sonra `Get-FileHash -Algorithm SHA256` ile hem kaynağın hem kopyanın özetini al. Kayıt `docs/superpowers/plans/2026-10-29-d10-campaign-record.md` ("After the run") şu değerleri verir:

| Dosya | sha256 |
|---|---|
| bildiri2026/paper_report.txt | `09d7686fef70f69729f9f64f3c5bc22336fe72208a7f01e93d5513ed575129a0` |
| bildiri2026/paper_report.json | `0ce425020fc3de81291e125d4be44809edbfc27a41b2372b01bc0370dcabb0d2` |
| yaem2026/paper_report.txt | `75851928bb0d291edf5a818e9b99ddc3306beaaa7258ba6179527b1f675e4af9` |
| yaem2026/paper_report.json | `74f6016c1e4a4630400aa6fad1e17c5ad2b830fb207107ce7bd858044a6ef38a` |

Kayıt `run_index.json` için yalnızca "index sha256" verir: bildiri2026 `410d2767fccfe65865d3562a84b388e9305b99646eee455f05be52fe21f71a85`, yaem2026 `72a6bba626ce1d6294142ab8f8704371e5f200d6d799ca1bb7654fa0cdabac22`. Dosya özeti bununla aynıysa "eşit", değilse "farklı (index sha256 dosya özeti olmayabilir)" yaz; bu durumda durma.

Dört rapor dosyasından birinin kaynağı ya da kopyası tablodaki değerle eşleşmezse commit etme, dur ve sahibe bildir.

### Adım 3: commit ve gönderme
1. `$W` içinde `git add tasima/sonuclar/d10-campaign`, sonra `git diff --cached --stat`: yalnızca altı yeni dosya görünmeli.
2. `git check-attr text -- tasima/sonuclar/d10-campaign/bildiri2026/paper_report.txt`: `text: unset` olmalı.
3. Commit et (mesaj: `results: D-10 campaign paper reports and run indexes copied byte-exact into tasima/sonuclar/d10-campaign (sha256 equal to the campaign record)`). Sonra `git status --short` boş olmalı ve `Get-FileHash` altı dosyada Adım 2'deki değerleri yeniden vermeli.
4. `git push -u origin results/d10-reports`.

### Adım 4: sahibe rapor (Türkçe, sade)
Altı dosyanın boyutu ve sha256'sı (kaynak = kopya = kayıt), `run_index.json` için eşit/farklı, commit hash'i, gönderilen dal. Son cümle: "Dizüstündeki şefe `results/d10-reports` dalının hazır olduğunu söyleyin."
