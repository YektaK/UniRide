# Akademik Parametre Optimizasyonu - ANOVA ve Taguchi Analizi
---
## Elde Edilen Bulgular

### 2-opt
- **Problem**: eil51
- **Toplam Kombinasyon Sayisi**: 24
- **En Iyi Ortalama Sonuc**: 432.0 ± 2.1602
- **Taguchi S/N Orani**: -52.8665 dB

**En Iyi Parametre Seti**:
```json
{
  "max_iterations": 500,
  "first_improvement": true,
  "num_starts": 10
}
```

**Parametre Onem Sirasi (ANOVA F-Istatistigine Gore)**:
| Siralama | Parametre | F Degeri | %5 Anlamlilik | %1 Anlamlilik |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 27.5338 | Evet | Evet |
| 2 | first_improvement | 2.856 | Hayir | Hayir |
| 3 | max_iterations | 0.2103 | Hayir | Hayir |

**Parametre Seviye Etkileri (Ortalama Degerler)**:

*max_iterations*:
  - Seviye 1000: 440.05
  - Seviye 2000: 438.68
  - Seviye 500: 440.76

*first_improvement*:
  - Seviye False: 441.93
  - Seviye True: 437.73

*num_starts*:
  - Seviye 1: 449.15
  - Seviye 10: 434.73
  - Seviye 3: 438.53
  - Seviye 5: 436.90

### 3-opt
- **Problem**: eil51
- **Toplam Kombinasyon Sayisi**: 18
- **En Iyi Ortalama Sonuc**: 434.0 ± 2.0
- **Taguchi S/N Orani**: -52.8664 dB

**En Iyi Parametre Seti**:
```json
{
  "max_iterations": 400,
  "first_improvement": true,
  "num_starts": 5
}
```

**Parametre Onem Sirasi (ANOVA F-Istatistigine Gore)**:
| Siralama | Parametre | F Degeri | %5 Anlamlilik | %1 Anlamlilik |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 15.6946 | Evet | Evet |
| 2 | first_improvement | 3.4603 | Evet | Hayir |
| 3 | max_iterations | 0.2793 | Hayir | Hayir |

**Parametre Seviye Etkileri (Ortalama Degerler)**:

*max_iterations*:
  - Seviye 200: 439.58
  - Seviye 400: 438.92
  - Seviye 800: 441.02

*first_improvement*:
  - Seviye False: 441.79
  - Seviye True: 437.89

*num_starts*:
  - Seviye 1: 444.82
  - Seviye 3: 439.12
  - Seviye 5: 435.58

### GA
- **Problem**: eil51
- **Toplam Kombinasyon Sayisi**: 27
- **En Iyi Ortalama Sonuc**: 440.5 ± 6.1328
- **Taguchi S/N Orani**: -52.9895 dB

**En Iyi Parametre Seti**:
```json
{
  "population_size": 40,
  "generations": 100,
  "crossover_rate": 0.75,
  "mutation_rate": 0.25,
  "elite_count": 3
}
```

**Parametre Onem Sirasi (ANOVA F-Istatistigine Gore)**:
| Siralama | Parametre | F Degeri | %5 Anlamlilik | %1 Anlamlilik |
|----------|-----------|----------|---------------|---------------|
| 1 | mutation_rate | 3.1283 | Evet | Hayir |
| 2 | elite_count | 0.3129 | Hayir | Hayir |
| 3 | crossover_rate | 0.1448 | Hayir | Hayir |
| 4 | population_size | 0.0 | Hayir | Hayir |
| 5 | generations | 0.0 | Hayir | Hayir |

**Parametre Seviye Etkileri (Ortalama Degerler)**:

*population_size*:
  - Seviye 40: 446.13

*generations*:
  - Seviye 100: 446.13

*crossover_rate*:
  - Seviye 0.75: 445.68
  - Seviye 0.85: 446.21
  - Seviye 0.95: 446.51

*mutation_rate*:
  - Seviye 0.05: 448.14
  - Seviye 0.15: 444.89
  - Seviye 0.25: 445.37

*elite_count*:
  - Seviye 1: 446.47
  - Seviye 2: 446.51
  - Seviye 3: 445.42

### Or-opt
- **Problem**: eil51
- **Toplam Kombinasyon Sayisi**: 18
- **En Iyi Ortalama Sonuc**: 443.6 ± 6.0406
- **Taguchi S/N Orani**: -53.1917 dB

**En Iyi Parametre Seti**:
```json
{
  "max_iterations": 300,
  "max_segment_size": 3,
  "num_starts": 3
}
```

**Parametre Onem Sirasi (ANOVA F-Istatistigine Gore)**:
| Siralama | Parametre | F Degeri | %5 Anlamlilik | %1 Anlamlilik |
|----------|-----------|----------|---------------|---------------|
| 1 | num_starts | 12.9244 | Evet | Evet |
| 2 | max_segment_size | 2.397 | Hayir | Hayir |
| 3 | max_iterations | 0.5114 | Hayir | Hayir |

**Parametre Seviye Etkileri (Ortalama Degerler)**:

*max_iterations*:
  - Seviye 300: 458.41
  - Seviye 600: 454.64

*max_segment_size*:
  - Seviye 1: 463.55
  - Seviye 2: 455.17
  - Seviye 3: 450.87

*num_starts*:
  - Seviye 1: 468.45
  - Seviye 3: 452.02
  - Seviye 5: 449.12

### PSO
- **Problem**: eil51
- **Toplam Kombinasyon Sayisi**: 18
- **En Iyi Ortalama Sonuc**: 438.6 ± 6.802
- **Taguchi S/N Orani**: -52.9287 dB

**En Iyi Parametre Seti**:
```json
{
  "swarm_size": 20,
  "max_iterations": 100,
  "inertia_weight": 0.9,
  "cognitive_coeff": 1.49445
}
```

**Parametre Onem Sirasi (ANOVA F-Istatistigine Gore)**:
| Siralama | Parametre | F Degeri | %5 Anlamlilik | %1 Anlamlilik |
|----------|-----------|----------|---------------|---------------|
| 1 | inertia_weight | 0.4413 | Hayir | Hayir |
| 2 | cognitive_coeff | 0.289 | Hayir | Hayir |
| 3 | max_iterations | 0.0441 | Hayir | Hayir |
| 4 | swarm_size | 0.0 | Hayir | Hayir |

**Parametre Seviye Etkileri (Ortalama Degerler)**:

*swarm_size*:
  - Seviye 20: 443.03

*max_iterations*:
  - Seviye 100: 443.14
  - Seviye 200: 442.91

*inertia_weight*:
  - Seviye 0.6: 443.57
  - Seviye 0.729: 443.20
  - Seviye 0.9: 442.32

*cognitive_coeff*:
  - Seviye 1.0: 442.50
  - Seviye 1.49445: 443.03
  - Seviye 2.0: 443.55

---
## Yorum ve Sonuc
En yuksek F degerine sahip parametre, sonucu en fazla etkileyen faktordur. Taguchi S/N orani yuksek olan kombinasyonlar, hem dusuk ortalama hem de dusuk degiskenlik saglar. Akademik makale icin tablolarda ANOVA F ve p degerleri, ayrica Taguchi S/N degerleri sunulmalidir.
