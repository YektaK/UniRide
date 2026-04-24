# 🏆 MASTER Akademik Parametre Optimizasyonu Raporu
> Bu rapor `analyze_tuning.py` tarafından üretilmiş olup, **TÜM geçmiş koşu dosyalarındaki verilerin kümülatif olarak birleştirilmesiyle** (Problem ve Algoritma bazında) ANOVA / Taguchi analizlerini barındırır.
---
## Elde Edilen Bulgular

### 2-opt (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 18
- **En İyi Ortalama Sonuç**: 7766.8
- **Taguchi S/N Oranı**: -78.0961 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 2000,
  "first_improvement": true,
  "num_starts": 10
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 22.9473 | Evet | Evet |
| 2 | first_improvement | 2.5004 | Hayır | Hayır |
| 3 | max_iterations | 0.0468 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 8013.23
  - Seviye 2000: 8046.60
  - Seviye 500: 8029.40

*first_improvement*:
  - Seviye False: 8093.38
  - Seviye True: 7966.11

*num_starts*:
  - Seviye 1: 8239.63
  - Seviye 10: 7896.00
  - Seviye 5: 7953.60

### 3-opt (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 18
- **En İyi Ortalama Sonuç**: 7821.4
- **Taguchi S/N Oranı**: -78.1571 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 800,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 10.0303 | Evet | Evet |
| 2 | first_improvement | 3.4325 | Evet | Hayır |
| 3 | max_iterations | 0.0513 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 200: 8072.43
  - Seviye 400: 8086.47
  - Seviye 800: 8101.93

*first_improvement*:
  - Seviye False: 8148.36
  - Seviye True: 8025.53

*num_starts*:
  - Seviye 1: 8239.63
  - Seviye 3: 8039.57
  - Seviye 5: 7981.63

### GA (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 7563.0
- **Taguchi S/N Oranı**: -77.7443 dB

**En İyi Parametre Seti**:
```json
{
  "population_size": 120,
  "generations": 200,
  "crossover_rate": 0.75,
  "mutation_rate": 0.1,
  "elite_count": 1
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | population_size | 12.1131 | Evet | Evet |
| 2 | generations | 0.8671 | Hayır | Hayır |
| 3 | mutation_rate | 0.6459 | Hayır | Hayır |
| 4 | crossover_rate | 0.2706 | Hayır | Hayır |
| 5 | elite_count | 0.0152 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*population_size*:
  - Seviye 120: 7663.94
  - Seviye 40: 7772.32
  - Seviye 80: 7696.49

*generations*:
  - Seviye 100: 7722.71
  - Seviye 200: 7697.69

*crossover_rate*:
  - Seviye 0.75: 7705.31
  - Seviye 0.85: 7719.21

*mutation_rate*:
  - Seviye 0.1: 7702.99
  - Seviye 0.25: 7724.43

*elite_count*:
  - Seviye 1: 7711.04
  - Seviye 3: 7714.37

### Or-opt (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 7968.0
- **Taguchi S/N Oranı**: -78.435 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 300,
  "max_segment_size": 3,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_segment_size | 10.5891 | Evet | Evet |
| 2 | num_starts | 6.4056 | Evet | Evet |
| 3 | max_iterations | 0.3954 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 8285.27
  - Seviye 300: 8380.18
  - Seviye 600: 8377.36

*max_segment_size*:
  - Seviye 1: 8579.49
  - Seviye 2: 8281.87
  - Seviye 3: 8181.44

*num_starts*:
  - Seviye 1: 8549.96
  - Seviye 3: 8279.62
  - Seviye 5: 8213.22

### PSO (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 7638.6
- **Taguchi S/N Oranı**: -77.7797 dB

**En İyi Parametre Seti**:
```json
{
  "swarm_size": 60,
  "max_iterations": 300,
  "inertia_weight": 0.9,
  "cognitive_coeff": 2.0
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | swarm_size | 15.0925 | Evet | Evet |
| 2 | cognitive_coeff | 2.9641 | Hayır | Hayır |
| 3 | max_iterations | 0.7376 | Hayır | Hayır |
| 4 | inertia_weight | 0.4018 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*swarm_size*:
  - Seviye 20: 7817.80
  - Seviye 40: 7740.90
  - Seviye 60: 7681.78

*max_iterations*:
  - Seviye 100: 7742.13
  - Seviye 200: 7766.13
  - Seviye 300: 7723.67

*inertia_weight*:
  - Seviye 0.6: 7728.60
  - Seviye 0.729: 7745.70
  - Seviye 0.9: 7759.53

*cognitive_coeff*:
  - Seviye 1.0: 7689.63
  - Seviye 1.49445: 7763.36
  - Seviye 2.0: 7762.56

### 2-opt (Problem: eil76)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 18
- **En İyi Ortalama Sonuç**: 559.0
- **Taguchi S/N Oranı**: -55.1501 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "first_improvement": true,
  "num_starts": 10
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 14.438 | Evet | Evet |
| 2 | first_improvement | 5.0228 | Evet | Evet |
| 3 | max_iterations | 0.0065 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 572.13
  - Seviye 2000: 572.37
  - Seviye 500: 571.70

*first_improvement*:
  - Seviye False: 576.67
  - Seviye True: 567.47

*num_starts*:
  - Seviye 1: 582.77
  - Seviye 10: 565.47
  - Seviye 5: 567.97

### 3-opt (Problem: eil76)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 18
- **En İyi Ortalama Sonuç**: 563.8
- **Taguchi S/N Oranı**: -55.5098 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 400,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_iterations | 4.7034 | Evet | Evet |
| 2 | first_improvement | 2.0099 | Hayır | Hayır |
| 3 | num_starts | 0.4204 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 200: 634.83
  - Seviye 400: 574.80
  - Seviye 800: 574.07

*first_improvement*:
  - Seviye False: 579.24
  - Seviye True: 609.89

*num_starts*:
  - Seviye 1: 605.70
  - Seviye 3: 597.63
  - Seviye 5: 580.37

### GA (Problem: eil76)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 554.6
- **Taguchi S/N Oranı**: -54.966 dB

**En İyi Parametre Seti**:
```json
{
  "population_size": 120,
  "generations": 100,
  "crossover_rate": 0.85,
  "mutation_rate": 0.25,
  "elite_count": 1
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | population_size | 13.4281 | Evet | Evet |
| 2 | elite_count | 2.0795 | Hayır | Hayır |
| 3 | mutation_rate | 0.1404 | Hayır | Hayır |
| 4 | generations | 0.0355 | Hayır | Hayır |
| 5 | crossover_rate | 0.0087 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*population_size*:
  - Seviye 120: 557.96
  - Seviye 40: 562.18
  - Seviye 80: 560.34

*generations*:
  - Seviye 100: 560.06
  - Seviye 200: 560.25

*crossover_rate*:
  - Seviye 0.75: 560.09
  - Seviye 0.85: 560.19

*mutation_rate*:
  - Seviye 0.1: 559.97
  - Seviye 0.25: 560.35

*elite_count*:
  - Seviye 1: 559.52
  - Seviye 3: 560.92

### Or-opt (Problem: eil76)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 576.0
- **Taguchi S/N Oranı**: -56.577 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 600,
  "max_segment_size": 3,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_iterations | 109.7205 | Evet | Evet |
| 2 | num_starts | 0.6111 | Hayır | Hayır |
| 3 | max_segment_size | 0.0505 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 604.20
  - Seviye 300: 793.44
  - Seviye 600: 605.64

*max_segment_size*:
  - Seviye 1: 674.96
  - Seviye 2: 668.20
  - Seviye 3: 660.13

*num_starts*:
  - Seviye 1: 695.67
  - Seviye 3: 661.09
  - Seviye 5: 646.53

### PSO (Problem: eil76)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 555.2
- **Taguchi S/N Oranı**: -54.9518 dB

**En İyi Parametre Seti**:
```json
{
  "swarm_size": 60,
  "max_iterations": 300,
  "inertia_weight": 0.6,
  "cognitive_coeff": 1.0
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | swarm_size | 7.5894 | Evet | Evet |
| 2 | cognitive_coeff | 2.4213 | Hayır | Hayır |
| 3 | inertia_weight | 0.4867 | Hayır | Hayır |
| 4 | max_iterations | 0.0653 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*swarm_size*:
  - Seviye 20: 561.23
  - Seviye 40: 559.18
  - Seviye 60: 557.49

*max_iterations*:
  - Seviye 100: 559.13
  - Seviye 200: 559.47
  - Seviye 300: 559.07

*inertia_weight*:
  - Seviye 0.6: 558.68
  - Seviye 0.729: 559.25
  - Seviye 0.9: 559.80

*cognitive_coeff*:
  - Seviye 1.0: 558.00
  - Seviye 1.49445: 558.96
  - Seviye 2.0: 560.49

---
## Yorum ve Sonuç
En yüksek F değerine sahip parametre, sonucu en fazla etkileyen faktördür. Taguchi S/N oranı yüksek olan kombinasyonlar, hem düşük ortalama hem de düşük değişkenlik sağlar. Akademik makale için tablolarda ANOVA F ve Taguchi S/N değerleri sunulabilir.
