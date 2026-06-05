import os
import threading
import asyncio
from flask import Flask, jsonify
from main import bot  # Imports your bot instance from main.py

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "Discord bot wrapper is running."})

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot.run(os.environ.get('TOKEN'))

# Start the bot in the background so Flask can finish loading
if "TOKEN" in os.environ:
    threading.Thread(target=run_bot, daemon=True).start()
