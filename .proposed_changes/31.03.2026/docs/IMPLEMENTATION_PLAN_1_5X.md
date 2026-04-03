# Faz 1.5X Implementation Plan: IE Resource Engine

> **Tarih:** 28 Mart 2026  
> **Versiyon:** 1.0  
> **Referans:** [Konuşma Geçmişi](../konusma_gecmisi.txt) | [IE Resource Model](../IE_RESOURCE_MODEL.md) | [ROADMAP](../ROADMAP.md)

---

## 🎯 Genel Bakış

Bu doküman, UniRide projesinin **Faz 1.5X: Heterojen Filo + IE Engine** fazının detaylı uygulama planını içerir. Bu faz, konuşma geçmişindeki (konusma_gecmisi.txt) Madde 3, 5, 14, 19, 21, 23 taleplerine dayanmaktadır.

### Konuşma Geçmişi Taleplerinin Eşleşmesi

| Madde | Talep | Faz 1.5X Karşılığı |
|-------|-------|-------------------|
| 3 | Farklı kapasiteli araçlar | VehicleConfig schema, Split Decoder V2 |
| 5 | Bütünsel yaklaşım | IE Resource Engine (resource_profiler.py) |
| 14 | Verimsiz noktaları görme | Bottleneck identification, Sandbox Mode |
| 19 | Toplayıcı/Dağıtıcı ayrımı | Directional Blocking Logic |
| 21 | Standart araç ihtiyacı tablosu | Resource Histogram, Resource Tracks |
| 23 | So/Sw kırılımı görme | hourly_demand, Tooltip breakdown |

---

## 📋 Sprint Planı

### Sprint 1: Pipeline B Tamamlama (Hafta 1)

**Hedef:** Pipeline B algoritmalarını tamamlamak ve Registry'ye eklemek

#### Görev 1.5.8: Strategy Registry Güncelleme

**Dosyalar:**
- `optimizer_api/strategies/__init__.py`

**Yapılacaklar:**
```python
# Yeni import'lar ekle
from strategies.ga_split_strategy import GASplitStrategy
from strategies.pso_split_strategy import PSOSplitStrategy  # Yeni
from strategies.hho_split_strategy import HHOSplitStrategy  # Yeni
from strategies.gwo_split_strategy import GWOSplitStrategy  # Yeni
from strategies.pyvrp_strategy import PyVRPStrategy, PyVRPAlternativeStrategy
from strategies.vroom_strategy import VROOMStrategy, VROOMFallbackStrategy

# Registry güncelle
STRATEGY_REGISTRY = {
    # Mevcut Pipeline A
    "genetic_algorithm": _ga_strategy,
    "pso": _pso_strategy,
    "gwo": _gwo_strategy,
    "hho": _hho_strategy,
    
    # YENİ: Pipeline B (Split)
    "ga_split": GASplitStrategy(),
    "pso_split": PSOSplitStrategy(),  # Yeni
    "hho_split": HHOSplitStrategy(),  # Yeni
    "gwo_split": GWOSplitStrategy(),  # Yeni
    
    # YENİ: Bağımsız Çözücüler
    "pyvrp": PyVRPStrategy(),
    "pyvrp_alt": PyVRPAlternativeStrategy(),
    "vroom": VROOMStrategy(),
    "vroom_fallback": VROOMFallbackStrategy(),
}

# Yeni fonksiyonlar ekle
def get_available_solvers() -> dict:
    """Kurulu kütüphane durumunu döndürür"""
    
def get_recommended_strategy(n_students: int, priority: str) -> str:
    """Problem büyüklüğüne göre önerilen algoritmayı döndürür"""
```

#### Görev 1.5.2: Hybrid Base Strategy

**Dosyalar:**
- `optimizer_api/strategies/hybrid_base_strategy.py` (YENİ)

**Yapılacaklar:**
```python
from abc import abstractmethod
from strategies.base_strategy import BaseRoutingStrategy
from utils.split_decoder import SplitDecoder

class HybridSplitStrategy(BaseRoutingStrategy):
    """Tüm Split tabanlı algoritmalar için temel sınıf"""
    
    def __init__(self):
        self.split_decoder = None
    
    def optimize(self, request):
        # Split Decoder başlat
        self.split_decoder = SplitDecoder(
            sw_cap=request.sw_capacity,
            so_cap=request.so_capacity,
            max_tour_duration=request.max_travel_time
        )
        
        # Giant Tour optimizasyonu (override edilecek)
        waypoints = [s.location_code for s in request.students]
        best_tour = self._optimize_giant_tour(waypoints, request)
        
        # Split Decoder ile rotalara böl
        routes, cost = self.split_decoder.decode(best_tour, ...)
        
        # Local search uygula
        routes = [self._local_search(r) for r in routes]
        
        return self._build_response(routes, cost)
    
    @abstractmethod
    def _optimize_giant_tour(self, waypoints, request):
        """Her algoritma kendi optimizasyonunu implemente eder"""
        pass
```

#### Görev 1.5.3-1.5.6: Split Stratejileri

**Dosyalar:**
- `optimizer_api/strategies/pso_split_strategy.py` (YENİ)
- `optimizer_api/strategies/hho_split_strategy.py` (YENİ)
- `optimizer_api/strategies/gwo_split_strategy.py` (YENİ)

**PSO-Split Yapısı:**
```python
from strategies.hybrid_base_strategy import HybridSplitStrategy

class PSOSplitStrategy(HybridSplitStrategy):
    @property
    def name(self) -> str:
        return "pso_split"
    
    def _optimize_giant_tour(self, waypoints, request):
        # PSO swarm initialization (giant tour permütasyonları)
        # Velocity update (swap operations)
        # Fitness evaluation → Split decoder ile maliyet hesaplama
        pass
```

---

### Sprint 2: IE Engine Core (Hafta 1-2)

**Hedef:** Endüstri Mühendisliği kaynak yönetimi motorunu oluşturmak

#### Görev 1.5X.3: IE Resource Engine

**Dosyalar:**
- `optimizer_api/utils/resource_profiler.py` (YENİ)
- `optimizer_api/tests/test_resource_profiler.py` (YENİ)

**Sınıf Yapısı:**
```python
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from models.schemas import VehicleConfig, StudentNode

@dataclass
class ResourceBlock:
    """Araç zaman bloğu"""
    vehicle_id: str
    start_time: int  # minutes from midnight
    end_time: int
    direction: str  # 'pickup' or 'dropoff'
    students: List[str]

@dataclass
class HourlyDemand:
    """Saatlik talep"""
    hour: str  # "08:00"
    pickup_sw: int
    pickup_so: int
    dropoff_sw: int
    dropoff_so: int

class ResourceProfiler:
    """
    Endüstri Mühendisliği Kaynak Profilleme Motoru
    
    İki modda çalışır:
    1. BENCHMARK: Standart araç cinsinden teorik minimum
    2. SANDBOX: Mevcut araçlarla simülasyon
    """
    
    def __init__(
        self,
        standard_sw_capacity: int = 4,
        standard_so_capacity: int = 5,
        max_tour_duration: int = 120,
        cooldown_minutes: int = 15
    ):
        self.standard_sw_cap = standard_sw_capacity
        self.standard_so_cap = standard_so_capacity
        self.max_tour_duration = max_tour_duration
        self.cooldown = cooldown_minutes
    
    def calculate_standard_vehicle_needs(
        self,
        students: List[StudentNode],
        time_matrix: Dict,
        mode: str = 'pickup'
    ) -> Dict:
        """
        Standart minibüs (4 Sw + 5 So) cinsinden ihtiyaç hesaplama
        
        Konuşma Geçmişi Madde 21: "Standart araç cinsinden kaç adet araç gerektiğini belirlemesi"
        """
        pass
    
    def generate_hourly_demand(
        self,
        students: List[StudentNode],
        pickup_times: Dict[str, str],
        dropoff_times: Dict[str, str]
    ) -> Dict[str, HourlyDemand]:
        """
        Saatlik Sw/So talep kırılımı
        
        Konuşma Geçmişi Madde 23: "O saat dilimi için So, Sw'leri de görmek"
        """
        pass
    
    def identify_bottlenecks(
        self,
        hourly_demand: Dict[str, HourlyDemand],
        available_vehicles: List[VehicleConfig]
    ) -> List[Dict]:
        """
        Darboğaz tespiti
        
        Konuşma Geçmişi Madde 14: "Verimsiz noktaları görüp yeni koşullarla planlama"
        """
        pass
    
    def check_directional_conflict(
        self,
        vehicle_id: str,
        pickup_block: ResourceBlock,
        dropoff_block: ResourceBlock
    ) -> bool:
        """
        Yönsel çakışma kontrolü
        
        Konuşma Geçmişi Madde 19: "Aynı saat dilimi için hem toplaycı hem dağıtıcı araçlar"
        Kural: Pickup [T-120, T], Dropoff [T, T+120] - çakışma olamaz
        """
        pass
    
    def calculate_resource_blocks(
        self,
        routes: List[Dict],
        direction: str
    ) -> List[ResourceBlock]:
        """Her rota için zaman bloku hesaplama"""
        pass
    
    def suggest_time_shifts(
        self,
        hourly_demand: Dict[str, HourlyDemand],
        slack_window_minutes: int = 60
    ) -> List[Dict]:
        """
        Slack time önerileri
        
        Konuşma Geçmişi Madde 14: "Öğrencinin hareket saatini değiştirerek kaynak sayısını minimum tutma"
        """
        pass
```

#### Görev 1.5X.4: Directional Blocking

**Konuşma Geçmişi Madde 19 Gereksinimleri:**
- Aynı saat diliminde hem gelen (pickup) hem giden (dropoff) öğrenciler olacak
- Toplayıcı araçlar: Öğrenciyi alıp okula getirir (T - max_tour_time, T)
- Dağıtıcı araçlar: Okuldan öğrenciyi eve götürür (T, T + max_tour_time)
- Aynı araç aynı anda iki işlem yapamaz

**Implementasyon:**
```python
def calculate_resource_blocks(
    self,
    routes: List[Dict],
    direction: str,
    target_time: int  # minutes from midnight
) -> ResourceBlock:
    """
    Yönsel blok hesaplama
    
    Args:
        routes: Rota listesi
        direction: 'pickup' veya 'dropoff'
        target_time: Hedef saat (okula varış veya okuldan ayrılış)
    """
    if direction == 'pickup':
        # Pickup: Araç T-120'de çıkar, T'de okulda olur
        start_time = target_time - self.max_tour_duration
        end_time = target_time
    else:  # dropoff
        # Dropoff: Araç T'de okuldan çıkar, T+120'de döner
        start_time = target_time
        end_time = target_time + self.max_tour_duration
    
    return ResourceBlock(
        vehicle_id=routes[0]['vehicle_id'],
        start_time=start_time,
        end_time=end_time + self.cooldown,  # +15 dk cooldown
        direction=direction,
        students=[s['id'] for s in routes[0]['students']]
    )
```

---

### Sprint 3: IE Dashboard (Hafta 2-3)

**Hedef:** Frontend IE görselleştirme bileşenlerini oluşturmak

#### Görev 1.5X.7: Resource Histogram

**Dosyalar:**
- `src/components/admin/resource-histogram.tsx` (YENİ)

**Konuşma Geçmişi Madde 21:**
> "Zaman çizelgesi x ekseni saat olacak şekilde gidiş için ve geliş için gerekli araçlar stack edilmiş"

**Props:**
```typescript
interface ResourceHistogramProps {
  hourlyDemand: HourlyDemandData[];
  showBottlenecks?: boolean;
  onHourClick?: (hour: string) => void;
}

interface HourlyDemandData {
  hour: string;  // "08:00"
  pickupSw: number;
  pickupSo: number;
  dropoffSw: number;
  dropoffSo: number;
  totalVehiclesNeeded: number;
  isInfeasible?: boolean;
}
```

**Görsel Tasarım:**
```
Saatlik Araç İhtiyacı

08:00  ██░░░░░░░░  2 araç
       [Pickup: 2 Sw, 3 So]
       
09:00  ████░░░░░░  4 araç
       [Pickup: 4 Sw, 5 So]
       [Dropoff: 1 Sw, 2 So]
       
12:00  ██████░░░░  ⚠️ INFEASIBLE
       [6 araç gerekli, 5 mevcut]
```

#### Görev 1.5X.8: Resource Tracks (Gantt)

**Dosyalar:**
- `src/components/admin/resource-tracks.tsx` (YENİ)

**Konuşma Geçmişi Madde 21:**
> "Araç kullanım blokları da saatlik talep grafiğinin x ekseni ile hizalı olursa hangi araç hangi saat diliminde kullanılıyor net görüntülenebilir"

**Props:**
```typescript
interface ResourceTracksProps {
  vehicles: VehicleConfig[];
  blocks: ResourceBlock[];
  timeRange: { start: string; end: string };
  onBlockClick?: (block: ResourceBlock) => void;
}
```

**Görsel Tasarım:**
```
Araç Kullanım Zaman Çizelgesi

       08:00  09:00  10:00  11:00  12:00  13:00  14:00

Araç 1 [██████]      [████████]      [████]
       Pickup        Dropoff         Pickup

Araç 2      [██████]      [████████]
            Pickup        Dropoff

Araç 3           [COOLDOWN: 15dk]
```

---

### Sprint 4: Sandbox Mode (Hafta 3-4)

**Hedef:** Admin'in manuel fine-tune yapabileceği arayüz

#### Görev 1.5X.9: Sandbox Mode

**Dosyalar:**
- `src/app/(app)/admin/sandbox/page.tsx` (YENİ)
- `src/components/admin/vehicle-configurator.tsx` (YENİ)
- `src/components/admin/student-shift-dialog.tsx` (YENİ)

**Konuşma Geçmişi Madde 14:**
> "Günlük plan veriler geçici olarak güncellenerek yeniden oluşturulabilmeli, gün içi admin panelden bu fine tune edebilmeliyim"

**Özellikler:**
1. **Araç Ekleme/Çıkarma:**
   - Mevcut araçlardan seçim
   - Yeni araç tanımlama (kapasite belirleme)
   - Araç silme

2. **Öğrenci Kaydırma:**
   - Öğrenci listesi
   - Mevcut saat gösterimi
   - Yeni saat seçimi (±60 dk)
   - Etki önizlemesi ("1 araç tasarrufu")

3. **Re-optimization:**
   - Değişiklikleri uygula butonu
   - Before/After karşılaştırma
   - Yeni rota sonuçları

**Sayfa Yapısı:**
```typescript
export default function SandboxPage() {
  const [vehicles, setVehicles] = useState<VehicleConfig[]>([]);
  const [studentShifts, setStudentShifts] = useState<Shift[]>([]);
  const [originalResult, setOriginalResult] = useState<OptimizationResult>();
  const [newResult, setNewResult] = useState<OptimizationResult>();
  
  return (
    <div className="sandbox-layout">
      {/* Sol Panel: Konfigürasyon */}
      <VehicleConfigurator 
        vehicles={vehicles} 
        onChange={setVehicles} 
      />
      
      {/* Orta Panel: Öğrenci Kaydırma */}
      <StudentShiftPanel
        shifts={studentShifts}
        onChange={setStudentShifts}
      />
      
      {/* Sağ Panel: Sonuçlar */}
      <ComparisonPanel
        original={originalResult}
        optimized={newResult}
        onReoptimize={handleReoptimize}
      />
    </div>
  );
}
```

---

## 📊 API Endpoint Planı

### Yeni Endpoint'ler

```python
# GET /api/v1/resource-profile
# IE Engine'den kaynak profili al
{
    "date": "2026-03-28",
    "mode": "benchmark",  # veya "sandbox"
    "standard_vehicles_needed": 5,
    "hourly_demand": {
        "08:00": {"pickup": {"sw": 2, "so": 3}, "dropoff": {"sw": 0, "so": 0}},
        "09:00": {"pickup": {"sw": 4, "so": 5}, "dropoff": {"sw": 1, "so": 2}}
    },
    "bottlenecks": [
        {"time": "12:00", "type": "infeasible", "reason": "Sw > available"}
    ],
    "time_shift_suggestions": [
        {"student_id": "s1", "current": "12:00", "suggested": "11:00", "savings": 1}
    ]
}

# POST /api/v1/sandbox/optimize
# Sandbox modda optimizasyon
{
    "vehicles": [...],
    "student_shifts": [...],
    "original_plan_id": "uuid"
}

# GET /api/v1/directional-blocks
# Yönsel blokları görüntüle
{
    "date": "2026-03-28",
    "blocks": [
        {"vehicle_id": "v1", "start": "09:00", "end": "11:00", "direction": "pickup"},
        {"vehicle_id": "v1", "start": "14:00", "end": "16:00", "direction": "dropoff"}
    ]
}
```

---

## ✅ Test Planı

### Unit Testler

```python
# test_resource_profiler.py

def test_standard_vehicle_needs_calculation():
    """30 öğrenci → 4 minibüs (16 Sw + 14 So)"""
    pass

def test_hourly_demand_generation():
    """Saatlik Sw/So kırılımı doğru hesaplanmalı"""
    pass

def test_bottleneck_identification():
    """12:00'de 10 öğrenci, kapasite 9 → infeasible tespiti"""
    pass

def test_directional_conflict_detection():
    """Aynı araç için pickup ve dropoff çakışması"""
    pass

def test_slack_time_suggestions():
    """2 öğrenciyi kaydır → 1 araç tasarrufu"""
    pass
```

### Entegrasyon Testleri

1. **E2E Test:** vehicle-planning → IE Dashboard → Sandbox → Re-optimization
2. **Performans Test:** 300 öğrenci, 20 araç senaryosu
3. **Heterojen Filo Test:** Farklı kapasiteli araçlarla optimizasyon

---

## 📅 Zaman Çizelgesi

| Sprint | Süre | Görevler | Çıktılar |
|--------|------|----------|----------|
| Sprint 1 | Hafta 1 | Pipeline B tamamlama | PSO/HHO/GWO-Split, Registry güncelleme |
| Sprint 2 | Hafta 1-2 | IE Engine Core | resource_profiler.py, Directional Blocking |
| Sprint 3 | Hafta 2-3 | IE Dashboard | Histogram, Resource Tracks |
| Sprint 4 | Hafta 3-4 | Sandbox Mode | Fine-tune UI, Re-optimization |

---

## 🔗 Bağımlılıklar

```
Sprint 1 (Pipeline B)
    └── Registry güncelleme
        └──
Sprint 2 (IE Engine)
    ├── schemas.py (tanımlı)
    ├── split_decoder.py (tanımlı)
    └── resource_profiler.py (yeni)
        └──
Sprint 3 (Dashboard)
    ├── ResourceHistogram
    └── ResourceTracks
        └──
Sprint 4 (Sandbox)
    └── Sandbox Mode
```

---

*Bu plan 28 Mart 2026 tarihinde kod yapısı ve dokümanlar analiz edilerek hazırlanmıştır.*
