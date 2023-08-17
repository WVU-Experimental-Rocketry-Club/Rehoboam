from .scarlet import Scarlet

async def setup(bot):
    await bot.add_cog(Scarlet(bot))