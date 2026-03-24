━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ÖZET - Yapılan Güncellemeler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Değiştirilen 10 Dosya:

│ # │ Dosya                                          │ Durum      │
├───┼────────────────────────────────────────────────┼────────────┤
│ 1 │ optimizer_api/utils/local_search.py            │ 🆕 YENİ    │
│ 2 │ optimizer_api/strategies/gwo_strategy.py       │ 🆕 YENİ    │
│ 3 │ optimizer_api/strategies/hho_strategy.py       │ 🆕 YENİ    │
│ 4 │ optimizer_api/strategies/two_opt_strategy.py   │ 🆕 YENİ    │
│ 5 │ optimizer_api/strategies/__init__.py           │ 🔄 GÜNCEL  │
│ 6 │ optimizer_api/strategies/ga_strategy.py        │ 🔄 GÜNCEL  │
│ 7 │ optimizer_api/strategies/pso_strategy.py       │ 🔄 GÜNCEL  │
│ 8 │ optimizer_api/models/schemas.py                │ 🔄 GÜNCEL  │
│ 9 │ optimizer_api/main.py                          │ 🔄 GÜNCEL  │
│10 │ src/services/optimizer-service.ts               │ 🔄 GÜNCEL  │

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Önemli Değişiklikler:

✅ 2-opt kod tekrarı → local_search.py'de merkezi hale getirildi
✅ GWO (Gri Kurt) ve HHO (Harris Hawks) algoritmaları eklendi
✅ Two-Opt bağımsız strateji olarak kullanılabilir
✅ local_search_type parametresi: none, two_opt, three_opt, or_opt, hybrid
✅ API versiyon 3.0.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━