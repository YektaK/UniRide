# UniRide CVRPTW - Deployment Guide

## Sürüm: 2.0.0 | Tarih: 30 Mart 2026

---

## 📋 Ön Gereksinimler

### Sistem Gereksinimleri
| Bileşen | Minimum | Önerilen |
|---------|---------|----------|
| Node.js | 18.x | 20.x LTS |
| Python | 3.10 | 3.11+ |
| PostgreSQL | 14.x | 15.x |
| RAM | 4GB | 8GB |
| Disk | 10GB | 20GB |

### Gerekli Hesaplar
- Supabase hesabı (ücretsiz tier yeterli)
- GitHub hesabı (CI/CD için)
- Dropbox hesabı (opsiyonel, dosya paylaşımı için)

---

## 🚀 Hızlı Başlangıç

### 1. Projeyi İndir
```bash
# Projeyi klonla veya indir
git clone <repo-url> uniride
cd uniride

# veya zip'ten çıkar
unzip UniRide_Complete_Project.zip
cd uniride
```

### 2. Environment Variables
```bash
# .env.local dosyası oluştur
cp .env.local.template .env.local

# Gerekli değerleri doldur
nano .env.local
```

```env
# Supabase (Zorunlu)
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJxxx...
SUPABASE_SERVICE_ROLE_KEY=eyJxxx...

# Optimizer API
OPTIMIZER_API_URL=http://127.0.0.1:8000

# Opsiyonel
NEXT_PUBLIC_USE_MOCK_DB=false
```

### 3. Frontend Kurulumu
```bash
# Bağımlılıkları yükle
npm install

# TypeScript kontrolü
npm run typecheck

# Development server'ı başlat
npm run dev
```

### 4. Backend Kurulumu
```bash
# Python sanal ortam oluştur
cd optimizer_api
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
.\venv\Scripts\activate  # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt

# Server'ı başlat
uvicorn main:app --reload --port 8000
```

### 5. Veritabanı Kurulumu
```sql
-- Supabase SQL Editor'de çalıştır
-- supabase/schema.sql dosyasını kopyala-yapıştır

-- RLS politikalarını ekle
-- supabase/rls_policies.sql dosyasını çalıştır
```

---

## 🏗️ Production Deployment

### Seçenek 1: Vercel + Railway

#### Frontend (Vercel)
```bash
# Vercel CLI yükle
npm i -g vercel

# Deploy
vercel --prod
```

#### Backend (Railway)
```bash
# Railway CLI yükle
npm i -g @railway/cli

# Login ve deploy
railway login
railway init
railway up
```

### Seçenek 2: Docker

#### Dockerfile (Frontend)
```dockerfile
# Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

#### Dockerfile (Backend)
```dockerfile
# optimizer_api/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml
```yaml
version: '3.8'
services:
  frontend:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - OPTIMIZER_API_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build: ./optimizer_api
    ports:
      - "8000:8000"
    environment:
      - CORS_ORIGINS=http://localhost:3000,https://your-domain.com

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

```bash
# Tüm servisleri başlat
docker-compose up -d

# Logları görüntüle
docker-compose logs -f
```

---

## 🔧 Yapılandırma

### Algoritma Parametreleri
```typescript
// src/lib/algorithm-constants.ts
export const ALGORITHM_CONFIG = {
  genetic_algorithm: {
    population_size: 50,
    max_iterations: 100,
    crossover_rate: 0.85,
    mutation_rate: 0.15
  },
  pso: {
    swarm_size: 30,
    max_iterations: 100,
    inertia_weight: 0.7
  }
};
```

### Capacity Ayarları
```typescript
// src/lib/config.ts
export const DEFAULT_SW_CAPACITY = 4;  // Tekerlekli sandalye
export const DEFAULT_SO_CAPACITY = 5;  // Normal koltuk
export const DEFAULT_MAX_TRAVEL_TIME = 120; // dakika
```

---

## 📊 Monitoring

### Health Check Endpoints
```bash
# Frontend health
curl https://your-domain.com/api/health

# Backend health
curl https://api.your-domain.com/health
```

### Logging
```typescript
// Structured logging example
logger.info({
  event: 'optimization_completed',
  algorithm: 'genetic_algorithm',
  students: 25,
  duration_ms: 2500,
  vehicles: 4,
  timestamp: new Date().toISOString()
});
```

---

## 🔐 Güvenlik

### Production Checklist
- [ ] Supabase RLS politikaları aktif
- [ ] CORS ayarları doğru
- [ ] Rate limiting aktif
- [ ] HTTPS aktif
- [ ] Environment variables güvenli
- [ ] API keys rotasyonu planlanmış

### Supabase RLS Örnekleri
```sql
-- Öğrenciler sadece kendi verilerini görebilir
CREATE POLICY "Students own data"
ON ride_requests FOR SELECT
USING (user_id = auth.uid());

-- Adminler tüm verileri görebilir
CREATE POLICY "Admins full access"
ON ride_requests FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM users 
    WHERE id = auth.uid() AND role = 'admin'
  )
);
```

---

## 🐛 Sorun Giderme

### Yaygın Sorunlar

#### 1. "Cannot connect to optimizer API"
```bash
# Backend çalışıyor mu kontrol et
curl http://localhost:8000/health

# Portu kontrol et
lsof -i :8000
```

#### 2. "Supabase connection failed"
```bash
# Environment variables kontrol et
echo $NEXT_PUBLIC_SUPABASE_URL

# Supabase dashboard'dan URL ve key'i doğrula
```

#### 3. "Type errors in build"
```bash
# TypeScript hatalarını bul
npm run typecheck

# node_modules'ü temizle ve yeniden yükle
rm -rf node_modules package-lock.json
npm install
```

---

## 📁 Proje Yapısı

```
uniride/
├── src/                      # Next.js kaynak kodu
│   ├── app/                  # App Router sayfaları
│   ├── components/           # React bileşenleri
│   ├── services/             # İş mantığı servisleri
│   ├── lib/                  # Yardımcı fonksiyonlar
│   └── types/                # TypeScript tipleri
├── optimizer_api/            # Python backend
│   ├── main.py               # FastAPI giriş noktası
│   ├── models/               # Pydantic modeller
│   ├── strategies/           # Optimizasyon algoritmaları
│   └── utils/                # Yardımcı fonksiyonlar
├── supabase/                 # Veritabanı şeması
│   ├── schema.sql            # Tablo tanımları
│   └── rls_policies.sql      # RLS politikaları
├── docs/                     # Dokümantasyon
├── package.json              # npm bağımlılıkları
└── docker-compose.yml        # Docker yapılandırması
```

---

## 🧪 Test

### Unit Tests
```bash
# Frontend testleri
npm test

# Backend testleri
cd optimizer_api
pytest tests/
```

### Integration Tests
```bash
# API endpoint testleri
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{"algorithm": "ga", "students": [...], "depot": {...}}'
```

---

## 📞 Destek

- **Dokümantasyon:** `/docs` klasörü
- **Issue Tracker:** GitHub Issues
- **Email:** [Proje yöneticisi email]

---

*Bu rehber proje güncellemeleriyle senkronize tutulacaktır.*
