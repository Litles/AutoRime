@echo off
setlocal EnableDelayedExpansion

echo Start building schemas ...
echo:
cd Rime
..\librime_x86\bin\rime_deployer.exe --build
echo:
echo Done.
pause
