@echo off
REM Job Alert - scheduled scan (runs via Windows Task Scheduler every 30 min)
REM Uses pythonw.exe so no console window pops up; output goes to the log file.
cd /d D:\job-alert
"C:\Users\moham\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe" main.py ^
  --keywords "python developer" ^
  --max-experience 2 ^
  --location remote ^
  --location India ^
  --interval 30 ^
  --once ^
  --log-file logs\job-alert.log
