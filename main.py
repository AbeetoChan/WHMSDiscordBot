import json
import redis
import discord

###################
redis_db = redis.Redis(host="localhost", port=6379, db=0)
###################

#######################
with open("config.json") as f:
    json_data = json.load(f)

    # Load the bot token from the file - the only thing we need
    TOKEN = json_data["BOT_TOKEN"]
#######################

# Intents
intents: discord.Intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Discord now requires gateway intents
bot = discord.Bot(intents=intents)

#################
bot.redis_db = redis_db
bot.load_extension("leveling")
#################

bot.run(TOKEN)
