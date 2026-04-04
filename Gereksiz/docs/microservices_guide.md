# UniRide Mikroservis Çalıştırma ve Test Rehberi

Bu rehber, UniRide projesindeki optimizasyon ve planlama mikroservislerinin nasıl çalıştırılacağını ve test edileceğini açıklar.

## 1. Servislerin Yapısı
Optimizasyon servisleri `src/services/doubus` altında yer alır:
- **Route Optimizer:** Tek araçlık rota optimizasyonu (`nearest-neighbor`, `permutation`, `2-opt`).
- **Multi-Vehicle Routing:** Çoklu araç atama ve kümeleme (K-Means).
- **Genetic/PSO (Planlanan):** İleride eklenecek gelişmiş algoritmalar.

## 2. API Endpoint'leri
Mikroservislere şu endpoint'ler üzerinden erişilir:
- `POST /api/optimize-route`: Rota optimizasyonunu tetikler.
- `POST /api/calculate-vehicles`: Araç planlama ve rota dağıtımını başlatır.

## 3. Lokal Çalıştırma
Uygulamayı geliştirme modunda başlatın:
```bash
npm run dev
```

## 4. Test Etme

### A. Otomatik Testler (Vitest/Node Test)
Daha önce oluşturduğumuz test senaryolarını çalıştırarak mantığın doğruluğunu kontrol edebilirsiniz:
```bash
node --test temp_test_js/__tests__/route-optimizer.test.js
```

### B. Manuel API Testi (Curl)
Terminal üzerinden doğrudan API'ye istek atarak servisleri test edebilirsiniz:

**Rota Optimizasyonu Testi:**
```bash
curl -X POST http://localhost:3000/api/optimize-route \
  -H "Content-Type: application/json" \
  -d '{
    "start": "Dudullu",
    "end": "Dogus Kampus",
    "waypoints": ["Sw1", "So2"],
    "strategy": "two-opt"
  }'
```

### C. Gelişmiş Optimizasyon Testi (GA/PSO)
Yeni eklenen algoritmaları test etmek için `strategy` parametresini `ga` veya `pso` olarak güncelleyerek (uygulandıktan sonra) yukarıdaki komutu kullanabilirsiniz.

## 5. Hata İzleme
Mikroservislerde bir sorun olduğunda:
1. Terminal loglarını (`npm run dev` çıktısı) kontrol edin.
2. `src/lib/logger.ts` (varsa) üzerinden hata detaylarını inceleyin.
3. Supabase bağlantısının aktif olduğundan emin olun.
