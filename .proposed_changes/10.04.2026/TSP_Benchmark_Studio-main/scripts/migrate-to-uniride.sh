#!/usr/bin/env bash
# =============================================================================
# migrate-to-uniride.sh
#
# Bu script UniRide reposunun kökünden çalıştırılır.
# TSP_Benchmark_Studio içeriğini
#   UniRide/proposed_changes/TSP_Benchmark_Studio/
# klasörüne kopyalar.
#
# Kullanım (UniRide repo kökünde):
#   bash proposed_changes/TSP_Benchmark_Studio/scripts/migrate-to-uniride.sh
# veya ilk çalıştırmada (henüz dosya yokken):
#   curl -fsSL https://raw.githubusercontent.com/YektaK/TSP_Benchmark_Studio/main/scripts/migrate-to-uniride.sh | bash
# =============================================================================
set -euo pipefail

REPO_URL="https://github.com/YektaK/TSP_Benchmark_Studio"
BRANCH="main"
DEST=".proposed_changes/TSP_Benchmark_Studio"

# ── UniRide repo kökünde olduğumuzu doğrula ────────────────────────────────
if [ ! -d ".git" ]; then
  echo "❌ Hata: Bu script UniRide reposunun kökünden çalıştırılmalıdır."
  echo "   (Geçerli dizinde .git klasörü bulunamadı)"
  exit 1
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   TSP Benchmark Studio → UniRide Migration                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Hedef: $DEST"
echo ""

# ── Hedef klasörü oluştur ──────────────────────────────────────────────────
if [ -d "$DEST" ]; then
  echo "⚠️  $DEST zaten mevcut."
  read -r -p "   Üzerine yazılsın mı? (mevcut içerik silinir) [y/N] " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "İptal edildi."
    exit 0
  fi
  rm -rf "$DEST"
fi

mkdir -p "$DEST"

# ── GitHub'dan tarball indir ve çıkar ─────────────────────────────────────
echo "→ İndiriliyor: $REPO_URL (branch: $BRANCH)..."

if command -v curl &>/dev/null; then
  curl -fsSL "$REPO_URL/archive/refs/heads/$BRANCH.tar.gz" \
    | tar -xz --strip-components=1 -C "$DEST"
elif command -v wget &>/dev/null; then
  wget -qO- "$REPO_URL/archive/refs/heads/$BRANCH.tar.gz" \
    | tar -xz --strip-components=1 -C "$DEST"
else
  echo "❌ curl veya wget gerekli."
  exit 1
fi

echo "→ İndirme tamamlandı."

# ── Gereksiz dosyaları temizle ────────────────────────────────────────────
echo "→ Entegrasyon için gereksiz dosyalar kaldırılıyor..."

# Agent context dosyaları (bu repoya özel, UniRide'da gerekmez)
rm -rf "$DEST/agent-ctx"

# İç agent iş günlüğü
rm -f  "$DEST/worklog.md"

# Bun lockfile'ları (UniRide'da regenerate edilir)
rm -f  "$DEST/bun.lock"
rm -f  "$DEST/mini-services/benchmark-runner/bun.lock"

# Bu migration scripti zaten çalışıyor, tekrar indirilmesine gerek yok
# (scripts/ klasörü korunur — migrate-to-uniride.sh dahil, referans olarak)

echo ""
echo "✅ Başarılı! Dosyalar hazır: $DEST"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Klasör yapısı:"
echo "═══════════════════════════════════════════════════════════════"
find "$DEST" -maxdepth 2 -not -path "*/.git/*" | sort | head -60
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Sonraki adımlar:"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo " 1. MIGRATION_TO_UNIRIDE.md dosyasını oku:"
echo "    cat $DEST/MIGRATION_TO_UNIRIDE.md"
echo ""
echo " 2. Bir Copilot agent'a şu görevi ver:"
echo "    'proposed_changes/TSP_Benchmark_Studio içindeki TSP Benchmark"
echo "     Studio kodunu MIGRATION_TO_UNIRIDE.md rehberini takip ederek"
echo "     UniRide ana projesine entegre et.'"
echo ""
echo " 3. Entegrasyon tamamlandıktan sonra:"
echo "    - proposed_changes/TSP_Benchmark_Studio/ klasörünü sil"
echo "    - YektaK/TSP_Benchmark_Studio reposunu arşivle veya sil"
echo ""
