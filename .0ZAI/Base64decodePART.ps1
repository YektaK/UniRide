# Tüm part dosyalarını birleştir
 $parts = Get-ChildItem -Filter "base64_part*.txt" | Sort-Object Name
 $base64 = ($parts | ForEach-Object { Get-Content $_.FullName -Raw }) -join ""
 $bytes = [System.Convert]::FromBase64String($base64.Trim())
[System.IO.File]::WriteAllBytes("output.zip", $bytes)