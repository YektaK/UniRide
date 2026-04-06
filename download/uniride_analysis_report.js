const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header, Footer, 
        AlignmentType, PageOrientation, LevelFormat, HeadingLevel, BorderStyle, WidthType, 
        ShadingType, VerticalAlign, PageNumber, PageBreak, TableOfContents } = require('docx');
const fs = require('fs');

// Color scheme - Nordic (cool gray, misty blue)
const colors = {
  primary: "#1A1F16",
  body: "#2D3329",
  secondary: "#4A5548",
  accent: "#94A3B8",
  tableBg: "#F8FAF7"
};

const tableBorder = { style: BorderStyle.SINGLE, size: 8, color: colors.accent };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Times New Roman", size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 48, bold: true, color: colors.primary, font: "Times New Roman" },
        paragraph: { spacing: { before: 240, after: 120 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: colors.primary, font: "Times New Roman" },
        paragraph: { spacing: { before: 300, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: colors.secondary, font: "Times New Roman" },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: colors.secondary, font: "Times New Roman" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } }
    ]
  },
  numbering: {
    config: [
      { reference: "bullet-list",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-list-1",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-list-2",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-list-3",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-list-4",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-list-5",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-list-6",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
    ]
  },
  sections: [
    // COVER PAGE
    {
      properties: {
        page: { margin: { top: 0, right: 0, bottom: 0, left: 0 } }
      },
      children: [
        new Paragraph({ spacing: { before: 3000 }, children: [] }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 400 },
          children: [new TextRun({ text: "UniRide", size: 72, bold: true, color: colors.primary, font: "Times New Roman" })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "Engelli Öğrenci Servis Optimizasyon Sistemi", size: 28, color: colors.secondary, font: "Times New Roman" })]
        }),
        new Paragraph({ spacing: { before: 1500 }, children: [] }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "KAPSAMLI PROJE ANALİZ RAPORU", size: 36, bold: true, color: colors.primary, font: "Times New Roman" })]
        }),
        new Paragraph({ spacing: { before: 500 }, children: [] }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Mevcut Durum | İşleyiş | Hatalar | Geliştirme Önerileri", size: 22, color: colors.secondary, font: "Times New Roman" })]
        }),
        new Paragraph({ spacing: { before: 2000 }, children: [] }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Tarih: Mart 2026", size: 20, color: colors.accent, font: "Times New Roman" })]
        })
      ]
    },
    // TABLE OF CONTENTS
    {
      properties: {
        page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
      },
      headers: {
        default: new Header({ children: [new Paragraph({ 
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "UniRide - Proje Analiz Raporu", size: 18, color: colors.accent })]
        })] })
      },
      footers: {
        default: new Footer({ children: [new Paragraph({ 
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Sayfa ", size: 18 }), new TextRun({ children: [PageNumber.CURRENT], size: 18 }), new TextRun({ text: " / ", size: 18 }), new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18 })]
        })] })
      },
      children: [
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          children: [new TextRun({ text: "İçindekiler", bold: true })]
        }),
        new TableOfContents("İçindekiler", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 200 },
          children: [new TextRun({ text: "Not: Bu içindekiler tablosu alan kodlarıyla oluşturulmuştur. Sayfa numaralarının güncel olması için sağ tıklayıp \"Alanı Güncelle\" seçeneğini kullanın.", size: 18, color: colors.accent, italics: true })]
        }),
        new Paragraph({ children: [new PageBreak()] })
      ]
    },
    // MAIN CONTENT
    {
      properties: {
        page: { margin: { top: 1800, right: 1440, bottom: 1440, left: 1440 } }
      },
      headers: {
        default: new Header({ children: [new Paragraph({ 
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "UniRide - Proje Analiz Raporu", size: 18, color: colors.accent })]
        })] })
      },
      footers: {
        default: new Footer({ children: [new Paragraph({ 
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Sayfa ", size: 18 }), new TextRun({ children: [PageNumber.CURRENT], size: 18 }), new TextRun({ text: " / ", size: 18 }), new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18 })]
        })] })
      },
      children: [
        // SECTION 1: EXECUTIVE SUMMARY
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. Yönetici Özeti")] }),
        
        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "UniRide, engelli öğrenciler için optimize edilmiş servis taşımacılığı sağlayan kapsamlı bir Next.js web uygulamasıdır. Proje, Doğuş Üniversitesi'nde öğrenim gören engelli öğrencilerin günlük ulaşım ihtiyaçlarını karşılamak amacıyla geliştirilmiştir. Sistem, haftalık ders programlarına dayalı otomatik rota optimizasyonu, çoklu araç ataması ve gerçek zamanlı takip özellikleri sunmaktadır.", size: 22 })]
        }),
        
        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Bu analiz raporu, projenin mevcut durumunu, işleyişini, hatalı ve eksik yönlerini, ayrıca geliştirme önerilerini detaylı bir şekilde ele almaktadır. Proje, 125 TypeScript dosyasından oluşmakta olup, frontend, backend, veritabanı ve optimizasyon servisleri olmak üzere dört ana bileşenden oluşmaktadır.", size: 22 })]
        }),

        // SECTION 2: PROJE YAPISI
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. Proje Yapısı ve Organizasyon")] }),
        
        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.1 Teknoloji Stack")] }),
        
        new Table({
          columnWidths: [3000, 6360],
          margins: { top: 100, bottom: 100, left: 150, right: 150 },
          rows: [
            new TableRow({
              tableHeader: true,
              children: [
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Katman", bold: true, size: 22 })] })] }),
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Teknolojiler", bold: true, size: 22 })] })] })
              ]
            }),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Frontend", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Backend", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Next.js API Routes, Supabase Auth", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Veritabanı", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Supabase (PostgreSQL), RLS Policies", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Optimizasyon", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "DouBus Service, GA, PSO, 2-Opt, K-Means", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "AI Entegrasyonu", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Google Genkit, Gemini 2.0 Flash", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Python API", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "FastAPI, OR-Tools CVRP, Greedy Heuristics", size: 22 })] })] })
            ]})
          ]
        }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.2 Dizin Yapısı")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Proje, modern Next.js App Router mimarisini kullanmaktadır. Kaynak kodu src/ dizini altında organize edilmiştir. Temel dizinler ve içerikleri aşağıdaki gibidir:", size: 22 })]
        }),

        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun({ text: "src/app/ - Sayfa bileşenleri ve API route'ları (Next.js App Router)", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun({ text: "src/components/ - Yeniden kullanılabilir UI bileşenleri (shadcn/ui tabanlı)", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun({ text: "src/lib/ - Veritabanı işlemleri, auth, konfigürasyon", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun({ text: "src/services/ - İş mantığı ve optimizasyon servisleri", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun({ text: "src/types/ - TypeScript tip tanımlamaları", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun({ text: "src/ai/ - Genkit AI akışları", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun({ text: "optimizer_api/ - Python FastAPI optimizasyon servisi", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun({ text: "supabase/ - Veritabanı şeması ve RLS politikaları", size: 22 })] }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        // SECTION 3: İŞLEYİŞ
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. Uygulama İşleyişi")] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.1 Kullanıcı Rolleri ve Yetkiler")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Sistem üç farklı kullanıcı rolü desteklemektedir. Her rolün kendine özgü sayfaları ve yetkileri bulunmaktadır. Öğrenciler ders programı yönetimi ve servis talebi oluşturma yetkisine sahiptir. Şoförler araç atamalarını görüntüleyebilir ve navigasyon yapabilir. Admin kullanıcıları ise tüm sistemi yönetebilir.", size: 22 })]
        }),

        new Table({
          columnWidths: [2000, 3680, 3680],
          margins: { top: 100, bottom: 100, left: 150, right: 150 },
          rows: [
            new TableRow({
              tableHeader: true,
              children: [
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Rol", bold: true, size: 22 })] })] }),
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Sayfalar", bold: true, size: 22 })] })] }),
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Yetkiler", bold: true, size: 22 })] })] })
              ]
            }),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Student", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Dashboard, Schedule, Request Ride, History", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Program görüntüleme/düzenleme, talep oluşturma", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Driver", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Assignments, Navigation, History", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Atama görüntüleme, navigasyon", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Admin", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Users, Vehicles, Schedules, Requests, Reports", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Tam yönetim yetkisi, optimizasyon", size: 22 })] })] })
            ]})
          ]
        }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.2 Ana İş Akışları")] }),

        new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("3.2.1 Öğrenci İş Akışı")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Öğrenci kayıt olduktan sonra sisteme giriş yapar ve dashboard üzerinden yaklaşan servis bilgilerini görür. Haftalık ders programını sisteme girer veya Excel ile toplu yükler. Sistem otomatik olarak bu programa dayalı servis talepleri oluşturur. Öğrenci, bir önceki gün saat 22:00'de gelen bildirimi onaylar. Servis günü araç takibi yapabilir ve geçmiş servislerini görüntüleyebilir.", size: 22 })]
        }),

        new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("3.2.2 Admin İş Akışı")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Admin kullanıcıları araç, şoför ve öğrenci yönetimi yapabilir. Toplu Excel yüklemesi ile öğrenci programlarını sisteme aktarabilir. Rota optimizasyonunu tetikleyerek öğrencileri araçlara atayabilir. Şoför görevlendirmelerini Excel veya PDF olarak dışa aktarabilir. Raporlama sayfasından zaman bazlı talep analizi yapabilir.", size: 22 })]
        }),

        new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("3.2.3 Şoför İş Akışı")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Şoförler atandıkları güzergahları ve öğrenci listelerini görüntüler. Navigasyon sayfasından optimize edilmiş rotayı takip eder. Öğrenci alım/bırakım işlemlerini sisteme kaydeder. Geçmiş görevlerini tarih bazlı filtreleyebilir.", size: 22 })]
        }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.3 Rota Optimizasyon Süreci")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "DouBus servisi, engelli öğrenci taşımacılığı için özelleştirilmiş bir rota optimizasyon sistemi sunar. Sistem, öğrencilerin engel türlerine (Sw: tekerlekli sandalye, So: diğer engeller) göre araç kapasitesi hesaplar. K-Means kümeleme ile öğrencileri gruplar ve her küme için optimal rotayı hesaplar. Rota stratejileri arasında Genetik Algoritma (GA), Parçacık Sürü Optimizasyonu (PSO), 2-Opt ve permütasyon yöntemleri bulunur.", size: 22 })]
        }),

        // SECTION 4: VERİTABANI
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. Veritabanı Mimarisi")] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.1 Tablo Yapısı")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Supabase (PostgreSQL) üzerinde 8 ana tablo bulunmaktadır. Tablolar arası ilişkiler foreign key kısıtlamaları ile tanımlanmıştır. Row Level Security (RLS) politikaları ile veri güvenliği sağlanmıştır. Tüm tablolarda updated_at için otomatik tetikleyici mevcuttur.", size: 22 })]
        }),

        new Table({
          columnWidths: [2500, 6860],
          margins: { top: 100, bottom: 100, left: 150, right: 150 },
          rows: [
            new TableRow({
              tableHeader: true,
              children: [
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Tablo", bold: true, size: 22 })] })] }),
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Açıklama", bold: true, size: 22 })] })] })
              ]
            }),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "users", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Kullanıcı bilgileri (rol, engel türü, adres, koordinat)", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "weekly_schedules", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Haftalık ders programları (JSONB entries)", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "ride_requests", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Servis talepleri (durum, zaman, konum)", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "vehicles", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Araç bilgileri (kapasite, plaka, durum)", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "routes", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Optimize edilmiş rotalar (waypoints, süre)", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "route_assignments", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Araç-şoför-öğrenci atamaları", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "notifications", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Kullanıcı bildirimleri", size: 22 })] })] })
            ]}),
            new TableRow({ children: [
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "admin_settings", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Sistem ayarları (bildirim şablonları)", size: 22 })] })] })
            ]})
          ]
        }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        // SECTION 5: HATALAR
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. Tespit Edilen Sorunlar")] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.1 Kritik Sorunlar")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Proje incelendiğinde, sistemin çalışmasını etkileyebilecek veya güvenlik riski oluşturabilecek kritik sorunlar tespit edilmiştir. Bu sorunların bir kısmı önceki düzeltmeler ile giderilmiş olsa da, bazıları halen mevcuttur.", size: 22 })]
        }),

        new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "TypeScript Type Safety: supabase-db.ts dosyasında toCamelCase ve toSnakeCase fonksiyonları 'any' tipi kullanmaktadır. Bu, runtime hatalarına neden olabilir.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Database Constraint Eksikliği: weekly_schedules.user_id için UNIQUE constraint bulunmamaktadır. Bir kullanıcının birden fazla programı olabilir.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Dev-Reset Endpoint Güvenliği: /api/auth/dev-reset endpoint'i production'da açık kalırsa güvenlik riski oluşturur.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Notification Sistemi Eksik: Bildirim gönderimi için Cloud Functions veya scheduled job mevcut değil.", size: 22 })] }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.2 Orta Öncelikli Sorunlar")] }),

        new Paragraph({ numbering: { reference: "numbered-list-2", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Error Handling: API route'larında yetersiz hata yönetimi mevcut. Hatalar console.log ile yazılıyor ama kullanıcıya detaylı bilgi verilmiyor.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-2", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Input Validation: Zod veya benzeri bir validation kütüphanesi kullanılmamış. Form validasyonları yetersiz.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-2", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Caching: Veritabanı sorguları için caching mekanizması yok. Her istek veritabanına gidiyor.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-2", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Testing: Unit veya integration testleri bulunmamaktadır. Kod değişikliklerinin regresyon testi yapılamıyor.", size: 22 })] }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.3 Düşük Öncelikli Sorunlar")] }),

        new Paragraph({ numbering: { reference: "numbered-list-3", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Hard-coded Değerler: Bazı sabitler kod içinde tanımlı. Bunlar environment variable'a taşınmalı.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-3", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Console.log Kullanımı: Production'da console.log'lar temizlenmeli veya logging library kullanılmalı.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-3", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Duplicate Code: Bazı fonksiyonlar birden fazla yerde tekrarlanmış.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-3", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Documentation: API ve fonksiyon dokümantasyonları eksik.", size: 22 })] }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        // SECTION 6: EKSİK ÖZELLİKLER
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("6. Eksik Özellikler ve Tamamlanmamış İşler")] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.1 Bildirim Sistemi")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Bildirim sistemi için veritabanı tablosu mevcut ancak gönderim mekanizması eksik. Öğrencilere bir önceki gün saat 22:00'de bildirim gönderilmesi gerekiyor. Bu işlem için Firebase Cloud Functions veya Supabase Edge Functions ile scheduled job oluşturulmalı. Şu an sadece frontend'de bildirim görüntüleniyor, push notification veya email gönderimi yok.", size: 22 })]
        }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.2 Otomatik Planlama")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Gece 23:00'de otomatik rota optimizasyonu ve araç ataması yapılması planlanmış ancak scheduled job mevcut değil. schedule-to-requests.ts servisi hazır ancak otomatik tetikleme yok. Admin manuel olarak tetiklemek zorunda.", size: 22 })]
        }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.3 Gerçek Zamanlı Takip")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "track-ride sayfası mevcut ancak gerçek GPS entegrasyonu yok. Araç konumu için WebSocket veya Server-Sent Events gerekli. Şu an sadece statik rota bilgisi gösteriliyor.", size: 22 })]
        }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.4 Ödeme Entegrasyonu")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Ödeme sistemi entegrasyonu planlanmış ancak implement edilmemiş. İyzipay veya Stripe entegrasyonu gerekiyor.", size: 22 })]
        }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        // SECTION 7: ÖNERİLER
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("7. Geliştirme Önerileri")] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.1 Hemen Yapılması Gerekenler (1-2 Hafta)")] }),

        new Paragraph({ numbering: { reference: "numbered-list-4", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "TypeScript tip güvenliğini artırın: 'any' tiplerini proper tiplerle değiştirin.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-4", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Database constraint ekleyin: weekly_schedules.user_id için UNIQUE constraint.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-4", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Dev-reset endpoint'ini environment bazlı koruyun: if (process.env.NODE_ENV !== 'development') return 403.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-4", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Zod ile API input validation ekleyin.", size: 22 })] }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.2 Kısa Vadeli (1 Ay)")] }),

        new Paragraph({ numbering: { reference: "numbered-list-5", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Supabase Edge Functions ile scheduled job oluşturun (bildirim ve planlama için).", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-5", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Redis veya Upstash ile caching katmanı ekleyin.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-5", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Jest ve React Testing Library ile test suite oluşturun.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-5", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Error tracking için Sentry entegrasyonu yapın.", size: 22 })] }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.3 Orta Vadeli (2-3 Ay)")] }),

        new Paragraph({ numbering: { reference: "numbered-list-6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "WebSocket ile gerçek zamanlı araç takibi.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Mobil uygulama (React Native veya PWA).", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Ödeme sistemi entegrasyonu.", size: 22 })] }),
        new Paragraph({ numbering: { reference: "numbered-list-6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Advanced analytics dashboard.", size: 22 })] }),

        new Paragraph({ spacing: { before: 200 }, children: [] }),

        // SECTION 8: SONUÇ
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("8. Sonuç")] }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "UniRide projesi, engelli öğrenci taşımacılığı için sağlam bir temel üzerine inşa edilmiştir. Next.js 16, TypeScript ve Supabase kullanılarak modern bir teknoloji stack ile geliştirilmiştir. DouBus rota optimizasyon servisi, GA ve PSO algoritmaları ile desteklenmiştir.", size: 22 })]
        }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Mevcut durumda temel CRUD işlemleri, kullanıcı yönetimi, rota optimizasyonu ve raporlama fonksiyonları çalışır durumdadır. Ancak bildirim sistemi, otomatik planlama ve gerçek zamanlı takip gibi kritik özellikler eksiktir. Bu eksikliklerin giderilmesi, projeyi production-ready hale getirecektir.", size: 22 })]
        }),

        new Paragraph({
          spacing: { after: 200 },
          children: [new TextRun({ text: "Önerilen geliştirme planı izlendiğinde, 2-3 ay içinde tam fonksiyonel bir sistem elde edilecektir. Öncelik verilecek konular: tip güvenliği, scheduled jobs ve testing altyapısıdır.", size: 22 })]
        })
      ]
    }
  ]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/home/z/my-project/download/UniRide_Proje_Analiz_Raporu.docx", buffer);
  console.log("Rapor oluşturuldu: UniRide_Proje_Analiz_Raporu.docx");
});
