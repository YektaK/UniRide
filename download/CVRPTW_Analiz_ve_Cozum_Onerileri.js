const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, 
        Header, Footer, AlignmentType, PageOrientation, LevelFormat, 
        TableOfContents, HeadingLevel, BorderStyle, WidthType, 
        ShadingType, VerticalAlign, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

// Color palette - Academic style
const colors = {
  primary: "#1A1F16",
  body: "#2D3329",
  secondary: "#4A5548",
  accent: "#94A3B8",
  tableBg: "#F8FAF7"
};

const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: colors.secondary };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Times New Roman", size: 24 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 56, bold: true, color: colors.primary, font: "Times New Roman" },
        paragraph: { spacing: { before: 240, after: 120 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: colors.primary, font: "Times New Roman" },
        paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: colors.secondary, font: "Times New Roman" },
        paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: colors.body, font: "Times New Roman" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } }
    ]
  },
  numbering: {
    config: [
      { reference: "bullet-list",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-1",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-2",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-3",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-4",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
    ]
  },
  sections: [
    // Cover Page
    {
      properties: { page: { margin: { top: 0, right: 0, bottom: 0, left: 0 } } },
      children: [
        new Paragraph({ spacing: { before: 6000 } }),
        new Paragraph({ 
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "CVRPTW:", size: 72, bold: true, color: colors.primary, font: "Times New Roman" })]
        }),
        new Paragraph({ 
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Ölçeklenebilirlik ve Kümeleme Sezgiselleri", size: 48, color: colors.secondary, font: "Times New Roman" })]
        }),
        new Paragraph({ spacing: { before: 1000 } }),
        new Paragraph({ 
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Akademik Araştırma ve Çözüm Önerileri Raporu", size: 28, color: colors.body, font: "Times New Roman" })]
        }),
        new Paragraph({ spacing: { before: 2000 } }),
        new Paragraph({ 
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "UniRide Projesi", size: 24, color: colors.accent, font: "Times New Roman" })]
        }),
        new Paragraph({ 
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Mart 2026", size: 22, color: colors.accent, font: "Times New Roman" })]
        })
      ]
    },
    // Main Content
    {
      properties: { page: { margin: { top: 1800, right: 1440, bottom: 1440, left: 1440 } } },
      headers: {
        default: new Header({ children: [new Paragraph({ 
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "CVRPTW Analiz Raporu", size: 20, color: colors.accent, font: "Times New Roman" })]
        })] })
      },
      footers: {
        default: new Footer({ children: [new Paragraph({ 
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Sayfa ", size: 20 }), new TextRun({ children: [PageNumber.CURRENT], size: 20 }), new TextRun({ text: " / ", size: 20 }), new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 20 })]
        })] })
      },
      children: [
        // TOC
        new TableOfContents("İçindekiler", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({ 
          alignment: AlignmentType.CENTER,
          spacing: { before: 200 },
          children: [new TextRun({ text: "Not: İçindekiler sayfası güncellendiğinde sayfa numaraları otomatik güncellenecektir.", size: 18, color: "999999", italics: true })]
        }),
        new Paragraph({ children: [new PageBreak()] }),

        // Executive Summary
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. Yönetici Özeti")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Bu rapor, UniRide projesi kapsamında karşılaşılan Capacitated Vehicle Routing Problem with Time Windows (CVRPTW) probleminin ölçeklenebilirlik sorunlarını ele almaktadır. Mevcut öğrenci sayısı N≈30 seviyelerinden N≥300 seviyelerine çıkış hedeflenirken, \"Cluster-First, Route-Second\" yaklaşımının katı (rigid) yapısının yarattığı verimsizlikler analiz edilmiş ve güncel akademik literatür ışığında üç alternatif strateji değerlendirilmiştir. Araştırma bulguları, Hybrid Genetic Search (HGS) algoritmasının ve PyVRP kütüphanesinin bu problem için en uygun çözüm olduğunu ortaya koymaktadır.", font: "Times New Roman", size: 24 })]
        }),

        // Problem Definition
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. Problem Tanımı")] }),
        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.1 Proje Kapsamı")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "UniRide projesi, fiziksel engelli (Sw - tekerlekli sandalye) ve engeli bulunmayan (So - normal koltuk) üniversite öğrencilerinin belirli zaman dilimlerinde kampüs içi ve dışı noktalara taşınmasını amaçlamaktadır. Bu, klasik bir Capacitated Vehicle Routing Problem with Time Windows (CVRPTW) modelidir ve lojistik alanındaki en karmaşık kombinatoryal optimizasyon problemlerinden birini temsil eder. Problemin zorluğu, hem kapasite kısıtlarının heterojen yapısından (tekerlekli sandalye ve normal koltuk için farklı kapasiteler) hem de zaman penceresi kısıtlarının dinamik yapısından kaynaklanmaktadır.", font: "Times New Roman", size: 24 })]
        }),
        
        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.2 Kısıtlar (Constraints)")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Sistemde tanımlanan temel kısıtlar şu şekildedir:", font: "Times New Roman", size: 24 })]
        }),
        new Paragraph({ numbering: { reference: "numbered-1", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Araç Kapasitesi: Her aracın maksimum 4 tekerlekli sandalyeli öğrenci (Sw) ve maksimum 5 normal koltuk (So) kapasitesi vardır. Tam kapasite Cmax = 9'dur. Bu heterojen kapasite yapısı, klasik CVRP'den farklı olarak çok boyutlu kapasite planlaması gerektirmektedir.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-1", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Sürüş Süresi Sınırı (Time Window): Bir aracın kampüsten çıkıp tüm öğrencileri bırakıp/alıp tekrar dönmesi için geçen toplam süre belirlenen bir sınırı (Tmax = 45-120 dakika) aşmamalıdır. Bu kısıt, öğrencilerin ders saatlerine yetişmesi açısından kritik öneme sahiptir.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-1", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Mesafe/Zaman Matrisi: Noktalar arası süre asimetriktir ve gerçek trafik/mesafe verilerine dayalı bir [V×V] matrisinden okunmaktadır. Bu asimetrik yapı, A→B ve B→A sürelerinin farklı olabileceği gerçek dünya koşullarını yansıtmaktadır.", font: "Times New Roman", size: 24 })] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.3 Mevcut Mimari ve Sorunlar")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Mevcut sistem, büyük ölçekli problemler (N≥300) için doğrudan sezgisel algoritma uygulamasının eksponansiyel zaman karmaşıklığı (O(N!) veya O(N²)) nedeniyle uygulanabilir olmaması nedeniyle \"Cluster-First, Route-Second\" (Önce Kümele, Sonra Rotala) prensibini benimsemiştir. Bu yaklaşımda K-Means algoritması ile öğrenciler kapasiteye bağlı olarak belirli sayıda (K) araca bölünmekte, ardından oluşan her küçük alt kümeye Genetik Algoritma (GA) veya PSO uygulanmaktadır.", font: "Times New Roman", size: 24 })]
        }),
        
        new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Temel Sorun: Katı Kümeleme (Rigid Clustering)")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Mevcut sistemdeki temel sorunlar şunlardır:", font: "Times New Roman", size: 24 })]
        }),
        new Paragraph({ numbering: { reference: "numbered-2", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "K-Means gibi mesafe tabanlı standart kümeleme algoritmaları, gerçek trafik süresini (time_matrix) ve Tmax (maksimum tur süresi) kısıtını görmezden gelmektedir. Bu durum, coğrafi olarak yakın ancak trafik açısından uzak noktaların aynı kümeye atanmasına yol açmaktadır.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-2", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Genetik Algoritma çizdiği rotada 45 dakika sınırını sadece 2 dakika ile aşsa bile, mevcut sistem \"Bu küme geçersiz\" diyerek K değerini (araç sayısını) +1 artırmakta ve K-Means'i baştan çalıştırmaktadır. Bu yaklaşım, küçük sapmalar için büyük maliyetli yeniden hesaplamalara neden olmaktadır.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-2", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Sistem sınır değerlerindeki sapmalara tolerans göstermediği (Re-insertion yapmadığı) için, kümeler \"beton gibi\" katıdır. Bu durum, optimize edilebilir öğrenci transferlerinin engellenmesine neden olmaktadır.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-2", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Bu durum, sırf 2 dakika aştı diye yeni bir araç açılmasına ve bu aracın içine o bölgeden sadece tek bir öğrencinin atanmasına (inefficient single-student routes) yol açmaktadır. Bu tür \"tek öğrencilik rotalar\", araç kullanım verimliliğini ciddi şekilde düşürmektedir.", font: "Times New Roman", size: 24 })] }),

        // Academic Research
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. Akademik Literatür Araştırması")] }),
        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.1 Büyük Ölçekli VRP Çözümleri (2023-2026)")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Son yıllarda yayınlanan akademik çalışmalarda, büyük ölçekli VRP problemleri için çeşitli yenilikçi yaklaşımlar önerilmiştir. 2024 yılında Transportation Research Part E dergisinde yayınlanan \"An efficient heuristic for very large-scale vehicle routing\" başlıklı çalışma (25 alıntı), N≥300 ölçeklerinde etkili sezgisel yöntemler sunmaktadır. Benzer şekilde, arXiv'de 2024'te yayınlanan çalışma, büyük ölçekli VRP örnekleri için ayrıştırma ve budama stratejileri kullanan meta-sezgisellerin başarısını ortaya koymaktadır.", font: "Times New Roman", size: 24 })]
        }),

        // PyVRP and HGS
        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.2 Hybrid Genetic Search (HGS) ve PyVRP")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "VRP literatüründe en önemli gelişmelerden biri, Hybrid Genetic Search (HGS) algoritmasının ortaya çıkışıdır. Thibaut Vidal tarafından geliştirilen HGS-CVRP algoritması, 2020 yılında yayınlanan ve 402'den fazla alıntı alan çalışmada detaylandırılmıştır. Bu algoritma, genetik algoritma ile yerel arama yöntemlerini (local search) birleştirerek üstün performans sağlamaktadır. 2023-2024 yıllarında yayınlanan \"PyVRP: A High-Performance VRP Solver Package\" başlıklı çalışma (108 alıntı), HGS algoritmasının Python'da yüksek performanslı bir implementasyonunu sunmaktadır.", font: "Times New Roman", size: 24 })]
        }),

        new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("HGS'nin Temel Avantajları")] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "SWAP* hareketlerinin verimli keşfi ile yerel arama performansının önemli ölçüde artırılması", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Çeşitli VRP varyantlarını (CVRP, VRPTW, VRPB vb.) tek bir çerçevede ele alma yeteneği", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Büyük ölçekli problemler (N≥1000) için bile hızlı ve kaliteli çözümler üretebilme", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Asimetrik mesafe matrislerini doğrudan işleyebilme (UniRide için kritik)", font: "Times New Roman", size: 24 })] }),

        // Clarke-Wright
        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.3 Clarke-Wright Savings Algoritması")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Clarke-Wright (CW) savings algoritması, 1964'ten bu yana VRP çözümlerinde yaygın olarak kullanılan klasik bir yöntemdir. 2024 yılında yayınlanan \"Modification of the Clarke and Wright Algorithm\" başlıklı çalışma ve 2025'teki \"A Fast Savings Algorithm for Solving Large-Scale\" çalışması, bu algoritmanın modern adaptasyonlarını sunmaktadır. Algoritmanın temel mantığı, \"Bu iki öğrenci aynı araca binerse toplam süreden ne kadar tasarruf ederiz?\" sorusuna dayanan savings matrix oluşturmaktır.", font: "Times New Roman", size: 24 })]
        }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Ancak, CW algoritması N=300 ölçeğinde bazı sınırlamalar göstermektedir. Öncelikle, algoritma kapasite kısıtlarını ancak tur oluşturma aşamasında kontrol etmektedir, bu da kırılım noktası tespit edildiğinde yeniden düzenleme gerektirmektedir. İkinci olarak, heterojen kapasite (Sw/So) kısıtlarını doğrudan ele almak için ek modifikasyonlar gerekmektedir.", font: "Times New Roman", size: 24 })]
        }),

        // OR-Tools
        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.4 Google OR-Tools VRP")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Google OR-Tools, endüstri standardı bir VRP çözücüsü olup Guided Local Search (GLS) meta-sezgiselini kullanmaktadır. Ancak, OR Stack Exchange'deki tartışmalara göre, 4000 düğümlü klasik bir VRP'nin 10 saniyede çözülmesi beklenmemektedir. N=300 için ise OR-Tools, 10-30 saniye gibi makul sürelerde iyi kalitede çözümler üretebilmektedir. OR-Tools'un temel gücü, C/C++ tabanlı implementasyonu ile yüksek performans sunması ve çeşitli kısıtları (kapasite, zaman penceresi, pickup-delivery) doğrudan modelleyebilmesidir.", font: "Times New Roman", size: 24 })]
        }),

        // Strategy Comparison Table
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. Strateji Karşılaştırması")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Aşağıdaki tablo, değerlendirilen üç alternatif stratejinin karşılaştırmalı analizini sunmaktadır:", font: "Times New Roman", size: 24 })]
        }),
        
        new Table({
          columnWidths: [2340, 2340, 2340, 2340],
          margins: { top: 100, bottom: 100, left: 180, right: 180 },
          rows: [
            new TableRow({
              tableHeader: true,
              children: [
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Kriter", bold: true, size: 22 })] })] }),
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Clarke-Wright", bold: true, size: 22 })] })] }),
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Re-Insertion", bold: true, size: 22 })] })] }),
                new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "PyVRP/HGS", bold: true, size: 22 })] })] })
              ]
            }),
            new TableRow({
              children: [
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "N=300 Performansı", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Orta", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "İyi", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Mükemmel", size: 22 })] })] })
              ]
            }),
            new TableRow({
              children: [
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Implementasyon Zorluğu", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Düşük", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Yüksek", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Düşük (pip install)", size: 22 })] })] })
              ]
            }),
            new TableRow({
              children: [
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Akademik Destek", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Geleneksel", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Sınırlı", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "402+ alıntı", size: 22 })] })] })
              ]
            }),
            new TableRow({
              children: [
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Heterojen Kapasite", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Modifikasyon gerekli", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Destekleniyor", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Doğal destek", size: 22 })] })] })
              ]
            }),
            new TableRow({
              children: [
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Asimetrik Matris", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Destekleniyor", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Destekleniyor", size: 22 })] })] }),
                new TableCell({ borders: cellBorders, children: [new Paragraph({ children: [new TextRun({ text: "Doğal destek", size: 22 })] })] })
              ]
            })
          ]
        }),
        new Paragraph({ 
          alignment: AlignmentType.CENTER,
          spacing: { before: 100 },
          children: [new TextRun({ text: "Tablo 1: Strateji Karşılaştırma Matrisi", size: 18, italics: true, color: colors.secondary })]
        }),

        // Recommendations
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. Çözüm Önerileri")] }),
        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.1 Birincil Öneri: PyVRP (HGS) Entegrasyonu")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Akademik araştırma bulguları ve karşılaştırmalı analiz sonucunda, UniRide projesi için birincil önerimiz PyVRP kütüphanesinin entegrasyonudur. Bu önerinin temel gerekçeleri şunlardır:", font: "Times New Roman", size: 24 })]
        }),
        new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Akademik Doğrulama: 402+ alıntı ile kanıtlanmış performans ve güvenilirlik. HGS algoritması, CVRP ve VRPTW için en başarılı meta-sezgisel yaklaşım olarak kabul edilmektedir.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Heterojen Kapasite Desteği: PyVRP, çok boyutlu kapasite kısıtlarını doğal olarak desteklemektedir. Bu, Sw (tekerlekli sandalye) ve So (normal koltuk) için ayrı kapasitelerin modellenmesini kolaylaştırmaktadır.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Asimetrik Matris Desteği: HGS-CVRP, asimetrik mesafe/süre matrislerini doğrudan işleyebilmektedir. Bu, gerçek dünya trafik verilerinin kullanımı için kritik öneme sahiptir.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Kümeleme Gereksinimini Ortadan Kaldırma: PyVRP, N=300 ölçeğinde \"Divide and Conquer\" mimarisine ihtiyaç duymadan doğrudan çözüm üretebilmektedir. Bu, katı kümeleme sorunlarını kökten çözmektedir.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Kolay Entegrasyon: pip install pyvrp ile kurulum ve Python API ile kolay entegrasyon imkanı sunmaktadır.", font: "Times New Roman", size: 24 })] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.2 İkincil Öneri: Re-Insertion Mekanizması")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Eğer mevcut GA/PSO altyapısı korunmak isteniyorsa, Re-Insertion ve Penalty Systems mekanizmasının eklenmesi önerilmektedir. Bu yaklaşım, mevcut \"Cluster-First\" yapısını korurken kümeleme katılığını azaltacaktır. Önerilen mekanizma şöyle çalışmaktadır:", font: "Times New Roman", size: 24 })]
        }),
        new Paragraph({ numbering: { reference: "numbered-4", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "GA/PSO rotalama sırasında kısıtı aşan en uçtaki gen (outlier node) tespit edilir. Bu tespit, rota süresinin Tmax'ı ne kadar aştığına göre yapılır.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-4", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Aşan düğüm, ceza fonksiyonu ile işaretlenir ve gen havuzundan çıkarılır. Ceza fonksiyonu, kısıt ihlalinin büyüklüğüne göre dinamik olarak ayarlanır.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-4", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Düğüm, komşu kümeye \"genetik göç\" (Genetic Migration) ile aktarılır. Bu aktarım, coğrafi yakınlık ve kapasite uygunluğu kriterlerine göre yapılır.", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "numbered-4", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Komşu küme, yeni düğümü entegre etmek için yerel optimizasyon yapar. Bu, küçük bir TSP problemi olarak ele alınabilir.", font: "Times New Roman", size: 24 })] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.3 Üçüncül Öneri: OR-Tools Optimizasyonu")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Mevcut OR-Tools entegrasyonu optimize edilerek kullanılabilir. Mevcut koddaki time_limit = 30 saniye ayarı, N=300 için makuldür. Ancak, first_solution_strategy ve local_search_metaheuristic parametrelerinin optimize edilmesi gerekmektedir. Önerilen ayarlar: PATH_CHEAPEST_ARC başlangıç stratejisi ve GUIDED_LOCAL_SEARCH meta-sezgiseli. Bu kombinasyon, OR-Tools'un yerel arama yeteneklerini en üst düzeye çıkarmaktadır.", font: "Times New Roman", size: 24 })]
        }),

        // Implementation Roadmap
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("6. Implementasyon Yol Haritası")] }),
        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.1 Kısa Vadeli (1-2 Hafta)")] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "PyVRP kütüphanesinin kurulumu ve temel entegrasyonu (pip install pyvrp)", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Mevcut time_matrix ve student verilerinin PyVRP formatına dönüştürülmesi", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Heterojen kapasite (Sw/So) kısıtlarının PyVRP'de modellenmesi", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Basit bir karşılaştırma testi: PyVRP vs mevcut GA (N=30 ile)", font: "Times New Roman", size: 24 })] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.2 Orta Vadeli (3-4 Hafta)")] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "PyVRP'nin optimizer_api'ye strateji olarak entegrasyonu", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Frontend'de PyVRP seçeneğinin eklenmesi (algorithm-constants.ts güncellemesi)", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "N=100, N=200, N=300 ölçeklerinde performans testleri", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Sonuçların karşılaştırmalı raporlanması ve görselleştirilmesi", font: "Times New Roman", size: 24 })] }),

        new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.3 Uzun Vadeli (5-8 Hafta)")] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Kümeleme katmanının tamamen kaldırılması veya opsiyonel hale getirilmesi", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Dinamik yeniden planlama (real-time re-routing) yeteneklerinin eklenmesi", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "PyVRP VRPTW (zaman pencereli) varyantına geçiş", font: "Times New Roman", size: 24 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Öğrenci onay/iptal mekanizmasının optimizasyon ile entegrasyonu", font: "Times New Roman", size: 24 })] }),

        // Conclusion
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("7. Sonuç")] }),
        new Paragraph({ 
          spacing: { line: 250 },
          children: [new TextRun({ text: "Bu rapor kapsamında, UniRide projesinin CVRPTW probleminde karşılaşılan ölçeklenebilirlik sorunları analiz edilmiş ve güncel akademik literatür ışığında çözüm önerileri sunulmuştur. Araştırma bulguları, Hybrid Genetic Search (HGS) algoritmasının ve PyVRP kütüphanesinin bu problem için en uygun çözüm olduğunu açıkça ortaya koymaktadır. PyVRP entegrasyonu, hem mevcut katı kümeleme sorunlarını kökten çözecek hem de N≥300 ölçeklerinde yüksek performans sağlayacaktır. Önerilen implementasyon yol haritasının takip edilmesi, projenin ölçeklenebilirlik hedeflerine ulaşmasını sağlayacaktır.", font: "Times New Roman", size: 24 })]
        }),

        // References
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("8. Kaynaklar")] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Vidal, T. (2020). Hybrid Genetic Search for the CVRP. Transportation Science.", font: "Times New Roman", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Wouda, N.A., Lan, L., Wiering, M.A. (2024). PyVRP: A High-Performance VRP Solver Package. INFORMS Journal on Computing.", font: "Times New Roman", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Chen, L. et al. (2024). An efficient heuristic for very large-scale vehicle routing. Transportation Research Part E.", font: "Times New Roman", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Kool, W. et al. (2022). Hybrid Genetic Search for the Vehicle Routing Problem with Time Windows.", font: "Times New Roman", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Google OR-Tools Documentation. (2024). Vehicle Routing Problem Guide.", font: "Times New Roman", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "PyVRP Documentation. (2024). https://pyvrp.org/", font: "Times New Roman", size: 22 })] }),
        new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "HGS-CVRP GitHub Repository. https://github.com/vidalt/HGS-CVRP", font: "Times New Roman", size: 22 })] })
      ]
    }
  ]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/home/z/my-project/download/CVRPTW_Analiz_ve_Cozum_Onerileri.docx", buffer);
  console.log("Document created successfully!");
});
