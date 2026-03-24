# UniRide Optimizer API - GWO & HHO Güncelleme Paketi

## 📦 Paket İçeriği

Bu paket, UniRide Optimizer API'ye GWO (Grey Wolf Optimizer) ve HHO (Harris Hawks Optimization) algoritmalarını ekler.

## 📁 Dosya Yapısı ve Kurulum

```
optimizer_api/
├── main.py                              → optimizer_api/
├── models/
│   └── schemas.py                       → optimizer_api/models/
├── strategies/
│   ├── __init__.py                      → optimizer_api/strategies/
│   ├── gwo_strategy.py                  → optimizer_api/strategies/ (YENİ)
│   └── hho_strategy.py                  → optimizer_api/strategies/ (YENİ)
├── test_gwo.py                          → optimizer_api/ (TEST)
├── test_hho.py                          → optimizer_api/ (TEST)
├── test_comparison.py                   → optimizer_api/ (TEST)
└── verify_strategies.py                 → optimizer_api/ (TEST)
```

## 🚀 Kurulum Adımları

1. Zip dosyasını `optimizer_api` klasörüne çıkarın
2. Dosyalar aynı isimli dosyaların üzerine yazılacak
3. API'yi yeniden başlatın: `python main.py` veya `uvicorn main:app --reload`

## ✅ Yeni Algoritmalar

| Algoritma | Kod | Açıklama |
|-----------|-----|----------|
| **GWO** | `gwo` veya `grey_wolf` | Gri Kurt Optimizasyonu - Sosyal hiyerarşi tabanlı |
| **HHO** | `hho` veya `harris_hawks` | Harris Hawks Optimizasyonu - Kaçış enerjisi tabanlı |

## 📊 API Versiyonu

**v2.2.0** (GA, PSO, GWO, HHO, Greedy, Permutation, OR-Tools)

## 🔌 Kullanım Örneği

```bash
# GWO ile optimizasyon
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "gwo",
    "students": [...],
    "depot": {...}
  }'

# HHO ile optimizasyon
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "hho",
    "students": [...],
    "depot": {...}
  }'

# Tüm algoritmaları karşılaştır
curl -X POST http://localhost:8000/api/v1/compare \
  -H "Content-Type: application/json" \
  -d '{"students": [...], "depot": {...}}'
```

## 🧪 Test

```bash
cd optimizer_api
python test_gwo.py           # GWO testi
python test_hho.py           # HHO testi
python test_comparison.py    # Tüm algoritma karşılaştırması
python verify_strategies.py  # Strateji registry doğrulama
```

---
**Tarih:** 19.03.2026
