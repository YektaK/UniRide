# 📊 UniRide Mevcut Durum Analizi

> Son güncelleme: 26 Mart 2026  
> Veritabanı doğrulama: ✅ Tamamlandı

---

## 1. Veritabanı Doğrulama Sonuçları

| Kontrol | Beklenen | Gerçek | Durum |
|---|---|---|---|
| Toplam satır | 812 | **812** | ✅ |
| Origin sayısı | 29 (D.Kampus + 9Sw + 19So) | **29** | ✅ |
| Her origin'in edge sayısı | 28 | **28** | ✅ |
| D.Kampus → Sw1 süresi | > 0 | **40 dk** | ✅ |
| Kolon yapısı | origin_code, destination_code, duration_minutes | **Uyumlu** | ✅ |
| distance_meters | — | **null** | ⚠️ Boş |

---

## 2. Hedef İşlevler Karşılaştırması

| # | Hedef İşlev | Durum | Not |
|---|---|---|---|
| 1 | Öğrenci kaydı (kendi + merkezi) | ✅ | Register sayfası + admin panel |
| 2 | Ders programı girişi | ✅ | Import script + admin sayfaları |
| 3 | Onay/iptal mekanizması | ⚠️ Kısmi | Deadline mantığı yok |
| 4 | Ders dışı talep girişi | ✅ | request-ride sayfası |
| 5 | Koordinat seçimi (konum/adres) | ⚠️ Kısmi | Sabit dosya, dinamik seçim yok |
| 6 | Admin rota oluşturma | ✅ | vehicle-planning Python'a bağlı (Faz 1.1) |
| 7 | 8+ algoritma seçimi | ✅ | Python'da var, UI bağlı |
| 8 | Algoritma karşılaştırma | ✅ | compare sayfası çalışıyor |
| 9 | Sw/So kapasite kısıtları | ✅ | Python'da implemente |
| 10 | Max tur süresi kısıtı | ✅ | Python'da implemente |
| 11 | time_matrix kullanımı | ✅ | Encoding fix tamamlandı (Faz 1.2) |
| 12 | Atama görüntüleme | ⚠️ Kısmi | Sonuçlar DB'ye kaydedilmiyor |
| 13 | Canlı konum takibi | ❌ Yok | Planlanan faz |
| 14 | Dinamik uzaklık güncelleme | ❌ Yok | Planlanan faz |

---

## 3. Sayfa Bazlı Entegrasyon Durumu

| Admin Sayfası | Backend | Python Bağlantısı | Durum |
|---|---|---|---|
| `route-test` | Python API (optimizer-service) | ✅ Doğrudan | **Çalışır** |
| `compare` | Python API (optimizer-service) | ✅ Doğrudan | **Çalışır** |
| `vehicle-planning` | Python API (optimizer-service) | ✅ Düzeltildi (Faz 1.1) | **Çalışır** |

---

## 4. CVRPTW Analizi: Katı Kümeleme Sorunu

### 4.1 Sorun Tanımı

Mevcut "Cluster-First, Route-Second" yaklaşımında K-Means öğrencileri coğrafi mesafeye göre kümeliyor fakat:
- **Time matrix duyarsız:** Gerçek trafik süresini bilmiyor
- **Katı küme sınırları:** Süre kısıtı aşıldığında küme iptal ediliyor, araç sayısı +1 artıyor
- **Tek öğrencilik rotalar:** %15-20 oranında verimsiz tek kişilik araç ataması oluşuyor

### 4.2 Sorunlu Kod Bölümü (`clustering.py`)

```python
for attempt in range(max_attempts):
    clusters = self.cluster_students(points, num_vehicles)
    # ...
    if route_duration > self.max_tour_time:
        valid = False
        break  # ← KÜME REDDEDİLİYOR!
    
    num_vehicles += 1  # ← YENİ ARAÇ AÇILIYOR!
```

### 4.3 Çözüm: Giant Tour + Split Decoder (KN10)

Prins (2004) referansıyla, K-Means kümelemesi yerine tüm öğrenciler tek bir "Giant Tour" permütasyonunda meta-sezgisel ile optimize edilip, ardından Dinamik Programlama (DP) tabanlı Split Decoder ile `time_matrix` ve kapasite kısıtlarına %100 uygun rotalara bölünecektir.

| Metrik | Mevcut (K-Means) | Hedef (Split) | İyileştirme |
|--------|------------------|---------------|-------------|
| Ort. Araç Sayısı | 7-8 | 5-6 | -20% |
| Tek Öğrenci Rotalar | %15-20 | <%5 | -75% |
| Feasibility | %92 | %100 | +8% |
| Time Matrix | Duyarsız | Duyarlı | ✓ |

Detaylı implementasyon planı → [ROADMAP.md](./ROADMAP.md) Faz 1.5

---

## 5. Ölçeklenebilirlik (N ≥ 300)

| N | Permütasyon Sayısı | Durum |
|---|---|---|
| 10 | 3,628,800 | Exact çözülebilir |
| 30 | 2.65 × 10³² | Meta-sezgisel gerekli |
| 300 | Astronomik | Meta-sezgisel + Split |

Split Decoder, N=300 seviyelerinde bile O(N²) karmaşıklıkla çalıştığı için ölçeklenebilirlik sorununu çözer. Detaylı analiz → [Ölçeklenebilirlik Seçenekleri](./superpowers/specs/2026-03-26-scalability-options.md)

---

## 6. Teknik İnceleme Bulguları (26 Mart 2026)

| # | Bulgu | Ciddiyet | Durum |
|---|-------|----------|-------|
| B1 | N>100'de Giant Tour (Pipeline B) arama uzayı patlar | ⚠️ Yüksek | ✅ Pipeline Seçim Matrisi ile çözüldü |
| B2 | DP formülasyonunda Sw+So AND kısıtı atlanabilir | 🔴 Kritik | ✅ Kısıt Referans Tablosu oluşturuldu |
| B3 | Performans tabloları tahmini değerler içeriyor | ⚠️ Orta | ⬜ Benchmark (Görev 1.5.10) sonrası güncellenecek |
| B4 | Eski K-Means tabanlı algoritmalar UI'da karışıklık yaratır | ⚠️ Orta | ✅ Pipeline etiketi eklenecek |
| B5 | `max_tour_time` tutuarsızlığı (45/120/180 dk) | 🔴 Kritik | ✅ Tek referans noktası: 120 dk |
| B6 | OR-Tools + Split Decoder birleşimi anlamsız | ℹ️ Düşük | ✅ OR-Tools bağımsız referans olarak belgelendi |

### Çift Pipeline Kararı (KN12)

İnceleme sonucunda **hem** Pipeline A (Sweep/CW + Heuristic) **hem** Pipeline B (Giant Tour + Split) paralel olarak desteklenecek şekilde mimari güncellendi. Bunlar birbirini tamamlayan iki farklı VRP paradigmasıdır ve N boyutuna göre otomatik veya admin seçimiyle kullanılır.

Detaylı mimari → [ARCHITECTURE.md §3](./ARCHITECTURE.md)
