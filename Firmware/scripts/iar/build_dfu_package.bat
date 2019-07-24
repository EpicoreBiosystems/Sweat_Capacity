@echo off
set DFU_TOOL_DIR=..

set APP_HEX_DIR="..\..\application\iar\_build"
set RELEASE_DIR="..\..\builds\iar"

if not exist %RELEASE_DIR% mkdir %RELEASE_DIR%

@echo Build application DFU package

REM NOTE: application version must be greater than or equal to the current one.
%DFU_TOOL_DIR%\nrfutil pkg generate --hw-version 52 --application %APP_HEX_DIR%\sweat_capacity.hex --key-file %DFU_TOOL_DIR%\priv.pem --sd-req 0xa8 --application-version-string "1.0.0" %RELEASE_DIR%\sweat_capacity_app_dfu_package.zip

@echo on
%DFU_TOOL_DIR%\nrfutil pkg display %RELEASE_DIR%\sweat_capacity_app_dfu_package.zip

@echo off

