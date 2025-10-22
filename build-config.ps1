# build-config.ps1 - Interactive config.yaml builder for Python Script Runner
#
# This cross-platform PowerShell script helps you create a customized
# config.yaml file by asking questions about your monitoring needs.
#
# Usage:
#   .\build-config.ps1
#   OR
#   pwsh build-config.ps1  (cross-platform)
#
# Supports: Windows, macOS, Linux

#Requires -Version 5.1

# Enable strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Global error handler
trap {
    Write-Host ""
    Write-Color "❌ An unexpected error occurred:" "Red"
    Write-Color "   $($_.Exception.Message)" "Red"
    Write-Host ""
    Write-Color "Stack trace:" "Yellow"
    Write-Host $_.ScriptStackTrace
    Write-Host ""
    Write-Color "If this error persists, please report it at:" "Cyan"
    Write-Color "https://github.com/jomardyan/Python-Script-Runner/issues" "Cyan"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Cleanup handler for Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Write-Host ""
    Write-Color "\n🛑 Setup cancelled by user." "Yellow"
    Write-Host ""
}

# Function to write colored output
function Write-Color {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    try {
        Write-Host $Text -ForegroundColor $Color
    }
    catch {
        # Fallback if color output fails
        Write-Host $Text
    }
}

function Write-Success {
    param([string]$Text)
    Write-Color "✓ $Text" "Green"
}

function Write-Info {
    param([string]$Text)
    Write-Color $Text "Cyan"
}

function Write-Question {
    param([string]$Text)
    Write-Color $Text "Yellow"
}

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Color "═══════════════════════════════════════════════════════════" "Magenta"
    Write-Color "  $Text" "Magenta"
    Write-Color "═══════════════════════════════════════════════════════════" "Magenta"
    Write-Host ""
}

function Get-YesNo {
    param(
        [string]$Question,
        [bool]$Default = $true
    )
    
    try {
        $defaultText = if ($Default) { "Y/n" } else { "y/N" }
        $response = Read-Host "$Question [$defaultText]"
        
        if ([string]::IsNullOrWhiteSpace($response)) {
            return $Default
        }
        
        return $response -match "^[Yy]"
    }
    catch {
        Write-Color "  ⚠️  Invalid input, using default: $Default" "Yellow"
        return $Default
    }
}

function Get-Input {
    param(
        [string]$Question,
        [string]$Default = "",
        [bool]$Required = $false,
        [int]$MaxRetries = 3
    )
    
    $prompt = if ($Default) { "$Question [$Default]" } else { $Question }
    $attempts = 0
    
    do {
        try {
            $response = Read-Host $prompt
            
            if ([string]::IsNullOrWhiteSpace($response)) {
                if ($Default) {
                    return $Default
                }
                elseif ($Required) {
                    $attempts++
                    if ($attempts -ge $MaxRetries) {
                        Write-Color "  ❌ Maximum retry attempts reached. Using empty value." "Red"
                        return ""
                    }
                    Write-Color "  ⚠️  This field is required. Please enter a value. (Attempt $attempts/$MaxRetries)" "Red"
                    continue
                }
                else {
                    return ""
                }
            }
            
            return $response
        }
        catch {
            Write-Color "  ⚠️  Input error: $($_.Exception.Message)" "Red"
            if ($Default) {
                return $Default
            }
        }
    } while ($Required)
}

function Get-Number {
    param(
        [string]$Question,
        [int]$Default = 0,
        [int]$Min = 0,
        [int]$Max = [int]::MaxValue,
        [int]$MaxRetries = 5
    )
    
    $attempts = 0
    
    do {
        try {
            $response = Read-Host "$Question [$Default]"
            
            if ([string]::IsNullOrWhiteSpace($response)) {
                return $Default
            }
            
            if ($response -notmatch '^-?\d+$') {
                $attempts++
                if ($attempts -ge $MaxRetries) {
                    Write-Color "  ❌ Maximum retry attempts reached. Using default: $Default" "Red"
                    return $Default
                }
                Write-Color "  ⚠️  Please enter a valid number (Attempt $attempts/$MaxRetries)" "Red"
                continue
            }
            
            $number = [int]$response
            
            if ($number -lt $Min) {
                $attempts++
                Write-Color "  ⚠️  Value must be at least $Min (Attempt $attempts/$MaxRetries)" "Red"
                if ($attempts -ge $MaxRetries) {
                    return $Default
                }
                continue
            }
            
            if ($number -gt $Max) {
                $attempts++
                Write-Color "  ⚠️  Value must not exceed $Max (Attempt $attempts/$MaxRetries)" "Red"
                if ($attempts -ge $MaxRetries) {
                    return $Default
                }
                continue
            }
            
            return $number
        }
        catch {
            $attempts++
            Write-Color "  ⚠️  Invalid input: $($_.Exception.Message)" "Red"
            if ($attempts -ge $MaxRetries) {
                Write-Color "  ❌ Using default value: $Default" "Yellow"
                return $Default
            }
        }
    } while ($attempts -lt $MaxRetries)
    
    return $Default
}

# Clear screen for clean interface
try {
    Clear-Host
}
catch {
    # Ignore clear screen errors in non-interactive environments
}

Write-Section "Python Script Runner - Config Builder"

Write-Info "This wizard will help you create a customized config.yaml file"
Write-Info "for monitoring your Python scripts with alerts, gates, and integrations."
Write-Host ""
Write-Info "Press Ctrl+C at any time to cancel."
Write-Host ""

# Validate we're in the correct directory
if (-not (Test-Path "setup.py") -and -not (Test-Path "runner.py")) {
    Write-Color "⚠️  Warning: You don't appear to be in the Python Script Runner directory." "Yellow"
    Write-Host "The config.yaml file will be created in the current directory."
    Write-Host ""
    if (-not (Get-YesNo "Continue anyway?" $false)) {
        Write-Color "Setup cancelled." "Yellow"
        exit 0
    }
    Write-Host ""
}

# Initialize configuration object
try {
    $config = @{
        alerts = @()
        performance_gates = @()
        notifications = @{}
        database = @{}
        retry = @{}
    }
}
catch {
    Write-Color "❌ Failed to initialize configuration object: $($_.Exception.Message)" "Red"
    exit 1
}

# ============================================================================
# ALERTS CONFIGURATION
# ============================================================================

Write-Section "Alert Configuration"

Write-Info "Alerts notify you when metrics exceed thresholds (e.g., high CPU, memory)."
Write-Host ""

if (Get-YesNo "Do you want to configure alerts?" $true) {
    $addMoreAlerts = $true
    
    while ($addMoreAlerts) {
        Write-Host ""
        Write-Question "▶ Creating new alert..."
        Write-Host ""
        
        $alertName = Get-Input "  Alert name (e.g., 'cpu_high', 'memory_warning')" -Required $true
        
        Write-Host ""
        Write-Info "  Common conditions:"
        Write-Host "    - cpu_max > 85"
        Write-Host "    - memory_max_mb > 1024"
        Write-Host "    - execution_time_seconds > 3600"
        Write-Host "    - success == False"
        Write-Host ""
        
        $condition = Get-Input "  Condition (e.g., 'cpu_max > 85')" -Required $true
        
        Write-Host ""
        Write-Info "  Severity levels: INFO, WARNING, ERROR, CRITICAL"
        $severity = Get-Input "  Severity" "WARNING"
        
        Write-Host ""
        Write-Info "  Available channels: email, slack, webhook, pagerduty"
        $channelsInput = Get-Input "  Channels (comma-separated)" "slack"
        $channels = $channelsInput -split ',' | ForEach-Object { $_.Trim() }
        
        # Add alert to config
        try {
            $config.alerts += @{
                name = $alertName
                condition = $condition
                severity = $severity.ToUpper()
                channels = $channels
            }
        }
        catch {
            Write-Color "  ⚠️  Failed to add alert: $($_.Exception.Message)" "Red"
            Write-Host "  Skipping this alert..."
            continue
        }
        
        Write-Success "Alert '$alertName' added!"
        
        Write-Host ""
        $addMoreAlerts = Get-YesNo "Add another alert?" $false
    }
}

# ============================================================================
# PERFORMANCE GATES CONFIGURATION
# ============================================================================

Write-Section "Performance Gates"

Write-Info "Performance gates stop execution if metrics exceed limits (useful in CI/CD)."
Write-Host ""

if (Get-YesNo "Do you want to configure performance gates?" $true) {
    $addMoreGates = $true
    
    while ($addMoreGates) {
        Write-Host ""
        Write-Question "▶ Creating new performance gate..."
        Write-Host ""
        
        Write-Info "  Common metrics:"
        Write-Host "    - cpu_max (percentage)"
        Write-Host "    - memory_max_mb (megabytes)"
        Write-Host "    - execution_time_seconds (seconds)"
        Write-Host ""
        
        $metricName = Get-Input "  Metric name" -Required $true
        $maxValue = Get-Number "  Maximum allowed value" 90 0
        
        # Add gate to config
        try {
            $config.performance_gates += @{
                metric_name = $metricName
                max_value = $maxValue
            }
        }
        catch {
            Write-Color "  ⚠️  Failed to add performance gate: $($_.Exception.Message)" "Red"
            Write-Host "  Skipping this gate..."
            continue
        }
        
        Write-Success "Gate for '$metricName' added (max: $maxValue)!"
        
        Write-Host ""
        $addMoreGates = Get-YesNo "Add another performance gate?" $false
    }
}

# ============================================================================
# NOTIFICATIONS CONFIGURATION
# ============================================================================

Write-Section "Notification Channels"

# Slack Configuration
if (Get-YesNo "Do you want to configure Slack notifications?" $false) {
    try {
        Write-Host ""
        $slackWebhook = Get-Input "  Slack webhook URL" -Required $true
        
        # Validate webhook URL format
        if ($slackWebhook -and $slackWebhook -notmatch '^https://hooks\.slack\.com/') {
            Write-Color "  ⚠️  Warning: URL doesn't look like a Slack webhook. Continue anyway? " "Yellow" -NoNewline
            if (-not (Get-YesNo "" $true)) {
                Write-Host "  Skipping Slack configuration..."
                return
            }
        }
        
        $slackChannel = Get-Input "  Slack channel (optional)" ""
        $slackUsername = Get-Input "  Bot username" "Script Runner Bot"
        
        $config.notifications.slack = @{
            webhook_url = $slackWebhook
        }
        
        if ($slackChannel) {
            $config.notifications.slack.channel = $slackChannel
        }
        
        $config.notifications.slack.username = $slackUsername
        
        Write-Success "Slack configured!"
    }
    catch {
        Write-Color "  ⚠️  Failed to configure Slack: $($_.Exception.Message)" "Red"
        Write-Host "  Skipping Slack configuration..."
    }
}

# Email Configuration
Write-Host ""
if (Get-YesNo "Do you want to configure email notifications?" $false) {
    try {
        Write-Host ""
        $smtpServer = Get-Input "  SMTP server (e.g., smtp.gmail.com)" -Required $true
        $smtpPort = Get-Number "  SMTP port" 587 1 65535
        $useTLS = Get-YesNo "  Use TLS/SSL?" $true
        $fromEmail = Get-Input "  From email address" -Required $true
        
        # Validate email format
        if ($fromEmail -and $fromEmail -notmatch '^[^@]+@[^@]+\.[^@]+$') {
            Write-Color "  ⚠️  Warning: Email address format looks invalid" "Yellow"
        }
        
        $toEmail = Get-Input "  To email address(es) (comma-separated)" -Required $true
        
        $toAddresses = $toEmail -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
        
        if ($toAddresses.Count -eq 0) {
            Write-Color "  ⚠️  No valid email addresses provided. Skipping email configuration." "Red"
        }
        else {
            $config.notifications.email = @{
                smtp_server = $smtpServer
                smtp_port = $smtpPort
                from = $fromEmail
                to = $toAddresses
                use_tls = $useTLS
            }
            
            if (Get-YesNo "  Does SMTP require authentication?" $true) {
                Write-Info "  Note: Store credentials in environment variables:"
                Write-Info "    SMTP_USERNAME and SMTP_PASSWORD"
            }
            
            Write-Success "Email configured!"
        }
    }
    catch {
        Write-Color "  ⚠️  Failed to configure email: $($_.Exception.Message)" "Red"
        Write-Host "  Skipping email configuration..."
    }
}

# Webhook Configuration
Write-Host ""
if (Get-YesNo "Do you want to configure webhook notifications?" $false) {
    try {
        Write-Host ""
        $webhookUrl = Get-Input "  Webhook URL" -Required $true
        
        # Validate URL format
        if ($webhookUrl -and $webhookUrl -notmatch '^https?://') {
            Write-Color "  ⚠️  Warning: URL should start with http:// or https://" "Yellow"
            if (-not (Get-YesNo "  Continue anyway?" $false)) {
                Write-Host "  Skipping webhook configuration..."
                return
            }
        }
        
        $webhookMethod = Get-Input "  HTTP method" "POST"
        
        # Validate HTTP method
        $validMethods = @('GET', 'POST', 'PUT', 'PATCH', 'DELETE')
        if ($webhookMethod.ToUpper() -notin $validMethods) {
            Write-Color "  ⚠️  Warning: '$webhookMethod' is not a standard HTTP method" "Yellow"
        }
        
        $config.notifications.webhook = @{
            url = $webhookUrl
            method = $webhookMethod.ToUpper()
        }
        
        if (Get-YesNo "  Add custom headers?" $false) {
            Write-Info "  Note: Add headers manually to config.yaml after generation"
        }
        
        Write-Success "Webhook configured!"
    }
    catch {
        Write-Color "  ⚠️  Failed to configure webhook: $($_.Exception.Message)" "Red"
        Write-Host "  Skipping webhook configuration..."
    }
}

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

Write-Section "Database Configuration"

Write-Info "SQLite database stores historical metrics for trend analysis."
Write-Host ""

if (Get-YesNo "Do you want to configure the metrics database?" $true) {
    Write-Host ""
    
    # Detect OS for default path
    $isWindowsOS = if (Test-Path variable:IsWindows) { $IsWindows } else { $true }
    $defaultDbPath = if ($isWindowsOS) {
        "C:\ProgramData\python-script-runner\metrics.db"
    } else {
        "/var/lib/python-script-runner/metrics.db"
    }
    
    $dbPath = Get-Input "  Database path" $defaultDbPath
    $retentionDays = Get-Number "  Retention period (days, 0 = unlimited)" 90 0
    
    $config.database = @{
        path = $dbPath
    }
    
    if ($retentionDays -gt 0) {
        $config.database.retention_days = $retentionDays
    }
    
    Write-Success "Database configured!"
}

# ============================================================================
# RETRY CONFIGURATION
# ============================================================================

Write-Section "Retry Configuration"

Write-Info "Configure automatic retry behavior for failed scripts."
Write-Host ""

if (Get-YesNo "Do you want to configure retry behavior?" $true) {
    Write-Host ""
    
    Write-Info "  Retry strategies:"
    Write-Host "    - linear: Fixed delay between retries"
    Write-Host "    - exponential: Increasing delay (1s, 2s, 4s, 8s...)"
    Write-Host "    - fibonacci: Fibonacci sequence delay (1s, 1s, 2s, 3s, 5s...)"
    Write-Host ""
    
    $strategy = Get-Input "  Retry strategy" "exponential"
    $maxAttempts = Get-Number "  Maximum retry attempts" 3 1
    $baseDelay = Get-Number "  Base delay (seconds)" 1 0
    
    $config.retry = @{
        strategy = $strategy.ToLower()
        max_attempts = $maxAttempts
        base_delay = $baseDelay
    }
    
    if (Get-YesNo "  Retry only on specific exit codes?" $false) {
        Write-Info "  Note: Add retry_on_exit_codes list manually to config.yaml"
    }
    
    Write-Success "Retry configured!"
}

# ============================================================================
# ADDITIONAL OPTIONS
# ============================================================================

Write-Section "Additional Options"

$timeout = Get-Number "Execution timeout (seconds, 0 = no limit)" 0 0
if ($timeout -gt 0) {
    $config.timeout_seconds = $timeout
}

if (Get-YesNo "Enable verbose logging?" $false) {
    $config.verbose = $true
}

if (Get-YesNo "Enable anomaly detection?" $false) {
    $config.detect_anomalies = $true
}

if (Get-YesNo "Enable trend analysis?" $false) {
    $config.analyze_trends = $true
}

# ============================================================================
# GENERATE YAML FILE
# ============================================================================

Write-Section "Generating Configuration"

# Build YAML content
$yamlContent = @"
# Python Script Runner Configuration
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
#
# This file configures monitoring, alerting, and performance gates
# for Python Script Runner.
#
# Usage: python -m runner script.py --config config.yaml

"@

# Add alerts section
if ($config.alerts.Count -gt 0) {
    $yamlContent += "`n# Alert Configuration`n"
    $yamlContent += "alerts:`n"
    foreach ($alert in $config.alerts) {
        $yamlContent += "  - name: $($alert.name)`n"
        $yamlContent += "    condition: $($alert.condition)`n"
        $yamlContent += "    severity: $($alert.severity)`n"
        $yamlContent += "    channels: [$(($alert.channels -join ', '))]`n"
    }
}

# Add performance gates section
if ($config.performance_gates.Count -gt 0) {
    $yamlContent += "`n# Performance Gates`n"
    $yamlContent += "performance_gates:`n"
    foreach ($gate in $config.performance_gates) {
        $yamlContent += "  - metric_name: $($gate.metric_name)`n"
        $yamlContent += "    max_value: $($gate.max_value)`n"
    }
}

# Add notifications section
if ($config.notifications.Count -gt 0) {
    $yamlContent += "`n# Notification Channels`n"
    $yamlContent += "notifications:`n"
    
    if ($config.notifications.ContainsKey('slack')) {
        $yamlContent += "  slack:`n"
        $yamlContent += "    webhook_url: `"$($config.notifications.slack.webhook_url)`"`n"
        if ($config.notifications.slack.ContainsKey('channel') -and $config.notifications.slack.channel) {
            $yamlContent += "    channel: `"$($config.notifications.slack.channel)`"`n"
        }
        $yamlContent += "    username: `"$($config.notifications.slack.username)`"`n"
    }
    
    if ($config.notifications.ContainsKey('email')) {
        $yamlContent += "  email:`n"
        $yamlContent += "    smtp_server: `"$($config.notifications.email.smtp_server)`"`n"
        $yamlContent += "    smtp_port: $($config.notifications.email.smtp_port)`n"
        $yamlContent += "    from: `"$($config.notifications.email.from)`"`n"
        $yamlContent += "    to:`n"
        foreach ($addr in $config.notifications.email.to) {
            $yamlContent += "      - `"$addr`"`n"
        }
        $yamlContent += "    use_tls: $($config.notifications.email.use_tls.ToString().ToLower())`n"
    }
    
    if ($config.notifications.ContainsKey('webhook')) {
        $yamlContent += "  webhook:`n"
        $yamlContent += "    url: `"$($config.notifications.webhook.url)`"`n"
        $yamlContent += "    method: $($config.notifications.webhook.method)`n"
    }
}

# Add database section
if ($config.database.Count -gt 0) {
    $yamlContent += "`n# Database Configuration`n"
    $yamlContent += "database:`n"
    $yamlContent += "  path: `"$($config.database.path)`"`n"
    if ($config.database.ContainsKey('retention_days') -and $config.database.retention_days -gt 0) {
        $yamlContent += "  retention_days: $($config.database.retention_days)`n"
    }
}

# Add retry section
if ($config.retry.Count -gt 0) {
    $yamlContent += "`n# Retry Configuration`n"
    $yamlContent += "retry:`n"
    $yamlContent += "  strategy: $($config.retry.strategy)`n"
    $yamlContent += "  max_attempts: $($config.retry.max_attempts)`n"
    $yamlContent += "  base_delay: $($config.retry.base_delay)`n"
}

# Add additional options
if ($config.ContainsKey('timeout_seconds') -and $config.timeout_seconds -gt 0) {
    $yamlContent += "`n# Execution timeout (seconds)`n"
    $yamlContent += "timeout_seconds: $($config.timeout_seconds)`n"
}

if ($config.ContainsKey('verbose') -and $config.verbose) {
    $yamlContent += "`n# Enable verbose logging`n"
    $yamlContent += "verbose: true`n"
}

if ($config.ContainsKey('detect_anomalies') -and $config.detect_anomalies) {
    $yamlContent += "`n# Enable ML-powered anomaly detection`n"
    $yamlContent += "detect_anomalies: true`n"
}

if ($config.ContainsKey('analyze_trends') -and $config.analyze_trends) {
    $yamlContent += "`n# Enable trend analysis`n"
    $yamlContent += "analyze_trends: true`n"
}

# Add footer
$yamlContent += "`n# For more configuration options, see:`n"
$yamlContent += "# https://github.com/jomardyan/Python-Script-Runner`n"

# Determine output filename
$outputFile = "config.yaml"
$counter = 1

if (Test-Path $outputFile) {
    Write-Host ""
    Write-Question "File '$outputFile' already exists."
    
    if (Get-YesNo "Overwrite existing file?" $false) {
        Remove-Item $outputFile -Force
    } else {
        # Find available filename
        while (Test-Path "config-$counter.yaml") {
            $counter++
        }
        $outputFile = "config-$counter.yaml"
        Write-Info "Using filename: $outputFile"
    }
}

# Write YAML file
Write-Host ""
Write-Info "Writing configuration to: $outputFile"

try {
    # Validate we can write to the directory
    $outputDir = Split-Path -Parent $outputFile
    if (-not $outputDir) {
        $outputDir = (Get-Location).Path
    }
    
    if (-not (Test-Path $outputDir)) {
        Write-Info "Creating directory: $outputDir"
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    # Test write permissions
    $testFile = Join-Path $outputDir ".write-test-$(Get-Random).tmp"
    try {
        Set-Content -Path $testFile -Value "test" -ErrorAction Stop
        Remove-Item $testFile -Force -ErrorAction SilentlyContinue
    }
    catch {
        throw "No write permission in directory: $outputDir"
    }
    
    # Write the actual file
    Set-Content -Path $outputFile -Value $yamlContent -Encoding UTF8 -ErrorAction Stop
    
    # Verify file was written
    if (-not (Test-Path $outputFile)) {
        throw "File was not created: $outputFile"
    }
    
    $fileSize = (Get-Item $outputFile).Length
    if ($fileSize -eq 0) {
        throw "File was created but is empty: $outputFile"
    }
    
    Write-Success "Configuration file created successfully!"
    Write-Info "File size: $fileSize bytes"
}
catch {
    Write-Color "❌ Error writing file: $($_.Exception.Message)" "Red"
    Write-Host ""
    Write-Color "Troubleshooting:" "Yellow"
    Write-Host "  - Check you have write permissions in this directory"
    Write-Host "  - Ensure the disk is not full"
    Write-Host "  - Try running with elevated permissions (sudo/admin)"
    Write-Host ""
    Write-Info "Configuration content (copy manually if needed):"
    Write-Host ""
    Write-Host $yamlContent
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# ============================================================================
# SUMMARY
# ============================================================================

Write-Section "Configuration Summary"

Write-Success "Configuration file: $outputFile"
Write-Host ""

if ($config.alerts.Count -gt 0) {
    Write-Info "✓ $($config.alerts.Count) alert(s) configured"
}

if ($config.performance_gates.Count -gt 0) {
    Write-Info "✓ $($config.performance_gates.Count) performance gate(s) configured"
}

if ($config.notifications.ContainsKey('slack')) {
    Write-Info "✓ Slack notifications enabled"
}

if ($config.notifications.ContainsKey('email')) {
    Write-Info "✓ Email notifications enabled"
}

if ($config.notifications.ContainsKey('webhook')) {
    Write-Info "✓ Webhook notifications enabled"
}

if ($config.database.ContainsKey('path')) {
    Write-Info "✓ Database configured: $($config.database.path)"
}

if ($config.retry.ContainsKey('strategy')) {
    Write-Info "✓ Retry strategy: $($config.retry.strategy) (max $($config.retry.max_attempts) attempts)"
}

Write-Host ""
Write-Section "Next Steps"

Write-Info "Use your new configuration:"
Write-Host ""
Write-Color "  python -m runner myscript.py --config $outputFile" "Green"
Write-Host ""
Write-Info "Or use it as a Python library:"
Write-Host ""
Write-Host "  from runner import ScriptRunner"
Write-Host "  runner = ScriptRunner('script.py', config_file='$outputFile')"
Write-Host "  runner.run_script()"
Write-Host ""
Write-Info "Documentation: https://github.com/jomardyan/Python-Script-Runner"
Write-Host ""
Write-Success "Setup complete! 🎉"
Write-Host ""
