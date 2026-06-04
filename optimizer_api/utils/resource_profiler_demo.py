"""
IE Resource Profiler Demo Script

Bu script, ResourceProfiler'ın temel kullanımını gösterir.
Gerçek verilerle çalışmak için temel bir örnek.

Kullanım:
    cd optimizer_api
    python utils/resource_profiler_demo.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.resource_profiler import ResourceProfiler
from models.schemas import StudentNode, VehicleConfig
from typing import List


def create_sample_students() -> List[StudentNode]:
    """Örnek öğrenci verisi oluştur"""
    students = []

    # 8 Sw (wheelchair) öğrenci
    for i in range(8):
        students.append(StudentNode(
            id=f"sw_{i+1}",
            name=f"Sw Öğrenci {i+1}",
            location_code=f"Sw{i+1}",
            coordinates={"lat": 40.84 + i*0.001, "lng": 31.15 + i*0.001},
            disability_type="Sw"
        ))

    # 12 So (other) öğrenci
    for i in range(12):
        students.append(StudentNode(
            id=f"so_{i+1}",
            name=f"So Öğrenci {i+1}",
            location_code=f"So{i+1}",
            coordinates={"lat": 40.85 + i*0.001, "lng": 31.16 + i*0.001},
            disability_type="So"
        ))

    return students


def create_sample_vehicles() -> List[VehicleConfig]:
    """Örnek araç verisi oluştur"""
    return [
        VehicleConfig(vehicle_id="Minibüs-1", sw_capacity=4, so_capacity=5),
        VehicleConfig(vehicle_id="Minibüs-2", sw_capacity=4, so_capacity=5),
        VehicleConfig(vehicle_id="Van-1", sw_capacity=2, so_capacity=3),
    ]


def create_sample_schedules(students: List[StudentNode]):
    """Örnek zamanlama verisi oluştur"""
    pickup_times = {}
    dropoff_times = {}

    # Sabah 08:00-09:00 arası pickup
    for i, student in enumerate(students[:10]):  # İlk 10 öğrenci
        pickup_times[student.id] = f"08:{30 + i*3:02d}"  # 08:30, 08:33, ...

    for i, student in enumerate(students[10:]):  # Kalan öğrenciler
        pickup_times[student.id] = f"09:{i*5:02d}"  # 09:00, 09:05, ...

    # Akşam 17:00-18:00 arası dropoff
    for i, student in enumerate(students):
        dropoff_times[student.id] = f"{17 + i//10}:{(i%10)*5:02d}"

    return pickup_times, dropoff_times


def demo_standard_vehicle_needs():
    """Demo: Standart araç ihtiyacı hesaplama"""
    print("=" * 60)
    print("DEMO 1: Standart Araç İhtiyacı Hesaplama")
    print("=" * 60)

    students = create_sample_students()
    profiler = ResourceProfiler()

    result = profiler.calculate_standard_vehicle_needs(students)

    print(f"\nToplam Öğrenci: {result['total_students']}")
    print(f"  - Sw (Tekerlekli Sandalye): {result['sw_count']}")
    print(f"  - So (Diğer): {result['so_count']}")
    print(f"\nStandart Araç İhtiyacı: {result['standard_vehicles_needed']} minibüs")
    print(f"  - Sw kapasitesine göre: {result['by_capacity']['by_sw']} araç")
    print(f"  - So kapasitesine göre: {result['by_capacity']['by_so']} araç")
    print(f"\nOrtalama Doluluk: %{result['utilization_percent']}")
    print(f"  - Sw doluluk: %{result['utilization_breakdown']['sw']}")
    print(f"  - So doluluk: %{result['utilization_breakdown']['so']}")


def demo_hourly_demand():
    """Demo: Saatlik talep analizi"""
    print("\n" + "=" * 60)
    print("DEMO 2: Saatlik Talep Analizi (Sw/So Kırılımı)")
    print("=" * 60)

    students = create_sample_students()
    profiler = ResourceProfiler()

    pickup_times, dropoff_times = create_sample_schedules(students)

    hourly_demand = profiler.generate_hourly_demand(
        students, pickup_times, dropoff_times
    )

    print("\nSaatlik Talep:")
    print("-" * 60)
    print(f"{'Saat':<10} {'Pickup Sw':<12} {'Pickup So':<12} {'Dropoff Sw':<12} {'Dropoff So':<12}")
    print("-" * 60)

    for hour in sorted(hourly_demand.keys()):
        d = hourly_demand[hour]
        if d.total_pickup > 0 or d.total_dropoff > 0:
            print(f"{hour:<10} {d.pickup_sw:<12} {d.pickup_so:<12} {d.dropoff_sw:<12} {d.dropoff_so:<12}")


def demo_bottleneck_detection():
    """Demo: Darboğaz tespiti"""
    print("\n" + "=" * 60)
    print("DEMO 3: Darboğaz Tespiti")
    print("=" * 60)

    students = create_sample_students()
    vehicles = create_sample_vehicles()
    profiler = ResourceProfiler()

    # 20 öğrenciyi aynı saatte planla (darboğaz oluştur)
    pickup_times = {s.id: "09:00" for s in students[:20]}

    hourly_demand = profiler.generate_hourly_demand(students, pickup_times, {})
    bottlenecks = profiler.identify_bottlenecks(hourly_demand, vehicles, 'pickup')

    if bottlenecks:
        print(f"\n⚠️  {len(bottlenecks)} darboğaz tespit edildi:")
        for b in bottlenecks:
            print(f"\n  Saat: {b.hour}")
            print(f"  Tip: {b.type}")
            print(f"  Şiddet: {b.severity}")
            print(f"  Açıklama: {b.description}")
            print(f"  İhtiyaç: Sw={b.sw_needed}, So={b.so_needed}")
            print(f"  Mevcut: Sw={b.sw_available}, So={b.so_available}")
    else:
        print("\n✅ Darboğaz tespit edilmedi.")


def demo_directional_blocking():
    """Demo: Yönsel bloklama"""
    print("\n" + "=" * 60)
    print("DEMO 4: Yönsel Bloklama (Directional Blocking)")
    print("=" * 60)

    profiler = ResourceProfiler(max_tour_duration=120, cooldown_minutes=15)

    # Örnek rotalar
    pickup_routes = [
        {'vehicle_id': 'Minibüs-1', 'students': [{'id': 's1', 'disability_type': 'Sw'}]},
    ]
    dropoff_routes = [
        {'vehicle_id': 'Minibüs-1', 'students': [{'id': 's1', 'disability_type': 'Sw'}]},
    ]

    # Pickup bloğu: 09:00'da okula varış
    pickup_blocks = profiler.calculate_resource_blocks(
        pickup_routes, 'pickup', {'Minibüs-1': '09:00'}
    )

    # Dropoff bloğu: 09:30'da okuldan ayrılış (çakışacak)
    dropoff_blocks_conflict = profiler.calculate_resource_blocks(
        dropoff_routes, 'dropoff', {'Minibüs-1': '09:30'}
    )

    # Dropoff bloğu: 12:00'da okuldan ayrılış (çakışmayacak)
    dropoff_blocks_ok = profiler.calculate_resource_blocks(
        dropoff_routes, 'dropoff', {'Minibüs-1': '12:00'}
    )

    print("\nPickup Bloğu (Minibüs-1, 09:00 okula varış):")
    for b in pickup_blocks:
        print(f"  Başlangıç: {b.start_time//60:02d}:{b.start_time%60:02d}")
        print(f"  Bitiş: {b.end_time//60:02d}:{b.end_time%60:02d}")

    print("\nDropoff Bloğu (Minibüs-1, 09:30 okuldan ayrılış):")
    for b in dropoff_blocks_conflict:
        print(f"  Başlangıç: {b.start_time//60:02d}:{b.start_time%60:02d}")
        print(f"  Bitiş: {b.end_time//60:02d}:{b.end_time%60:02d}")

    conflict = profiler.check_directional_conflict(
        pickup_blocks[0], dropoff_blocks_conflict[0]
    )
    print(f"\n  Çakışma Durumu: {'⚠️  ÇAKIŞMA VAR!' if conflict else '✅ Çakışma yok'}")

    print("\nDropoff Bloğu (Minibüs-1, 12:00 okuldan ayrılış):")
    for b in dropoff_blocks_ok:
        print(f"  Başlangıç: {b.start_time//60:02d}:{b.start_time%60:02d}")
        print(f"  Bitiş: {b.end_time//60:02d}:{b.end_time%60:02d}")

    conflict_ok = profiler.check_directional_conflict(
        pickup_blocks[0], dropoff_blocks_ok[0]
    )
    print(f"\n  Çakışma Durumu: {'⚠️  ÇAKIŞMA VAR!' if conflict_ok else '✅ Çakışma yok'}")


def demo_time_shift_suggestions():
    """Demo: Zaman kaydırma önerileri"""
    print("\n" + "=" * 60)
    print("DEMO 5: Zaman Kaydırma Önerileri (Slack Time)")
    print("=" * 60)

    students = create_sample_students()
    vehicles = create_sample_vehicles()
    profiler = ResourceProfiler()

    # Darboğazlı program oluştur
    pickup_times = {}
    for i, student in enumerate(students[:15]):  # İlk 15 öğrenci
        pickup_times[student.id] = "09:00"  # Hepsi aynı saatte

    for i, student in enumerate(students[15:]):
        pickup_times[student.id] = "10:00"

    hourly_demand = profiler.generate_hourly_demand(students, pickup_times, {})
    bottlenecks = profiler.identify_bottlenecks(hourly_demand, vehicles, 'pickup')

    bottleneck_hours = [b.hour for b in bottlenecks]
    suggestions = profiler.suggest_time_shifts(hourly_demand, bottleneck_hours)

    if suggestions:
        print(f"\n💡 {len(suggestions)} zaman kaydırma önerisi:")
        for s in suggestions:
            print(f"\n  {s.student_name}")
            print(f"  Mevcut: {s.current_time} → Öneri: {s.suggested_time}")
            print(f"  Kaydırma: {s.shift_minutes:+d} dakika")
            print(f"  Neden: {s.reason}")
            if s.savings_vehicles > 0:
                print(f"  Tasarruf: {s.savings_vehicles} araç")
    else:
        print("\n✅ Zaman kaydırma önerisi yok.")


def demo_full_ie_report():
    """Demo: Tam IE raporu"""
    print("\n" + "=" * 60)
    print("DEMO 6: Tam IE Analiz Raporu")
    print("=" * 60)

    students = create_sample_students()
    vehicles = create_sample_vehicles()
    pickup_times, dropoff_times = create_sample_schedules(students)

    profiler = ResourceProfiler()
    report = profiler.generate_ie_report(
        students, vehicles, pickup_times, dropoff_times
    )

    print("\n📊 ÖZET:")
    print(f"  Toplam Öğrenci: {report['summary']['total_students']}")
    print(f"  Mevcut Araç: {report['summary']['available_vehicles']}")
    print(f"  Standart Araç İhtiyacı: {report['summary']['standard_vehicles_needed']}")
    print(f"  Darboğaz Sayısı: {report['summary']['bottleneck_count']}")
    print(f"  Kaydırma Önerisi: {report['summary']['shift_suggestions_count']}")

    if report['bottlenecks']:
        print("\n⚠️  DARBOĞAZLAR:")
        for b in report['bottlenecks'][:3]:  # İlk 3
            print(f"  {b['hour']}: {b['description']}")

    if report['shift_suggestions']:
        print("\n💡 ZAMAN KAYDIRMA ÖNERİLERİ:")
        for s in report['shift_suggestions'][:3]:
            print(f"  {s['student_name']}: {s['current_time']} → {s['suggested_time']}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("IE RESOURCE PROFILER - DEMO")
    print("Endüstri Mühendisliği Kaynak Yönetimi Motoru")
    print("=" * 60)

    demo_standard_vehicle_needs()
    demo_hourly_demand()
    demo_bottleneck_detection()
    demo_directional_blocking()
    demo_time_shift_suggestions()
    demo_full_ie_report()

    print("\n" + "=" * 60)
    print("Demo tamamlandı!")
    print("=" * 60)
