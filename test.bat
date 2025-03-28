@echo off
chcp 65001
setlocal EnableDelayedExpansion

echo Entering librime console ...
echo Tip: input codes to get candidates, input "1" to commit the first candidate
echo Tip: input "exit" to exit when in "(not composing)" status
echo:
cd Rime
..\librime_x86\bin\rime_api_console.exe
echo:
echo Done.
pause
