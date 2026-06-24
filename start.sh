#!/bin/sh

echo "🚀 بدء تشغيل API..."
uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000} &

echo "🤖 بدء تشغيل البوت..."
python bot.py
