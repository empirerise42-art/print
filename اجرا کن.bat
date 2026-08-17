@echo off
chcp 65001 >nul
title چاپ 16 عکس در برگ A4
echo ========================================
echo    برنامه چاپ 16 عکس در برگ A4
echo ========================================
echo.
echo در حال اجرای برنامه...
echo.
python A4_Printer.py
if errorlevel 1 (
    echo.
    echo خطا در اجرای برنامه!
    echo لطفاً مطمئن شوید Python نصب است.
    echo.
    pause
)
