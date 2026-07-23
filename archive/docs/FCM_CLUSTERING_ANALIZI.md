# FCM Clustering Analizi ve Geliştirme Raporu

## Tarih: 05 Nisan 2026
## Konu: Mevcut FCM Implementasyonunun Analizi ve Geliştirilmesi

---

## 1. Executive Summary

Bu belge, UniRide projesindeki FCM (Fuzzy C-Means) clustering implementasyonunun detaylı analizini sunmaktadır. Analiz, geçmiş çalışmalarımızdan elde edilen MATLAB kodları ile mevcut Python implementasyonumuzun karşılaştırmasını içermektedir. Sonuç olarak, FCM algoritmasından elde edilen üyelik matrisinin daha etkin kullanılması için **Border Point Detection** ve **Transfer Mekanizması** önerileri geliştirilmiştir.

---

## 2. Mevcut Implementasyon Analizi

### 2.1 Dosya Konumu
```
optimizer_api/utils/clustering_strategies/fuzzy_cmeans.py
```

### 2.2 Mevcut Akış

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEVCUT FCM AKIŞI                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Girdi: points (List[Point]), k (küme sayısı)                │
│                                                                  │
│  2. Üyelik Matrisi Başlatma (n × k)                             │
│     └── Rastgele değerler, satır toplamları = 1                 │
│                                                                  │
│  3. İterasyon (max_iterations = 100):                           │
│     ├── Küme merkezlerini güncelle                              │
│     │   └── centroid_j = Σ(U[i,j]^m * point_i) / Σ(U[i,j]^m)   │
│     │                                                           │
│     └── Üyelik matrisini güncelle                               │
│         └── U[i,j] = 1 / Σ(d_ij/d_ik)^(2/(m-1))                │
│                                                                  │
│  4. Hard Assignment (SATIR 52-61)                               │
│     └── Her noktayı max(U) ile tek bir kümeye ata               │
│     └── ÜYELİK MATRİSİ ATILIYOR ← KRİTİK KAYIP                  │
│                                                                  │
│  5. Kapasite Kontrolü                                           │
│     └── Aşan kümeleri recursive olarak böl                      │
│                                                                  │
│  6. Çıktı: List[Cluster]                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Kritik Sorun: Üyelik Matrisinin Atılması

```python
# Mevcut kod (satır 52-61)
# Hard assignment step (max membership)
assignments = []
for i in range(n):
    max_val = -1
    max_idx = 0
    for j in range(k):
        if U[i][j] > max_val:
            max_val = U[i][j]
            max_idx = j
    assignments.append(max_idx)  # ← Sadece en yüksek değer alınıyor
```

**Sorun:** FCM'in en değerli çıktısı olan üyelik matrisi (U), hard assignment sonrası tamamen atılıyor.

**Örnek Kayıp:**
```
Öğrenci-5 için üyelik değerleri:
  Cluster 0 (Araç-1): 0.55
  Cluster 1 (Araç-2): 0.42  ← Bu bilgi kayıp!
  Cluster 2 (Araç-3): 0.03

Mevcut: "Araç-1'e ata" → BİTTİ
Geliştirilmiş: "Araç-1'e ata AMA Araç-2'ye de %42 ait, transfer adayı"
```

---

## 3. MATLAB Kodlarından Çıkarılan Dersler

### 3.1 İncelenen Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `FCM_IKI_ASAMA_MERKEZ.m` | İki aşamalı kümeleme, merkez bazlı bağlantı |
| `FCM_TEK_ASAMA_MERKEZ.m` | Tek aşama, merkez bazlı bağlantı noktası seçimi |
| `FCM_TEK_ASAMA_UYELIK.m` | Üyelik farkı bazlı bağlantı noktası seçimi |

### 3.2 Temel Yaklaşımlar

#### Yaklaşım 1: Merkez Bazlı Bağlantı Noktası Seçimi

```matlab
% İki küme merkezi arasındaki çizginin ORTA NOKTASI
MXx = (MX(i1,1) + MX(i2,1)) / 2;  % Orta nokta X koordinatı
MXy = (MX(i1,2) + MX(i2,2)) / 2;  % Orta nokta Y koordinatı

% Bu orta noktaya en yakın elemanları her iki kümeden de bul
FARK = abs(data(A,1)' - MXx) + abs(data(A,2)' - MYy);
BAGLA1 = A(INDS1);  % Küme A'dan bağlantı noktası
BAGLA2 = B(INDS2);  % Küme B'den bağlantı noktası
```

**Fikir:** İki kümenin sınır bölgesindeki noktaları geometrik olarak belirle.

#### Yaklaşım 2: Üyelik Farkı Bazlı Bağlantı Noktası Seçimi

```matlab
% İki küme için üyelik değerleri
U1 = U(i1, A);  % Küme 1'e ait A noktalarının üyelikleri
U2 = U(i2, A);  % Küme 2'ye ait A noktalarının üyelikleri

% Üyelik farkı
KF = abs(U1 - U2);

% Farkı EN AZ olan → İki kümeye de yakın
[D, INDS] = min(KF);
BAGLA = A(INDS);  % Bağlantı noktası
```

**Fikir:** İki kümeye olan üyelik farkı en az olan noktalar "sınır noktası"dır.

### 3.3 MATLAB Yaklaşımlarının VRP'ye Uyarlanması

MATLAB kodları TSP için yazılmış (küme bağlama mantığı). VRP'de her küme zaten ayrı bir araç olduğu için:

| TSP (MATLAB) | VRP (UniRide) |
|--------------|---------------|
| Küme bağlama | Transfer mekanizması |
| Border point → bağlantı | Border point → transfer adayı |
| Tek tur oluştur | Çoklu rota optimize et |

**Uyarlama Stratejisi:**
```
Border Point Detection (Sınır Noktası Tespiti)
    ↓
İki araca da yüksek düzeyde ait olan öğrenciler
    ↓
Transfer Adayı olarak işaretle
    ↓
Kısıt ihlali durumunda transfer et
```

---

## 4. Önerilen Geliştirmeler

### 4.1 Border Point Detection (Sınır Noktası Tespiti)

#### Tanımlar

```python
@dataclass
class StudentMembership:
    """Öğrencinin küme üyelik bilgileri"""
    student_id: str
    
    # Üyelik değerleri (tüm cluster'lar için)
    membership_values: Dict[int, float]  # {cluster_id: üyelik_değeri}
    
    # Türetilmiş bilgiler
    primary_cluster: int        # En yüksek üyelikli cluster
    primary_membership: float   # En yüksek üyelik değeri
    secondary_cluster: int      # 2. en yüksek üyelikli cluster
    secondary_membership: float # 2. en yüksek üyelik değeri
    
    # Belirsizlik analizi
    ambiguity_score: float      # |primary - secondary|
    border_status: str          # "HIGH", "MEDIUM", "LOW"
```

#### Belirsizlik Skoru ve Border Status

```
ambiguity_score = |primary_membership - secondary_membership|

Border Status Eşik Değerleri:
┌─────────────────────────────────────────────────────────┐
│ ambiguity_score < 0.15  → BORDER_HIGH  (çok belirsiz)  │
│ 0.15 ≤ ambiguity_score < 0.30 → BORDER_MEDIUM          │
│ ambiguity_score ≥ 0.30  → BORDER_LOW   (net ait)       │
└─────────────────────────────────────────────────────────┘
```

**Mantık:**
- Düşük ambiguity_score → Yüksek belirsizlik → İki kümeye de yakın
- Yüksek ambiguity_score → Düşük belirsizlik → Net bir kümeye ait

### 4.2 Transfer Mekanizması

#### Transfer Önceliği

```
Transfer Önceliği = ambiguity_score (DÜŞÜK = YÜKSEK ÖNCİLİK)

Örnek:
┌────────────────────────────────────────────────────────────┐
│ Öğrenci A: primary=0.52, secondary=0.45                    │
│            ambiguity = |0.52-0.45| = 0.07                   │
│            → BORDER_HIGH, transfer önceliği: YÜKSEK        │
│                                                             │
│ Öğrenci B: primary=0.85, secondary=0.10                    │
│            ambiguity = |0.85-0.10| = 0.75                   │
│            → BORDER_LOW, transfer önceliği: DÜŞÜK          │
└────────────────────────────────────────────────────────────┘
```

#### Transfer Algoritması

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRANSFER ALGORITMASI                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  FOR each cluster in clusters:                                   │
│    violations = check_violations(cluster)                        │
│                                                                  │
│    IF violations exist:                                          │
│      border_points = cluster.get_border_points()                 │
│      SORT border_points BY ambiguity_score ASC                   │
│                                                                  │
│      FOR point in border_points:                                 │
│        target_cluster = point.secondary_cluster                  │
│                                                                  │
│        IF transfer_feasible(point, target_cluster):              │
│          transfer(point, cluster, target_cluster)                │
│          BREAK  // Her ihlal için en iyi transfer                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Hierarchical Clustering (İki Aşamalı)

#### Motivasyon

Büyük problemlerde (N > threshold) tek aşamalı FCM:
- Yavaş yakınsama
- Daha fazla lokal optimum
- Daha zayıf küme kalitesi

#### İki Aşamalı Yaklaşım

```
┌─────────────────────────────────────────────────────────────────┐
│                  HIERARCHICAL FCM AKIŞI                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  IF n_students > THRESHOLD:  // Threshold deneme ile belirlenecek│
│                                                                  │
│    AŞAMA 1: Bölgesel Kümeleme (Coarse)                          │
│    ├── num_regions = max(2, n // 30)                            │
│    ├── regions = FCM(students, num_regions)                     │
│    └── Her bölge ~30 öğrenci                                    │
│                                                                  │
│    AŞAMA 2: Araç Kümelemesi (Fine)                              │
│    ├── FOR each region in regions:                              │
│    │   ├── vehicles_for_region = calculate_allocation(region)   │
│    │   └── sub_clusters = FCM(region.points, vehicles)         │
│    └── Tüm alt kümeleri birleştir                               │
│                                                                  │
│    AŞAMA 3: Border Point Transfer                               │
│    └── Bölgeler arası transfer optimizasyonu                    │
│                                                                  │
│  ELSE:                                                           │
│    Standart tek aşamalı FCM                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Uygulama Planı

### 5.1 Yeni Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `fuzzy_cmeans_enhanced.py` | Border detection + Transfer mekanizması |
| `hierarchical_fcm.py` | İki aşamalı clustering |
| `tests/test_fcm_enhanced.py` | Birim testleri |
| `tests/benchmark_hierarchical_fcm.py` | Threshold belirleme benchmarkı |

### 5.2 Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|------------|
| `clustering_strategies/__init__.py` | Yeni stratejileri ekle |
| `clustering.py` | EnhancedCluster dataclass ekle |

### 5.3 Benchmark Planı (Threshold Belirleme)

Benchmark, gerçek TSPLIB problemleri kullanılarak gerçekleştirilecektir. Her hedef boyut için 3 TSPLIB problemi seçilmiştir:

```
Test Problemleri (TSPLIB - Her boyut için 3 problem):
│
├── ~50  (Hedef: 50)
│   ├── eil51    (n=51,  optimal=426)
│   ├── berlin52 (n=52,  optimal=7542)
│   └── eil76    (n=76,  optimal=538)
│
├── ~100 (Hedef: 100)
│   ├── kroA100  (n=100, optimal=21282)
│   ├── kroB100  (n=100, optimal=22141)
│   └── kroC100  (n=100, optimal=20749)
│
├── ~150 (Hedef: 150)
│   ├── kroA150  (n=150, optimal=26524)
│   ├── kroB150  (n=150, optimal=26130)
│   └── pr152    (n=152, optimal=73682)
│
├── ~200 (Hedef: 200)
│   ├── kroA200  (n=200, optimal=29368)
│   ├── kroB200  (n=200, optimal=29437)
│   └── ts225    (n=225, optimal=126843)
│
├── ~300 (Hedef: 300)
│   ├── gil262   (n=262, optimal=2412)
│   ├── pr299    (n=299, optimal=48191)
│   └── lin318   (n=318, optimal=42029)
│
└── ~500 (Hedef: 500)
    ├── rd400    (n=400, optimal=15281)
    ├── pr439    (n=439, optimal=107217)
    └── d493     (n=493, optimal=35002)

Toplam: 18 TSPLIB problemi × 3 strateji × 3 run = 162 test

Ölçümler:
├── Çalışma süresi (ms)
├── Çözüm kalitesi (total distance)
├── Kapasite ihlali sayısı (SW/SO ayrı)
├── Küme istatistikleri (avg/std size)
└── Border point sayısı (enhanced strateji için)
```

**Not:** TSPLIB koordinatları normalize edilip öğrenci noktalarına dönüştürülecektir. Engellilik türü (Sw/So) rastgele atanacaktır (3:5 oranı).

---

## 6. Beklenen Sonuçlar

### 6.1 Metrik Tahminleri

| Metrik | Mevcut | Beklenen İyileşme |
|--------|--------|-------------------|
| **Capacity Violation** | ~10% | ~2-5% ↓ |
| **Büyük Problem (N>100) Süre** | 60-120s | 30-60s ↓ |
| **Çözüm Kalitesi** | Baseline | ~5-10% ↓ |

### 6.2 Akademik Katkı

Bu çalışma aşağıdaki çıktıları hedeflemektedir:
1. **Bildiri**: FCM üyelik matrisinin VRP'de transfer optimizasyonu için kullanımı
2. **Metodoloji**: Border point detection ile kümeleme sonrası iyileştirme

---

## 7. Sonuç

Mevcut FCM implementasyonumuz temel algoritmayı doğru uygulamaktadır, ancak FCM'in en değerli çıktısı olan üyelik matrisi atılmaktadır. Bu raporda önerilen geliştirmeler ile:

1. **Border Point Detection**: İki araca da yüksek düzeyde ait olan öğrencilerin tespiti
2. **Transfer Mekanizması**: Kısıt ihlallerinde akıllı öğrenci transferi
3. **Hierarchical Clustering**: Büyük problemler için iki aşamalı yaklaşım

Bu geliştirmeler, hem pratik çözüm kalitesini artıracak hem de akademik bir katkı sağlayacaktır.

---

## Ek A: MATLAB Kod Referansları

### A.1 FCM_TEK_ASAMA_UYELIK.m - Üyelik Farkı Hesaplama

```matlab
% Satır 73-79
U1=U(i1,A);
U2=U(i2,A);
KF=abs(U1-U2);  % Kritik satır - üyelik farkı
[D1 INDS1]=min(KF);
BAGLA1=A(INDS1);
```

### A.2 FCM_IKI_ASAMA_MERKEZ.m - İki Aşamalı Yapı

```matlab
% Satır 11-13
CLUSTER_SAYISI1=C1;  % 1. Aşama küme sayısı
CLUSTER_SAYISI2=C2;  % 2. Aşama küme sayısı

% İki aşamalı yapı
[SON_TUR2]=FCMyek2CLUSTER(CLUSTER_SAYISI2,SEHIR_NO1,X_KONUMU1,Y_KONUMU1);
```

---

*Bu belge UniRide projesi kapsamında hazırlanmıştır.*
*Yazar: Super Z AI Assistant*
*Tarih: 05 Nisan 2026*
