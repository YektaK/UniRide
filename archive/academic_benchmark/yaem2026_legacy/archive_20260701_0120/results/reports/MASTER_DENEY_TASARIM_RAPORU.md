# Master Akademik Parametre Optimizasyonu Raporu — YAEM 2026

> Bu rapor tüm geçmiş koşu dosyalarındaki verilerin kümülatif birleştirilmesiyle oluşturulmuştur.
---
## Elde Edilen Bulgular

### 2-opt (Problem: berlin52)
- **Toplam Kombinasyon Kaydı**: 18
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

**Parametre Seviye Etkileri**:

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
- **Toplam Kombinasyon Kaydı**: 18
- **En İyi Ortalama Sonuç**: 7908.8
- **Taguchi S/N Oranı**: -78.5702 dB

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
| 1 | num_starts | 4.0108 | Evet | Evet |
| 2 | max_iterations | 2.1313 | Hayır | Hayır |
| 3 | first_improvement | 0.0958 | Hayır | Hayır |

**Parametre Seviye Etkileri**:

*max_iterations*:
  - Seviye 200: 8823.20
  - Seviye 400: 8331.67
  - Seviye 800: 8239.37

*first_improvement*:
  - Seviye False: 8506.78
  - Seviye True: 8422.71

*num_starts*:
  - Seviye 1: 8917.70
  - Seviye 3: 8273.13
  - Seviye 5: 8203.40

### GA (Problem: berlin52)
- **Toplam Kombinasyon Kaydı**: 27
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

**Parametre Seviye Etkileri**:

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

### GWO (Problem: berlin52)
- **Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 7670.2
- **Taguchi S/N Oranı**: -77.8243 dB

**En İyi Parametre Seti**:
```json
{
  "pack_size": 70,
  "max_iterations": 250,
  "initial_a": 2.0,
  "exploration_rate": 0.6,
  "max_no_improvement": 75,
  "polish_interval": 15,
  "polish_iters": 15,
  "final_polish_iters": 300
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | pack_size | 14.3782 | Evet | Evet |
| 2 | polish_iters | 3.1008 | Evet | Hayır |
| 3 | exploration_rate | 0.6124 | Hayır | Hayır |
| 4 | max_no_improvement | 0.5829 | Hayır | Hayır |
| 5 | max_iterations | 0.415 | Hayır | Hayır |
| 6 | initial_a | 0.0323 | Hayır | Hayır |
| 7 | final_polish_iters | 0.0054 | Hayır | Hayır |
| 8 | polish_interval | 0.0014 | Hayır | Hayır |

**Parametre Seviye Etkileri**:

*pack_size*:
  - Seviye 30: 7814.19
  - Seviye 50: 7810.00
  - Seviye 70: 7733.96

*max_iterations*:
  - Seviye 150: 7772.04
  - Seviye 250: 7794.80
  - Seviye 350: 7788.42

*initial_a*:
  - Seviye 1.0: 7781.41
  - Seviye 2.0: 7786.68
  - Seviye 3.0: 7787.00

*exploration_rate*:
  - Seviye 0.2: 7794.02
  - Seviye 0.4: 7796.80
  - Seviye 0.6: 7772.15

*max_no_improvement*:
  - Seviye 100: 7778.49
  - Seviye 50: 7774.52
  - Seviye 75: 7801.07

*polish_interval*:
  - Seviye 15: 7783.87
  - Seviye 25: 7783.67
  - Seviye 35: 7785.35

*polish_iters*:
  - Seviye 10: 7755.72
  - Seviye 15: 7769.02
  - Seviye 5: 7811.85

*final_polish_iters*:
  - Seviye 100: 7782.69
  - Seviye 200: 7785.17
  - Seviye 300: 7784.71

### GWO-ALNS (Problem: berlin52)
- **Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 7542.0
- **Taguchi S/N Oranı**: -77.6195 dB

**En İyi Parametre Seti**:
```json
{
  "pack_size": 50,
  "max_iterations": 250,
  "initial_a": 1.0,
  "exploration_rate": 0.4,
  "max_no_improvement": 50,
  "polish_interval": 15,
  "alns_iterations": 150,
  "alns_remove_ratio": 0.15,
  "final_polish_iters": 100
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | alns_remove_ratio | 6.1671 | Evet | Evet |
| 2 | alns_iterations | 2.782 | Hayır | Hayır |
| 3 | pack_size | 1.6145 | Hayır | Hayır |
| 4 | final_polish_iters | 1.1048 | Hayır | Hayır |
| 5 | exploration_rate | 0.4447 | Hayır | Hayır |
| 6 | max_no_improvement | 0.2651 | Hayır | Hayır |
| 7 | max_iterations | 0.2008 | Hayır | Hayır |
| 8 | polish_interval | 0.1639 | Hayır | Hayır |
| 9 | initial_a | 0.0448 | Hayır | Hayır |

**Parametre Seviye Etkileri**:

*pack_size*:
  - Seviye 30: 7623.51
  - Seviye 50: 7574.83
  - Seviye 70: 7598.76

*max_iterations*:
  - Seviye 150: 7608.82
  - Seviye 250: 7602.74
  - Seviye 350: 7591.06

*initial_a*:
  - Seviye 1.0: 7601.85
  - Seviye 2.0: 7606.60
  - Seviye 3.0: 7597.47

*exploration_rate*:
  - Seviye 0.2: 7607.48
  - Seviye 0.4: 7589.16
  - Seviye 0.6: 7614.97

*max_no_improvement*:
  - Seviye 100: 7612.12
  - Seviye 50: 7607.46
  - Seviye 75: 7593.50

*polish_interval*:
  - Seviye 15: 7594.14
  - Seviye 25: 7606.56
  - Seviye 35: 7609.17

*alns_iterations*:
  - Seviye 100: 7607.38
  - Seviye 150: 7552.48
  - Seviye 50: 7620.69

*alns_remove_ratio*:
  - Seviye 0.1: 7652.12
  - Seviye 0.15: 7588.34
  - Seviye 0.2: 7567.63

*final_polish_iters*:
  - Seviye 100: 7609.16
  - Seviye 200: 7618.40
  - Seviye 300: 7577.90

### GWO-LKH (Problem: berlin52)
- **Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 7748.4
- **Taguchi S/N Oranı**: -77.9024 dB

**En İyi Parametre Seti**:
```json
{
  "pack_size": 50,
  "max_iterations": 250,
  "initial_a": 3.0,
  "exploration_rate": 0.2,
  "max_no_improvement": 100,
  "polish_interval": 15,
  "polish_iters": 5,
  "final_polish_iters": 100
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | pack_size | 4.3587 | Evet | Evet |
| 2 | max_no_improvement | 1.3123 | Hayır | Hayır |
| 3 | exploration_rate | 1.2537 | Hayır | Hayır |
| 4 | polish_interval | 0.8028 | Hayır | Hayır |
| 5 | polish_iters | 0.739 | Hayır | Hayır |
| 6 | max_iterations | 0.5408 | Hayır | Hayır |
| 7 | initial_a | 0.1186 | Hayır | Hayır |
| 8 | final_polish_iters | 0.0516 | Hayır | Hayır |

**Parametre Seviye Etkileri**:

*pack_size*:
  - Seviye 30: 7879.63
  - Seviye 50: 7807.67
  - Seviye 70: 7832.86

*max_iterations*:
  - Seviye 150: 7857.78
  - Seviye 250: 7836.23
  - Seviye 350: 7863.50

*initial_a*:
  - Seviye 1.0: 7849.61
  - Seviye 2.0: 7861.53
  - Seviye 3.0: 7855.92

*exploration_rate*:
  - Seviye 0.2: 7857.91
  - Seviye 0.4: 7820.80
  - Seviye 0.6: 7864.71

*max_no_improvement*:
  - Seviye 100: 7835.69
  - Seviye 50: 7875.02
  - Seviye 75: 7859.20

*polish_interval*:
  - Seviye 15: 7839.98
  - Seviye 25: 7868.45
  - Seviye 35: 7858.40

*polish_iters*:
  - Seviye 10: 7832.96
  - Seviye 15: 7867.64
  - Seviye 5: 7850.69

*final_polish_iters*:
  - Seviye 100: 7851.20
  - Seviye 200: 7853.06
  - Seviye 300: 7859.09

### GWO-Pure (Problem: berlin52)
- **Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 14544.6
- **Taguchi S/N Oranı**: -84.9473 dB

**En İyi Parametre Seti**:
```json
{
  "pack_size": 30,
  "max_iterations": 350,
  "initial_a": 2.0,
  "exploration_rate": 0.6,
  "max_no_improvement": 75
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | pack_size | 4.8515 | Evet | Evet |
| 2 | initial_a | 4.6151 | Evet | Evet |
| 3 | max_iterations | 3.033 | Evet | Hayır |
| 4 | max_no_improvement | 0.4719 | Hayır | Hayır |
| 5 | exploration_rate | 0.1779 | Hayır | Hayır |

**Parametre Seviye Etkileri**:

*pack_size*:
  - Seviye 30: 18328.11
  - Seviye 50: 17380.67
  - Seviye 70: 16362.63

*max_iterations*:
  - Seviye 150: 18572.67
  - Seviye 250: 17322.97
  - Seviye 350: 17027.02

*initial_a*:
  - Seviye 1.0: 18263.17
  - Seviye 2.0: 15944.95
  - Seviye 3.0: 17327.98

*exploration_rate*:
  - Seviye 0.2: 17719.91
  - Seviye 0.4: 17345.47
  - Seviye 0.6: 17751.58

*max_no_improvement*:
  - Seviye 100: 17578.91
  - Seviye 50: 17188.31
  - Seviye 75: 17969.98

### HHO-ALNS (Problem: berlin52)
- **Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 7542.0
- **Taguchi S/N Oranı**: -77.6158 dB

**En İyi Parametre Seti**:
```json
{
  "hawks": 50,
  "max_iterations": 350,
  "initial_energy": 1.0,
  "jump_probability": 0.7,
  "max_no_improvement": 75,
  "dive_count": 5,
  "levy_scale": 0.2,
  "polish_interval": 25,
  "alns_iterations": 100,
  "alns_remove_ratio": 0.15,
  "final_polish_iters": 100
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | alns_iterations | 5.0628 | Evet | Evet |
| 2 | alns_remove_ratio | 4.1383 | Evet | Evet |
| 3 | hawks | 1.9628 | Hayır | Hayır |
| 4 | max_iterations | 1.2157 | Hayır | Hayır |
| 5 | max_no_improvement | 0.6983 | Hayır | Hayır |
| 6 | levy_scale | 0.6343 | Hayır | Hayır |
| 7 | polish_interval | 0.5273 | Hayır | Hayır |
| 8 | jump_probability | 0.3113 | Hayır | Hayır |
| 9 | dive_count | 0.1255 | Hayır | Hayır |
| 10 | initial_energy | 0.0994 | Hayır | Hayır |
| 11 | final_polish_iters | 0.0349 | Hayır | Hayır |

**Parametre Seviye Etkileri**:

*hawks*:
  - Seviye 30: 7622.25
  - Seviye 50: 7561.70
  - Seviye 70: 7590.25

*max_iterations*:
  - Seviye 150: 7569.57
  - Seviye 250: 7606.96
  - Seviye 350: 7616.22

*initial_energy*:
  - Seviye 0.5: 7607.90
  - Seviye 1.0: 7593.98
  - Seviye 1.5: 7598.63

*jump_probability*:
  - Seviye 0.3: 7610.40
  - Seviye 0.5: 7609.57
  - Seviye 0.7: 7589.37

*max_no_improvement*:
  - Seviye 100: 7588.48
  - Seviye 50: 7622.73
  - Seviye 75: 7590.53

*dive_count*:
  - Seviye 2: 7605.37
  - Seviye 3: 7589.30
  - Seviye 5: 7602.45

*levy_scale*:
  - Seviye 0.2: 7580.38
  - Seviye 0.3: 7609.43
  - Seviye 0.5: 7611.36

*polish_interval*:
  - Seviye 15: 7586.52
  - Seviye 25: 7612.13
  - Seviye 35: 7584.88

*alns_iterations*:
  - Seviye 100: 7561.06
  - Seviye 150: 7577.82
  - Seviye 50: 7641.24

*alns_remove_ratio*:
  - Seviye 0.1: 7652.80
  - Seviye 0.15: 7599.93
  - Seviye 0.2: 7562.82

*final_polish_iters*:
  - Seviye 100: 7600.04
  - Seviye 200: 7593.69
  - Seviye 300: 7602.52

### HHO-LKH (Problem: berlin52)
- **Toplam Kombinasyon Kaydı**: 27
- **En İyi Ortalama Sonuç**: 7748.4
- **Taguchi S/N Oranı**: -77.911 dB

**En İyi Parametre Seti**:
```json
{
  "hawks": 50,
  "max_iterations": 350,
  "initial_energy": 1.5,
  "jump_probability": 0.7,
  "max_no_improvement": 50,
  "dive_count": 2,
  "levy_scale": 0.5,
  "polish_interval": 15,
  "polish_iters": 15,
  "final_polish_iters": 200
}
```

**Parametre Önem Sırası (ANOVA F-İstatistiğine Göre)**:
| Sıralama | Parametre | F Değeri | %5 Anlamlılık | %1 Anlamlılık |
|----------|-----------|----------|---------------|---------------|
| 1 | hawks | 2.7725 | Hayır | Hayır |
| 2 | polish_iters | 2.3495 | Hayır | Hayır |
| 3 | jump_probability | 1.594 | Hayır | Hayır |
| 4 | max_no_improvement | 1.0169 | Hayır | Hayır |
| 5 | levy_scale | 0.6467 | Hayır | Hayır |
| 6 | initial_energy | 0.6391 | Hayır | Hayır |
| 7 | dive_count | 0.3086 | Hayır | Hayır |
| 8 | polish_interval | 0.2355 | Hayır | Hayır |
| 9 | max_iterations | 0.1335 | Hayır | Hayır |
| 10 | final_polish_iters | 0.0486 | Hayır | Hayır |

**Parametre Seviye Etkileri**:

*hawks*:
  - Seviye 30: 7882.71
  - Seviye 50: 7834.20
  - Seviye 70: 7838.09

*max_iterations*:
  - Seviye 150: 7869.22
  - Seviye 250: 7862.00
  - Seviye 350: 7855.92

*initial_energy*:
  - Seviye 0.5: 7868.30
  - Seviye 1.0: 7870.55
  - Seviye 1.5: 7842.03

*jump_probability*:
  - Seviye 0.3: 7839.52
  - Seviye 0.5: 7884.73
  - Seviye 0.7: 7870.42

*max_no_improvement*:
  - Seviye 100: 7884.85
  - Seviye 50: 7850.46
  - Seviye 75: 7854.98

*dive_count*:
  - Seviye 2: 7852.20
  - Seviye 3: 7864.73
  - Seviye 5: 7874.03

*levy_scale*:
  - Seviye 0.2: 7873.76
  - Seviye 0.3: 7869.83
  - Seviye 0.5: 7847.78

*polish_interval*:
  - Seviye 15: 7852.02
  - Seviye 25: 7865.11
  - Seviye 35: 7869.33

*polish_iters*:
  - Seviye 10: 7845.89
  - Seviye 15: 7845.52
  - Seviye 5: 7890.18

*final_polish_iters*:
  - Seviye 100: 7861.00
  - Seviye 200: 7858.75
  - Seviye 300: 7867.15

### Or-opt (Problem: berlin52)
- **Toplam Kombinasyon Kaydı**: 27
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

**Parametre Seviye Etkileri**:

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
- **Toplam Kombinasyon Kaydı**: 27
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

**Parametre Seviye Etkileri**:

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

---
## Yorum ve Sonuç
En yüksek F değerine sahip parametre, sonucu en fazla etkileyen faktördür. Taguchi S/N oranı yüksek olan kombinasyonlar, hem düşük ortalama hem de düşük değişkenlik sağlar.
