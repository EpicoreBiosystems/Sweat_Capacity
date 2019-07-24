@echo off
set NRFJPROG_DIR="C:\Program Files (x86)\Nordic Semiconductor\nrf5x\bin"
set NRF_SDK_DIR="..\..\nRF5_SDK_15.0.0_a53641a"
set DFU_TOOL_DIR=..

set APP_HEX_DIR="..\..\application\iar\_build"
set BL_HEX_DIR="..\..\bootloader\iar\_build"
set SD_HEX_DIR="%NRF_SDK_DIR%\components\softdevice\s132\hex"
set RELEASE_DIR="..\..\builds\iar"

if not exist %RELEASE_DIR% mkdir %RELEASE_DIR%

%DFU_TOOL_DIR%\nrfutil.exe settings generate --family NRF52 --application %APP_HEX_DIR%\sweat_capacity.hex --application-version-string "1.0.0" --bootloader-version 1 --bl-settings-version 1 --no-backup %RELEASE_DIR%\bl_settings.hex

%NRFJPROG_DIR%\mergehex.exe -m %BL_HEX_DIR%\sweat_secure_bootloader_ble.hex %RELEASE_DIR%\bl_settings.hex -o %RELEASE_DIR%\sweat_bootloader_with_settings.hex
%NRFJPROG_DIR%\mergehex.exe -m %SD_HEX_DIR%\s132_nrf52_6.0.0_softdevice.hex %RELEASE_DIR%\sweat_bootloader_with_settings.hex -o %RELEASE_DIR%\sweat_sd_bl.hex
%NRFJPROG_DIR%\mergehex.exe -m %APP_HEX_DIR%\sweat_capacity.hex %RELEASE_DIR%\sweat_sd_bl.hex -o %RELEASE_DIR%\sweat_capacity_sd_bl_app.hex

@echo The all-in-one production firmware created at %RELEASE_DIR%\sweat_capacity_sd_bl_app.hex
