 $base64 = Get-Content -Path "code.zipbase64.txt" -Raw
 $bytes = [System.Convert]::FromBase64String($base64.Trim())
[System.IO.File]::WriteAllBytes("UniRide_Dokumantasyon.zip", $bytes)