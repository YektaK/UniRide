#!/usr/bin/env node
// TSP Benchmark Studio — User Guide & Technical Documentation
// DM-1 (Deep Cyan) palette + R1 cover recipe

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, TableOfContents,
  HeadingLevel, BorderStyle, WidthType, ShadingType, VerticalAlign,
  PageBreak, PageNumber, SectionType, NumberFormat, TableLayoutType,
} = require("docx");

// ═══════════════════════════════════════════════════════════════════
// PALETTE — DM-1 (Deep Cyan)
// ═══════════════════════════════════════════════════════════════════
const P = {
  bg: "162235", primary: "FFFFFF", accent: "37DCF2",
  coverTitle: "FFFFFF", coverSubtitle: "B0B8C0", coverMeta: "90989F", coverFooter: "687078",
  body: "000000", secondary: "506070",
  tHeaderBg: "1B6B7A", tHeaderText: "FFFFFF", tAccentLine: "1B6B7A", tInnerLine: "C8DDE2", tSurface: "EDF3F5",
};

// ═══════════════════════════════════════════════════════════════════
// HELPERS
// ═════════════════════════.primary═════════════════════════════════════
const NB = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: NB, bottom: NB, left: NB, right: NB };
const allNoBorders = { top: NB, bottom: NB, left: NB, right: NB, insideHorizontal: NB, insideVertical: NB };

const FONT = "Calibri";
const BODY_SIZE = 22;   // 11pt
const H1_SIZE = 36;     // 18pt
const H2_SIZE = 28;     // 14pt
const H3_SIZE = 24;     // 12pt
const LINE_SPACING = 312;

function bodyPara(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: LINE_SPACING },
    alignment: AlignmentType.LEFT,
    ...opts,
    children: [new TextRun({ text, font: FONT, size: BODY_SIZE, color: P.body })],
  });
}

function bodyParaRuns(runs, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: LINE_SPACING },
    alignment: AlignmentType.LEFT,
    ...opts,
    children: runs,
  });
}

function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 600, after: 300, line: LINE_SPACING },
    children: [new TextRun({ text, font: FONT, size: H1_SIZE, bold: true, color: "1B6B7A" })],
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 400, after: 200, line: LINE_SPACING },
    children: [new TextRun({ text, font: FONT, size: H2_SIZE, bold: true, color: P.tAccentLine })],
  });
}

function heading3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 300, after: 150, line: LINE_SPACING },
    children: [new TextRun({ text, font: FONT, size: H3_SIZE, bold: true, color: P.secondary })],
  });
}

function bulletItem(text, ref = "bl") {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 60, line: LINE_SPACING },
    children: [new TextRun({ text, font: FONT, size: BODY_SIZE, color: P.body })],
  });
}

function bulletItemBold(boldText, normalText, ref = "bl") {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 60, line: LINE_SPACING },
    children: [
      new TextRun({ text: boldText, font: FONT, size: BODY_SIZE, bold: true, color: P.body }),
      new TextRun({ text: normalText, font: FONT, size: BODY_SIZE, color: P.body }),
    ],
  });
}

function numberedItem(text, ref) {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 60, line: LINE_SPACING },
    children: [new TextRun({ text, font: FONT, size: BODY_SIZE, color: P.body })],
  });
}

function numberedItemBold(boldText, normalText, ref) {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 60, line: LINE_SPACING },
    children: [
      new TextRun({ text: boldText, font: FONT, size: BODY_SIZE, bold: true, color: P.body }),
      new TextRun({ text: normalText, font: FONT, size: BODY_SIZE, color: P.body }),
    ],
  });
}

function codeBlock(lines) {
  return lines.map(line => new Paragraph({
    spacing: { after: 0, line: 260 },
    shading: { type: ShadingType.CLEAR, fill: "F5F5F5" },
    indent: { left: 360 },
    children: [new TextRun({ text: line, font: "Courier New", size: 18, color: "333333" })],
  }));
}

function spacer(h = 200) {
  return new Paragraph({ spacing: { before: h } });
}

function tableCaption(text) {
  return new Paragraph({
    spacing: { before: 60, after: 200, line: LINE_SPACING },
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text, font: FONT, size: 18, italics: true, color: P.secondary })],
  });
}

// ═══════════════════════════════════════════════════════════════════
// TABLE BUILDER — Horizontal-Only style with DM-1 colors
// ═══════════════════════════════════════════════════════════════════
function makeTable(headers, rows, colWidths) {
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => new TableCell({
      width: { size: colWidths[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: P.tHeaderBg },
      borders: {
        top: { style: BorderStyle.SINGLE, size: 2, color: P.tAccentLine },
        bottom: { style: BorderStyle.SINGLE, size: 2, color: P.tAccentLine },
        left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
      },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 40, after: 40 },
        children: [new TextRun({ text: h, font: FONT, size: 20, bold: true, color: P.tHeaderText })],
      })],
    })),
  });

  const dataRows = rows.map((row, rowIdx) => new TableRow({
    children: row.map((cell, i) => new TableCell({
      width: { size: colWidths[i], type: WidthType.DXA },
      shading: rowIdx % 2 === 0 ? { type: ShadingType.CLEAR, fill: P.tSurface } : undefined,
      borders: {
        top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.SINGLE, size: 1, color: P.tInnerLine },
        left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
      },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
        spacing: { before: 30, after: 30 },
        children: [new TextRun({ text: String(cell), font: FONT, size: 20, color: P.body })],
      })],
    })),
  }));

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: colWidths,
    rows: [headerRow, ...dataRows],
    margins: { top: 60, bottom: 60, left: 120, right: 120 },
  });
}

// ═══════════════════════════════════════════════════════════════════
// COVER — R1 Pure Paragraph Left with DM-1 palette
// ═══════════════════════════════════════════════════════════════════
function buildCover() {
  const title = "TSP Benchmark Studio";
  const subtitle = "User Guide & Technical Documentation";
  const version = "v1.2.0";
  const date = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const stackLine = "Next.js 16  |  React 19  |  TypeScript  |  Tailwind CSS 4  |  Recharts  |  Zustand";

  const padL = 1200, padR = 800;
  const accentLeft = { style: BorderStyle.SINGLE, size: 8, color: P.accent, space: 12 };
  const children = [];

  // Top whitespace
  children.push(new Paragraph({ spacing: { before: 4800 } }));

  // English label with accent bottom border
  children.push(new Paragraph({
    indent: { left: padL, right: padR }, spacing: { after: 500 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: P.accent, space: 8 } },
    children: [new TextRun({ text: "T S P   B E N C H M A R K   S T U D I O",
      size: 18, color: P.accent, font: FONT, characterSpacing: 40 })],
  }));

  // Main title
  children.push(new Paragraph({
    indent: { left: padL },
    spacing: { after: 300, line: Math.ceil(40 * 23), lineRule: "atLeast" },
    children: [new TextRun({ text: title, size: 80, bold: true, color: P.coverTitle, font: FONT })],
  }));

  // Subtitle
  children.push(new Paragraph({
    indent: { left: padL }, spacing: { after: 800 },
    children: [new TextRun({ text: subtitle, size: 26, color: P.coverSubtitle, font: FONT })],
  }));

  // Meta info lines with left accent
  const metaLines = [
    `Version ${version}`,
    date,
    stackLine,
  ];
  for (const line of metaLines) {
    children.push(new Paragraph({
      indent: { left: padL + 200 }, spacing: { after: 80 },
      border: { left: accentLeft },
      children: [new TextRun({ text: line, size: 22, color: P.coverMeta, font: FONT })],
    }));
  }

  // Bottom whitespace
  children.push(new Paragraph({ spacing: { before: 3200 } }));

  // Footer with top accent separator
  children.push(new Paragraph({
    indent: { left: padL, right: padR },
    border: { top: { style: BorderStyle.SINGLE, size: 2, color: P.accent, space: 8 } },
    spacing: { before: 200 },
    children: [
      new TextRun({ text: "TSP Benchmark Studio", size: 16, color: P.coverFooter, font: FONT }),
      new TextRun({ text: "                                                        ", size: 16 }),
      new TextRun({ text: "Academic Benchmark Platform", size: 16, color: P.coverFooter, font: FONT }),
    ],
  }));

  return [new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.FIXED,
    borders: allNoBorders,
    rows: [new TableRow({
      height: { value: 16838, rule: "exact" },
      children: [new TableCell({
        shading: { type: ShadingType.CLEAR, fill: P.bg },
        borders: noBorders,
        children,
      })],
    })],
  })];
}

// ═══════════════════════════════════════════════════════════════════
// NUMBERING CONFIG
// ═══════════════════════════════════════════════════════════════════
function buildNumberingConfig() {
  const bulletLevel = {
    level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 720, hanging: 360 } } },
  };
  const numLevel = {
    level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 720, hanging: 360 } } },
  };
  const configs = [
    { reference: "bl", levels: [bulletLevel] },
    { reference: "bl2", levels: [bulletLevel] },
    { reference: "bl3", levels: [bulletLevel] },
    { reference: "bl4", levels: [bulletLevel] },
    { reference: "bl5", levels: [bulletLevel] },
    { reference: "bl6", levels: [bulletLevel] },
    { reference: "bl7", levels: [bulletLevel] },
    { reference: "bl8", levels: [bulletLevel] },
    { reference: "bl9", levels: [bulletLevel] },
    { reference: "bl10", levels: [bulletLevel] },
    { reference: "bl11", levels: [bulletLevel] },
    { reference: "n1", levels: [numLevel] },
    { reference: "n2", levels: [numLevel] },
    { reference: "n3", levels: [numLevel] },
    { reference: "n4", levels: [numLevel] },
    { reference: "n5", levels: [numLevel] },
  ];
  return { config: configs };
}

// ═══════════════════════════════════════════════════════════════════
// CONTENT CHAPTERS
// ═══════════════════════════════════════════════════════════════════

// ── Chapter 1: Introduction ──
function ch1() {
  return [
    heading1("Chapter 1: Introduction"),
    heading2("1.1 What is TSP Benchmark Studio?"),
    bodyPara("TSP Benchmark Studio is an academic web-based platform designed for running, analyzing, and comparing Traveling Salesman Problem (TSP) algorithms at scale. Built on a modern technology stack, it provides a comprehensive suite of tools for researchers, students, and algorithm engineers to benchmark heuristic and meta-heuristic optimization algorithms against the well-known TSPLIB problem library."),
    bodyPara("The platform supports real-time experiment execution via Socket.io, offers rich interactive visualizations through Recharts, and provides robust data management with CSV/JSON/LaTeX export capabilities. The application ships with demo data so users can explore the interface immediately, and supports custom data loading for production research workflows."),

    heading2("1.2 Key Features"),
    bulletItemBold("Multi-Algorithm Support: ", "Nine TSP algorithms spanning local search (2-opt, 3-opt, Or-opt, Swap, Hybrid) and meta-heuristic (GA, PSO, GWO, HHO) categories.", "bl"),
    bulletItemBold("45 TSPLIB Problems: ", "Curated dataset of 17 small, 13 medium, and 15 large-scale problems with known optimal solutions.", "bl"),
    bulletItemBold("Real-Time Experiments: ", "Socket.io-powered benchmark runner service with live progress, ETA, and streaming results.", "bl"),
    bulletItemBold("Advanced Analytics: ", "Performance profiles, Friedman rankings, heatmaps, radar charts, box plots, and win-rate matrices.", "bl"),
    bulletItemBold("Dark/Light Themes: ", "Full theme support with system preference detection via next-themes.", "bl"),
    bulletItemBold("Data Portability: ", "Export results in CSV, JSON, and LaTeX table formats for direct use in papers.", "bl"),
    bulletItemBold("Configurable Parameters: ", "Fine-grained algorithm parameter control with preset configurations for quick experimentation.", "bl"),

    heading2("1.3 Target Audience"),
    bulletItemBold("Researchers: ", "Academic researchers studying combinatorial optimization, benchmarking new algorithm variants, or comparing performance across problem scales.", "bl2"),
    bulletItemBold("Students: ", "Graduate and undergraduate students learning about heuristic algorithms, with built-in demo data for immediate exploration.", "bl2"),
    bulletItemBold("Algorithm Engineers: ", "Practitioners developing or tuning optimization algorithms who need rigorous statistical comparison tools.", "bl2"),

    heading2("1.4 Technology Stack Summary"),
    makeTable(
      ["Layer", "Technology", "Version"],
      [
        ["Framework", "Next.js", "16"],
        ["UI Library", "React", "19"],
        ["Language", "TypeScript", "5"],
        ["Styling", "Tailwind CSS", "4"],
        ["UI Components", "shadcn/ui", "Latest"],
        ["Charts", "Recharts", "2.15"],
        ["State Management", "Zustand", "5"],
        ["Animations", "Framer Motion", "12"],
        ["Real-Time", "Socket.io", "4.8"],
        ["Database", "Prisma + SQLite", "6"],
        ["Runtime", "Bun", "Latest"],
      ],
      [3000, 3000, 3360]
    ),
    tableCaption("Table 1.1: Technology stack overview"),
  ];
}

// ── Chapter 2: Getting Started ──
function ch2() {
  return [
    heading1("Chapter 2: Getting Started"),
    heading2("2.1 System Requirements"),
    bulletItemBold("Node.js: ", "v18.0 or later (v24 recommended)", "bl"),
    bulletItemBold("Bun: ", "Latest stable release", "bl"),
    bulletItemBold("Git: ", "For cloning the repository", "bl"),
    bulletItemBold("Browser: ", "Chrome, Firefox, Edge, or Safari (latest two major versions)", "bl"),
    bulletItemBold("OS: ", "Windows 10+, macOS 12+, or Linux (kernel 5.x+)", "bl"),

    heading2("2.2 Installation Steps"),
    numberedItemBold("Clone the repository: ", "git clone https://github.com/your-org/tsp-benchmark-studio.git && cd tsp-benchmark-studio", "n1"),
    numberedItemBold("Install dependencies: ", "bun install", "n1"),
    numberedItemBold("Set up the database: ", "bun run db:push", "n1"),
    numberedItemBold("Start the development server: ", "bun run dev", "n1"),
    numberedItemBold("Start the benchmark runner service: ", "cd mini-services/benchmark-runner && bun run index.ts", "n1"),
    numberedItemBold("Open the application: ", "Navigate to http://localhost:3000 in your browser.", "n1"),

    heading2("2.3 Accessing the Application"),
    bodyPara("After starting the development server, the application is accessible at http://localhost:3000. The main interface features a sidebar navigation with four primary views: Dashboard, Experiment Designer (Deney Tasarimcisi), Results (Sonuclar), and Algorithms (Algoritmalar). The application loads with pre-generated demo data, allowing you to explore all features without running experiments."),
    bodyPara("To start the benchmark runner mini-service (required for live experiments), navigate to the mini-services/benchmark-runner directory and run the service on port 3003. The Next.js application communicates with this service via HTTP POST requests and Socket.io events."),

    heading2("2.4 First-Time Setup"),
    heading3("Using Demo Data"),
    bodyPara("The application ships with realistic demo data generated using a seeded random function. This includes benchmark results for all 5 ready algorithms across 10 small TSPLIB problems. The demo data is automatically loaded when the application starts, providing immediate access to charts, tables, and analytics without any configuration."),
    heading3("Loading Custom Data"),
    bodyPara("You can import your own benchmark results using CSV or JSON files. Navigate to the Results view and use the file upload buttons in the toolbar. The CSV format must include columns: problem, dimension, optimal, strategy, avg_gap, best_gap, avg_time_ms, avg_length, best_length, n_runs. The JSON format uses a nested structure with problem names as top-level keys and algorithm names as second-level keys."),
    heading3("Demo Data Regeneration"),
    bodyPara("To regenerate demo data, click the \"Regenerate Demo\" button in the Dashboard toolbar. This resets all results to the seeded demo set and clears any imported or experiment-generated data. This action cannot be undone."),
  ];
}

// ── Chapter 3: Dashboard ──
function ch3() {
  return [
    heading1("Chapter 3: Dashboard"),
    heading2("3.1 Overview"),
    bodyPara("The Dashboard is the primary landing view of TSP Benchmark Studio. It provides a high-level summary of all benchmark results, including key performance statistics, interactive charts, and comprehensive data tables. The dashboard is designed to give researchers an at-a-glance understanding of algorithm performance across the entire problem set."),
    bodyPara("At the top of the dashboard, four statistics cards display the most important metrics, followed by filter controls and a series of analytical visualizations. The dashboard automatically updates when new experiment results are merged from the Experiment Designer."),

    heading2("3.2 Statistics Cards"),
    makeTable(
      ["Card", "Description", "Calculation"],
      [
        ["Total Experiments", "Total number of algorithm-problem benchmark runs", "Count of all result rows"],
        ["Algorithms Tested", "Number of unique algorithms with results", "Distinct strategy values"],
        ["Avg GAP", "Average optimality gap across all results", "mean(avg_gap)"],
        ["Best Algorithm", "Algorithm with lowest average GAP", "min(mean avg_gap per algo)"],
      ],
      [2400, 3600, 3360]
    ),
    tableCaption("Table 3.1: Dashboard statistics cards"),

    heading2("3.3 Filter Controls"),
    heading3("Category Filter"),
    bodyPara("Four tab-style buttons allow filtering by problem category: All, Small (dim <= 150), Medium (150 < dim <= 500), and Large (dim > 500). Selecting a category filters all charts, tables, and statistics to show only results for problems in that category."),
    heading3("Algorithm Filter"),
    bodyPara("A dropdown selector allows filtering results to a specific algorithm. When set to \"All Algorithms,\" results from all tested algorithms are displayed. The dropdown dynamically populates based on algorithms present in the current result set."),

    heading2("3.4 Charts"),
    heading3("Algorithm Performance Bar Chart"),
    bodyPara("Displays the average optimality gap (GAP%) for each algorithm, sorted from lowest to highest. Bar colors correspond to each algorithm's assigned color. This chart provides a quick visual comparison of solution quality across algorithms."),
    heading3("Average Execution Time Chart"),
    bodyPara("Shows the average execution time in milliseconds for each algorithm. This chart helps identify trade-offs between solution quality and computational cost. Algorithms that achieve lower GAP at higher time cost may be suitable for offline optimization, while faster algorithms may be preferred for real-time applications."),
    heading3("Algorithm Comparison Radar Chart"),
    bodyPara("A radar (spider) chart that normalizes and displays multiple performance dimensions for each algorithm. Dimensions typically include average GAP, average time, and win rate. The radar chart enables holistic comparison, revealing algorithms that perform well across multiple criteria versus those optimized for a single metric."),

    heading2("3.5 Problem Coverage Summary"),
    bodyPara("A detailed table listing each TSPLIB problem in the current result set, showing its dimension, optimal tour length, category, the best-performing algorithm for that problem, and the best GAP achieved. This table is useful for identifying problem-specific algorithm strengths and weaknesses."),
    heading2("3.6 Quick Experiment Summary"),
    bodyPara("A summary card showing the status of the most recent experiment run, including the run ID, number of completed experiments, and elapsed time. If no experiment has been run, this card displays guidance to navigate to the Experiment Designer."),
  ];
}

// ── Chapter 4: Experiment Designer ──
function ch4() {
  return [
    heading1("Chapter 4: Experiment Designer"),
    heading2("4.1 Overview"),
    bodyPara("The Experiment Designer (Deney Tasarimcisi) is the core tool for configuring and executing benchmark experiments. It provides a structured workflow for selecting algorithms, choosing problems, configuring parameters, and running experiments with real-time progress tracking. The designer uses a multi-panel layout that separates algorithm selection, problem selection, and experiment settings into distinct, manageable sections."),

    heading2("4.2 Algorithm Selection"),
    bodyPara("The algorithm selection panel displays all 9 available algorithms as checkboxes, grouped by type (Local Search and Meta-Heuristic). Five algorithms are marked as \"Ready\" (2-opt, 3-opt, Or-opt, Swap, Hybrid) and can be immediately used in experiments. Four algorithms (GA, PSO, GWO, HHO) are marked as \"Planned\" and are displayed but disabled."),
    bodyPara("Two utility buttons are provided: \"Select All\" enables all ready algorithms, and \"Clear\" deselects all. Each algorithm checkbox shows the algorithm name, type badge, and complexity information."),

    heading2("4.3 Algorithm Parameters Configuration"),
    bodyPara("Below the algorithm selection, expandable parameter panels allow fine-tuning each algorithm. When expanded, a panel displays all configurable parameters with their current values, range constraints, and descriptions. Parameters include:"),
    makeTable(
      ["Algorithm", "Parameter", "Default", "Range"],
      [
        ["2-opt", "max_iterations", "2000", "100 - 50,000"],
        ["3-opt", "max_iterations", "200", "10 - 5,000"],
        ["Or-opt", "max_iterations", "1000", "100 - 30,000"],
        ["Swap", "max_iterations", "5000", "100 - 100,000"],
        ["Hybrid", "cycles", "5", "1 - 50"],
        ["GA", "7 parameters", "pop=50, gen=100, ...", "See Algo Reference"],
        ["PSO", "6 parameters", "swarm=30, iter=100, ...", "See Algo Reference"],
        ["GWO", "4 parameters", "pop=30, iter=100, ...", "See Algo Reference"],
        ["HHO", "4 parameters", "pop=30, iter=100, ...", "See Algo Reference"],
      ],
      [2000, 2200, 2560, 2600]
    ),
    tableCaption("Table 4.1: Algorithm parameter overview"),

    heading2("4.4 Problem Selection"),
    bodyPara("The problem selection panel provides a searchable list of all 45 TSPLIB problems, organized by category. A search field allows quick filtering by problem name. Problems are grouped into three sections:"),
    bulletItemBold("Small (17 problems): ", "berlin52 through pr152, dimensions 51-152", "bl3"),
    bulletItemBold("Medium (13 problems): ", "kroA150 through rd400, dimensions 150-400", "bl3"),
    bulletItemBold("Large (15 problems): ", "d493 through pr2392, dimensions 493-2392", "bl3"),
    bodyPara("Each category has \"Select All\" and \"Clear\" buttons. The current selection count is displayed prominently, along with the experiment matrix size (algorithms x problems)."),

    heading2("4.5 Experiment Matrix Preview"),
    bodyPara("A live counter shows the total number of experiment combinations (selected algorithms multiplied by selected problems). For example, selecting 5 algorithms and 10 problems yields a matrix of 50 experiments. This preview helps users understand the scope of their experiment before starting it."),

    heading2("4.6 Experiment Settings"),
    makeTable(
      ["Setting", "Description", "Default"],
      [
        ["Runs per Experiment", "Number of independent runs per algorithm-problem pair", "3"],
        ["Workers", "Number of parallel worker threads (simulation)", "4"],
        ["Random Seed", "Base seed for reproducible results", "42"],
        ["Skip Cached", "Skip experiments that already have results", "Enabled"],
      ],
      [2800, 3800, 2760]
    ),
    tableCaption("Table 4.2: Experiment settings"),

    heading2("4.7 Preset Configurations"),
    bodyPara("Four preset buttons provide quick configuration for common experiment scenarios:"),
    makeTable(
      ["Preset", "Algorithms", "Problems", "Runs"],
      [
        ["Quick Test", "5 ready", "5 small", "1"],
        ["Standard", "5 ready", "17 small", "3"],
        ["Comprehensive", "5 ready", "30 (small + medium)", "5"],
        ["Full Scope", "5 ready", "All 45", "5"],
      ],
      [2400, 2000, 2560, 2400]
    ),
    tableCaption("Table 4.3: Preset configuration overview"),

    heading2("4.8 Running Experiments"),
    bodyPara("Click the \"Start Experiment\" button to begin. The application sends a POST request to the benchmark runner service on port 3003, which begins executing experiments sequentially. Real-time progress is displayed via Socket.io events showing:"),
    bulletItemBold("Progress: ", "Completed/total experiments, percentage bar, current algorithm-problem pair", "bl4"),
    bulletItemBold("Elapsed Time: ", "Total elapsed time since experiment start", "bl4"),
    bulletItemBold("ETA: ", "Estimated time remaining based on average experiment duration", "bl4"),
    bulletItemBold("Live Results: ", "Individual results appear as they complete, with GAP and time metrics", "bl4"),
    bodyPara("After all experiments complete, the results are automatically merged into the main result set. A completion banner shows the total number of results and total computation time. Users can then navigate to the Results view for detailed analysis."),
  ];
}

// ── Chapter 5: Results & Analysis ──
function ch5() {
  return [
    heading1("Chapter 5: Results & Analysis"),
    heading2("5.1 Overview"),
    bodyPara("The Results view (Sonuclar) is the analytical heart of TSP Benchmark Studio. It is organized into three sub-tabs: Overview, Charts, and Details. Each tab provides progressively deeper levels of analysis, from summary statistics to publication-ready visualizations and exportable data tables."),

    heading2("5.2 Overview Sub-Tab"),
    heading3("Summary Banner"),
    bodyPara("A prominent banner at the top displays the total number of results, the number of unique algorithms and problems, and the overall average GAP. This provides immediate context for the data being analyzed."),
    heading3("Quick Statistics"),
    bodyPara("A row of metric cards showing: Best Overall GAP, Worst Overall GAP, Fastest Average Time, and the Total Unique Problem-Algorithm Pairs tested."),
    heading3("Algorithm Ranking Table (Friedman)"),
    bodyPara("A ranking table inspired by Friedman's non-parametric test. Algorithms are ranked by their average GAP score, with the best algorithm ranked first. The table shows average GAP, minimum GAP, maximum GAP, average time, and number of experiments for each algorithm. Rankings use Friedman-style average rank assignment for tied values."),
    heading3("Performance Heatmap"),
    bodyPara("A color-coded grid showing the GAP achieved by each algorithm on each problem. Rows represent algorithms, columns represent problems, and cell colors indicate GAP values (greener = better, redder = worse). This visualization quickly reveals algorithm-problem interactions and identifies problems where certain algorithms excel."),
    heading3("Speed Ranking"),
    bodyPara("A horizontal bar chart ranking algorithms by average execution time from fastest to slowest. This complements the quality-focused performance charts by highlighting computational efficiency differences."),

    heading2("5.3 Charts Sub-Tab"),
    heading3("Performance Profile Chart"),
    bodyPara("A cumulative distribution function (CDF) plot showing the proportion of problems solved within a given factor (tau) of the best-known solution. The x-axis represents the performance ratio tau, and the y-axis represents the fraction of problems. Algorithms with curves that reach higher y-values at lower tau values are superior. This is the standard Dolan-Moré performance profile used in optimization benchmarking literature."),
    heading3("GAP Distribution Range"),
    bodyPara("A range chart showing the minimum and maximum GAP achieved by each algorithm across all problems, with the average GAP marked. This visualization highlights the consistency of algorithms: narrow ranges indicate stable performance, while wide ranges suggest sensitivity to problem characteristics."),
    heading3("GAP vs Time Scatter Plot"),
    bodyPara("A scatter plot with average GAP on the x-axis and average execution time on the y-axis, with each point representing an algorithm. This plot reveals the Pareto frontier of quality vs. speed trade-offs. Algorithms in the bottom-left corner are both fast and high-quality."),
    heading3("Problem Difficulty Analysis"),
    bodyPara("A chart analyzing the relative difficulty of problems based on the average GAP achieved across all algorithms. Problems are sorted from easiest (lowest average GAP) to hardest (highest average GAP)."),
    heading3("Category Performance"),
    bodyPara("Grouped bar charts showing algorithm performance broken down by problem category (Small, Medium, Large). This reveals how algorithm relative performance changes with problem scale."),
    heading3("Box Plot Visualization"),
    bodyPara("Box-and-whisker plots for each algorithm showing the distribution of GAP values across all problems. Each box displays the median, quartiles, and outliers, providing a comprehensive view of algorithm performance variability."),
    heading3("Win Rate Matrix"),
    bodyPara("A matrix showing how often each algorithm achieves the best result compared to every other algorithm. Each cell represents the number of problems where the row algorithm outperforms the column algorithm. The diagonal is zero. This pairwise comparison is useful for statistical testing and identifying significant performance differences."),

    heading2("5.4 Details Sub-Tab"),
    heading3("Head-to-Head Comparison"),
    bodyPara("A dropdown selector allows choosing two algorithms for direct comparison. When selected, the view filters to show only results where both algorithms have been tested on the same problems, enabling side-by-side comparison of GAP and time metrics."),
    heading3("Results Table"),
    bodyPara("A comprehensive, sortable, paginated table displaying all benchmark results. Columns include: Problem, Dimension, Optimal, Strategy, Avg GAP, Best GAP, Avg Length, Best Length, Avg Time, and Runs. Users can sort by any column (ascending or descending) and control the number of rows displayed per page (10, 15, 25, 50, or 100)."),
    heading3("Export Options"),
    makeTable(
      ["Format", "Description", "Use Case"],
      [
        ["CSV", "Comma-separated values with header row", "Data analysis in Excel, Python, R"],
        ["JSON", "Nested structure: {problem: {strategy: {metrics}}}", "Programmatic data processing"],
        ["LaTeX", "Formatted LaTeX table (tabular environment)", "Direct inclusion in academic papers"],
      ],
      [1600, 3800, 3960]
    ),
    tableCaption("Table 5.1: Export format specifications"),
  ];
}

// ── Chapter 6: Algorithms Library ──
function ch6() {
  return [
    heading1("Chapter 6: Algorithms Library"),
    heading2("6.1 Algorithm Cards Overview"),
    bodyPara("The Algorithms Library view displays all 9 algorithms as visually rich cards. Each card shows the algorithm name, type badge (Local Search or Meta-Heuristic), complexity notation, status indicator (Ready or Planned), and a brief description. Ready algorithms are displayed with full interactivity; planned algorithms are visually distinguished and marked as upcoming."),
    bodyPara("Cards are organized in a responsive grid layout that adapts to screen size. Each card uses the algorithm's assigned color for visual identification, matching the colors used throughout the dashboard and results charts."),

    heading2("6.2 Algorithm Detail Sheet"),
    bodyPara("Clicking on any algorithm card opens a comprehensive detail sheet (sheet panel) with the following information:"),
    bulletItemBold("Description: ", "A detailed explanation of the algorithm's approach, including its theoretical foundation and practical characteristics.", "bl5"),
    bulletItemBold("Complexity: ", "Time complexity in Big-O notation, explaining how computation scales with problem size.", "bl5"),
    bulletItemBold("Performance Characteristics: ", "Expected GAP range and execution time characteristics based on the TSPLIB benchmark suite.", "bl5"),
    bulletItemBold("Parameters: ", "Complete list of configurable parameters with descriptions, types, default values, ranges, and units.", "bl5"),
    bulletItemBold("Pseudocode: ", "High-level pseudocode describing the algorithm's main loop and key operations.", "bl5"),

    heading2("6.3 Local Search Algorithms"),
    heading3("6.3.1 2-opt"),
    bodyPara("The 2-opt algorithm iteratively removes two edges from the tour and reconnects them in the opposite way. If the reconnection produces a shorter tour, the change is accepted. This process repeats until no improving 2-opt move can be found. Complexity: O(n^2). Typical GAP range: 2-6%. Fast execution makes it suitable as a baseline and as a refinement step within other algorithms."),

    heading3("6.3.2 3-opt"),
    bodyPara("The 3-opt algorithm extends 2-opt by removing three edges and considering all possible reconnections (there are 7 possible ways to reconnect three edges into a tour). This allows more complex tour restructuring at the cost of higher computational complexity. Complexity: O(n^3). Typical GAP range: 0.3-3%. Produces significantly better solutions than 2-opt but takes considerably longer."),

    heading3("6.3.3 Or-opt"),
    bodyPara("The Or-opt algorithm moves sequences of 2 or 3 consecutive nodes (segments) to different positions in the tour. This neighborhood is a subset of 3-opt but is more efficient to explore. Complexity: O(n^2). Typical GAP range: 1.5-5%. Provides a good balance between solution quality and speed."),

    heading3("6.3.4 Swap"),
    bodyPara("The Swap algorithm exchanges the positions of two nodes in the tour. It is the simplest local search neighborhood, checking all pairs of nodes. Complexity: O(n^2). Typical GAP range: 4-12%. While not competitive in solution quality, it serves as an educational baseline and is extremely fast."),

    heading3("6.3.5 Hybrid"),
    bodyPara("The Hybrid algorithm combines 2-opt, 3-opt, and Or-opt in a cyclic fashion. Each cycle applies one iteration of 2-opt, then 3-opt, then Or-opt, repeating for a configurable number of cycles. This multi-neighborhood approach captures the strengths of each component. Complexity: O(n^3). Typical GAP range: 0.2-2.5%. This is the strongest local search algorithm in the suite and serves as the recommended default."),

    heading2("6.4 Meta-Heuristic Algorithms (Planned)"),
    bodyPara("Four meta-heuristic algorithms are planned for future implementation. Each is designed for global search and is expected to complement the local search algorithms by exploring the solution space more broadly:"),
    heading3("6.4.1 Genetic Algorithm (GA)"),
    bodyPara("A population-based evolutionary algorithm that uses crossover, mutation, and selection operators to evolve a population of tours toward better solutions. Supports tournament selection, configurable crossover and mutation rates, elite preservation, and optional local search refinement. Expected GAP range: 1-4%."),
    heading3("6.4.2 Particle Swarm Optimization (PSO)"),
    bodyPara("A swarm intelligence algorithm where particles (potential solutions) move through the solution space guided by their personal best and the global best positions. Uses the Clerc constriction factor for velocity updates. Supports local search refinement. Expected GAP range: 1.5-5%."),
    heading3("6.4.3 Grey Wolf Optimizer (GWO)"),
    bodyPara("Inspired by the hunting hierarchy of grey wolves (alpha, beta, delta, omega). The alpha wolf leads the hunt toward the optimal solution. The exploration-exploitation balance is controlled by a linearly decreasing parameter. Expected GAP range: 2-6%."),
    heading3("6.4.4 Harris Hawks Optimization (HHO)"),
    bodyPara("Mimics the cooperative hunting strategy of Harris hawks. The algorithm dynamically switches between exploration (soft/hard besiege) and exploitation (rapid dives) phases based on a jump probability parameter. Expected GAP range: 1.5-5%."),
  ];
}

// ── Chapter 7: Algorithm Reference ──
function ch7() {
  return [
    heading1("Chapter 7: Algorithm Reference"),
    bodyPara("This chapter provides a comprehensive reference table of all 9 algorithms supported by TSP Benchmark Studio, along with detailed performance characteristics for each algorithm."),

    heading2("7.1 Complete Algorithm Reference Table"),
    makeTable(
      ["Algorithm", "Type", "Complexity", "Status", "Params", "Description"],
      [
        ["2-opt", "Local Search", "O(n\u00B2)", "Ready", "1", "Edge-pair reconnection improvement"],
        ["3-opt", "Local Search", "O(n\u00B3)", "Ready", "1", "Three-edge reconnection improvement"],
        ["Or-opt", "Local Search", "O(n\u00B2)", "Ready", "1", "Segment relocation improvement"],
        ["Swap", "Local Search", "O(n\u00B2)", "Ready", "1", "Node position exchange"],
        ["Hybrid", "Local Search", "O(n\u00B3)", "Ready", "1", "Combined 2-opt + 3-opt + Or-opt cycles"],
        ["GA", "Meta-Heuristic", "O(pop\u00D7gen\u00D7n)", "Planned", "7", "Evolutionary crossover + mutation"],
        ["PSO", "Meta-Heuristic", "O(swarm\u00D7iter\u00D7n)", "Planned", "6", "Swarm particle movement optimization"],
        ["GWO", "Meta-Heuristic", "O(pop\u00D7iter\u00D7n)", "Planned", "4", "Grey wolf alpha-beta-delta hierarchy"],
        ["HHO", "Meta-Heuristic", "O(pop\u00D7iter\u00D7n)", "Planned", "4", "Harris hawk cooperative hunting"],
      ],
      [1600, 1600, 2000, 1200, 900, 2060]
    ),
    tableCaption("Table 7.1: Complete algorithm reference"),

    heading2("7.2 Performance Characteristics"),
    makeTable(
      ["Algorithm", "Avg GAP Range", "Time Range", "Best For"],
      [
        ["2-opt", "2.0% - 5.5%", "8 - 45 ms", "Quick baseline comparison"],
        ["3-opt", "0.3% - 3.0%", "40 - 180 ms", "High-quality solutions"],
        ["Or-opt", "1.5% - 4.5%", "6 - 35 ms", "Balanced quality/speed"],
        ["Swap", "4.0% - 12.0%", "3 - 18 ms", "Fast educational baseline"],
        ["Hybrid", "0.2% - 2.5%", "80 - 400 ms", "Best local search quality"],
        ["GA", "1.0% - 4.0%", "200 - 1000 ms", "Global exploration"],
        ["PSO", "1.5% - 5.0%", "150 - 800 ms", "Swarm-based search"],
        ["GWO", "2.0% - 6.0%", "120 - 600 ms", "Hierarchical optimization"],
        ["HHO", "1.5% - 5.0%", "100 - 500 ms", "Adaptive exploration-exploitation"],
      ],
      [1800, 2200, 2200, 3160]
    ),
    tableCaption("Table 7.2: Algorithm performance characteristics"),
  ];
}

// ── Chapter 8: Data Import & Export ──
function ch8() {
  return [
    heading1("Chapter 8: Data Import & Export"),

    heading2("8.1 CSV Format Specification"),
    bodyPara("CSV files must include a header row followed by data rows. Columns are comma-separated. The following columns are supported:"),
    ...codeBlock([
      "problem,dimension,optimal,strategy,avg_length,avg_gap,",
      "best_length,best_gap,avg_time_ms,elapsed_ms,n_runs,timestamp",
      "",
      "berlin52,52,7542,Hybrid,7589,0.62,7558,0.21,215.3,646.0,3,2026-04-08T...",
      "eil51,51,426,2-opt,440,3.29,435,2.11,12.5,37.5,3,2026-04-08T...",
    ]),
    spacer(100),
    makeTable(
      ["Column", "Type", "Required", "Description"],
      [
        ["problem", "string", "Yes", "TSPLIB problem name"],
        ["dimension", "integer", "Yes", "Number of nodes"],
        ["optimal", "number", "Yes", "Best known tour length"],
        ["strategy", "string", "Yes", "Algorithm short name"],
        ["avg_length", "number", "Yes", "Average tour length across runs"],
        ["avg_gap", "number", "Yes", "Average optimality gap (%)"],
        ["best_length", "number", "No", "Best tour length achieved"],
        ["best_gap", "number", "No", "Best optimality gap (%)"],
        ["avg_time_ms", "number", "Yes", "Average execution time (ms)"],
        ["elapsed_ms", "number", "No", "Total elapsed time (ms)"],
        ["n_runs", "integer", "No", "Number of independent runs (default: 3)"],
        ["timestamp", "string", "No", "ISO 8601 timestamp"],
      ],
      [2200, 1600, 1400, 4160]
    ),
    tableCaption("Table 8.1: CSV column specification"),

    heading2("8.2 JSON Format Specification"),
    bodyPara("JSON files use a nested structure where the top-level keys are problem names and second-level keys are algorithm strategy names:"),
    ...codeBlock([
      '{',
      '  "berlin52": {',
      '    "Hybrid": {',
      '      "avg_length": 7589, "avg_gap": 0.62,',
      '      "best_length": 7558, "best_gap": 0.21,',
      '      "avg_time_ms": 215.3, "elapsed_ms": 646.0,',
      '      "n_runs": 3, "timestamp": "2026-04-08T..."',
      '    },',
      '    "2-opt": { ... }',
      '  },',
      '  "eil51": { ... }',
      '}',
    ]),
    spacer(100),

    heading2("8.3 LaTeX Export Format"),
    bodyPara("The LaTeX export generates a formatted tabular environment suitable for direct inclusion in academic papers:"),
    ...codeBlock([
      '\\begin{table}[htbp]',
      '\\centering',
      '\\caption{Benchmark Results}',
      '\\begin{tabular}{llrrrr}',
      '\\hline',
      'Problem & Algo & Avg GAP & Best GAP & Time (ms) & Runs \\\\',
      '\\hline',
      'berlin52 & Hybrid & 0.62 & 0.21 & 215.3 & 3 \\\\',
      'eil51 & 2-opt & 3.29 & 2.11 & 12.5 & 3 \\\\',
      '\\hline',
      '\\end{tabular}',
      '\\end{table}',
    ]),
    spacer(100),

    heading2("8.4 Using File Upload Buttons"),
    bodyPara("Navigate to the Results view and locate the toolbar at the top of the page. Three buttons are provided for data import/export:"),
    bulletItemBold("Upload CSV: ", "Opens a file picker for .csv files. The file is parsed client-side and results are merged into the store.", "bl6"),
    bulletItemBold("Upload JSON: ", "Opens a file picker for .json files. The nested structure is parsed and results are merged.", "bl6"),
    bulletItemBold("Export: ", "A dropdown button offering CSV, JSON, and LaTeX export options. Exports the currently filtered result set.", "bl6"),

    heading2("8.5 Demo Data Regeneration"),
    bodyPara("The \"Regenerate Demo\" button (available in the Dashboard toolbar) resets the entire result set to the built-in demo data. This uses a seeded pseudo-random number generator (seed: 42) to produce reproducible results for 5 ready algorithms across 10 small problems. The demo data includes realistic GAP and time distributions based on published benchmark results for TSPLIB problems."),
  ];
}

// ── Chapter 9: Architecture ──
function ch9() {
  return [
    heading1("Chapter 9: Architecture"),

    heading2("9.1 Frontend Stack"),
    bodyPara("TSP Benchmark Studio is built on a modern React-based frontend with server-side rendering capabilities:"),
    makeTable(
      ["Technology", "Version", "Purpose"],
      [
        ["Next.js", "16", "Full-stack React framework with App Router"],
        ["React", "19", "UI component library with concurrent features"],
        ["TypeScript", "5", "Static type checking and enhanced DX"],
        ["Tailwind CSS", "4", "Utility-first CSS framework"],
        ["shadcn/ui", "Latest", "45 composable UI components built on Radix"],
        ["Framer Motion", "12", "Declarative animations and transitions"],
        ["Recharts", "2.15", "Declarative charting library (7+ chart types)"],
        ["Zustand", "5", "Lightweight state management"],
        ["next-themes", "0.4", "Dark/light theme switching"],
        ["Lucide React", "0.525", "Icon library"],
      ],
      [2400, 1600, 5360]
    ),
    tableCaption("Table 9.1: Frontend technology stack"),

    heading2("9.2 State Management"),
    bodyPara("Application state is managed through a single Zustand store (benchmark-store.ts) that handles:"),
    bulletItemBold("Result Data: ", "Array of BenchmarkResult objects, with filtering, sorting, and computed statistics.", "bl7"),
    bulletItemBold("UI State: ", "Active view, sidebar visibility, filter selections, pagination.", "bl7"),
    bulletItemBold("Experiment Config: ", "Selected algorithms, problems, parameters, and run settings.", "bl7"),
    bulletItemBold("Run Execution: ", "Running status, progress tracking, accumulated results, error handling.", "bl7"),
    bodyPara("The store exports computed getters (getFilteredResults, getStats, getAlgorithmSummary, getProblemSummary) that derive statistics from the raw results array, ensuring consistency across views."),

    heading2("9.3 Backend: Benchmark Runner Service"),
    bodyPara("The benchmark runner is a standalone mini-service (mini-services/benchmark-runner/index.ts) built with Node.js HTTP and Socket.io:"),
    bulletItemBold("HTTP Endpoints: ", "POST /run (start experiment), GET /status (progress query), POST /stop (abort run).", "bl8"),
    bulletItemBold("Socket.io Events: ", "Real-time push of progress updates, individual results, and completion notifications.", "bl8"),
    bulletItemBold("Port: ", "3003 (configurable).", "bl8"),
    bulletItemBold("Simulation: ", "Uses seeded pseudo-random generation to produce reproducible benchmark results matching realistic GAP and time distributions.", "bl8"),

    heading2("9.4 Database"),
    bodyPara("The application uses Prisma ORM with SQLite for persistent storage. The database schema supports task management features and benchmark result persistence. The Prisma schema is defined in prisma/schema.prisma and can be managed using bun run db:push (apply schema) or bun run db:migrate (versioned migrations)."),

    heading2("9.5 File Structure Overview"),
    ...codeBlock([
      "tsp-benchmark-studio/",
      "+-- src/",
      "|   +-- app/                    # Next.js App Router",
      "|   |   +-- api/benchmark/run/  # REST API for experiments",
      "|   |   +-- layout.tsx          # Root layout with sidebar",
      "|   |   +-- page.tsx            # Main application page",
      "|   +-- components/",
      "|   |   +-- ui/                 # 45 shadcn/ui components",
      "|   |   +-- benchmark/          # Custom benchmark components",
      "|   +-- store/benchmark-store.ts # Zustand store",
      "|   +-- lib/utils.ts            # Utility functions",
      "+-- mini-services/",
      "|   +-- benchmark-runner/       # Socket.io benchmark service",
      "+-- tsp-benchmark-cli/          # Python CLI benchmark tool",
      "+-- prisma/schema.prisma        # Database schema",
    ]),
  ];
}

// ── Chapter 10: API Reference ──
function ch10() {
  return [
    heading1("Chapter 10: API Reference"),

    heading2("10.1 POST /api/benchmark/run"),
    bodyPara("Starts a new benchmark experiment by forwarding the configuration to the benchmark runner mini-service."),
    heading3("Request Body"),
    ...codeBlock([
      '{',
      '  "algorithms": [',
      '    { "id": "two_opt", "params": { "max_iterations": 2000 } },',
      '    { "id": "hybrid", "params": { "cycles": 5 } }',
      '  ],',
      '  "problems": ["berlin52", "eil51", "st70"],',
      '  "settings": {',
      '    "nRuns": 3,',
      '    "workers": 4,',
      '    "seed": 42,',
      '    "skipCached": true',
      '  }',
      '}',
    ]),
    spacer(80),
    heading3("Response (202 Accepted)"),
    ...codeBlock([
      '{',
      '  "runId": "run_m1abc2_xyz123",',
      '  "totalExperiments": 6,',
      '  "status": "running",',
      '  "message": "Benchmark run started with 6 experiments"',
      '}',
    ]),
    spacer(80),
    heading3("Error Responses"),
    makeTable(
      ["Status", "Condition", "Response"],
      [
        ["400", "No algorithms selected", '{ "error": "At least one algorithm required" }'],
        ["400", "No problems selected", '{ "error": "At least one problem required" }'],
        ["409", "Run already in progress", '{ "error": "Run already in progress", "code": "BUSY" }'],
        ["503", "Runner service unreachable", '{ "error": "Cannot connect to benchmark service" }'],
      ],
      [1200, 2800, 5360]
    ),
    tableCaption("Table 10.1: Error responses"),

    heading2("10.2 Socket.io Events"),
    bodyPara("The benchmark runner service emits events on the \"benchmark\" channel. Clients connect to ws://localhost:3003/socket.io/ and listen for the following event types:"),
    heading3("benchmark:progress"),
    ...codeBlock([
      '{',
      '  "type": "progress",',
      '  "data": {',
      '    "runId": "run_m1abc2_xyz123",',
      '    "completed": 3, "total": 6, "percentage": 50.0,',
      '    "current": { "problem": "st70", "algorithm": "3-opt", "run": 2 },',
      '    "elapsed_ms": 5432, "eta_ms": 5400',
      '  }',
      '}',
    ]),
    spacer(80),
    heading3("benchmark:result"),
    ...codeBlock([
      '{',
      '  "type": "result",',
      '  "data": {',
      '    "runId": "run_m1abc2_xyz123",',
      '    "problem": "berlin52", "dimension": 52, "optimal": 7542,',
      '    "algorithm": "2-opt",',
      '    "avg_gap": 3.45, "best_gap": 1.82,',
      '    "avg_time_ms": 22.3, "avg_length": 7802,',
      '    "best_length": 7679, "n_runs": 3',
      '  }',
      '}',
    ]),
    spacer(80),
    heading3("benchmark:complete"),
    ...codeBlock([
      '{',
      '  "type": "complete",',
      '  "data": {',
      '    "runId": "run_m1abc2_xyz123",',
      '    "results": [ ... ],',
      '    "total_results": 6,',
      '    "total_time_ms": 12850,',
      '    "csv_data": "problem,dimension,..."',
      '  }',
      '}',
    ]),
  ];
}

// ── Chapter 11: Troubleshooting ──
function ch11() {
  return [
    heading1("Chapter 11: Troubleshooting"),

    heading2("11.1 Common Issues and Solutions"),

    heading3("Turbopack Permission Errors"),
    bodyPara("When running bun run dev, you may encounter permission-related errors from Turbopack (Next.js dev server). This is a known issue on some Linux systems:"),
    bulletItemBold("Symptom: ", "Error messages about cache directory permissions or file system watcher limits.", "bl9"),
    bulletItemBold("Solution 1: ", "Increase the inotify watcher limit: sudo sysctl fs.inotify.max_user_watches=524288", "bl9"),
    bulletItemBold("Solution 2: ", "Clear the .next cache directory: rm -rf .next && bun run dev", "bl9"),
    bulletItemBold("Solution 3: ", "Run with --turbopack flag explicitly or use Node.js instead of Bun for development.", "bl9"),

    heading3("Socket.io Connection Issues"),
    bodyPara("If real-time experiment progress is not updating:"),
    bulletItemBold("Symptom: ", "Start Experiment button returns an error, or progress stays at 0%.", "bl10"),
    bulletItemBold("Solution 1: ", "Ensure the benchmark runner service is running on port 3003: cd mini-services/benchmark-runner && bun run index.ts", "bl10"),
    bulletItemBold("Solution 2: ", "Check CORS settings if running on a different host. The service allows all origins by default.", "bl10"),
    bulletItemBold("Solution 3: ", "Verify the Socket.io path matches between client and server (/socket.io).", "bl10"),
    bulletItemBold("Solution 4: ", "Check browser console for WebSocket connection errors or mixed content warnings.", "bl10"),

    heading3("Data Loading Problems"),
    bodyPara("Issues when importing CSV or JSON data:"),
    bulletItemBold("Symptom: ", "Upload button does nothing, or error toast appears.", "bl11"),
    bulletItemBold("Solution 1: ", "Verify CSV headers match the expected column names (case-insensitive: problem, dimension, optimal, strategy, avg_gap, avg_time_ms).", "bl11"),
    bulletItemBold("Solution 2: ", "Ensure JSON follows the nested structure: {\"problem_name\": {\"strategy_name\": {metrics}}}.", "bl11"),
    bulletItemBold("Solution 3: ", "Check that problem names in the file match TSPLIB names recognized by the application. Unknown problem names will not be auto-linked to dimension/optimal data.", "bl11"),
    bulletItemBold("Solution 4: ", "For large files (>10MB), consider loading data in smaller batches to avoid browser memory issues.", "bl11"),

    heading3("Charts Not Rendering"),
    bodyPara("If charts appear blank or do not display:"),
    bulletItemBold("Solution 1: ", "Ensure there is data in the result set. Empty data produces empty charts.", "bl11"),
    bulletItemBold("Solution 2: ", "Try clearing filters (set category to \"All\" and algorithm to \"All\").", "bl11"),
    bulletItemBold("Solution 3: ", "Resize the browser window to trigger chart redraw.", "bl11"),

    heading3("Experiment Run Stalls"),
    bodyPara("If an experiment stops progressing:"),
    bulletItemBold("Solution 1: ", "Check the benchmark runner console for error messages.", "bl11"),
    bulletItemBold("Solution 2: ", "Use the Stop button to cancel the stalled run and start a new one.", "bl11"),
    bulletItemBold("Solution 3: ", "Restart the benchmark runner service.", "bl11"),
  ];
}

// ═══════════════════════════════════════════════════════════════════
// BUILD DOCUMENT
// ═══════════════════════════════════════════════════════════════════
async function main() {
  const doc = new Document({
    styles: {
      default: {
        document: {
          run: { font: FONT, size: BODY_SIZE, color: P.body },
          paragraph: { spacing: { line: LINE_SPACING } },
        },
      },
      paragraphStyles: [
        {
          id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: H1_SIZE, bold: true, color: "1B6B7A", font: FONT },
          paragraph: { spacing: { before: 600, after: 300 }, outlineLevel: 0 },
        },
        {
          id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: H2_SIZE, bold: true, color: P.tAccentLine, font: FONT },
          paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 1 },
        },
        {
          id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: H3_SIZE, bold: true, color: P.secondary, font: FONT },
          paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 2 },
        },
      ],
    },
    numbering: buildNumberingConfig(),
    sections: [
      // ── Section 1: Cover ──
      {
        properties: {
          page: {
            size: { width: 11906, height: 16838 },
            margin: { top: 0, bottom: 0, left: 0, right: 0 },
          },
        },
        children: buildCover(),
      },
      // ── Section 2: TOC (Front matter, Roman numerals) ──
      {
        properties: {
          type: SectionType.NEXT_PAGE,
          page: {
            size: { width: 11906, height: 16838 },
            margin: { top: 1800, bottom: 1440, left: 1701, right: 1417 },
            pageNumbers: { start: 1, formatType: NumberFormat.UPPER_ROMAN },
          },
        },
        headers: {
          default: new Header({
            children: [new Paragraph({
              alignment: AlignmentType.RIGHT,
              children: [new TextRun({ text: "TSP Benchmark Studio", font: FONT, size: 16, color: P.secondary, italics: true })],
            })],
          }),
        },
        footers: {
          default: new Footer({
            children: [new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [new TextRun({ text: "Page ", font: FONT, size: 16, color: P.secondary }),
                new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: P.secondary })],
            })],
          }),
        },
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 480, after: 360 },
            children: [new TextRun({ text: "Table of Contents", bold: true, size: 32, font: FONT, color: "1B6B7A" })],
          }),
          new TableOfContents("Table of Contents", {
            hyperlink: true,
            headingStyleRange: "1-3",
          }),
          new Paragraph({
            spacing: { before: 200 },
            children: [new TextRun({
              text: "Note: This Table of Contents is generated via field codes. To ensure page number accuracy after editing, please right-click the TOC and select \"Update Field.\"",
              italics: true, size: 18, color: "888888", font: FONT,
            })],
          }),
          new Paragraph({ children: [new PageBreak()] }),
        ],
      },
      // ── Section 3: Body (Arabic numerals starting at 1) ──
      {
        properties: {
          type: SectionType.NEXT_PAGE,
          page: {
            size: { width: 11906, height: 16838 },
            margin: { top: 1800, bottom: 1440, left: 1701, right: 1417 },
            pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL },
          },
        },
        headers: {
          default: new Header({
            children: [new Paragraph({
              alignment: AlignmentType.RIGHT,
              children: [new TextRun({ text: "TSP Benchmark Studio  |  User Guide & Technical Documentation", font: FONT, size: 16, color: P.secondary, italics: true })],
            })],
          }),
        },
        footers: {
          default: new Footer({
            children: [new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [new TextRun({ text: "Page ", font: FONT, size: 16, color: P.secondary }),
                new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: P.secondary })],
            })],
          }),
        },
        children: [
          ...ch1(),
          ...ch2(),
          ...ch3(),
          ...ch4(),
          ...ch5(),
          ...ch6(),
          ...ch7(),
          ...ch8(),
          ...ch9(),
          ...ch10(),
          ...ch11(),
        ],
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  const outPath = path.join(__dirname, "TSP_Benchmark_Studio_Guide.docx");
  fs.writeFileSync(outPath, buffer);
  console.log("Document generated:", outPath);
}

main().catch(err => { console.error("Error:", err); process.exit(1); });
