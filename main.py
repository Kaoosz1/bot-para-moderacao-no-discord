import discord
from discord.ext import commands, tasks
import qrcode
from io import BytesIO
import asyncio
import datetime
import re
import json
import os

from dotenv import load_dotenv
load_dotenv()


intents = discord.Intents.all()
bot = commands.Bot(".", intents=intents)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# IDs dos usuários autorizados
w1eak = int(os.getenv("ID_W1EAK"))
jake = int(os.getenv("ID_JAKE"))
USUARIOS_PODEM_BANIR = [w1eak, jake]

# Categorias e cargos permitidos
CATEGORIAS_PERMITIDAS = ["Bem Vindo !", "♱"]
CARGO_PERMITIDO = ["ticket helper", "criarcall"]

# ID da categoria das calls
ID_CATEGORIA_CALLS = int(os.getenv("ID_CATEGORIA_CALLS"))

# Armazenamento de calls privadas
calls_privadas = {}
advertencias = {}

# Whitelist de usuários e blacklist de canais
WHITELIST_IDS = [w1eak, jake]
BLACKLIST_CANAIS = [int(os.getenv("ID_CANAL_BLACKLIST"))]  # Coloque o ID real do canal geral

# Regex para identificar links
LINK_REGEX = r"(https?://\S+|www\.\S+)"

# Arquivo para salvar palavras proibidas
ARQUIVO_PALAVRAS = "palavras.json"


# ----------------------- Gerenciamento do JSON -----------------------
def carregar_palavras():
    if not os.path.exists(ARQUIVO_PALAVRAS):
        with open(ARQUIVO_PALAVRAS, "w") as f:
            json.dump({"palavras": []}, f)
    with open(ARQUIVO_PALAVRAS, "r") as f:
        return json.load(f).get("palavras", [])

def salvar_palavras(lista):
    with open(ARQUIVO_PALAVRAS, "w") as f:
        json.dump({"palavras": lista}, f, indent=4)


PALAVRAS_PROIBIDAS = carregar_palavras()


# ----------------------- Eventos e Lógica -----------------------
@bot.event
async def on_ready():
    print("Bot inicializado com sucesso")
    verificar_calls_inativas.start()

async def gerar_qrcode(texto):
    qr = qrcode.make(texto)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(fp=buffer, filename="pix.png")

def autorizado(ctx):
    cat = ctx.channel.category and ctx.channel.category.name in CATEGORIAS_PERMITIDAS
    role_ok = any(role.name in CARGO_PERMITIDO for role in ctx.author.roles)
    return cat and role_ok

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    texto = message.content.lower()

    if message.author.id in WHITELIST_IDS:
        await bot.process_commands(message)
        return

    if message.channel.id in BLACKLIST_CANAIS and re.search(LINK_REGEX, texto):
        try:
            await message.delete()
            await message.channel.send(f"🚫 {message.author.mention}, links não são permitidos aqui.")
        except:
            pass
        await bot.process_commands(message)
        return

    if any(p in texto for p in PALAVRAS_PROIBIDAS):
        try:
            await message.delete()
        except:
            pass
        await aplicar_punicao(message)

    await bot.process_commands(message)

async def aplicar_punicao(message):
    membro = message.author
    guild = message.guild
    cnt = advertencias.get(membro.id, 0) + 1
    advertencias[membro.id] = cnt

    cargo = discord.utils.get(guild.roles, name="Advertido")
    if not cargo:
        cargo = await guild.create_role(name="Advertido")
    await membro.add_roles(cargo)

    if cnt == 1:
        await aplicar_timeout(membro, 600)
        await message.channel.send(f"⚠️ {membro.mention} – Mute de 10 minutos.")
    elif cnt == 2:
        await aplicar_timeout(membro, 3600)
        await message.channel.send(f"⚠️ {membro.mention} – Mute de 1 hora.")
    else:
        try:
            await membro.kick(reason="3 advertências.")
            await message.channel.send(f"⛔ {membro.mention} foi expulso após 3 infrações.")
        except:
            await message.channel.send("❌ Sem permissão para expulsar.")
        advertencias.pop(membro.id, None)

async def aplicar_timeout(membro, segundos):
    until = datetime.datetime.utcnow() + datetime.timedelta(seconds=segundos)
    try:
        await membro.timeout(until)
    except:
        pass


# ----------------------- Comandos existentes -----------------------
@bot.command()
async def pix(ctx):
    if not autorizado(ctx):
        return await ctx.reply("❌ Sem permissão.")
    chave = "368aac3e-7c0c-47b5-96b7-59bfbf280b0e" if ctx.author.id == w1eak else "apel4kk@gmail.com"
    await ctx.reply(chave)
    await ctx.send(file=await gerar_qrcode(chave))
    await ctx.send("NÃO ACEITAMOS MercadoPago, PicPay, Inter. Recomendamos Nubank.")

# ... Seus comandos otmz, sensi, ban, criarcall, permitir, remover, limpar continuam iguais ...

# ----------------------- Comandos de moderação -----------------------
@bot.command()
async def advertencias(ctx, membro: discord.Member = None):
    m = membro or ctx.author
    cnt = advertencias.get(m.id, 0)
    await ctx.send(f"{m.mention} tem {cnt} advertência(s).")

@bot.command()
@commands.has_permissions(administrator=True)
async def limparadvertencias(ctx, membro: discord.Member):
    if membro.id in advertencias:
        advertencias.pop(membro.id)
        await ctx.send("🗑️ Advertências removidas.")
    else:
        await ctx.send("❗ Sem advertências.")

@bot.command()
@commands.has_permissions(administrator=True)
async def addpalavra(ctx, *, palavra: str):
    w = palavra.lower().strip()
    if w in PALAVRAS_PROIBIDAS:
        return await ctx.send("⚠️ Já existe.")
    PALAVRAS_PROIBIDAS.append(w)
    salvar_palavras(PALAVRAS_PROIBIDAS)
    await ctx.send(f"✅ `{w}` adicionada.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removepalavra(ctx, *, palavra: str):
    w = palavra.lower().strip()
    if w not in PALAVRAS_PROIBIDAS:
        return await ctx.send("⚠️ Não encontrada.")
    PALAVRAS_PROIBIDAS.remove(w)
    salvar_palavras(PALAVRAS_PROIBIDAS)
    await ctx.send(f"✅ `{w}` removida.")

@bot.command()
@commands.has_permissions(administrator=True)
async def listarpalavras(ctx):
    if not PALAVRAS_PROIBIDAS:
        return await ctx.send("ℹ️ Nenhuma palavra proibida.")
    await ctx.send("🚫 Proibidas: " + ", ".join(f"`{p}`" for p in PALAVRAS_PROIBIDAS))


# ----------------------- Background Task para calls  -----------------------
@tasks.loop(minutes=30)
async def verificar_calls_inativas():
    now = datetime.datetime.utcnow()
    for cid, info in list(calls_privadas.items()):
        if (now - info["ultima_atividade"]).total_seconds() > 86400:
            chan = bot.get_channel(cid)
            if chan:
                await chan.delete(reason="Expirou 24h.")
            calls_privadas.pop(cid, None)

# ----------------------- Inicia bot -----------------------
bot.run("MTM4NTE5NTQ4MTQ0NTE3MTI0MA.Gu9LvN.6r_RS0rZmn2fZ6bwwIUcMn7xTaLcbl_qPA35_E")
