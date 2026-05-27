from flask import Flask, render_template_string, request, redirect, url_for
import mercadopago
import datetime

app = Flask(__name__)

sdk = mercadopago.SDK("TEST-4734346917637424-052718-4a94639f7278292cb00bf2729aefb204-142273030")

# --- BASE DE DATOS ESTRUCTURADA ---
# Lista donde guardaremos cada reserva como un "contrato" independiente con ID único
reservas = [
    # Ejemplos cargados para que veas cómo el sistema maneja la superposición de fechas en un mismo módulo
    {
        "id": 1, "modulo": 1, "estado": "Ocupado", "huesped": "Carlos Pereyra", 
        "dni": "20111222", "desde": "2026-06-01", "hasta": "2026-06-05", "personas": "2"
    },
    {
        "id": 2, "modulo": 1, "estado": "Ocupado", "huesped": "Marta Gómez", 
        "dni": "30444555", "desde": "2026-06-10", "hasta": "2026-06-15", "personas": "1"
    }
]

# Total de módulos físicos en Bell Ville
TOTAL_MODULOS = 16

# --- FUNCIÓN CLAVE: DETECTOR DE SUPERPOSICIÓN DE FECHAS ---
def verificar_disponibilidad(modulo, desde_str, hasta_str, reserva_id_ignorar=None):
    """ Devuelve True si el módulo está LIBRE en ese rango de fechas """
    nuevas_fechas = (
        datetime.datetime.strptime(desde_str, "%Y-%m-%d").date(),
        datetime.datetime.strptime(hasta_str, "%Y-%m-%d").date()
    )
    
    for res in reservas:
        # Ignoramos la reserva actual si la estamos editando/reasignando de habitación
        if reserva_id_ignorar and res["id"] == reserva_id_ignorar:
            continue
            
        if res["modulo"] == modulo and res["estado"] in ["Pendiente de Pago", "Ocupado"]:
            res_desde = datetime.datetime.strptime(res["desde"], "%Y-%m-%d").date()
            res_hasta = datetime.datetime.strptime(res["hasta"], "%Y-%m-%d").date()
            
            # Fórmula matemática de cruce de rangos: (InicioA <= FinB) y (FinA >= InicioB)
            if nuevas_fechas[0] < res_hasta and nuevas_fechas[1] > res_desde:
                return False # ¡Hay superposición! Está ocupado esos días
                
    return True # El módulo está limpio en esas fechas

# --- DISEÑO VISUAL ---

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
        <p>Introducí tus fechas. El sistema validará la disponibilidad real en la agenda.</p>
        <form action="/reservar" method="POST">
            <div class="form-group">
                <label>Nombre Completo</label>
                <input type="text" name="nombre" placeholder="Marta Gómez" required>
            </div>
            <div class="form-group">
                <label>DNI / Pasaporte</label>
                <input type="text" name="dni" placeholder="35123456" required>
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
    <meta charset="UTF-8"><title>Pagar Reserva</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f1f5f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center; max-width: 400px; width:100%; }
        .btn-simular { display: inline-block; margin-top: 25px; padding: 14px; background: #10b981; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; width: 90%; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Lugar Asegurado 🕒</h2>
        <p>Bloqueamos un espacio en la agenda para tus fechas del <strong>{{ desde }}</strong> al <strong>{{ hasta }}</strong>.</p>
        <p>Monto: $15.000 ARS</p>
        <a href="/webhook_simulado?reserva_id={{ reserva_id }}" class="btn-simular">🟢 [ Simular Pago Exitoso ]</a>
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
        .btn-ws { background: #25d366; color: white; padding: 6px 12px; text-decoration: none; border-radius: 6px; font-size: 12px; font-weight: bold; }
        .error-flash { background: #fee2e2; color: #ef4444; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <header>
        <h1>Centro de Mandos - Agenda del Hotel</h1>
        <a href="/" style="color: #38bdf8; text-decoration:none; font-weight:bold;">+ Simular Cliente</a>
    </header>
    
    <div class="contenedor">
        {% if msg_error %}
            <div class="error-flash">⚠️ {{ msg_error }}</div>
        {% endif %}

        <div class="seccion">
            <h2>Todas las Reservas y Asignación de Módulos</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Huésped</th>
                        <th>DNI</th>
                        <th>Desde</th>
                        <th>Hasta</th>
                        <th>Módulo Físico</th>
                        <th>Estado</th>
                        <th>Acción</th>
                    </tr>
                </thead>
                <tbody>
                    {% for res in reservas %}
                    <tr>
                        <td>#{{ res.id }}</td>
                        <td><strong>{{ res.huesped }}</strong></td>
                        <td>{{ res.dni }}</td>
                        <td>{{ res.desde }}</td>
                        <td>{{ res.hasta }}</td>
                        <td>
                            <form action="/reasignar" method="POST" style="margin:0; display:inline;">
                                <input type="hidden" name="reserva_id" value="{{ res.id }}">
                                <select name="nuevo_modulo" onchange="this.form.submit()">
                                    {% for m in range(1, total_modulos + 1) %}
                                        <option value="{{ m }}" {{ 'selected' if res.modulo == m }}>Módulo {{ m }}</option>
                                    {% endfor %}
                                </select>
                            </form>
                        </td>
                        <td>
                            <span class="badge {{ 'pendiente' if res.estado == 'Pendiente de Pago' else 'ocupado' }}">
                                {{ res.estado }}
                            </span>
                        </td>
                        <td>
                            <a href="#" class="btn-ws">📱 WhatsApp</a>
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
    desde = request.form.get('desde')
    hasta = request.form.get('hasta')
    personas = request.form.get('personas')
    
    # Buscamos de forma automatizada qué módulo tiene libre ESTE rango de fechas exacto
    modulo_libre = None
    for m in range(1, TOTAL_MODULOS + 1):
        if verificar_disponibilidad(m, desde, hasta):
            modulo_libre = m
            break
            
    if not modulo_libre:
        return "Lo sentimos, no hay disponibilidad en ninguna habitación para las fechas seleccionadas.", 400
        
    # Creamos el registro de la reserva
    nueva_res = {
        "id": len(reservas) + 1,
        "modulo": modulo_libre,
        "estado": "Pendiente de Pago",
        "huesped": nombre,
        "dni": dni,
        "desde": desde,
        "hasta": hasta,
        "personas": personas
    }
    reservas.append(nueva_res)
    
    return render_template_string(HTML_PAGO, reserva_id=nueva_res["id"], desde=desde, hasta=hasta)

@app.route('/webhook_simulado')
def webhook_simulado():
    res_id = int(request.args.get('reserva_id'))
    for res in reservas:
        if res["id"] == res_id:
            res["estado"] = "Ocupado"
            break
    return redirect(url_for('ver_panel'))

# CAMBIAR HABITACIÓN AL VUELO: Ruta que procesa el menú desplegable del administrador
@app.route('/reasignar', methods=['POST'])
def reasignar_modulo():
    res_id = int(request.form.get('reserva_id'))
    nuevo_mod = int(request.form.get('nuevo_modulo'))
    
    # Buscamos los datos de esa reserva para validar las fechas contra el nuevo módulo
    res_actual = None
    for res in reservas:
        if res["id"] == res_id:
            res_actual = res
            break
            
    if res_actual:
        # Clave: Verificamos si el nuevo módulo que elegiste está libre en ESAS fechas
        if verificar_disponibilidad(nuevo_mod, res_actual["desde"], res_actual["hasta"], reserva_id_ignorar=res_id):
            res_actual["modulo"] = nuevo_mod
            print(f"[ADMIN] Reserva #{res_id} movida con éxito al Módulo {nuevo_mod}")
            return redirect(url_for('ver_panel'))
        else:
            # Si el módulo que elegiste está pisado por otra reserva en esos días, tira aviso
            return redirect(url_for('ver_panel', error=f"¡Error! El Módulo {nuevo_mod} ya está ocupado en las fechas de esa reserva."))
            
    return redirect(url_for('ver_panel'))

@app.route('/panel')
def ver_panel():
    error_msg = request.args.get('error')
    return render_template_string(HTML_PANEL, reservas=reservas, total_modulos=TOTAL_MODULOS, msg_error=error_msg)

if __name__ == '__main__':
    app.run(debug=True, port=5000)