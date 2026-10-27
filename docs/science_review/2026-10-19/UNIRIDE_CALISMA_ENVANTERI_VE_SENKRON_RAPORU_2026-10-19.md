# UniRide: Claude Science çalışma envanteri ve Claude Code ile senkron durumu

**Anlık görüntü:** 19 Ekim 2026, 23:40 (yerel saat)
**Depo:** `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide`
**Hazırlayan:** Claude Science (salt okunur inceleme; depoda hiçbir dosya değiştirilmedi, Git'te hiçbir işlem yapılmadı)

> Claude Code bu inceleme sırasında da commit atıyordu. İnceleme başladığında `WIP` dalı `559826b5` (22:37) üzerindeydi; 23:40'ta `320d9083` (23:39) üzerinde. Aradaki sürede `docs/gate-c-plan` dalı `WIP`'e birleştirildi, dal ve worktree'si kaldırıldı. Aşağıdaki Git bilgileri 23:40 anlık görüntüsüdür.

---

## 1. Özet

1. **İki Claude Science oturumu var.** Bu projede iki Claude Science oturumu UniRide üzerinde çalıştı:
   - `ef0bc5e9`, "Literature Graph Analysis for Algorithm Inventory" (13–17 Ekim; 7 alt ajan). Literatür ve kod denetimi, algoritma geliştirme, Astra 6 revizyonları, öğrenilmiş örüntüler, nihai bulgular, kanıt arşivi ve yeniden üretim paketi bu oturumda yapıldı.
   - `0908ac40`, bu oturum (16–19 Ekim). Akademik strateji ve finansman raporu ile bu envanter burada üretildi.
2. **Claude Science Git'e hiç yazmadı.** Transkriptlerde depo yolunu içeren araç çağrılarında `commit`, `checkout`, `merge`, `stash`, `push`, `clean` ya da `worktree add/remove` geçmiyor; yalnızca okuma komutları (`status`, `log`, `rev-parse`, `diff --stat`, `grep`) var. İzlenen (tracked) hiçbir dosya değiştirilmedi: ana klasörde şu an bekleyen tracked değişiklik sıfır.
3. **Claude Science çıktılarının büyük kısmı hiçbir dalda yok.** 13 Ekim literatür çıktıları (8 dosya), sahibi tarafından `WIP`'e commit'lendi (`c78b679d`, `90c88cdb`). Sonraki tüm Claude Science üretimi ana çalışma klasöründe **izlenmeyen (untracked) dosya** olarak duruyor: **181 dosya, yaklaşık 6,8 MB**, iki klasör ağacında:
   - `docs/science_review/2026-10-13/astra6_design_brief/` (176 dosya)
   - `docs/akademik_strateji/2026-10-16/` (5 dosya)
4. **Kopukluğun nedeni.** Claude Code iş paketlerini worktree'lerde (`.claude/worktrees/…`) commit'lenmiş içerik üzerinden yürütüyor. İzlenmeyen dosyalar worktree'lere taşınmaz. `docs/DECISION_LOG.md`'de Claude Science'a yalnızca iki atıf var: 13 Ekim süreç kararı (P05) ve literatür incelemesine dayanan etiket düzeltmeleri. Astra 6 revizyonları, `NIHAI_BIRLESIK_BULGULAR…`, kanıt arşivi, yeniden üretim paketi ve akademik strateji raporu Claude Code'un hiçbir commit'inde ya da belgesinde geçmiyor.
5. **İki taraf aynı soruları ayrı ayrı çözmüş.** 15–19 Ekim'de Claude Code "exact" hattını (WP-E1 … WP-E8, WP-E10) inceleme, test ve manifestlerle `WIP`'e commit'ledi. Claude Science da 13–17 Ekim'de aynı soruları (kesin dalga çözümü, gün düzeyi filo, tipli filo) kendi prototipleriyle yanıtlamıştı. Kayıtlı sonuçlar birbiriyle tutarlı görünüyor; ikisi de 228/228 dalgada optimum buluyor. Ancak kod tabanları ayrı ve aralarında henüz sistematik bir karşılaştırma yapılmadı (Bölüm 5).
6. **Akademik strateji raporu iki şeyi görmeden yazıldı.** 16 Ekim raporu Claude Code'un exact altyapısını ve depodaki mevcut konferans çalışmalarını bilmiyordu: ISARC, Göbeklitepe bildirisi "Özel Gereksinimli Bireyler İçin Okul Servisi Uygulaması" ve YAEM 2026. Rapordaki makale ve bildiri önerileri bunlarla hizalanmalı (Bölüm 6).

---

## 2. Git durumu (19.10.2026, 23:40)

| Öğe | Durum |
|---|---|
| Ana klasörde checkout edilen dal | `WIP` @ `320d9083` (23:39), `origin/WIP` ile eşit (önde/geride commit yok) |
| `main` | `origin/main` 30.09.2026'da kalmış; varsayılan entegrasyon dalı `WIP` (README politikası) |
| Yerel dallar | `WIP`; `docs/method-note-h06` (WIP'e **birleşmiş**, silinebilir); `research/architecture-2026-10` (10.10.2026, **birleşmemiş**, uzak dalı yok) |
| Kayıtlı worktree | Yalnızca ana klasör (`gate-c-plan` worktree'si 23:39'da kaldırıldı) |
| Kayıtsız worktree klasörleri | `.claude/worktrees/wp-e10/` (boş); `.temp/worktrees/codex-demo-safe-fixes`, `codex-fleet-evidence-fix`, `codex-ride-limit-fix` (7 Ekim) |
| Stash | `stash@{0}` "pre-wip-fast-forward-2026-09-30", `stash@{1}` "autostash" |
| Bekleyen tracked değişiklik | Yok |
| İzlenmeyen dosya | 200 (ayrıntı: Bölüm 3 ve CSV) |

**13–19 Ekim'de tüm dallarda commit sayısı:** 13 Eki 48, 14 Eki 78, 15 Eki 129, 16 Eki 24, 17 Eki 51, 18 Eki 59, 19 Eki 74. Hepsi Claude Code/sahip hattından.

---

## 3. Depodaki izlenmeyen dosyaların kaynağa göre dökümü

| Kaynak | Klasör | Dosya | Boyut | Artifakt deposunda birebir yedek |
|---|---|---|---|---|
| **Claude Science, diğer oturum (ef0bc5e9)** | `docs/science_review/2026-10-13/astra6_design_brief/` (kök dosyalar) | 29 | 1,3 MB | 26 |
| | `…/astra6_design_brief/nihai_kanit_arsivi_2026-10-17/` | 90 | 2,4 MB | 90 |
| | `…/astra6_design_brief/sekiller_ogrenilmis_oruntu/` | 3 | 0,7 MB | 3 |
| | `…/astra6_design_brief/yeniden_uretim_paketi_2026-10-17/` | 54 | 1,5 MB | 26 |
| **Claude Science, bu oturum (0908ac40)** | `docs/akademik_strateji/2026-10-16/` | 5 | 0,7 MB | 4 (5. dosya bağlantıları göreli yapılmış kopya) |
| Codex | `astra6_design_brief/` kökü: `ASTRA6_YENI_ALGORITMA_TASARIMLARI.md`, `CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14.md`, `CODEX_BUTUNSEL_DEGERLENDIRME_VE_AKADEMIK_KATKI_2026-10-16.md` | 3 | 0,2 MB | 2 (kullanıcı yüklemesi) |
| Codex (muhtemel) | `docs/science_review/2026-10-13/codex_trio_evidence/` (`probe.py`, `probe-results.json`) | 2 | 13 KB | 0 |
| Kullanıcı/Codex görev dosyaları | `docs/CODEX_*.md` (9–13 Ekim) | 9 | 0,1 MB | 1 |
| Kullanıcı/Codex | `docs/paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD_1fe7325.docx` | 1 | 0,5 MB | 0 |
| Claude Code (ATSP-19 yedeği artığı) | `academic_benchmark/tsplib_data/tsplib.db.bak-atsp19-2026-10-13-shm/-wal` | 2 | 32 KB | 0 |
| Diğer/eski | `INSTRUCTION_REVIEW_2026-09-07.md`, `scratch_dummy` (0 bayt) | 2 | 5 KB | 0 |

Dosya bazında tam liste (kaynak, boyut, değiştirilme zamanı, SHA-256, yedek durumu) için CSV'ye bakın.

**Yedek riski.** Claude Science dosyalarının 149'u uygulamadaki artifakt deposunda birebir duruyor. Kalan 32 dosyanın tek kopyası bu çalışma klasöründe:
- yeniden üretim paketinin ara çıktıları (`ciktilar/*.jsonl`, `lodo/prune_in.pkl`) ve sürücü betikleri (`surucu/*.py`);
- kök klasördeki üç belgenin (`ASTRA_DEGERLENDIRME_2026-10-15.md`, `ML_ROTA_LITERATUR_2026-10-15.md`, `SCIENCE_OGRENILMIS_ORUNTU_CALISMASI_2026-10-15.md`) artifakttan farklı sürümleri.

Ana klasörde `git clean -fd` çalıştırılırsa ya da klasör yeniden klonlanırsa bu 32 dosya geri getirilemez.

### 3.1 Claude Science çıktılarının içerik haritası

**13 Ekim** (`docs/science_review/2026-10-13/`, **commit'li**, 8 dosya): `ALGORITHM_LITERATURE_SOTA_2026-10-13.md`, `algorithm_literature_table.csv`, `code_audit_findings.json`, `dogrulanmadi_yanitlari.csv`, `kaynakca.csv`, `lit_hits_K1-K4.json`, `lit_hits_K5-K7.json`, `lit_hits_K8_K11.json`.

**13–17 Ekim** (`astra6_design_brief/`, **izlenmeyen**):
- Codex için hazırlanan tasarım brifi: `00_PROMPT_ASTRA6_YENI_ALGORITMA_TASARIMI.md` ve 17 ek (`01_…`–`17_…`). Eklerin bazıları depo belgelerinin kopyası.
- Codex belgelerinin Claude Science revizyonları: `ASTRA6_YENI_ALGORITMA_TASARIMLARI_ClaudeScience.md` ve `…_ClaudeScience1.md`; `CODEX_OGRENILMIS_ROTA_ORUNTULERI_TASARIMI_2026-10-14_ClaudeScience.md` ve `…_ClaudeScience1.md`.
- Değerlendirme ve çalışmalar: `ASTRA_DEGERLENDIRME_2026-10-15.md`, `astra_issues.csv`, `SCIENCE_OGRENILMIS_ORUNTU_CALISMASI_2026-10-15.md`, `ML_ROTA_LITERATUR_2026-10-15.md`, `ml_rota_kaynakca.csv`, `sekiller_ogrenilmis_oruntu/`.
- Codex'in 16 Ekim değerlendirmesine yanıt: `CLAUDE_SCIENCE_YANIT_BUTUNSEL_DEGERLENDIRME_2026-10-17.md`.
- **Yetkili tek bulgu belgesi:** `NIHAI_BIRLESIK_BULGULAR_VE_YOL_HARITASI_2026-10-17_ClaudeScience.md`. Önceki iddiaların yerine geçer; §7'de 23 düzeltme var.
- `nihai_kanit_arsivi_2026-10-17/`: 90 dosya kod ve ham sonuç, SHA-256 manifesti, README. Arşivdeki betikler depo kökünü sabit yolla içeriyor; çalıştırılabilir kopyaları yeniden üretim paketinde.
- `yeniden_uretim_paketi_2026-10-17/`: `src/`, `surucu/`, `ciktilar/`, `requirements.txt`, README. Tek giriş noktası `surucu/calistir.py`; depo kökü `UNIRIDE_ROOT` ortam değişkeninden okunuyor. README'ye göre 17 Ekim'de ana hatlar yeniden koşturuldu: `dogrula.py` 61/61 kontrolü geçti; WAVE-EXACT 228/228 hücrede rota sayısı ve dakika arşivle aynı çıktı, sertifika ihlali sıfır. Yeniden koşturulmayan hatlar README'nin "Kalan işler" bölümünde.

**16 Ekim** (`docs/akademik_strateji/2026-10-16/`, **izlenmeyen**): akademik strateji raporu (md ve docx), fayda-maliyet figürü, seçenek tablosu (CSV), puan simülasyonu (CSV).

**Depo dışında:** Uygulamanın artifakt deposunda bu projeye ait 170 artifakt sürümü var. Oturumların çalışma klasörleri (workspace) boşta kalınca temizleniyor; kalıcı olanlar artifaktlar ve depoya kopyalanan dosyalar.

---

## 4. Aynı dönemde Claude Code'un `WIP`'e commit'ledikleri (seçme)

| Tarih | İş paketi | Kayıtlı sonuç (commit mesajından) |
|---|---|---|
| 13 Eki | Claude Science literatür çıktıları + etiket düzeltmeleri; ATSP-19 veri seti; legacy sonuç karantinası (A10, A11, A13) | Claude Science bulguları metin düzeltmesi olarak işlenmiş |
| 14–15 Eki | Denetim düzeltmeleri (H6, H12, H15, H17, M4, M8, M18, M26 …) | — |
| 15 Eki | WP-E1 rota sayımı + kaba kuvvet kâhini; WP-E2 AMPL küme bölümleme altyapısı | 500 örnekte kâhinle aynı; Gurobi ve HiGHS uyumlu |
| 16 Eki | WP-E3 GOAL 1 koşucusu (tek tip) | 228 dalganın tamamı optimum; HiGHS uyumlu |
| 17 Eki | WP-E10 filo yeniden koşumu; WP-E4a tipli menüler | 1872 seçenek: 1705 optimum, 167 olurlu çözümsüzlüğü kanıtlı |
| 18 Eki | WP-E4b birleşik menüyle gün seçimi; WP-E6 boşluk raporu; WP-E7 kesin TSP/ATSP (DFJ); ölçekleme sondası | 120 hücre; birleşik menü 11 hücrede GA'dan az araç. 16 TSPLIB örneği + ft53'te 17/17 yayımlanmış optimum yeniden üretildi |
| 18 Eki | `docs/paper` yöntem notuna §7 "exact reference" bölümü | — |
| 19 Eki | WP-E8 `exact_reference_v1` protokolü; web-akademik ayrıştırma; H8/M5/L2 düzeltmeleri; **Gate C planı** (A17) | Gate C planı "Bildiri" ve "YAEM" çalışma profillerini makale setine hizalıyor (C-19, C-13) |

---

## 5. Örtüşme haritası: Claude Science prototipi ve Claude Code karşılığı

| Konu | Claude Science (izlenmeyen) | Claude Code (`WIP`'te commit'li) | Durum ve öneri |
|---|---|---|---|
| Kesin dalga çözümü | WAVE-EXACT: alt küme DP + iki aşamalı HiGHS küme bölümleme; 228/228 kanıtlı optimum; GA-Split 19 dalgada optimum dışı | WP-E1 sayım + WP-E2 AMPL küme bölümleme + WP-E3 koşucu; 228 dalganın tamamı optimum | **Aynı soru.** Kanonik sürüm Claude Code'unki (test, inceleme, manifest). Claude Science sonucu bağımsız çapraz doğrulama olarak kullanılmalı: dalga başına K* ve dakika karşılaştırması |
| Gün düzeyi ve tipli filo | DAY-JOINT/TYPED + LB0: olay noktası eşzamanlılık modeli; haftalık filo R=60/70'te 6'dan 5'e | WP-E4a tipli menüler, WP-E4b birleşik menüyle gün seçimi, WP-E10 | **Benzer soru, farklı tanım.** Claude Science ortak gün modeli kurdu; Claude Code menü birleşimiyle seçim yapıyor. Sonuçların hangi tanımla kıyaslanacağına karar verilmeli |
| Büyük dalgalar | ESN-SP, S1–S3 sentetik ölçek | Ölçekleme sondası (20–80 öğrenci, 231 koşu) | Kısmi örtüşme |
| TSP | ILS-fast, LKH karşılaştırması, ft53 | WP-E7 kesin TSP/ATSP referansı | Tamamlayıcı (sezgisel ve kesin referans) |
| Trio denetimi / adil protokol | E2BSO/R2DMA/P-AOEA mekanizma denetimi, eşit süreli ILS kontrolü | 13 Ekim etiket düzeltmeleri, M26, A13 karantina, Gate C (adil protokol, memetik cilalama M19) | Claude Code 13 Ekim bulgularını uygulamış; sonraki denetim ayrıntıları ona ulaşmamış |
| Öğrenilmiş örüntüler (ML) | GBM yay tahmini, negatif sonuçlar | Yok | Yalnız Claude Science'ta |
| Yayın planı | Akademik strateji raporu (16 Ekim) | Gate C: Bildiri ve YAEM profilleri; yöntem notu §7 | **Hizalanmamış** (Bölüm 6) |

---

## 6. Akademik strateji raporu için düzeltme notu

Depoda şu önceki çalışmalar bulunuyor:
- `archive/academic_benchmark/bildiri2026_legacy/bildiri2026/Bildiri.md`: "Özel Gereksinimli Bireyler İçin Okul Servisi Uygulaması". Sosyal sorumluluk kapsamındaki "Engelsiz Ulaşım" projesinin vaka analizi; 2-opt, 3-opt, Or-opt, GA ve PSO TSPLIB'de karşılaştırılıyor. Kaynak dosya yolu "Gobeklitepe" klasörünü gösteriyor.
- `archive/academic_benchmark/yaem2026_legacy/`: YAEM 2026 uygulama özeti. Önceki ISARC çalışmasının kurgusunu makine öğrenmesi destekli hiperparametre aktarımıyla genişletiyor.

Bu yüzden 16 Ekim raporunda şu güncellemeler gerekli:
1. Bu üç bildiri (ISARC, Göbeklitepe, YAEM 2026) portföye "mevcut eser" olarak eklenmeli. Önerilen SCI makaleleri bunlara atıf yapıp açıkça ötesine geçmeli (mükerrer yayın riski). Doçentlik 8. maddesinde aynı toplantıdan yalnızca bir bildiri puanlanıyor ve tavan 10 puan; bu bildirilerin CPCI kapsamı ayrıca kontrol edilmeli.
2. Amiral makale (P1) ve filo makalesi (P2), Claude Code'un commit'li `exact_reference_v1` altyapısına dayanmalı. Claude Science prototipleri bağımsız doğrulama olarak kullanılmalı.
3. Gate C'deki Bildiri ve YAEM profilleri (C-19, C-13) ile rapordaki CNF-1, CNF-2 ve TRD-1 önerileri tek bir yayın takviminde birleştirilmeli.

---

## 7. Öneriler (sırasıyla; Git işlemleri size veya Claude Code'a bırakıldı)

1. **Önce yedek.** Claude Science'ın 181 izlenmeyen dosyasını commit'leyin. Ayrı bir dal açmak en temizi (ör. `docs/science-review-2026-10`, `WIP`'ten). Kapsam: `docs/science_review/2026-10-13/astra6_design_brief/` ve `docs/akademik_strateji/`. Toplam yaklaşık 6,8 MB. En büyük ikili dosya `ciktilar/lodo/prune_in.pkl` (0,5 MB); isterseniz dışarıda bırakılabilir.
2. **Claude Code'a köprü notu.** Ekteki notu `DECISION_LOG`'a P05'in devamı olarak işletin. Yetkili belgenin `NIHAI_BIRLESIK_BULGULAR…` olduğunu, exact hattında kanonik kodun Claude Code'unki olduğunu ve Claude Science prototiplerinin bağımsız doğrulama olduğunu kayda geçirin.
3. **Çapraz doğrulama görevi.** Claude Science'ın 228 dalga sonuçlarını Claude Code'un WP-E3 `exact_routes.json` ve gap tablolarıyla dalga dalga karşılaştırın (K*, dakika, rota kümesi). Salt okunur ve kısa bir iş; isterseniz bir sonraki adımda yapabilirim.
4. **Akademik strateji raporunu güncelleyin.** Bölüm 6'daki üç düzeltmeyi işleyin.
5. **Çalışma kuralı.** Tek yazar ilkesi: Claude Science yalnızca `docs/science_review/<tarih>/` altına yazsın, kod klasörlerine dokunmasın. Bu dosyaları Claude Code bir "science import" commit'iyle içeri alsın. Claude Science'a görev verirken başlangıç commit'ini (`WIP` hash'i) belirtin; böylece hangi kod durumunu incelediği kayıtlı olur.
6. **Temizlik (isteğe bağlı, size ait).**
   - `git worktree prune`; boş `.claude/worktrees/wp-e10/` ve eski `.temp/worktrees/codex-*` klasörleri.
   - Birleşmiş `docs/method-note-h06` dalının silinmesi.
   - `research/architecture-2026-10` ve iki eski stash için karar.
   - `tsplib.db.bak-…-shm/-wal` artıkları ve `scratch_dummy`.

### Ek: Claude Code'a verilebilecek köprü notu

> Claude Science 13–19 Ekim'de UniRide üzerinde salt okunur analiz yaptı ve çıktıları izlenmeyen dosya olarak `docs/science_review/2026-10-13/astra6_design_brief/` ile `docs/akademik_strateji/2026-10-16/` altına yazdı. Bu dosyalar henüz hiçbir dalda yok. Yetkili bulgu belgesi `NIHAI_BIRLESIK_BULGULAR_VE_YOL_HARITASI_2026-10-17_ClaudeScience.md`'dir. Exact hattında (WP-E1…E8) kanonik kod sizinkidir; Claude Science'ın WAVE-EXACT ve DAY-JOINT/TYPED prototipleri bağımsız doğrulama içindir, üretim koduna taşınmayacak. Lütfen (1) bu klasörleri ayrı bir dalda commit'leyin, (2) DECISION_LOG'a P05 devamı olarak bir kayıt düşün, (3) 228 dalga sonuçlarının çapraz karşılaştırmasını ayrı bir iş paketi olarak planlayın.

---

## 8. Yöntem ve sınırlar

- Claude Science oturumları ve dosya yazımları, uygulamanın oturum veritabanından (oturum listesi, araç çağrısı transkriptleri, hücre kayıtları) ve artifakt sağlama toplamlarından çıkarıldı.
- Depo durumu `git` okuma komutlarıyla ve dosya sistemi taramasıyla belirlendi. Her izlenmeyen dosyanın SHA-256'sı artifakt sürümleriyle eşleştirildi: 200 dosyanın 152'si eşleşti.
- Eşleşmeyen dosyaların kaynağı klasör, ad ve içerik işaretlerine göre atandı. "Codex (muhtemel)" etiketi bir çıkarımdır.
- Transkript taraması yalnızca depo yolunu açıkça içeren araç çağrılarını kapsıyor. Git yazma komutu bulunmaması bu kapsam içinde geçerlidir. Bekleyen tracked değişiklik olmaması da aynı sonucu destekliyor.
- Claude Code tarafındaki sonuçlar commit mesajlarından aktarıldı; Claude Code'un sonuç dosyaları bu raporda yeniden hesaplanmadı.
