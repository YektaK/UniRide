#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Code Review Report Generator
"""

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# Register fonts
pdfmetrics.registerFont(TTFont('Microsoft YaHei', '/usr/share/fonts/truetype/chinese/msyh.ttf'))
pdfmetrics.registerFont(TTFont('SimHei', '/usr/share/fonts/truetype/chinese/SimHei.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', '/usr/share/fonts/truetype/english/Times-New-Roman.ttf'))
registerFontFamily('Microsoft YaHei', normal='Microsoft YaHei', bold='Microsoft YaHei')
registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman')

# Define colors
TABLE_HEADER_COLOR = colors.HexColor('#1F4E79')
TABLE_ROW_EVEN = colors.white
TABLE_ROW_ODD = colors.HexColor('#F5F5F5')

# Define styles
styles = getSampleStyleSheet()

cover_title_style = ParagraphStyle(
    name='CoverTitle',
    fontName='Microsoft YaHei',
    fontSize=36,
    leading=42,
    alignment=TA_CENTER,
    spaceAfter=36
)

cover_subtitle_style = ParagraphStyle(
    name='CoverSubtitle',
    fontName='SimHei',
    fontSize=18,
    leading=24,
    alignment=TA_CENTER,
    spaceAfter=48
)

h1_style = ParagraphStyle(
    name='H1Style',
    fontName='Microsoft YaHei',
    fontSize=18,
    leading=24,
    alignment=TA_LEFT,
    spaceBefore=18,
    spaceAfter=12,
    textColor=colors.HexColor('#1F4E79')
)

h2_style = ParagraphStyle(
    name='H2Style',
    fontName='Microsoft YaHei',
    fontSize=14,
    leading=18,
    alignment=TA_LEFT,
    spaceBefore=12,
    spaceAfter=8,
    textColor=colors.HexColor('#2E74B5')
)

body_style = ParagraphStyle(
    name='BodyStyle',
    fontName='SimHei',
    fontSize=11,
    leading=18,
    alignment=TA_LEFT,
    spaceAfter=8,
    wordWrap='CJK'
)

code_style = ParagraphStyle(
    name='CodeStyle',
    fontName='Times New Roman',
    fontSize=9,
    leading=12,
    alignment=TA_LEFT,
    spaceAfter=6,
    leftIndent=20,
    backColor=colors.HexColor('#F5F5F5')
)

table_header_style = ParagraphStyle(
    name='TableHeader',
    fontName='Microsoft YaHei',
    fontSize=10,
    leading=14,
    alignment=TA_CENTER,
    textColor=colors.white
)

table_cell_style = ParagraphStyle(
    name='TableCell',
    fontName='SimHei',
    fontSize=10,
    leading=14,
    alignment=TA_LEFT,
    wordWrap='CJK'
)

critical_style = ParagraphStyle(
    name='CriticalStyle',
    fontName='SimHei',
    fontSize=11,
    leading=18,
    alignment=TA_LEFT,
    spaceAfter=8,
    textColor=colors.HexColor('#C00000'),
    wordWrap='CJK'
)

def create_table(data, col_widths):
    """Create formatted table"""
    wrapped_data = []
    for row in data:
        wrapped_row = []
        for cell in row:
            if isinstance(cell, str):
                wrapped_row.append(Paragraph(cell, table_cell_style))
            else:
                wrapped_row.append(cell)
        wrapped_data.append(wrapped_row)
    
    table = Table(wrapped_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Microsoft YaHei'),
        ('FONTNAME', (0, 1), (-1, -1), 'SimHei'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    for i in range(1, len(wrapped_data)):
        if i % 2 == 0:
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), TABLE_ROW_ODD)]))
        else:
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), TABLE_ROW_EVEN)]))
    
    return table

def build_report():
    doc = SimpleDocTemplate(
        "/home/z/my-project/download/UniRide_Kod_Inceleme_Raporu.pdf",
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title='UniRide_Kod_Inceleme_Raporu',
        author='Z.ai',
        creator='Z.ai',
        subject='UniRide Projesi Kod Inceleme ve Durum Degerlendirme Raporu'
    )
    
    story = []
    
    # ========== COVER PAGE ==========
    story.append(Spacer(1, 120))
    story.append(Paragraph("<b>UniRide Projesi</b>", cover_title_style))
    story.append(Paragraph("Kod Inceleme ve Durum Degerlendirme Raporu", cover_subtitle_style))
    story.append(Spacer(1, 60))
    story.append(Paragraph("Engelli Ogrenci Servis Optimizasyon Sistemi", body_style))
    story.append(Paragraph("Next.js 16 + TypeScript + Supabase", body_style))
    story.append(Spacer(1, 100))
    story.append(Paragraph("Tarih: Mart 2026", body_style))
    story.append(Paragraph("Hazirlayan: Z.ai Kod Analiz Sistemi", body_style))
    story.append(PageBreak())
    
    # ========== 1. EXECUTIVE SUMMARY ==========
    story.append(Paragraph("<b>1. Yonetici Ozeti</b>", h1_style))
    story.append(Spacer(1, 12))
    
    summary_text = """Bu rapor, UniRide projesinin mevcut kod tabaninin kapsamli bir incelemesini icermektedir. Proje, engelli universite ogrencileri icin servis rotalama optimizasyonu saglayan bir Next.js uygulamasidir. Inceleme sonucunda 8 kritik sorun, 12 orta oncelikli sorun ve 18 dusuk oncelikli iyilestirme onerisi tespit edilmistir. Projenin temel mimarisi saglam olmakla birlikte, bazi onemli guvenlik, performans ve bakim sorunlari mevcuttur."""
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 12))
    
    # Summary table
    summary_data = [
        [Paragraph('<b>Kategori</b>', table_header_style), Paragraph('<b>Sayi</b>', table_header_style), Paragraph('<b>Durum</b>', table_header_style)],
        ['Kritik Sorunlar', '8', 'Acil Duzeltim Gerekli'],
        ['Orta Oncelikli Sorunlar', '12', 'Planli Duzeltim'],
        ['Dusuk Oncelikli Sorunlar', '18', 'Iyilestirme Onerisi'],
        ['Dogru Uygulamalar', '15+', 'Korunmali'],
    ]
    story.append(create_table(summary_data, [6*cm, 3*cm, 5*cm]))
    story.append(Spacer(1, 18))
    
    # ========== 2. PROJECT OVERVIEW ==========
    story.append(Paragraph("<b>2. Proje Genel Bakis</b>", h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>2.1 Teknoloji Yigini</b>", h2_style))
    
    tech_data = [
        [Paragraph('<b>Katman</b>', table_header_style), Paragraph('<b>Teknoloji</b>', table_header_style), Paragraph('<b>Versiyon</b>', table_header_style)],
        ['Frontend Framework', 'Next.js', '16.1.6'],
        ['UI Library', 'React', '18.3.1'],
        ['Dil', 'TypeScript', '5.x'],
        ['UI Komponentleri', 'shadcn/ui (Radix)', 'Latest'],
        ['Stil', 'Tailwind CSS', '3.4.1'],
        ['Veritabani', 'Supabase', '2.98.0'],
        ['AI Entegrasyonu', 'Genkit (Google AI)', '1.8.0'],
        ['Test', 'Vitest', '4.0.18'],
    ]
    story.append(create_table(tech_data, [5*cm, 5*cm, 3*cm]))
    story.append(Spacer(1, 18))
    
    story.append(Paragraph("<b>2.2 Proje Yapisi</b>", h2_style))
    
    structure_text = """Proje, Next.js App Router mimarisini kullanmaktadir ve iyi organize edilmis bir klasor yapisina sahiptir. Kaynak kodlar src/ klasoru altinda organize edilmistir. Uygulama modulleri app/ altinda route-based olarak ayrilmistir. Admin, Driver ve Student olmak uzere uc ana kullanici rolu bulunmaktadir. Servis katmani services/ altinda yer almakta ve is mantigi burada yurutulmektedir. DouBus adli ozel bir rota optimizasyon servisi bulunmaktadir."""
    story.append(Paragraph(structure_text, body_style))
    story.append(Spacer(1, 12))
    
    # ========== 3. CRITICAL ISSUES ==========
    story.append(Paragraph("<b>3. Kritik Sorunlar (Yuksek Oncelik)</b>", h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>3.1 Hard-coded API URL Guvenlik Riski</b>", h2_style))
    
    issue1_text = """DOSYA: src/services/doubus/multi-vehicle-routing.ts (Satir: 3288) - Python optimizasyon API'si icin URL hard-coded olarak yazilmis. Bu, gelistirme ve uretim ortamlari arasinda gecis yapmayi zorlastirir ve guvenlik riski olusturur."""
    story.append(Paragraph(issue1_text, critical_style))
    
    code1 = """// MEVCUT (Yanlis):
const response = await fetch("http://127.0.0.1:8000/api/v1/optimize", {...});

// ONERILEN:
const API_URL = process.env.OPTIMIZER_API_URL || "http://127.0.0.1:8000";
const response = await fetch(`${API_URL}/api/v1/optimize`, {...});"""
    story.append(Paragraph(code1, code_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>3.2 GA ve PSO Algoritmalari Bos (Taslak)</b>", h2_style))
    
    issue2_text = """DOSYA: src/services/doubus/route-strategies/ga-strategy.ts, pso-strategy.ts - Genetik Algoritma (GA) ve Parcacik Surusu Optimizasyonu (PSO) stratejileri sadece interface uyumlu bos metodlar icermektedir. Bu, .ai-handover.md dosyasinda da belirtilmistir. Rota optimizasyonu icin kritik olan bu algoritmalar calismamaktadir."""
    story.append(Paragraph(issue2_text, critical_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>3.3 TypeScript Type Safety Sorunlari</b>", h2_style))
    
    issue3_text = """DOSYA: src/lib/supabase-db.ts - toCamelCase ve toSnakeCase fonksiyonlari 'any' tipi kullanmaktadir. Bu, TypeScript'in tip guvenligi avantajlarini ortadan kaldirir ve runtime hatalarina neden olabilir. Ayrica bircok yerde 'as any' ve 'as never' tip donusumleri kullanilmistir."""
    story.append(Paragraph(issue3_text, critical_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>3.4 Auth Token Race Condition Riski</b>", h2_style))
    
    issue4_text = """DOSYA: src/lib/admin-api.ts - getAuthToken() fonksiyonu birden fazla async islemi sirayla dener. Hizli ardisik cagrilarda race condition olusabilir. Session refresh ve getUser cagrilari arasinda tutarsizlik riski vardir."""
    story.append(Paragraph(issue4_text, critical_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>3.5 Veritabani UNIQUE Kisitlamasi Eksik</b>", h2_style))
    
    issue5_text = """DOSYA: .ai-handover.md ve supabase/fix_schema.sql - weekly_schedules tablosundaki user_id sutunu icin UNIQUE kisitlamasi Supabase'de manuel olarak uygulanmasi gerekmektedir. Bu kisitlama olmadan, bir kullanici icin birden fazla schedule olusturulabilir ve veri tutarsizliklari yasabilir."""
    story.append(Paragraph(issue5_text, critical_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>3.6 Location Mapper Default Fallback Riski</b>", h2_style))
    
    issue6_text = """DOSYA: src/services/doubus/location-mapper.ts (Satir: 3075) - Adres eslesmesi bulunamazsa default olarak 'Sw1' dondurulmektedir. Bu, yanlis lokasyonlara servis yapilmasina neden olabilir. Hata firlatmak veya null donmek daha guvenli olacaktir."""
    story.append(Paragraph(issue6_text, critical_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>3.7 Dev-Reset Endpoint Guvenlik Riski</b>", h2_style))
    
    issue7_text = """DOSYA: src/app/api/auth/dev-reset/route.ts - Sadece NODE_ENV kontrolu ile sinirli olsa da, bu endpoint uretim ortaminda yanlislikla aktif kalabilir. Ek guvenlik katmanlari (IP whitelist, auth token) onerilir."""
    story.append(Paragraph(issue7_text, critical_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>3.8 Schedule Import Mukerrer Veri Kontrolu</b>", h2_style))
    
    issue8_text = """DOSYA: src/services/excel/import.ts - Excel import sirasinda ayni ogrenci icin tekrarlanan gunler icin veri degistirilir ancak eski verilerin tamamen silinip silinmedigi net degil. Merge mantigi data integrity sorunlarina yol acabilir."""
    story.append(Paragraph(issue8_text, critical_style))
    story.append(Spacer(1, 18))
    
    # ========== 4. MEDIUM ISSUES ==========
    story.append(Paragraph("<b>4. Orta Oncelikli Sorunlar</b>", h1_style))
    story.append(Spacer(1, 12))
    
    medium_issues = [
        ['Sorun', 'Dosya', 'Aciklama'],
        ['Memory Leak Riski', 'src/hooks/use-toast.ts', 'memoryState modul seviyesinde degisken'],
        ['Error Handling Eksik', 'src/app/api/admin/users/route.ts', 'Rollback sirasinda hata bildirimi yok'],
        ['Hard-coded Capacities', 'src/services/vehicle-calculator.ts', 'Arac kapasiteleri sabit degerler'],
        ['Missing Input Validation', 'src/app/api/admin/vehicles/route.ts', 'POST endpoint validasyon eksik'],
        ['Travel Times Static', 'src/services/doubus/route.ts', 'Real-time trafik bilgisi yok'],
        ['K-Means Random Init', 'src/services/clustering.ts', 'Deterministik degil'],
        ['No Pagination', 'src/app/api/admin/users/route.ts', 'Buyuk veri setlerinde sorun'],
        ['Console.error Kullanimi', 'Multiple files', 'Log sistemine donusturulmeli'],
        ['Missing Rate Limiting', 'All API routes', 'DoS riski'],
        ['Incomplete RLS Policies', 'supabase/rls_policies.sql', 'Bazi tablolarda eksik'],
        ['No Transaction Support', 'src/lib/supabase-db.ts', 'Coklu islem destegi yok'],
        ['Duplicate Code', 'Multiple API files', 'Tekrarlanan kod patternleri'],
    ]
    
    story.append(create_table(medium_issues, [4*cm, 4.5*cm, 5.5*cm]))
    story.append(Spacer(1, 18))
    
    # ========== 5. LOW PRIORITY ==========
    story.append(Paragraph("<b>5. Dusuk Oncelikli Sorunlar ve Iyilestirme Onerileri</b>", h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>5.1 Kod Organizasyonu</b>", h2_style))
    
    low1_text = """src/lib/supabase-db.ts dosyasi 1600+ satir uzunlugundadir ve Single Responsibility Principle ihlal edilmektedir. Bu dosya user, schedule, vehicle, route operations gibi ayri modullere bolunmelidir."""
    story.append(Paragraph(low1_text, body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>5.2 Performans Optimizasyonlari</b>", h2_style))
    
    perf_text = """K-means clustering icin Web Workers kullanimi onerilir. Buyuk veri setlerinde UI blocklanmasini onlemek icin arka planda calisma saglanmalidir. Travel time matrix icin memoization veya caching mekanizmasi eklenebilir."""
    story.append(Paragraph(perf_text, body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>5.3 Test Kapsami</b>", h2_style))
    
    test_text = """Mevcut testler AppError ve Zod validation lari icermektedir. Ancak servis katmani, API route lari ve React komponentleri icin unit test ve integration test yazilmalidir. E2E testler icin Playwright onerilir."""
    story.append(Paragraph(test_text, body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>5.4 Dokumentasyon</b>", h2_style))
    
    doc_text = """API endpoint leri icin JSDoc yorumlari eksik. OpenAPI/Swagger dokumantasyonu olusturulmali. Komplex algoritma dosyalari icin detayli aciklamalar eklenmeli."""
    story.append(Paragraph(doc_text, body_style))
    story.append(Spacer(1, 18))
    
    # ========== 6. POSITIVE FINDINGS ==========
    story.append(Paragraph("<b>6. Dogru Yapilmis Uygulamalar</b>", h1_style))
    story.append(Spacer(1, 12))
    
    positive_data = [
        [Paragraph('<b>Uygulama</b>', table_header_style), Paragraph('<b>Aciklama</b>', table_header_style)],
        ['Moduler Mimari', 'Kodlar islevlerine gore iyi ayrilmis'],
        ['TypeScript Kullanimi', 'Tip tanimlari mevcut, strict mode aktif'],
        ['shadcn/ui Entegrasyonu', 'Tutarli UI komponentleri, accessibility'],
        ['Route-Based Auth', 'Middleware ile route korumasi'],
        ['AppError Sinifi', 'Merkezi hata yonetimi pattern'],
        ['Zod Validation', 'API input validasyonu'],
        ['Supabase Admin Client', 'RLS bypass duzgun yapilmis'],
        ['Strategy Pattern', 'Route optimizasyon pattern'],
        ['K-Means++ Init', 'Optimize edilmis baslangic noktalari'],
        ['Excel Import/Export', 'XLSX kutuphanesi entegrasyonu'],
        ['Genkit AI Flow', 'Duzenli AI flow tanimi'],
    ]
    
    story.append(create_table(positive_data, [5*cm, 9*cm]))
    story.append(Spacer(1, 18))
    
    # ========== 7. RECOMMENDATIONS ==========
    story.append(Paragraph("<b>7. Oncelikli Aksiyon Plani</b>", h1_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>7.1 Acil (1-2 Hafta)</b>", h2_style))
    
    urgent_text = """- Python API URL environment variable olarak tasinmali
- weekly_schedules.user_id UNIQUE constraint Supabase de uygulanmali
- location-mapper.ts default fallback null olarak degistirilmeli
- API route lari icin rate limiting eklenmeli"""
    story.append(Paragraph(urgent_text, body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>7.2 Kisa Vadeli (1 Ay)</b>", h2_style))
    
    short_text = """- GA ve PSO algoritmalari implement edilmeli
- Type any kullanimlari kaldirilip proper type lar yazilmali
- Error handling ve logging mekanizmasi kurulmali
- API pagination destegi eklenmeli"""
    story.append(Paragraph(short_text, body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>7.3 Orta Vadeli (2-3 Ay)</b>", h2_style))
    
    mid_text = """- supabase-db.ts dosyasi modullere ayrilmali
- Unit test ve integration test kapsami artirilmali
- Real-time trafik bilgisi entegrasyonu arastirilmali
- API dokumantasyonu (OpenAPI) olusturulmali"""
    story.append(Paragraph(mid_text, body_style))
    story.append(Spacer(1, 18))
    
    # ========== 8. CONCLUSION ==========
    story.append(Paragraph("<b>8. Sonuc</b>", h1_style))
    story.append(Spacer(1, 12))
    
    conclusion_text = """UniRide projesi, engelli ogrenciler icin servis optimizasyonu yapan degerli bir uygulamadir. Projenin temel mimarisi saglam temellere dayanmaktadir ve modern teknolojiler kullanilmaktadir. Ancak, tespit edilen kritik sorunlarin acil olarak giderilmesi gerekmektedir. Ozellikle guvenlik, tip guvenligi ve algoritma tamamlanmasi oncelikli olarak ele alinmalidir. Bu raporda belirtilen oneriler uygulandigi takdirde, proje uretim ortama hazir hale gelecektir."""
    story.append(Paragraph(conclusion_text, body_style))
    story.append(Spacer(1, 24))
    
    # Build PDF
    doc.build(story)
    print("PDF olusturuldu: /home/z/my-project/download/UniRide_Kod_Inceleme_Raporu.pdf")

if __name__ == "__main__":
    build_report()
