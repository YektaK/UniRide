# 🏆 MASTER Akademik Parametre Optimizasyonu Raporu
> Bu rapor `analyze_tuning.py` tarafından üretilmiş olup, **TÜM geçmiş koşu dosyalarındaki verilerin kümülatif olarak birleştirilmesiyle** (Problem ve Algoritma bazında) ANOVA / Taguchi analizlerini barındırır.
---
## Elde Edilen Bulgular

### 2-opt (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 30
- **En İyi Ortalama Sonuç**: 7766.8
- **Taguchi S/N Oranı**: -78.1171 dB

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
| 1 | num_starts | 24.5121 | Evet | Evet |
| 2 | first_improvement | 6.1481 | Evet | Evet |
| 3 | max_iterations | 0.165 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 8029.53
  - Seviye 2000: 8046.60
  - Seviye 500: 8070.53

*first_improvement*:
  - Seviye False: 8130.54
  - Seviye True: 7987.26

*num_starts*:
  - Seviye 1: 8211.07
  - Seviye 10: 7896.00
  - Seviye 5: 7964.30

### 3-opt (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 22
- **En İyi Ortalama Sonuç**: 7821.4
- **Taguchi S/N Oranı**: -78.1493 dB

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
| 1 | num_starts | 12.3374 | Evet | Evet |
| 2 | first_improvement | 4.0858 | Evet | Evet |
| 3 | max_iterations | 0.0924 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 200: 8072.43
  - Seviye 300: 8029.50
  - Seviye 400: 8086.47
  - Seviye 500: 8066.00
  - Seviye 800: 8101.93

*first_improvement*:
  - Seviye False: 8148.36
  - Seviye True: 8032.37

*num_starts*:
  - Seviye 1: 8213.48
  - Seviye 3: 8039.57
  - Seviye 5: 7976.35

### GA (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 35
- **En İyi Ortalama Sonuç**: 7563.0
- **Taguchi S/N Oranı**: -77.7429 dB

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
| 1 | population_size | 10.1214 | Evet | Evet |
| 2 | mutation_rate | 0.6858 | Hayır | Hayır |
| 3 | crossover_rate | 0.1541 | Hayır | Hayır |
| 4 | generations | 0.1199 | Hayır | Hayır |
| 5 | elite_count | 0.0245 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*population_size*:
  - Seviye 100: 7649.50
  - Seviye 120: 7663.94
  - Seviye 40: 7772.32
  - Seviye 50: 7765.34
  - Seviye 80: 7696.49

*generations*:
  - Seviye 100: 7714.80
  - Seviye 200: 7706.75

*crossover_rate*:
  - Seviye 0.75: 7705.31
  - Seviye 0.8: 7707.42
  - Seviye 0.85: 7719.21

*mutation_rate*:
  - Seviye 0.1: 7704.53
  - Seviye 0.25: 7724.43

*elite_count*:
  - Seviye 1: 7711.04
  - Seviye 2: 7707.42
  - Seviye 3: 7714.37

### Or-opt (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 31
- **En İyi Ortalama Sonuç**: 7968.0
- **Taguchi S/N Oranı**: -78.4315 dB

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
| 1 | num_starts | 9.1034 | Evet | Evet |
| 2 | max_segment_size | 8.3828 | Evet | Evet |
| 3 | max_iterations | 1.1399 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 8285.27
  - Seviye 300: 8394.77
  - Seviye 500: 7968.33
  - Seviye 600: 8377.36

*max_segment_size*:
  - Seviye 1: 8579.49
  - Seviye 2: 8265.04
  - Seviye 3: 8227.33

*num_starts*:
  - Seviye 1: 8548.21
  - Seviye 3: 8279.62
  - Seviye 5: 8192.94

### PSO (Problem: berlin52)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 35
- **En İyi Ortalama Sonuç**: 7595.67
- **Taguchi S/N Oranı**: -77.7622 dB

**En İyi Parametre Seti**:
```json
{
  "swarm_size": 50,
  "max_iterations": 200,
  "inertia_weight": 0.729,
  "cognitive_coeff": 1.494
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | swarm_size | 8.5878 | Evet | Evet |
| 2 | cognitive_coeff | 4.4751 | Evet | Evet |
| 3 | inertia_weight | 1.2639 | Hayır | Hayır |
| 4 | max_iterations | 0.0308 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*swarm_size*:
  - Seviye 20: 7781.70
  - Seviye 40: 7740.90
  - Seviye 50: 7642.00
  - Seviye 60: 7681.78

*max_iterations*:
  - Seviye 100: 7728.14
  - Seviye 200: 7731.89
  - Seviye 300: 7723.67

*inertia_weight*:
  - Seviye 0.6: 7728.60
  - Seviye 0.729: 7710.73
  - Seviye 0.9: 7759.53

*cognitive_coeff*:
  - Seviye 1.0: 7689.63
  - Seviye 1.494: 7675.75
  - Seviye 1.49445: 7763.36
  - Seviye 2.0: 7762.56

### 2-opt (Problem: eil51)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 439.0
- **Taguchi S/N Oranı**: -52.956 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 1000,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_iterations | 2.522 | Hayır | Hayır |
| 2 | num_starts | 0.8283 | Hayır | Hayır |
| 3 | first_improvement | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 442.00
  - Seviye 500: 446.83

*first_improvement*:
  - Seviye True: 444.41

*num_starts*:
  - Seviye 1: 446.16
  - Seviye 5: 442.66

### 3-opt (Problem: eil51)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 439.0
- **Taguchi S/N Oranı**: -52.956 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_iterations | 2.522 | Hayır | Hayır |
| 2 | num_starts | 0.8283 | Hayır | Hayır |
| 3 | first_improvement | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 300: 446.83
  - Seviye 500: 442.00

*first_improvement*:
  - Seviye True: 444.41

*num_starts*:
  - Seviye 1: 446.16
  - Seviye 5: 442.66

### GA (Problem: eil51)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 31
- **En İyi Ortalama Sonuç**: 430.6
- **Taguchi S/N Oranı**: -52.7487 dB

**En İyi Parametre Seti**:
```json
{
  "population_size": 120,
  "generations": 200,
  "crossover_rate": 0.85,
  "mutation_rate": 0.1,
  "elite_count": 1
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | population_size | 9.9069 | Evet | Evet |
| 2 | generations | 0.5106 | Hayır | Hayır |
| 3 | crossover_rate | 0.1413 | Hayır | Hayır |
| 4 | elite_count | 0.1257 | Hayır | Hayır |
| 5 | mutation_rate | 0.0119 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*population_size*:
  - Seviye 100: 432.66
  - Seviye 120: 432.48
  - Seviye 40: 435.32
  - Seviye 50: 435.84
  - Seviye 80: 433.89

*generations*:
  - Seviye 100: 434.13
  - Seviye 200: 433.69

*crossover_rate*:
  - Seviye 0.75: 433.77
  - Seviye 0.8: 434.25
  - Seviye 0.85: 434.01

*mutation_rate*:
  - Seviye 0.1: 433.97
  - Seviye 0.25: 433.90

*elite_count*:
  - Seviye 1: 433.80
  - Seviye 2: 434.25
  - Seviye 3: 434.02

### Or-opt (Problem: eil51)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 452.33
- **Taguchi S/N Oranı**: -53.6178 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "max_segment_size": 2,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 25.2665 | Evet | Evet |
| 2 | max_iterations | 1.3528 | Hayır | Hayır |
| 3 | max_segment_size | 0.2781 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 300: 487.89
  - Seviye 500: 452.33

*max_segment_size*:
  - Seviye 2: 474.11
  - Seviye 3: 493.67

*num_starts*:
  - Seviye 1: 502.34
  - Seviye 5: 455.66

### PSO (Problem: eil51)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 31
- **En İyi Ortalama Sonuç**: 431.8
- **Taguchi S/N Oranı**: -52.7524 dB

**En İyi Parametre Seti**:
```json
{
  "swarm_size": 40,
  "max_iterations": 100,
  "inertia_weight": 0.6,
  "cognitive_coeff": 1.0
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | swarm_size | 11.4548 | Evet | Evet |
| 2 | inertia_weight | 2.4138 | Hayır | Hayır |
| 3 | cognitive_coeff | 1.1711 | Hayır | Hayır |
| 4 | max_iterations | 0.3829 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*swarm_size*:
  - Seviye 20: 436.14
  - Seviye 40: 433.16
  - Seviye 50: 433.66
  - Seviye 60: 433.07

*max_iterations*:
  - Seviye 100: 434.12
  - Seviye 200: 434.47
  - Seviye 300: 433.71

*inertia_weight*:
  - Seviye 0.6: 433.14
  - Seviye 0.729: 434.83
  - Seviye 0.9: 434.29

*cognitive_coeff*:
  - Seviye 1.0: 433.54
  - Seviye 1.494: 435.58
  - Seviye 1.49445: 433.80
  - Seviye 2.0: 434.33

### 2-opt (Problem: eil76)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 26
- **En İyi Ortalama Sonuç**: 559.0
- **Taguchi S/N Oranı**: -55.1353 dB

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
| 1 | num_starts | 17.6628 | Evet | Evet |
| 2 | first_improvement | 4.856 | Evet | Evet |
| 3 | max_iterations | 0.3498 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 572.13
  - Seviye 1500: 566.66
  - Seviye 2000: 572.37
  - Seviye 500: 571.49

*first_improvement*:
  - Seviye False: 574.80
  - Seviye True: 567.40

*num_starts*:
  - Seviye 1: 579.79
  - Seviye 10: 564.28
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
- **Havuzdaki Toplam Kombinasyon Kaydı**: 35
- **En İyi Ortalama Sonuç**: 554.6
- **Taguchi S/N Oranı**: -54.9585 dB

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
| 1 | population_size | 8.5993 | Evet | Evet |
| 2 | elite_count | 2.9939 | Hayır | Hayır |
| 3 | crossover_rate | 1.942 | Hayır | Hayır |
| 4 | generations | 1.7509 | Hayır | Hayır |
| 5 | mutation_rate | 0.609 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*population_size*:
  - Seviye 120: 557.96
  - Seviye 150: 556.33
  - Seviye 40: 562.18
  - Seviye 50: 559.67
  - Seviye 80: 560.34

*generations*:
  - Seviye 100: 559.78
  - Seviye 200: 560.25
  - Seviye 300: 557.33

*crossover_rate*:
  - Seviye 0.75: 560.09
  - Seviye 0.8: 558.00
  - Seviye 0.85: 560.19

*mutation_rate*:
  - Seviye 0.05: 559.66
  - Seviye 0.1: 559.21
  - Seviye 0.25: 560.35

*elite_count*:
  - Seviye 1: 559.52
  - Seviye 2: 558.00
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
- **Havuzdaki Toplam Kombinasyon Kaydı**: 31
- **En İyi Ortalama Sonuç**: 555.2
- **Taguchi S/N Oranı**: -54.953 dB

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
| 1 | swarm_size | 7.8523 | Evet | Evet |
| 2 | cognitive_coeff | 1.334 | Hayır | Hayır |
| 3 | inertia_weight | 0.4391 | Hayır | Hayır |
| 4 | max_iterations | 0.0244 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*swarm_size*:
  - Seviye 20: 561.23
  - Seviye 30: 563.50
  - Seviye 40: 559.18
  - Seviye 60: 557.49
  - Seviye 70: 556.17

*max_iterations*:
  - Seviye 100: 559.26
  - Seviye 200: 559.47
  - Seviye 300: 559.21

*inertia_weight*:
  - Seviye 0.6: 558.68
  - Seviye 0.729: 559.44
  - Seviye 0.9: 559.80

*cognitive_coeff*:
  - Seviye 1.0: 558.00
  - Seviye 1.494: 559.84
  - Seviye 1.49445: 558.96
  - Seviye 2.0: 560.49

### 2-opt (Problem: kroA100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 21935.0
- **Taguchi S/N Oranı**: -86.8906 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 1.3808 | Hayır | Hayır |
| 2 | max_iterations | 0.2405 | Hayır | Hayır |
| 3 | first_improvement | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 22050.67
  - Seviye 500: 22162.17

*first_improvement*:
  - Seviye True: 22106.42

*num_starts*:
  - Seviye 1: 22215.17
  - Seviye 5: 21997.67

### 3-opt (Problem: kroA100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 22041.0
- **Taguchi S/N Oranı**: -90.1722 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "first_improvement": true,
  "num_starts": 1
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_iterations | 115.8297 | Evet | Evet |
| 2 | num_starts | 0.0169 | Hayır | Hayır |
| 3 | first_improvement | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 300: 39898.67
  - Seviye 500: 22050.67

*first_improvement*:
  - Seviye True: 30974.67

*num_starts*:
  - Seviye 1: 31799.00
  - Seviye 5: 30150.33

### GA (Problem: kroA100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 21605.67
- **Taguchi S/N Oranı**: -86.762 dB

**En İyi Parametre Seti**:
```json
{
  "population_size": 100,
  "generations": 200,
  "crossover_rate": 0.8,
  "mutation_rate": 0.1,
  "elite_count": 2
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | population_size | 1.0925 | Hayır | Hayır |
| 2 | generations | 0.2533 | Hayır | Hayır |
| 3 | crossover_rate | 0.0 | Hayır | Hayır |
| 4 | mutation_rate | 0.0 | Hayır | Hayır |
| 5 | elite_count | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*population_size*:
  - Seviye 100: 21718.83
  - Seviye 50: 21845.00

*generations*:
  - Seviye 100: 21817.50
  - Seviye 200: 21746.33

*crossover_rate*:
  - Seviye 0.8: 21781.92

*mutation_rate*:
  - Seviye 0.1: 21781.92

*elite_count*:
  - Seviye 2: 21781.92

### Or-opt (Problem: kroA100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 8
- **En İyi Ortalama Sonuç**: 48360.0
- **Taguchi S/N Oranı**: -97.8539 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "max_segment_size": 2,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_iterations | 218.91 | Evet | Evet |
| 2 | num_starts | 5.1741 | Evet | Evet |
| 3 | max_segment_size | 1.6733 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 300: 85705.45
  - Seviye 500: 48360.00

*max_segment_size*:
  - Seviye 2: 71949.89
  - Seviye 3: 89626.67

*num_starts*:
  - Seviye 1: 87522.83
  - Seviye 5: 65215.33

### PSO (Problem: kroA100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 21688.33
- **Taguchi S/N Oranı**: -86.7675 dB

**En İyi Parametre Seti**:
```json
{
  "swarm_size": 50,
  "max_iterations": 100,
  "inertia_weight": 0.729,
  "cognitive_coeff": 1.494
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | swarm_size | 0.5322 | Hayır | Hayır |
| 2 | max_iterations | 0.1318 | Hayır | Hayır |
| 3 | inertia_weight | 0.0 | Hayır | Hayır |
| 4 | cognitive_coeff | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*swarm_size*:
  - Seviye 20: 21841.83
  - Seviye 50: 21749.33

*max_iterations*:
  - Seviye 100: 21820.67
  - Seviye 200: 21770.50

*inertia_weight*:
  - Seviye 0.729: 21795.58

*cognitive_coeff*:
  - Seviye 1.494: 21795.58

### 2-opt (Problem: rd100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 8231.0
- **Taguchi S/N Oranı**: -78.4943 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 14.35 | Evet | Evet |
| 2 | max_iterations | 0.2329 | Hayır | Hayır |
| 3 | first_improvement | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 8457.50
  - Seviye 500: 8356.50

*first_improvement*:
  - Seviye True: 8407.00

*num_starts*:
  - Seviye 1: 8553.50
  - Seviye 5: 8260.50

### 3-opt (Problem: rd100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 8290.0
- **Taguchi S/N Oranı**: -80.8421 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_iterations | 6.7625 | Evet | Evet |
| 2 | num_starts | 0.3149 | Hayır | Hayır |
| 3 | first_improvement | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 300: 12971.33
  - Seviye 500: 8457.50

*first_improvement*:
  - Seviye True: 10714.42

*num_starts*:
  - Seviye 1: 11662.00
  - Seviye 5: 9766.83

### GA (Problem: rd100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 8091.33
- **Taguchi S/N Oranı**: -78.2329 dB

**En İyi Parametre Seti**:
```json
{
  "population_size": 100,
  "generations": 100,
  "crossover_rate": 0.8,
  "mutation_rate": 0.1,
  "elite_count": 2
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | generations | 11.082 | Evet | Evet |
| 2 | population_size | 0.0595 | Hayır | Hayır |
| 3 | crossover_rate | 0.0 | Hayır | Hayır |
| 4 | mutation_rate | 0.0 | Hayır | Hayır |
| 5 | elite_count | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*population_size*:
  - Seviye 100: 8169.33
  - Seviye 50: 8148.50

*generations*:
  - Seviye 100: 8102.50
  - Seviye 200: 8215.33

*crossover_rate*:
  - Seviye 0.8: 8158.91

*mutation_rate*:
  - Seviye 0.1: 8158.91

*elite_count*:
  - Seviye 2: 8158.91

### Or-opt (Problem: rd100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 8
- **En İyi Ortalama Sonuç**: 13860.33
- **Taguchi S/N Oranı**: -87.5932 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "max_segment_size": 2,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_iterations | 119.5574 | Evet | Evet |
| 2 | num_starts | 4.1709 | Evet | Evet |
| 3 | max_segment_size | 2.353 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 300: 26458.11
  - Seviye 500: 13860.33

*max_segment_size*:
  - Seviye 2: 21595.66
  - Seviye 3: 28447.67

*num_starts*:
  - Seviye 1: 26888.50
  - Seviye 5: 19728.83

### PSO (Problem: rd100)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 8119.0
- **Taguchi S/N Oranı**: -78.2046 dB

**En İyi Parametre Seti**:
```json
{
  "swarm_size": 20,
  "max_iterations": 100,
  "inertia_weight": 0.729,
  "cognitive_coeff": 1.494
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | swarm_size | 2.3505 | Hayır | Hayır |
| 2 | max_iterations | 1.5296 | Hayır | Hayır |
| 3 | inertia_weight | 0.0 | Hayır | Hayır |
| 4 | cognitive_coeff | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*swarm_size*:
  - Seviye 20: 8126.16
  - Seviye 50: 8139.00

*max_iterations*:
  - Seviye 100: 8126.84
  - Seviye 200: 8138.33

*inertia_weight*:
  - Seviye 0.729: 8132.58

*cognitive_coeff*:
  - Seviye 1.494: 8132.58

### 2-opt (Problem: st70)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 691.33
- **Taguchi S/N Oranı**: -56.8816 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 3.4483 | Evet | Hayır |
| 2 | max_iterations | 0.1208 | Hayır | Hayır |
| 3 | first_improvement | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 1000: 696.83
  - Seviye 500: 699.83

*first_improvement*:
  - Seviye True: 698.33

*num_starts*:
  - Seviye 1: 703.33
  - Seviye 5: 693.33

### 3-opt (Problem: st70)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 691.33
- **Taguchi S/N Oranı**: -56.8816 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 300,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 3.4483 | Evet | Hayır |
| 2 | max_iterations | 0.1208 | Hayır | Hayır |
| 3 | first_improvement | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 300: 699.83
  - Seviye 500: 696.83

*first_improvement*:
  - Seviye True: 698.33

*num_starts*:
  - Seviye 1: 703.33
  - Seviye 5: 693.33

### GA (Problem: st70)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 682.0
- **Taguchi S/N Oranı**: -56.7223 dB

**En İyi Parametre Seti**:
```json
{
  "population_size": 100,
  "generations": 200,
  "crossover_rate": 0.8,
  "mutation_rate": 0.1,
  "elite_count": 2
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | population_size | 5.547 | Evet | Evet |
| 2 | generations | 0.4502 | Hayır | Hayır |
| 3 | crossover_rate | 0.0 | Hayır | Hayır |
| 4 | mutation_rate | 0.0 | Hayır | Hayır |
| 5 | elite_count | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*population_size*:
  - Seviye 100: 683.66
  - Seviye 50: 687.66

*generations*:
  - Seviye 100: 686.66
  - Seviye 200: 684.66

*crossover_rate*:
  - Seviye 0.8: 685.66

*mutation_rate*:
  - Seviye 0.1: 685.66

*elite_count*:
  - Seviye 2: 685.66

### Or-opt (Problem: st70)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 8
- **En İyi Ortalama Sonuç**: 760.33
- **Taguchi S/N Oranı**: -60.1736 dB

**En İyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "max_segment_size": 2,
  "num_starts": 5
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 44.1494 | Evet | Evet |
| 2 | max_iterations | 12.6005 | Evet | Evet |
| 3 | max_segment_size | 2.8327 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*max_iterations*:
  - Seviye 300: 1087.33
  - Seviye 500: 760.33

*max_segment_size*:
  - Seviye 2: 949.33
  - Seviye 3: 1174.33

*num_starts*:
  - Seviye 1: 1167.00
  - Seviye 5: 844.16

### PSO (Problem: st70)
- **Havuzdaki Toplam Kombinasyon Kaydı**: 4
- **En İyi Ortalama Sonuç**: 682.33
- **Taguchi S/N Oranı**: -56.7297 dB

**En İyi Parametre Seti**:
```json
{
  "swarm_size": 50,
  "max_iterations": 200,
  "inertia_weight": 0.729,
  "cognitive_coeff": 1.494
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | max_iterations | 3.7481 | Evet | Hayır |
| 2 | swarm_size | 1.0348 | Hayır | Hayır |
| 3 | inertia_weight | 0.0 | Hayır | Hayır |
| 4 | cognitive_coeff | 0.0 | Hayır | Hayır |

**Parametre Seviye Etkileri (Ortalama Değerler)**:

*swarm_size*:
  - Seviye 20: 688.00
  - Seviye 50: 684.50

*max_iterations*:
  - Seviye 100: 688.67
  - Seviye 200: 683.83

*inertia_weight*:
  - Seviye 0.729: 686.25

*cognitive_coeff*:
  - Seviye 1.494: 686.25

---
## Yorum ve Sonuç
En yüksek F değerine sahip parametre, sonucu en fazla etkileyen faktördür. Taguchi S/N oranı yüksek olan kombinasyonlar, hem düşük ortalama hem de düşük değişkenlik sağlar. Akademik makale için tablolarda ANOVA F ve Taguchi S/N değerleri sunulabilir.
