@echo off
echo Starting both Backend and Chatbot servers...

REM =============================================
REM 1. سيرفر الواجهة الرئيسية (Main Backend)
REM =============================================
REM **تأكد من أن اسم البيئة هو 'venv' أو غيِّره إلى الاسم الصحيح**
call .\venv311\Scripts\activate 
echo Starting Main Server on Port 5000...
start cmd /k "python app.py"

REM =============================================
REM 2. سيرفر الشات بوت (Chatbot Server)
REM =============================================
call./venv311/Scripts/activate
uvicorn app.chatapp:app --reload
echo Starting Chatbot Server on Port 8000...
start cmd /k "python -m uvicorn app.chatapp:app --reload"

echo Both servers initiated. Check the new command windows for server logs.
pause