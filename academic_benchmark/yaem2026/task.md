# YAEM 2026 Optuna & Universal Parameters Görev Listesi

- `[x]` 1. `2_run_tuning.py` dosyasını Optuna TPE kullanacak şekilde güncelle.
  - `[x]` `generate_combinations` ve `fractional_fallback` mantığını sil.
  - `[x]` Optuna entegrasyonunu (`optuna.create_study`) kur ve 30 Trial (deneme) yap.
- `[x]` 2. Yeni `extract_universal_params.py` betiğini yaz.
  - `[x]` `tuned_parameters_db.json` üzerinden her algoritmanın en çok tekrar eden (Mod) değerlerini çıkar.
  - `[x]` `universal_parameters_db.json` adıyla yeni veritabanına kaydet.
- `[x]` 3. `run_isarc_experiments.py` dosyasını güncelle.
  - `[x]` Sadece 4 TSPLIB problemi için config üretecek şekilde ayarla.
  - `[x]` Adım 2.5 olarak `extract_universal_params.py` dosyasını çağırmasını sağla.
- `[x]` 4. `3_run_benchmark.py` dosyasını güncelle.
  - `[x]` `tuned_parameters_db.json` yerine `universal_parameters_db.json` okuyacak şekilde düzelt.
  - `[x]` Tüm TSPLIB problemleri ve `student_matrix` üzerinde test yapmasını sağla.
- `[x]` 5. Test ve Doğrulama.
