# GitHub İş Akışı - AI Agent ile Takım Çalışması

> **Oluşturulma:** 04.04.2026 - Ekleyen: Z.ai
> **Amaç:** Birden fazla AI agent ve geliştiricinin aynı repo üzerinde güvenli çalışması

---

## 1. Genel Yapı

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   GITHUB (Bulut)                    LOKAL (Senin Bilgisayar)   │
│   ──────────────                    ────────────────────────   │
│                                                                 │
│   main branch                       main branch (kopya)        │
│   (ana kodlar)                      (çalışma alanı)            │
│       │                                  │                     │
│       │  ←──── git pull ─────            │                     │
│       │                                  │                     │
│       │  ────── git push ────→           │                     │
│                                                                 │
│   PR #15 (Z.ai'nin değişikliği)                                │
│   PR #16 (Başka AI'nın değişikliği)                            │
│   PR #17 (Developer değişikliği)                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. AI Agent Kuralları

### 2.1 Branch İsimlendirme

```
feature/zai-KONU-TARİH
feature/copilot-KONU-TARİH
feature/dev-İSİM-KONU

Örnekler:
- feature/zai-sota-solvers-04.04.2026
- feature/zai-alns-operators-05.04.2026
- feature/copilot-bugfix-indexerror
- feature/dev-yekta-ui-fix
```

### 2.2 Commit Mesaj Formatı

```
[TİP]: Kısa açıklama (GG.AA.YYYY - Ekleyen: İsim)

Tipler:
- feat: Yeni özellik
- fix: Hata düzeltme
- docs: Dokümantasyon
- refactor: Kod iyileştirme
- test: Test ekleme/düzeltme
- chore: Bakım işleri

Örnek:
feat: PyVRP benchmark entegrasyonu (04.04.2026 - Z.ai)
```

### 2.3 PR Açma Formatı

```markdown
## Değişiklikler
- Madde 1
- Madde 2

## Test
- [ ] Test 1
- [ ] Test 2

## Dokümantasyon
- [ ] Güncellendi

## Reviewer
@YektaK
```

---

## 3. Lokalde PR Test Etme (VS Code)

### 3.1 PR'ı İndirme

```
1. VS Code aç
2. Sol tarafta "Source Control" ikonu (Ctrl+Shift+G)
3. "..." menüsü → "Pull Request" → "Checkout Pull Request"
4. Listeden PR'ı seç
5. VS Code otomatik dosyaları günceller
```

### 3.2 Terminal ile

```bash
# PR'ları listele
gh pr list

# PR'ı lokale çek
gh pr checkout 15

# Artık o branch'tasın, dosyalar değişti
# Test et
python -m pytest
python run_smart_benchmark.py
```

---

## 4. PR Onaylama / Reddetme

### 4.1 Onaylama (Merge)

```
VS Code:
1. "Source Control" → "..." → "Pull"
2. GitHub.com'a git → PR → "Merge Pull Request"

Terminal:
gh pr merge 15 --squash
git checkout main
git pull origin main
```

### 4.2 Reddetme

```
VS Code:
1. Sol alt köşede branch ismine tıkla
2. "main" seç → Dosyalar eski haline döner
3. GitHub.com'da PR → "Close Pull Request"

Terminal:
git checkout main           # Eski hale dön
gh pr close 15 -c "Sebep"   # GitHub'da kapat
```

---

## 5. Önemli Kurallar

### 5.1 Branch Protection (GitHub Ayarları)

```
Settings → Branches → Add rule (main için)

✅ Require pull request reviews before merging
   └── Required approving reviews: 1

✅ Require status checks to pass before merging

✅ Do not allow bypassing settings
```

### 5.2 Silme Yasağı (Dokümantasyon için)

```
Kod veya dokümantasyon silmek yerine:

1. Olumsuz görüş ekle:
   "Eski yaklaşım (04.04.2026 - Z.ai: X nedeniyle önerilmiyor)"

2. İptal işareti koy:
   "- [İPTAL] Eski madde (04.04.2026 - Z.ai: Sebep)"

3. Görüş çakışması:
   "• Yaklaşım A (01.04.2026 - X: Öneriliyor)"
   "• Yaklaşım A (04.04.2026 - Z.ai: Testlerde başarısız)"
```

---

## 6. Tam İş Akışı Şeması

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  DURUM                    YAPILACAK                 SONUÇ           │
│  ─────                    ─────────                 ─────           │
│                                                                     │
│  AI PR açtı  ────→  gh pr checkout N  ────→  Dosyalar değişti      │
│                                                                     │
│  Test ediyorum  ────→  python test.py  ────→  Başarılı mı?         │
│                                                                     │
│  ┌─────────────┴─────────────┐                                      │
│  │                           │                                      │
│  ▼                           ▼                                      │
│ BEĞENDM                     BEĞENMEDM                              │
│  │                           │                                      │
│  ▼                           ▼                                      │
│ gh pr merge N             git checkout main                         │
│ git pull origin main      gh pr close N                             │
│  │                           │                                      │
│  ▼                           ▼                                      │
│ Değişiklikler            Eski hale döndü                           │
│ main'de artık             Reddedildi                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. VS Code Eklentileri

```
1. "GitHub Pull Requests and Issues"
   → PR'ları VS Code içinde yönet

2. "GitLens"
   → Kim ne değiştirmiş gör

3. "Git Graph"
   → Branch geçmişi görselleştir
```

---

## 8. Sık Kullanılan Komutlar

```bash
# Repo'yu ilk kez al
git clone https://github.com/YektaK/UniRide.git

# Değişiklikleri al
git pull origin main

# PR'ları gör
gh pr list

# PR'ı test et
gh pr checkout 15

# main'e dön
git checkout main

# PR onayla
gh pr merge 15 --squash

# PR reddet
gh pr close 15 -c "Sebep"

# Mevcut durumu gör
git status
git branch
```

---

## 9. Güvenlik

| Konu | Açıklama |
|------|----------|
| Token | `ghp_` ile başlar, gizli tutulmalı |
| Scope | Sadece `repo` yetkisi yeterli |
| Süre | 90 gün veya No expiration |
| İptal | Settings → Developer settings → Tokens → Delete |

---

## 10. Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| "Merge conflict" | PR sahibi düzeltmeli |
| "Branch out of date" | `git fetch` + `git rebase origin/main` |
| "Push rejected" | `git pull` önce, sonra tekrar push |
| Yanlış merge ettim | `git revert MERGE_COMMIT_HASH` |

---

*Bu doküman, AI agent'lar ve geliştiriciler arası işbirliği için oluşturulmuştur.*
