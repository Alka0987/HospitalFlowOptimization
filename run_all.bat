@echo off
SETLOCAL
TITLE Mission Control

REM Set paths
SET "PROJECT_DIR=%~dp0"
REM Remove trailing backslash if present
IF %PROJECT_DIR:~-1%==\ SET "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

SET "JAVA_HOME=%PROJECT_DIR%\java\jdk-21.0.2"
SET "KAFKA_DIR=%PROJECT_DIR%\kafka"

REM Check Java
IF NOT EXIST "%JAVA_HOME%" (
    echo [ERROR] Java not found at "%JAVA_HOME%"
    echo Please run 'setup_kafka.ps1' first!
    pause
    exit /b
)

echo ========================================================
echo   SMART HOSPITAL - SYSTEM LAUNCHER
echo ========================================================
echo.
echo Launching components in separate windows...
echo Project Dir: "%PROJECT_DIR%"
echo Kafka Dir:   "%KAFKA_DIR%"
echo.

REM 1. Start Zookeeper
echo [1/5] Starting Zookeeper...
start "1. Zookeeper" cmd /k "set "JAVA_HOME=%JAVA_HOME%" && cd /d "%KAFKA_DIR%" && bin\windows\zookeeper-server-start.bat config\zookeeper.properties"
timeout /t 5 >nul

REM 2. Start Kafka Broker
echo [2/5] Starting Kafka Broker...
start "2. Kafka Broker" cmd /k "set "JAVA_HOME=%JAVA_HOME%" && cd /d "%KAFKA_DIR%" && bin\windows\kafka-server-start.bat config\server.properties"
timeout /t 10 >nul

REM 3. Create Topic
echo [3/5] Creating Topic 'hospital_arrivals'...
cmd /c "set "JAVA_HOME=%JAVA_HOME%" && cd /d "%KAFKA_DIR%" && bin\windows\kafka-topics.bat --create --topic hospital_arrivals --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1 --if-not-exists"

REM 4. Start Consumer
echo [4/5] Starting Backend Consumer...
start "3. Backend Brain (Consumer)" cmd /k "cd /d "%PROJECT_DIR%" && py kafka_consumer.py"

REM 5. Start Producer
echo [5/5] Starting Simulation (Producer)...
start "4. Simulation Input (Producer)" cmd /k "cd /d "%PROJECT_DIR%" && py kafka_producer.py"

REM 6. Start Dashboard
echo [6/5] Starting Dashboard...
start "5. Dashboard UI" cmd /k "cd /d "%PROJECT_DIR%" && py -m streamlit run dashboard.py"

echo.
echo DONE! All systems go.
echo Press any key to close this launcher (windows will stay open).
pause
