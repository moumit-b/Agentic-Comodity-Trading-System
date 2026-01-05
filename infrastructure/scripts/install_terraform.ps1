# Install Terraform on Windows
# Run this as Administrator

Write-Host "Installing Terraform..." -ForegroundColor Green

# Check if Chocolatey is installed
$chocoInstalled = Get-Command choco -ErrorAction SilentlyContinue

if ($chocoInstalled) {
    Write-Host "Installing Terraform via Chocolatey..."
    choco install terraform -y
} else {
    Write-Host "Chocolatey not found. Installing Terraform manually..."

    # Download Terraform
    $terraformVersion = "1.7.0"
    $downloadUrl = "https://releases.hashicorp.com/terraform/${terraformVersion}/terraform_${terraformVersion}_windows_amd64.zip"
    $zipPath = "$env:TEMP\terraform.zip"
    $extractPath = "$env:ProgramFiles\Terraform"

    Write-Host "Downloading Terraform $terraformVersion..."
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath

    # Extract and install
    Write-Host "Extracting Terraform..."
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

    # Add to PATH
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($currentPath -notlike "*$extractPath*") {
        Write-Host "Adding Terraform to PATH..."
        [Environment]::SetEnvironmentVariable(
            "Path",
            "$currentPath;$extractPath",
            "Machine"
        )
    }

    # Clean up
    Remove-Item $zipPath -Force
}

# Refresh environment PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Verify installation
Write-Host "`nVerifying installation..." -ForegroundColor Yellow
try {
    terraform --version
    Write-Host "`nTerraform installed successfully!" -ForegroundColor Green
    Write-Host "Close and reopen PowerShell to use 'terraform' command." -ForegroundColor Cyan
} catch {
    Write-Host "`nTerraform installation may require a system restart." -ForegroundColor Yellow
}
