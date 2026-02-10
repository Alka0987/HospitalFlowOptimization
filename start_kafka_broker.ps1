
# Start Kafka Broker (Requires Java & Zookeeper running)
$env:JAVA_HOME = "$PSScriptRoot\java\jdk-21.0.2"
$kafkaDir = "$PSScriptRoot\kafka"

if (-not (Test-Path $env:JAVA_HOME)) {
    Write-Host "Error: Java not found at $env:JAVA_HOME. Run setup_kafka.ps1 first."
    exit
}

Write-Host "Starting Kafka Broker..."
& "$kafkaDir\bin\windows\kafka-server-start.bat" "$kafkaDir\config\server.properties"
