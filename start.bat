@echo off
echo ===================================================
echo       Starting PharmaVisit CRM Services
echo ===================================================

echo [1/2] Starting Route Optimizer Microservice...
start "PharmaVisit - Route Optimizer" cmd /c "cd route-optimizer && python main.py"

echo [2/2] Starting Laravel Server...
php artisan serve
