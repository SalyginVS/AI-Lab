# setup-check.ps1 — Верификация клиентской части Lab RTX3090
# Паспорт лаборатории v25, Этап 13
# Использование: powershell -ExecutionPolicy Bypass -File setup-check.ps1

$PassCount = 0
$FailCount = 0
$WarnCount = 0

$ServerIP = "192.168.0.128"
$GatewayPort = 8000
$OllamaPort = 11434
$RAGPort = 8100

$ContinueDir = Join-Path $env:USERPROFILE ".continue"

function Pass($msg) {
    Write-Host "[PASS] $msg" -ForegroundColor Green
    $script:PassCount++
}

function Fail($msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    $script:FailCount++
}

function Warn($msg) {
    Write-Host "[WARN] $msg" -ForegroundColor Yellow
    $script:WarnCount++
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Lab RTX3090 — Client Setup Check" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# --- Секция 1: Continue.dev файлы ---
Write-Host "--- Continue.dev файлы ---"

$ConfigPath = Join-Path $ContinueDir "config.yaml"
if (Test-Path $ConfigPath) {
    Pass "config.yaml exists"

    $ConfigContent = Get-Content $ConfigPath -Raw -ErrorAction SilentlyContinue
    if ($ConfigContent) {
        # Проверка моделей (ищем строки с 'model:' или 'title:')
        $ModelLines = ($ConfigContent | Select-String -Pattern "^\s+title:" -AllMatches).Matches.Count
        if ($ModelLines -ge 10) {
            Pass "config.yaml models: $ModelLines (ожидалось >= 10)"
        } else {
            Warn "config.yaml models found: $ModelLines (ожидалось >= 10)"
        }

        # Проверка apiKey не заглушка
        $ExampleKeys = ($ConfigContent | Select-String -Pattern "apiKey:\s*ollama" -AllMatches).Matches.Count
        if ($ExampleKeys -eq 0) {
            Pass "config.yaml: no placeholder apiKey 'ollama'"
        } else {
            Fail "config.yaml: $ExampleKeys model(s) still have apiKey: ollama"
        }

        # Проверка Gemma 4 в Tier 1
        if ($ConfigContent -match "gemma4") {
            Pass "config.yaml: Gemma 4 present"
        } else {
            Warn "config.yaml: Gemma 4 not found"
        }
    }
} else {
    Fail "config.yaml not found at $ConfigPath"
}

Write-Host ""

# --- Секция 2: Rules ---
Write-Host "--- Rules ---"

$RulesDir = Join-Path $ContinueDir "rules"

$ExpectedRules = @("01-general.md", "02-coding.md", "03-security.md")
foreach ($rule in $ExpectedRules) {
    $RulePath = Join-Path $RulesDir $rule
    if (Test-Path $RulePath) {
        Pass "rules/$rule"
    } else {
        if ($rule -eq "03-security.md") {
            Fail "rules/$rule not found (Этап 13 артефакт)"
        } else {
            Fail "rules/$rule not found"
        }
    }
}

Write-Host ""

# --- Секция 3: MCP Servers ---
Write-Host "--- MCP Servers ---"

$MCPDir = Join-Path $ContinueDir "mcpServers"

$ExpectedMCP = @("git.yaml", "rag.yaml")
foreach ($mcp in $ExpectedMCP) {
    $MCPPath = Join-Path $MCPDir $mcp
    if (Test-Path $MCPPath) {
        Pass "mcpServers/$mcp"
    } else {
        Fail "mcpServers/$mcp not found"
    }
}

Write-Host ""

# --- Секция 4: Connectivity ---
Write-Host "--- Connectivity ---"

# Gateway health
try {
    $GWHealth = Invoke-RestMethod -Uri "http://${ServerIP}:${GatewayPort}/health" -TimeoutSec 5 -ErrorAction Stop
    Pass "Gateway ${ServerIP}:${GatewayPort} — OK (version: $($GWHealth.version))"

    if ($GWHealth.auth_enabled -eq $true) {
        Pass "Gateway auth: mandatory"
    } else {
        Fail "Gateway auth: not enabled"
    }
} catch {
    Fail "Gateway ${ServerIP}:${GatewayPort} — не отвечает: $($_.Exception.Message)"
}

# Gateway metrics (auth exempt)
try {
    $null = Invoke-RestMethod -Uri "http://${ServerIP}:${GatewayPort}/metrics" -TimeoutSec 5 -ErrorAction Stop
    Pass "Gateway /metrics — OK"
} catch {
    Fail "Gateway /metrics — не отвечает"
}

# Ollama (FIM autocomplete direct)
try {
    $OllamaResp = Invoke-RestMethod -Uri "http://${ServerIP}:${OllamaPort}/api/tags" -TimeoutSec 5 -ErrorAction Stop
    $OllamaModels = $OllamaResp.models.Count
    Pass "Ollama ${ServerIP}:${OllamaPort} — OK ($OllamaModels models)"
} catch {
    Fail "Ollama ${ServerIP}:${OllamaPort} — не отвечает (FIM autocomplete не работает): $($_.Exception.Message)"
}

# RAG MCP
try {
    $null = Invoke-WebRequest -Uri "http://${ServerIP}:${RAGPort}/mcp" -TimeoutSec 5 -Method Post -ErrorAction Stop
    Pass "RAG MCP ${ServerIP}:${RAGPort} — OK"
} catch {
    # MCP может вернуть не-200 на голый POST, но главное — TCP доступен
    if ($_.Exception.Response) {
        Pass "RAG MCP ${ServerIP}:${RAGPort} — reachable (HTTP $($_.Exception.Response.StatusCode.value__))"
    } else {
        Fail "RAG MCP ${ServerIP}:${RAGPort} — не отвечает: $($_.Exception.Message)"
    }
}

Write-Host ""

# --- Секция 5: VS Code и расширения ---
Write-Host "--- VS Code ---"

$CodeCmd = Get-Command code -ErrorAction SilentlyContinue
if ($CodeCmd) {
    Pass "VS Code: found"

    $Extensions = & code --list-extensions 2>/dev/null
    if ($Extensions -match "Continue.continue") {
        Pass "Continue.dev extension: installed"
    } else {
        Fail "Continue.dev extension: not found"
    }
} else {
    Warn "VS Code 'code' command not in PATH (проверьте вручную)"
}

# uv
$UvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($UvCmd) {
    $UvVer = & uv --version 2>$null
    Pass "uv: $UvVer"
} else {
    Warn "uv: not found (нужен для mcp-server-git)"
}

Write-Host ""

# --- Summary ---
$Total = $PassCount + $FailCount + $WarnCount

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  PASS: $PassCount  |  FAIL: $FailCount  |  WARN: $WarnCount  |  TOTAL: $Total" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if ($FailCount -gt 0) {
    Write-Host "  STATUS: FAIL — есть критичные проблемы" -ForegroundColor Red
    exit 1
} elseif ($WarnCount -gt 0) {
    Write-Host "  STATUS: PASS with warnings" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "  STATUS: ALL PASS" -ForegroundColor Green
    exit 0
}
