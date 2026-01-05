# Install AWS CLI v2 on Windows
# Run this as Administrator

Write-Host "Installing AWS CLI v2..." -ForegroundColor Green

# Download AWS CLI installer
$installerUrl = "https://awscli.amazonaws.com/AWSCLIV2.msi"
$installerPath = "$env:TEMP\AWSCLIV2.msi"

Write-Host "Downloading AWS CLI installer..."
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

# Install AWS CLI
Write-Host "Installing AWS CLI (this may take a minute)..."
Start-Process msiexec.exe -ArgumentList "/i", $installerPath, "/quiet", "/norestart" -Wait

# Clean up
Remove-Item $installerPath -Force

# Verify installation
Write-Host "`nVerifying installation..." -ForegroundColor Yellow
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

try {
    aws --version
    Write-Host "`nAWS CLI installed successfully!" -ForegroundColor Green
    Write-Host "Close and reopen PowerShell to use 'aws' command." -ForegroundColor Cyan
} catch {
    Write-Host "`nAWS CLI installation may require a system restart." -ForegroundColor Yellow
}

Write-Host "`nNext step: Run 'aws configure' to set up your credentials" -ForegroundColor Cyan
