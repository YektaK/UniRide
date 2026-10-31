# DURUM — devam eden işler

Son güncelleme: 2026-10-31 (D-10 kampanyası tamam; G1 birleşti, D-10 dalları temizlendi, MT1 B ve D hatları başladı). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir. Sahip dışarıdayken şefin aldığı kararlar: DECISION_LOG **A20** (L1–L13) ve **A21** (MT6 takip planı, OQ-F1..F8); her biri seçenekler, artı/eksi, seçim, geri alma yolu ile.

## Durum

| İş | Durum |
|---|---|
| Gate D (Paket D) | **KAPANDI** (D-13, `04612880`; kanıt `docs/superpowers/plans/2026-10-26-gate-d-mt6-close-evidence.md`; A18). Ölçüt 6'nın değer eşleşmesi ön-onay commit'ine ertelendi (A20 L11). D-04b2 TAMAM (aşağıda); D-12 yayın yalnız sahip izniyle. |
| MT6 | **KAPANDI** (MT6-07; A19). |
| MT6 takip planı (sota_common arşivi, shim'ler, denetim L3 ve L10, RUN 3-opt hamlesi) | **KAPANDI** (MT6F-09, `e8851f34`; kanıt `docs/superpowers/plans/2026-10-27-mt6-followup-close-evidence.md`; A21). Yalnız `SOTA-RUN-TSP` sonuçları değişti; Bildiri/YAEM değişmedi. |
| Makale raporu komutu, üretim çözücü kaydı, analiz cilası 1–2, birikmiş işler 1 | BİRLEŞTİ (A20 L2, L3, L7, L10, L12, L13). |
| CI: analiz testleri akademik ek paket olmadan toplanıyor | BİRLEŞTİ `13819af5` (D-04a eki; PR #27 kapatıldı). Gece işindeki `UNIRIDE_REQUIRE_ANALYSIS_EXTRA=1` ilk gece koşusunda kontrol edilecek. |
| MT1 (zaman pencereleri, okula dönüş, dürüst araç sayısı) | KISMEN BİRLEŞTİ (O09; plan `docs/superpowers/plans/2026-10-27-mt1-time-window-unification.md`). Hemen-birleşecek küme BİRLEŞTİ: MT1-10 `8ad1b94b`, 08 `0fc7bc7b`, 07 `a74aff76`, 01 `7584f2fa`, 02 `8513c2b6`, 03 `f9bf58f6`, 04 `ac22a383`. İlk kapanış kaydı + demo kabulü (228/228 dalga öncesi/sonrası/arşiv aynı): `docs/superpowers/plans/2026-10-28-mt1-first-close-evidence.md`; H16 pano notu birleşti. **B ve D hatları BAŞLADI (2026-10-31, sahip OK; O09 notu):** MT1-11 BİRLEŞTİ `9f8c0b73` (H16; Opus ONAY r2; takip işleri O09 notunda; sahip işi: `tsplib.db`'deki Solomon örneklerinin yeniden aktarılması). MT1-05 Opus denetiminde (`feat/mt1-05-decoder-tw-simulator`; H3 ofset 0 nedeni bulundu ve dalda düzeltildi). MT1-12 başlıyor (11 birleşti); 06, 05'ten sonra; 09, 06'dan sonra; sonra 4b koşusu ve MT1-13 ikinci kayıt. Açık: `arrival_minutes` anlamı (sahip sorusu). |

## Makale ölçeğinde koşudan önce zorunlu

- Yazılım ön koşulları TAMAM. Kalanlar donanım ve sahip işleri:
- D-04b2 TAMAM (2026-10-28, A18; kayıt `docs/superpowers/plans/2026-10-27-d04b2-strong-pc-measurement.md`): güçlü PC'de seri tahmin Bildiri 14,02 sa, YAEM 9,56 sa sabit bütçe + YAEM native 5,85 sa (toplam ~29,4 sa).
- Kampanyadan önce güçlü PC'de: dizüstündeki güncel `tsplib.db` oraya kopyalanacak ve iki örnek-kümesi testi orada geçmeli (A18 D-04b2 karar a); `pyvrp<0.14` sınırı (karar b, ayrı küçük iş).
- Ön-onay değerleri BİRLEŞTİ `cb449ed4` (A18): 30 koşu, native 1000 ve bütün algoritmalar (Bildiri listesi 2→10 düzeltildi), analiz planları `minimum_n_per_cell` 30 ve `unresolved` boş, `.gitattributes`; durumlar `draft`.
- YAEM adlandırması BİRLEŞTİ `ecea6ee6` (`yaem2026-v1`, yayın yeri "YAEM 2026"); Bildiri yayın yeri BİRLEŞTİ `bcef9feb` ("14. Uluslararası Göbeklitepe Bilimsel Çalışmalar Kongresi"); onay öncesi profil değerleri tamam. G9 deneme kontrolü geçti (A18). Koşu planı taslakları dalda: `docs/d10-run-plans` (`de3efae2`, birleşmedi; `[EKSİK]` alanlar var). Gece CI düzeltmesi BİRLEŞTİ `8ef7a23e` (A18); elle tetiklenen gece koşusu Linux'ta yeşil (8956 geçti).
- Bildiri native yeniden ölçümü BİRLEŞTİ `44c47434` (A18): Bildiri sabit bütçe 13,69 sa + native 5,83 sa (2100 koşu); YAEM 9,53 + 5,89 sa; seri toplam ~34,9 sa. `pyvrp<0.14` sınırı `pyproject.toml`'da var.
- Etkinleştirmeye hazır testler BİRLEŞTİ `b4946252` (A18 karar a; Opus ONAY). Koşu planları `docs/d10-run-plans-v2` dalında (`bd3d4e5b`, olgu ONAY); onay commit'inde WIP'e girer.
- Temel commit `1a322a8f`; güçlü PC tam test koşusu `a06bc20a` (API'de 1 ortam hatası, sahip kabul etti); kayıt kampanyadan sonra WIP'e birleşti `23d416c0`.
- **ONAY COMMIT'İ `2c7c5996` (2026-10-29, DECISION_LOG A22; Opus ONAY; gönderildi).** Planlar `docs/run_plans/` (olgu ONAY r3). Eski taslak dalı `docs/d10-run-plans` silindi (sahip OK).
- **KAMPANYA TAMAM (2026-10-31, A22 sonuç notu).** Kayıt `docs/superpowers/plans/2026-10-29-d10-campaign-record.md` (birleşti `960f1282`). bildiri2026 6300/6300, yaem2026 3960/3960, 0 başarısız; `verify_manifests` OK; `campaign_report --paper` iki çalışmada da exit 0. Çıktılar güçlü PC'de `C:\UniRideCampaign\<study_id>\` (koşu dışarı yazar); iki çalışmanın `paper_report.txt/.json` ve `run_index.json` dosyaları WIP'te `tasima/sonuclar/d10-campaign/` (G1 birleşti `1a77d7a9`, sha256 kayıtla aynı; A23). `C:\wt\d10-campaign-ck` artık gerekmiyor; sahip güçlü PC'de silebilir. OQ-F7 birleştirme yasağı kapandı.
- D-10 dalları temizlendi (2026-10-31, sahip OK; A23 notu): `results/d10-campaign`, `results/d10-reports`, `results/d10-base-suite`, `docs/d10-run-plans-v2` ve `C:\wt\d10-run-plans-v2` silindi; v2'nin ucu `archive/d10-run-plans-v2-20261031` etiketinde.
- Sırada: raporların yazı hattına alınması (makaleye D-10 sonuçları); sonra D-13 bloğu o commit'te yeniden ve D-12 (sahip izniyle; A22 notu).

## Bilgisayarlar arası görevler

Kurallar `tasima/README.md` ve `AGENTS.md` ("Cross-Machine Tasks"); karar A23. Görev durumu yalnızca bu tabloda. Durumlar: `bekliyor`, `başladı`, `sonuç geldi`, `tamam`.

| No | İstem dosyası | Bilgisayar | Durum | Sonuç dalı |
|---|---|---|---|---|
| G1 | `tasima/gorevler/2026-10-31-guclu-pc-d10-rapor-kopya-istem.md` (D-10 raporları + koşu dizinleri → `tasima/sonuclar/d10-campaign/`) | güçlü PC | tamam (birleşti `1a77d7a9`, 2026-10-31) | `results/d10-reports` (silindi) |

Önceki güçlü PC istemleri (D-04b2, Bildiri native, temel commit testi, D-10 kampanyası) `tasima/gorevler/` altında; hepsi tamam.

## Sahibin kararını bekleyenler

- D-12 yayın (WIP → main, taslak PR) yalnız sahibin açık izniyle. 2026-10-31 sahip: şimdilik bekle; D-10 sonuçları makaleye girince D-13 bloğu yeni commit'te koşulur, D-12 oradan (A22 notu).
- A20 (L1–L13) ve A21 (OQ-F1..F8) şef kararlarının sahip tarafından gözden geçirilmesi (2026-10-31 sahip: kendisi okuyacak).

## Ertelenen işler

- Makale koşusundan sonra: `tsp_matrix_metaheuristics/*` seed varsayılanları (A21 OQ-F4 a); Or-opt native kabulünün kuyruk yamasından ana kümelere taşınması (A20 L5).
- Ayrı plan: `ls_engine` 2-opt/Or-opt/swap katmanlarının arka uca bağlı davranışı (A21 OQ-F8 a).
- MT7 ile: `run/status`, `run/stop` BFF rotaları (H14 ile birlikte).
- Cila: `uniride.egg-info/SOURCES.txt` silinmiş yolları listeliyor; shim koruma testi `scripts/` taramıyor; sabit-matris eşitlik testinde kullanılmayan `symmetric` parametresi; RUN'un 3-opt dışı hamleleri ATSP'de ters çeviriyor; canlı yönetici araç planlama sayfasında matris-hata bildirimi testi yok; `test_mutation_proof_tsp.py:109` sahte fonksiyonu kaldırılan anahtar sözcüğü kabul ediyor; `/compare` ve rota-test sayfası `termination_reason`/`solver_code_version` taşımıyor (plan kaydetmiyorlar).
- D-05 cila: plana örnek başına uygulanabilirlik beyanı yok (karma aile reddedilir).
- J11 README'den `scripts/compare_exact_day_joint_runs.py` betiğine işaret (yazı hattı).
- `scratch/test_hho.py`; eski cila listesi (C-12/C-16b/J3/ayrıştırıcı).
