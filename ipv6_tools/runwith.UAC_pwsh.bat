@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
SET count=1
FOR /F "tokens=* USEBACKQ" %%F IN (`pwsh -NoProfile -ExecutionPolicy Bypass -Command "[System.Text.Encoding]::Default.EncodingName"`) DO (
SET var!count!=%%F
SET /a count=!count!+1
)
if "%~1"=="" (
    echo No Script Provided, Drag the "*.ps1" to this batch to try again
    pause

) else (
    if /i "%var1%"=="Unicode (UTF-8)" (
        pwsh -NoProfile -ExecutionPolicy Bypass -Command "& {Start-Process pwsh -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~1""' -Verb RunAs}"
    ) else (
        echo If Nothing Happend after pressing ENTER 
        echo Save the "*.ps1" file with encoding "GBK/GB2312/ANSI" then try again
        pause
	pwsh -NoProfile -ExecutionPolicy Bypass -Command "& {Start-Process pwsh -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~1""' -Verb RunAs}"
    )
)

ENDLOCAL
