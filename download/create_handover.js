const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header, Footer, 
        AlignmentType, PageOrientation, LevelFormat, HeadingLevel, BorderStyle, WidthType, 
        ShadingType, VerticalAlign, PageNumber, PageBreak, TableOfContents } = require('docx');
const fs = require('fs');

// Color scheme - "Midnight Code" for tech documentation
const colors = {
    primary: "020617",      // Midnight Black - Titles
    body: "1E293B",         // Deep Slate Blue - Body
    secondary: "64748B",    // Cool Blue-Gray - Subtitles
    accent: "94A3B8",       // Steady Silver - Accent
    tableBg: "F8FAFC",      // Glacial Blue-White - Table Background
    tableHeader: "E2E8F0"   // Light gray for table headers
};

// Table border style
const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: colors.secondary };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

// Create document
const doc = new Document({
    styles: {
        default: { document: { run: { font: "Calibri", size: 22 } } },
        paragraphStyles: [
            { id: "Title", name: "Title", basedOn: "Normal",
                run: { size: 56, bold: true, color: colors.primary, font: "Times New Roman" },
                paragraph: { spacing: { before: 0, after: 240 }, alignment: AlignmentType.CENTER } },
            { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
                run: { size: 32, bold: true, color: colors.primary, font: "Times New Roman" },
                paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 } },
            { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
                run: { size: 26, bold: true, color: colors.secondary, font: "Times New Roman" },
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
            { reference: "numbered-backend",
                levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
            { reference: "numbered-frontend",
                levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
            { reference: "numbered-api",
                levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
            { reference: "numbered-steps",
                levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
        ]
    },
    sections: [
        // Cover Page
        {
            properties: {
                page: { margin: { top: 0, right: 0, bottom: 0, left: 0 } }
            },
            children: [
                new Paragraph({ spacing: { before: 6000 } }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "UniRide CVRP Optimizasyon Sistemi", size: 72, bold: true, color: colors.primary, font: "Times New Roman" })]
                }),
                new Paragraph({ spacing: { before: 400 } }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "Developer Handover Dokümanı", size: 36, color: colors.secondary, font: "Times New Roman" })]
                }),
                new Paragraph({ spacing: { before: 800 } }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "Algoritma ve Local Search Güncellemeleri", size: 28, color: colors.body })]
                }),
                new Paragraph({ spacing: { before: 400 } }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "Versiyon 3.0.0", size: 24, color: colors.accent })]
                }),
                new Paragraph({ spacing: { before: 2000 } }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "Tarih: 24 Mart 2026", size: 22, color: colors.secondary })]
                }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "Hazırlayan: Z.ai Development Team", size: 22, color: colors.secondary })]
                })
            ]
        },
        // Main Content
        {
            properties: {
                page: { margin: { top: 1800, right: 1440, bottom: 1440, left: 1440 } }
            },
            headers: {
                default: new Header({ children: [new Paragraph({
                    alignment: AlignmentType.RIGHT,
                    children: [new TextRun({ text: "UniRide Handover Dokümanı", size: 18, color: colors.secondary })]
                })] })
            },
            footers: {
                default: new Footer({ children: [new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "— ", color: colors.accent }), new TextRun({ children: [PageNumber.CURRENT], color: colors.accent }), new TextRun({ text: " —", color: colors.accent })]
                })] })
            },
            children: [
                // TOC
                new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("İçindekiler")] }),
                new TableOfContents("İçindekiler", { hyperlink: true, headingStyleRange: "1-3" }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    spacing: { before: 200, after: 400 },
                    children: [new TextRun({ text: "Not: İçindekiler alan kodları ile oluşturulmuştur. Sayfa numaralarını güncellemek için sağ tıklayıp \"Alanı Güncelle\" seçeneğini kullanın.", size: 18, color: "999999" })]
                }),
                new Paragraph({ children: [new PageBreak()] }),

                // 1. Özet
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. Özet")] }),
                new Paragraph({
                    spacing: { after: 200, line: 250 },
                    children: [new TextRun({ text: "Bu doküman, UniRide CVRP (Capacitated Vehicle Routing Problem) optimizasyon sisteminde yapılan önemli güncellemeleri belgelemektedir. Güncellemeler, backend (Python) ve frontend (TypeScript/React) katmanlarını kapsamakta olup, sistemin algoritma seçeneklerini genişletmekte ve kod kalitesini artırmaktadır.", color: colors.body })]
                }),
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.1 Yapılan Değişiklikler")] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "GWO (Grey Wolf Optimizer) algoritması eklendi", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "HHO (Harris Hawks Optimization) algoritması eklendi", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Two-Opt standalone stratejisi eklendi", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Local Search Type parametresi tüm meta-sezgisel algoritmalara eklendi (2-opt, 3-opt, Or-opt, Hybrid)", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "2-opt kod tekrarı merkezi local_search modülüne taşındı", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Frontend UI güncellendi: Yerel Arama dropdown'ı eklendi", color: colors.body })] }),

                // 2. Backend Değişiklikleri
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. Backend Değişiklikleri (Python)")] }),
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.1 Yeni Dosyalar")] }),
                
                // Backend files table
                new Table({
                    columnWidths: [3500, 5860],
                    margins: { top: 100, bottom: 100, left: 180, right: 180 },
                    rows: [
                        new TableRow({
                            tableHeader: true,
                            children: [
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 3500, type: WidthType.DXA },
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Dosya Yolu", bold: true, size: 22 })] })] }),
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 5860, type: WidthType.DXA },
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Açıklama", bold: true, size: 22 })] })] })
                            ]
                        }),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, width: { size: 3500, type: WidthType.DXA },
                                children: [new Paragraph({ children: [new TextRun({ text: "utils/local_search.py", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, width: { size: 5860, type: WidthType.DXA },
                                children: [new Paragraph({ children: [new TextRun({ text: "Merkezi local search modülü (2-opt, 3-opt, Or-opt, Hybrid)", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, width: { size: 3500, type: WidthType.DXA },
                                children: [new Paragraph({ children: [new TextRun({ text: "strategies/gwo_strategy.py", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, width: { size: 5860, type: WidthType.DXA },
                                children: [new Paragraph({ children: [new TextRun({ text: "Grey Wolf Optimizer implementasyonu", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, width: { size: 3500, type: WidthType.DXA },
                                children: [new Paragraph({ children: [new TextRun({ text: "strategies/hho_strategy.py", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, width: { size: 5860, type: WidthType.DXA },
                                children: [new Paragraph({ children: [new TextRun({ text: "Harris Hawks Optimization implementasyonu", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, width: { size: 3500, type: WidthType.DXA },
                                children: [new Paragraph({ children: [new TextRun({ text: "strategies/two_opt_strategy.py", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, width: { size: 5860, type: WidthType.DXA },
                                children: [new Paragraph({ children: [new TextRun({ text: "Standalone Two-Opt stratejisi (multi-start desteği)", size: 20 })] })] })
                        ]})
                    ]
                }),
                new Paragraph({ spacing: { after: 200 } }),

                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.2 Güncellenen Dosyalar")] }),
                new Paragraph({ numbering: { reference: "numbered-backend", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "strategies/__init__.py - STRATEGY_REGISTRY güncellendi, GWO, HHO ve Two-Opt eklendi", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-backend", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "strategies/ga_strategy.py - local_search_type parametresi eklendi, merkezi local_search modülü kullanımı", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-backend", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "strategies/pso_strategy.py - local_search_type parametresi eklendi, merkezi local_search modülü kullanımı", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-backend", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "models/schemas.py - LocalSearchType enum eklendi, GWO ve HHO config şemaları", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-backend", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "main.py - API v3.0.0, GWO/HHO endpoint'leri, compareAllAlgorithms güncellendi", color: colors.body })] }),

                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.3 Local Search Type Seçenekleri")] }),
                new Table({
                    columnWidths: [2000, 3500, 3860],
                    margins: { top: 100, bottom: 100, left: 180, right: 180 },
                    rows: [
                        new TableRow({
                            tableHeader: true,
                            children: [
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 2000, type: WidthType.DXA },
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Değer", bold: true, size: 22 })] })] }),
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 3500, type: WidthType.DXA },
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Görünen Ad", bold: true, size: 22 })] })] }),
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 3860, type: WidthType.DXA },
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Açıklama", bold: true, size: 22 })] })] })
                            ]
                        }),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "none", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Yok", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Yerel arama uygulanmaz", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "two_opt", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "2-Opt (Klasik)", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Kenar değiştirme ile iyileştirme", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "three_opt", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "3-Opt (Yüksek Kalite)", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "3 kenar değiştirme, daha kaliteli", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "or_opt", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Or-Opt (Kümeleme)", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Alt tur yeniden konumlandırma", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "hybrid", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Hibrit (Kombine)", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "2-opt + 3-opt + Or-opt kombine", size: 20 })] })] })
                        ]})
                    ]
                }),
                new Paragraph({ spacing: { after: 200 } }),

                // 3. Frontend Değişiklikleri
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. Frontend Değişiklikleri (TypeScript/React)")] }),
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.1 Güncellenen Dosyalar")] }),
                new Table({
                    columnWidths: [4500, 4860],
                    margins: { top: 100, bottom: 100, left: 180, right: 180 },
                    rows: [
                        new TableRow({
                            tableHeader: true,
                            children: [
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 4500, type: WidthType.DXA },
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Dosya Yolu", bold: true, size: 22 })] })] }),
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER, width: { size: 4860, type: WidthType.DXA },
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Değişiklik", bold: true, size: 22 })] })] })
                            ]
                        }),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "src/lib/algorithm-constants.ts", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Two-Opt algoritması, Local Search sabitleri, helper fonksiyonlar", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "src/services/vehicle-calculator.ts", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "local_search_type parametresi eklendi", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "src/app/api/calculate-vehicles/route.ts", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "local_search_type parametresi, default genetic_algorithm", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "src/app/(app)/admin/route-test/page.tsx", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Yerel Arama dropdown'ı eklendi", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "src/app/(app)/admin/vehicle-planning/page.tsx", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Yerel Arama dropdown'ı eklendi", size: 20 })] })] })
                        ]})
                    ]
                }),
                new Paragraph({ spacing: { after: 200 } }),

                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.2 algorithm-constants.ts Yeni Fonksiyonlar")] }),
                new Paragraph({ numbering: { reference: "numbered-frontend", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "algorithmSupportsLocalSearch(algorithm) - Algoritmanın local search destekleyip desteklemediğini kontrol eder", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-frontend", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "getLocalSearchDisplayName(type) - Local search type için görünen ad döndürür", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-frontend", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "LOCAL_SEARCH_OPTIONS - UI dropdown için hazır options array", color: colors.body })] }),

                // 4. API Değişiklikleri
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. API Değişiklikleri")] }),
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.1 POST /api/v1/optimize")] }),
                new Paragraph({ spacing: { after: 200, line: 250 }, children: [new TextRun({ text: "Yeni opsiyonel parametreler:", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-api", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "local_search_type: \"none\" | \"two_opt\" | \"three_opt\" | \"or_opt\" | \"hybrid\"", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-api", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "gwo_config: { population_size, max_iterations, initial_a, exploration_rate, local_search_type }", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-api", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "hho_config: { population_size, max_iterations, initial_energy, jump_probability, local_search_type }", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-api", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "two_opt_config: { max_iterations, multi_start, num_starts }", color: colors.body })] }),

                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.2 Algoritma Destek Matrisi")] }),
                new Table({
                    columnWidths: [3000, 2000, 2500, 1860],
                    margins: { top: 100, bottom: 100, left: 180, right: 180 },
                    rows: [
                        new TableRow({
                            tableHeader: true,
                            children: [
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Algoritma", bold: true, size: 22 })] })] }),
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Önerilen", bold: true, size: 22 })] })] }),
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Local Search", bold: true, size: 22 })] })] }),
                                new TableCell({ borders: cellBorders, shading: { fill: colors.tableHeader, type: ShadingType.CLEAR }, verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Karmaşıklık", bold: true, size: 22 })] })] })
                            ]
                        }),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Genetik Algoritma (GA)", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "✓", size: 20, color: "22C55E" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "✓", size: 20, color: "22C55E" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "O(g×p×n²)", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "PSO", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "✓", size: 20, color: "22C55E" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "✓", size: 20, color: "22C55E" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "O(i×s×n²)", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Gri Kurt (GWO)", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "✓", size: 20, color: "22C55E" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "✓", size: 20, color: "22C55E" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "O(i×p×n²)", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Harris Hawks (HHO)", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "✓", size: 20, color: "22C55E" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "✓", size: 20, color: "22C55E" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "O(i×h×n²)", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Two-Opt Local Search", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "—", size: 20, color: "64748B" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "—", size: 20, color: "64748B" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "O(n²)", size: 20 })] })] })
                        ]}),
                        new TableRow({ children: [
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: "Greedy", size: 20 })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "—", size: 20, color: "64748B" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "—", size: 20, color: "64748B" })] })] }),
                            new TableCell({ borders: cellBorders, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "O(n²)", size: 20 })] })] })
                        ]})
                    ]
                }),
                new Paragraph({ spacing: { after: 200 } }),

                // 5. Kurulum ve Dağıtım
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. Kurulum ve Dağıtım")] }),
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.1 Backend Kurulumu")] }),
                new Paragraph({ numbering: { reference: "numbered-steps", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "optimizer_api/utils/local_search.py dosyasını oluşturun", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-steps", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "optimizer_api/strategies/ altına gwo_strategy.py, hho_strategy.py, two_opt_strategy.py ekleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-steps", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "strategies/__init__.py dosyasını güncelleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-steps", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "ga_strategy.py ve pso_strategy.py dosyalarını güncelleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-steps", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "models/schemas.py dosyasını güncelleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-steps", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "main.py dosyasını güncelleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "numbered-steps", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Python API'yi yeniden başlatın: uvicorn main:app --reload", color: colors.body })] }),

                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.2 Frontend Kurulumu")] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "src/lib/algorithm-constants.ts dosyasını güncelleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "src/services/vehicle-calculator.ts dosyasını güncelleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "src/app/api/calculate-vehicles/route.ts dosyasını güncelleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "src/app/(app)/admin/route-test/page.tsx dosyasını güncelleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "src/app/(app)/admin/vehicle-planning/page.tsx dosyasını güncelleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "npm run dev veya npm run build çalıştırın", color: colors.body })] }),

                // 6. Test ve Doğrulama
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("6. Test ve Doğrulama")] }),
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.1 Backend Testi")] }),
                new Paragraph({ spacing: { after: 200, line: 250 }, children: [new TextRun({ text: "Python API'yi test etmek için:", color: colors.body })] }),
                new Paragraph({ spacing: { line: 250 }, children: [new TextRun({ text: "# Health check\ncurl http://localhost:8000/health\n\n# GWO ile optimizasyon\ncurl -X POST http://localhost:8000/api/v1/optimize \\\n  -H \"Content-Type: application/json\" \\\n  -d '{\"algorithm\": \"gwo\", \"students\": [...], \"depot\": {...}}'\n\n# Algoritma karşılaştırma\ncurl -X POST http://localhost:8000/api/v1/compare \\\n  -H \"Content-Type: application/json\" \\\n  -d '{\"students\": [...], \"depot\": {...}}'", font: "Courier New", size: 18 })] }),

                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.2 Frontend Testi")] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "/admin/route-test sayfasına gidin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Algoritma dropdown'ından GWO veya HHO seçin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Yerel Arama dropdown'ından bir seçenek belirleyin", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Noktalar seçip \"Optimize Et\" butonuna tıklayın", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Sonuçların doğru döndüğünü doğrulayın", color: colors.body })] }),

                // 7. Sonraki Adımlar
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("7. Sonraki Adımlar ve Öneriler")] }),
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.1 Önerilen İyileştirmeler")] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Algoritma performans karşılaştırma dashboard'u eklenmesi", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Hyperparameter tuning için otomatik optimizasyon", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Sonuçların veritabanında saklanması ve geçmiş sorgulama", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Real-time optimizasyon ilerleme göstergesi (WebSocket)", color: colors.body })] }),

                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("7.2 Bilinen Sorunlar")] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "Permütasyon algoritması 10+ nokta için çok yavaş çalışıyor (UI'da uyarı var)", color: colors.body })] }),
                new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { line: 250 }, children: [new TextRun({ text: "OR-Tools CVRP ekstra bağımlılık gerektiriyor (google-ortools)", color: colors.body })] }),

                // 8. İletişim
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("8. İletişim ve Destek")] }),
                new Paragraph({ spacing: { line: 250 }, children: [new TextRun({ text: "Bu dokümantasyon ile ilgili sorularınız için Z.ai Development Team ile iletişime geçebilirsiniz. Teknik detaylar ve kod örnekleri için ilgili dosyalardaki yorum satırlarını inceleyebilirsiniz.", color: colors.body })] }),
                new Paragraph({ spacing: { before: 400 } }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "— Doküman Sonu —", size: 20, color: colors.accent })]
                })
            ]
        }
    ]
});

// Save document
Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("/home/z/my-project/download/UniRide_Handover_Dokumani.docx", buffer);
    console.log("Handover dokümanı oluşturuldu: /home/z/my-project/download/UniRide_Handover_Dokumani.docx");
});
