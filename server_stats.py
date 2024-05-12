#!/usr/bin/env python3
import psutil
import requests
import json
import re
from datetime import datetime, timedelta

def get_cpu_usage():
    cpu_usage = psutil.cpu_percent(interval=5) # Obtenemos el uso de cpu de los ultimos 5 segundos

    return cpu_usage

# Obtenemos el consumo de RAM en uso y el total
def get_ram_usage():
    ram = psutil.virtual_memory()
    used_ram_gb = round(ram.used / (1024 * 1024 * 1024), 2) # Pasamos de bytes, a megas y a gigas, con 2 decimales
    total_ram_gb = round(ram.total / (1024 * 1024 * 1024), 2) # " "

    return used_ram_gb, total_ram_gb

# En función de los umbrales, definimos el emoji que corresponde a cada valor, y el color del embed
def get_embed_color_and_emoji(cpu_usage, used_ram_gb, total_ram_gb):
    if cpu_usage > 90 or used_ram_gb / total_ram_gb > 0.90:
        color = 16711680 # Código de color Rojo en RGB
        cpu_emoji = ":red_circle:"
        ram_emoji = ":red_circle:"
    elif cpu_usage > 80 or used_ram_gb / total_ram_gb > 0.80:
        color = 16776960 # Código de color Amarillo en RGB
        cpu_emoji = ":yellow_circle:"
        ram_emoji = ":yellow_circle:"
    else: # Definimos un else, para no meter el return en cada condición
        color = 65280  # Código de color Verde en RGB
        cpu_emoji = ":green_circle:"
        ram_emoji = ":green_circle:"

    return color, cpu_emoji, ram_emoji

# Todo: Documentar
def daily_report_12h():
    twelve_ago = datetime.now() - timedelta(hours=12)

    total_cpu = 0
    total_ram = 0
    count = 0

    with open('/logs/server_stats.txt', 'r') as logs_file:
        for line in logs_file:
            stats = line.split(' - ')
            stats_date = datetime.strptime(stats[0], '%d/%m/%Y %H:%M:%S')

            if stats_date >= twelve_ago:
                # Obtenemos los valores que nos interesan de una linea como la siguiente:
                # 12/05/2024 18:30:06 - CPU: 13.9% - RAM: 12.48GB / 31.31GB
                cpu_value = float(re.search(r'CPU: (\d+\.\d+)%', line).group(1))
                ram_value = float(re.search(r'RAM: (\d+\.\d+)GB', line).group(1))

                total_cpu += cpu_value
                total_ram += ram_value
                count += 1

        logs_file.close()

    if count > 0:
        avg_cpu = round(float(total_cpu / count), 2)
        avg_ram = round(float(total_ram / count), 2)

        return avg_cpu, avg_ram
    
    return None, None

def send_alert(cpu_usage, ram_usage, total_ram_gb):
    # Esto es la ""contraseña"" / token del bot DripperES - Metrics. Solo se activa al mandar peticiones mas abajo
    token = 'token de la aplicación - discord developer portal'

    # Url de la API que corresponde al servidor de Zero CLub y los mensajes que se envian en él
    url = 'https://discord.com/api/v9/channels/1211255060739260417/messages'

    # Necesitamos autenticarnos para poder realizar la petición
    headers = {
        'Authorization': f'Bot {token}',
        'Content-Type': 'application/json',
    }

    color, cpu_emoji, ram_emoji = get_embed_color_and_emoji(cpu_usage, used_ram_gb, total_ram_gb)

    embed = {
        "embeds": [
            {
                "title": "Dedicado [ip del dedicado]",
                "description": f"Se requiere la revisión de un técnico",
                "color": color,
                "fields": [
                    { "name": f"{cpu_emoji} CPU: {cpu_usage}%", "value": "" },
                    { "name": f"{ram_emoji} RAM: {used_ram_gb}GB / {total_ram_gb}GB", "value": "" }
                ]
            }
        ]
    }

    # En caso que tanto la cpu como la ram, estén por debajo del 80% registramos un log
    log_file = '/logs/server_stats.txt'
    current_date = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    # Registramos una entrada habitual como log
    with open(log_file, 'a') as f:
        f.write(f"{current_date} - CPU: {cpu_usage}% - RAM: {used_ram_gb}GB / {total_ram_gb}GB\n")
        f.close()

    time_now = datetime.now()
 
    # Si superan los umbrales, mandamos mensaje a Discord
    if cpu_usage > 80 or used_ram_gb / total_ram_gb > 0.80:
        content = "<@&1238919771085475920>"
        embed["content"] = content
        response = requests.post(url, headers=headers, data=json.dumps(embed))

        if response.status_code == 200:
            requests.post(url, headers=headers, data={"content": "<@&1238919771085475920>"})
        else:
            print("Error al enviar el mensaje de alerta:", response.text)

    # Genera un renvio de datos cada 12h uno a las 00 y otro a las 12h
    if (time_now.hour == 0 and time_now.minute == 0) or (time_now.hour == 12 and time_now.minute == 0):
        report_cpu, report_ram = daily_report_12h()
        report_ram_percent = round((report_ram / total_ram_gb) * 100, 2) # Vlores inteligibles

        embed = {
            "embeds": [
                {
                    "title": "Dedicado [ip del dedicado] - Reporte",
                    "description": f"Esta es una aproximación del conusmo de las últimas 12 horas",
                    "color": 16737235,
                    "fields": [
                        { "name": f"{cpu_emoji} Avg CPU: {report_cpu}%", "value": "" },
                        { "name": f"{ram_emoji} Avg RAM: {report_ram}GB [{report_ram_percent}%]", "value": "" }
                    ]
                }
            ]
        }

        response = requests.post(url, headers=headers, data=json.dumps(embed))

        if response.status_code == 200:
            requests.post(url, headers=headers, data={"content": "<@&1238919771085475920>"})
        else:
            print("Error al enviar el mensaje de alerta:", response.text)

# Este es el punto de entrada del script
if __name__ == "__main__":
    cpu_usage = get_cpu_usage()
    used_ram_gb, total_ram_gb = get_ram_usage()
    send_alert(cpu_usage, used_ram_gb, total_ram_gb)
    