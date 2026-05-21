import re
from datetime import datetime

# Updating Changelog
with open("docs/04_Changelog.md", "r", encoding="utf-8") as f:
    changelog = f.read()

new_log = """## 2026-05-21 — "Split-Brain" Architecture Resolution & Core Consolidation (GitHub Copilot)

**GitHub Copilot** — Comprehensive Code Review (2026-05-20) recommendations implemented.

### ✅ Tamamlananlar (Tamamlanan Aşama 1-5)
- **uniride_core Paketi Oluşturuldu:** `pyproject.toml` ile sisteme dahil edilebilir (`pip install -e .`) ortak bir matematik ve algoritma kütüphanesi oluşturuldu. `sys.path` hack'leri (`sys.path.insert`) sistemin 15+ dosyasından temizlendi.
- **Split Brain (Kod Tekrarı) Çözüldü:** `optimizer_api` içindeki yavaş, string-bazlı kopya (duplicate) SOTA algoritmaları silindi. Canonical Numba SOTA uygulamaları (E2BSO, R2DMA, P-AOEA vb.) `uniride_core/algorithms/` içerisine taşındı.
- **FastAPI Adapter Katmanı:** `ebso_strategy.py`, `aoea_strategy.py` ve `rdma_strategy.py` artık Next.js string (UUID) isteklerini Integer matrislerine çevirerek ultra-hızlı Numba kütüphanesine paslıyor, sonucu tekrar String'e çevirip istemciye dönüyor.
- **Veri Modelleri Tekilleştirildi:** Parçalı yapıdaki `TSPProblem`, `BenchmarkProblem` ve `ProblemInstance` tek bir ortak `uniride_core.models.ProblemInstance` ve `TSPResult` altında birleştirildi. Dataclass'lar içerisine `__post_init__` matematiksel parametre validasyonları eklendi.
- **Deprecated Kodların Silinmesi:** `academic_benchmark/old/`, `legacy/` ve `cache/` atıl klasörleri sistemden tamamen temizlendi ve testler %100 başarılı hale getirildi.

"""

changelog = changelog.replace("## 2026-04-14", new_log + "## 2026-04-14")

with open("docs/04_Changelog.md", "w", encoding="utf-8") as f:
    f.write(changelog)

# Updating Architecture
with open("docs/02_Architecture.md", "r", encoding="utf-8") as f:
    arch = f.read()

new_arch = """┌─────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER (BFF)                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Next.js API Routes                       │   │
│  │  /api/optimize-route  /api/admin/*  /api/benchmark/*    │   │
│  │  /api/faz0/status     /api/faz3/status                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              │ HTTP/REST                        │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         Python Optimization Engine (Port 8099)           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │   │
│  │  │ Pipeline │ │ Pipeline │ │ Holistic │ │ API Adapter│ │   │
│  │  │    A     │ │    B     │ │ Solvers  │ │ Layer      │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              │ Python Imports (Int Matrices)    │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │            uniride_core (Math & Algorithms)              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────────────────┐ │   │
│  │  │ SOTA v3.0│ │ Models   │ │ Numba Accelerated Ops   │ │   │
│  │  │(E2BSO...)│ │          │ │ Local Search (2opt...)  │ │   │
│  │  └──────────┘ └──────────┘ └─────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘"""

arch = re.sub(
    r"┌─────────────────────────────────────────────────────────────────┐\n│                    BUSINESS LOGIC LAYER \(BFF\).*?└─────────────────────────────────────────────────────────────────┘",
    new_arch, arch, flags=re.DOTALL
)

with open("docs/02_Architecture.md", "w", encoding="utf-8") as f:
    f.write(arch)

