# 📚 UniRide Proje Dokümantasyonu

> **Bu klasördeki dokümanlar projenin "tek doğru kaynağı"dır (single source of truth).**  
> **Tüm AI agent'lar ve geliştiriciler kod yazmaya başlamadan önce bu dokümanları OKUMAK ve UYMAK zorundadır.**

## Dosya Yapısı

| Dosya | İçerik | Ne zaman oku? |
|---|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Mimari kurallar, dosya sorumluluk haritası, API kontratları | **Her zaman, ilk önce** |
| [ROADMAP.md](./ROADMAP.md) | Faz bazlı geliştirme planı, görev tanımları | Yeni iş alırken |
| [ANALYSIS.md](./ANALYSIS.md) | Mevcut durum analizi, uyumlu/uyumsuz noktalar, DB doğrulama | Sistemi anlamak için |
| [CHANGELOG.md](./CHANGELOG.md) | Yapılan değişikliklerin kronolojik kaydı | Her commit sonrası güncelle |

## Kurallar

1. **Kod yazmadan önce** `ARCHITECTURE.md` oku
2. **Yeni görev alırken** `ROADMAP.md`'den hangi faz/görevde olduğunu kontrol et
3. **Her anlamlı değişiklik sonrası** `CHANGELOG.md`'ye kayıt ekle
4. **Mimari değişiklik yapmadan önce** bu dokümanları güncelle, sonra kodu değiştir
