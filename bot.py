import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from aiohttp import web

# ตั้งค่า Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix='/', intents=intents)

# ตัวแปรเก็บสถานะ
is_playing = False

@bot.event
async def on_ready():
    print(f'บอทพร้อมใช้งาน: {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f'ซิงค์คำสั่ง {len(synced)} คำสั่งเรียบร้อย')
    except Exception as e:
        print(f'เกิดข้อผิดพลาดในการซิงค์: {e}')

@bot.tree.command(name="tome", description="เรียกบอทเข้าห้องเสียง")
async def tome(interaction: discord.Interaction):
    if interaction.user.voice is None:
        await interaction.response.send_message("❌ คุณต้องอยู่ในห้องเสียงก่อน!", ephemeral=True)
        return
    
    channel = interaction.user.voice.channel
    
    if interaction.guild.voice_client is not None:
        await interaction.guild.voice_client.move_to(channel)
        await interaction.response.send_message(f"✅ ย้ายไปที่ห้อง: {channel.name}")
    else:
        await channel.connect()
        await interaction.response.send_message(f"✅ เข้าห้องเสียง: {channel.name}")

@bot.tree.command(name="p1", description="เล่นไฟล์เสียง p1.mp3")
async def p1(interaction: discord.Interaction):
    global is_playing
    
    if interaction.guild.voice_client is None:
        await interaction.response.send_message("❌ บอทต้องอยู่ในห้องเสียงก่อน! ใช้คำสั่ง /tome", ephemeral=True)
        return
    
    if is_playing:
        await interaction.response.send_message("❌ กำลังเล่นเสียงอยู่แล้ว!", ephemeral=True)
        return
    
    if not os.path.exists('p1.mp3'):
        await interaction.response.send_message("❌ ไม่พบไฟล์ p1.mp3", ephemeral=True)
        return
    
    voice_client = interaction.guild.voice_client
    
    # ฟังก์ชันที่เรียกเมื่อเล่นเสียงจบ
    def after_playing(error):
        global is_playing
        is_playing = False
        if error:
            print(f'เกิดข้อผิดพลาด: {error}')
    
    is_playing = True
    voice_client.play(discord.FFmpegPCMAudio('p1.mp3'), after=after_playing)
    await interaction.response.send_message("🎵 กำลังเล่น p1.mp3")

@bot.tree.command(name="out", description="ให้บอทออกจากห้องเสียง")
async def out(interaction: discord.Interaction):
    if interaction.guild.voice_client is None:
        await interaction.response.send_message("❌ บอทไม่ได้อยู่ในห้องเสียง!", ephemeral=True)
        return
    
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message("👋 ออกจากห้องเสียงแล้ว")

# ระบบ Web Server สำหรับป้องกันโฮสดับบน Render
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_get('/health', handle_ping)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()
    print(f'Web server เริ่มทำงานที่พอร์ต {os.environ.get("PORT", 8080)}')

async def self_ping():
    """ปิงตัวเองทุก 5 นาทีเพื่อป้องกันโฮสดับ"""
    await bot.wait_until_ready()
    import aiohttp
    
    # รอให้ web server พร้อม
    await asyncio.sleep(10)
    
    while not bot.is_closed():
        try:
            async with aiohttp.ClientSession() as session:
                # ปิงตัวเอง
                render_url = os.environ.get('RENDER_EXTERNAL_URL')
                if render_url:
                    async with session.get(f"{render_url}/health") as response:
                        if response.status == 200:
                            print("✓ Self-ping สำเร็จ")
        except Exception as e:
            print(f"Self-ping error: {e}")
        
        # รอ 5 นาที
        await asyncio.sleep(300)

async def main():
    # เริ่ม web server
    await start_web_server()
    
    # เริ่มบอท
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        print("❌ ไม่พบ DISCORD_TOKEN ใน environment variables!")
        return
    
    async with bot:
        # เริ่ม self-ping task หลังจากบอทพร้อม
        bot.loop.create_task(self_ping())
        await bot.start(token)

if __name__ == '__main__':
    asyncio.run(main())
