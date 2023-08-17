import asyncio
from .rehoboam import Rehoboam, check_folders, check_files

async def setup(bot):
    check_folders()
    check_files()

    await bot.add_cog(Rehoboam(bot))