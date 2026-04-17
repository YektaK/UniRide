import ZAI from "z-ai-web-dev-sdk";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { problems, selectedAlgorithms, goal } = body as {
      problems: Array<{ name: string; dimension: number; category: string; optimal: number | null }>;
      selectedAlgorithms: string[];
      goal?: string;
    };

    if (!problems || !selectedAlgorithms) {
      return NextResponse.json(
        { success: false, error: "Problems and selectedAlgorithms are required" },
        { status: 400 }
      );
    }

    const zai = await ZAI.create();

    const problemSummary = problems
      .map((p) => `${p.name} (${p.dimension} nodes, ${p.category}, optimal: ${p.optimal ?? "?"})`)
      .join(", ");

    const goalText =
      goal === "quality"
        ? "en yüksek çözüm kalitesi"
        : goal === "speed"
          ? "en hızlı çalışma süresi"
          : goal === "balanced"
            ? "kalite ve hız dengesi"
            : "genel performans";

    const userMessage = `Seçilen Problemler: ${problemSummary}

Seçilen Algoritmalar: ${selectedAlgorithms.join(", ")}

Hedef: ${goalText}

Lütfen bu problemler ve algoritmalar için:
1. En uygun algoritma önerisini verin
2. Hangi pipeline'ın (A, B veya Holistik) neden daha uygun olduğunu açıklayın
3. Problem boyutuna göre strateji önerin
4. Beklenen performans öngörüsünü paylaşın

Cevabı kısa ve öz tutun (maksimum 3-4 paragraf). Türkçe yanıt verin.`;

    const completion = await zai.chat.completions.create({
      messages: [
        {
          role: "assistant",
          content:
            "Sen UniRide ride-sharing optimizasyon platformu için uzman algoritma danışmanısın. TSP/CVRP benchmark gereksinimlerini analiz eder ve mevcut pipeline seçeneklerinden en iyi algoritmaları önerirsin. Pipeline A (Cluster-First, Route-Second: Sweep/CW + GA/PSO/GWO/HHO), Pipeline B (Route-First, Cluster-Second: GA-Split/PSO-Split/GWO-Split/HHO-Split ile Optimal Split), Holistik çözücüler (OR-Tools CVRP, PyVRP HGS DIMACS birincisi, VROOM ultra-hızlı), ve Sezgisel algoritmalar (2-opt, Greedy, Permütasyon) arasındaki farkları iyi bilirsin. Kısa, pratik ve eyleme geçirilebilir tavsiyeler verirsin. Türkçe yanıt verirsin.",
        },
        {
          role: "user",
          content: userMessage,
        },
      ],
      thinking: { type: "disabled" },
    });

    const advice = completion.choices[0]?.message?.content;

    if (!advice) {
      return NextResponse.json(
        { success: false, error: "AI danışmanından boş yanıt alındı" },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true, advice });
  } catch (error) {
    console.error("[AI Advisor API Error]", error);
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : "Bilinmeyen hata" },
      { status: 500 }
    );
  }
}
