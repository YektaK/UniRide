# Sprint 1 Test Planı: Pipeline B Stratejileri

> **Tarih:** 28 Mart 2026  
> **Kapsam:** PSO-Split, HHO-Split, GWO-Split + Strategy Registry + Frontend Integration  
> **Durum:** Planlama Aşaması

---

## 1. Test Kapsamı Özeti

### 1.1 Test Edilecek Bileşenler

| # | Bileşen | Dosya(lar) | Öncelik |
|---|---------|------------|---------|
| 1 | **PSO-Split Strategy** | `strategies/pso_split_strategy.py` | 🔴 Kritik |
| 2 | **HHO-Split Strategy** | `strategies/hho_split_strategy.py` | 🔴 Kritik |
| 3 | **GWO-Split Strategy** | `strategies/gwo_split_strategy.py` | 🔴 Kritik |
| 4 | **Strategy Registry** | `strategies/__init__.py` | 🔴 Kritik |
| 5 | **Frontend Constants** | `lib/algorithm-constants.ts` | 🟡 Yüksek |
| 6 | **Split Decoder** | `utils/split_decoder.py` | 🔴 Kritik |
| 7 | **Integration** | API + UI End-to-End | 🟡 Yüksek |

### 1.2 Test Türleri

| Tür | Açıklama | Kapsam |
|-----|----------|--------|
| **Unit Test** | Her strateji için bağımsız test | Tüm stratejiler |
| **Integration Test** | Registry + Strateji entegrasyonu | Registry, API |
| **End-to-End Test** | UI'dan API'ye kadar tam akış | Frontend + Backend |
| **Performance Test** | Büyük ölçekli veri testi | 30, 100, 300 öğrenci |
| **Regression Test** | Mevcut algoritmaların bozulmadığı kontrolü | Pipeline A algoritmaları |

---

## 2. Unit Test Planı

### 2.1 PSO-Split Testleri (`test_pso_split.py`)

```python
# Test Suite: PSOSplitUnitTest

class TestPSOSplitInitialization:
    """PSO-Split başlatma testleri"""
    
    def test_default_config_loaded(self):
        """Varsayılan konfigürasyon değerlerinin doğru yüklendiği"""
        # Expected: swarm_size=60, max_iterations=200, inertia_weight=0.9
        pass
    
    def test_custom_config_override(self):
        """Özel konfigürasyonun varsayılanı geçersiz kıldığı"""
        # Test: {"swarm_size": 80} → swarm_size=80
        pass
    
    def test_seed_reproducibility(self):
        """Aynı seed ile aynı sonuçların üretildiği"""
        # Test: seed=42 ile iki çalıştırma → aynı initial swarm
        pass


class TestPSOSplitOptimization:
    """PSO-Split optimizasyon testleri"""
    
    def test_empty_students(self):
        """Boş öğrenci listesi ile başarılı yanıt döndürdüğü"""
        # Expected: success=True, routes=[], total_vehicles=0
        pass
    
    def test_single_student(self):
        """Tek öğrenci ile doğru rota ürettiği"""
        # Expected: 1 araç, 2 durak (depot → student → depot)
        pass
    
    def test_sw_so_constraints(self):
        """Sw/So kapasite kısıtlarını doğru uyguladığı"""
        # Test: 5 Sw + 5 So → En az 2 araç (4 Sw + 5 So kapasite)
        pass
    
    def test_max_tour_time_constraint(self):
        """Maksimum tur süresi kısıtını doğru uyguladığı"""
        # Test: max_tour_time=120 → Hiçbir rota 120 dk'yı aşmamalı
        pass
    
    def test_split_decoder_integration(self):
        """Split Decoder ile doğru entegre olduğu"""
        # Test: Giant tour → Routes dönüşümü başarılı
        pass
    
    def test_feasibility_guarantee(self):
        """Üretilen rotaların %100 feasible olduğu"""
        # Test: Sw ≤ 4, So ≤ 5, toplam ≤ 9
        pass


class TestPSOSplitConvergence:
    """PSO-Split yakınsama testleri"""
    
    def test_convergence_with_iterations(self):
        """İterasyonlarla birlikte maliyetin azaldığı"""
        # Test: Generation 0 cost > Generation N cost
        pass
    
    def test_no_improvement_stopping(self):
        """max_no_improvement sonrası durduğu"""
        # Test: 40 iterasyon improvement yoksa durmalı
        pass
    
    def test_linear_inertia_decay(self):
        """Inertia weight'in lineer azaldığı"""
        # Test: iteration=0 → 0.9, iteration=max → 0.4
        pass
```

### 2.2 HHO-Split Testleri (`test_hho_split.py`)

```python
# Test Suite: HHOSplitUnitTest

class TestHHOSplitMechanics:
    """HHO mekanikleri testleri"""
    
    def test_levy_flight_mutation(self):
        """Lévy flight mutasyonunun çalıştığı"""
        # Test: Pozisyon değişikliği gözlemlenmeli
        pass
    
    def test_escape_energy_calculation(self):
        """Kaçış enerjisinin doğru hesulandığı"""
        # Test: E = 2*E0*(1 - t/T)*initial_energy
        pass
    
    def test_soft_besiege_selection(self):
        """Soft besiege stratejisinin seçildiği"""
        # Test: |E| >= 0.5 ve r < 0.4
        pass
    
    def test_hard_besiege_selection(self):
        """Hard besiege stratejisinin seçildiği"""
        # Test: |E| < 0.5 ve r < 0.4
        pass
    
    def test_exploration_exploitation_transition(self):
        """Keşif-sömürü geçişinin doğru olduğu"""
        # Test: Early iterations → exploration, late → exploitation
        pass
```

### 2.3 GWO-Split Testleri (`test_gwo_split.py`)

```python
# Test Suite: GWOSplitUnitTest

class TestGWOSplitHierarchy:
    """GWO hiyerarşi testleri"""
    
    def test_alpha_beta_delta_selection(self):
        """Alpha, Beta, Delta kurtların doğru seçildiği"""
        # Test: En iyi 3 çözüm lider olarak seçilmeli
        pass
    
    def test_social_hierarchy_update(self):
        """Sosyal hiyerarşinin güncellendiği"""
        # Test: Daha iyi çözüm bulunduğunda liderler değişmeli
        pass
    
    def test_linear_a_decay(self):
        """'a' parametresinin lineer azaldığı"""
        # Test: initial_a → 0 lineer azalma
        pass
    
    def test_position_update_weights(self):
        """Pozisyon güncelleme ağırlıklarının doğru olduğu"""
        # Test: Alpha 0.7, Beta 0.5, Delta 0.3 ağırlık
        pass
```

### 2.4 Split Decoder Testleri (`test_split_decoder.py`)

```python
# Test Suite: SplitDecoderUnitTest

class TestSplitDecoderBasic:
    """Split Decoder temel testleri"""
    
    def test_empty_tour(self):
        """Boş tour için boş sonuç döndürdüğü"""
        pass
    
    def test_single_customer(self):
        """Tek müşteri için tek rota döndürdüğü"""
        pass
    
    def test_capacity_feasibility(self):
        """Kapasite kısıtlarını doğru uyguladığı"""
        pass
    
    def test_time_constraint(self):
        """Zaman kısıtlarını doğru uyguladığı"""
        pass
    
    def test_optimal_partitioning(self):
        """Optimal bölme yaptığı (Prins, 2004)"""
        # Test: Bilinen test case'lerde optimal sonuç
        pass


class TestSplitDecoderV2:
    """Split Decoder V2 (heterojen) testleri"""
    
    def test_heterogeneous_vehicle_assignment(self):
        """Farklı kapasiteli araç ataması"""
        pass
    
    def test_best_vehicle_selection(self):
        """En uygun araç tipinin seçildiği"""
        pass
```

---

## 3. Integration Test Planı

### 3.1 Strategy Registry Testleri (`test_strategy_registry.py`)

```python
# Test Suite: StrategyRegistryIntegrationTest

class TestStrategyRegistry:
    """Strategy Registry entegrasyon testleri"""
    
    def test_all_strategies_registered(self):
        """Tüm stratejilerin registry'de olduğu"""
        # Expected: ga_split, pso_split, hho_split, gwo_split
        pass
    
    def test_pipeline_b_strategies_accessible(self):
        """Pipeline B stratejilerine erişilebildiği"""
        # Test: get_strategy("pso_split") returns PSOSplitStrategy
        pass
    
    def test_get_available_solvers(self):
        """Kullanılabilir çözücü listesinin doğru olduğu"""
        pass
    
    def test_get_recommended_strategy(self):
        """Önerilen strateji fonksiyonunun doğru çalıştığı"""
        # Test: n=30 → ga_split, n=100 → pso_split
        pass
    
    def test_graceful_fallback_for_missing_packages(self):
        """Eksik paketler için graceful fallback"""
        # Test: pyvrp yoksa ortools'e fallback
        pass
```

### 3.2 API Integration Testleri

```python
# Test Suite: APIIntegrationTest

class TestOptimizeEndpoint:
    """/api/v1/optimize endpoint testleri"""
    
    def test_pso_split_via_api(self):
        """API üzerinden PSO-Split çağrılabildiği"""
        # POST /api/v1/optimize with algorithm="pso_split"
        pass
    
    def test_hho_split_via_api(self):
        """API üzerinden HHO-Split çağrılabildiği"""
        pass
    
    def test_gwo_split_via_api(self):
        """API üzerinden GWO-Split çağrılabildiği"""
        pass
    
    def test_algorithm_not_found_error(self):
        """Geçersiz algoritma için 400 döndürdüğü"""
        pass
    
    def test_response_format_consistency(self):
        """Yanıt formatının tutarlı olduğu"""
        # Tüm stratejiler aynı formatı döndürmeli
        pass
```

---

## 4. End-to-End Test Planı

### 4.1 UI Integration Testleri

| Test ID | Senaryo | Adımlar | Beklenen Sonuç |
|---------|---------|---------|----------------|
| E2E-01 | Algoritma seçimi dropdown | 1. Vehicle Planning sayfasına git<br>2. Algoritma dropdown'ını aç | Pipeline kategorileri görünmeli |
| E2E-02 | PSO-Split seçimi | 1. "Route-First" kategorisini aç<br>2. PSO-Split seç | Seçim başarılı, API'ye doğru key gitmeli |
| E2E-03 | Optimizasyon çalıştırma | 1. Öğrenci seç<br>2. PSO-Split seç<br>3. Hesapla butonuna tıkla | Sonuçlar gelmeli, araç sayısı gösterilmeli |
| E2E-04 | Sonuç gösterimi | Optimizasyon sonrası | Rotalar, süreler, Sw/So sayıları doğru görünmeli |

---

## 5. Performance Test Planı

### 5.1 Benchmark Senaryoları

| Senaryo | N (Öğrenci) | Algoritmalar | Metrikler |
|---------|-------------|--------------|-----------|
| Small | 10 | PSO-Split, HHO-Split, GWO-Split, GA-Split | Execution time, vehicle count, feasibility |
| Medium | 30 | Tüm Pipeline B | Execution time, vehicle count, quality vs Pipeline A |
| Large | 100 | PSO-Split, GA-Split, OR-Tools | Execution time, memory usage, quality |
| XLarge | 300 | OR-Tools, PyVRP, VROOM | Execution time, scalability |

### 5.2 Quality Metrics

| Metrik | Açıklama | Karşılaştırma |
|--------|----------|---------------|
| Vehicle Count | Toplam araç sayısı | Pipeline A vs Pipeline B |
| Total Duration | Toplam süre (dk) | Pipeline A vs Pipeline B |
| Feasibility Rate | %100 feasible çözüm oranı | Tüm algoritmalar |
| Single-Student Routes | Tek öğrencili rota sayısı | Pipeline A vs Pipeline B |

---

## 6. Regression Test Planı

### 6.1 Mevcut Algoritmaların Testi

| Algoritma | Test | Neden |
|-----------|------|-------|
| genetic_algorithm | E2E test çalıştır | Registry değişikliği etkilemiş mi? |
| pso | E2E test çalıştır | Registry değişikliği etkilemiş mi? |
| hho | E2E test çalıştır | Registry değişikliği etkilemiş mi? |
| gwo | E2E test çalıştır | Registry değişikliği etkilemiş mi? |
| ortools_cvrp | E2E test çalıştır | Fallback mantığı çalışıyor mu? |

---

## 7. Test Verisi

### 7.1 Test Öğrenci Setleri

```python
# Test Set 1: Small (10 öğrenci)
TEST_SMALL = [
    {"id": "s1", "location_code": "Sw1", "disability_type": "Sw"},
    {"id": "s2", "location_code": "So1", "disability_type": "So"},
    # ... 10 öğrenci (4 Sw, 6 So)
]

# Test Set 2: Medium (30 öğrenci)
TEST_MEDIUM = [
    # ... 30 öğrenci (10 Sw, 20 So)
]

# Test Set 3: Large (100 öğrenci)
TEST_LARGE = [
    # ... 100 öğrenci (30 Sw, 70 So)
]
```

### 7.2 Known Test Cases

| Case | Sw | So | Expected Min Vehicles | Reason |
|------|-----|-----|----------------------|--------|
| TC-01 | 4 | 5 | 1 | Exact capacity fit |
| TC-02 | 5 | 5 | 2 | Sw overflow (4+1) |
| TC-03 | 4 | 6 | 2 | So overflow (5+1) |
| TC-04 | 8 | 10 | 2 | Double capacity |

---

## 8. Test Ortamı Gereksinimleri

### 8.1 Python Test Ortamı

```bash
# Gereksinimler
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-timeout>=2.1.0

# Opsiyonel (test edilecek)
pyvrp>=0.8.0
pyvroom>=0.9.0
```

### 8.2 Test Çalıştırma

```bash
# Tüm testleri çalıştır
cd UniRide/optimizer_api
pytest tests/ -v --cov=strategies --cov-report=html

# Sadece Pipeline B testleri
pytest tests/test_*_split.py -v

# Sadece registry testleri
pytest tests/test_strategy_registry.py -v

# Performance testleri (uzun süreli)
pytest tests/test_performance.py -v --timeout=300
```

---

## 9. Test Takvimi

| Gün | Aktivite | Sorumlu |
|-----|----------|---------|
| Gün 1 | Unit test yazımı (PSO-Split, HHO-Split, GWO-Split) | - |
| Gün 2 | Registry integration testleri | - |
| Gün 3 | API integration testleri | - |
| Gün 4 | E2E testleri ve UI doğrulama | - |
| Gün 5 | Performance testleri ve raporlama | - |

---

## 10. Başarı Kriterleri

### 10.1 Test Coverage Hedefleri

| Bileşen | Hedef Coverage | Minimum Coverage |
|---------|---------------|------------------|
| PSO-Split Strategy | 90% | 80% |
| HHO-Split Strategy | 90% | 80% |
| GWO-Split Strategy | 90% | 80% |
| Strategy Registry | 95% | 85% |
| Split Decoder | 85% | 75% |

### 10.2 Fonksiyonel Kriterler

- [ ] Tüm Pipeline B algoritmaları başarıyla çalışıyor
- [ ] Registry'den tüm algoritmalara erişilebiliyor
- [ ] UI'dan algoritma seçimi çalışıyor
- [ ] Sonuç formatı tutarlı
- [ ] Pipeline A algoritmaları bozulmamış

### 10.3 Performance Kriterleri

- [ ] N=30 için < 10 saniye
- [ ] N=100 için < 60 saniye
- [ ] N=300 için < 300 saniye (OR-Tools/PyVRP/VROOM)
- [ ] Pipeline B, Pipeline A'dan daha az araç üretiyor (ortalama)

---

## 11. Riskler ve Mitigasyon

| Risk | Olasılık | Etki | Mitigasyon |
|------|----------|------|------------|
| Split Decoder hatalı çalışıyor | Düşük | Yüksek | Unit test ile doğrulama |
| Registry'de naming mismatch | Orta | Yüksek | Integration test ile kontrol |
| Frontend-backend uyumsuzluğu | Orta | Orta | E2E test ile doğrulama |
| Performance beklentilerinin altında | Düşük | Orta | Benchmark testleri |

---

*Bu test planı 28 Mart 2026 tarihinde Sprint 1 tamamlandıktan sonra uygulanacaktır.*
