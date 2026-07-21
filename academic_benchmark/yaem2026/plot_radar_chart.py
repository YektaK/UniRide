import matplotlib.pyplot as plt
import numpy as np
import os

def create_student_radar_chart():
    # Yeni Kategori İsimleri
    categories = [
        'Kalite', 
        'Hız', 
        'Verimlilik', 
        'Genelleme', 
        'Kararlılık'
    ]
    N = len(categories)

    # Açıları hesapla
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1] # Grafiği kapatmak için

    # Sadece 4 Algoritma ve Puanları (Öğrenci Zaman Matrisi Odaklı 0-100 Puan)
    # 1. GWO-ALNS
    gwo_alns_scores = [100, 30, 70, 100, 100]
    gwo_alns_scores += gwo_alns_scores[:1]

    # 2. HHO-ALNS
    hho_alns_scores = [100, 20, 65, 100, 100]
    hho_alns_scores += hho_alns_scores[:1]

    # 3. 2-opt
    two_opt_scores = [90, 100, 95, 90, 70]
    two_opt_scores += two_opt_scores[:1]

    # 4. 3-opt
    three_opt_scores = [85, 90, 90, 85, 60]
    three_opt_scores += three_opt_scores[:1]

    # Plot Ayarları
    fig, ax = plt.subplots(figsize=(9, 8), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2) # Kalite en üstte olsun
    ax.set_theta_direction(-1)
    
    # X Eksen (Kategoriler)
    plt.xticks(angles[:-1], categories, size=13, fontweight='bold')
    
    # Y Eksen (Puanlar)
    ax.set_rlabel_position(0)
    plt.yticks([20, 40, 60, 80, 100], ["20", "40", "60", "80", "100"], color="grey", size=10)
    plt.ylim(0, 100)

    # Çizgiler
    ax.plot(angles, gwo_alns_scores, linewidth=2, linestyle='solid', label='GWO-ALNS', color='#2ca02c') # Yeşil
    ax.fill(angles, gwo_alns_scores, '#2ca02c', alpha=0.1)

    ax.plot(angles, hho_alns_scores, linewidth=2, linestyle='solid', label='HHO-ALNS', color='#1f77b4') # Mavi
    ax.fill(angles, hho_alns_scores, '#1f77b4', alpha=0.1)

    ax.plot(angles, two_opt_scores, linewidth=2, linestyle='solid', label='2-opt', color='#ff7f0e') # Turuncu
    ax.fill(angles, two_opt_scores, '#ff7f0e', alpha=0.1)
    
    ax.plot(angles, three_opt_scores, linewidth=2, linestyle='solid', label='3-opt', color='#d62728') # Kırmızı
    ax.fill(angles, three_opt_scores, '#d62728', alpha=0.1)

    # Başlık ve Legend
    plt.title('Öğrenci Zaman Matrisi Performans Karşılaştırma Matrisi (Radar Chart)', size=14, fontweight='bold', y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

    # Kaydetme
    os.makedirs('results/plots', exist_ok=True)
    save_path = 'results/plots/radar_chart_yaem2026.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[*] Yeni Radar Chart başarıyla oluşturuldu: {save_path}")

if __name__ == '__main__':
    create_student_radar_chart()
