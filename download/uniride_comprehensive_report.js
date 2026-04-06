const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, 
        Header, Footer, AlignmentType, PageOrientation, LevelFormat, 
        TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType, 
        VerticalAlign, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

// Renk paleti - "Ink & Zen" (Profesyonel)
const colors = {
  primary: "0B1220",
  body: "0F172A",
  secondary: "2B2B2B",
  accent: "9AA6B2",
  tableBg: "F1F5F9"
};

// Tablo kenarlıkları
const tableBorder = { style: BorderStyle.SINGLE, size: 12, color: colors.primary };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } };

// Yardımcı fonksiyonlar
const createHeading1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 400, after: 200 },
  children: [new TextRun({ text, bold: true, size: 32, font: "Times New Roman", color: colors.primary })]
});

const createHeading2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 300, after: 150 },
  children: [new TextRun({ text, bold: true, size: 28, font: "Times New Roman", color: colors.primary })]
});

const createBodyParagraph = (text) => new Paragraph({
  spacing: { before: 100, after: 100, line: 312 },
  alignment: AlignmentType.LEFT,
  children: [new TextRun({ text, size: 22, font: "Times New Roman", color: colors.body })]
});

const createBulletItem = (text, reference) => new Paragraph({
  numbering: { reference, level: 0 },
  spacing: { before: 50, after: 50, line: 312 },
  children: [new TextRun({ text, size: 22, font: "Times New Roman", color: colors.body })]
});

// Tablo oluştur
const createTable = (headers, rows, columnWidths) => {
  const tableRows = [];
  
  // Header row
  tableRows.push(new TableRow({
    tableHeader: true,
    children: headers.map((header, i) => new TableCell({
      borders: cellBorders,
      width: { size: columnWidths[i], type: WidthType.DXA },
      shading: { fill: colors.tableBg, type: ShadingType.CLEAR },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: header, bold: true, size: 22, font: "Times New Roman" })]
      })]
    }))
  }));
  
  // Data rows
  rows.forEach(row => {
    tableRows.push(new TableRow({
      children: row.map((cell, i) => new TableCell({
        borders: cellBorders,
        width: { size: columnWidths[i], type: WidthType.DXA },
        verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({
          alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
          children: [new TextRun({ text: cell, size: 20, font: "Times New Roman" })]
        })]
      }))
    }));
  });
  
  return new Table({
    columnWidths,
    margins: { top: 100, bottom: 100, left: 180, right: 180 },
    rows: tableRows
  });
};

// Numbering config
const numberingConfig = {
  config: [
    { reference: "bullet-main", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: "bullet-features", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: "bullet-issues", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: "bullet-improve", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: "bullet-todo", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: "numbered-steps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
  ]
};

// Ana doküman
const doc = new Document({
  numbering: numberingConfig,
  styles: {
    default: { document: { run: { font: "Times New Roman", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Times New Roman", color: colors.primary },
        paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Times New Roman", color: colors.primary },
        paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Times New Roman", color: colors.secondary },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } }
    ]
  },
  sections: [
    // KAPAK SAYFASI
    {
      properties: {
        page: { margin: { top: 0, right: 0, bottom: 0, left: 0 } }
      },
      children: [
        new Paragraph({ spacing: { before: 3000 }, children: [] }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 1000, after: 400 },
          children: [new TextRun({ text: "UniRide", bold: true, size: 72, font: "Times New Roman", color: colors.primary })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "Engelli Öğrenci Taşıma Optimizasyon Sistemi", size: 32, font: "Times New Roman", color: colors.secondary })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 600, after: 200 },
          children: [new TextRun({ text: "KAPSAMLI PROJE ANALİZ RAPORU", bold: true, size: 36, font: "Times New Roman", color: colors.primary })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 2000 },
          children: [new TextRun({ text: new Date().toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric' }), size: 24, font: "Times New Roman", color: colors.accent })]
        }),
        new Paragraph({ children: [new PageBreak()] })
      ]
    },
    // ANA İÇERİK
    {
      properties: {
        page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "UniRide - Proje Analiz Raporu", size: 18, font: "Times New Roman", color: colors.accent, italics: true })]
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "— ", size: 18, font: "Times New Roman", color: colors.accent }),
              new TextRun({ children: [PageNumber.CURRENT], size: 18, font: "Times New Roman", color: colors.accent }),
              new TextRun({ text: " —", size: 18, font: "Times New Roman", color: colors.accent })
            ]
          })]
        })
      },
      children: [
        // İÇİNDEKİLER
        new TableOfContents("İçindekiler", { hyperlink: true, headingStyleRange: "1-2" }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 100, after: 300 },
          children: [new TextRun({ text: "Not: İçindekiler alan kodları ile oluşturulmuştur. Sayfa numaralarını güncellemek için içeriğe sağ tıklayıp \"Alanı Güncelle\" seçeneğini kullanın.", size: 18, font: "Times New Roman", color: "999999", italics: true })]
        }),
        
        new Paragraph({ children: [new PageBreak()] }),
        
        // 1. YÖNETİCİ ÖZETİ
        createHeading1("1. Yönetici Özeti"),
        createBodyParagraph("UniRide, engelli öğrencilerin üniversite kampüslerine ulaşımını optimize eden kapsamlı bir web uygulamasıdır. Next.js 16 tabanlı frontend, Supabase (PostgreSQL) veritabanı ve gelişmiş rota optimizasyon algoritmalarından oluşan bu sistem, tekerlekli sandalye kullanıcıları (Sw) ve yürüyerek hareket edebilen öğrenciler (So) için özel tasarlanmış taşıma çözümleri sunmaktadır."),
        createBodyParagraph("Bu analiz raporu, projenin mevcut durumunu, mimari yapısını, işlevselliklerini, tespit edilen sorunları ve geliştirme önerilerini detaylı olarak ele almaktadır. Özellikle proje içinde yer alan iki ayrı optimizasyon sisteminin (DouBus ve Python Optimizer) durumu kritik bir bulgu olarak değerlendirilmektedir."),
        
        createHeading2("1.1 Proje Özellikleri Özeti"),
        createTable(
          ["Özellik", "Durum", "Açıklama"],
          [
            ["Frontend Framework", "Tamamlandı", "Next.js 16 + App Router"],
            ["Veritabanı", "Tamamlandı", "Supabase (PostgreSQL) + RLS"],
            ["Kimlik Doğrulama", "Tamamlandı", "Supabase Auth + JWT"],
            ["Rota Optimizasyonu", "Tamamlandı", "GA, PSO, 2-Opt, Nearest Neighbor"],
            ["Çoklu Araç Yönlendirme", "Tamamlandı", "K-Means Clustering + TSP"],
            ["Python Optimizer API", "Kullanım Dışı", "Dead Code - Entegre Edilmemiş"]
          ],
          [3500, 2000, 3860]
        ),
        new Paragraph({ spacing: { after: 200 }, children: [] }),
        
        // 2. MİMARİ YAPI
        createHeading1("2. Mimari Yapı"),
        createBodyParagraph("UniRide, modern bir full-stack web uygulaması mimarisi kullanılarak geliştirilmiştir. Sistem, birbirinden bağımsız ancak entegre çalışan bileşenlerden oluşmaktadır. Bu bölümde, projenin teknik mimarisi ve bileşenleri detaylı olarak açıklanmaktadır."),
        
        createHeading2("2.1 Teknoloji Yığını"),
        createTable(
          ["Katman", "Teknoloji", "Versiyon"],
          [
            ["Frontend", "Next.js (App Router)", "16.x"],
            ["UI Framework", "shadcn/ui + Tailwind CSS", "Latest"],
            ["Backend", "Next.js API Routes", "16.x"],
            ["Veritabanı", "Supabase (PostgreSQL)", "2.x"],
            ["Auth", "Supabase Auth", "2.x"],
            ["Route Optimization", "TypeScript DouBus Service", "Custom"],
            ["Alt Optimizer", "Python FastAPI", "Kullanım Dışı"]
          ],
          [3000, 3500, 2860]
        ),
        new Paragraph({ spacing: { after: 200 }, children: [] }),
        
        createHeading2("2.2 Veritabanı Şeması"),
        createBodyParagraph("Proje, 8 ana tablodan oluşan kapsamlı bir veritabanı şemasına sahiptir. Row Level Security (RLS) politikaları ile güvenlik sağlanmaktadır."),
        createBulletItem("users - Kullanıcı hesapları (student, admin, driver rolleri)", "bullet-main"),
        createBulletItem("weekly_schedules - Öğrenci haftalık ders programları", "bullet-main"),
        createBulletItem("ride_requests - Servis talepleri (scheduled/adhoc)", "bullet-main"),
        createBulletItem("vehicles - Araç bilgileri ve kapasiteleri", "bullet-main"),
        createBulletItem("routes - Optimize edilmiş rotalar", "bullet-main"),
        createBulletItem("route_assignments - Araç-şoför-rota atamaları", "bullet-main"),
        createBulletItem("notifications - Kullanıcı bildirimleri", "bullet-main"),
        createBulletItem("admin_settings - Sistem ayarları", "bullet-main"),
        new Paragraph({ spacing: { after: 200 }, children: [] }),
        
        // 3. KRİTİK BULGU: DOUBUS VS PYTHON
        createHeading1("3. Kritik Bulgu: DouBus vs Python Optimizer"),
        createBodyParagraph("Proje incelemesi sırasında tespit edilen en kritik durum, iki ayrı optimizasyon sisteminin bulunmasıdır. Bu sistemler aynı amaç için geliştirilmiş olmasına rağmen, birbirlerinden tamamen bağımsız çalışmaktadır."),
        
        createHeading2("3.1 DouBus Service (TypeScript)"),
        createBodyParagraph("DouBus servisi, TypeScript ile yazılmış ve doğrudan Next.js uygulamasına entegre edilmiş rota optimizasyon sistemidir. Bu servis şu stratejileri desteklemektedir:"),
        createBulletItem("Genetic Algorithm (GA) - Popülasyon tabanlı meta-sezgisel optimizasyon", "bullet-features"),
        createBulletItem("Particle Swarm Optimization (PSO) - Sürü zekası tabanlı optimizasyon", "bullet-features"),
        createBulletItem("2-Opt - Lokal arama iyileştirme algoritması", "bullet-features"),
        createBulletItem("Nearest Neighbor - Greedy tabanlı hızlı çözüm", "bullet-features"),
        createBulletItem("Permutation - Tam arama (n≤10 için optimal)", "bullet-features"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        createBodyParagraph("DouBus servisi aktif olarak kullanılmaktadır ve /api/optimize-route ile /api/calculate-vehicles endpoint'leri tarafından çağrılmaktadır."),
        
        createHeading2("3.2 Python Optimizer API (FastAPI)"),
        createBodyParagraph("Python tabanlı optimizer API, optimizer_api/ klasöründe yer alır ve şu stratejileri içermektedir:"),
        createBulletItem("OR-Tools CVRP - Google'ın araç yönlendirme kütüphanesi", "bullet-features"),
        createBulletItem("K-Means TSP - Kümeleme tabanlı TSP çözümü", "bullet-features"),
        createBulletItem("Greedy Heuristic - Hızlı sezgisel çözüm", "bullet-features"),
        createBulletItem("Permutation TSP - Tam permütasyon araması", "bullet-features"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        createBodyParagraph("config.ts dosyasında OPTIMIZER_API_URL tanımlı olmasına rağmen, bu API hiçbir endpoint tarafından çağrılmamaktadır. Bu durum 'dead code' olarak değerlendirilmektedir."),
        
        createHeading2("3.3 Karşılaştırma Tablosu"),
        createTable(
          ["Özellik", "DouBus (TS)", "Python API"],
          [
            ["Kullanım Durumu", "AKTİF", "Kullanım Dışı"],
            ["Entegrasyon", "Direkt Import", "HTTP API"],
            ["Strateji Sayısı", "5", "4"],
            ["GA/PSO Desteği", "Var", "Yok"],
            ["OR-Tools Desteği", "Yok", "Var"],
            ["Bakım Gereksinimi", "Düşük", "Yüksek"]
          ],
          [3500, 2930, 2930]
        ),
        new Paragraph({ spacing: { after: 200 }, children: [] }),
        
        createHeading2("3.4 Öneri"),
        createBodyParagraph("Bu durum için iki ana yaklaşım önerilmektedir. Birincisi, Python API tamamen kaldırılabilir ve kod tabanından silinebilir. Bu yaklaşım, bakım yükünü azaltacak ve kod karmaşasını ortadan kaldıracaktır. İkincisi, Python API'deki OR-Tools CVRP stratejisi TypeScript'e port edilebilir ve DouBus servisine entegre edilebilir. OR-Tools, büyük ölçekli VRP problemleri için endüstri standardıdır ve değerli bir özellik olabilir."),
        
        // 4. MEVCUT İŞLEVSELLİKLER
        createHeading1("4. Mevcut İşlevsellikler"),
        
        createHeading2("4.1 Öğrenci (Student) Özellikleri"),
        createBulletItem("Dashboard - Yaklaşan servis bilgileri ve hızlı erişim menüsü", "bullet-features"),
        createBulletItem("Ders Programı Yönetimi - Haftalık program oluşturma ve düzenleme", "bullet-features"),
        createBulletItem("Anlık Servis Talebi - Program dışı taşıma ihtiyaçları için talep oluşturma", "bullet-features"),
        createBulletItem("Servis Takibi - Aktif servis durumunu görüntüleme", "bullet-features"),
        createBulletItem("Geçmiş Rotalar - Önceki servis kullanımlarını görüntüleme", "bullet-features"),
        createBulletItem("Profil Yönetimi - Kişisel bilgileri güncelleme", "bullet-features"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        
        createHeading2("4.2 Admin Özellikleri"),
        createBulletItem("Kullanıcı Yönetimi - Öğrenci, sürücü ve admin hesaplarını yönetme", "bullet-features"),
        createBulletItem("Araç Yönetimi - Servis araçlarını ekleme, düzenleme, silme", "bullet-features"),
        createBulletItem("Servis Talepleri - Gelen talepleri onaylama/reddetme", "bullet-features"),
        createBulletItem("Araç Planlama - Öğrencileri araçlara atama ve rota oluşturma", "bullet-features"),
        createBulletItem("Rota Test - Farklı optimizasyon stratejilerini test etme", "bullet-features"),
        createBulletItem("Raporlar - Sistem kullanım istatistiklerini görüntüleme", "bullet-features"),
        createBulletItem("Ders Programları - Toplu yükleme ve düzenleme", "bullet-features"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        
        createHeading2("4.3 Sürücü (Driver) Özellikleri"),
        createBulletItem("Günlük Atamalar - Atanan rotaları ve öğrencileri görüntüleme", "bullet-features"),
        createBulletItem("Navigasyon - Rota üzerindeki durakları takip etme", "bullet-features"),
        createBulletItem("Geçmiş Rotalar - Önceki görevleri görüntüleme", "bullet-features"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        
        createHeading2("4.4 Rota Optimizasyon Algoritmaları"),
        createBodyParagraph("Proje, TSP (Travelling Salesman Problem) çözümü için birden fazla algoritma sunmaktadır. Bu algoritmalar, farklı performans ve kalite dengeleri sunarak çeşitli senaryolara uyum sağlamaktadır."),
        createTable(
          ["Algoritma", "Zaman Karmaşıklığı", "Kullanım Senaryosu"],
          [
            ["Nearest Neighbor", "O(n²)", "Hızlı çözüm, küçük problemler"],
            ["2-Opt", "O(n³)", "Dengeli performans, orta ölçek"],
            ["Genetic Algorithm", "O(g × p × n²)", "Büyük problemler, yakın-optimal"],
            ["PSO", "O(i × s × n²)", "Hızlı yakınsama, meta-sezgisel"],
            ["Permutation", "O(n!)", "n≤10 için garanti optimal"]
          ],
          [3500, 2500, 3360]
        ),
        new Paragraph({ spacing: { after: 200 }, children: [] }),
        
        // 5. TESPİT EDİLEN SORUNLAR
        createHeading1("5. Tespit Edilen Sorunlar"),
        
        createHeading2("5.1 Kritik Sorunlar"),
        createBulletItem("Python Optimizer Entegrasyon Eksikliği: API tanımlı ancak kullanılmıyor. Dead code olarak değerlendirilmelidir.", "bullet-issues"),
        createBulletItem("Type Safety Eksiklikleri: Bazı dosyalarda 'any' tip kullanımı mevcut.", "bullet-issues"),
        createBulletItem("Pagination Eksikliği: Büyük veri setlerinde performans sorunu yaşanabilir.", "bullet-issues"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        
        createHeading2("5.2 Orta Öncelikli Sorunlar"),
        createBulletItem("Rate Limiting Eksikliği: API endpoint'lerinde koruma yok.", "bullet-issues"),
        createBulletItem("Hata Yönetimi: Bazı endpoint'lerde yetersiz error handling.", "bullet-issues"),
        createBulletItem("Logging: Yapılandırılmış log sistemi yok.", "bullet-issues"),
        createBulletItem("Test Coverage: Unit ve integration testleri eksik.", "bullet-issues"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        
        createHeading2("5.3 Düşük Öncelikli Sorunlar"),
        createBulletItem("Code Documentation: Yetersiz yorum satırları.", "bullet-issues"),
        createBulletItem("Environment Variables: Bazı sabitler hard-coded.", "bullet-issues"),
        createBulletItem("CSS Organization: Tailwind class'ları organize edilebilir.", "bullet-issues"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        
        // 6. GELİŞTİRME ÖNERİLERİ
        createHeading1("6. Geliştirme Önerileri"),
        
        createHeading2("6.1 Kısa Vadeli (1-2 Hafta)"),
        createBulletItem("Python Optimizer API kaldırılmalı veya entegre edilmeli", "bullet-improve"),
        createBulletItem("TypeScript tip güvenliği iyileştirilmeli", "bullet-improve"),
        createBulletItem("API rate limiting eklenmeli", "bullet-improve"),
        createBulletItem("Pagination implementasyonu yapılmalı", "bullet-improve"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        
        createHeading2("6.2 Orta Vadeli (1-2 Ay)"),
        createBulletItem("Kapsamlı test suite oluşturulmalı (Jest + Playwright)", "bullet-improve"),
        createBulletItem("Yapılandırılmış logging sistemi eklenmeli (Winston/Pino)", "bullet-improve"),
        createBulletItem("Real-time notifications (WebSocket/Server-Sent Events)", "bullet-improve"),
        createBulletItem("API documentation (Swagger/OpenAPI)", "bullet-improve"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        
        createHeading2("6.3 Uzun Vadeli (3+ Ay)"),
        createBulletItem("Mobile uygulama (React Native veya PWA)", "bullet-improve"),
        createBulletItem("Gelişmiş analitik dashboard", "bullet-improve"),
        createBulletItem("AI tabanlı talep tahmin sistemi", "bullet-improve"),
        createBulletItem("Çoklu kampüs desteği", "bullet-improve"),
        new Paragraph({ spacing: { after: 100 }, children: [] }),
        
        // 7. KALAN İŞLER
        createHeading1("7. Kalan İşler ve Önceliklendirme"),
        createTable(
          ["İş", "Öncelik", "Tahmini Süre", "Durum"],
          [
            ["Python API entegrasyon/kaldırma", "Yüksek", "4 saat", "Bekliyor"],
            ["Type Safety iyileştirmesi", "Yüksek", "8 saat", "Bekliyor"],
            ["Rate Limiting", "Orta", "4 saat", "Bekliyor"],
            ["Pagination", "Orta", "6 saat", "Bekliyor"],
            ["Test Suite", "Orta", "16 saat", "Bekliyor"],
            ["Logging System", "Düşük", "4 saat", "Bekliyor"],
            ["API Documentation", "Düşük", "8 saat", "Bekliyor"]
          ],
          [3800, 1800, 2000, 1760]
        ),
        new Paragraph({ spacing: { after: 200 }, children: [] }),
        
        // 8. SONUÇ
        createHeading1("8. Sonuç"),
        createBodyParagraph("UniRide projesi, engelli öğrenci taşıma optimizasyonu için sağlam bir temel sunmaktadır. Next.js 16, Supabase ve gelişmiş optimizasyon algoritmalarının kombinasyonu, modern ve ölçeklenebilir bir çözüm oluşturmaktadır."),
        createBodyParagraph("Ancak, tespit edilen en kritik sorun olan Python Optimizer API'nin kullanım dışı olması, kod tekrarı ve bakım yükü yaratmaktadır. Bu sorunun çözümü, projenin uzun vadeli başarısı için önemlidir."),
        createBodyParagraph("Önerilen geliştirme yol haritası takip edildiğinde, UniRide production-ready bir uygulama haline gelecektir. Kısa vadeli öneriler öncelikli olarak ele alınmalı, ardından orta ve uzun vadeli hedeflere yönelinmelidir.")
      ]
    }
  ]
});

// Kaydet
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/home/z/my-project/download/UniRide_Kapsamli_Analiz_Raporu.docx", buffer);
  console.log("Rapor başarıyla oluşturuldu: /home/z/my-project/download/UniRide_Kapsamli_Analiz_Raporu.docx");
});
