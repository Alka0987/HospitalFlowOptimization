# setup_kafka.ps1
# PowerShell script to download and setup Java (OpenJDK) and Apache Kafka on Windows

$ErrorActionPreference = "Stop"

$workDir = Get-Location
$javaDir = "$workDir\java"
$kafkaDir = "$workDir\kafka"

# URLs (Update versions as needed)
$jdkUrl = "https://download.java.net/java/GA/jdk21.0.2/f2283984656d49d69e91c558476027ac/13/GPL/openjdk-21.0.2_windows-x64_bin.zip"
$kafkaUrl = "https://archive.apache.org/dist/kafka/3.6.1/kafka_2.13-3.6.1.tgz"

Write-Host "=== Setting up Kafka Environment ==="

# 1. Setup Java
if (-not (Test-Path $javaDir)) {
    Write-Host "Creating Java directory..."
    New-Item -ItemType Directory -Force -Path $javaDir | Out-Null
    
    $jdkZip = "$workDir\openjdk.zip"
    Write-Host "Downloading OpenJDK from $jdkUrl ..."
    Invoke-WebRequest -Uri $jdkUrl -OutFile $jdkZip
    
    Write-Host "Extracting OpenJDK..."
    Expand-Archive -Path $jdkZip -DestinationPath $javaDir -Force
    
    # Find the bin folder
    $binPath = Get-ChildItem -Path $javaDir -Recurse -Filter "bin" | Select-Object -First 1 -ExpandProperty FullName
    Write-Host "Java available at: $binPath"
    
    # Clean up zip
    Remove-Item $jdkZip
} else {
    Write-Host "Java directory already exists. Skipping download."
}

# 2. Setup Kafka
if (-not (Test-Path $kafkaDir)) {
    Write-Host "Creating Kafka directory..."
    New-Item -ItemType Directory -Force -Path $kafkaDir | Out-Null
    
    $kafkaTgz = "$workDir\kafka.tgz"
    Write-Host "Downloading Kafka from $kafkaUrl ..."
    Invoke-WebRequest -Uri $kafkaUrl -OutFile $kafkaTgz
    
    Write-Host "Extracting Kafka (this may take a moment)..."
    # Use tar command (available in Windows 10+)
    tar -xzf $kafkaTgz -C $kafkaDir
    
    # Move files up one level if nested
    $extractedRoot = Get-ChildItem -Path $kafkaDir | Select-Object -First 1
    if ($extractedRoot.Name -like "kafka_*") {
        Write-Host "Adjusting folder structure..."
        Get-ChildItem -Path $extractedRoot.FullName | Move-Item -Destination $kafkaDir
        Remove-Item $extractedRoot.FullName
    }
    
    Write-Host "Kafka extracted to: $kafkaDir"
    
    # Clean up tgz
    Remove-Item $kafkaTgz
} else {
    Write-Host "Kafka directory already exists. Skipping download."
}

Write-Host "`n=== Setup Complete ==="
Write-Host "To run Kafka, you will need 4 terminals."
Write-Host "I will create a helper script 'run_kafka_windows.ps1' to assist you."
