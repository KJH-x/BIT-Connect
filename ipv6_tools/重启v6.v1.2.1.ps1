param([bool]$detail = 0) 
# encoding : utf-8
# 重启v6.ps1
# Version 1.2.1

function Get-IPAddressType {
    param (
        [string]$ipAddress
    )
    $ipv4Pattern = '^((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])$'
    $ipv6Pattern = '^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$'
    if ($ipAddress -match $ipv6Pattern) {
        return 6
    }
    elseif ($ipAddress -match $ipv4Pattern) {
        return 4
    }
    else {
        return 0
    }
}

# 获取公网地址
function Test-IPW() {
    # return
    try {
        $uri = "test.ipw.cn"
        return (Invoke-RestMethod -Uri $uri -NoProxy)
    }
    catch {
        Write-Host "[警告] 无法连接到ipw.cn，请先连接到互联网后再尝试本脚本" -ForegroundColor Red
        exit
    }
}
# 显示网络适配器列表以供用户选择
function ShowAdapterList {
    param(
        [System.Object]$adapters
    )
    Write-Host ("-" * 80)
    Write-Host "[信息] 请选择要配置的网络适配器："
    Write-Host "-1. 打开 test-ipv6.com 查看完整测试"
    Write-Host " 0. 退出脚本"
    for ($i = 0; $i -lt $adapters.Count; $i++) {
        if ($adapters[$i].Name -like '*以太网*' -or $adapters[$i].Name -like '*Ethernet*') {
            Write-Host " $($i + 1). $($adapters[$i].Name) <-也许是这个" -ForegroundColor Cyan
        }
        else {
            Write-Host " $($i + 1). $($adapters[$i].Name)"
        }
    }
    Write-Host ("-" * 80)
}

# 显示适配器IP信息
function ShowAdapterIPInfo {
    $ipAddresses = Get-NetIPAddress -InterfaceAlias $selectedAdapter.Name
    Write-Host ("-" * 80)
    if ($detail) {
        Write-Host "[信息] 当前网络适配器连接详细信息："
        $ipAddresses
    }
    else {
        Write-Host "[警告] 不会打印当前网络适配器" -NoNewline -ForegroundColor Red
        Write-Host "$($selectedAdapter.Name)" -NoNewline -ForegroundColor Cyan
        Write-Host "连接详细信息" -ForegroundColor Red

        Write-Host "[信息] 向脚本传递参数`-detail 1`以打印详细信息"

        Write-Host "[信息] 当前网络适配器" -NoNewline
        Write-Host "$($selectedAdapter.Name)" -NoNewline -ForegroundColor Cyan
        Write-Host "的 IP 有："

        # 本地地址将会以暗红色显示
        foreach ($ip in $ipAddresses | Select-Object -ExpandProperty IPAddress) {
            if ($ip -like "fe80:*" -or $ip -like "10.*" -or $ip -like "192.*") {
                Write-Host "       LAN Address: $ip" -ForegroundColor DarkRed 
            }
            else {
                Write-Host "       $ip"
            }
        }
        
    }
    Write-Host ("-" * 80)
}

# 询问用户是否继续
function ConfirmContinue {
    Write-Host ("-" * 80)
    Write-Host  "[等待输入] 选择 (Y)es/(N)o > " -NoNewline -ForegroundColor Green
    $continue = Read-Host
    if ($continue -eq "Y" -or $continue -eq "y") {
        Write-Host "[信息] 您选择了 (Y)es。"
        return $true
    }
    elseif ($continue -eq "N" -or $continue -eq "n") {
        Write-Host "[信息] 您选择了 (N)o"
        return $false
    }
    else {
        Write-Host "[信息] 您的输入无效，请重试"
        return ConfirmContinue
    }
}
function Test-InternetAdapter {
    param (
        [bool]$skipAutoCheck
    )
    $adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }
    if (-not $skipAutoCheck) {
        # 试图自动获取
        $ipAddress = Test-IPW
        foreach ($adapter in $adapters) {
            $ipType = Get-IPAddressType $ipAddress
            $adapterIPAddress = $adapter | Get-NetIPAddress | Select-Object -ExpandProperty IPAddress
            if ($adapterIPAddress -contains $ipAddress) {
                # Write-Host "Adapter $($adapter.Name) is using IP address $ipAddress"
                Write-Host "[信息] 当前访问网络的网络适配器" -NoNewline
                Write-Host "$($adapter.Name)" -NoNewline -ForegroundColor Cyan
                Write-Host ", IP 是："
                if ($ipType -eq 6) {
                    Write-Host "       $ipAddress" -ForegroundColor Cyan
                    Write-Host "       您的网络是IPv6访问优先，应该可以正常使用各种功能" -ForegroundColor Yellow
                }
                elseif ($ipType -eq 4) {
                    # 校园网下不应该返回本地v4地址，为了泛用性，保留此分支
                    Write-Host "       $ipAddress" -ForegroundColor DarkRed
                    Write-Host "       您的网络是IPv4访问优先，建议执行重置操作" -ForegroundColor Red
                }
                else {
                    # 不应该抵达的分支
                    Write-Host "       $ipAddress" -ForegroundColor DarkRed
                    Write-Host "       判断异常" -ForegroundColor Red
                }
                return $adapter
            }
        }
    }
    if ( -not $skipAutoCheck) {
        Write-Host "[警告] 测试返回了本地没有的公网地址" -ForegroundColor Red
        Write-Host "[警告] 无法自动判断当前访问网络的网络适配器" -ForegroundColor Red
        if ($ipType -eq 6) {
            # 有细分判断方法但是没必要
            Write-Host "       $ipAddress" -ForegroundColor Cyan
            Write-Host "       您的网络是IPv6访问优先，但与本地地址不一致" -ForegroundColor Yellow
            Write-Host "       可能是NAT或者Teredo" -ForegroundColor Yellow
        }
        elseif ($ipType -eq 4) {
            Write-Host "       $ipAddress" -ForegroundColor DarkRed
            Write-Host "       您的网络是IPv4访问优先，建议执行重置操作" -ForegroundColor Red
            Write-Host "       这可能是临时问题，完整测试请在下面的选择中输入-1" -ForegroundColor Red
        }
        else {
            # 不应该抵达的分支
            Write-Host "       $ipAddress" -ForegroundColor DarkRed
            Write-Host "       判断异常" -ForegroundColor Red
        }
    }
    $adapters = Get-NetAdapter
    ShowAdapterList  -adapters $adapters
    do {
        Write-Host  "[等待输入] 输入序号 > " -NoNewline -ForegroundColor Green
        $selectedAdapterIndex = Read-Host

        # 验证用户输入的序号是否有效
        if ($selectedAdapterIndex -ge -1 -and $selectedAdapterIndex -le $adapters.Count) {
            if ($selectedAdapterIndex -eq -1) {
                # 用户选择退出
                Write-Host "[信息] 您选择了 -1. 打开 test-ipv6.com 查看完整测试 "
                Start-Process "http://test-ipv6.com/"
                Write-Host  "[等待输入] 按任意键继续 > " -ForegroundColor Green
                # 按下任意键检测
                Read-Host -AsSecureString
                continue
            }
            elseif ($selectedAdapterIndex -eq 0) {
                # 用户选择退出
                Write-Host "[信息] 您选择了 0. 退出脚本。"
                exit
            }
            else {
                return $adapters[$selectedAdapterIndex - 1]
            }
        }
        else {
            Write-Host "[信息] 输入有误，请重试"
        }
    }while ($true)
}


# 管理员权限检查
Write-Host ("-" * 80)
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    # 非管理员身份，因powershell策略限制，自提升较为困难
    Write-Host "[警告] 您需要以管理员身份运行该脚本。（以管理员身份运行powershell）" -ForegroundColor Red
    Write-Host  "[等待输入] 按任意键退出 > " -ForegroundColor Green
    # 按下任意键检测
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');
    Write-Host ("-" * 80)
}
else {
    Write-Host "[警告] 您正在以管理员身份运行该脚本。注意操作安全" -ForegroundColor Red
}
$skipAutoCheck = 0
do {
    # 提示用户输入所选网络适配器的序号
    # 用户选择有效序号
    $selectedAdapter = Test-InternetAdapter -skipAutoCheck $skipAutoCheck

    # 获取该网络适配器的 Internet 协议版本 6 (TCP/IPv6) 配置
    $ipv6Setting = Get-NetAdapterBinding -Name $selectedAdapter.Name -ComponentID "ms_tcpip6"

    # 显示适配器IP信息
    ShowAdapterIPInfo

    Write-Host "[信息] $($selectedAdapter.Name) 的" -NoNewline
    Write-Host "【Internet 协议版本 6 (TCP/IPv6)】" -NoNewline -ForegroundColor Cyan
    Write-Host "状态为：$($ipv6Setting.Enabled)"
            
    Write-Host "[信息] 需要重启 $($selectedAdapter.Name) 的" -NoNewline
    Write-Host "【Internet 协议版本 6 (TCP/IPv6)】" -NoNewline -ForegroundColor Cyan
    Write-Host "吗, 此操作会断开当前reloa连接"

    if (ConfirmContinue) {
        # 停用 ms_tcpip6
        Disable-NetAdapterBinding -Name $selectedAdapter.Name -ComponentID "ms_tcpip6"

        Write-Host "[信息] 已禁用 $($selectedAdapter.Name) 的" -NoNewline
        Write-Host "【Internet 协议版本 6 (TCP/IPv6)】" -NoNewline -ForegroundColor Cyan
        Write-Host "。"
                    
        # 等待3秒
        Write-Host "[信息] 等待3秒。"
        Start-Sleep -Seconds 3
                    
        # 启用 ms_tcpip6
        Enable-NetAdapterBinding -Name $selectedAdapter.Name -ComponentID "ms_tcpip6"

        Write-Host "[信息] 已启用 $($selectedAdapter.Name) 的" -NoNewline
        Write-Host "【Internet 协议版本 6 (TCP/IPv6)】" -NoNewline -ForegroundColor Cyan
        Write-Host "。"

        # 等待10秒
        Write-Host "[信息] 等待10秒。或使用Ctrl+C直接退出"
        Start-Sleep -Seconds 10
                    
        # 显示适配器IP信息
        ShowAdapterIPInfo
    }
    # 询问用户是否继续
    Write-Host "[信息] 继续操作其他适配器(是/Yes)，还是直接退出(否/No)"
    if (-not (ConfirmContinue)) {
        break
    }
    # else {continue}
    $skipAutoCheck = 1
} while ($true)
Write-Host "[信息] 程序结束"