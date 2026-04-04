<#
  UniRide Dosya Envanteri Tarama Scripti
  Tarama dışı: .next, node_modules
  Çıktı: JSON + CSV
#>

$RootPath = $PSScriptRoot
if (-not $RootPath) { $RootPath = (Get-Location).Path }
$ExcludedDirs = @('.next', 'node_modules', '.git')
$OutputDir = Join-Path $RootPath "_scan_output"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Çıktı klasörü oluştur
if (-not (Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null }

# Kategori tanımları
$UnnecessaryPatterns = @{
    "log_dosyasi"           = @("*.log")
    "ts_buildinfo"          = @("*.tsbuildinfo")
    "python_cache"          = @("__pycache__", "*.pyc")
    "env_backup"            = @("*.bak")
    "tek_kullanimli_script" = @("import_*.js", "cleanup_*.js", "inspect_*.js", "analyze_*.js", "generate_*.py", "test_clustering.py", "verify_strategies.py", "read_docx.py", "test_*.py")
    "text_dump"             = @("full_project*.txt", "pdf_content.txt", "*.ps1", "*.txt")
    "akademik_taslak"       = @("*.docx", "paper_draft.html", "*.pdf", "*.html")
    "image_export"          = @("Fig*.jpg", "Mapcoded.png", "supabase-schema-*.png")
    "proje_disi_icerik"     = @("ALTERNATIVES.md", "DRAFT*")
    "one_cikan_dosya"       = @("24.03.2026_cursor_analiz.md", "algorithm_integration_audit.md", "calculate_vehicles_with_vrp_fixed_v11.m")
    "tekrar_edici_rapor"    = @("SUPABASE_AUTH_COMPLETE.md", "SUPABASE_NEXT_STEPS.md", "FIREBASE_FIX_COMPLETE.md", "FIXES_COMPLETE.md", "FIREBASE_SETUP.md", "DATABASE_SETUP_COMPLETE.md", "QUICK_START.md", "README_DATABASE.md", "WINDOWS_SETUP.md")
    "data_dosyasi"          = @("Veri.xlsx", "test_users.xlsx", "test_users.csv", "base64.txt")
}

# Yardımcı fonksiyon: Dosya kategorisini belirle
function Get-FileCategory {
    param([string]$FileName, [string]$RelPath, [string]$Extension)
    
    # Check unnecessary patterns
    foreach ($cat in $UnnecessaryPatterns.Keys) {
        foreach ($pattern in $UnnecessaryPatterns[$cat]) {
            if ($FileName -like $pattern -or $RelPath -like "*$pattern*") {
                return @{ Necessary = $false; Category = $cat }
            }
        }
    }

    # Check extension-based categories
    switch ($Extension) {
        ".pyc"       { return @{ Necessary = $false; Category = "python_cache" } }
        ".log"       { return @{ Necessary = $false; Category = "log_dosyasi" } }
        ".tsbuildinfo" { return @{ Necessary = $false; Category = "ts_buildinfo" } }
        ".bak"       { return @{ Necessary = $false; Category = "env_backup" } }
        ".py"        { 
            if ($FileName -match "^(generate_|test_|read_|verify_)") { 
                return @{ Necessary = $false; Category = "tek_kullanimli_script" }
            }
            return @{ Necessary = $true; Category = "python_kaynak" }
        }
        ".js"        { 
            if ($FileName -match "^(import_|cleanup_|inspect_|analyze_)") { 
                return @{ Necessary = $false; Category = "tek_kullanimli_script" }
            }
            return @{ Necessary = $true; Category = "javascript" }
        }
        ".m"         { return @{ Necessary = $false; Category = "proje_disi_icerik" } }
        ".sql"       { return @{ Necessary = $true; Category = "veritabani_migration" } }
        ".tsx"       { return @{ Necessary = $true; Category = "react_component" } }
        ".ts"        { return @{ Necessary = $true; Category = "typescript_kaynak" } }
        ".md"        { 
            if ($FileName -match "^(SUPABASE_|FIREBASE_|FIXES_|DATABASE_|QUICK_|WINDOWS_)") {
                return @{ Necessary = $false; Category = "tekrar_edici_rapor" }
            }
            return @{ Necessary = $true; Category = "dokumantasyon" }
        }
        ".css"       { return @{ Necessary = $true; Category = "stil_dosyasi" } }
        ".json"      { return @{ Necessary = $true; Category = "konfigurasyon" } }
        ".mjs"       { return @{ Necessary = $true; Category = "modul" } }
        ".yaml"      { return @{ Necessary = $true; Category = "konfigurasyon" } }
        ".yml"       { return @{ Necessary = $true; Category = "konfigurasyon" } }
        ".html"      { return @{ Necessary = $false; Category = "akademik_taslak" } }
        ".jpg"       { return @{ Necessary = $false; Category = "image_export" } }
        ".png"       { return @{ Necessary = $false; Category = "image_export" } }
        ".docx"      { return @{ Necessary = $false; Category = "akademik_taslak" } }
        ".pdf"       { return @{ Necessary = $false; Category = "akademik_taslak" } }
        ".xlsx"      { return @{ Necessary = $false; Category = "data_dosyasi" } }
        ".csv"       { return @{ Necessary = $false; Category = "data_dosyasi" } }
        ".txt"       { return @{ Necessary = $false; Category = "text_dump" } }
        ".m"         { return @{ Necessary = $false; Category = "proje_disi_icerik" } }
        ".ps1"       { return @{ Necessary = $false; Category = "text_dump" } }
        default      { return @{ Necessary = $true; Category = "diger" } }
    }
}

# Ana tarama
$AllFiles = @()
$UnnecessaryFiles = @()

Get-ChildItem -Path $RootPath -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
    $File = $_
    $RelPath = $File.FullName.Substring($RootPath.Length + 1)
    
    # Tarama dışı dizin kontrolü
    $IsExcluded = $false
    foreach ($ExDir in $ExcludedDirs) {
        if ($RelPath -like "$ExDir*" -or $RelPath -like "*\$ExDir\*") {
            $IsExcluded = $true
            break
        }
    }
    
    if ($IsExcluded) { return }
    
    $Extension = $File.Extension.ToLower()
    $CatInfo = Get-FileCategory -FileName $File.Name -RelPath $RelPath -Extension $Extension
    
    $FileObj = [PSCustomObject]@{
        tam_yol          = $File.FullName
        goreli_yol       = $RelPath
        dosya_adi        = $File.Name
        boyut_byte       = $File.Length
        boyut_okunabilir = if ($File.Length -gt 1MB) { "{0:N2} MB" -f ($File.Length / 1MB) } 
                           elseif ($File.Length -gt 1KB) { "{0:N2} KB" -f ($File.Length / 1KB) } 
                           else { "$($File.Length) B" }
        son_degisim      = $File.LastWriteTime.ToString("yyyy-MM-ddTHH:mm:ss")
        uzanti           = $Extension
        kategori         = $CatInfo.Category
        gerekli_mi       = $CatInfo.Necessary
    }
    
    $AllFiles += $FileObj
    
    if (-not $CatInfo.Necessary) {
        $UnnecessaryFiles += $FileObj
    }
}

# Sonuçları yaz
$TotalCount = $AllFiles.Count
$UnnecessaryCount = $UnnecessaryFiles.Count
$UnnecessarySizeMB = ($UnnecessaryFiles | Measure-Object -Property boyut_byte -Sum).Sum / 1MB

# JSON rapor
$InventoryReport = @{
    tarama_tarihi              = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
    kok_dizin                  = $RootPath
    tarama_disi_dizinler       = $ExcludedDirs
    toplam_taranan_dosya       = $TotalCount
    gereksiz_dosya_sayisi      = $UnnecessaryCount
    gereksiz_toplam_boyut_mb   = [math]::Round($UnnecessarySizeMB, 2)
    vazgecilmez_dosya_sayisi   = $TotalCount - $UnnecessaryCount
    kategori_dagilimi          = @{}
    vazgecilmez_dosyalar       = $AllFiles | Where-Object { $_.gerekli_mi -eq $true }
    gereksiz_dosyalar          = $UnnecessaryFiles
}

# Kategori dağılımı
$AllFiles | Group-Object kategori | ForEach-Object {
    $InventoryReport.kategori_dagilimi[$_.Name] = @{
        dosya_sayisi     = $_.Count
        toplam_boyut_mb  = [math]::Round(($_.Group | Measure-Object -Property boyut_byte -Sum).Sum / 1MB, 2)
    }
}

# JSON kaydet
$JsonPath = Join-Path $OutputDir "envanter_raporu_$Timestamp.json"
$InventoryReport | ConvertTo-Json -Depth 10 | Out-File -FilePath $JsonPath -Encoding UTF8

# CSV kaydet
$CsvPath = Join-Path $OutputDir "gereksiz_dosyalar_$Timestamp.csv"
$UnnecessaryFiles | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding UTF8

# Tüm dosyalar CSV
$AllCsvPath = Join-Path $OutputDir "tum_dosyalar_$Timestamp.csv"
$AllFiles | Export-Csv -Path $AllCsvPath -NoTypeInformation -Encoding UTF8

# Sonuç yazdır
Write-Host "=== TARAMA SONUÇLARI ===" -ForegroundColor Cyan
Write-Host "Toplam taranan dosya: $TotalCount" -ForegroundColor White
Write-Host "Gereksiz dosya sayısı: $UnnecessaryCount" -ForegroundColor Yellow
Write-Host "Gereksiz toplam boyut: $([math]::Round($UnnecessarySizeMB, 2)) MB" -ForegroundColor Yellow
Write-Host "Gerekli dosya sayısı: $($TotalCount - $UnnecessaryCount)" -ForegroundColor Green
Write-Host ""
Write-Host "Kategori Dağılımı:" -ForegroundColor Cyan
$InventoryReport.kategori_dagilimi.GetEnumerator() | Sort-Object Value.dosya_sayisi -Descending | ForEach-Object {
    Write-Host "  $($_.Key): $($_.Value.dosya_sayisi) dosya, $($_.Value.toplam_boyut_mb) MB" -ForegroundColor Gray
}
Write-Host ""
Write-Host "Çıktı dosyaları:" -ForegroundColor Green
Write-Host "  JSON: $JsonPath" -ForegroundColor Gray
Write-Host "  Gereksiz CSV: $CsvPath" -ForegroundColor Gray
Write-Host "  Tüm dosyalar CSV: $AllCsvPath" -ForegroundColor Gray
