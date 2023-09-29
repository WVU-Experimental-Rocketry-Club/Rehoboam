from .sandpaper import Sandpaper

async def setup(bot):
    await bot.add_cog(Sandpaper(bot))