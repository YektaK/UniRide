# UniRide Heterojen Filo & IE Optimizasyonu: Tam Konuşma Geçmişi

> **Tarih:** 27 Mart 2026  
> **Katılımcılar:** Admin (Kullanıcı), Antigravity (AI Asistanı)

Bu doküman, "Heterojen Filo" ve "Endüstri Mühendisliği Kaynak Planlaması" özelliklerinin tasarım ve planlama aşamasındaki tüm diyaloğu ve alınan kararları içerir.

---

## BÖLÜM 1: Başlangıç ve Analiz (Özetlenmiş Geçmiş)

*Eski konuşmaların sistem tarafından korunan özetidir.*

### 1.1. Hedef Belirleme
Kullanıcı, UniRide projesinde araç kapasitelerinin (Sw - Tekerlekli Sandalye, So - Diğer Engel) her araç için farklı olabildiği "Heterojen Filo" desteğini ve buna bağlı karar destek sistemini talep etti. 

### 1.2. Teknik Analiz
Backend mimarisi (Python FastAPI + PyVRP/VROOM) incelendi. `OptimizationRequest` şemasının ve `SplitDecoder` algoritmasının bu esnekliğe uygun hale getirilmesi gerektiği saptandı. Supabase tarafındaki `vehicles` tablosunun dinamik olarak okunması kararlaştırıldı.

---

## BÖLÜM 2: Tasarım ve İyileştirme (Canlı Diyalog ve Kararlar)

*Bu bölüm, tasarımın "IE Kaynak Planlaması" modeline evrildiği aşamayı içerir.*

### 2.1. Tasarım Seçimi (Visual Brainstorming)
**Kullanıcı:** "Bir gelişme olmadı, Supabase 'vehicles' tablosunu kullanmalıyız."
**Antigravity:** (Visual Companion üzerinden 2-3 yaklaşım sundu: Holistic Daily Planning vs. Ad-hoc Request Windows).
**Kullanıcı:** "Bütünsel yaklaşarak en uygun araç planlamasını sistem yapmalı. Saat 11 için büyük aracı çıkartırsak sonraki saate araç kalmayabilir, sistem bunu öngörmeli."

### 2.2. IE (Endüstri Mühendisliği) Perspektifinin Dahil Edilmesi
**Kullanıcı:** "Sadece çözümsüzlüğe değil, verimsiz çözümlere de bakmak istiyorum. Bir endüstri mühendisi olarak yaklaşıp sistemi planlamak istiyorum. Standart araç cinsinden kaç araç gerektiğini görmeliyim. Araçlar hem giden hem gelen öğrenciler için planlanmalı, ama çakışmalar (Inbound/Outbound) unutulmamalı."

**Kararlar:**
-   **Benchmark**: Önce "İdeal" (Standart Minibüs) ihtiyacı hesaplanacak.
-   **Resource Blocking**: Geliş rotası çizen araç, o esnada gidiş için "Bloke" sayılacak.
-   **Slack Time**: Öğrenci saati esnetilerek araç tasarrufu teşvik edilecek.

### 2.3. Dashboard ve Görselleştirme Talepleri
**Kullanıcı:** "Standart araç ihtiyacını detaylı bir tablo olarak görmek istiyorum. X ekseni saat olacak şekilde gidiş/geliş talepleri stack edilmeli. Araç blokları histogram ile hizalı olsun."

**Antigravity:** (IE Dashboard v3 Mockup oluşturuldu: Alınan X-axis, Sw/So hassasiyet kırımları, darboğaz göstergeleri).
**Kullanıcı:** "Şu an için uygun görünüyor. Algoritmaların da buna uygun çalışması gerektiğini unutmayalım."

---

## BÖLÜM 3: Uygulama Planı ve Final Onayı

### 3.1. Uygulama Planı Hazırlığı
**Antigravity:** `implementation_plan.md` oluşturuldu.
-   **Backend**: `resource_profiler.py` (IE logic), `SplitDecoderV2` (Heterogeneous), VROOM/PyVRP güncellemeleri.
-   **Frontend**: `ResourceHistogram.tsx`, Sandbox Dashboard.

### 3.2. Spec Review (Teknik İnceleme)
Tasarım dokümanı (`2026-03-27-heterogeneous-fleet-design.md`) bir alt-agent tarafından incelendi.
-   **Öneri**: Araçlar arası 15 dakikalık "Cooldown" süresi eklendi.
-   **Öneri**: Araç tipi değişiminde "Re-optimization" tetikleyici (trigger) eklendi.

### 3.3. Belgeleme
Kullanıcı, tüm bu mantık silsilesini ve diyalog geçmişini bir doküman olarak kayıt edilmesini talep etti. (Bu dosya).

---

## SONUÇ VE SON DURUM
Tasarım onaylandı, uygulama planı hazırlandı. Bir sonraki aşama kod yazımı ve entegrasyon sürecidir.
