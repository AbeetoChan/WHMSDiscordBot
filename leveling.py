import discord
from discord.ext import commands
from redis import Redis
from new_user_setup import handle_member_join

with open("swear_words.txt") as s:
    SWEAR_WORDS = [sw.lower().replace("\n", "") for sw in s.readlines()]


class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.redis_db: Redis = bot.redis_db

    @commands.slash_command(description="See how many swear strikes a user has")
    async def see_swear_strikes(self, ctx: discord.ApplicationContext, user: str):
        roles = [x.name for x in ctx.author.roles]
        if "Admin" not in roles:
            await ctx.respond("Sorry! You do not have the privellages to run this command!")
            return

        user = ctx.author.guild.get_member_named(user)

        try:
            user_id = user.id
        except AttributeError:
            await ctx.respond("It seems like that person does not exist...")
            return

        if not self.redis_db.exists(str(user_id)):
            await ctx.respond("Sorry! That person has not sent a message on the server yet!")
            return

        strikes = int(self.redis_db.hget(str(user_id), "strikes"))

        dm = await ctx.author.create_dm()
        await dm.send(f"{user.display_name} has {strikes} strikes")
        await ctx.respond("You should get a dm about now...")

    @commands.slash_command(description="See your level!")
    async def level(self, ctx: discord.ApplicationContext):
        user_id = ctx.author.id

        if not self.redis_db.exists(str(user_id)):
            await self.handle_member_join(ctx.author)

        level = int(self.redis_db.hget(str(user_id), "lvl"))

        embed = discord.Embed(
            title="Level",
            description=f"You are level {level}",
            color=discord.Color.gold()
        )

        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)

        await ctx.respond(embed=embed)

    @commands.slash_command(description="See this server's level leaderboard!")
    async def leaderboard(self, ctx: discord.ApplicationContext):
        db_keys = self.redis_db.keys()  # Might be slow when there are more users, runs in O(N) time
        db_values = [(int(user), int(self.redis_db.hget(user, "lvl"))) for user in db_keys]
        # There is currently no way to do this functionality natively in Redis rn

        db_values.sort(key=lambda k: k[1], reverse=True)

        embed = discord.Embed(
            title="Leaderboard",
            description="The current server leaderboard\n",
            color=discord.Color.gold()
        )

        for u in db_values[:5]:
            user = await self.bot.fetch_user(u[0])
            embed.description += f"**{user.display_name}**: level {u[1]}\n"

        if ctx.author.avatar is None:
            embed.set_author(name=ctx.author.display_name)
        else:
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar)

        embed.set_footer(text="The rankings are subject to change")
        await ctx.respond(embed=embed)

    @staticmethod
    async def level_up(message: discord.Message, new_level):
        embed = discord.Embed(
            title="Level up!",
            description=f"You have leveled up to level {new_level}!",
            color=discord.Color.gold()
        )

        if message.author.avatar is None:
            embed.set_author(name=message.author.display_name)
        else:
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
        await message.reply(embed=embed)

    @staticmethod
    def can_level_up(current_level, pts):
        # This is a reimplementation of mee6's alg
        return (current_level ** 2) / 45 + 3.3 * current_level < pts

    @staticmethod
    def has_profanity_in_it(content: str):
        for sw in SWEAR_WORDS:
            if sw in content:
                return True

        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return

        user_id = message.author.id

        if self.has_profanity_in_it(message.content):
            strike = self.redis_db.hincrby(str(user_id), "strikes", 1)

            await message.delete()
            dm = await message.author.create_dm()
            await dm.send(f"Please don't send offensive messages like that! Strike #{strike}")
            return

        if not self.redis_db.exists(str(user_id)):
            await handle_member_join(self.redis_db, message.author)

        with self.redis_db.pipeline() as pipe:
            pts = self.redis_db.hincrby(str(user_id), "pts", 1)
            current_level = int(self.redis_db.hget(str(user_id), "lvl"))

            if self.can_level_up(current_level, pts):
                pipe.hset(str(user_id), "pts", 0)
                level = self.redis_db.hincrby(str(user_id), "lvl", 1)
                await self.level_up(message, level)

            pipe.execute()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        NOTE
        This would have to be completely changed if this bot were to join more than one server
        """
        await handle_member_join(self.redis_db, member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """
        NOTE
        This would have to be completely changed if this bot were to join more than one server
        """
        user_id = member.id

        self.redis_db.delete(str(user_id))


def setup(bot):
    bot.add_cog(Leveling(bot))
