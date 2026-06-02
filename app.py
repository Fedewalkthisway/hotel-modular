from flask import Flask, render_template_string, request, redirect, url_for
import requests
import datetime
import random
import os

app = Flask(__name__)

# --- CONFIGURACIÓN DE WHATSAPP ---
ULTRAMSG_INSTANCE = os.environ.get("ULTRAMSG_INSTANCE")
ULTRAMSG_TOKEN = os.environ.get("ULTRAMSG_TOKEN")
ULTRAMSG_API_URL = f"https://api.ultramsg.com/instance{ULTRAMSG_INSTANCE}/messages/chat"

# --- CREDENCIALES DE SUPABASE ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_HEADERS = {
    "apikey": os.environ.get("SUPABASE_KEY"),
    "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY')}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

TOTAL_MODULOS = 16

def enviar_whatsapp(telefono, mensaje):
    num_limpio = "".join(filter(str.isdigit, str(telefono)))
    if not num_limpio.startswith("54"):
        num_limpio = "54" + num_limpio
        
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": num_limpio,
        "body": mensaje
    }
    try:
        response = requests.post(ULTRAMSG_API_URL, data=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Error al enviar WhatsApp: {e}")
        return False

def verificar_disponibilidad(modulo, desde_str, hasta_str, reserva_id_ignorar=None):
    nuevas_fechas = (
        datetime.datetime.strptime(desde_str, "%Y-%m-%d").date(),
        datetime.datetime.strptime(hasta_str, "%Y-%m-%d").date()
    )
    url = f"{SUPABASE_URL}?modulo=eq.{modulo}&estado=in.(\"Pendiente de Pago\",\"Ocupado\")"
    response = requests.get(url, headers=SUPABASE_HEADERS)
    reservas_existentes = response.json() if response.status_code == 200 else []
    
    for res in reservas_existentes:
        if reserva_id_ignorar is not None and int(res["id"]) == int(res_id_ignorar):
            continue
        res_desde = datetime.datetime.strptime(res["desde"], "%Y-%m-%d").date()
        res_hasta = datetime.datetime.strptime(res["hasta"], "%Y-%m-%d").date()
        if nuevas_fechas[0] < res_hasta and nuevas_fechas[1] > res_desde:
            return False 
    return True

# --- DISEÑOS VISUALES ---

HTML_FORMULARIO = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reserva - Hotel Modular</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f1f5f9; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); width: 100%; max-width: 450px; }
        h2 { color: #0f172a; margin: 0 0 10px 0; text-align: center; font-size: 24px; }
        p { color: #64748b; text-align: center; margin-bottom: 25px; font-size: 14px; }
        .form-group { margin-bottom: 18px; }
        .row { display: flex; gap: 15px; }
        .row .form-group { flex: 1; }
        label { display: block; margin-bottom: 6px; color: #334155; font-weight: 600; font-size: 14px; }
        input, select { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; font-size: 15px; }
        button { width: 100%; padding: 14px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Reserva tu Estadía</h2>
        <p>Introducí tus fechas. El sistema validará la disponibilidad real en la nube.</p>
        <form action="/reservar" method="POST">
            <div class="form-group">
                <label>Nombre Completo</label>
                <input type="text" name="nombre" placeholder="Marta Gómez" required>
            </div>
            <div class="form-group">
                <label>DNI / Pasaporte</label>
                <input type="text" name="dni" placeholder="35123456" required>
            </div>
            <div class="form-group">
                <label>Celular (Con código de área ej: 3537654321)</label>
                <input type="text" name="telefono" placeholder="3537654321" required>
            </div>
            <div class="row">
                <div class="form-group">
                    <label>Fecha Entrada</label>
                    <input type="date" name="desde" required>
                </div>
                <div class="form-group">
                    <label>Fecha Salida</label>
                    <input type="date" name="hasta" required>
                </div>
            </div>
            <div class="form-group">
                <label>Cantidad de Personas</label>
                <select name="personas">
                    <option value="1">1 Persona</option>
                    <option value="2">2 Personas</option>
                </select>
            </div>
            <button type="submit">Ir a Pagar 💳</button>
        </form>
    </div>
</body>
</html>
"""

HTML_PAGO = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pagar Reserva</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f1f5f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center; max-width: 400px; width:100%; }
        .btn-simular { display: inline-block; margin-top: 25px; padding: 14px; background: #10b981; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; width: 90%; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Lugar Asegurado 🕒</h2>
        <p>Bloqueamos el espacio temporalmente para tus fechas.</p>
        <p>Monto: $15.000 ARS</p>
        <a href="/webhook_simulado?reserva_id={{ reserva_id }}" class="btn-simular">🟢 [ Simular Pago Exitoso ]</a>
    </div>
</body>
</html>
"""

HTML_EXITO_CLIENTE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pago Exitoso</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #ecfdf5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center; max-width: 400px; width:100%; border-top: 5px solid #10b981; }
        h2 { color: #065f46; }
        p { color: #047857; font-size: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>¡Pago Confirmado! 🎉</h2>
        <p>Tu estadía ya está reservada de forma definitiva.</p>
        <p>Te enviamos un mensaje de confirmación por <strong>WhatsApp</strong>. ¡Muchas gracias!</p>
    </div>
</body>
</html>
"""

HTML_PANEL = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><title>Panel Agenda - Hotel Modular</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        header { max-width: 1200px; margin: 0 auto 30px auto; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 20px; }
        h1 { margin: 0; font-size: 28px; color: #38bdf8; }
        .contenedor { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 30px; }
        .seccion { background: #1e293b; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
        h2 { color: #e2e8f0; margin-top: 0; font-size: 20px; border-left: 4px solid #38bdf8; padding-left: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #334155; font-size: 14px; }
        th { color: #94a3b8; font-weight: 600; }
        .badge { font-size: 12px; padding: 4px 8px; border-radius: 20px; font-weight: bold; }
        .badge.pendiente { background: rgba(234,179,8,0.2); color: #fde047; }
        .badge.ocupado { background: rgba(239,68,68,0.2); color: #f87171; }
        select { background: #0f172a; color: #f8fafc; border: 1px solid #475569; padding: 6px; border-radius: 6px; font-size: 13px; }
        .error-flash { background: #fee2e2; color: #ef4444; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-weight: bold; }
        .btn-cron { background: #38bdf8; color: #0f172a; padding: 10px 15px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 14px; }
    </style>
</head>
<body>
    <header>
        <h1>Centro de Mandos (Persistente)</h1>
        <div>
            <a href="/cron_checkin" class="btn-cron" style="margin-right: 10px;">🤖 Forzar Robot Check-in (Simulador)</a>
            <a href="/" target="_blank" style="color: #38bdf8; text-decoration:none; font-weight:bold;">+ Abrir Formulario</a>
        </div>
    </header>
    
    <div class="contenedor">
        {% if msg_error %}
            <div class="error-flash">⚠️ {{ msg_error }}</div>
        {% endif %}

        <div class="seccion">
            <h2>Todas las Reservas Guardadas en la Nube</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Huésped</th>
                        <th>DNI</th>
                        <th>Celular</th>
                        <th>Desde</th>
                        <th>Hasta</th>
                        <th>Módulo Físico</th>
                        <th>PIN Acceso</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {% for res in reservas %}
                    <tr>
                        <td>#{{ res.id }}</td>
                        <td><strong>{{ res.huesped }}</strong></td>
                        <td>{{ res.dni }}</td>
                        <td>{{ res.telefono }}</td>
                        <td>{{ res.desde }}</td>
                        <td>{{ res.hasta }}</td>
                        <td>
                            <form action="/reasignar" method="POST" style="margin:0; display:inline;">
                                <input type="hidden" name="reserva_id" value="{{ res.id }}">
                                <select name="nuevo_modulo" onchange="this.form.submit()">
                                    {% for m in range(1, total_modulos + 1) %}
                                        <option value="{{ m }}" {{ 'selected' if res.modulo|int == m }}>Módulo {{ m }}</option>
                                    {% endfor %}
                                </select>
                            </form>
                        </td>
                        <td><code>{{ res.codigo_acceso if res.codigo_acceso else 'No asignado' }}</code></td>
                        <td>
                            <span class="badge {{ 'pendiente' if res.estado == 'Pendiente de Pago' else 'ocupado' }}">
                                {{ res.estado }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# --- RUTAS ---

@app.route('/')
def mostrar_formulario():
    return render_template_string(HTML_FORMULARIO)

@app.route('/reservar', methods=['POST'])
def procesar_reserva():
    nombre = request.form.get('nombre')
    dni = request.form.get('dni')
    telefono = request.form.get('telefono')
    desde = request.form.get('desde')
    hasta = request.form.get('hasta')
    personas = request.form.get('personas')
    
    modulo_libre = None
    for m in range(1, TOTAL_MODULOS + 1):
        if verificar_disponibilidad(m, desde, hasta):
            modulo_libre = m
            break
            
    if not modulo_libre:
        return "Lo sentimos, no hay disponibilidad.", 400
        
    pin_generado = str(random.randint(1000, 9999))
        
    nueva_reserva_data = {
        "modulo": modulo_libre,
        "estado": "Pendiente de Pago",
        "huesped": nombre,
        "dni": dni,
        "telefono": telefono,
        "desde": desde,
        "hasta": hasta,
        "personas": personas,
        "codigo_acceso": pin_generado
    }
    
    response = requests.post(SUPABASE_URL, headers=SUPABASE_HEADERS, json=nueva_reserva_data)
    datos_respuesta = response.json()
    
    if isinstance(datos_respuesta, list) and len(datos_respuesta) > 0:
        reserva_id = datos_respuesta[0]["id"]
    elif isinstance(datos_respuesta, dict) and "id" in datos_respuesta:
        reserva_id = datos_respuesta["id"]
    else:
        return f"Error al guardar en la base de datos: {response.text}", 500
    
    return render_template_string(HTML_PAGO, reserva_id=reserva_id)

@app.route('/webhook_simulado')
def webhook_simulado():
    res_id = int(request.args.get('reserva_id'))
    url_select = f"{SUPABASE_URL}?id=eq.{res_id}"
    
    res_actual = requests.get(url_select, headers=SUPABASE_HEADERS).json()[0]
    requests.patch(url_select, headers=SUPABASE_HEADERS, json={"estado": "Ocupado"})
    
    msg_confirmacion = (
        f"¡Hola {res_actual['huesped']}! Recibimos tu pago correctamente. 👍\n\n"
        f"Tu reserva para ingresar el {res_actual['desde']} está confirmada.\n"
        f"El día de tu llegada, unas horas antes del horario de check-in, te enviaremos por este mismo medio el número de módulo asignado y tu código numérico de acceso temporal. ¡Buen viaje!"
    )
    enviar_whatsapp(res_actual['telefono'], msg_confirmacion)
    
    # CAMBIO CRÍTICO: El cliente va a una pantalla de éxito, nunca más al panel
    return render_template_string(HTML_EXITO_CLIENTE)

@app.route('/cron_checkin')
def cron_checkin():
    hoy_str = datetime.date.today().strftime("%Y-%m-%d")
    url = f"{SUPABASE_URL}?desde=eq.{hoy_str}&estado=eq.Ocupado"
    response = requests.get(url, headers=SUPABASE_HEADERS)
    reservas_de_hoy = response.json() if response.status_code == 200 else []
    
    mensajes_enviados = 0
    for res in reservas_de_hoy:
        msg_acceso = (
            f"¡Hola {res['huesped']}! Hoy es tu día de ingreso en Hotel Modular. 🏨✨\n\n"
            f"Tu espacio está listo:\n"
            f"🚪 Módulo asignado: MÓDULO {res['modulo']}\n"
            f"🔑 Código de acceso: {res['codigo_acceso']}\n\n"
            f"Recordá que el código se activará automáticamente a la hora del check-in. ¡Que disfrutes tu estadía!"
        )
        exito = enviar_whatsapp(res['telefono'], msg_acceso)
        if exito:
            mensajes_enviados += 1
            
    return f"Robot ejecutado. Se enviaron {mensajes_enviados} mensajes de check-in para el día de hoy ({hoy_str}).", 200

@app.route('/reasignar', methods=['POST'])
def reasignar_modulo():
    res_id = int(request.form.get('reserva_id'))
    nuevo_mod = int(request.form.get('nuevo_modulo'))
    
    url_select = f"{SUPABASE_URL}?id=eq.{res_id}"
    response = requests.get(url_select, headers=SUPABASE_HEADERS)
    res_actual = response.json()[0] if response.json() else None
            
    if res_actual:
        if verificar_disponibilidad(nuevo_mod, res_actual["desde"], res_actual["hasta"], reserva_id_ignorar=res_id):
            requests.patch(url_select, headers=SUPABASE_HEADERS, json={"modulo": nuevo_mod})
            return redirect('/panel_control_secreto_hotel')
        else:
            return redirect('/panel_control_secreto_hotel?error=' + f"¡Error! El Módulo {nuevo_mod} ya está ocupado en esas fechas.")
            
    return redirect('/panel_control_secreto_hotel')

# NUEVA RUTA PRIVADA PARA VOS
@app.route('/panel_control_secreto_hotel')
def ver_panel():
    error_msg = request.args.get('error')
    url = f"{SUPABASE_URL}?order=id.asc"
    response = requests.get(url, headers=SUPABASE_HEADERS)
    lista_reservas = response.json() if response.status_code == 200 else []
    return render_template_string(HTML_PANEL, reservas=lista_reservas, total_modulos=TOTAL_MODULOS, msg_error=error_msg)

if __name__ == '__main__':
    app.run(debug=True, port=5000)