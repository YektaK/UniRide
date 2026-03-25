# 📊 UniRide Mevcut Durum Analizi

> Son güncelleme: 25 Mart 2026  
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
| 6 | Admin rota oluşturma | ❌ Crash | vehicle-planning Python'a bağlı değil |
| 7 | 5 algoritma seçimi | ❌ Kopuk | Python'da var ama UI bağlı değil |
| 8 | Algoritma karşılaştırma | ✅ | compare sayfası çalışıyor |
| 9 | Sw/So kapasite kısıtları | ✅ | Python'da implemente |
| 10 | Max tur süresi kısıtı | ✅ | Python'da implemente |
| 11 | time_matrix kullanımı | ⚠️ Risk | Veri tam, Windows encoding riski |
| 12 | Atama görüntüleme | ⚠️ Kısmi | Sonuçlar DB'ye kaydedilmiyor |
| 13 | Canlı konum takibi | ❌ Yok | Planlanan faz |
| 14 | Dinamik uzaklık güncelleme | ❌ Yok | Planlanan faz |

---

## 3. Sayfa Bazlı Entegrasyon Durumu

| Admin Sayfası | Backend | Python Bağlantısı | Durum |
|---|---|---|---|
| `route-test` | Python API (optimizer-service) | ✅ Doğrudan | **Çalışır** |
| `compare` | Python API (optimizer-service) | ✅ Doğrudan | **Çalışır** |
| `vehicle-planning` | TypeScript (local) | ❌ Bağlantı yok | **Crash** |

---

## 4. Tespit Edilen Kritik Sorunlar

1. **`vehicle-planning` → Python API bağlantısı yok** (crash)
2. **`doubus/route-strategies/index.ts`** silinmiş dosya import'ları
3. **`vehicle-planning`** eski algoritma key'leri kullanıyor
4. **Windows encoding** → DataLoader time_matrix yükleyemiyor
5. **`multi-vehicle-routing.ts`** Python payload uyumsuzluğu
6. **Rota sonuçları** Supabase'e kaydedilmiyor

Detaylı düzeltme planı için → [ROADMAP.md](./ROADMAP.md)
