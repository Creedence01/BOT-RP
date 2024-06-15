import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import json
import os
import random

TOKEN = 'MTI1MDEyMzYwMDExMTk5MjkxMg.Gry83G.zjMlDDf2TlJs-TsLqZyU_NHnA6TtSRzjNtJRkk'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# File to save data
data_file = 'data.json'

# Carregar dados do arquivo JSON
try:
    with open('data.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    data = {}

# Load data
def load_data():
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
                print("Data loaded:", data)  # Debugging line
                return data
        except json.JSONDecodeError as e:
            print(f"Error loading data: {e}")
            return {}
    else:
        print(f"Data file {data_file} not found.")
        return {}

data = load_data()

# Save data function
def save_data():
    try:
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=4)
            print("Data saved:", data)  # Debugging line
    except IOError as e:
        print(f"Failed to save '{data_file}': {e}")
        # Força a sobrescrita do arquivo
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=4)
            print("Data forcibly saved:", data)  # Debugging line

# Função para obter dados do usuário sem registrar automaticamente
def get_user_data(user):
    user_id = str(user.id)
    return data.get(user_id, None)

# Função para registrar um novo usuário
def register_user(user):
    user_id = str(user.id)
    if user_id not in data:
        data[user_id] = {
            'country': '',
            'gdp': 0,
            'military_balance': 0,
            'investment_balance': 0,
            'military_percentage': 0,
            'investment_limit': 5,
            'purchase_limit': 3,
            'purchases': [],
            'investments': {},  # Corrigido para ser um dicionário
            'stock': {},
            'idh': 0.500,
            'last_idh_change': 0,
            'soldiers': 100_000,
            'last_recruit': 0,
            'tax_percentage': 0.00,
            'last_tax_change': None
        }
        save_data()

# Start the background task
@bot.event
async def on_ready():
    check_tax_effects.start()
    print(f'Logged in as {bot.user.name}')


# Calculate percentage based on GDP
def calculate_percentage(gdp_value):
    if gdp_value < 500_000_000_000:
        return 0.20
    elif gdp_value < 1_000_000_000_000:
        return 0.10
    else:
        return 0.05

# Set limits based on country size
def set_limits(gdp):
    if gdp < 500_000_000_000:
        return 5, 5  # Small country
    elif gdp < 1_000_000_000_000:
        return 4, 4  # Medium country
    else:
        return 3, 3  # Large country


# Função para converter um valor de string para float, tratando vírgulas e notação científica
def parse_float(value_str):
    try:
        return float(value_str.replace(',', '').replace('e', 'E'))
    except ValueError:
        return None
    
# Comando para registrar o usuário
@bot.command()
@commands.has_role('ADMIN')
async def registro(ctx, user: discord.User, country: str, gdp: str):
    user_id = str(user.id)
    if user_id in data and data[user_id].get('country'):
        await ctx.send(f"O usuário {user.mention} já está registrado.")
        return

    try:
        gdp_value = int(gdp.replace(",", ""))
    except ValueError:
        await ctx.send(f"O valor do PIB '{gdp}' é inválido. Por favor, insira um valor numérico válido.")
        return

    register_user(user)
    user_data = get_user_data(user)
    user_data['country'] = country
    user_data['gdp'] = gdp_value
    user_data['military_percentage'] = calculate_percentage(gdp_value)
    user_data['military_balance'] = int(gdp_value * user_data['military_percentage'])
    user_data['investment_balance'] = int(gdp_value * (1 - user_data['military_percentage']))
    user_data['investment_limit'], user_data['purchase_limit'] = set_limits(gdp_value)
    user_data['soldiers'] = 100_000  # Inicializa com 100 mil soldados

    save_data()
    await ctx.send(f"Usuário {user.mention} registrado com sucesso!")

    # Tipos de investimento
INVESTMENT_TYPES = {
    'EDUC': 'Educação',
    'SUS': 'Saúde',
    'SEGP': 'Segurança Pública',
    'INFRA': 'Infraestrutura Pública',
    'ESPA': 'Investimento Espacial',
    'INDURCIO': 'Indústria e Comércio',
    'TECNO': 'Tecnologia',
    'CIEN': 'Ciência',
    'ESPOR': 'Esportes',
    'CULRA': 'Cultura',
}

# Potencial de retorno para cada tipo de investimento
POTENTIAL_RETURN = {
    'EDUC': 0.10,
    'SUS': 0.10,
    'INFRA': 0.10,
    'INDURCIO': 0.10,
    'TECNO': 0.10,
    'CIEN': 0.10,
    'SEGP': 0.05,
    'ESPA': 0.05,
    'ESPOR': 0.05,
    'CULRA': 0.05,
}

#comando para remover um usuario
@bot.command()
@commands.has_role('ADMIN')
async def remover(ctx, user: discord.User):
    user_id = str(user.id)
    if user_id not in data:
        await ctx.send(f"Usuário {user.mention} não encontrado.")
        return

    del data[user_id]
    save_data()
    await ctx.send(f"Usuário {user.mention} removido com sucesso.")


# Command to show user's balance
@bot.command()
async def saldo(ctx):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return
    await ctx.send(f"Saldo Militar: ${user_data['military_balance']:,}\nSaldo de Investimento: ${user_data['investment_balance']:,}")

# Comando para investir
@bot.command()
async def investir(ctx, tipo: str, valor_str: str):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return

    tipo = tipo.upper()
    if tipo not in INVESTMENT_TYPES:
        await ctx.send(f"{user.mention}, tipo de investimento inválido.")
        return

    valor = parse_float(valor_str)
    if valor is None:
        await ctx.send(f"{user.mention}, valor de investimento inválido.")
        return

    if valor > user_data['investment_balance']:
        await ctx.send(f"{user.mention}, você não possui saldo de investimento suficiente.")
        return

    if tipo not in user_data['investments']:
        user_data['investments'][tipo] = 0

    user_data['investment_balance'] -= valor
    user_data['investments'][tipo] += valor

    save_data()

    # Formatação do valor para exibir com separador de milhar e sem casas decimais
    valor_formatado = f"R${valor:,.0f}"

    await ctx.send(f"Investimento de {valor_formatado} realizado com sucesso em {INVESTMENT_TYPES[tipo]}!")

@bot.command()
@commands.has_role('ADMIN')
async def resetar_investimentos(ctx, user: discord.User):
    user_id = str(user.id)
    if user_id not in data:
        await ctx.send(f"Usuário {user.mention} não encontrado.")
        return

    # Resetar todos os investimentos do usuário
    user_data = get_user_data(user)
    user_data['investments'] = {}
    save_data()

    await ctx.send(f"Investimentos de {user.mention} resetados com sucesso.")

# Comando para ver os investimentos de um usuário
@bot.command()
async def investimentos(ctx, user: discord.User = None):
    if user is None:
        user = ctx.author

    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return

    total_investido = sum(user_data['investments'].values())
    potencial_retorno = sum(user_data['investments'][tipo] * POTENTIAL_RETURN[tipo] for tipo in user_data['investments'])

    investments_message = "\n".join([
        f"{INVESTMENT_TYPES.get(tipo, tipo)}: R${valor:,}"
        for tipo, valor in user_data['investments'].items()
    ])

    await ctx.send(
        f"**País:** {user_data['country']}\n"
        f"**Total Investido:** R${total_investido:,}\n"
        f"{investments_message}\n"
        f"**Potencial Retorno Atual:** R${potencial_retorno:,}"
    )

# Comando para editar o investimento de um usuário (apenas para administradores)
@bot.command()
@commands.has_role('ADMIN')
async def editar_investimento(ctx, user: discord.User, tipo: str, valor: int):
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention} não está cadastrado.")
        return

    tipo = tipo.upper()
    if tipo not in INVESTMENT_TYPES:
        await ctx.send(f"{user.mention}, tipo de investimento inválido.")
        return

    user_data['investments'][tipo] = valor
    save_data()
    await ctx.send(f"Investimento de {user.mention} em {INVESTMENT_TYPES[tipo]} atualizado para R${valor:,}.")

# Comando para limpar os investimentos de todos os usuários ou de um usuário específico
@bot.command()
@commands.has_role('ADMIN')
async def limpar_investimentos(ctx, alvo: str):
    if alvo.lower() == 'todos':
        for user_id in data:
            data[user_id]['investments'] = {}
        save_data()
        await ctx.send("Todos os investimentos foram limpos.")
    else:
        user = await commands.UserConverter().convert(ctx, alvo)
        user_data = get_user_data(user)
        if not user_data:
            await ctx.send(f"{user.mention} não está cadastrado.")
            return

        user_data['investments'] = {}
        save_data()
        await ctx.send(f"Todos os investimentos de {user.mention} foram limpos.")

# Command to purchase vehicles
@bot.command()
async def comprar(ctx, vehicle: str, quantity: int):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return

    now = datetime.now()
    user_data['purchases'] = [pur for pur in user_data['purchases'] if (now - datetime.fromisoformat(pur)).days < 1]
    if len(user_data['purchases']) >= user_data['purchase_limit']:
        await ctx.send(f"{user.mention} já realizou todas as compras possíveis hoje. Tente novamente amanhã.")
        return

    vehicles = {
        'TN': {'time': 1, 'cost': 3_000_000},
        'BD': {'time': 0, 'cost': 2_500_000},
        'AT': {'time': 0, 'cost': 3_500_000},
        'AC': {'time': 0, 'cost': 5_000_000},
        'HC': {'time': 0, 'cost': 6_000_000},
        'DR': {'time': 0, 'cost': 7_000_000},
        'AV': {'time': 0, 'cost': 15_000_000},
        'BM': {'time': 0, 'cost': 25_000_000},
        'RC': {'time': 0, 'cost': 30_000_000},
        'CR': {'time': 0, 'cost': 20_000_000},
        'RN': {'time': 0, 'cost': 5_000_000},
        'LN': {'time': 0, 'cost': 150_000_000},
        'SB': {'time': 0, 'cost': 30_000_000},
        'PA': {'time': 0, 'cost': 40_000_000},
        'PH': {'time': 0, 'cost': 30_000_000},
        'MS': {'time': 0, 'cost': 60_000_000},
        'MH': {'time': 0, 'cost': 80_000_000},
        'MC': {'time': 0, 'cost': 200_000_000},
        'MB': {'time': 0, 'cost': 500_000_000},
    }

    if vehicle not in vehicles:
        await ctx.send(f"{user.mention} veículo inválido.")
        return

    total_cost = vehicles[vehicle]['cost'] * quantity
    if total_cost > user_data['military_balance']:
        await ctx.send(f"{user.mention} não possui saldo militar suficiente.")
        return

    user_data['military_balance'] -= total_cost
    user_data['purchases'].append(now.isoformat())
    delivery_time = vehicles[vehicle]['time'] * quantity
    delivery_time = now + timedelta(hours=delivery_time)

    if 'pending_purchases' not in user_data:
        user_data['pending_purchases'] = []

    user_data['pending_purchases'].append({
        'vehicle': vehicle,
        'quantity': quantity,
        'total_cost': total_cost,
        'delivery_time': delivery_time.isoformat()
    })

    async def add_to_stock():
        await asyncio.sleep(vehicles[vehicle]['time'] * quantity * 3600)
        user_data['stock'][vehicle] = user_data['stock'].get(vehicle, 0) + quantity
        save_data()
        await ctx.send(f"{quantity} unidades de {vehicle} foram entregues a {user.mention}.")

    asyncio.create_task(add_to_stock())
    save_data()
    await ctx.send(f"Compra de {quantity} unidades de {vehicle} realizada com sucesso! Serão entregues em {delivery_time.strftime('%Y-%m-%d %H:%M:%S')}.")

# Map of vehicle codes to full names
VEHICLE_NAMES = {
    'TN': 'Tanque',
    'BD': 'Blindado',
    'AT': 'Artilharia',
    'AC': 'Aeronave de Combate',
    'HC': 'Helicóptero de Combate',
    'DR': 'Drone',
    'AV': 'Avião Cargueiro',
    'BM': 'Bombardeiro',
    'RC': 'Reconhecedor',
    'CR': 'Cruzadores',
    'RN': 'Reconhecedor',
    'LN': 'Lancha',
    'SB': 'Submarino',
    'PA': 'Porta-aviões',
    'PH': 'Porta-helicópteros',
    'MS': 'Mísseis',
    'MH': 'Mísseis Hipersônicos',
    'MC': 'Mísseis de Cruzeiro',
    'MB': 'Mísseis Balísticos',
}

# Command to show stock
@bot.command()
async def estoque(ctx):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return

    if user_data['stock']:
        stock_message = "\n".join([
            f"**{VEHICLE_NAMES.get(vehicle, vehicle)} ({vehicle})**: {quantity} {'unidade' if quantity == 1 else 'unidades'}"
            for vehicle, quantity in user_data['stock'].items()
        ])
        await ctx.send(f"**Estoque de {user.mention}:**\n{stock_message}")
    else:
        await ctx.send(f"{user.mention} não possui veículos em estoque.")

@bot.command()
async def cancelar_compras(ctx):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return

    total_refund = 0
    now = datetime.now()

    # Calcula o reembolso total e remove compras pendentes
    for purchase in user_data['pending_purchases']:
        if now < datetime.fromisoformat(purchase['delivery_time']):
            total_refund += purchase['total_cost']

    # Atualiza o saldo militar e limpa as compras pendentes
    user_data['military_balance'] += total_refund
    user_data['pending_purchases'] = [p for p in user_data['pending_purchases'] if now >= datetime.fromisoformat(p['delivery_time'])]
    save_data()

    # Mensagem de confirmação
    if total_refund > 0:
        await ctx.send(f"{user.mention}, todas as compras pendentes foram canceladas e ${total_refund:,} foram reembolsados ao seu saldo militar.")
    else:
        await ctx.send(f"{user.mention}, não há compras pendentes para cancelar.")

     # Tratamento da porcentagem
    try:
        percentage = float(percentage.strip('%'))  # Remove o % se presente e converte para float
    except ValueError:
        await ctx.send("Por favor, forneça um número válido para a porcentagem de impostos.")
        return
    
     # Validação do intervalo da porcentagem de impostos
    if percentage > 20:
        await ctx.send(f"Impostos ajustados para {percentage}%. Isso é muito alto! A população está revoltada e a economia está estagnada. Diminua os impostos!")
    elif 10 <= percentage <= 20:
        await ctx.send(f"Impostos ajustados para {percentage}%. A população está neutra e o PIB não foi influenciado.")
    elif percentage < 10:
        await ctx.send(f"Impostos ajustados para {percentage}%. A população está feliz com a nova medida e seu PIB vai aumentar a cada 24 horas.")
    
    user_data['tax_percentage'] = percentage
    user_data['last_tax_change'] = datetime.now().isoformat()
    save_data()

@bot.command()
async def recrutar(ctx):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return
    now = datetime.now()
    if user_data['last_recruit']:
        last_recruit_time = datetime.fromisoformat(user_data['last_recruit'])
        if (now - last_recruit_time).days < 1:
            await ctx.send(f"{user.mention}, você só pode recrutar soldados uma vez a cada 24 horas.")
            return

    recruit_options = [300, 500, 1000, 1200]
    new_soldiers = random.choice(recruit_options)
    user_data['soldiers'] += new_soldiers
    user_data['last_recruit'] = now.isoformat()
    save_data()
    await ctx.send(f"{user.mention}, você recrutou {new_soldiers} soldados. Total de soldados: {user_data['soldiers']:,}")

@bot.command()
async def dispensar(ctx, quantidade: int):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return

    if quantidade > user_data['soldiers']:
        await ctx.send(f"{user.mention}, você não pode dispensar mais soldados do que possui.")
        return

    user_data['soldiers'] -= quantidade
    save_data()
    await ctx.send(f"{user.mention}, você dispensou {quantidade} soldados. Total de soldados restantes: {user_data['soldiers']:,}")

        
        # Check if 'soldiers' key exists
    if 'soldiers' in user_data:
            soldiers = user_data['soldiers']
    else:
        soldiers = 0


@bot.command()
@commands.has_role('ADMIN')
async def modificar_soldados(ctx, user: discord.User, quantidade: int):
    user_data = get_user_data(user)
    user_data['soldiers'] = quantidade
    save_data()
    await ctx.send(f"A quantidade de soldados de {user.mention} foi ajustada para {quantidade:,}.")

# Função para formatar números com vírgulas
def format_number(number):
    return "{:,}".format(number)

# Comando para pesquisar dados do usuário
@bot.command()
async def pesquisar(ctx, to_user: discord.User):
    user_data = get_user_data(to_user)  # Obtém os dados do usuário mencionado
    if not user_data:
        await ctx.send(f"Usuario não cadastrado.")
        return
    
    country = user_data['country']
    gdp = format_number(user_data['gdp'])
    military_balance = format_number(user_data['military_balance'])
    investment_balance = format_number(user_data['investment_balance'])
    military_percentage = user_data['military_percentage'] * 100  # Multiplica por 100 para exibir como porcentagem
    investment_limit = format_number(user_data['investment_limit'])
    purchase_limit = format_number(user_data['purchase_limit'])
    idh = user_data['idh']
    soldiers = format_number(user_data['soldiers'])
    tax_percentage = user_data['tax_percentage']
    
    embed = discord.Embed(title=f"Informações do país de {to_user.display_name}")
    embed.add_field(name="País", value=country, inline=False)
    embed.add_field(name="PIB", value=f"${gdp}", inline=False)
    embed.add_field(name="Balanço Militar", value=f"${military_balance}", inline=False)
    embed.add_field(name="Balanço de Investimento", value=f"${investment_balance}", inline=False)
    embed.add_field(name="Porcentagem Militar", value=f"{military_percentage:.2f}%", inline=False)
    embed.add_field(name="Limite de Investimento", value=f"{investment_limit}", inline=False)
    embed.add_field(name="Limite de Compras", value=f"{purchase_limit}", inline=False)
    embed.add_field(name="IDH", value=f"{idh}", inline=False)
    embed.add_field(name="Soldados", value=f"{soldiers}", inline=False)
    embed.add_field(name="Porcentagem de Impostos", value=f"{tax_percentage:.2f}%", inline=False)

    await ctx.send(embed=embed)


# Command to transfer vehicles
@bot.command()
async def transferir(ctx, to_user: discord.User, vehicle: str, quantity: int):
    from_user = ctx.author
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return
    

    from_user_data = get_user_data(from_user)
    to_user_data = get_user_data(to_user)

    if vehicle not in from_user_data['stock'] or from_user_data['stock'][vehicle] < quantity:
        await ctx.send(f"{from_user.mention} não possui veículos suficientes de {vehicle} para transferir.")
        return

    from_user_data['stock'][vehicle] -= quantity
    if vehicle not in to_user_data['stock']:
        to_user_data['stock'][vehicle] = 0
    to_user_data['stock'][vehicle] += quantity

    save_data()
    await ctx.send(f"{quantity} unidades de {vehicle} foram transferidas de {from_user.mention} para {to_user.mention} com sucesso.")

# Command to pay another user
@bot.command()
async def pagar(ctx, to_user: discord.User, amount: int, tipo: str):
    from_user = ctx.author
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{from_user.mention}, você não está cadastrado.")
        return
    
    from_user_data = get_user_data(from_user)
    to_user_data = get_user_data(to_user)

    if tipo == 'militar':
        if amount > from_user_data['military_balance']:
            await ctx.send(f"{from_user.mention} não possui saldo militar suficiente.")
            return
        from_user_data['military_balance'] -= amount
        to_user_data['military_balance'] += amount
    elif tipo == 'investimento':
        if amount > from_user_data['investment_balance']:
            await ctx.send(f"{from_user.mention} não possui saldo de investimento suficiente.")
            return
        from_user_data['investment_balance'] -= amount
        to_user_data['investment_balance'] += amount
    else:
        await ctx.send(f"Tipo de saldo inválido. Use 'militar' ou 'investimento'.")
        return

    save_data()
    await ctx.send(f"Transferência de ${amount:,} do saldo {tipo} de {from_user.mention} para {to_user.mention} realizada com sucesso.")

# Command to add money to a user
@bot.command()
@commands.has_role('ADMIN')
async def adicionar(ctx, user: discord.User, tipo: str, amount: int):
    user_data = get_user_data(user)
    if tipo == 'militar':
        user_data['military_balance'] += amount
    elif tipo == 'investimento':
        user_data['investment_balance'] += amount
    elif tipo == 'pib':
        user_data['gdp'] += amount
        user_data['military_percentage'] = calculate_percentage(user_data['gdp'])
        user_data['military_balance'] = int(user_data['gdp'] * user_data['military_percentage'])
        user_data['investment_balance'] = int(user_data['gdp'] * (1 - user_data['military_percentage']))
        user_data['investment_limit'], user_data['purchase_limit'] = set_limits(user_data['gdp'])
    else:
        await ctx.send(f"Tipo de saldo inválido. Use 'militar', 'investimento' ou 'pib'.")
        return

    save_data()
    await ctx.send(f"{amount} adicionados ao saldo {tipo} de {user.mention} com sucesso.")

# Command to remove money from a user
@bot.command()
@commands.has_role('ADMIN')
async def remover_valor(ctx, user: discord.User, tipo: str, amount: int):
    user_data = get_user_data(user)
    if tipo == 'militar':
        user_data['military_balance'] = max(0, user_data['military_balance'] - amount)
    elif tipo == 'investimento':
        user_data['investment_balance'] = max(0, user_data['investment_balance'] - amount)
    elif tipo == 'pib':
        user_data['gdp'] = max(0, user_data['gdp'] - amount)
        user_data['military_percentage'] = calculate_percentage(user_data['gdp'])
        user_data['military_balance'] = int(user_data['gdp'] * user_data['military_percentage'])
        user_data['investment_balance'] = int(user_data['gdp'] * (1 - user_data['military_percentage']))
        user_data['investment_limit'], user_data['purchase_limit'] = set_limits(user_data['gdp'])
    else:
        await ctx.send(f"Tipo de saldo inválido. Use 'militar', 'investimento' ou 'pib'.")
        return

    save_data()
    await ctx.send(f"{amount} removidos do saldo {tipo} de {user.mention} com sucesso.")

# Command to increase IDH
@bot.command()
async def IDH(ctx):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return
    

    user_data = get_user_data(user)
    now = datetime.now()

    if user_data['last_idh_change']:
        last_change_time = datetime.fromisoformat(user_data['last_idh_change'])
        if (now - last_change_time).days < 1:
            await ctx.send(f"{user.mention}, você só pode alterar o IDH uma vez a cada 24 horas.")
            return

    if user_data['idh'] >= 1:
        await ctx.send(f"{user.mention}, você já está com o seu IDH máximo.")
        return

    increase_values = [0.003, 0.005, 0.006, 0.007]
    increase = random.choice(increase_values)

    if user_data['idh'] + increase > 1:
        increase = 1 - user_data['idh']

    user_data['idh'] += increase
    user_data['last_idh_change'] = now.isoformat()
    save_data()
    await ctx.send(f"{user.mention}, seu IDH foi aumentado em {increase:.3f}. Novo IDH: {user_data['idh']:.3f}")

# Command to decrease IDH
@bot.command()
async def IDHmenos(ctx):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return

    user_data = get_user_data(user)
    now = datetime.now()

    if user_data['last_idh_change']:
        last_change_time = datetime.fromisoformat(user_data['last_idh_change'])
        if (now - last_change_time).days < 1:
            await ctx.send(f"{user.mention}, você só pode alterar o IDH uma vez a cada 24 horas.")
            return

    if user_data['idh'] <= 0.500:
        await ctx.send(f"{user.mention}, você já está com o seu IDH mínimo.")
        return

    decrease_values = [0.003, 0.004, 0.005, 0.006, 0.008]
    decrease = random.choice(decrease_values)

    if user_data['idh'] - decrease < 0.500:
        decrease = user_data['idh'] - 0.500

    user_data['idh'] -= decrease
    user_data['last_idh_change'] = now.isoformat()
    save_data()
    await ctx.send(f"{user.mention}, seu IDH foi diminuído em {decrease:.3f}. Novo IDH: {user_data['idh']:.3f}")

@bot.command()
@commands.has_role('ADMIN')
async def ajustar_idh(ctx, user: discord.User, new_idh: float):
    user_data = get_user_data(user)

    # Verifica se o novo IDH está dentro dos limites permitidos
    if new_idh < 0.5 or new_idh > 1.0:
        await ctx.send("O novo IDH deve estar entre 0.5 e 1.0.")
        return

    user_data['idh'] = new_idh
    save_data()

    await ctx.send(f"IDH de {user.mention} ajustado para {new_idh:.3f}.")

# Carregar dados do arquivo data.json
def load_data():
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

# Ordenar usuários pelo PIB em ordem decrescente
def sort_users_by_gdp(data):
    sorted_users = sorted(data.items(), key=lambda item: item[1]['gdp'], reverse=True)
    return sorted_users

# Configurar páginas do ranking
def setup_pages(users, items_per_page=10):
    pages = []
    for i in range(0, len(users), items_per_page):
        pages.append(users[i:i + items_per_page])
    return pages

# Salvar páginas do ranking no arquivo ranking.json
def save_ranking(pages):
    with open('ranking.json', 'w') as f:
        json.dump(pages, f, indent=4)

# Comando para exibir o ranking
@bot.command()
async def ranking(ctx, page_num: int = 1):
    data = load_data()
    
    # Verificar se há dados para processar
    if not data:
        await ctx.send("Não há dados disponíveis para gerar o ranking.")
        return
    
    sorted_users = sort_users_by_gdp(data)
    ranking_pages = setup_pages(sorted_users)

    # Verificar se a página solicitada está dentro do limite
    if page_num < 1 or page_num > len(ranking_pages):
        await ctx.send(f"Página inválida. O ranking tem {len(ranking_pages)} páginas.")
        return

    current_page = ranking_pages[page_num - 1]
    embed = discord.Embed(title=f"Ranking - Página {page_num}", color=discord.Color.blurple())

    # Adicionar os usuários da página ao embed
    for rank, (user_id, user_data) in enumerate(current_page, start=page_num * 10 - 9):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(name=f"{rank}. {user.name}", value=f"PIB: ${user_data['gdp']:,}", inline=False)

    await ctx.send(embed=embed)

    
# Command to adjust taxes
@bot.command()
async def impostos(ctx, percentage: str):
    user = ctx.author
    user_data = get_user_data(user)
    if not user_data:
        await ctx.send(f"{user.mention}, você não está cadastrado.")
        return
    
    user_data = get_user_data(user)

    try:
        percentage = float(percentage.strip('%'))  # Remove o % se presente e converte para float
    except ValueError:
        await ctx.send("Por favor, forneça um número válido para a porcentagem de impostos.")
        return
    
    # Validação do intervalo da porcentagem de impostos
    if percentage > 20:
        await ctx.send(f"Impostos ajustados para {percentage}%. Isso é muito alto! A população está revoltada e a economia está estagnada. Diminua os impostos!")
    elif 10 <= percentage <= 20:
        await ctx.send(f"Impostos ajustados para {percentage}%. A população vai se manter estável, porém o PIB não vai aumentar ou diminuir.")
    elif percentage < 10:
        await ctx.send(f"Impostos ajustados para {percentage}%. A população está feliz com a nova medida e seu PIB vai aumentar a cada 24 horas.")
    
    user_data['tax_percentage'] = percentage
    user_data['last_tax_change'] = datetime.now().isoformat()
    save_data()


# Background task to check tax effects
@tasks.loop(hours=1)
async def check_tax_effects():
    now = datetime.now()
    print(f"Running check_tax_effects at {now}")  # Debug statement
    
    for user_id, user_data in data.items():
        if user_data['last_tax_change']:
            last_change = datetime.fromisoformat(user_data['last_tax_change'])
        else:
            last_change = datetime.min
        
        tax_duration = now - last_change
        print(f"Checking user {user_id}: tax_percentage={user_data['tax_percentage']}, tax_duration={tax_duration}")  # Debug statement
        
        channel = bot.get_channel(1250680873729130496)

        if not channel:
            print("Channel 'população' not found")  # Debug statement
            continue

        if tax_duration >= timedelta(hours=24):  # Adjust based on the original 24 hours
            gdp_change = 0
            if user_data['tax_percentage'] > 20:
                gdp_change = -0.02  # Decrease GDP by 2%
                await channel.send(f"<@{user_id}> A população está revoltada com os impostos altos e o PIB diminuiu 2%.")
            elif 10 <= user_data['tax_percentage'] <= 20:
                await channel.send(f"<@{user_id}> A população está neutra e o PIB não foi influenciado.")
            elif user_data['tax_percentage'] < 10:
                gdp_change = 0.01  # Increase GDP by 1%
                await channel.send(f"<@{user_id}> A população está feliz com os impostos baixos e o PIB aumentou 1%.")

            if gdp_change != 0:
                user_data['gdp'] *= (1 + gdp_change)
                user_data['military_balance'] *= (1 + gdp_change)
                user_data['investment_balance'] *= (1 + gdp_change)

            user_data['last_tax_change'] = now.isoformat()
    
    save_data()


    # Start tasks when bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    check_tax_effects.start()

bot.run(TOKEN)