from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# Font kayıtları
pdfmetrics.registerFont(TTFont('Microsoft YaHei', '/usr/share/fonts/truetype/chinese/msyh.ttf'))
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))

registerFontFamily('Microsoft YaHei', normal='Microsoft YaHei', bold='Microsoft YaHei')
registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')

# PDF oluştur
doc = SimpleDocTemplate(
    "/home/z/my-project/download/UniRide_Detayli_Analiz_Raporu.pdf",
    pagesize=A4,
    title="UniRide Detayli Analiz Raporu",
    author="Z.ai",
    creator="Z.ai",
    subject="UniRide CVRPTW Proje Kod Analizi"
)

styles = getSampleStyleSheet()

# Stiller
title_style = ParagraphStyle(
    name='TitleStyle',
    fontName='Microsoft YaHei',
    fontSize=28,
    leading=36,
    alignment=TA_CENTER,
    spaceAfter=24
)

subtitle_style = ParagraphStyle(
    name='SubtitleStyle',
    fontName='SimHei',
    fontSize=14,
    leading=20,
    alignment=TA_CENTER,
    spaceAfter=48
)

h1_style = ParagraphStyle(
    name='H1Style',
    fontName='Microsoft YaHei',
    fontSize=16,
    leading=22,
    alignment=TA_LEFT,
    spaceBefore=18,
    spaceAfter=12,
    textColor=colors.HexColor('#1F4E79')
)

h2_style = ParagraphStyle(
    name='H2Style',
    fontName='Microsoft YaHei',
    fontSize=13,
    leading=18,
    alignment=TA_LEFT,
    spaceBefore=12,
    spaceAfter=8,
    textColor=colors.HexColor('#2E75B6')
)

body_style = ParagraphStyle(
    name='BodyStyle',
    fontName='SimHei',
    fontSize=10.5,
    leading=18,
    alignment=TA_LEFT,
    spaceAfter=8,
    wordWrap='CJK'
)

caption_style = ParagraphStyle(
    name='CaptionStyle',
    fontName='SimHei',
    fontSize=9,
    leading=12,
    alignment=TA_CENTER,
    spaceAfter=12
)

# Header style for tables
header_style = ParagraphStyle(
    name='TableHeader',
    fontName='Microsoft YaHei',
    fontSize=10,
    textColor=colors.white,
    alignment=TA_CENTER
)

cell_style = ParagraphStyle(
    name='TableCell',
    fontName='SimHei',
    fontSize=9,
    leading=12,
    alignment=TA_CENTER,
    wordWrap='CJK'
)

cell_left_style = ParagraphStyle(
    name='TableCellLeft',
    fontName='SimHei',
    fontSize=9,
    leading=12,
    alignment=TA_LEFT,
    wordWrap='CJK'
)

story = []

# Kapak Sayfası
story.append(Spacer(1, 120))
story.append(Paragraph("UniRide CVRPTW", title_style))
story.append(Paragraph("Detayli Kod Analizi ve Yol Haritasi Raporu", subtitle_style))
story.append(Spacer(1, 36))
story.append(Paragraph("Tarih: 03 Nisan 2026", ParagraphStyle(
    name='DateStyle',
    fontName='SimHei',
    fontSize=12,
    leading=16,
    alignment=TA_CENTER
)))
story.append(Paragraph("Analiz Araci: Z.ai", ParagraphStyle(
    name='AuthorStyle',
    fontName='SimHei',
    fontSize=11,
    leading=15,
    alignment=TA_CENTER
)))
story.append(PageBreak())

# 1. Proje Ozeti
story.append(Paragraph("1. Proje Ozeti", h1_style))

story.append(Paragraph(
    "UniRide, ozel ogrenci tasima sistemi icin gelistirilmis kapsamli bir CVRPTW (Kapasiteli Arac Rotalama Problemi Zaman Pencereli) cozum platformudur. Proje, iki ana hedefe hizmet etmektedir: (1) Ticari canli urun olarak stabil hibrit algoritmalar ile guvenilir rota planlamasi saglamak, (2) Akademik arastirma ve makale calismalari icin SOTA (State-of-the-Art) algoritmalarini test edebilecek bir altyapi sunmak. Bu cift-yollu (Dual-Track) mimari, projenin hem ticari hem de akademik deger kazanmasini saglamaktadir.",
    body_style
))

story.append(Paragraph(
    "Proje, Next.js 16 tabanli frontend ve Python FastAPI tabanli backend olmak uzere iki ana bileşenden olusmaktadir. Frontend TypeScript, Tailwind CSS ve shadcn/ui kutuphanesi ile modern bir kullanici arayuzu sunarken, backend Python ile cesitli meta-sezgisel algoritmalar (GA, PSO, GWO, HHO) ve holistik cozuculer (OR-Tools, PyVRP, VROOM) kullanarak rota optimizasyonu gerceklestirmektedir. Supabase/PostgreSQL veritabani ile veri kalıcılığı saglanmaktadir.",
    body_style
))

# 2. Mimari Yapı
story.append(Paragraph("2. Mimari Yapı", h1_style))

story.append(Paragraph("2.1 Genel Sistem Mimarisi", h2_style))

story.append(Paragraph(
    "Sistem uc ana katmandan olusmaktadir: Presentation Layer (Frontend), Business Logic Layer (Backend API) ve Data Layer (Database). Frontend Next.js App Router ile SSR destegi sunmakta ve kullanici etkilesimlerini yonetmektedir. Backend Python FastAPI ile optimizasyon algoritmalarini calistirmakta ve sonuclari API uzerinden iletmektedir. Veritabani katmaninda Supabase PostgreSQL ile kullanici, arac, rota ve ride request verileri saklanmaktadir.",
    body_style
))

# Mimari tablosu
arch_data = [
    [Paragraph('<b>Katman</b>', header_style), Paragraph('<b>Teknoloji</b>', header_style), Paragraph('<b>Sorumluluk</b>', header_style)],
    [Paragraph('Frontend', cell_style), Paragraph('Next.js 16 + TypeScript', cell_style), Paragraph('Kullanici arayuzu, SSR, API proxy', cell_left_style)],
    [Paragraph('Backend API', cell_style), Paragraph('Python FastAPI', cell_style), Paragraph('Optimizasyon algoritmalari, CVRPTW', cell_left_style)],
    [Paragraph('Database', cell_style), Paragraph('Supabase PostgreSQL', cell_style), Paragraph('Veri kaliciligi, RLS politikalari', cell_left_style)],
    [Paragraph('Cache', cell_style), Paragraph('JSON Metadata', cell_style), Paragraph('Benchmark sonuclari, hash takibi', cell_left_style)],
]

arch_table = Table(arch_data, colWidths=[3*cm, 4.5*cm, 7*cm])
arch_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
]))
story.append(Spacer(1, 12))
story.append(arch_table)
story.append(Spacer(1, 6))
story.append(Paragraph("Tablo 1: Sistem Katmanlari ve Teknolojileri", caption_style))
story.append(Spacer(1, 18))

story.append(Paragraph("2.2 Algoritma Mimarisi (Cift Pipeline)", h2_style))

story.append(Paragraph(
    "Proje, VRP cozumu icin iki farkli pipeline yaklasimi sunmaktadir. Pipeline A (Cluster-First, Route-Second): Oncesi coğrafik kumeleme (Sweep/CW algoritmalari), sonrasi her kume icin TSP cozumu. Bu yaklasim, kucuk ve orta olcekli problemler icin uygundur. Pipeline B (Route-First, Cluster-Second): Tum ogrenciler icin dev tur (giant tour) olusturma, sonrasi optimal bolme (Split Decoder) ile arac rotalarina ayirma. Bu yaklasim, buyuk olcekli problemlerde daha verimlidir.",
    body_style
))

# Pipeline tablosu
pipeline_data = [
    [Paragraph('<b>Pipeline</b>', header_style), Paragraph('<b>Algoritmalar</b>', header_style), Paragraph('<b>Karmaşiklik</b>', header_style), Paragraph('<b>Kullanim</b>', header_style)],
    [Paragraph('Pipeline A', cell_style), Paragraph('GA, PSO, GWO, HHO', cell_style), Paragraph('O(g*p*n2) + Sweep', cell_style), Paragraph('Orta olcek', cell_style)],
    [Paragraph('Pipeline B', cell_style), Paragraph('GA-Split, PSO-Split, GWO-Split, HHO-Split', cell_style), Paragraph('O(g*p*n2) + O(n2) Split', cell_style), Paragraph('Tum olcekler', cell_style)],
    [Paragraph('Holistik', cell_style), Paragraph('OR-Tools, PyVRP, VROOM', cell_style), Paragraph('O(n3) / O(n2 log n)', cell_style), Paragraph('Buyuk olcek', cell_style)],
]

pipeline_table = Table(pipeline_data, colWidths=[2.5*cm, 5*cm, 4*cm, 3*cm])
pipeline_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
]))
story.append(Spacer(1, 12))
story.append(pipeline_table)
story.append(Spacer(1, 6))
story.append(Paragraph("Tablo 2: Pipeline Karsilastirmasi", caption_style))
story.append(Spacer(1, 18))

# 3. Kod Analizi
story.append(Paragraph("3. Kod Analizi", h1_style))

story.append(Paragraph("3.1 Backend Kod Kalitesi", h2_style))

story.append(Paragraph(
    "Backend Python kodlari yuksek kaliteli ve moduler bir mimariye sahiptir. Strategy Pattern ile algoritmalar birbirinden bagimsiz olarak gelistirilebilmekte ve STRATEGY_REGISTRY mekanizmasi ile dinamik olarak yuklenebilmektedir. BaseRoutingStrategy soyut sinifi tum algoritmalar icin ortak bir arayuz tanimlamakta ve kod tekrarini onlemektedir. LinearSplitDecoder sinifi O(N*B) zaman karmasikligi ile dev turleri optimal sekilde bolmekte ve Time-Warp ceza mekanizmasi ile esnek cozumler uretebilmektedir.",
    body_style
))

story.append(Paragraph(
    "LocalSearch modulu (local_search.py) 2-opt, 3-opt, Or-opt, Swap, Cross Exchange ve Hybrid olmak uzere 6 farkli yerel arama algoritmasi sunmaktadir. Bu modul, tum meta-sezgisel algoritmalar tarafindan ortak olarak kullanilmakta ve kod tekrarini onlemektedir. Her bir algoritma icin akademik kaynak referanslari (Croes 1958, Lin 1965, Or 1976, Taillard 1993) dokumante edilmistir.",
    body_style
))

story.append(Paragraph("3.2 Frontend Kod Kalitesi", h2_style))

story.append(Paragraph(
    "Frontend TypeScript kodlari modern React pratikleri ile yazilmistir. algorithm-constants.ts dosyasi tek dogruluk kaynagi (Single Source of Truth) olarak tum algoritma isimlerini, gorunen adlarini ve aciklamalarini icermektedir. optimizer-service.ts dosyasi Python API ile iletisimi saglamakta ve tip guvenli bir arayuz sunmaktadir. Supabase entegrasyonu ile kimlik dogrulama ve veritabani islemleri merkezi olarak yonetilmektedir.",
    body_style
))

story.append(Paragraph("3.3 Akademik Benchmark Altyapisi", h2_style))

story.append(Paragraph(
    "Proje, akademik makale hedefi dogrultusunda gelistirilmis bir Smart Benchmark sistemi icermektedir. academic_benchmark klasoru altinda yer alan bu sistem, TSPLIB problemlerini dinamik olarak yuklemekte, algoritma kodlarinin SHA256 hash degerlerini takip etmekte ve degisen kodlar icin otomatik yeniden test baslatmaktadir. run_smart_benchmark.py dosyasi interaktif bir terminal dashboard sunarak kullaniciya test secenekleri sunmaktadir.",
    body_style
))

# 4. Tamamlanan Bilesenler
story.append(Paragraph("4. Tamamlanan Bilesenler", h1_style))

story.append(Paragraph(
    "Asagidaki tablo, projede tamamlanmis olan ana bilesenleri ve bunlarin durumlarini ozetlemektedir. Faz 1 kritik duzeltmeler, Faz 1.5 Split algoritmalar, Faz 1.5X Heterojen Filo ve IE Engine, P1-P3 veritabani kalıcılığı ve time window destegi tamamlanmistir. Akademik benchmark altyapisi de son durumda calisir durumdadır.",
    body_style
))

# Tamamlanan tablosu
completed_data = [
    [Paragraph('<b>Faz</b>', header_style), Paragraph('<b>Bilesen</b>', header_style), Paragraph('<b>Durum</b>', header_style)],
    [Paragraph('Faz 1', cell_style), Paragraph('Kritik Duzeltmeler (API proxy, encoding, auth)', cell_left_style), Paragraph('TAMAMLANDI', cell_style)],
    [Paragraph('Faz 1.5', cell_style), Paragraph('Split Decoder + Pipeline B Algoritmalar', cell_left_style), Paragraph('TAMAMLANDI', cell_style)],
    [Paragraph('Faz 1.5X', cell_style), Paragraph('Heterojen Filo + IE Resource Engine', cell_left_style), Paragraph('TAMAMLANDI', cell_style)],
    [Paragraph('P1', cell_style), Paragraph('Veritabani Kaliciligi (route_plans tablosu)', cell_left_style), Paragraph('TAMAMLANDI', cell_style)],
    [Paragraph('P2', cell_style), Paragraph('Sandbox Backend API', cell_left_style), Paragraph('TAMAMLANDI', cell_style)],
    [Paragraph('P3', cell_style), Paragraph('Time Window Destegi (CVRPTW)', cell_left_style), Paragraph('TAMAMLANDI', cell_style)],
    [Paragraph('SOTA', cell_style), Paragraph('Akademik Benchmark Altyapisi', cell_left_style), Paragraph('TAMAMLANDI', cell_style)],
    [Paragraph('Faz 2', cell_style), Paragraph('Surucu Atama Sistemi', cell_left_style), Paragraph('BEKLIYOR', cell_style)],
    [Paragraph('Faz 4', cell_style), Paragraph('Bildirim Sistemi', cell_left_style), Paragraph('PLANLANDI', cell_style)],
]

completed_table = Table(completed_data, colWidths=[2.5*cm, 8*cm, 4*cm])
completed_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('BACKGROUND', (0, 1), (-1, 7), colors.HexColor('#E8F5E9')),
    ('BACKGROUND', (0, 8), (-1, -1), colors.HexColor('#FFF3E0')),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
]))
story.append(Spacer(1, 12))
story.append(completed_table)
story.append(Spacer(1, 6))
story.append(Paragraph("Tablo 3: Proje Durumu Ozeti", caption_style))
story.append(Spacer(1, 18))

# 5. SOTA Framework Vizyonu
story.append(Paragraph("5. SOTA Framework Vizyonu", h1_style))

story.append(Paragraph(
    "Projenin SOTA (State-of-the-Art) framework vizyonu, mevcut optimizasyon motorunu 2024-2026 VRP akademik makalelerinde kanitlanmis yaklasimlarla donusturmeyi hedeflemektedir. Bu vizyon 4 ana mimari karari icermektedir: (1) Lineer Zamanli Split Algoritmasi - O(N2)'den O(N)'e gecis, (2) Infeasibility Relaxation - Time-Warp ve kapasite cezalari ile esnek cozumler, (3) ALNS Destekli Suri Hibridizasyonu - Destroy/Repair operatorleri, (4) Multi-Objective Optimizasyon - Pareto Front coklu cozumler.",
    body_style
))

story.append(Paragraph("5.1 Faz 1: Core Engine (TAMAMLANDI)", h2_style))

story.append(Paragraph(
    "LinearSplitDecoder ile O(N*B) zamanli bolme algoritmasi implemente edildi. Time-Warp cezalari ve Soft Capacity mekanizmasi ile esnek cozum uretimi saglandi. Test sonuclarina gore 150 ogrencilik testte calisma hizi 1.57 ms'den 0.80 ms'ye dusuruldu (%50 iyilestirme). Motor artik Time-Warp cezalarini tam desteklemektedir.",
    body_style
))

story.append(Paragraph("5.2 Faz 2: ALNS Operatörleri (BEKLIYOR)", h2_style))

story.append(Paragraph(
    "Bir sonraki adim, ALNS (Adaptive Large Neighborhood Search) operatorlerinin tasarlanmasidir. Bu operatorler: Random Removal (cesitlilik), Worst Removal (ceza odakli), Shaw Related Removal (yakin duraklar), Greedy Insertion ve Regret-2 Insertion (SOTA) seklindedir. Bu operatorler, suru algoritmalarinin kullanacagi akıllı rota degistirme ve tamir mekanizmalarini olusturacaktir.",
    body_style
))

story.append(Paragraph("5.3 Faz 3: Hibritizasyon (BEKLIYOR)", h2_style))

story.append(Paragraph(
    "ALNS operatorlerinin HHO, PSO gibi meta-sezgisel algoritmalarla birlestirilmesi planlanmaktadir. Algoritma artik vektor degistirmek yerine ALNS operator olasiliklarini (Roulette Wheel) guncelleyecektir. Basarili operatorler odullendirilecek (Adaptive mekanizma). Bu yaklasim, MO-HHO-ALNS stratejisi olarak literature katki saglayabilir.",
    body_style
))

# 6. Teknik Borclar
story.append(Paragraph("6. Teknik Borclar ve Eksiklikler", h1_style))

story.append(Paragraph(
    "Proje analizi sirasinda tespit edilen teknik borclar ve eksiklikler asagida listelenmistir. Bu unsurlar, projenin ilerleyen donemlerinde ele alinmasi gereken oncelikli gorevleri olusturmaktadir.",
    body_style
))

# Teknik borç tablosu
debt_data = [
    [Paragraph('<b>Oncelik</b>', header_style), Paragraph('<b>Konu</b>', header_style), Paragraph('<b>Aciklama</b>', header_style)],
    [Paragraph('Orta', cell_style), Paragraph('Test Coverage Dusuk', cell_left_style), Paragraph('Sadece resource_profiler test edildi (20 test). Diger moduller icin test yazilmali.', cell_left_style)],
    [Paragraph('Orta', cell_style), Paragraph('Local Search Kisitli', cell_left_style), Paragraph('Sadece 2-opt varsayilan. 3-opt ve Or-opt daha yaygin kullanilmali.', cell_left_style)],
    [Paragraph('Orta', cell_style), Paragraph('time_matrix Caching Yok', cell_left_style), Paragraph('Her istekte DBden yukleniyor. Redis veya bellek ici cache uygulanmali.', cell_left_style)],
    [Paragraph('Dusuk', cell_style), Paragraph('Heterojen Filo Kisim', cell_left_style), Paragraph('VehicleConfig semada var ama stratejilerde pasif. Entegrasyon gerekli.', cell_left_style)],
    [Paragraph('Dusuk', cell_style), Paragraph('Hybrid Base Strategy Yok', cell_left_style), Paragraph('Teknik borc (RI1). Ortak hibrit strateji tabani olusturulmali.', cell_left_style)],
]

debt_table = Table(debt_data, colWidths=[2.5*cm, 4*cm, 8*cm])
debt_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
]))
story.append(Spacer(1, 12))
story.append(debt_table)
story.append(Spacer(1, 6))
story.append(Paragraph("Tablo 4: Teknik Borclar ve Eksiklikler", caption_style))
story.append(Spacer(1, 18))

# 7. Yol Haritasi
story.append(Paragraph("7. Yol Haritasi ve Oneriler", h1_style))

story.append(Paragraph("7.1 Kisa Vadeli Hedefler (1-2 Hafta)", h2_style))

story.append(Paragraph(
    "ALNS operatorlerinin tasarlanmasi ve implementasyonu oncelikli gorev olarak belirlenmistir. optimizer_api/strategies/alns_operators.py dosyasi olusturularak Random Removal, Worst Removal, Shaw Related Removal, Greedy Insertion ve Regret-2 Insertion operatorleri yazilmalidir. Bu operatorler, Strategy Pattern ile moduler bir yapida olmali ve dev tur (giant tour) uzerinde calismalidir.",
    body_style
))

story.append(Paragraph("7.2 Orta Vadeli Hedefler (3-4 Hafta)", h2_style))

story.append(Paragraph(
    "MO-HHO-ALNS hibrit stratejisinin implementasyonu ve mevcut benchmark sistemi ile test edilmesi gerekmektedir. Strateji, HHO algoritmasinin suru zekasini ALNS operator secimi icin kullanmali ve LinearSplitDecoder ile sonuc uretmelidir. Test sonuclari TSPLIB problemleri uzerinde dogrulanmali ve akademik makale hazirliklari baslatilmalidir.",
    body_style
))

story.append(Paragraph("7.3 Uzun Vadeli Hedefler (2-3 Ay)", h2_style))

story.append(Paragraph(
    "Multi-Objective (Pareto Front) optimizasyon destegi eklenerek Admin kullanicilarina coklu senaryo secenegi sunulmalidir. Bildirim sistemi (Faz 4) implementasyonu tamamlanmali ve production deployment icin CI/CD pipeline kurulmalidir. Akademik makale yazimi ve uluslararasi konferans gonderimi hedeflenmelidir.",
    body_style
))

# 8. Sonuc
story.append(Paragraph("8. Sonuc", h1_style))

story.append(Paragraph(
    "UniRide projesi, hem ticari bir urun hem de akademik bir arastirma platformu olarak basariyla gelistirilmektedir. Mevcut durumda temel optimizasyon algoritmalari (GA, PSO, GWO, HHO) ve Pipeline B (Split) mimarisi calisir durumdadır. LinearSplitDecoder ile O(N*B) zamanli bolme, Time-Warp cezalari ile esnek cozum uretimi ve Smart Benchmark sistemi ile akademik test altyapisi tamamlanmistir.",
    body_style
))

story.append(Paragraph(
    "Bir sonraki oncelikli gorev, SOTA Framework Faz 2 kapsaminda ALNS operatorlerinin tasarlanmasidir. Bu operatorler, projenin akademik makale hedefine dogru kritik bir adim olusturmaktadir. Teknik borclarin (test coverage, time_matrix caching) kademeli olarak giderilmesi ve surucu atama sisteminin tamamlanmasi, projenin ticari degerini artiracaktir.",
    body_style
))

# Build PDF
doc.build(story)
print("PDF olusturuldu: /home/z/my-project/download/UniRide_Detayli_Analiz_Raporu.pdf")
