# CVRPTW Veritabanı Entegrasyon Planı

> **Tarih:** 30 Mart 2026
> **Durum:** Analiz Tamamlandı - Implementasyona Hazır

---

## 1. Veritabanı Yapısı Özeti

### 1.1. Mevcut Tablolar

| Tablo | Amaç | CVRPTW İlişkisi |
|-------|------|-----------------|
| `users` | Öğrenci bilgileri | disability_type, location_code |
| `weekly_schedules` | Ders programları | Time window kaynağı |
| `ride_requests` | Taşıma talepleri | Pickup/dropoff time'lar |
| `vehicles` | Araç bilgileri | Heterogeneous fleet |
| `time_matrix` | Seyahat süreleri | Distance/duration matrix |
| `route_plans` | Optimizasyon sonuçları | direction, routes JSON |

### 1.2. weekly_schedules.entries Formatı

```json
{
  "id": "entry_xxx",
  "dayOfWeek": "monday",
  "startTime": "09:00",
  "endTime": "14:00",
  "location": "Dogus Kampus",
  "courseName": "Ders Programı"
}
```

**Alanlar:**
- `dayOfWeek`: monday, tuesday, wednesday, thursday, friday
- `startTime`: Ders başlangıç saati (HH:MM) → **Pickup hedef varış saati**
- `endTime`: Ders bitiş saati (HH:MM) → **Dropoff başlangıç saati**
- `location`: Okul lokasyonu (Dogus Kampus → D.Kampus)

---

## 2. Time Window Extraction Mantığı

### 2.1. Pickup (Geliş) için

```
Input: weekly_schedules.entry.startTime = "09:00"

Time Window Hesaplama:
1. Hedef Varış Saati = startTime = 09:00 (öğrenci derste)
2. Latest Arrival (l_i) = 09:00 (geç kalma yok)
3. Earliest Arrival (e_i) = 08:30 (30dk önce varış kabul edilebilir)

Backward Scheduling:
- Tur süresi tahmini = 90 dk (örnek)
- Araç çıkış saati = 09:00 - 90dk = 07:30
- Offset eklenmiş = 07:20 (şoför bildirimi)
```

### 2.2. Dropoff (Gidiş) için

```
Input: weekly_schedules.entry.endTime = "14:00"

Time Window Hesaplama:
1. Okuldan Ayrılma Saati = endTime'i sonraki tam saate yuvarla
   - 14:00 → 14:00 (tam saat)
   - 14:50 → 15:00 (yuvarlama)
2. Earliest Departure (e_i) = 14:00
3. Latest Dropoff (l_i) = 18:00 (esnek pencere)

Forward Scheduling:
- Tur süresi tahmini = rota bazlı hesaplanır
- Her durak için varış saati hesaplanır
```

### 2.3. Time Window Formatı (Python için)

```python
# Time window dict formatı
time_windows = {
    "location_code": (earliest_minutes, latest_minutes)
}

# Örnek: Sw1 için 09:00'da okulda olmalı
# 09:00 = 540 dakika (gece yarısından itibaren)
time_windows = {
    "Sw1": (510, 540),  # 08:30 - 09:00 (30dk pencere)
    "Sw2": (510, 540),
    "So3": (510, 540),
}
```

---

## 3. Günlük Planlama Akışı

### 3.1. Akşam Optimizasyonu (Her Gece)

```
1. Fetch weekly_schedules for next day
   - dayOfWeek = tomorrow's day name
   - Join with users to get location_code, disability_type

2. Build student list with time windows
   - For each entry: extract startTime, endTime
   - Calculate time_windows dict

3. Run optimization
   - Direction = "pickup" → backward scheduling
   - Direction = "dropoff" → forward scheduling

4. Save to route_plans
   - direction, routes JSON, status = "draft"
```

### 3.2. Gün İçi Güncellemeler

```
1. New ride_request arrives
   - type = "extra" (ders dışı)
   - requested_pickup_time / requested_dropoff_time mevcut

2. Admin approval
   - status → "approved"

3. Re-optimization (if needed)
   - Add new student to existing routes
   - Or create new route

4. Update route_plans
```

---

## 4. Python API Entegrasyonu

### 4.1. Yeni Veri Akışı

```
Supabase → Next.js API → Python API → Optimization → Results
     ↓              ↓              ↓
weekly_schedules  transform    OptimizationRequest
                  to Student   with time_windows
```

### 4.2. StudentNode Güncellemesi (Gerekli)

Mevcut:
```python
class StudentNode(BaseModel):
    id: str
    location_code: str
    disability_type: str
```

Eklenecek:
```python
class StudentNode(BaseModel):
    id: str
    location_code: str
    disability_type: str
    pickup_time: Optional[str] = None      # "09:00"
    dropoff_time: Optional[str] = None     # "14:00"
    direction: Optional[str] = None        # "pickup" or "dropoff"
```

### 4.3. OptimizationRequest Güncellemesi

```python
class OptimizationRequest(BaseModel):
    # ... mevcut alanlar ...
    direction: str = "pickup"              # "pickup" or "dropoff"
    use_time_windows: bool = True
    target_arrival_time: Optional[str] = None  # "09:00" (pickup için)
```

---

## 5. Implementasyon Adımları

### Faz 1: Veri Transformasyonu (2-3 saat)
- [ ] `weekly_schedules_to_students()` fonksiyonu
- [ ] DayOfWeek → Date conversion
- [ ] Time string → Minutes conversion

### Faz 2: Python API Güncellemesi (4-5 saat)
- [ ] StudentNode model güncellemesi
- [ ] OptimizationRequest model güncellemesi
- [ ] Time window extraction logic
- [ ] main.py endpoint güncellemesi

### Faz 3: SplitDecoder TW Desteği (6-8 saat)
- [ ] Backward scheduling implementasyonu
- [ ] Time window constraint checking
- [ ] Route feasibility validation

### Faz 4: Frontend Entegrasyonu (3-4 saat)
- [ ] Direction seçimi UI
- [ ] Time window görüntüleme
- [ ] Route plan confirmation flow

---

## 6. Örnek SQL Sorguları

### 6.1. Yarınki Öğrenci Listesi (Pickup için)

```sql
SELECT
    u.id,
    u.name,
    u.location_code,
    u.disability_type,
    w.entry->>'startTime' as pickup_time,
    w.entry->>'endTime' as dropoff_time
FROM users u
JOIN (
    SELECT
        user_id,
        jsonb_array_elements(entries) as entry
    FROM weekly_schedules
) w ON u.id = w.user_id
WHERE LOWER(w.entry->>'dayOfWeek') = LOWER(TO_CHAR(CURRENT_DATE + 1, 'day'))
ORDER BY w.entry->>'startTime';
```

### 6.2. Time Matrix'i Python Formatına Çevirme

```sql
SELECT
    origin_code,
    destination_code,
    duration_minutes
FROM time_matrix
ORDER BY origin_code, destination_code;
```

---

## 7. Sonraki Adım

**Veritabanı yapısı analizi tamamlandı.** Şimdi:

1. **Onayınızı alıyorum:** Bu plan doğru mu?
2. **Faz 1'e başlayalım mı?** (Python API model güncellemeleri)

veya

3. **Önce bir test sorgusu çalıştıralım mı?** (Gerçek verilerle öğrenci listesi çekme)
