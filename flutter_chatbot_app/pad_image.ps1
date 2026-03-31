# Script tạo ảnh icon với padding cho Android Adaptive Icon
# Safe zone của adaptive icon chỉ hiển thị ~66% vùng trung tâm
# Logo hình thoi cần thu nhỏ xuống ~45% để không bị cắt

Add-Type -AssemblyName System.Drawing

$inPath = Join-Path $PSScriptRoot "assets\images\logo-ctu.png"
$outPath = Join-Path $PSScriptRoot "assets\images\logo-ctu-padded.png"

$img = [System.Drawing.Image]::FromFile($inPath)

# Tạo canvas 1024x1024 (kích thước chuẩn cho app icon)
$canvasSize = 1024
$bmp = New-Object System.Drawing.Bitmap($canvasSize, $canvasSize)
$g = [System.Drawing.Graphics]::FromImage($bmp)

# Chất lượng render cao
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

# Nền trắng
$g.Clear([System.Drawing.Color]::White)

# Thu nhỏ logo xuống 45% canvas để nằm gọn trong safe zone
$scale = 0.45
$newWidth = [math]::Round($canvasSize * $scale)
$newHeight = [math]::Round($canvasSize * $scale)

# Căn giữa logo trên canvas
$x = [math]::Round(($canvasSize - $newWidth) / 2)
$y = [math]::Round(($canvasSize - $newHeight) / 2)

$g.DrawImage($img, $x, $y, $newWidth, $newHeight)

$bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)

$g.Dispose()
$bmp.Dispose()
$img.Dispose()

Write-Host "Done! Logo padded at $outPath (${canvasSize}x${canvasSize}, logo scale: $($scale * 100)%)"
