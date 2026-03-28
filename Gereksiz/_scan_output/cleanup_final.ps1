# Ayarlar
 $RootPath = "C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide"
# CSV dosyasının konumu. Eğer dosya _scan_output klasöründeyse aşağıdaki yolu kullanın.
# Değilse ve doğrudan UniRide içindeyse 'Join-Path $RootPath "gereksiz_dosyalar_20260328_220932.csv"' yapın.
 $CsvPath = Join-Path $RootPath "_scan_output\gereksiz_dosyalar_20260328_220932.csv"

# Kontrol: CSV dosyası var mı?
if (-not (Test-Path $CsvPath)) {
    Write-Host "HATA: CSV dosyasi bulunamadi!" -ForegroundColor Red
    Write-Host "Beklenen yol: $CsvPath"
    Write-Host "Lutfen \$CsvPath degiskenini dogru dosya yoluna gore duzenleyin."
    Read-Host "Cikmak icin Enter'a basin"
    exit
}

Write-Host "CSV dosyasi okunuyor: $CsvPath" -ForegroundColor Cyan

# CSV'yi oku (Ayırıcı '|' karakteridir)
 $csvData = Import-Csv -Path $CsvPath -Delimiter '|'

 $TargetBase = Join-Path $RootPath "Gereksiz"
 $movedCount = 0
 $failedCount = 0
 $notFoundCount = 0

Write-Host "Islem basliyor... Toplam $($csvData.Count) kayit bulundu.`n" -ForegroundColor Yellow

foreach ($row in $csvData) {
    # CSV sütunlarını al
    $relPath = $row.goreli_yol.Trim()   # Göreli yol (Daha güvenilir)
    $category = $row.kategori.Trim()   # Kategori (Hedef klasör adı)
    $fileName = $row.dosya_adi.Trim()  # Dosya adı
    $fullPathInCsv = $row.tam_yol.Trim() # CSV'deki tam yol (Yedek çözüm)

    # 1. Dosya yolunu belirle (Önce göreli yolu dene)
    $sourcePath = Join-Path $RootPath $relPath
    
    # 2. Dosya bulunamazsa ve CSV'deki tam yol boş değilse, tam yolu düzeltip dene
    # Not: Chat penceresinde backslash'lar kaybolmuş olabilir (C:Users... gibi).
    # Dosya sistemimizde C:\Users... olmalı.
    if (-not (Test-Path $sourcePath) -and $fullPathInCsv -ne "") {
        # Basit bir onarim dene: Sürücü harfinden sonra \ ekle
        $fixedPath = $fullPathInCsv -replace '^([A-Z]):', '$1:\'
        
        # Eğer hala yoksa, muhtemelen tüm backslash'lar gitmiştir (Düzeltme zor ama denenmeli)
        if (-not (Test-Path $fixedPath)) {
            # UniRide ana klasörüne göre path'i yeniden oluştur (son çare)
            # Burada relPath'in doğru oldugunu varsayiyoruz, ama dosya silinmis olabilir.
        } else {
            $sourcePath = $fixedPath
        }
    }

    # Dosya gerçekten var mı?
    if (Test-Path $sourcePath) {
        # Hedef klasörü belirle: Root\Gereksiz\Kategori
        $destCategoryDir = Join-Path $TargetBase $category
        
        # Klasör yoksa oluştur
        if (-not (Test-Path $destCategoryDir)) {
            try {
                New-Item -ItemType Directory -Path $destCategoryDir -Force | Out-Null
            } catch {
                Write-Host "HATA: Klasör olusturulamadi: $destCategoryDir" -ForegroundColor Red
                $failedCount++
                continue
            }
        }

        $destPath = Join-Path $destCategoryDir $fileName

        # Aynı isimli dosya varsa isim çakışmasını önle (dosya_adi_1.ext)
        if (Test-Path $destPath) {
            $baseName = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
            $ext = [System.IO.Path]::GetExtension($fileName)
            $counter = 1
            while (Test-Path (Join-Path $destCategoryDir "$baseName_$counter$ext")) {
                $counter++
            }
            $destPath = Join-Path $destCategoryDir "$baseName_$counter$ext"
        }

        # Taşıma işlemi
        try {
            Move-Item -Path $sourcePath -Destination $destPath -Force
            Write-Host "[$movedCount] TASINDI: $fileName -> [$category]" -ForegroundColor Gray
            $movedCount++
        }
        catch {
            Write-Host "HATA: $fileName tasinamadi. $($_.Exception.Message)" -ForegroundColor Red
            $failedCount++
        }
    }
    else {
        # Dosya bulunamadıysa (Zaten silinmiş veya taşınmış olabilir)
        Write-Host "ATLANDI: Dosya bulunamadi - $fileName" -ForegroundColor DarkYellow
        $notFoundCount++
    }
}

# Sonuç Raporu
Write-Host "`n------------------------------------------------------------"
Write-Host "TEMIZLIK ISLEMI TAMAMLANDI" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"
Write-Host "Basariyla Tasinan : $movedCount dosya" -ForegroundColor Green
Write-Host "Bulunamayan      : $notFoundCount dosya" -ForegroundColor Yellow
if ($failedCount -gt 0) { Write-Host "Hata Alan       : $failedCount dosya" -ForegroundColor Red }
Write-Host "------------------------------------------------------------"
Write-Host "Dosyalar '$TargetBase' klasoru icerisinde kategorilerine gore tasindi."
Read-Host "Cikmak icin Enter'a basin"