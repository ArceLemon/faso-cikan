# Pilotage de Faso Cikan sous Windows (équivalent PowerShell de ./faso).
# Usage : .\faso.ps1 demarrer | arreter | etat | journaux [service] | agents
#         .\faso.ps1 revoquer MATRICULE | reintegrer MATRICULE | code MATRICULE
#         .\faso.ps1 certificat | tests | reinitialiser
param(
    [string]$Commande = "aide",
    [string]$Arg
)
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Config-Element {
    $v = @{}
    Get-Content .env | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object { $k, $x = $_ -split '=', 2; $v[$k] = $x }
    $m = Get-Content element\config\config.modele.json -Raw -Encoding UTF8
    $r = [regex]::Replace($m, '\$\{([A-Z_]+)\}', { param($g) $v[$g.Groups[1].Value] })
    [IO.File]::WriteAllText("$PWD\element\config\config.json", $r, (New-Object Text.UTF8Encoding $false))
}

function Console-Faso { docker compose exec -T console python -m app @args }

function Secret($n = 40) {
    $alphabet = [char[]]([char]'A'..[char]'Z' + [char]'a'..[char]'z' + [char]'0'..[char]'9')
    $octets = New-Object byte[] $n
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($octets)
    -join ($octets | ForEach-Object { $alphabet[$_ % $alphabet.Length] })
}

function Init-Env {
    if (Test-Path .env) { Write-Host ".env existe déjà, rien à faire."; return }
    $lignes = @(
        "# Généré par faso.ps1 init. Ne pas versionner.",
        "FASO_DOMAINE=faso.localhost",
        "FASO_SERVER_NAME=faso.gov.bf",
        "POSTGRES_PASSWORD=$(Secret)",
        "KEYCLOAK_DB_PASSWORD=$(Secret)",
        "KEYCLOAK_ADMIN=admin-faso",
        "KEYCLOAK_ADMIN_PASSWORD=$(Secret 24)",
        "SYNAPSE_OIDC_SECRET=$(Secret)",
        "SYNAPSE_REGISTRATION_SHARED_SECRET=$(Secret 64)",
        "SYNAPSE_MACAROON_SECRET=$(Secret 64)",
        "SYNAPSE_FORM_SECRET=$(Secret 64)",
        "CONSOLE_OIDC_SECRET=$(Secret)",
        "CONSOLE_SESSION_SECRET=$(Secret 64)",
        "CONSOLE_API_JETON=$(Secret 48)"
    )
    [IO.File]::WriteAllText("$PWD\.env", ($lignes -join "`n") + "`n", (New-Object Text.UTF8Encoding $false))
    Write-Host "Fichier .env créé."
}

switch ($Commande) {
    "init" { Init-Env }
    "demarrer" {
        Init-Env
        Config-Element
        docker compose up -d --build
        docker compose ps
    }
    "arreter"    { docker compose stop }
    "etat"       { docker compose ps }
    "journaux"   { docker compose logs -f --tail 100 $Arg }
    "agents"     { Console-Faso agents }
    "revoquer"   { Console-Faso revoquer $Arg }
    "reintegrer" { Console-Faso reintegrer $Arg }
    "code"       { docker run --rm -v "${PWD}\demo:/demo:ro" python:3.12-slim python /demo/code.py $Arg }
    "certificat" {
        New-Item -ItemType Directory -Force certificats | Out-Null
        docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt certificats/faso-ca.crt
        Import-Certificate -FilePath "$PWD\certificats\faso-ca.crt" -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
        Write-Host "Certificat approuvé. Redémarrez le navigateur."
    }
    "tests" {
        docker compose --profile tests build tests
        docker compose --profile tests run --rm tests
    }
    "reinitialiser" {
        if ((Read-Host "Taper SUPPRIMER pour tout effacer") -eq "SUPPRIMER") { docker compose --profile tests down -v }
    }
    default { Get-Content $PSCommandPath -TotalCount 4 }
}
