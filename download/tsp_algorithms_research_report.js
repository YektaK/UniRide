const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, 
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType, 
        ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat } = require('docx');
const fs = require('fs');

// Color scheme - Academic style
const colors = {
  primary: "1A365D",      // Deep navy blue
  secondary: "2D3748",    // Dark gray
  accent: "4A5568",       // Medium gray
  tableBg: "F7FAFC",      // Light blue-gray
  tableHeader: "E2E8F0"   // Slightly darker
};

// Table border style
const tableBorder = { style: BorderStyle.SINGLE, size: 8, color: "CBD5E0" };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Times New Roman", size: 24 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 48, bold: true, color: colors.primary, font: "Times New Roman" },
        paragraph: { spacing: { before: 200, after: 200 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: colors.primary, font: "Times New Roman" },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: colors.secondary, font: "Times New Roman" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: colors.accent, font: "Times New Roman" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } }
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
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
    ]
  },
  sections: [{
    properties: {
      page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({ 
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "TSP Optimizasyon Algoritmaları Araştırma Raporu", italics: true, size: 20, color: colors.accent })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ 
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Sayfa ", size: 20 }), new TextRun({ children: [PageNumber.CURRENT], size: 20 }), new TextRun({ text: " / ", size: 20 }), new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 20 })]
      })] })
    },
    children: [
      // Title
      new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("TSP ve CVRP İçin Modern Optimizasyon Algoritmaları")] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
        children: [new TextRun({ text: "Bilimsel Makale Yazımı İçin Araştırma Raporu", size: 22, italics: true, color: colors.secondary })] }),
      
      // Introduction
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. Giriş")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Gezgin Satıcı Problemi (Traveling Salesman Problem - TSP) ve Kapasiteli Araç Rotalama Problemi (Capacitated Vehicle Routing Problem - CVRP), kombinatoryal optimizasyon alanının en zorlu NP-zor problemleri arasında yer almaktadır. Bu problemler, lojistik, ulaşım, üretim planlama ve birçok endüstriyel alanda kritik öneme sahiptir. Son yıllarda, bu problemlerin çözümü için çok sayıda yeni meta-sezgisel algoritma önerilmiş ve mevcut algoritmalar geliştirilmiştir. Bu rapor, bilimsel bir makale yazımı için uygun olan, son yıllarda popülerleşen ve literatürde geniş kabul gören algoritmaları sistematik bir şekilde incelemektedir.")] }),
      
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Araştırmamız kapsamında, mevcut projede kullanılan Genetik Algoritma (GA) ve Parçacık Sürü Optimizasyonu (PSO) algoritmalarına ek olarak, literatürde öne çıkan diğer algoritmalar detaylı olarak incelenmiştir. Her algoritmanın çalışma prensibi, TSP/CVRP problemlerine uygulanabilirliği, avantajları, dezavantajları ve bilimsel makale yazımı için uygunluğu değerlendirilmiştir. Özellikle, Nature dergisi ve IEEE gibi prestijli yayınevlerinde son yıllarda yayımlanan çalışmalar referans alınmıştır.")] }),

      // Section 2 - Classic Algorithms
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. Klasik ve Kanıtlanmış Algoritmalar")] }),
      
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.1 Lin-Kernighan-Helsgaun (LKH)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Lin-Kernighan-Helsgaun (LKH) algoritması, TSP çözümünde \"altın standart\" olarak kabul edilmektedir. Keld Helsgaun tarafından geliştirilen bu algoritma, klasik Lin-Kernighan sezgisel yönteminin geliştirilmiş bir versiyonudur. 2024 yılındaki güncellemelerle, büyük ölçekli TSP örnekleri için ortalama %13 daha hızlı çözüm üretebilmektedir. LKH, özellikle 10.000'den fazla şehir içeren büyük örneklerde optimal veya optimala çok yakın sonuçlar vermektedir.")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Algoritmanın temel çalışma prensibi, k-opt yerel arama hareketlerinin dinamik olarak belirlenmesi ve karmaşık takas işlemlerinin gerçekleştirilmesidir. LKH'nin en önemli özelliği, arama sürecinde kaçak (escape) mekanizmaları kullanarak yerel optimumlardan kurtulabilmesidir. Bilimsel makale çalışmalarında, LKH genellikle karşılaştırma基准 (benchmark) olarak kullanılmakta ve önerilen yeni algoritmalar LKH'ya karşı test edilmektedir.")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "Makale Önerisi: ", bold: true }), new TextRun("LKH ile diğer meta-sezgisel algoritmaların hibrit kullanımı, novel bir araştırma konusu olabilir.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.2 Concorde TSP Solver")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Concorde, simetrik TSP için geliştirilmiş en gelişmiş kesin çözüm alıcısıdır. Branch-and-Bound ve probleme özgü kesme düzlemi yöntemleri üzerine kuruludur. Applegate, Bixby ve Chvatal tarafından geliştirilen Concorde, on binlerce şehir içeren TSP örneklerini optimal olarak çözebilmektedir. 2022-2024 yılları arasında yapılan çalışmalar, Concorde'un başlangıç çözümlerinin Partition Crossover ile iyileştirilmesiyle önemli hız kazanımları elde edildiğini göstermektedir.")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Concorde'un akademik kullanımı yaygındır ve TSPLIB benchmark kütüphanesindeki tüm örneklerin optimal çözümleri Concorde tarafından bulunmuştur. Ancak, Concorde kesin bir algoritma olduğu için çok büyük örneklerde hesaplama süresi katlanarak artmaktadır. Bu nedenle, pratik uygulamalarda genellikle LKH veya meta-sezgisel algoritmalar tercih edilmektedir.")] }),

      // Section 3 - Bio-inspired Algorithms
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. Biyolojik İlhamlı Modern Algoritmalar")] }),
      
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.1 Gri Kurt Optimizasyonu (Grey Wolf Optimizer - GWO)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Gri Kurt Optimizasyonu (GWO), 2014 yılında Mirjalili tarafından önerilen ve gri kurtların sosyal hiyerarşisi ve avlanma davranışlarından ilham alan bir meta-sezgisel algoritmadır. Algoritma, kurt sürüsünün alfa, beta, delta ve omega hiyerarşisini modelleyerek arama sürecini yönlendirir. Son yıllarda TSP ve CVRP problemlerine başarıyla uygulanmış ve literatürde geniş kabul görmüştür. 2024 yılında MDPI'da yayımlanan bir çalışma, GWO'nun çok amaçlı CVRP problemlerinde etkili olduğunu göstermektedir.")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("GWO'nun TSP'ye uygulanması için ayrık versiyonlar geliştirilmiştir. Bu versiyonlarda, kurtların konumları permütasyonlar olarak temsil edilir ve avlanma davranışı şehirler arası takas işlemleriyle gerçekleştirilir. Nature dergisinde 2024'te yayımlanan bir araştırma, GWO'nun Balina Optimizasyon Algoritması ile hibrit kullanımının (hGWOA) araç rotalama problemlerinde üstün performans gösterdiğini ortaya koymuştur. Bu çalışma 43 atıf alarak algoritmanın etkisini kanıtlamıştır.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.2 Harris Hawks Optimizasyonu (HHO)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Harris Hawks Optimizasyonu (HHO), Harris şahinlerinin avlanma davranışlarından ilham alan ve 2019 yılında önerilen güçlü bir meta-sezgisel algoritmadır. Algoritmanın en önemli özelliği, avın kaçış enerjisine göre uyarlanabilir avlanma stratejileri kullanmasıdır. 2022-2025 yılları arasında TSP ve VRP problemlerine uygulanmış ve IEEE, ACM gibi prestijli yayınevlerinde çok sayıda makale yayımlanmıştır.")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("2025 yılında Nature Scientific Reports'ta yayımlanan bir çalışma, HHO'nun kombine pertürbasyon stratejisiyle geliştirilmiş versiyonunun (HHO-CPS) TSP'de üstün performans gösterdiğini ortaya koymuştur. Bu çalışma, 9 atıf alarak güncel araştırmalarda algoritmanın önemini göstermektedir. Araştırmacılar, HHO'nun çeşitli kaçış enerjisi formülleri ve keşif-sömürü dengesi üzerinde yoğunlaşmışlardır.")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "Makale Önerisi: ", bold: true }), new TextRun("HHO'nun CVRP'deki kapasite kısıtlarına özel adaptasyonu novel bir katkı olabilir.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.3 Balina Optimizasyon Algoritması (Whale Optimization Algorithm - WOA)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Balina Optimizasyon Algoritması (WOA), kambur balinaların baloncuk avı tekniğinden ilham alan ve 2016 yılında önerilen popüler bir meta-sezgisel algoritmadır. Balinaların sarmal hareketleri ve baloncuk ağları oluşturarak avlanması, algoritmanın arama mekanizmasını oluşturur. WOA, sürekli optimizasyon problemlerinde başarılı olduğu gibi, TSP gibi ayrık problemlere de uyarlanmıştır.")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("2024 yılında Nature dergisinde yayımlanan ve 43 atıf alan bir çalışma, WOA ve GWO'nun hibrit kullanımının (hGWOA) araç rotalama problemlerinde çok etkili olduğunu göstermiştir. Bu hibrit yaklaşım, her iki algoritmanın güçlü yönlerini birleştirerek keşif ve sömürü dengesini optimize etmektedir. WOA'nın TSP'ye uygulanmasında, sarmal hareket şehir takasları olarak modellenir ve baloncuk ağları lokal arama olarak kullanılır.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.4 Afrika Akbabası Optimizasyonu (African Vultures Optimization Algorithm - AVOA)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Afrika Akbabası Optimizasyon Algoritması (AVOA), akbabaların beslenme ve uçuş davranışlarından ilham alan nispeten yeni bir meta-sezgisel algoritmadır. 2024-2025 yıllarında yapılan çalışmalar, AVOA'nın TSP ve VRP problemlerine başarıyla uygulanabileceğini göstermektedir. MDPI dergisinde 2024'te yayımlanan bir çalışma, iyileştirilmiş AVOA versiyonunun araç rotalama problemlerinde PSO ve geleneksel AVOA'dan daha iyi performans gösterdiğini ortaya koymuştur.")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("AVOA'nın en önemli özelliği, akbabaların açlık seviyesine göre farklı beslenme stratejileri kullanmasıdır. Bu özellik, algoritmanın arama sürecinde keşif ve sömürü arasında dinamik geçişler yapmasını sağlar. ResearchGate'de 2024'te yayımlanan bir derleme çalışması, AVOA'nın son uygulamalarını ve iyileştirmelerini kapsamlı olarak incelemiştir.")] }),

      // Section 4 - New Generation Algorithms
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. Yeni Nesil ve Az Bilinen Algoritmalar")] }),
      
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.1 Serçe Arama Algoritması (Sparrow Search Algorithm - SSA)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Serçe Arama Algoritması (SSA), serçelerin yiyecek arama ve kaçınma davranışlarından ilham alan 2020 yılında önerilen bir algoritmadır. ACM Digital Library'de 2024'te yayımlanan bir çalışma, SSA'nın Simüle Tavlama ve Tabu Arama ile karşılaştırılmasını yapmış ve TSP'de rekabetçi sonuçlar elde etmiştir. SSA'nın en önemli özelliği, üreticiler (producers) ve takipçiler (scroungers) arasındaki dinamik rol değişimidir.")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "Makale Önerisi: ", bold: true }), new TextRun("SSA'nın CVRP'deki kümelenmiş yapılarla etkileşimi araştırılabilir.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.2 Yapay Tavşan Optimizasyonu (Artificial Rabbits Optimization - ARO)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Yapay Tavşan Optimizasyonu (ARO), tavşanların kaçış ve gizlenme davranışlarından ilham alan yeni bir algoritmadır. Tavşanların yırtıcılardan kaçışı ve farklı sığınaklar kullanması, algoritmanın arama mekanizmasını oluşturur. ARO'nun TSP'ye uyarlanması için permütasyon tabanlı gösterimler ve ayrık operatörler geliştirilmiştir. Literatürde henüz TSP/CVRP uygulamaları sınırlı olduğundan, bu alanda novel katkı potansiyeli yüksektir.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.3 Orman Gazabı Optimizasyonu (Hunger Games Search - HGS)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Orman Gazabı Optimizasyonu (HGS), organizmaların açlık motivasyonuyla yiyecek arama davranışından ilham alan bir algoritmadır. Açlık seviyesi, bireylerin arama stratejilerini belirler ve aç bireyler daha agresif arama yapar. HGS, TSP gibi ayrık problemlere uyarlanabilir ve özellikle çok modlu (multimodal) arama uzaylarında etkilidir.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.4 Büyü Optimizasyonu (Growth Optimizer - GO)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Büyü Optimizasyonu (GO), organizmaların büyüme sürecinden ilham alan ve 2023 yılında önerilen bir algoritmadır. INASS dergisinde yayımlanan bir çalışma, GO'nun TSP'de başarıyla uygulandığını göstermektedir. GO'nun temel fikri, bireylerin büyüme ve gelişme süreçlerini modelleyerek optimizasyon yapmaktır. Bu algoritma, literatürde az bilinmektedir ve novel araştırma potansiyeli taşımaktadır.")] }),

      // Section 5 - Deep Learning Approaches
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. Derin Öğrenme ve Pekiştirmeli Öğrenme Yaklaşımları")] }),
      
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.1 Sinirsel Kombinatoryal Optimizasyon (Neural Combinatorial Optimization)")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Sinirsel Kombinatoryal Optimizasyon (NCO), derin öğrenme ve pekiştirmeli öğrenmeyi birleştirerek kombinatoryal optimizasyon problemlerini çözen modern bir yaklaşımdır. Google Research ve akademik laboratuvarlarda yoğun olarak araştırılmaktadır. 2024-2025 yıllarında yayımlanan çalışmalar, NCO'nun TSP'de传统 sezgisel yöntemlerle rekabetçi sonuçlar üretebildiğini göstermektedir. Springer'de yayımlanan bir derleme, DL tabanlı TSP algoritmalarını dört kategoriye ayırmıştır.")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("NCO'nun en büyük avantajı, bir kez eğitildikten sonra yeni problem örneklerinde çok hızlı çözüm üretebilmesidir. Ancak, eğitim süreci hesaplama açısından maliyetlidir ve algoritmanın genelleme yeteneği problem boyutuna bağlıdır. IEEE'de 2024'te yayımlanan bir çalışma, NCO'nun geleneksel sezgisel yöntemlerle hibrit kullanımını araştırmıştır.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.2 Difüzyon Modelleri ile Optimizasyon")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Difüzyon modelleri, son yıllarda görüntü üretiminde büyük başarı elde ettikten sonra, kombinatoryal optimizasyon alanına da uyarlanmıştır. LG AI Research, ICML 2024'te yayımlanan çalışmalarında difüzyon modellerinin TSP çözümünde nasıl kullanılabileceğini göstermiştir. Bu yaklaşım, çözüm uzayını aşamalı olarak gürültüden arındırarak optimal çözüme yaklaşır.")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "Makale Önerisi: ", bold: true }), new TextRun("Difüzyon modelleri ile meta-sezgisel algoritmaların karşılaştırması güncel ve novel bir konudur.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.3 Graph Neural Networks (GNN) ile TSP")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Grafik Sinir Ağları (GNN), TSP'nin grafik yapısını doğrudan modelleyebildiği için bu probleme çok uygundur. OpenReview'de yayımlanan bir çalışma, GNN gömülerini LKH ile birleştirerek güçlü bir yaklaşım önermektedir. Bu yaklaşım, grafik yapısını öğrenip ardından LKH'nın arama sürecini yönlendirmektedir. ArXiv'de 2024'te yayımlanan bir çalışma, GNN'nin farklı boyutlardaki TSP örneklerine genelleme yapabilmesini araştırmıştır.")] }),

      // Section 6 - Comparison Table
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("6. Algoritma Karşılaştırma Tablosu")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Aşağıdaki tablo, bilimsel makale yazımı için uygun olan algoritmaların kapsamlı bir karşılaştırmasını sunmaktadır. Tabloda her algoritmanın literatürdeki yeri, TSP/CVRP uygunluğu, makale potansiyeli ve önerilen kullanım alanları belirtilmiştir.")] }),

      // Comparison Table
      new Table({
        columnWidths: [2200, 2000, 1800, 1800, 2000],
        rows: [
          new TableRow({
            tableHeader: true,
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 2200, type: WidthType.DXA },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Algoritma", bold: true, size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 2000, type: WidthType.DXA },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Kategori", bold: true, size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 1800, type: WidthType.DXA },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "TSP/CVRP Uygunluğu", bold: true, size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 1800, type: WidthType.DXA },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Makale Potansiyeli", bold: true, size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 2000, type: WidthType.DXA },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Son Çalışma Yılı", bold: true, size: 22 })] })] })
            ]
          }),
          // LKH
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "LKH", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Klasik Sezgisel", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Çok Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Benchmark", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2024", size: 22 })] })] })
            ]
          }),
          // GWO
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "GWO (Gri Kurt)", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Biyolojik İlhamlı", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Çok Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2024", size: 22 })] })] })
            ]
          }),
          // HHO
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "HHO (Harris Hawks)", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Biyolojik İlhamlı", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Çok Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Çok Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2025", size: 22 })] })] })
            ]
          }),
          // WOA
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "WOA (Balina)", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Biyolojik İlhamlı", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Çok Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2024", size: 22 })] })] })
            ]
          }),
          // AVOA
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "AVOA (Akbaba)", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Biyolojik İlhamlı", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Orta-Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2024", size: 22 })] })] })
            ]
          }),
          // SSA
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "SSA (Serçe Arama)", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Biyolojik İlhamlı", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Orta", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2024", size: 22 })] })] })
            ]
          }),
          // ARO
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "ARO (Tavşan)", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Biyolojik İlhamlı", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Deneysel", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Çok Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2023-2024", size: 22 })] })] })
            ]
          }),
          // NCO
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "NCO (Sinirsel)", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Derin Öğrenme", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Orta-Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Çok Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, shading: { fill: colors.tableBg, type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2024-2025", size: 22 })] })] })
            ]
          }),
          // Diffusion
          new TableRow({
            children: [
              new TableCell({ borders: cellBorders, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Difüzyon Modelleri", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Derin Öğrenme", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Deneysel", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Çok Yüksek", size: 22 })] })] }),
              new TableCell({ borders: cellBorders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2024", size: 22 })] })] })
            ]
          })
        ]
      }),
      new Paragraph({ spacing: { before: 100, after: 300 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Tablo 1: TSP/CVRP için Algoritma Karşılaştırması", italics: true, size: 20 })] }),

      // Section 7 - Recommendations
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("7. Bilimsel Makale Önerileri ve Araştırma Yönleri")] }),
      
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.1 Yüksek Potansiyelli Araştırma Konuları")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Literatür taraması ve güncel yayın trendleri doğrultusunda, bilimsel indeksli makale yazımı için aşağıdaki konular önerilmektedir. Bu konular hem güncel literatüre katkı sağlayacak hem de original araştırma potansiyeli taşımaktadır. Özellikle hibrit yaklaşımlar ve az bilinen algoritmaların TSP/CVRP'ye uyarlanması, yüksek atıf potansiyeli olan çalışmalardır.")] }),
      
      new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "Hibrit GWO-WOA Yaklaşımı: ", bold: true }), new TextRun("Nature 2024'te yayımlanan çalışmanın devamı olarak, farklı problemlerde performans analizi ve parametre optimizasyonu araştırılabilir.")] }),
      new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "HHO ile CVRP: ", bold: true }), new TextRun("HHO'nun kapasite kısıtlarına özel adaptasyonu ve çok depolu VRP'ye genelleştirilmesi novel bir katkı olacaktır.")] }),
      new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "ARO/AVOA ile TSP: ", bold: true }), new TextRun("Az bilinen bu algoritmaların TSP'ye uyarlanması ve mevcut algoritmalarla karşılaştırılması yüksek novel değer taşır.")] }),
      new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "GNN-LKH Hibriti: ", bold: true }), new TextRun("Grafik sinir ağları ile LKH'nin birleştirilmesi, hem derin öğrenme hem de klasik optimizasyon literatürüne katkı sağlar.")] }),
      new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "Çok Amaçlı CVRP: ", bold: true }), new TextRun("Tek bir amaç fonksiyonu yerine, mesafe, zaman, yakıt tüketimi gibi birden fazla amaç fonksiyonunun optimize edilmesi.")] }),
      new Paragraph({ numbering: { reference: "numbered-list-1", level: 0 }, spacing: { after: 200, line: 360 },
        children: [new TextRun({ text: "Dinamik VRP: ", bold: true }), new TextRun("Zaman içinde değişen talepler ve trafik koşulları altında gerçek zamanlı rota optimizasyonu.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.2 Mevcut Proje ile Entegrasyon Önerileri")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Mevcut UniRide projesinde GA ve PSO algoritmaları zaten Python API'sinde implemente edilmiştir. Bilimsel makale yazımı için bu algoritmaların yanı sıra aşağıdaki eklemeler önerilmektedir:")] }),
      
      new Paragraph({ numbering: { reference: "numbered-list-2", level: 0 }, spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "GWO Implementasyonu: ", bold: true }), new TextRun("Gri Kurt Optimizasyonu, mevcut PSO ile benzer yapıda olup karşılaştırmalı analiz için idealdir.")] }),
      new Paragraph({ numbering: { reference: "numbered-list-2", level: 0 }, spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "HHO Implementasyonu: ", bold: true }), new TextRun("Harris Hawks, dinamik keşif-sömürü mekanizması ile farklı performans karakteristikleri gösterecektir.")] }),
      new Paragraph({ numbering: { reference: "numbered-list-2", level: 0 }, spacing: { after: 100, line: 360 },
        children: [new TextRun({ text: "LKH Entegrasyonu: ", bold: true }), new TextRun("Benchmark amaçlı LKH implementasyonu veya mevcut LKH kütüphanesinin Python binding'i.")] }),
      new Paragraph({ numbering: { reference: "numbered-list-2", level: 0 }, spacing: { after: 200, line: 360 },
        children: [new TextRun({ text: "Otomatik Karşılaştırma Sistemi: ", bold: true }), new TextRun("Tüm algoritmaların otomatik olarak çalıştırılıp sonuçların istatistiksel analizi.")] }),

      // Section 8 - Conclusion
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("8. Sonuç ve Değerlendirme")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Bu araştırma raporu, TSP ve CVRP optimizasyonu için kullanılabilecek modern algoritmaları sistematik bir şekilde incelemiştir. Literatür taraması sonucunda, Gri Kurt Optimizasyonu (GWO), Harris Hawks Optimizasyonu (HHO) ve Balina Optimizasyon Algoritması (WOA) gibi biyolojik ilhamlı algoritmaların son yıllarda en popüler ve en çok atıf alan yaklaşımlar olduğu tespit edilmiştir. Bu algoritmalar, Nature, IEEE ve ACM gibi prestijli yayınevlerinde yayımlanan çalışmalarda başarıyla uygulanmıştır.")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Bilimsel makale yazımı için en uygun algoritmalar, hem literatürde kabul görmüş hem de novel katkı potansiyeli taşıyan algoritmalardır. Bu bağlamda, HHO ve GWO yüksek potansiyelli algoritmalar olarak öne çıkmaktadır. Ayrıca, ARO ve AVOA gibi az bilinen algoritmaların TSP/CVRP'ye uyarlanması, orijinal katkı potansiyeli açısından çok değerlidir. Derin öğrenme tabanlı yaklaşımlar (NCO, Difüzyon Modelleri, GNN) ise en güncel ve en çok ilgi gören araştırma alanlarıdır.")] }),
      new Paragraph({ spacing: { after: 200, line: 360 },
        children: [new TextRun("Mevcut projede GA ve PSO algoritmaları bulunduğundan, bilimsel makale için bu algoritmaların yanı sıra GWO ve HHO implementasyonları önerilmektedir. Bu dört algoritmanın (GA, PSO, GWO, HHO) karşılaştırmalı analizi, hem bilimsel katkı sağlayacak hem de projenin teknik derinliğini artıracaktır. Benchmark olarak LKH kullanılması, sonuçların güvenilirliğini ve karşılaştırılabilirliğini artıracaktır.")] }),

      // References
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Kaynaklar")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[1] Nature Scientific Reports (2024). \"Hybrid whale optimization algorithm for enhanced routing.\" DOI: 10.1038/s41598-024-51359-2")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[2] Nature Scientific Reports (2025). \"Harris Hawk optimization algorithm with combined perturbation strategy.\" DOI: 10.1038/s41598-025-04705-x")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[3] IEEE Access (2024). \"A Deep Reinforcement Learning Assisted Heuristic for Solving TSP.\"")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[4] ACM Digital Library (2024). \"Metaheuristic Approach for Solving the Traveling Salesman Problem.\" DOI: 10.1145/3638209.3638217")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[5] MDPI Processes (2024). \"Improved African Vulture Optimization Algorithm.\" DOI: 10.3390/pr13071956")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[6] ArXiv (2024). \"A Speed-up for Helsgaun's TSP Heuristic.\" arXiv:2401.16149")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[7] Springer (2024). \"A survey on deep learning-based algorithms for the traveling salesman problem.\" DOI: 10.1007/s11704-024-40490-y")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[8] Zenodo (2025). \"Travelling Salesman Problem (TSP): Algorithms and Approaches.\"")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[9] Science Direct (2024). \"A comprehensive survey on the generalized traveling salesman problem.\" DOI: 10.1016/j.ejor.2023.110908")] }),
      new Paragraph({ spacing: { after: 100, line: 360 },
        children: [new TextRun("[10] INASS Journal (2024). \"A New Method for TSP Relied on Growth Optimization Algorithm.\"")] })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('/home/z/my-project/download/TSP_CVRP_Optimizasyon_Algoritmalari_Arastirma_Raporu.docx', buffer);
  console.log('Document created successfully!');
});
