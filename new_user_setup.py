import discord
from redis import Redis


async def handle_member_join(redis_db: Redis, member: discord.Member):
    user_id = member.id

    with redis_db.pipeline() as pipe:
        pipe.hmset(str(user_id), {
            "pts": 0,
            "lvl": 0,
            "strikes": 0
        })
        pipe.execute()
