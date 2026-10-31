# Taşıma klasörü (dizüstü ↔ güçlü PC)

Bu klasör, iki bilgisayar arasında git ile taşınan görevleri ve sonuçları tutar (DECISION_LOG A23).

- `gorevler/`: bir bilgisayara verilen istem dosyaları. Dosya adı `YYYY-AA-GG-<bilgisayar>-<konu>-istem.md`. İstem, sahibin yeni bir oturuma yapıştıracağı metni ve uyulacak kuralları içerir. 2026-10-31'den önceki istemler `docs/handoff/` altındaydı; eski kayıtlar o yolu anar.
- `sonuclar/`: bir görevin depoya alınması kararlaştırılmış çıktıları, `sonuclar/<görev>/...` altında. Buradaki dosyalar bayt bayt korunur (`.gitattributes`: `tasima/sonuclar/** -text`), çünkü kayıtlar sha256 değerlerini tutar. Makale ölçeğindeki koşular yine depo dışına yazar (`study.output_policy.paper_scale_location` = `external`); buraya yalnızca koşu bittikten sonra, kayıttaki sha256 ile eşleşen kopyalar girer. `docs/paper/results/` bu klasörle karıştırılmaz.

## Görev durumu

Görevlerin durumu yalnızca kök dizindeki `DURUM.md` dosyasının "Bilgisayarlar arası görevler" tablosunda tutulur (no, istem dosyası, bilgisayar, durum, sonuç dalı). Bu klasörde ayrı bir durum dosyası yoktur.

Bilgisayar adları tabloda `dizüstü` ve `güçlü PC`. Oturum hangi bilgisayarda olduğunu deponun yolundan anlar: güçlü PC'de yol `Masaüstü` klasöründen, dizüstünde `Desktop` klasöründen geçer.

## İş akışı

1. Dizüstündeki şef oturumu istemi `gorevler/` altına yazar, `DURUM.md` tablosuna `bekliyor` satırı ekler ve `WIP`'e gönderir.
2. Diğer bilgisayarda `git pull --ff-only origin WIP`; oturum başında `AGENTS.md` gereği tablo okunur ve o bilgisayara atanmış `bekliyor` görev sahibe bildirilir. Görev kendiliğinden başlamaz; sahip istemi yeni bir oturuma yapıştırır.
3. Görev yalnızca kendi `results/...` dalına commit eder ve onu gönderir; `WIP`'e commit, push ya da birleştirme yapmaz.
4. Şef sonuç dalını okur, `--no-ff` ile birleştirir ve tablodaki satırı `tamam` yapar.
