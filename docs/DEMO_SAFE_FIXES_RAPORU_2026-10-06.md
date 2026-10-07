# UniRide ayrı dallarda düzeltme ve demo raporu

Tarih: 6 Ekim 2026. Kapsam: doğrulanan iki hata, birbirinden bağımsız düzeltme dalları ve bu düzeltmeleri birleştiren yerel demo sürümü.

## Dallar ve korunan başlangıç

| Dal | Kod commit'i | Amaç |
| --- | --- | --- |
| `WIP` | `613531955e720c48a49203b71fa678abeb33d921` | Korunan mevcut sürüm |
| `codex/ride-limit-fix` | `4bae8ddcd949be485f6fef62fac9045ac14329a5` | Yolculuk sınırı ön kontrolü |
| `codex/fleet-evidence-fix` | `54a8af1` | Gerçek filo yeterliliği sonucunun kanıtı |
| `codex/demo-safe-fixes` | `f63716d` | İki düzeltmenin birleşik kodu |

Çalışma dizinleri, `<repo>\.temp\worktrees\` altında sırasıyla `codex-ride-limit-fix`, `codex-fleet-evidence-fix`, `codex-demo-safe-fixes` dizinleridir. Düzeltme dalları aynı başlangıç commit'inden ayrıldı; yalnız demo dalında birleştirildi. WIP/main üzerinde kaynak değişikliği veya birleştirme yapılmadı. Mevcut checkout'ta önceden bulunan `INSTRUCTION_REVIEW_2026-09-07.md` değiştirilmedi. Git durumunda yalnız bu önceden mevcut izlenmeyen dosya kaldı.

## 1. Yolculuk sınırı

Doğrudan kampüs–öğrenci süresini bütün olası rotaların alt sınırı kabul eden API ön kontrolü kaldırıldı. Matris üçgen eşitsizliği garanti etmediğinden bu kontrol geçerli bir dolaylı rotayı engelleyebiliyordu. Kullanılmayan `requiredDirectRideMinutes` yardımcısı da kaldırıldı.

Çözücüye `max_ride_time` sınırı gönderilmeye devam eder. Hesaplanan gerçek rotanın süre/kapasite/matris doğrulaması ve `ride_time_violation` sertifikası denetimi korunur. `minimumFeasibleRideMinutes` uyumluluk için nullable sözleşmede kaldı; yeni üretici null döndürür. UI, eski doğrudan süreyi kesin minimum veya aşılamaz limit olarak göstermez. TR/EN mesajları bu sınırla uygun rota hesaplanamadığını söyler; bütün olası rotaların imkânsız olduğu iddiasında bulunmaz.

Regresyonlar: pickup ve dropoff için tam yönlü, üçgen eşitsizliği sağlamayan matrislerde doğrudan süre 100, gerçek dolaylı yolculuk 20, sınır 50 ve tur 30 dakika olduğunda çözücüye ulaşılır ve geçerli önizleme kabul edilir. API testinde taşıma/kimlik/veri kaynağı taklit edilir; gerçek önizleme doğrulayıcısı çalışır. Bu, canlı çözücüyle aynı verinin uçtan uca çalıştırıldığı anlamına gelmez.

## 2. Filo karşılaştırması

Sanal araç sayısı ile gerçek aktif araç sayısının aritmetik farkı, gerçek filonun kapasite veya bekleme süreleri için yeterlilik kanıtı olarak kullanılmaz. Sanal modda gerçek filo yeterliliği `unknown` kalır; fark açıkça sanal şablona göre sayısal karşılaştırmadır. Kanıtlanmamış araç minimumu üst sınır olarak etiketlenir. Sanal sonuçtan boşta araç veya kesin ek araç ihtiyacı çıkarılmaz.

Canlı moddaki olumlu sonuç, bütün hesaplanmış rotaları kapsayan atama kaydı gerektirir. Eksik/tekrarlı/bilinmeyen rota veya araç kimliği, uyuşmayan zaman/öğrenci kaydı, çakışan atama veya eksik özet kanıtı yeterlilik sonucuna dönüşmez. Fiziksel kapasite ve cooldown doğrulamasının sahibi mevcut üretici/atama mekanizmasıdır; görünüm modeline ikinci bir çözücü eklenmedi. Opsiyonel `activeVehicleIds` cevap alanı, sunulduğunda araç kimliği kontrolüne yardımcı olur; eski cevaplara zorunlu alan eklenmedi.

Olumlu metin “Mevcut filo bu rotalara atanabildi”; canlı shortage metni “Mevcut filo bu rotalara atanamıyor” kapsamındadır. Küresel yeniden rota oluşturma imkânsızlığı veya kesin ilave araç sayısı iddia edilmez. TR/EN ekran testleri bu ayrımı doğrular.

## Doğrulama

| Kontrol | Tam komut / kapsam | Sonuç |
| --- | --- | --- |
| Yolculuk dalı | `npx.cmd vitest run src/services/dudullu-preview.test.ts src/app/api/admin/dudullu-preview/route.test.ts src/services/daily-plan-view.test.ts "src/app/(app)/admin/daily-plan/page.test.tsx"` | 4 dosya / 246 test geçti |
| Filo dalı | `npx.cmd vitest run src/services/daily-plan-view.test.ts "src/app/(app)/admin/daily-plan/page.test.tsx" src/app/api/admin/dudullu-preview/route.test.ts` | 3 dosya / 224 test geçti |
| Birleşik demo | `npx.cmd vitest run` | 48 dosya / 552 test geçti; 120.72 saniye |
| Her düzeltme ve birleşik demo | `npm.cmd run typecheck -- --incremental false` | Başarılı, 0 TypeScript hatası |
| Birleşik demo | `npm.cmd run lint` | Başarılı, 0 hata / 167 uyarı |
| Birleşik kod | `git diff --check 6135319 HEAD` | Başarılı |
| Hizmetler | optimizer8001 `/health`, `/api/v1/internal/readiness`; web9003 `/admin/daily-plan` | HTTP200, handshake gövdesi doğrulandı |
| Yetki sınırı | web9003 oturumsuz `/api/admin/dudullu-readiness` | HTTP401 |
| Ortam | CORS web9003, ortak iç API anahtarı, Python import kaynak dizinleri | Başarılı; gizli değerler yazdırılmadı |

Her iki düzeltme için ayrı salt okunur spesifikasyon ve kod kalitesi incelemesi onay verdi. Son birleşik kaynak incelemesi de READY sonucu verdi; engelleyici bulgu yok. Yolculuk testlerinin ilk başarısız sonucu önceki ajan tarafından görüldü; oturum kesintisinden sonra sonucu varsaymak yerine green testler yeniden çalıştırıldı. Filo dalının ilk red sonucu 15 başarısız / 61 başarılı idi; son 224 test ve commit, ajan kota nedeniyle durduktan sonra ana ajan tarafından doğrulandı/tamamlandı.

Lint'in 167 uyarısı başlangıç sürümündeki sayıyla aynıdır. Vitest ayrıca mevcut testlerde beklenen hata/log çıktıları ve değiştirilmeyen araç planlama ekranında DOM nesting uyarısı üretti. Bu rapor repository genelindeki bütün teknik borcun çözüldüğünü iddia etmez.

## Demo ortamı ve kalan sınırlar

Çalıştırma komutları: `docs/DEMO_SAFE_FIXES_KULLANIM.md`. Web9003 ve optimizer8001, mevcut9002/8000 sürümüyle çakışmadan ayrı dizinden çalışır. Python bağımlılık ortamı ve node_modules mevcut kurulumu kullanır; Python kodu PYTHONPATH ile aday dizininden çözülür. Mevcut sürümün env dosyaları korunur; yalnız adayın ignored env kopyalarında ortak iç API anahtarı oluşturuldu. Anahtarlar commit edilmedi.

**Kod/port izolasyonu veritabanı izolasyonu değildir:** aday aynı Supabase yapılandırmasını kullanır. Canlı veri değişikliği, yayınlama veya deployment yapılmadı. Yönetici hesabıyla canlı önizleme, kullanıcı etkileşimli uçtan uca demo ve üretim build'i sınanmadı. Yerel geliştirme modu/hizmet bağlantısı ve otomatik regresyonlar doğrulandı. Python solver kodu değişmediği için bu görevde Python/akademik benchmark suite'i tekrar çalıştırılmadı; eski test sonuçları bu dalın yeni doğrulaması olarak sunulmaz.

## Tamamlanma kaydı

Kod commit'leri, birleşik otomatik kontroller, son bağımsız kaynak incelemesi ve dokümantasyon tamamlandı. Son incelemede engelleyici bulgu yok. Sıfır süreli rotalar görünümde ihtiyatlı biçimde filo yeterliliği `unknown` olarak kalır; bu davranış olumlu bir yeterlilik iddiası üretmez ve bu iki güvenlik düzeltmesi için engel olarak değerlendirilmedi.

Son hizmet kontrolünde sağlık/handshake, CORS ve sayfa200/anonim API401 kontrolleri başarılıydı. Yalnız bu görev için açılan web ve optimizer süreçleri kapatıldı; ardından 9003 ve 8001 portlarının boşaldığı doğrulandı. Demo otomatik olarak çalışır durumda bırakılmadı; kullanım belgesindeki iki terminal komutuyla yeniden başlatılır. Dallar ve çalışma dizinleri yerelde korundu; uzak sunucuya push veya ana dala birleştirme yapılmadı.
