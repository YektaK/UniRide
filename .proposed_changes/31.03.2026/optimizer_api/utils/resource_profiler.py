"""
IE Resource Profiler - Endüstri Mühendisliği Kaynak Yönetimi Motoru

Bu modül, UniRide sisteminin kaynak planlama ve optimizasyon yeteneklerini sağlar:
- Standart araç ihtiyacı hesaplama
- Saatlik talep analizi (Sw/So kırılımı)
- Darboğaz tespiti
- Yönsel bloklama (Directional Blocking)
- Zaman kaydırma önerileri (Slack Time)

Referanslar:
- IE_RESOURCE_MODEL.md
- Konuşma Geçmişi Madde 14, 19, 21, 23
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from models.schemas import VehicleConfig, StudentNode

logger = logging.getLogger(__name__)


@dataclass
class ResourceBlock:
    """Araç zaman bloğu - bir aracın belirli bir zaman aralığındaki kullanımı"""
    vehicle_id: str
    start_time: int  # minutes from midnight (0-1440)
    end_time: int    # minutes from midnight (0-1440)
    direction: str   # 'pickup' veya 'dropoff'
    students: List[str] = field(default_factory=list)
    sw_count: int = 0
    so_count: int = 0


@dataclass
class HourlyDemand:
    """Saatlik talep verisi"""
    hour: str  # "08:00" format
    pickup_sw: int = 0
    pickup_so: int = 0
    dropoff_sw: int = 0
    dropoff_so: int = 0

    @property
    def total_pickup(self) -> int:
        return self.pickup_sw + self.pickup_so

    @property
    def total_dropoff(self) -> int:
        return self.dropoff_sw + self.dropoff_so

    @property
    def total_sw(self) -> int:
        return self.pickup_sw + self.dropoff_sw

    @property
    def total_so(self) -> int:
        return self.pickup_so + self.dropoff_so


@dataclass
class Bottleneck:
    """Darboğaz bilgisi"""
    hour: str
    type: str  # 'infeasible', 'low_efficiency', 'resource_conflict'
    severity: str  # 'high', 'medium', 'low'
    description: str
    sw_needed: int = 0
    so_needed: int = 0
    sw_available: int = 0
    so_available: int = 0
    vehicles_needed: int = 0
    vehicles_available: int = 0


@dataclass
class TimeShiftSuggestion:
    """Zaman kaydırma önerisi"""
    student_id: str
    student_name: str
    current_time: str
    suggested_time: str
    shift_minutes: int
    reason: str
    savings_vehicles: int = 0


class ResourceProfiler:
    """
    Endüstri Mühendisliği Kaynak Profilleme Motoru

    İki modda çalışır:
    1. BENCHMARK: Standart araç cinsinden teorik minimum
    2. SANDBOX: Mevcut araçlarla simülasyon

    Attributes:
        standard_sw_capacity: Standart minibüs Sw kapasitesi (default: 4)
        standard_so_capacity: Standart minibüs So kapasitesi (default: 5)
        max_tour_duration: Maksimum tur süresi dakika (default: 120)
        cooldown_minutes: Rotalar arası bekleme süresi (default: 15)
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

        logger.info(
            f"ResourceProfiler initialized: "
            f"standard_vehicle={standard_sw_capacity}Sw+{standard_so_capacity}So, "
            f"max_tour={max_tour_duration}min, cooldown={cooldown_minutes}min"
        )

    def calculate_standard_vehicle_needs(
        self,
        students: List[StudentNode],
        mode: str = 'pickup'
    ) -> Dict:
        """
        Standart minibüs (4 Sw + 5 So) cinsinden araç ihtiyacı hesaplama

        Konuşma Geçmişi Madde 21: "Standart araç cinsinden kaç adet araç gerektiğini belirlemesi"

        Args:
            students: Öğrenci listesi
            mode: 'pickup' veya 'dropoff' veya 'both'

        Returns:
            {
                'total_students': int,
                'sw_count': int,
                'so_count': int,
                'standard_vehicles_needed': int,
                'by_capacity': {
                    'by_sw': int,  # Sw kapasitesine göre
                    'by_so': int,  # So kapasitesine göre
                    'by_combined': int  # Karma (4Sw+5So)
                },
                'utilization_percent': float  # Doluluk oranı
            }
        """
        # Öğrenci sayıları
        sw_count = sum(1 for s in students if s.disability_type == 'Sw')
        so_count = len(students) - sw_count
        total = len(students)

        # Kapasiteye göre hesaplama
        by_sw = (sw_count + self.standard_sw_cap - 1) // self.standard_sw_cap if self.standard_sw_cap > 0 else 0
        by_so = (so_count + self.standard_so_cap - 1) // self.standard_so_cap if self.standard_so_cap > 0 else 0

        # Kombine hesaplama (gerçekçi: her araç hem Sw hem So taşıyabilir)
        # En az araç sayısı = max(Sw ihtiyacı, So ihtiyacı) ama kombinasyon mümkün
        standard_vehicles = max(by_sw, by_so)

        # Doluluk oranı
        total_capacity_sw = standard_vehicles * self.standard_sw_cap
        total_capacity_so = standard_vehicles * self.standard_so_cap
        utilization_sw = (sw_count / total_capacity_sw * 100) if total_capacity_sw > 0 else 0
        utilization_so = (so_count / total_capacity_so * 100) if total_capacity_so > 0 else 0
        avg_utilization = (utilization_sw + utilization_so) / 2

        result = {
            'total_students': total,
            'sw_count': sw_count,
            'so_count': so_count,
            'standard_vehicles_needed': standard_vehicles,
            'by_capacity': {
                'by_sw': by_sw,
                'by_so': by_so,
                'max_needed': max(by_sw, by_so)
            },
            'utilization_percent': round(avg_utilization, 1),
            'utilization_breakdown': {
                'sw': round(utilization_sw, 1),
                'so': round(utilization_so, 1)
            }
        }

        logger.debug(f"Standard vehicle needs: {result}")
        return result

    def generate_hourly_demand(
        self,
        students: List[StudentNode],
        pickup_times: Optional[Dict[str, str]] = None,
        dropoff_times: Optional[Dict[str, str]] = None,
        time_range: Tuple[int, int] = (6, 22)  # 06:00 - 22:00
    ) -> Dict[str, HourlyDemand]:
        """
        Saatlik Sw/So talep kırılımı

        Konuşma Geçmişi Madde 23: "O saat dilimi için So, Sw'leri de görmek"

        Args:
            students: Öğrenci listesi
            pickup_times: {student_id: "HH:MM"} - Geliş saatleri
            dropoff_times: {student_id: "HH:MM"} - Dönüş saatleri
            time_range: (start_hour, end_hour) - Analiz saat aralığı

        Returns:
            {"08:00": HourlyDemand, "09:00": HourlyDemand, ...}
        """
        demand = {}

        # Saat aralığı oluştur
        for hour in range(time_range[0], time_range[1] + 1):
            hour_str = f"{hour:02d}:00"
            demand[hour_str] = HourlyDemand(hour=hour_str)

        # Pickup talepleri
        if pickup_times:
            for student in students:
                time_str = pickup_times.get(student.id)
                if time_str:
                    hour_key = time_str[:2] + ":00"
                    if hour_key in demand:
                        if student.disability_type == 'Sw':
                            demand[hour_key].pickup_sw += 1
                        else:
                            demand[hour_key].pickup_so += 1

        # Dropoff talepleri
        if dropoff_times:
            for student in students:
                time_str = dropoff_times.get(student.id)
                if time_str:
                    hour_key = time_str[:2] + ":00"
                    if hour_key in demand:
                        if student.disability_type == 'Sw':
                            demand[hour_key].dropoff_sw += 1
                        else:
                            demand[hour_key].dropoff_so += 1

        logger.debug(f"Hourly demand generated for {len(demand)} hours")
        return demand

    def identify_bottlenecks(
        self,
        hourly_demand: Dict[str, HourlyDemand],
        available_vehicles: List[VehicleConfig],
        mode: str = 'pickup'
    ) -> List[Bottleneck]:
        """
        Darboğaz tespiti

        Konuşma Geçmişi Madde 14: "Verimsiz noktaları görüp yeni koşullarla planlama"

        Args:
            hourly_demand: Saatlik talep verisi
            available_vehicles: Mevcut araç listesi
            mode: 'pickup', 'dropoff', veya 'both'

        Returns:
            Bottleneck listesi
        """
        bottlenecks = []

        # Toplam mevcut kapasite
        total_sw_cap = sum(v.sw_capacity for v in available_vehicles)
        total_so_cap = sum(v.so_capacity for v in available_vehicles)
        total_vehicles = len(available_vehicles)

        for hour, demand in hourly_demand.items():
            # Talep hesapla
            if mode == 'pickup':
                sw_needed = demand.pickup_sw
                so_needed = demand.pickup_so
            elif mode == 'dropoff':
                sw_needed = demand.dropoff_sw
                so_needed = demand.dropoff_so
            else:  # both
                sw_needed = demand.total_sw
                so_needed = demand.total_so

            # Araç sayısı ihtiyacı (standart araç cinsinden)
            vehicles_by_sw = (sw_needed + self.standard_sw_cap - 1) // self.standard_sw_cap
            vehicles_by_so = (so_needed + self.standard_so_cap - 1) // self.standard_so_cap
            vehicles_needed = max(vehicles_by_sw, vehicles_by_so)

            # Darboğaz kontrolü
            is_infeasible = sw_needed > total_sw_cap or so_needed > total_so_cap
            is_over_capacity = vehicles_needed > total_vehicles

            if is_infeasible or is_over_capacity:
                severity = 'high' if is_infeasible else 'medium'

                if is_infeasible:
                    description = f"Kapasite yetersiz: Sw={sw_needed}/{total_sw_cap}, So={so_needed}/{total_so_cap}"
                else:
                    description = f"Araç yetersiz: {vehicles_needed} gerekli, {total_vehicles} mevcut"

                bottleneck = Bottleneck(
                    hour=hour,
                    type='infeasible' if is_infeasible else 'resource_conflict',
                    severity=severity,
                    description=description,
                    sw_needed=sw_needed,
                    so_needed=so_needed,
                    sw_available=total_sw_cap,
                    so_available=total_so_cap,
                    vehicles_needed=vehicles_needed,
                    vehicles_available=total_vehicles
                )
                bottlenecks.append(bottleneck)
                logger.warning(f"Bottleneck detected at {hour}: {description}")

            # Düşük verimlilik kontrolü (< 50% doluluk)
            elif vehicles_needed > 0:
                utilization = (sw_needed + so_needed) / (vehicles_needed * (self.standard_sw_cap + self.standard_so_cap))
                if utilization < 0.5:
                    bottleneck = Bottleneck(
                        hour=hour,
                        type='low_efficiency',
                        severity='low',
                        description=f"Düşük verimlilik: {utilization*100:.0f}% doluluk",
                        sw_needed=sw_needed,
                        so_needed=so_needed,
                        sw_available=total_sw_cap,
                        so_available=total_so_cap,
                        vehicles_needed=vehicles_needed,
                        vehicles_available=total_vehicles
                    )
                    bottlenecks.append(bottleneck)

        return sorted(bottlenecks, key=lambda x: x.hour)

    def calculate_resource_blocks(
        self,
        routes: List[Dict],
        direction: str,
        target_times: Optional[Dict[str, str]] = None
    ) -> List[ResourceBlock]:
        """
        Her rota için zaman bloku hesaplama

        Yönsel bloklama mantığı:
        - Pickup: Araç [T-120, T] arasında çalışır (okula varış T)
        - Dropoff: Araç [T, T+120] arasında çalışır (okuldan ayrılış T)

        Args:
            routes: Rota listesi
            direction: 'pickup' veya 'dropoff'
            target_times: {route_id: "HH:MM"} - Hedef saatler

        Returns:
            ResourceBlock listesi
        """
        blocks = []

        for i, route in enumerate(routes):
            vehicle_id = route.get('vehicle_id', f'vehicle_{i}')

            # Hedef saat belirle
            if target_times and vehicle_id in target_times:
                target_time_str = target_times[vehicle_id]
                hour, minute = map(int, target_time_str.split(':'))
                target_minutes = hour * 60 + minute
            else:
                # Varsayılan: sabah 09:00 pickup, akşam 17:00 dropoff
                target_minutes = 9 * 60 if direction == 'pickup' else 17 * 60

            # Blok sürelerini hesapla
            if direction == 'pickup':
                # Pickup: T-120'de başlar, T'de biter
                start_time = target_minutes - self.max_tour_duration
                end_time = target_minutes
            else:  # dropoff
                # Dropoff: T'de başlar, T+120'de biter
                start_time = target_minutes
                end_time = target_minutes + self.max_tour_duration

            # Cooldown ekle
            end_time += self.cooldown

            # Öğrenci sayıları
            students = route.get('students', [])
            sw_count = sum(1 for s in students if isinstance(s, dict) and s.get('disability_type') == 'Sw')
            so_count = len(students) - sw_count

            block = ResourceBlock(
                vehicle_id=vehicle_id,
                start_time=start_time,
                end_time=end_time,
                direction=direction,
                students=[s.get('id', str(s)) for s in students] if isinstance(students[0], dict) else [str(s) for s in students],
                sw_count=sw_count,
                so_count=so_count
            )
            blocks.append(block)

        logger.debug(f"Calculated {len(blocks)} resource blocks for {direction}")
        return blocks

    def check_directional_conflict(
        self,
        pickup_block: ResourceBlock,
        dropoff_block: ResourceBlock,
        same_vehicle: bool = True
    ) -> bool:
        """
        Yönsel çakışma kontrolü

        Konuşma Geçmişi Madde 19: "Aynı saat dilimi için hem toplayıcı hem dağıtıcı araçlar"
        Kural: Pickup [T-120, T], Dropoff [T, T+120] - çakışma olamaz

        Args:
            pickup_block: Pickup zaman bloğu
            dropoff_block: Dropoff zaman bloğu
            same_vehicle: Aynı araç için mi kontrol ediliyor

        Returns:
            True if conflict exists, False otherwise
        """
        # Aynı araç değilse çakışma yok
        if same_vehicle and pickup_block.vehicle_id != dropoff_block.vehicle_id:
            return False

        # Zaman çakışması kontrolü
        # Çakışma varsa: pickup bitiş > dropoff başlangıç VE dropoff bitiş > pickup başlangıç
        overlap = (
            pickup_block.end_time > dropoff_block.start_time and
            dropoff_block.end_time > pickup_block.start_time
        )

        if overlap:
            logger.warning(
                f"Directional conflict: {pickup_block.vehicle_id} "
                f"pickup[{pickup_block.start_time}-{pickup_block.end_time}] vs "
                f"dropoff[{dropoff_block.start_time}-{dropoff_block.end_time}]"
            )

        return overlap

    def suggest_time_shifts(
        self,
        hourly_demand: Dict[str, HourlyDemand],
        bottleneck_hours: List[str],
        slack_window_minutes: int = 60,
        shift_increment_minutes: int = 30
    ) -> List[TimeShiftSuggestion]:
        """
        Slack time önerileri

        Konuşma Geçmişi Madde 14: "Öğrencinin hareket saatini değiştirerek kaynak sayısını minimum tutma"

        Args:
            hourly_demand: Saatlik talep verisi
            bottleneck_hours: Darboğaz saatleri
            slack_window_minutes: Maksimum kaydırma süresi (±)
            shift_increment_minutes: Kaydırma adımı

        Returns:
            TimeShiftSuggestion listesi
        """
        suggestions = []

        for hour_str in bottleneck_hours:
            if hour_str not in hourly_demand:
                continue

            demand = hourly_demand[hour_str]
            hour = int(hour_str.split(':')[0])

            # Öneri: Pickup talebini komşu saatlere kaydır
            if demand.total_pickup > self.standard_sw_cap + self.standard_so_cap:
                # Öğrenci sayısı fazla, kaydırma öner
                excess = demand.total_pickup - (self.standard_sw_cap + self.standard_so_cap)

                # Önceki saat kontrolü
                prev_hour = f"{hour - 1:02d}:00"
                if prev_hour in hourly_demand:
                    prev_demand = hourly_demand[prev_hour]
                    if prev_demand.total_pickup < self.standard_sw_cap + self.standard_so_cap:
                        # Önceki saat müsait
                        suggestions.append(TimeShiftSuggestion(
                            student_id=f"students_at_{hour_str}",
                            student_name=f"{excess} öğrenci",
                            current_time=hour_str,
                            suggested_time=prev_hour,
                            shift_minutes=-60,
                            reason=f"{hour_str} saatinde kapasite aşımı, bir önceki saat müsait",
                            savings_vehicles=1
                        ))

                # Sonraki saat kontrolü
                next_hour = f"{hour + 1:02d}:00"
                if next_hour in hourly_demand:
                    next_demand = hourly_demand[next_hour]
                    if next_demand.total_pickup < self.standard_sw_cap + self.standard_so_cap:
                        suggestions.append(TimeShiftSuggestion(
                            student_id=f"students_at_{hour_str}",
                            student_name=f"{excess} öğrenci",
                            current_time=hour_str,
                            suggested_time=next_hour,
                            shift_minutes=60,
                            reason=f"{hour_str} saatinde kapasite aşımı, bir sonraki saat müsait",
                            savings_vehicles=1
                        ))

        logger.info(f"Generated {len(suggestions)} time shift suggestions")
        return suggestions

    def analyze_resource_utilization(
        self,
        blocks: List[ResourceBlock],
        available_vehicles: List[VehicleConfig],
        time_range: Tuple[int, int] = (6, 22)
    ) -> Dict:
        """
        Kaynak kullanım analizi

        Args:
            blocks: Tüm zaman blokları (pickup + dropoff)
            available_vehicles: Mevcut araç listesi
            time_range: Analiz saat aralığı

        Returns:
            Kullanım istatistikleri
        """
        total_minutes = (time_range[1] - time_range[0]) * 60
        vehicle_usage = {v.vehicle_id: 0 for v in available_vehicles}

        for block in blocks:
            if block.vehicle_id in vehicle_usage:
                duration = block.end_time - block.start_time
                vehicle_usage[block.vehicle_id] += duration

        # İstatistikler
        usage_percentages = {
            vid: (minutes / total_minutes * 100)
            for vid, minutes in vehicle_usage.items()
        }

        avg_utilization = sum(usage_percentages.values()) / len(usage_percentages) if usage_percentages else 0

        return {
            'average_utilization_percent': round(avg_utilization, 1),
            'vehicle_usage_minutes': vehicle_usage,
            'vehicle_usage_percent': {vid: round(pct, 1) for vid, pct in usage_percentages.items()},
            'total_operating_hours': sum(vehicle_usage.values()) / 60,
            'idle_vehicle_count': sum(1 for pct in usage_percentages.values() if pct < 10)
        }

    def generate_ie_report(
        self,
        students: List[StudentNode],
        available_vehicles: List[VehicleConfig],
        pickup_times: Optional[Dict[str, str]] = None,
        dropoff_times: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Tam IE analiz raporu

        Args:
            students: Öğrenci listesi
            available_vehicles: Mevcut araç listesi
            pickup_times: Geliş saatleri
            dropoff_times: Dönüş saatleri

        Returns:
            Kapsamlı IE raporu
        """
        # 1. Standart araç ihtiyacı
        standard_needs = self.calculate_standard_vehicle_needs(students)

        # 2. Saatlik talep
        hourly_demand = self.generate_hourly_demand(
            students, pickup_times, dropoff_times
        )

        # 3. Darboğazlar
        bottlenecks = self.identify_bottlenecks(
            hourly_demand, available_vehicles, mode='both'
        )

        # 4. Zaman kaydırma önerileri
        bottleneck_hours = [b.hour for b in bottlenecks if b.severity in ['high', 'medium']]
        shift_suggestions = self.suggest_time_shifts(
            hourly_demand, bottleneck_hours
        )

        # 5. Özet
        report = {
            'summary': {
                'total_students': len(students),
                'available_vehicles': len(available_vehicles),
                'standard_vehicles_needed': standard_needs['standard_vehicles_needed'],
                'bottleneck_count': len(bottlenecks),
                'shift_suggestions_count': len(shift_suggestions)
            },
            'standard_needs': standard_needs,
            'hourly_demand': {
                hour: {
                    'pickup_sw': d.pickup_sw,
                    'pickup_so': d.pickup_so,
                    'dropoff_sw': d.dropoff_sw,
                    'dropoff_so': d.dropoff_so,
                    'total_pickup': d.total_pickup,
                    'total_dropoff': d.total_dropoff
                }
                for hour, d in hourly_demand.items()
            },
            'bottlenecks': [
                {
                    'hour': b.hour,
                    'type': b.type,
                    'severity': b.severity,
                    'description': b.description,
                    'sw_needed': b.sw_needed,
                    'so_needed': b.so_needed,
                    'vehicles_needed': b.vehicles_needed
                }
                for b in bottlenecks
            ],
            'shift_suggestions': [
                {
                    'student_id': s.student_id,
                    'student_name': s.student_name,
                    'current_time': s.current_time,
                    'suggested_time': s.suggested_time,
                    'shift_minutes': s.shift_minutes,
                    'reason': s.reason,
                    'savings_vehicles': s.savings_vehicles
                }
                for s in shift_suggestions
            ]
        }

        logger.info(
            f"IE Report generated: {report['summary']['total_students']} students, "
            f"{report['summary']['bottleneck_count']} bottlenecks"
        )

        return report


# Utility functions
def minutes_to_time_str(minutes: int) -> str:
    """Dakikayı HH:MM formatına çevir"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def time_str_to_minutes(time_str: str) -> int:
    """HH:MM formatını dakikaya çevir"""
    hour, minute = map(int, time_str.split(':'))
    return hour * 60 + minute
