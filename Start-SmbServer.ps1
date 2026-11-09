<#
.SYNOPSIS
Starts a read-only, guest-access SMB 2/3 file server using Windows PowerShell 5.1
and SMBLibrary (https://github.com/TalAloni/SMBLibrary).

.DESCRIPTION
Hosts a local folder as a network share. SMBLibrary is a fully managed C# SMB
implementation; this script loads it into Windows PowerShell and runs the server
on background threads. Defaults: SMB2 + SMB3, guest login, read-only share,
TCP port 4450.

Guest login is enabled when the account named Guest has an empty password.
In that mode SMBLibrary accepts any credentials (or none) as a guest session.
Use -AllowWrite to make the share writable, or set -Password to require that
exact password for the Guest account (which also disables guest fallback).

Windows Explorer / "net use" always connect to TCP 445, which normally requires
an elevated shell and freeing port 445 (the built-in LanmanServer service).
Use -Port 445 for that scenario, or connect to 4450 with Test-SmbClient.ps1.

.PARAMETER Path
Local folder to share. Created if it does not exist. Defaults to .\share.

.PARAMETER ShareName
Share name visible to clients (\\host\ShareName). Defaults to the folder name.

.PARAMETER User
Account name. Default: Guest. Unknown account names are mapped to a guest
session when Guest has an empty password.

.PARAMETER Password
Account password. Default: empty (guest access). A non-empty password disables
the guest fallback and requires these credentials.

.PARAMETER Port
TCP port to listen on. Default: 4450 (no admin needed). 445 is the standard SMB
port used by Windows clients; binding it requires an elevated shell and the
LanmanServer service to be stopped.

.PARAMETER BindAddress
IP address to bind. Default: 0.0.0.0 (all interfaces). Use 127.0.0.1 for local only.

.PARAMETER AllowWrite
Allow write operations. By default the share is read-only for every session.

.PARAMETER EnableSMB1
Also accept the legacy SMB1/CIFS dialect (insecure, off by default).

.PARAMETER DisableSMB2
Disable SMB2 (SMB3 requires SMB2, so combine with -DisableSMB3 for SMB1 only).

.PARAMETER DisableSMB3
Disable SMB3.

.PARAMETER RunSeconds
Stop automatically after N seconds. 0 (default) runs until Ctrl+C.

.EXAMPLE
.\Start-SmbServer.ps1 -Path D:\Data -ShareName Data

.EXAMPLE
.\Start-SmbServer.ps1 -Path D:\Data -AllowWrite

.EXAMPLE
.\Start-SmbServer.ps1 -Port 445   # from an elevated shell

.NOTES
Requires Windows PowerShell 5.1 (powershell.exe) on Windows.
The script downloads the SMBLibrary NuGet packages into .\lib on first run.

For remote clients, allow the TCP port through Windows Firewall, for example:
    New-NetFirewallRule -DisplayName 'SMBLibrary server' -Direction Inbound -Protocol TCP -LocalPort 4450 -Action Allow

Windows 10/11 clients block guest logons by default. If Explorer reports that
insecure guest access is blocked, enable it on the client (admin):
    reg add HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters /v AllowInsecureGuestAuth /t REG_DWORD /d 1 /f
#>

#Requires -Version 5.1

[CmdletBinding()]
param(
    [string]$Path,
    [string]$ShareName,
    [string]$User = 'Guest',
    [string]$Password = '',
    [ValidateRange(1, 65535)]
    [int]$Port = 4450,
    [string]$BindAddress = '0.0.0.0',
    [switch]$AllowWrite,
    [switch]$EnableSMB1,
    [switch]$DisableSMB2,
    [switch]$DisableSMB3,
    [ValidateRange(0, [int]::MaxValue)]
    [int]$RunSeconds = 0
)

$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSEdition -ne 'Desktop') {
    throw 'This script targets Windows PowerShell 5.1. Run it with powershell.exe, not pwsh.'
}

if ([string]::IsNullOrWhiteSpace($Path)) {
    $Path = Join-Path $PSScriptRoot 'share'
}

$CoreVersion = '1.5.8.1'
$Win32Version = '1.5.8'
$LibDir = Join-Path $PSScriptRoot 'lib'
$CoreDll = Join-Path $LibDir 'SMBLibrary.dll'
$Win32Dll = Join-Path $LibDir 'SMBLibrary.Win32.dll'

function Save-NuGetAssembly {
    param(
        [string]$PackageId,
        [string]$Version,
        [string]$DllName,
        [string]$Destination
    )
    $tempDir = Join-Path ([IO.Path]::GetTempPath()) ('smblib-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    $previousProgress = $ProgressPreference
    $ProgressPreference = 'SilentlyContinue'
    try {
        $zip = Join-Path $tempDir 'package.zip'
        $uri = "https://www.nuget.org/api/v2/package/$PackageId/$Version"
        Write-Host "Downloading $PackageId $Version ..."
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add('User-Agent', 'WindowsPowerShell-SMBLibrary')
        $webClient.DownloadFile($uri, $zip)
        $webClient.Dispose()
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $tempDir)
        $source = Join-Path $tempDir "lib/net40/$DllName"
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Package $PackageId $Version does not contain lib/net40/$DllName"
        }
        Copy-Item -LiteralPath $source -Destination $Destination -Force
    }
    finally {
        $ProgressPreference = $previousProgress
        Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path -LiteralPath $CoreDll) -or -not (Test-Path -LiteralPath $Win32Dll)) {
    New-Item -ItemType Directory -Path $LibDir -Force | Out-Null
    try {
        $protocols = [Net.ServicePointManager]::SecurityProtocol
        if (($protocols -band [Net.SecurityProtocolType]::Tls12) -eq 0) {
            [Net.ServicePointManager]::SecurityProtocol = $protocols -bor [Net.SecurityProtocolType]::Tls12
        }
    }
    catch {
    }
    if (-not (Test-Path -LiteralPath $CoreDll)) {
        Save-NuGetAssembly -PackageId 'SMBLibrary' -Version $CoreVersion -DllName 'SMBLibrary.dll' -Destination $CoreDll
    }
    if (-not (Test-Path -LiteralPath $Win32Dll)) {
        Save-NuGetAssembly -PackageId 'SMBLibrary.Win32' -Version $Win32Version -DllName 'SMBLibrary.Win32.dll' -Destination $Win32Dll
    }
}

[void][System.Reflection.Assembly]::LoadFrom($CoreDll)
[void][System.Reflection.Assembly]::LoadFrom($Win32Dll)

$helperSource = @'
using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using SMBLibrary;
using SMBLibrary.Authentication.GSSAPI;
using SMBLibrary.Authentication.NTLM;
using SMBLibrary.Server;

namespace PwshSmbServerHost
{
    public static class SmbAuth
    {
        private static Dictionary<string, string> s_users = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        public static void SetUsers(string[] userPasswordPairs)
        {
            s_users.Clear();
            foreach (string pair in userPasswordPairs)
            {
                int separator = pair.IndexOf(':');
                if (separator <= 0)
                {
                    throw new ArgumentException("Expected user:password, got: " + pair);
                }
                s_users[pair.Substring(0, separator)] = pair.Substring(separator + 1);
            }
        }

        public static NTLMAuthenticationProviderBase CreateProvider()
        {
            return new IndependentNTLMAuthenticationProvider(GetPassword);
        }

        private static string GetPassword(string userName)
        {
            string password;
            if (s_users.TryGetValue(userName, out password))
            {
                return password;
            }
            return null;
        }
    }

    public static class ReadOnlyGuard
    {
        public static void Attach(FileSystemShare share)
        {
            share.AccessRequested += OnAccessRequested;
        }

        private static void OnAccessRequested(object sender, AccessRequestArgs args)
        {
            args.Allow = (args.RequestedAccess == FileAccess.Read);
        }
    }

    public class SmbServer : SMBServer
    {
        public SmbServer(SMBShareCollection shares, GSSProvider securityProvider) : base(shares, securityProvider)
        {
        }

        public void StartOnPort(IPAddress serverAddress, SMBTransportType transport, int port, bool enableSMB1, bool enableSMB2, bool enableSMB3)
        {
            Start(serverAddress, transport, port, enableSMB1, enableSMB2, enableSMB3, null);
        }
    }

    public static class SmbLog
    {
        public static void Attach(SMBServer server)
        {
            server.LogEntryAdded += OnLogEntry;
        }

        private static void OnLogEntry(object sender, Utilities.LogEntry entry)
        {
            Console.WriteLine("[SMB {0:HH:mm:ss}] {1} {2}: {3}", entry.Time, entry.Severity, entry.Source, entry.Message);
        }
    }
}
'@

if (-not ('PwshSmbServerHost.SmbServer' -as [type])) {
    Add-Type -TypeDefinition $helperSource -ReferencedAssemblies @($CoreDll)
}

if ([string]::IsNullOrWhiteSpace($ShareName)) {
    $ShareName = Split-Path -Leaf ([IO.Path]::GetFullPath($Path).TrimEnd('\', '/'))
    if ([string]::IsNullOrWhiteSpace($ShareName) -or $ShareName -match '[\\/:*?"<>|]') {
        $ShareName = 'share'
    }
}
elseif ($ShareName -match '[\\/:*?"<>|]') {
    throw "Invalid share name '$ShareName'."
}

$fullPath = [IO.Path]::GetFullPath($Path)
if (-not (Test-Path -LiteralPath $fullPath -PathType Container)) {
    Write-Host "Share folder does not exist, creating: $fullPath"
    New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
}
$fullPath = (Resolve-Path -LiteralPath $fullPath).ProviderPath

$enableSMB2 = -not $DisableSMB2
$enableSMB3 = -not $DisableSMB3
if ($enableSMB3 -and -not $enableSMB2) {
    throw "-DisableSMB2 cannot be combined with SMB3; add -DisableSMB3 for an SMB1-only server."
}
if (-not $EnableSMB1 -and -not $enableSMB2) {
    throw "All dialects are disabled. Remove -DisableSMB2, or add -EnableSMB1."
}

try {
    $bindIp = [System.Net.IPAddress]::Parse($BindAddress)
}
catch {
    $addresses = [System.Net.Dns]::GetHostAddresses($BindAddress)
    if ($addresses.Count -eq 0) {
        throw "Cannot resolve -BindAddress '$BindAddress'."
    }
    $bindIp = $addresses[0]
}

[PwshSmbServerHost.SmbAuth]::SetUsers([string[]]@(('{0}:{1}' -f $User, $Password)))

$provider = [PwshSmbServerHost.SmbAuth]::CreateProvider()
$securityProvider = [SMBLibrary.Authentication.GSSAPI.GSSProvider]::new($provider)
$fileStore = [SMBLibrary.Win32.NTDirectoryFileSystem]::new($fullPath)
$share = [SMBLibrary.Server.FileSystemShare]::new($ShareName, $fileStore)
if (-not $AllowWrite) {
    [PwshSmbServerHost.ReadOnlyGuard]::Attach($share)
}
$shares = [SMBLibrary.Server.SMBShareCollection]::new()
$shares.Add($share)

$server = [PwshSmbServerHost.SmbServer]::new($shares, $securityProvider)
if ($VerbosePreference -ne 'SilentlyContinue') {
    [PwshSmbServerHost.SmbLog]::Attach($server)
}

try {
    $server.StartOnPort($bindIp, [SMBLibrary.SMBTransportType]::DirectTCPTransport, $Port, [bool]$EnableSMB1, $enableSMB2, $enableSMB3)
}
catch [System.Net.Sockets.SocketException] {
    Write-Error ("Could not listen on {0}:{1} ({2}). Port 445 needs an elevated shell and no other SMB server (e.g. LanmanServer) using it. Try -Port 4450." -f $BindAddress, $Port, $_.Exception.Message)
    throw
}

$dialects = @()
if ($EnableSMB1) { $dialects += 'SMB1' }
if ($enableSMB2) { $dialects += 'SMB2' }
if ($enableSMB3) { $dialects += 'SMB3' }

$mode = 'Read-only'
if ($AllowWrite) {
    $mode = 'Read-write'
}

$account = $User
if ($User -ieq 'Guest' -and [string]::IsNullOrEmpty($Password)) {
    $account = 'Guest (empty password, guest fallback enabled)'
}

Write-Host ''
Write-Host 'SMB server is running.' -ForegroundColor Green
Write-Host ("  Share   : \\{0}\{1}" -f [Environment]::MachineName, $ShareName)
Write-Host ("  Folder  : {0}" -f $fullPath)
Write-Host ("  Listen  : {0}:{1} ({2})" -f $BindAddress, $Port, ($dialects -join ', '))
Write-Host ("  Account : {0}" -f $account)
Write-Host ("  Mode    : {0}" -f $mode)
if ($Port -ne 445) {
    Write-Host '  Note    : Windows Explorer / net use only use TCP 445. For those, run with -Port 445 (elevated).' -ForegroundColor Yellow
    Write-Host ('  Test    : powershell -File "{0}" -Port {1} -ShareName "{2}" -User "{3}" -Password "<password>"' -f (Join-Path $PSScriptRoot 'Test-SmbClient.ps1'), $Port, $ShareName, $User)
}
Write-Host '  Stop    : Ctrl+C'
Write-Host ''

$deadline = $null
if ($RunSeconds -gt 0) {
    $deadline = [DateTime]::UtcNow.AddSeconds($RunSeconds)
}

try {
    while ($true) {
        if ($null -ne $deadline -and [DateTime]::UtcNow -ge $deadline) {
            break
        }
        Start-Sleep -Milliseconds 500
    }
}
finally {
    $server.Stop()
    Write-Host 'SMB server stopped.'
}
