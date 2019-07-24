@echo off
set NRFJPROG_DIR="C:\Program Files (x86)\Nordic Semiconductor\nrf5x\bin"
set RELEASE_DIR="..\..\builds\armgcc"

@echo Erasing flash ...
%NRFJPROG_DIR%\nrfjprog -e

@echo Programming application ...
%NRFJPROG_DIR%\nrfjprog --reset --program %RELEASE_DIR%\sweat_sd_bl_app.hex --family NRF52 --verify

@echo Flash programming completed successfully!
pause