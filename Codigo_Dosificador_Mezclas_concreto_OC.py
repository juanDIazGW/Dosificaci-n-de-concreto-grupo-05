"""
Dosificador de mezclas para obra (Concreto y Morteros)
Cumple con el método de volúmenes absolutos, corrección por humedad/absorción,
abundamiento de arena, redondeo a medio recipiente con alertas (>5%),
lectura desde CSV editable e ilustración gráfica en obra.

Solo usa la biblioteca estándar de Python 3 (tkinter, csv, math, os, datetime).
Ejecutar:  python dosificacion_obra.py
"""
import csv
import math
import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# ---------------- Constantes y configuración ----------------
ARCHIVO_USOS_CSV = "usos_mezclas.csv"
KG_BULTO = 50.0
PSI_A_MPA = 0.00689476
ELEMENTOS_ESTRUCTURALES_BLOQUEADO_2000 = {"Zapata", "Columna", "Viga"}
MENSAJE_NSR10_2000 = (
    "Al no cumplir con la resistencia mínima estructural exigida por la NSR-10 "
    "(>= 2500 PSI / 17.2 MPa), no se puede proceder con el cálculo."
)

# Paleta de colores Ingeniería Civil
C_NAVY_OSC = "#0f172a"
C_NAVY = "#1e293b"
C_ACERO = "#334155"
C_AMARILLO = "#f59e0b"
C_AMARILLO_CLARO = "#fef3c7"
C_FONDO = "#eef2f6"
C_BLANCO = "#ffffff"
C_BORDE = "#cbd5e1"
C_TEXTO = "#1e293b"
C_SUBTEXTO = "#64748b"

# Tabla de referencia de concretos por resistencia (PSI -> c, a, g, a/c)
DOSIFICACIONES_CONCRETO = {
    2000: (1.0, 3.0, 4.0, 0.60),
    2500: (1.0, 2.0, 4.0, 0.55),
    3000: (1.0, 2.0, 3.0, 0.50),
    3500: (1.0, 2.0, 2.0, 0.45),
    4000: (1.0, 1.5, 2.5, 0.45),
}

# Propiedades físicas didácticas por defecto (Caso de comprobación del docente)
PROPIEDADES_DEFECTO = {
    "rho_cem": "1250",    # kg/m3 masa unitaria suelta cemento
    "g_cem": "3.10",      # densidad relativa G cemento
    "rho_are": "1550",    # kg/m3 masa unitaria suelta arena seca
    "g_are": "2.60",      # densidad relativa G arena
    "hum_are": "6.0",     # % humedad natural arena
    "abs_are": "2.0",     # % absorción arena
    "fab_are": "1.25",    # factor de abundamiento arena húmeda
    "rho_gra": "1500",    # kg/m3 masa unitaria suelta grava
    "g_gra": "2.65",      # densidad relativa G grava
    "hum_gra": "1.0",     # % humedad natural grava
    "abs_gra": "1.0",     # % absorción grava
    "aire_pct": "2.0",    # % aire atrapado/incorporado
}

# Recipientes estándar en obra (capacidad en litros)
RECIPIENTES_ESTANDAR = {
    "Balde estándar (20 L)": 20.0,
    "Carretilla rasa (60 L)": 60.0,
    "Palada estándar (4.5 L)": 4.5,
    "Recipiente especial (definir medidas)": None,
}

# Filas iniciales para crear el CSV editable si no existe
USOS_POR_DEFECTO_CSV = [
    {
        "nombre": "Pega de bloques",
        "categoria": "mortero",
        "psi_defecto": "",
        "cemento": "1",
        "arena": "4",
        "grava": "0",
        "rel_ac": "0.70",
        "espesor_def": "1.5",
        "formulario": "pega_bloques",
        "descripcion": "Mortero de pega 1:4 (a/c = 0.70) para mampostería. Calcula volumen real de juntas según bloque y espesor de pega.",
    },
    {
        "nombre": "Repello (Pañete)",
        "categoria": "mortero",
        "psi_defecto": "",
        "cemento": "1",
        "arena": "4",
        "grava": "0",
        "rel_ac": "0.70",
        "espesor_def": "1.5",
        "formulario": "repello",
        "descripcion": "Mortero 1:4 (a/c = 0.70) para recubrimiento de muros y cielos (espesor en cm y número de caras).",
    },
    {
        "nombre": "Nivelación de piso",
        "categoria": "mortero",
        "psi_defecto": "",
        "cemento": "1",
        "arena": "3",
        "grava": "0",
        "rel_ac": "0.60",
        "espesor_def": "4.0",
        "formulario": "nivelacion",
        "descripcion": "Mortero 1:3 (a/c = 0.60) para nivelación de pisos y alistados (sin grava).",
    },
    {
        "nombre": "Placa de contrapiso",
        "categoria": "concreto",
        "psi_defecto": "3000",
        "cemento": "1",
        "arena": "2",
        "grava": "3",
        "rel_ac": "0.50",
        "espesor_def": "0.10",
        "formulario": "prisma_general",
        "descripcion": "Concreto para contrapisos y senderos apoyados sobre terreno compactado.",
    },
    {
        "nombre": "Zapata",
        "categoria": "concreto",
        "psi_defecto": "3000",
        "cemento": "1",
        "arena": "2",
        "grava": "3",
        "rel_ac": "0.50",
        "espesor_def": "0.35",
        "formulario": "zapata",
        "descripcion": "Concreto estructural para cimentación superficial (base rectangular o circular, con pedestal opcional).",
    },
    {
        "nombre": "Columna",
        "categoria": "concreto",
        "psi_defecto": "3500",
        "cemento": "1",
        "arena": "2",
        "grava": "2",
        "rel_ac": "0.45",
        "espesor_def": "3.00",
        "formulario": "columna",
        "descripcion": "Concreto para elementos estructurales verticales (sección rectangular o cilíndrica).",
    },
    {
        "nombre": "Viga",
        "categoria": "concreto",
        "psi_defecto": "3500",
        "cemento": "1",
        "arena": "2",
        "grava": "2",
        "rel_ac": "0.45",
        "espesor_def": "0.30",
        "formulario": "prisma_general",
        "descripcion": "Concreto para elementos estructurales horizontales (b x h x L x cantidad).",
    },
]


def cargar_usos_desde_csv(ruta=ARCHIVO_USOS_CSV):
    """Carga los usos desde un CSV editable; si no existe, lo crea con los valores de referencia."""
    campos = [
        "nombre", "categoria", "psi_defecto", "cemento", "arena", "grava",
        "rel_ac", "espesor_def", "formulario", "descripcion"
    ]
    if not os.path.exists(ruta):
        try:
            with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=campos)
                w.writeheader()
                w.writerows(USOS_POR_DEFECTO_CSV)
        except OSError:
            pass

    usos = {}
    orden = []
    filas_fuente = []
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("nombre", "").strip():
                        filas_fuente.append(row)
        except OSError:
            filas_fuente = USOS_POR_DEFECTO_CSV
    if not filas_fuente:
        filas_fuente = USOS_POR_DEFECTO_CSV

    for row in filas_fuente:
        nombre = row["nombre"].strip()
        es_mortero = row.get("categoria", "concreto").strip().lower() == "mortero"
        psi_str = row.get("psi_defecto", "").strip()
        psi = int(float(psi_str)) if psi_str else None
        c = float(row.get("cemento", 1) or 1)
        a = float(row.get("arena", 2) or 2)
        g = float(row.get("grava", 0 if es_mortero else 3) or 0)
        ac = float(row.get("rel_ac", 0.70 if es_mortero else 0.50) or 0.50)
        esp = row.get("espesor_def", "0.10").strip() or "0.10"
        form = row.get("formulario", "prisma_general").strip() or "prisma_general"
        desc = row.get("descripcion", f"Mezcla para {nombre}.").strip()
        usos[nombre] = {
            "es_mortero": es_mortero,
            "psi": psi,
            "cemento": c,
            "arena": a,
            "grava": g,
            "rel_ac": ac,
            "espesor_def": esp,
            "formulario": form,
            "descripcion": desc,
        }
        orden.append(nombre)
    return usos, orden


# ---------------- Lógica matemática y validación ----------------
class ErrorValidacion(ValueError):
    pass


def leer_numero(texto, nombre, minimo=None, maximo=None, permitir_cero=False):
    limpio = str(texto).strip().replace(",", ".")
    if not limpio:
        raise ErrorValidacion(f"El campo «{nombre}» está vacío.")
    try:
        valor = float(limpio)
    except ValueError:
        raise ErrorValidacion(f"«{nombre}» debe ser un número (se escribió «{texto}»).")
    if not math.isfinite(valor):
        raise ErrorValidacion(f"«{nombre}» no es un número válido.")
    if valor < 0 or (valor == 0 and not permitir_cero):
        raise ErrorValidacion(f"«{nombre}» debe ser mayor que cero.")
    if minimo is not None and valor < minimo:
        raise ErrorValidacion(f"«{nombre}» no puede ser menor que {minimo}.")
    if maximo is not None and valor > maximo:
        raise ErrorValidacion(f"«{nombre}» no puede ser mayor que {maximo} (valor poco realista).")
    return valor


def redondear_medio_recipiente(valor):
    """Redondea al múltiplo de 0.5 más cercano."""
    return round(valor * 2.0) / 2.0


def calcular_mezcla_volumenes_absolutos(
    v_geom, desperdicio_pct,
    p_cem, p_are, p_gra, modo_proporcion, rel_ac,
    bultos_por_tanda,
    props,
    cap_recipiente_l, nombre_recipiente,
    es_mortero=False, detalle_extra=""
):
    """
    Implementa el método de volúmenes absolutos con:
    - Normalización de proporción (cemento = 1)
    - Entrada en volumen suelto seco o en peso (ambos producen la misma receta)
    - Rendimiento por tanda V_tanda = sum(Mi / rho_abs_i) / (1 - aire)
    - Abundamiento de arena húmeda V_arena_obra = V_seca * f_ab
    - Corrección de agua por humedad y absorción: Agua = Ma - sum(Mi * (hi - absi))
    - Redondeo a 0.5 recipientes con alerta si la desviación supera el 5%
    """
    alertas = []

    # 1. Normalización de la proporción respecto al cemento
    c_norm = 1.0
    a_norm = p_are / p_cem
    g_norm = p_gra / p_cem

    # 2. Masa de cemento por tanda (kg)
    masa_cem_tanda = bultos_por_tanda * KG_BULTO  # ej. 50 kg (1 bulto) o 25 kg (0.5 bulto)
    v_suelto_cem_tanda_l = (masa_cem_tanda / props["rho_cem"]) * 1000.0

    # 3. Conversión de proporción a masas y volúmenes sueltos secos por tanda
    if modo_proporcion == "volumen":
        v_suelto_are_tanda_l = v_suelto_cem_tanda_l * a_norm
        v_suelto_gra_tanda_l = v_suelto_cem_tanda_l * g_norm
        masa_are_tanda = (v_suelto_are_tanda_l / 1000.0) * props["rho_are"]
        masa_gra_tanda = (v_suelto_gra_tanda_l / 1000.0) * props["rho_gra"]
        prop_vol_str = f"1 : {a_norm:g} : {g_norm:g}"
        prop_peso_str = f"1 : {masa_are_tanda / masa_cem_tanda:.2f} : {masa_gra_tanda / masa_cem_tanda:.2f}"
    else:
        # Modo en peso: las partes son razones en masa respecto al cemento
        masa_are_tanda = masa_cem_tanda * a_norm
        masa_gra_tanda = masa_cem_tanda * g_norm
        v_suelto_are_tanda_l = (masa_are_tanda / props["rho_are"]) * 1000.0
        v_suelto_gra_tanda_l = (masa_gra_tanda / props["rho_gra"]) * 1000.0
        prop_peso_str = f"1 : {a_norm:g} : {g_norm:g}"
        prop_vol_str = (
            f"1 : {v_suelto_are_tanda_l / v_suelto_cem_tanda_l:.2f} : "
            f"{v_suelto_gra_tanda_l / v_suelto_cem_tanda_l:.2f}"
        )

    masa_agua_diseno_tanda = masa_cem_tanda * rel_ac  # 1 kg agua = 1 L

    # 4. Volúmenes absolutos por tanda (en Litros)
    v_abs_cem_l = masa_cem_tanda / props["g_cem"]
    v_abs_are_l = masa_are_tanda / props["g_are"]
    v_abs_gra_l = masa_gra_tanda / props["g_gra"]
    v_abs_agua_l = masa_agua_diseno_tanda / 1.0
    suma_v_abs_l = v_abs_cem_l + v_abs_are_l + v_abs_gra_l + v_abs_agua_l

    aire_frac = props["aire_pct"] / 100.0
    v_tanda_l = suma_v_abs_l / (1.0 - aire_frac)
    v_tanda_m3 = v_tanda_l / 1000.0
    bultos_por_m3 = bultos_por_tanda / v_tanda_m3

    # 5. Abundamiento de arena húmeda y corrección de agua por humedad libre
    v_arena_obra_tanda_l = v_suelto_are_tanda_l * props["fab_are"]
    v_grava_obra_tanda_l = v_suelto_gra_tanda_l

    hum_libre_are = (props["hum_are"] - props["abs_are"]) / 100.0
    hum_libre_gra = (props["hum_gra"] - props["abs_gra"]) / 100.0
    agua_aporte_are_l = masa_are_tanda * hum_libre_are
    agua_aporte_gra_l = masa_gra_tanda * hum_libre_gra
    agua_agregar_tanda_l = masa_agua_diseno_tanda - (agua_aporte_are_l + agua_aporte_gra_l)

    if agua_agregar_tanda_l < 0:
        alertas.append(
            f"ALERTA DE AGUA NEGATIVA ({agua_agregar_tanda_l:.1f} L): Los agregados tienen más humedad libre "
            f"({agua_aporte_are_l + agua_aporte_gra_l:.1f} L) que el agua de diseño ({masa_agua_diseno_tanda:.1f} L). "
            "Se ajusta agua a agregar en 0 L y se recomienda secar los agregados o ajustar la relación a/c."
        )
        agua_agregar_tanda_l = 0.0

    # 6. Cálculo de volumen total de obra y número de tandas / bultos
    v_total_requerido_m3 = v_geom * (1.0 + desperdicio_pct / 100.0)
    bultos_exactos = v_total_requerido_m3 * bultos_por_m3

    if es_mortero and bultos_por_tanda == 0.5:
        # En morteros a mano se permite redondear a medio bulto (0.5) hacia arriba
        bultos_pedir = math.ceil((bultos_exactos - 1e-9) * 2.0) / 2.0
    else:
        bultos_pedir = float(math.ceil(bultos_exactos - 1e-9))

    num_tandas = bultos_pedir / bultos_por_tanda
    v_producido_real_m3 = num_tandas * v_tanda_m3

    # 7. Receta por tanda en el recipiente seleccionado (redondeo a 0.5 y alerta > 5%)
    def evaluar_recipiente(vol_l, nombre_mat, permitir_otro_recip=True):
        if vol_l <= 1e-9:
            return 0.0, 0.0, 0.0
        exacto = vol_l / cap_recipiente_l
        redondeado = redondear_medio_recipiente(exacto)
        if redondeado == 0 and exacto > 0:
            redondeado = 0.5
        desv_pct = ((redondeado - exacto) / exacto) * 100.0
        if abs(desv_pct) > 5.0 and permitir_otro_recip:
            sugerencia = ""
            if cap_recipiente_l > 20.0:
                baldes_eq = vol_l / 20.0
                sugerencia = f" Sugerencia: use el Balde de 20 L ({baldes_eq:.1f} baldes) para mayor precisión."
            alertas.append(
                f"DESVIACIÓN > 5 % EN {nombre_mat.upper()}: {vol_l:.1f} L equivalen a {exacto:.2f} "
                f"en «{nombre_recipiente}». Al redondear a {redondeado:g} se altera la dosificación en "
                f"{desv_pct:+.1f}%.{sugerencia}"
            )
        return exacto, redondeado, desv_pct

    are_rec_ex, are_rec_red, are_desv = evaluar_recipiente(v_arena_obra_tanda_l, "Arena húmeda")
    gra_rec_ex, gra_rec_red, gra_desv = evaluar_recipiente(v_grava_obra_tanda_l, "Grava")
    agu_rec_ex, agu_rec_red, agu_desv = evaluar_recipiente(agua_agregar_tanda_l, "Agua")

    # 8. Pedido total de materiales para toda la obra (basado en el número real de tandas)
    total_cem_kg = bultos_pedir * KG_BULTO
    total_arena_humeda_m3 = (v_arena_obra_tanda_l * num_tandas) / 1000.0
    total_arena_seca_m3 = (v_suelto_are_tanda_l * num_tandas) / 1000.0
    total_grava_m3 = (v_grava_obra_tanda_l * num_tandas) / 1000.0
    total_agua_l = agua_agregar_tanda_l * num_tandas

    # Equivalencias en herramientas estándar para ilustración gráfica (por tanda y total)
    herramientas_tanda = {
        "cemento": (
            v_suelto_cem_tanda_l / 20.0,
            None,
            v_suelto_cem_tanda_l / 4.5,
        ),
        "arena": (
            v_arena_obra_tanda_l / 20.0,
            v_arena_obra_tanda_l / 60.0,
            v_arena_obra_tanda_l / 4.5,
        ),
        "grava": (0.0, 0.0, 0.0) if v_grava_obra_tanda_l == 0 else (
            v_grava_obra_tanda_l / 20.0,
            v_grava_obra_tanda_l / 60.0,
            v_grava_obra_tanda_l / 4.5,
        ),
        "agua": (
            agua_agregar_tanda_l / 20.0,
            None,
            None,
        ),
    }

    herramientas_total = {
        mat: (
            None if herramientas_tanda[mat][0] is None else herramientas_tanda[mat][0] * num_tandas,
            None if herramientas_tanda[mat][1] is None else herramientas_tanda[mat][1] * num_tandas,
            None if herramientas_tanda[mat][2] is None else herramientas_tanda[mat][2] * num_tandas,
        )
        for mat in ("cemento", "arena", "grava", "agua")
    }

    # 9. Memoria de cálculo explicativa paso a paso
    memoria = [
        f"1. NORMALIZACIÓN DE DOSIFICACIÓN ({modo_proporcion.upper()}):",
        f"   • Proporción ingresada: {p_cem:g} : {p_are:g} : {p_gra:g}  →  Normalizada (cemento = 1): 1 : {a_norm:g} : {g_norm:g}",
        f"   • Equivalencia en volumen suelto seco: {prop_vol_str}   |   Equivalencia en peso: {prop_peso_str}",
        f"   • Tamaño de tanda elegido: {bultos_por_tanda:g} bulto(s) de cemento = {masa_cem_tanda:.1f} kg ({v_suelto_cem_tanda_l:.1f} L sueltos).",
        "",
        "2. MÉTODO DE VOLÚMENES ABSOLUTOS POR TANDA:",
        f"   • Cemento: {masa_cem_tanda:.1f} kg / ({props['g_cem']:.2f} × 1000) = {v_abs_cem_l:.2f} L absolutos  [suelto: {v_suelto_cem_tanda_l:.1f} L]",
        f"   • Arena seca: {masa_are_tanda:.1f} kg / ({props['g_are']:.2f} × 1000) = {v_abs_are_l:.2f} L absolutos  [suelto: {v_suelto_are_tanda_l:.1f} L]",
        f"   • Grava: {masa_gra_tanda:.1f} kg / ({props['g_gra']:.2f} × 1000) = {v_abs_gra_l:.2f} L absolutos  [suelto: {v_suelto_gra_tanda_l:.1f} L]",
        f"   • Agua de diseño (a/c = {rel_ac:g}): {masa_agua_diseno_tanda:.1f} kg / 1000 = {v_abs_agua_l:.2f} L absolutos",
        f"   • Suma volúmenes sólidos + agua = {suma_v_abs_l:.2f} L",
        f"   • Rendimiento con {props['aire_pct']:g}% de aire: V_tanda = {suma_v_abs_l:.2f} / (1 - {aire_frac:.3f}) = {v_tanda_l:.2f} L ({v_tanda_m3:.4f} m³)",
        f"   • Consumo unitario: {bultos_por_m3:.2f} bultos de cemento por m³ de mezcla.",
        "",
        "3. CORRECCIONES DE OBRA (HUMEDAD Y ABUNDAMIENTO):",
        f"   • Arena húmeda (abundamiento f_ab = {props['fab_are']:.2f}): {v_suelto_are_tanda_l:.1f} L × {props['fab_are']:.2f} = {v_arena_obra_tanda_l:.1f} L en obra.",
        f"   • Agua libre arena: {masa_are_tanda:.1f} kg × ({props['hum_are']:g}% - {props['abs_are']:g}%) = {agua_aporte_are_l:+.1f} L",
        f"   • Agua libre grava: {masa_gra_tanda:.1f} kg × ({props['hum_gra']:g}% - {props['abs_gra']:g}%) = {agua_aporte_gra_l:+.1f} L",
        f"   • Agua neta a agregar por tanda: {masa_agua_diseno_tanda:.1f} - ({agua_aporte_are_l + agua_aporte_gra_l:+.1f}) = {agua_agregar_tanda_l:.1f} L.",
        "",
        "4. CANTIDAD DE TANDAS Y PEDIDO TOTAL:",
        f"   • Volumen geométrico: {v_geom:.3f} m³  |  Con {desperdicio_pct:g}% desperdicio: {v_total_requerido_m3:.3f} m³",
        f"   • Bultos exactos: {v_total_requerido_m3:.3f} × {bultos_por_m3:.2f} = {bultos_exactos:.2f} bultos  →  Pedido: {bultos_pedir:g} bultos ({num_tandas:g} tandas).",
        f"   • Volumen real producido con {num_tandas:g} tandas: {v_producido_real_m3:.3f} m³.",
    ]

    return {
        "v_geom": v_geom,
        "v_total": v_total_requerido_m3,
        "v_producido_real": v_producido_real_m3,
        "v_tanda_l": v_tanda_l,
        "bultos_por_m3": bultos_por_m3,
        "bultos_por_tanda": bultos_por_tanda,
        "bultos_exactos": bultos_exactos,
        "bultos": bultos_pedir,
        "num_tandas": num_tandas,
        "prop_vol_str": prop_vol_str,
        "prop_peso_str": prop_peso_str,
        "rel_ac": rel_ac,
        # Valores por tanda
        "tanda": {
            "cem_kg": masa_cem_tanda,
            "cem_l": v_suelto_cem_tanda_l,
            "are_kg": masa_are_tanda,
            "are_seca_l": v_suelto_are_tanda_l,
            "are_obra_l": v_arena_obra_tanda_l,
            "gra_kg": masa_gra_tanda,
            "gra_obra_l": v_grava_obra_tanda_l,
            "agua_l": agua_agregar_tanda_l,
            "are_rec_ex": are_rec_ex,
            "are_rec_red": are_rec_red,
            "are_desv": are_desv,
            "gra_rec_ex": gra_rec_ex,
            "gra_rec_red": gra_rec_red,
            "gra_desv": gra_desv,
            "agu_rec_ex": agu_rec_ex,
            "agu_rec_red": agu_rec_red,
            "agu_desv": agu_desv,
        },
        # Totales de obra (pedido)
        "cemento_kg": total_cem_kg,
        "arena_m3": total_arena_humeda_m3,
        "arena_seca_m3": total_arena_seca_m3,
        "grava_m3": total_grava_m3,
        "agua_l": total_agua_l,
        # Herramientas y extras
        "cap_recipiente_l": cap_recipiente_l,
        "nombre_recipiente": nombre_recipiente,
        "herramientas": herramientas_total,
        "herramientas_tanda": herramientas_tanda,
        "alertas": alertas,
        "memoria": "\n".join(memoria),
        "detalle_extra": detalle_extra,
    }


def exportar_csv(ruta, tipo_mezcla, entradas, r):
    t = r["tanda"]
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=",")
        w.writerow(["REPORTE TECNICO DE DOSIFICACION DE CONCRETO / MORTERO"])
        w.writerow(["Fecha", datetime.now().strftime("%Y-%m-%d %H:%M")])
        w.writerow(["Uso / Elemento", tipo_mezcla])
        w.writerow(["Proporcion normalizada (volumen suelto)", r["prop_vol_str"]])
        w.writerow(["Proporcion normalizada (peso)", r["prop_peso_str"]])
        w.writerow([])
        w.writerow(["DATOS DE ENTRADA"])
        for k, v in entradas:
            w.writerow([k, v])
        w.writerow(["Volumen geometrico (m3)", f"{r['v_geom']:.4f}"])
        w.writerow(["Volumen con desperdicio (m3)", f"{r['v_total']:.4f}"])
        w.writerow(["Rendimiento por tanda (L)", f"{r['v_tanda_l']:.2f}"])
        w.writerow(["Consumo bultos/m3", f"{r['bultos_por_m3']:.2f}"])
        w.writerow(["Numero de tandas", f"{r['num_tandas']:g}"])
        w.writerow([])
        w.writerow([f"TARJETA DE MEZCLA POR TANDA ({r['bultos_por_tanda']:g} bulto) — Recipiente: {r['nombre_recipiente']}"])
        w.writerow(["Material", "Cantidad en obra", "Recipientes exactos", "Recipientes redondeados (0.5)", "Desviacion (%)"])
        w.writerow(["Cemento", f"{t['cem_kg']:.1f} kg ({t['cem_l']:.1f} L)", f"{r['bultos_por_tanda']:g} bulto", f"{r['bultos_por_tanda']:g} bulto", "0.0%"])
        w.writerow(["Arena humeda", f"{t['are_obra_l']:.1f} L", f"{t['are_rec_ex']:.2f}", f"{t['are_rec_red']:g}", f"{t['are_desv']:+.1f}%"])
        if t["gra_obra_l"] > 0:
            w.writerow(["Grava", f"{t['gra_obra_l']:.1f} L", f"{t['gra_rec_ex']:.2f}", f"{t['gra_rec_red']:g}", f"{t['gra_desv']:+.1f}%"])
        w.writerow(["Agua a agregar", f"{t['agua_l']:.1f} L", f"{t['agu_rec_ex']:.2f}", f"{t['agu_rec_red']:g}", f"{t['agu_desv']:+.1f}%"])
        w.writerow([])
        w.writerow(["PEDIDO TOTAL DE MATERIALES PARA OBRA"])
        w.writerow(["Material", "Cantidad a pedir", "Observacion"])
        w.writerow(["Cemento", f"{r['bultos']:g} bultos de 50 kg", f"{r['cemento_kg']:.1f} kg (exacto: {r['bultos_exactos']:.2f} bultos)"])
        w.writerow(["Arena humeda", f"{r['arena_m3']:.3f} m3", f"equivale a {r['arena_seca_m3']:.3f} m3 de arena seca"])
        w.writerow(["Grava", f"{r['grava_m3']:.3f} m3", "no aplica (mortero)" if r["grava_m3"] == 0 else "agregado grueso"])
        w.writerow(["Agua neta", f"{r['agua_l']:.1f} L", f"relacion a/c = {r['rel_ac']:g} corregida por humedad"])
        if r["alertas"]:
            w.writerow([])
            w.writerow(["ALERTAS DE OBRA"])
            for al in r["alertas"]:
                w.writerow([al])


# ---------------- Ilustraciones vectoriales de Ingeniería Civil ----------------
class ArteIngenieria:
    """Primitivas gráficas de cascos, edificios en construcción y elementos estructurales."""

    @staticmethod
    def dibujar_casco(cv, x, y, escala=1.0):
        s = escala
        cv.create_oval(x + 4 * s, y + 34 * s, x + 58 * s, y + 42 * s, fill="#020617", outline="")
        cv.create_arc(
            x + 6 * s, y + 4 * s, x + 54 * s, y + 48 * s,
            start=0, extent=180, fill="#f59e0b", outline="#92400e", width=1.6
        )
        cv.create_polygon(
            x + 26 * s, y + 4 * s,
            x + 34 * s, y + 4 * s,
            x + 36 * s, y + 26 * s,
            x + 24 * s, y + 26 * s,
            fill="#fbbf24", outline="#b45309", width=1.2
        )
        cv.create_rectangle(
            x + 11 * s, y + 21 * s, x + 49 * s, y + 24 * s,
            fill="#f8fafc", outline=""
        )
        cv.create_polygon(
            x + 2 * s, y + 27 * s,
            x + 56 * s, y + 26 * s,
            x + 63 * s, y + 31 * s,
            x + 48 * s, y + 34 * s,
            x + 6 * s, y + 32 * s,
            fill="#d97706", outline="#78350f", width=1.5
        )
        cv.create_arc(
            x + 12 * s, y + 8 * s, x + 28 * s, y + 22 * s,
            start=100, extent=65, style="arc", outline="#fef3c7", width=2
        )

    @staticmethod
    def dibujar_escena_obra(cv, x, y):
        for gx in range(x, x + 310, 22):
            cv.create_line(gx, y, gx, y + 112, fill="#1e293b", width=1)
        for gy in range(y, y + 115, 22):
            cv.create_line(x, gy, x + 310, gy, fill="#1e293b", width=1)

        bx1, by1, bx2, by2 = x + 16, y + 32, x + 82, y + 104
        cv.create_rectangle(bx1, by1, bx2, by2, fill="#334155", outline="#64748b", width=1.5)
        for piso in range(4):
            wy = by1 + 8 + piso * 16
            for col in range(3):
                wx = bx1 + 8 + col * 19
                color_v = "#fef08a" if (piso + col) % 2 == 0 else "#0f172a"
                cv.create_rectangle(wx, wy, wx + 12, wy + 10, fill=color_v, outline="#475569")

        ex1, ey1, ex2, ey2 = x + 94, y + 18, x + 186, y + 104
        for cx in (ex1 + 4, ex1 + 32, ex1 + 60, ex2 - 4):
            cv.create_line(cx, ey1, cx, ey2, fill="#cbd5e1", width=4)
        for ly in (ey1 + 4, ey1 + 26, ey1 + 48, ey1 + 70, ey2):
            cv.create_line(ex1, ly, ex2, ly, fill="#94a3b8", width=4)
        cv.create_rectangle(ex1 + 6, ey1 + 50, ex2 - 6, ey2 - 2, fill="#ea580c", stipple="gray50", outline="#fb923c")
        for cx in (ex1 + 4, ex1 + 32, ex1 + 60, ex2 - 4):
            cv.create_line(cx - 1, ey1 - 7, cx - 1, ey1, fill="#f59e0b", width=1.5)
            cv.create_line(cx + 2, ey1 - 7, cx + 2, ey1, fill="#f59e0b", width=1.5)

        gx = x + 225
        gy_top = y + 8
        gy_bot = y + 104
        cv.create_rectangle(gx - 12, gy_bot - 8, gx + 12, gy_bot, fill="#64748b", outline="#94a3b8")
        cv.create_line(gx - 5, gy_top, gx - 5, gy_bot - 8, fill="#f59e0b", width=2)
        cv.create_line(gx + 5, gy_top, gx + 5, gy_bot - 8, fill="#f59e0b", width=2)
        for step in range(gy_top + 6, gy_bot - 10, 12):
            cv.create_line(gx - 5, step, gx + 5, step + 6, fill="#fbbf24", width=1.2)
            cv.create_line(gx + 5, step + 6, gx - 5, step + 12, fill="#fbbf24", width=1.2)
        pluma_y = gy_top + 12
        cv.create_line(gx - 68, pluma_y, gx + 58, pluma_y, fill="#f59e0b", width=2.5)
        cv.create_line(gx - 68, pluma_y - 4, gx + 58, pluma_y - 4, fill="#fbbf24", width=1.2)
        cv.create_line(gx, gy_top, gx - 60, pluma_y - 4, fill="#cbd5e1", width=1.2)
        cv.create_line(gx, gy_top, gx + 48, pluma_y - 4, fill="#cbd5e1", width=1.2)
        cv.create_rectangle(gx + 40, pluma_y + 1, gx + 56, pluma_y + 12, fill="#94a3b8", outline="#475569")
        cv.create_rectangle(gx - 11, pluma_y + 2, gx - 5, pluma_y + 11, fill="#38bdf8", outline="#f59e0b")
        carga_x = gx - 52
        cv.create_line(carga_x, pluma_y, carga_x, pluma_y + 28, fill="#e2e8f0", width=1.2)
        cv.create_polygon(
            carga_x - 6, pluma_y + 28,
            carga_x + 6, pluma_y + 28,
            carga_x + 4, pluma_y + 38,
            carga_x - 4, pluma_y + 38,
            fill="#f59e0b", outline="#78350f"
        )
        cv.create_line(x + 6, y + 104, x + 298, y + 104, fill="#f59e0b", width=2.5)

    @staticmethod
    def dibujar_icono_mezcla(cv, nombre, formulario="prisma_general"):
        if nombre == "Pega de bloques" or formulario == "pega_bloques":
            for fila in range(3):
                by = 8 + fila * 11
                offset = 8 if fila % 2 == 1 else 0
                for col in range(2):
                    bx = 8 + offset + col * 20
                    cv.create_rectangle(bx, by, bx + 18, by + 9, fill="#94a3b8", outline="#334155", width=1.2)
            cv.create_line(8, 19, 48, 19, fill="#f59e0b", width=2)
            cv.create_line(8, 30, 48, 30, fill="#f59e0b", width=2)

        elif nombre == "Repello (Pañete)" or formulario == "repello":
            cv.create_rectangle(10, 8, 34, 38, fill="#cbd5e1", outline="#475569", width=1.2)
            cv.create_rectangle(24, 8, 34, 38, fill="#fde68a", outline="#d97706", width=1.2)
            cv.create_polygon(32, 14, 46, 10, 46, 34, 32, 30, fill="#64748b", outline="#1e293b", width=1.2)
            cv.create_line(46, 22, 52, 22, fill="#92400e", width=3)

        elif nombre == "Nivelación de piso" or formulario == "nivelacion":
            cv.create_rectangle(8, 28, 48, 38, fill="#94a3b8", outline="#475569")
            cv.create_rectangle(8, 21, 48, 28, fill="#fcd34d", outline="#b45309")
            cv.create_rectangle(12, 11, 44, 18, fill="#f59e0b", outline="#78350f", width=1.2)
            cv.create_rectangle(24, 12, 32, 17, fill="#bae6fd", outline="#0284c7")

        elif nombre == "Placa de contrapiso":
            cv.create_polygon(8, 24, 28, 14, 48, 24, 28, 34, fill="#cbd5e1", outline="#334155", width=1.4)
            cv.create_polygon(8, 24, 28, 34, 28, 40, 8, 30, fill="#94a3b8", outline="#334155", width=1.2)
            cv.create_polygon(48, 24, 28, 34, 28, 40, 48, 30, fill="#64748b", outline="#334155", width=1.2)
            cv.create_line(18, 19, 38, 29, fill="#f59e0b", width=1.2)
            cv.create_line(38, 19, 18, 29, fill="#f59e0b", width=1.2)

        elif nombre == "Zapata" or formulario == "zapata":
            cv.create_polygon(
                22, 8, 34, 8, 34, 20,
                48, 26, 48, 38, 8, 38, 8, 26,
                22, 20,
                fill="#94a3b8", outline="#1e293b", width=1.5
            )
            cv.create_line(11, 34, 45, 34, fill="#f59e0b", width=2)
            for rx in range(14, 44, 7):
                cv.create_oval(rx - 1.5, 32.5, rx + 1.5, 35.5, fill="#d97706", outline="")

        elif nombre == "Columna" or formulario == "columna":
            cv.create_rectangle(18, 7, 38, 39, fill="#cbd5e1", outline="#1e293b", width=1.5)
            cv.create_line(22, 5, 22, 41, fill="#d97706", width=1.8)
            cv.create_line(34, 5, 34, 41, fill="#d97706", width=1.8)
            for sy in (13, 21, 29, 36):
                cv.create_line(18, sy, 38, sy, fill="#475569", width=1.4)

        else:  # Viga o uso personalizado
            cv.create_rectangle(6, 13, 50, 29, fill="#cbd5e1", outline="#1e293b", width=1.5)
            cv.create_line(8, 17, 48, 17, fill="#d97706", width=1.6)
            cv.create_line(8, 25, 48, 25, fill="#d97706", width=1.8)
            for sx in (13, 21, 28, 35, 43):
                cv.create_line(sx, 13, sx, 29, fill="#475569", width=1.2)
            cv.create_polygon(10, 29, 6, 37, 14, 37, fill="#334155", outline="")
            cv.create_polygon(46, 29, 42, 37, 50, 37, fill="#334155", outline="")


# ---------------- Ventana de ilustración gráfica en obra ----------------
class VentanaIlustracion(tk.Toplevel):
    """Muestra cantidades y representación gráfica vectorial de baldes, carretillas y palas."""

    ESTILOS_MATERIAL = {
        "cemento": ("Cemento", "#4b5563", "#9ca3af", "#1f2937"),
        "arena":   ("Arena húmeda", "#d97706", "#fcd34d", "#78350f"),
        "grava":   ("Grava",   "#475569", "#94a3b8", "#1e293b"),
        "agua":    ("Agua neta", "#0284c7", "#7dd3fc", "#0c4a6e"),
    }

    def __init__(self, master, tipo_mezcla, resultado):
        super().__init__(master)
        self.title(f"Ilustración de unidades en obra — {tipo_mezcla}")
        self.geometry("1020x710")
        self.minsize(880, 560)
        self.configure(bg=C_FONDO)
        self.transient(master)

        self.tipo_mezcla = tipo_mezcla
        self.resultado = resultado
        self.modo_vista = tk.StringVar(value="tanda")
        self._construir_ui()

    def _construir_ui(self):
        cab = tk.Frame(self, bg=C_NAVY_OSC, padx=18, pady=12)
        cab.pack(fill="x")

        cv_casco = tk.Canvas(cab, width=68, height=46, bg=C_NAVY_OSC, highlightthickness=0)
        cv_casco.pack(side="left", padx=(0, 12))
        ArteIngenieria.dibujar_casco(cv_casco, 2, 2, escala=1.0)

        txt_cab = tk.Frame(cab, bg=C_NAVY_OSC)
        txt_cab.pack(side="left", fill="both", expand=True)
        tk.Label(
            txt_cab,
            text=f"Ilustración de herramientas en obra — {self.tipo_mezcla}",
            font=("Segoe UI", 14, "bold"),
            fg="white",
            bg=C_NAVY_OSC,
        ).pack(anchor="w")
        tk.Label(
            txt_cab,
            text=(
                f"Rendimiento/tanda: {self.resultado['v_tanda_l']:.1f} L   •   "
                f"Total tandas: {self.resultado['num_tandas']:g}   •   "
                "Balde = 20 L   •   Carretilla rasa = 60 L   •   Palada ≈ 4.5 L"
            ),
            font=("Segoe UI", 9),
            fg="#fde68a",
            bg=C_NAVY_OSC,
        ).pack(anchor="w", pady=(2, 0))

        # Selector Por Tanda vs Total Obra
        sw_frame = tk.Frame(cab, bg=C_NAVY_OSC)
        sw_frame.pack(side="right")
        tk.Radiobutton(
            sw_frame, text="Por Tanda (1 receta)", variable=self.modo_vista, value="tanda",
            indicatoron=0, font=("Segoe UI", 9, "bold"), bg=C_ACERO, fg="white",
            selectcolor=C_AMARILLO, padx=10, pady=6, command=self._actualizar_contenido
        ).pack(side="left", padx=3)
        tk.Radiobutton(
            sw_frame, text="Total Obra", variable=self.modo_vista, value="total",
            indicatoron=0, font=("Segoe UI", 9, "bold"), bg=C_ACERO, fg="white",
            selectcolor=C_AMARILLO, padx=10, pady=6, command=self._actualizar_contenido
        ).pack(side="left", padx=3)

        franja = tk.Canvas(self, height=6, bg=C_AMARILLO, highlightthickness=0)
        franja.pack(fill="x")
        for sx in range(-20, 1400, 24):
            franja.create_polygon(sx, 0, sx + 12, 0, sx + 6, 6, sx - 6, 6, fill=C_NAVY_OSC, outline="")

        self.resumen_frame = tk.Frame(self, bg=C_FONDO, padx=16, pady=10)
        self.resumen_frame.pack(fill="x")

        cont_scroll = tk.Frame(self, bg=C_FONDO, padx=16, pady=4)
        cont_scroll.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(cont_scroll, bg=C_FONDO, highlightthickness=0)
        scrollbar = ttk.Scrollbar(cont_scroll, orient="vertical", command=self.canvas.yview)
        self.scrollable = tk.Frame(self.canvas, bg=C_FONDO)

        self.scrollable.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        win_id = self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(win_id, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._actualizar_contenido()

        pie = tk.Frame(self, bg=C_FONDO, padx=16, pady=10)
        pie.pack(fill="x")
        tk.Label(
            pie,
            text="Nota: Se incluyen correcciones por abundamiento de arena húmeda y humedad libre de agregados. Si supera 14 íconos se agrupa (+N más).",
            font=("Segoe UI", 8),
            fg=C_SUBTEXTO,
            bg=C_FONDO,
        ).pack(side="left")
        ttk.Button(pie, text="Cerrar ilustración", command=self.destroy).pack(side="right")

    def _actualizar_contenido(self):
        for w in self.resumen_frame.winfo_children():
            w.destroy()
        for w in self.scrollable.winfo_children():
            w.destroy()

        es_tanda = self.modo_vista.get() == "tanda"
        h = self.resultado["herramientas_tanda"] if es_tanda else self.resultado["herramientas"]
        etiqueta_alcance = "en cada tanda" if es_tanda else f"en {self.resultado['num_tandas']:g} tandas"

        tot_baldes = sum(h[m][0] or 0.0 for m in h)
        tot_carretillas = sum(h[m][1] or 0.0 for m in h)
        tot_paladas = sum(h[m][2] or 0.0 for m in h)

        tarjetas = [
            (f"Baldes (20 L) {etiqueta_alcance}", f"{tot_baldes:.1f}", "Suma de cemento, arena, grava y agua", "#0284c7", "balde"),
            (f"Carretillas (60 L) {etiqueta_alcance}", f"{tot_carretillas:.1f}", "Transporte de arena húmeda y grava", "#d97706", "carretilla"),
            (f"Paladas (~4.5 L) {etiqueta_alcance}", f"{tot_paladas:.1f}", "Dosificación manual de materiales secos", "#4b5563", "pala"),
        ]
        for idx, (titulo, valor, sub, color, tipo_icono) in enumerate(tarjetas):
            self.resumen_frame.columnconfigure(idx, weight=1, uniform="card_res")
            card = tk.Frame(
                self.resumen_frame, bg="white",
                highlightbackground=C_BORDE, highlightthickness=1,
                padx=12, pady=8
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=6)

            icono_cv = tk.Canvas(card, width=54, height=44, bg="white", highlightthickness=0)
            icono_cv.pack(side="left", padx=(0, 10))
            if tipo_icono == "balde":
                self._dibujar_balde(icono_cv, 8, 6, 36, 34, color, "#bae6fd", "#0c4a6e", 1.0)
            elif tipo_icono == "carretilla":
                self._dibujar_carretilla(icono_cv, 4, 8, 46, 30, color, "#fde68a", "#78350f", 1.0)
            else:
                self._dibujar_pala(icono_cv, 10, 4, 34, 38, color, "#d1d5db", "#1f2937", 1.0)

            txt = tk.Frame(card, bg="white")
            txt.pack(side="left", fill="both", expand=True)
            tk.Label(txt, text=titulo, font=("Segoe UI", 9, "bold"), fg="#374151", bg="white").pack(anchor="w")
            tk.Label(txt, text=valor, font=("Segoe UI", 15, "bold"), fg=color, bg="white").pack(anchor="w")
            tk.Label(txt, text=sub, font=("Segoe UI", 8), fg="#6b7280", bg="white").pack(anchor="w")

        self._renderizar_materiales(h, es_tanda)

    def _renderizar_materiales(self, h, es_tanda):
        orden_mat = ["cemento", "arena", "grava", "agua"]
        for mat in orden_mat:
            nombre, c_princ, c_claro, c_oscuro = self.ESTILOS_MATERIAL[mat]
            baldes, carretillas, paladas = h[mat]

            if mat == "grava" and self.resultado["grava_m3"] == 0:
                card = tk.Frame(
                    self.scrollable, bg="white",
                    highlightbackground=C_BORDE, highlightthickness=1,
                    padx=14, pady=10
                )
                card.pack(fill="x", pady=6)
                tk.Label(
                    card,
                    text="Grava: No aplica para esta mezcla (Mortero sin agregado grueso).",
                    font=("Segoe UI", 10, "italic"),
                    fg="#6b7280",
                    bg="white",
                ).pack(anchor="w")
                continue

            card = tk.Frame(
                self.scrollable, bg="white",
                highlightbackground=C_BORDE, highlightthickness=1,
                padx=14, pady=10
            )
            card.pack(fill="x", pady=6)

            top = tk.Frame(card, bg="white")
            top.pack(fill="x", pady=(0, 6))

            muestra = tk.Canvas(top, width=14, height=14, bg="white", highlightthickness=0)
            muestra.create_oval(2, 2, 12, 12, fill=c_princ, outline=c_oscuro)
            muestra.pack(side="left", padx=(0, 6))

            tk.Label(top, text=nombre.upper(), font=("Segoe UI", 11, "bold"), fg=c_oscuro, bg="white").pack(side="left")
            tk.Label(
                top,
                text=self._subtitulo_material(mat, es_tanda),
                font=("Segoe UI", 9),
                fg="#4b5563",
                bg="white",
            ).pack(side="right")

            herramientas_mat = [
                ("balde", "Baldes (20 L)", baldes),
                ("carretilla", "Carretillas (60 L)", carretillas),
                ("pala", "Paladas (~4.5 L)", paladas),
            ]
            for tipo_h, etiqueta, cantidad in herramientas_mat:
                fila = tk.Frame(card, bg="#f8fafc", pady=5, padx=8)
                fila.pack(fill="x", pady=3)

                izq = tk.Frame(fila, bg="#f8fafc", width=210)
                izq.pack(side="left", fill="y")
                izq.pack_propagate(False)

                tk.Label(izq, text=etiqueta, font=("Segoe UI", 9, "bold"), fg="#1f2937", bg="#f8fafc").pack(anchor="w")
                val_txt = "No aplica en obra" if cantidad is None else f"{cantidad:.1f} unidades"
                tk.Label(
                    izq,
                    text=val_txt,
                    font=("Segoe UI", 10, "bold") if cantidad is not None else ("Segoe UI", 9, "italic"),
                    fg=c_princ if cantidad is not None else "#9ca3af",
                    bg="#f8fafc",
                ).pack(anchor="w")

                cv = tk.Canvas(fila, height=44, bg="#f8fafc", highlightthickness=0)
                cv.pack(side="left", fill="x", expand=True)

                if cantidad is None or cantidad <= 0:
                    cv.create_text(
                        12, 22, anchor="w",
                        text="— (Este material no se mide con esta herramienta)",
                        font=("Segoe UI", 8, "italic"),
                        fill="#9ca3af",
                    )
                else:
                    self._dibujar_serie_herramientas(cv, tipo_h, cantidad, c_princ, c_claro, c_oscuro)

    def _subtitulo_material(self, mat, es_tanda):
        r = self.resultado
        t = r["tanda"]
        if es_tanda:
            if mat == "cemento":
                return f"Por tanda: {r['bultos_por_tanda']:g} bulto ({t['cem_kg']:.1f} kg = {t['cem_l']:.1f} L sueltos)"
            if mat == "arena":
                return f"Por tanda: {t['are_obra_l']:.1f} L húmeda ({t['are_seca_l']:.1f} L seca = {t['are_kg']:.1f} kg)"
            if mat == "grava":
                return f"Por tanda: {t['gra_obra_l']:.1f} L ({t['gra_kg']:.1f} kg)"
            return f"Por tanda: {t['agua_l']:.1f} L netos a agregar"
        else:
            if mat == "cemento":
                return f"Total obra: {r['bultos']:g} bultos ({r['cemento_kg']:.1f} kg)"
            if mat == "arena":
                return f"Total obra: {r['arena_m3']:.3f} m³ húmeda ({r['arena_seca_m3']:.3f} m³ seca)"
            if mat == "grava":
                return f"Total obra: {r['grava_m3']:.3f} m³"
            return f"Total obra: {r['agua_l']:.1f} L netos"

    def _dibujar_serie_herramientas(self, cv, tipo_h, cantidad, c_princ, c_claro, c_oscuro):
        max_iconos = 14
        enteros = int(math.floor(cantidad + 1e-9))
        fraccion = max(0.0, cantidad - enteros)

        total_items = enteros + (1 if fraccion >= 0.15 else 0)
        agrupado = total_items > max_iconos

        if agrupado:
            n_dibujar = 10
            restantes = cantidad - n_dibujar
        else:
            n_dibujar = total_items
            restantes = 0.0

        ancho_paso = 42 if tipo_h == "carretilla" else 34
        x = 8
        for i in range(n_dibujar):
            nivel = 1.0
            if not agrupado and i == enteros and fraccion >= 0.15:
                nivel = min(1.0, fraccion)

            if tipo_h == "balde":
                self._dibujar_balde(cv, x, 5, 26, 32, c_princ, c_claro, c_oscuro, nivel)
            elif tipo_h == "carretilla":
                self._dibujar_carretilla(cv, x, 7, 36, 28, c_princ, c_claro, c_oscuro, nivel)
            else:
                self._dibujar_pala(cv, x, 3, 26, 36, c_princ, c_claro, c_oscuro, nivel)
            x += ancho_paso

        if agrupado:
            badge_w = 115
            cv.create_rectangle(
                x + 6, 9, x + 6 + badge_w, 35,
                fill=c_claro, outline=c_princ, width=1.5
            )
            cv.create_text(
                x + 6 + badge_w / 2, 22,
                text=f"+ {restantes:.1f} más",
                font=("Segoe UI", 9, "bold"),
                fill=c_oscuro,
            )

    def _dibujar_balde(self, cv, x, y, w, h, c_princ, c_claro, c_oscuro, nivel):
        cv.create_arc(
            x + w * 0.15, y, x + w * 0.85, y + h * 0.42,
            start=0, extent=180, style="arc", outline=c_oscuro, width=1.5
        )
        top_y = y + h * 0.22
        bot_y = y + h * 0.95
        x1_t, x2_t = x + w * 0.12, x + w * 0.88
        x1_b, x2_b = x + w * 0.24, x + w * 0.76

        cv.create_polygon(
            x1_t, top_y, x2_t, top_y, x2_b, bot_y, x1_b, bot_y,
            fill="#ffffff", outline=c_oscuro, width=1.4
        )
        if nivel > 0.05:
            fill_top = bot_y - (bot_y - top_y) * nivel
            t = (fill_top - top_y) / (bot_y - top_y)
            fx1 = x1_t + (x1_b - x1_t) * t
            fx2 = x2_t + (x2_b - x2_t) * t
            cv.create_polygon(
                fx1, fill_top, fx2, fill_top, x2_b, bot_y, x1_b, bot_y,
                fill=c_princ, outline=""
            )
        cv.create_polygon(
            x1_t, top_y, x2_t, top_y, x2_b, bot_y, x1_b, bot_y,
            fill="", outline=c_oscuro, width=1.4
        )
        cv.create_line(x + w * 0.08, top_y, x + w * 0.92, top_y, fill=c_oscuro, width=2)

    def _dibujar_carretilla(self, cv, x, y, w, h, c_princ, c_claro, c_oscuro, nivel):
        tx1, ty1 = x + w * 0.22, y + h * 0.18
        tx2, ty2 = x + w * 0.88, y + h * 0.18
        bx1, by1 = x + w * 0.34, y + h * 0.62
        bx2, by2 = x + w * 0.76, y + h * 0.62

        if nivel > 0.05:
            pico_y = ty1 - h * 0.16 * nivel
            cv.create_polygon(
                tx1 + 2, ty1,
                (tx1 + tx2) / 2, pico_y,
                tx2 - 2, ty2,
                fill=c_claro, outline=c_princ, width=1
            )

        cv.create_polygon(
            tx1, ty1, tx2, ty2, bx2, by2, bx1, by1,
            fill=c_princ if nivel >= 0.5 else c_claro,
            outline=c_oscuro,
            width=1.4,
        )
        cv.create_line(x + w * 0.04, y + h * 0.32, bx1, by1, fill=c_oscuro, width=2)
        cv.create_line(x + w * 0.36, by1, x + w * 0.32, y + h * 0.92, fill=c_oscuro, width=1.8)
        cv.create_line(x + w * 0.32, y + h * 0.92, x + w * 0.44, y + h * 0.92, fill=c_oscuro, width=1.8)
        cv.create_line(bx2, by2, x + w * 0.84, y + h * 0.75, fill=c_oscuro, width=1.8)
        r = h * 0.20
        cx, cy = x + w * 0.84, y + h * 0.76
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#374151", outline="#111827", width=1.5)
        cv.create_oval(cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35, fill="#d1d5db", outline="")

    def _dibujar_pala(self, cv, x, y, w, h, c_princ, c_claro, c_oscuro, nivel):
        cx = x + w * 0.5
        cv.create_rectangle(
            cx - w * 0.18, y + h * 0.04, cx + w * 0.18, y + h * 0.18,
            outline="#78350f", width=1.8, fill="#fef3c7"
        )
        cv.create_line(cx, y + h * 0.18, cx, y + h * 0.54, fill="#92400e", width=3)

        px1, py1 = x + w * 0.20, y + h * 0.52
        px2, py2 = x + w * 0.80, y + h * 0.52
        punta_y = y + h * 0.95
        cv.create_polygon(
            px1, py1, px2, py2,
            px2, y + h * 0.76,
            cx, punta_y,
            px1, y + h * 0.76,
            fill="#e5e7eb", outline="#374151", width=1.4
        )
        if nivel > 0.05:
            ry = py1 + (y + h * 0.76 - py1) * (1.0 - nivel * 0.85)
            cv.create_polygon(
                px1 + 2, ry, px2 - 2, ry,
                px2 - 2, y + h * 0.75,
                cx, punta_y - 2,
                px1 + 2, y + h * 0.75,
                fill=c_princ, outline=""
            )


# ---------------- Interfaz gráfica principal ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dosificador de Mezclas para Obra — Ingeniería Civil (NSR-10)")
        self.geometry("1180x780")
        self.minsize(1020, 680)
        self.configure(bg=C_FONDO)

        self.usos_mezcla, self.orden_usos = cargar_usos_desde_csv()
        self.tipo_mezcla = None
        self.es_mortero = False
        self.resultado = None
        self.entradas = []

        # Variables de geometría y parámetros
        self.vars_geo = {}
        self.var_forma_seccion = tk.StringVar(value="rectangular")
        self.var_tiene_pedestal = tk.BooleanVar(value=False)
        self.var_modo_prop = tk.StringVar(value="volumen")
        self.var_bultos_tanda = tk.StringVar(value="1")

        # Variables de propiedades físicas de materiales
        self.vars_props = {k: tk.StringVar(value=v) for k, v in PROPIEDADES_DEFECTO.items()}

        # Variables de recipiente especial
        self.var_recipiente = tk.StringVar(value="Balde estándar (20 L)")
        self.var_tipo_esp_rec = tk.StringVar(value="cajon")
        self.var_rec_l = tk.StringVar(value="30")
        self.var_rec_a = tk.StringVar(value="30")
        self.var_rec_h = tk.StringVar(value="25")
        self.var_rec_d = tk.StringVar(value="30")

        self._estilos()

        self.vista_inicio = tk.Frame(self, bg=C_FONDO)
        self.vista_calculadora = tk.Frame(self, bg=C_FONDO)

        self._construir_inicio()
        self._construir_calculadora()

        self.mostrar_inicio()

    def _estilos(self):
        s = ttk.Style(self)
        if "clam" in s.theme_names():
            s.theme_use("clam")
        s.configure("TFrame", background=C_FONDO)
        s.configure("Card.TLabelframe", background=C_BLANCO, bordercolor=C_BORDE)
        s.configure(
            "Card.TLabelframe.Label",
            background=C_BLANCO,
            font=("Segoe UI", 10, "bold"),
            foreground=C_NAVY,
        )
        s.configure("TLabel", background=C_BLANCO, font=("Segoe UI", 9), foreground=C_TEXTO)
        s.configure("Sub.TLabel", background=C_FONDO, font=("Segoe UI", 10), foreground=C_SUBTEXTO)
        s.configure("TButton", font=("Segoe UI", 9, "bold"), padding=6)
        s.configure("Accion.TButton", background="#2563eb", foreground="white")
        s.map("Accion.TButton", background=[("active", "#1d4ed8"), ("disabled", "#94a3b8")])
        s.configure("Ilustrar.TButton", background="#0f766e", foreground="white")
        s.map("Ilustrar.TButton", background=[("active", "#115e59"), ("disabled", "#94a3b8")])
        s.configure("TCheckbutton", background=C_BLANCO, font=("Segoe UI", 9, "bold"), foreground=C_NAVY)
        s.configure("TRadiobutton", background=C_BLANCO, font=("Segoe UI", 8, "bold"), foreground=C_NAVY)
        s.configure("TNotebook", background=C_FONDO)
        s.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=(12, 6))
        s.configure("Treeview", font=("Segoe UI", 9), rowheight=29, background=C_BLANCO, fieldbackground=C_BLANCO)
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e2e8f0", foreground=C_NAVY_OSC)

    def _crear_cinta_obra(self, padre):
        cinta = tk.Canvas(padre, height=7, bg=C_AMARILLO, highlightthickness=0)
        cinta.pack(fill="x")
        for sx in range(-20, 1600, 26):
            cinta.create_polygon(sx, 0, sx + 13, 0, sx + 6, 7, sx - 7, 7, fill=C_NAVY_OSC, outline="")

    # --- Pantalla 1: Selección de uso ---
    def _construir_inicio(self):
        for w in self.vista_inicio.winfo_children():
            w.destroy()

        banner = tk.Frame(self.vista_inicio, bg=C_NAVY_OSC, padx=26, pady=14)
        banner.pack(fill="x")

        izq_banner = tk.Frame(banner, bg=C_NAVY_OSC)
        izq_banner.pack(side="left", fill="both", expand=True)

        fila_titulo = tk.Frame(izq_banner, bg=C_NAVY_OSC)
        fila_titulo.pack(anchor="w")

        cv_casco = tk.Canvas(fila_titulo, width=72, height=48, bg=C_NAVY_OSC, highlightthickness=0)
        cv_casco.pack(side="left", padx=(0, 12))
        ArteIngenieria.dibujar_casco(cv_casco, 2, 3, escala=1.05)

        titulos = tk.Frame(fila_titulo, bg=C_NAVY_OSC)
        titulos.pack(side="left")
        tk.Label(
            titulos,
            text="INGENIERÍA CIVIL  •  VOLÚMENES ABSOLUTOS EN OBRA",
            font=("Segoe UI", 9, "bold"),
            fg=C_AMARILLO,
            bg=C_NAVY_OSC,
        ).pack(anchor="w")
        tk.Label(
            titulos,
            text="Dosificador de Mezclas de Concreto y Morteros",
            font=("Segoe UI", 19, "bold"),
            fg="white",
            bg=C_NAVY_OSC,
        ).pack(anchor="w")

        tk.Label(
            izq_banner,
            text="Receta por tanda, corrección por humedad/abundamiento de arena, cumplimiento NSR-10 y control de recipientes.",
            font=("Segoe UI", 10),
            fg="#cbd5e1",
            bg=C_NAVY_OSC,
        ).pack(anchor="w", pady=(8, 0))

        cv_obra = tk.Canvas(banner, width=308, height=112, bg=C_NAVY_OSC, highlightthickness=0)
        cv_obra.pack(side="right", padx=(12, 0))
        ArteIngenieria.dibujar_escena_obra(cv_obra, 0, 0)

        self._crear_cinta_obra(self.vista_inicio)

        contenedor = tk.Frame(self.vista_inicio, bg=C_FONDO, padx=26, pady=16)
        contenedor.pack(fill="both", expand=True)

        barra_sup = tk.Frame(contenedor, bg=C_FONDO)
        barra_sup.pack(fill="x", pady=(0, 10))
        tk.Label(
            barra_sup,
            text="Paso 1: Seleccione el uso o elemento constructivo a preparar:",
            font=("Segoe UI", 11, "bold"),
            fg=C_NAVY,
            bg=C_FONDO,
        ).pack(side="left")

        ttk.Button(
            barra_sup,
            text="Recargar usos desde CSV",
            command=self._recargar_csv_usos,
        ).pack(side="right")

        grid_cards = tk.Frame(contenedor, bg=C_FONDO)
        grid_cards.pack(fill="both", expand=True)

        for col in range(3):
            grid_cards.columnconfigure(col, weight=1, uniform="mezcla_col")

        for idx, nombre in enumerate(self.orden_usos):
            fila = idx // 3
            col = idx % 3
            grid_cards.rowconfigure(fila, weight=1)
            self._crear_tarjeta_mezcla(grid_cards, nombre, fila, col)

        pie = tk.Frame(contenedor, bg="#e2e8f0", padx=14, pady=8)
        pie.pack(fill="x", pady=(12, 0))
        tk.Label(
            pie,
            text=(
                f"Tabla editable vinculada: «{ARCHIVO_USOS_CSV}»  |  "
                "Recipientes al ras: Balde = 20 L • Carretilla = 60 L • Palada ≈ 4.5 L • Cajón/Cilindro especial"
            ),
            font=("Segoe UI", 9, "bold"),
            fg=C_NAVY,
            bg="#e2e8f0",
        ).pack(anchor="w")

    def _recargar_csv_usos(self):
        self.usos_mezcla, self.orden_usos = cargar_usos_desde_csv()
        self._construir_inicio()
        messagebox.showinfo("Tabla actualizada", f"Se cargaron {len(self.orden_usos)} usos desde «{ARCHIVO_USOS_CSV}».")

    def _crear_tarjeta_mezcla(self, padre, nombre, fila, col):
        info_uso = self.usos_mezcla[nombre]
        es_mortero = info_uso["es_mortero"]
        psi = info_uso["psi"]
        c, a = info_uso["cemento"], info_uso["arena"]
        etiqueta_tipo = f"MORTERO {c:g}:{a:g} (a/c {info_uso['rel_ac']:g})" if es_mortero else f"CONCRETO {psi} PSI"
        color_badge = "#fef3c7" if es_mortero else "#dbeafe"
        texto_badge = "#92400e" if es_mortero else "#1e40af"

        card = tk.Frame(
            padre,
            bg=C_BLANCO,
            highlightbackground=C_BORDE,
            highlightthickness=1,
            padx=14,
            pady=10,
            cursor="hand2",
        )
        card.grid(row=fila, column=col, sticky="nsew", padx=8, pady=6)

        cv_ico = tk.Canvas(card, width=56, height=46, bg=C_BLANCO, highlightthickness=0, cursor="hand2")
        cv_ico.pack(side="left", padx=(0, 12))
        ArteIngenieria.dibujar_icono_mezcla(cv_ico, nombre, info_uso["formulario"])

        info = tk.Frame(card, bg=C_BLANCO, cursor="hand2")
        info.pack(side="left", fill="both", expand=True)

        badge = tk.Label(
            info,
            text=etiqueta_tipo,
            font=("Segoe UI", 8, "bold"),
            bg=color_badge,
            fg=texto_badge,
            padx=6,
            pady=1,
            cursor="hand2",
        )
        badge.pack(anchor="w")

        lbl_nombre = tk.Label(
            info,
            text=nombre,
            font=("Segoe UI", 12, "bold"),
            fg=C_NAVY_OSC,
            bg=C_BLANCO,
            cursor="hand2",
        )
        lbl_nombre.pack(anchor="w", pady=(4, 2))

        lbl_go = tk.Label(
            info,
            text="Configurar y dosificar →",
            font=("Segoe UI", 9),
            fg=C_SUBTEXTO,
            bg=C_BLANCO,
            cursor="hand2",
        )
        lbl_go.pack(anchor="w")

        widgets = (card, cv_ico, info, badge, lbl_nombre, lbl_go)

        def al_entrar(_):
            card.configure(highlightbackground=C_AMARILLO, highlightthickness=2, bg="#fffbeb")
            cv_ico.configure(bg="#fffbeb")
            info.configure(bg="#fffbeb")
            lbl_nombre.configure(bg="#fffbeb")
            lbl_go.configure(bg="#fffbeb", fg="#b45309")

        def al_salir(_):
            card.configure(highlightbackground=C_BORDE, highlightthickness=1, bg=C_BLANCO)
            cv_ico.configure(bg=C_BLANCO)
            info.configure(bg=C_BLANCO)
            lbl_nombre.configure(bg=C_BLANCO)
            lbl_go.configure(bg=C_BLANCO, fg=C_SUBTEXTO)

        for w in widgets:
            w.bind("<Enter>", al_entrar)
            w.bind("<Leave>", al_salir)
            w.bind("<Button-1>", lambda _, n=nombre: self.seleccionar_mezcla(n))

    # --- Pantalla 2: Calculadora ---
    def _construir_calculadora(self):
        cabecera = tk.Frame(self.vista_calculadora, bg=C_NAVY_OSC, padx=18, pady=9)
        cabecera.pack(fill="x")

        btn_volver = tk.Button(
            cabecera,
            text="← Cambiar uso",
            font=("Segoe UI", 9, "bold"),
            bg=C_ACERO,
            fg="white",
            activebackground="#475569",
            activeforeground="white",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.mostrar_inicio,
        )
        btn_volver.pack(side="left", padx=(0, 14))

        self.cv_icono_cab = tk.Canvas(cabecera, width=56, height=44, bg=C_NAVY_OSC, highlightthickness=0)
        self.cv_icono_cab.pack(side="left", padx=(0, 10))

        tit_frame = tk.Frame(cabecera, bg=C_NAVY_OSC)
        tit_frame.pack(side="left")
        tk.Label(
            tit_frame,
            text="ASISTENTE DE DOSIFICACIÓN EN OBRA  •  MÉTODO DE VOLÚMENES ABSOLUTOS",
            font=("Segoe UI", 8, "bold"),
            fg=C_AMARILLO,
            bg=C_NAVY_OSC,
        ).pack(anchor="w")
        self.lbl_titulo_mezcla = tk.Label(
            tit_frame,
            text="",
            font=("Segoe UI", 15, "bold"),
            fg="white",
            bg=C_NAVY_OSC,
        )
        self.lbl_titulo_mezcla.pack(anchor="w")

        cv_casco_mini = tk.Canvas(cabecera, width=58, height=42, bg=C_NAVY_OSC, highlightthickness=0)
        cv_casco_mini.pack(side="right")
        ArteIngenieria.dibujar_casco(cv_casco_mini, 2, 2, escala=0.85)

        self._crear_cinta_obra(self.vista_calculadora)

        cuerpo = ttk.Frame(self.vista_calculadora)
        cuerpo.pack(fill="both", expand=True, padx=12, pady=6)
        cuerpo.columnconfigure(0, weight=0)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        # --- Panel izquierdo con pestañas: 1. Obra y Medidas | 2. Materiales y Recipiente ---
        panel_izq = tk.Frame(cuerpo, bg=C_FONDO, width=370)
        panel_izq.grid(row=0, column=0, sticky="nsew", padx=(2, 8), pady=2)
        panel_izq.pack_propagate(False)

        self.nb_izq = ttk.Notebook(panel_izq)
        self.nb_izq.pack(fill="both", expand=True)

        tab_obra = tk.Frame(self.nb_izq, bg=C_BLANCO, padx=10, pady=8)
        tab_mat = tk.Frame(self.nb_izq, bg=C_BLANCO, padx=10, pady=8)
        self.nb_izq.add(tab_obra, text="1. Medidas y Dosificación")
        self.nb_izq.add(tab_mat, text="2. Materiales y Recipiente")

        self._construir_tab_obra(tab_obra)
        self._construir_tab_materiales(tab_mat)

        # Botones fijos al pie del panel izquierdo
        pie_izq = tk.Frame(panel_izq, bg=C_FONDO, pady=6)
        pie_izq.pack(fill="x")
        pie_izq.columnconfigure(0, weight=2)
        pie_izq.columnconfigure(1, weight=1)

        ttk.Button(pie_izq, text="Calcular dosificación", style="Accion.TButton", command=self.calcular).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(pie_izq, text="Limpiar", command=self.limpiar).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

        # --- Panel derecho: Resultados completos ---
        res = ttk.LabelFrame(cuerpo, text="Resultados de obra, tarjeta por tanda y memoria", style="Card.TLabelframe", padding=12)
        res.grid(row=0, column=1, sticky="nsew", padx=(4, 2), pady=2)
        res.columnconfigure(0, weight=1)
        res.rowconfigure(3, weight=1)

        self.l_desc = ttk.Label(res, text="", wraplength=740)
        self.l_desc.grid(row=0, column=0, sticky="w", pady=(0, 6))

        # Resumen volumen y rendimiento
        caja_vol = tk.Frame(res, bg="#f8fafc", highlightbackground=C_BORDE, highlightthickness=1, padx=10, pady=6)
        caja_vol.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self.l_vol = tk.Label(
            caja_vol, text="Volumen de mezcla: —",
            font=("Segoe UI", 10, "bold"), fg=C_NAVY_OSC, bg="#f8fafc"
        )
        self.l_vol.pack(anchor="w")
        self.l_prop = tk.Label(caja_vol, text="", font=("Segoe UI", 9), fg=C_SUBTEXTO, bg="#f8fafc")
        self.l_prop.pack(anchor="w", pady=(1, 0))
        self.l_extra = tk.Label(caja_vol, text="", font=("Segoe UI", 9, "bold"), fg="#b45309", bg="#f8fafc")

        # Caja de alertas (desviaciones >5%, agua negativa, etc.)
        self.frame_alertas = tk.Frame(res, bg="#fef2f2", highlightbackground="#fca5a5", highlightthickness=1, padx=10, pady=6)
        self.lbl_alertas = tk.Label(
            self.frame_alertas, text="", font=("Segoe UI", 8, "bold"),
            fg="#991b1b", bg="#fef2f2", justify="left", wraplength=720
        )
        self.lbl_alertas.pack(anchor="w")

        # Notebook derecho: Tablas (Tarjeta + Pedido) vs Explicación paso a paso
        self.nb_res = ttk.Notebook(res)
        self.nb_res.grid(row=3, column=0, sticky="nsew", pady=(4, 6))

        tab_tablas = tk.Frame(self.nb_res, bg=C_BLANCO, padx=6, pady=6)
        tab_memoria = tk.Frame(self.nb_res, bg=C_BLANCO, padx=6, pady=6)
        self.nb_res.add(tab_tablas, text="Tarjeta de Mezcla y Pedido Total")
        self.nb_res.add(tab_memoria, text="Explicación Paso a Paso (Fórmulas)")

        # Subsección A: Tarjeta de mezcla por tanda
        self.lbl_titulo_tarjeta = tk.Label(
            tab_tablas, text="TARJETA DE MEZCLA POR TANDA (Receta para el maestro)",
            font=("Segoe UI", 9, "bold"), fg=C_NAVY, bg=C_BLANCO
        )
        self.lbl_titulo_tarjeta.pack(anchor="w", pady=(0, 3))

        cols_t = ("mat", "cant", "rec_ex", "rec_red", "desv")
        heads_t = ("Material", "Cantidad en tanda", "Recipientes exactos", "Recipientes (0.5)", "Desviación")
        widths_t = (115, 165, 130, 130, 90)
        self.tabla_tanda = ttk.Treeview(tab_tablas, columns=cols_t, show="headings", height=4)
        for c, t, w in zip(cols_t, heads_t, widths_t):
            self.tabla_tanda.heading(c, text=t)
            self.tabla_tanda.column(c, width=w, anchor="center" if c in ("rec_ex", "rec_red", "desv") else "w")
        self.tabla_tanda.pack(fill="x", pady=(0, 10))

        # Subsección B: Pedido total de materiales
        tk.Label(
            tab_tablas, text="PEDIDO TOTAL DE MATERIALES PARA LA OBRA",
            font=("Segoe UI", 9, "bold"), fg=C_NAVY, bg=C_BLANCO
        ).pack(anchor="w", pady=(0, 3))

        cols_p = ("mat", "pedir", "detalle")
        heads_p = ("Material", "Cantidad a pedir", "Detalle técnico y equivalencia")
        widths_p = (125, 195, 340)
        self.tabla_pedido = ttk.Treeview(tab_tablas, columns=cols_p, show="headings", height=4)
        for c, t, w in zip(cols_p, heads_p, widths_p):
            self.tabla_pedido.heading(c, text=t)
            self.tabla_pedido.column(c, width=w, anchor="w")
        self.tabla_pedido.pack(fill="x")

        # Contenido de la pestaña Memoria de cálculo
        self.txt_memoria = tk.Text(
            tab_memoria, font=("Consolas", 9), bg="#f8fafc", fg=C_NAVY_OSC,
            wrap="word", relief="flat", padx=8, pady=8
        )
        self.txt_memoria.pack(fill="both", expand=True)
        self.txt_memoria.insert("1.0", "Realice un cálculo para ver la memoria paso a paso con todas las fórmulas.")
        self.txt_memoria.configure(state="disabled")

        # Barra de botones de resultados
        barra_acciones = ttk.Frame(res)
        barra_acciones.grid(row=4, column=0, sticky="ew", pady=(4, 4))
        barra_acciones.columnconfigure(0, weight=1)
        barra_acciones.columnconfigure(1, weight=1)

        self.btn_ilustrar = ttk.Button(
            barra_acciones,
            text="Ver ilustración de unidades en obra",
            style="Ilustrar.TButton",
            command=self.ver_ilustracion,
            state="disabled",
        )
        self.btn_ilustrar.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_csv = ttk.Button(
            barra_acciones,
            text="Exportar reporte técnico a CSV",
            command=self.exportar,
            state="disabled",
        )
        self.btn_csv.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.l_estado = ttk.Label(res, text="Ingrese los datos y presione «Calcular dosificación».", wraplength=740)
        self.l_estado.grid(row=5, column=0, sticky="w", pady=(2, 0))

    def _construir_tab_obra(self, padre):
        padre.columnconfigure(0, weight=1)

        self.lbl_res = ttk.Label(padre, text="Resistencia de referencia (PSI)")
        self.lbl_res.grid(row=0, column=0, sticky="w")
        self.cb = ttk.Combobox(
            padre,
            state="readonly",
            values=[f"{k} PSI ({k * PSI_A_MPA:.1f} MPa)" for k in DOSIFICACIONES_CONCRETO],
        )
        self.cb.current(2)
        self.cb.grid(row=1, column=0, sticky="ew", pady=(2, 6))
        self.cb.bind("<<ComboboxSelected>>", lambda e: self._al_elegir_resistencia())

        # Contenedor dinámico para medidas según el uso
        self.frame_dim = tk.Frame(padre, bg=C_BLANCO)
        self.frame_dim.grid(row=2, column=0, sticky="ew")
        self.frame_dim.columnconfigure(0, weight=1)
        self.frame_dim.columnconfigure(1, weight=1)

        # Proporción en volumen o en peso
        sep = ttk.Separator(padre, orient="horizontal")
        sep.grid(row=3, column=0, sticky="ew", pady=8)

        fila_modo = tk.Frame(padre, bg=C_BLANCO)
        fila_modo.grid(row=4, column=0, sticky="ew")
        ttk.Label(fila_modo, text="Dosificación en:").pack(side="left", padx=(0, 6))
        ttk.Radiobutton(fila_modo, text="Volumen suelto", variable=self.var_modo_prop, value="volumen").pack(side="left", padx=4)
        ttk.Radiobutton(fila_modo, text="Peso", variable=self.var_modo_prop, value="peso").pack(side="left", padx=4)

        fila_prop = tk.Frame(padre, bg=C_BLANCO)
        fila_prop.grid(row=5, column=0, sticky="ew", pady=(4, 0))
        for idx, lbl in enumerate(("Cemento", "Arena", "Grava")):
            ttk.Label(fila_prop, text=lbl).grid(row=0, column=idx, padx=3)
        self.v_c, self.v_a, self.v_g = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for idx, v in enumerate((self.v_c, self.v_a, self.v_g)):
            ttk.Entry(fila_prop, textvariable=v, width=9, justify="center").grid(row=1, column=idx, padx=3)

        fila_ac = tk.Frame(padre, bg=C_BLANCO)
        fila_ac.grid(row=6, column=0, sticky="ew", pady=(6, 0))
        fila_ac.columnconfigure(0, weight=1)
        fila_ac.columnconfigure(1, weight=1)
        fila_ac.columnconfigure(2, weight=1)

        ttk.Label(fila_ac, text="Relación a/c").grid(row=0, column=0, sticky="w", padx=(0, 3))
        ttk.Label(fila_ac, text="Desperdicio (%)").grid(row=0, column=1, sticky="w", padx=3)
        ttk.Label(fila_ac, text="Bultos/tanda").grid(row=0, column=2, sticky="w", padx=(3, 0))

        self.v_ac = tk.StringVar(value="0.50")
        self.v_desp = tk.StringVar(value="5")
        ttk.Entry(fila_ac, textvariable=self.v_ac, width=8).grid(row=1, column=0, sticky="ew", padx=(0, 3))
        ttk.Entry(fila_ac, textvariable=self.v_desp, width=8).grid(row=1, column=1, sticky="ew", padx=3)
        self.cb_tanda = ttk.Combobox(fila_ac, textvariable=self.var_bultos_tanda, state="readonly", width=7, values=["1", "0.5", "2"])
        self.cb_tanda.grid(row=1, column=2, sticky="ew", padx=(3, 0))

    def _construir_tab_materiales(self, padre):
        padre.columnconfigure(0, weight=1)

        # Catálogo de recipientes
        ttk.Label(padre, text="Recipiente de medición en obra (al ras):", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.cb_recipiente = ttk.Combobox(
            padre, textvariable=self.var_recipiente, state="readonly",
            values=list(RECIPIENTES_ESTANDAR.keys())
        )
        self.cb_recipiente.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        self.cb_recipiente.bind("<<ComboboxSelected>>", lambda e: self._toggle_recipiente_especial())

        # Panel recipiente especial (oculto por defecto)
        self.frame_rec_esp = tk.Frame(padre, bg="#f8fafc", highlightbackground=C_BORDE, highlightthickness=1, padx=6, pady=6)
        fila_tipo_r = tk.Frame(self.frame_rec_esp, bg="#f8fafc")
        fila_tipo_r.pack(fill="x")
        ttk.Radiobutton(
            fila_tipo_r, text="Cajón (L×A×H cm)", variable=self.var_tipo_esp_rec,
            value="cajon", command=self._toggle_tipo_esp_rec
        ).pack(side="left", padx=4)
        ttk.Radiobutton(
            fila_tipo_r, text="Cilindro (D×H cm)", variable=self.var_tipo_esp_rec,
            value="cilindro", command=self._toggle_tipo_esp_rec
        ).pack(side="left", padx=4)

        self.frame_med_rec = tk.Frame(self.frame_rec_esp, bg="#f8fafc")
        self.frame_med_rec.pack(fill="x", pady=(4, 0))
        self._toggle_tipo_esp_rec()

        # Tabla compacta de propiedades físicas de los materiales
        ttk.Separator(padre, orient="horizontal").grid(row=3, column=0, sticky="ew", pady=8)
        ttk.Label(padre, text="Propiedades físicas de materiales y aire:", font=("Segoe UI", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=(0, 4)
        )

        grid_p = tk.Frame(padre, bg=C_BLANCO)
        grid_p.grid(row=5, column=0, sticky="ew")
        for c in range(4):
            grid_p.columnconfigure(c, weight=1)

        enc_p = ("Propiedad", "Cemento", "Arena", "Grava")
        for col, txt in enumerate(enc_p):
            tk.Label(grid_p, text=txt, font=("Segoe UI", 8, "bold"), bg="#e2e8f0", fg=C_NAVY_OSC, pady=2).grid(
                row=0, column=col, sticky="ew", padx=1, pady=1
            )

        filas_props = [
            ("ρ suelta (kg/m³)", "rho_cem", "rho_are", "rho_gra"),
            ("Dens. rel. G", "g_cem", "g_are", "g_gra"),
            ("Humedad (%)", None, "hum_are", "hum_gra"),
            ("Absorción (%)", None, "abs_are", "abs_gra"),
            ("Abundamiento", None, "fab_are", None),
        ]
        for r_idx, (etq, kc, ka, kg) in enumerate(filas_props, start=1):
            tk.Label(grid_p, text=etq, font=("Segoe UI", 8), bg="#f8fafc", anchor="w", padx=4).grid(
                row=r_idx, column=0, sticky="ew", padx=1, pady=1
            )
            for c_idx, clave in enumerate((kc, ka, kg), start=1):
                if clave is None:
                    tk.Label(grid_p, text="—", font=("Segoe UI", 8), bg=C_BLANCO, fg="#94a3b8").grid(
                        row=r_idx, column=c_idx, sticky="ew"
                    )
                else:
                    ttk.Entry(grid_p, textvariable=self.vars_props[clave], width=7, justify="center").grid(
                        row=r_idx, column=c_idx, padx=2, pady=1
                    )

        fila_aire = tk.Frame(padre, bg=C_BLANCO)
        fila_aire.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(fila_aire, text="Contenido de aire en mezcla (%):").pack(side="left")
        ttk.Entry(fila_aire, textvariable=self.vars_props["aire_pct"], width=7, justify="center").pack(side="left", padx=8)

        ttk.Button(
            padre,
            text="Restaurar propiedades de referencia",
            command=self._restaurar_propiedades,
        ).grid(row=7, column=0, sticky="ew", pady=(10, 0))

    def _toggle_recipiente_especial(self):
        if self.var_recipiente.get() == "Recipiente especial (definir medidas)":
            self.frame_rec_esp.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        else:
            self.frame_rec_esp.grid_forget()

    def _toggle_tipo_esp_rec(self):
        for w in self.frame_med_rec.winfo_children():
            w.destroy()
        if self.var_tipo_esp_rec.get() == "cajon":
            for idx, (lbl, var) in enumerate((("L (cm)", self.var_rec_l), ("A (cm)", self.var_rec_a), ("H (cm)", self.var_rec_h))):
                tk.Label(self.frame_med_rec, text=lbl, font=("Segoe UI", 8), bg="#f8fafc").grid(row=0, column=idx)
                ttk.Entry(self.frame_med_rec, textvariable=var, width=8, justify="center").grid(row=1, column=idx, padx=3)
        else:
            for idx, (lbl, var) in enumerate((("Diámetro D (cm)", self.var_rec_d), ("Altura H (cm)", self.var_rec_h))):
                tk.Label(self.frame_med_rec, text=lbl, font=("Segoe UI", 8), bg="#f8fafc").grid(row=0, column=idx)
                ttk.Entry(self.frame_med_rec, textvariable=var, width=11, justify="center").grid(row=1, column=idx, padx=4)

    def _restaurar_propiedades(self):
        for k, v in PROPIEDADES_DEFECTO.items():
            self.vars_props[k].set(v)

    def _construir_campos_geometria(self, formulario, esp_def):
        for w in self.frame_dim.winfo_children():
            w.destroy()
        self.vars_geo.clear()
        self.var_tiene_pedestal.set(False)
        self.var_forma_seccion.set("rectangular")

        def add_par(fila, clave1, lbl1, def1, clave2=None, lbl2=None, def2=None):
            ttk.Label(self.frame_dim, text=lbl1).grid(row=fila * 2, column=0, sticky="w", pady=(4, 0), padx=(0, 3))
            v1 = tk.StringVar(value=def1)
            self.vars_geo[clave1] = v1
            if clave2 is None:
                ttk.Entry(self.frame_dim, textvariable=v1).grid(row=fila * 2 + 1, column=0, columnspan=2, sticky="ew")
            else:
                ttk.Entry(self.frame_dim, textvariable=v1, width=13).grid(row=fila * 2 + 1, column=0, sticky="ew", padx=(0, 3))
                ttk.Label(self.frame_dim, text=lbl2).grid(row=fila * 2, column=1, sticky="w", pady=(4, 0), padx=(3, 0))
                v2 = tk.StringVar(value=def2)
                self.vars_geo[clave2] = v2
                ttk.Entry(self.frame_dim, textvariable=v2, width=13).grid(row=fila * 2 + 1, column=1, sticky="ew", padx=(3, 0))

        if formulario == "pega_bloques":
            add_par(0, "largo_pared", "Largo pared (m)", "4.0", "alto_pared", "Altura pared (m)", "2.5")
            add_par(1, "largo_bloque", "Largo bloque (m)", "0.39", "alto_bloque", "Alto bloque (m)", "0.19")
            add_par(2, "esp_bloque", "Espesor bloque (m)", "0.14", "esp_junta_cm", "Espesor juntas (cm)", esp_def)
            add_par(3, "cant", "Número de paredes iguales", "1")

        elif formulario == "repello":
            add_par(0, "largo_sup", "Largo superficie (m)", "4.0", "alto_sup", "Altura superficie (m)", "2.5")
            add_par(1, "esp_panete_cm", "Espesor pañete (cm)", esp_def, "num_caras", "Caras a pañetar", "1")
            add_par(2, "cant", "Número de superficies iguales", "1")

        elif formulario == "nivelacion":
            add_par(0, "largo_piso", "Largo del piso (m)", "4.0", "ancho_piso", "Ancho del piso (m)", "3.0")
            add_par(1, "esp_niv_cm", "Espesor nivelación (cm)", esp_def, "cant", "Número de áreas iguales", "1")

        elif formulario == "zapata":
            add_par(0, "largo_base", "Largo base (m)", "1.20", "ancho_base", "Ancho base (m)", "1.20")
            add_par(1, "alto_zapata", "Altura zapata (m)", esp_def, "cant", "Zapatas iguales", "1")

            chk = ttk.Checkbutton(
                self.frame_dim, text="Incluir pedestal en la zapata",
                variable=self.var_tiene_pedestal, command=self._toggle_pedestal
            )
            chk.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 2))

            self.frame_pedestal = tk.Frame(self.frame_dim, bg="#f8fafc", highlightbackground=C_BORDE, highlightthickness=1, padx=6, pady=4)
            self.frame_pedestal.columnconfigure(0, weight=1)
            self.frame_pedestal.columnconfigure(1, weight=1)
            ttk.Label(self.frame_pedestal, text="Largo ped. (m)", background="#f8fafc").grid(row=0, column=0, sticky="w")
            ttk.Label(self.frame_pedestal, text="Ancho ped. (m)", background="#f8fafc").grid(row=0, column=1, sticky="w")
            self.vars_geo["largo_ped"] = tk.StringVar(value="0.35")
            self.vars_geo["ancho_ped"] = tk.StringVar(value="0.35")
            ttk.Entry(self.frame_pedestal, textvariable=self.vars_geo["largo_ped"], width=11).grid(row=1, column=0, sticky="ew", padx=(0, 3))
            ttk.Entry(self.frame_pedestal, textvariable=self.vars_geo["ancho_ped"], width=11).grid(row=1, column=1, sticky="ew", padx=(3, 0))
            ttk.Label(self.frame_pedestal, text="Altura pedestal (m)", background="#f8fafc").grid(row=2, column=0, columnspan=2, sticky="w", pady=(3, 0))
            self.vars_geo["alto_ped"] = tk.StringVar(value="0.80")
            ttk.Entry(self.frame_pedestal, textvariable=self.vars_geo["alto_ped"]).grid(row=3, column=0, columnspan=2, sticky="ew")

        elif formulario == "columna":
            fila_s = tk.Frame(self.frame_dim, bg=C_BLANCO)
            fila_s.grid(row=0, column=0, columnspan=2, sticky="w", pady=(2, 2))
            ttk.Radiobutton(
                fila_s, text="Rectangular (b×h)", variable=self.var_forma_seccion,
                value="rectangular", command=lambda: self._render_campos_columna(esp_def)
            ).pack(side="left", padx=(0, 6))
            ttk.Radiobutton(
                fila_s, text="Circular (π·D²·H/4)", variable=self.var_forma_seccion,
                value="circular", command=lambda: self._render_campos_columna(esp_def)
            ).pack(side="left")

            self.sub_col = tk.Frame(self.frame_dim, bg=C_BLANCO)
            self.sub_col.grid(row=1, column=0, columnspan=2, sticky="ew")
            self.sub_col.columnconfigure(0, weight=1)
            self.sub_col.columnconfigure(1, weight=1)
            self._render_campos_columna(esp_def)

        else:
            add_par(0, "largo", "Largo (m)", "4.0", "ancho", "Ancho (m)", "3.0")
            add_par(1, "espesor", "Espesor / altura (m)", esp_def, "cant", "Elementos iguales", "1")

    def _render_campos_columna(self, esp_def):
        for w in self.sub_col.winfo_children():
            w.destroy()
        if self.var_forma_seccion.get() == "rectangular":
            ttk.Label(self.sub_col, text="Base b (m)").grid(row=0, column=0, sticky="w")
            ttk.Label(self.sub_col, text="Lado h (m)").grid(row=0, column=1, sticky="w")
            self.vars_geo["col_b"] = tk.StringVar(value="0.30")
            self.vars_geo["col_h"] = tk.StringVar(value="0.30")
            ttk.Entry(self.sub_col, textvariable=self.vars_geo["col_b"], width=12).grid(row=1, column=0, sticky="ew", padx=(0, 3))
            ttk.Entry(self.sub_col, textvariable=self.vars_geo["col_h"], width=12).grid(row=1, column=1, sticky="ew", padx=(3, 0))
        else:
            ttk.Label(self.sub_col, text="Diámetro D (m)").grid(row=0, column=0, columnspan=2, sticky="w")
            self.vars_geo["col_d"] = tk.StringVar(value="0.35")
            ttk.Entry(self.sub_col, textvariable=self.vars_geo["col_d"]).grid(row=1, column=0, columnspan=2, sticky="ew")

        ttk.Label(self.sub_col, text="Altura H (m)").grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(self.sub_col, text="Columnas iguales").grid(row=2, column=1, sticky="w", pady=(4, 0))
        self.vars_geo["col_alt"] = tk.StringVar(value=esp_def)
        self.vars_geo["cant"] = tk.StringVar(value="1")
        ttk.Entry(self.sub_col, textvariable=self.vars_geo["col_alt"], width=12).grid(row=3, column=0, sticky="ew", padx=(0, 3))
        ttk.Entry(self.sub_col, textvariable=self.vars_geo["cant"], width=12).grid(row=3, column=1, sticky="ew", padx=(3, 0))

    def _toggle_pedestal(self):
        if not hasattr(self, "frame_pedestal"):
            return
        if self.var_tiene_pedestal.get():
            self.frame_pedestal.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(2, 2))
        else:
            self.frame_pedestal.grid_forget()

    def _al_elegir_resistencia(self):
        if self.es_mortero:
            return
        psi = int(self.cb.get().split()[0])
        c, a, g, ac = DOSIFICACIONES_CONCRETO[psi]
        self.v_c.set(f"{c:g}")
        self.v_a.set(f"{a:g}")
        self.v_g.set(f"{g:g}")
        self.v_ac.set(f"{ac:g}")

    # --- Navegación y acciones ---
    def mostrar_inicio(self):
        self.vista_calculadora.pack_forget()
        self.vista_inicio.pack(fill="both", expand=True)

    def seleccionar_mezcla(self, nombre):
        self.tipo_mezcla = nombre
        info = self.usos_mezcla[nombre]
        self.es_mortero = info["es_mortero"]

        self.lbl_titulo_mezcla.configure(text=nombre)
        self.l_desc.configure(text=info["descripcion"])

        self.cv_icono_cab.delete("all")
        self.cv_icono_cab.create_rectangle(2, 2, 54, 42, fill=C_BLANCO, outline=C_AMARILLO, width=1.5)
        ArteIngenieria.dibujar_icono_mezcla(self.cv_icono_cab, nombre, info["formulario"])

        if self.es_mortero:
            self.lbl_res.configure(text="Tipo de mezcla (Mortero)")
            self.cb.configure(state="disabled")
            self.cb.set(f"Mortero {info['cemento']:g}:{info['arena']:g} (a/c {info['rel_ac']:g})")
            self.cb_tanda.configure(values=["1", "0.5"])
        else:
            self.lbl_res.configure(text="Resistencia de referencia (PSI)")
            self.cb.configure(
                state="readonly",
                values=[f"{k} PSI ({k * PSI_A_MPA:.1f} MPa)" for k in DOSIFICACIONES_CONCRETO],
            )
            claves_psi = list(DOSIFICACIONES_CONCRETO.keys())
            if info["psi"] in claves_psi:
                self.cb.current(claves_psi.index(info["psi"]))
            self.cb_tanda.configure(values=["1", "2"])

        self.var_bultos_tanda.set("1")
        self._construir_campos_geometria(info["formulario"], info["espesor_def"])

        self.v_c.set(f"{info['cemento']:g}")
        self.v_a.set(f"{info['arena']:g}")
        self.v_g.set(f"{info['grava']:g}")
        self.v_ac.set(f"{info['rel_ac']:g}")
        self.v_desp.set("5")

        self.resultado = None
        self.tabla_tanda.delete(*self.tabla_tanda.get_children())
        self.tabla_pedido.delete(*self.tabla_pedido.get_children())
        self.l_vol.configure(text="Volumen de mezcla: —")
        self.l_prop.configure(text="")
        self.l_extra.pack_forget()
        self.frame_alertas.grid_forget()
        self.btn_ilustrar.configure(state="disabled")
        self.btn_csv.configure(state="disabled")
        self._estado("Ingrese los datos y presione «Calcular dosificación».")

        self.vista_inicio.pack_forget()
        self.vista_calculadora.pack(fill="both", expand=True)

    def _estado(self, texto, color="#111827"):
        self.l_estado.configure(text=texto, foreground=color)

    def _obtener_capacidad_recipiente(self):
        sel = self.var_recipiente.get()
        if RECIPIENTES_ESTANDAR[sel] is not None:
            return RECIPIENTES_ESTANDAR[sel], sel
        if self.var_tipo_esp_rec.get() == "cajon":
            l_cm = leer_numero(self.var_rec_l.get(), "Largo recipiente (cm)", minimo=5, maximo=300)
            a_cm = leer_numero(self.var_rec_a.get(), "Ancho recipiente (cm)", minimo=5, maximo=300)
            h_cm = leer_numero(self.var_rec_h.get(), "Alto recipiente (cm)", minimo=5, maximo=300)
            cap_l = (l_cm * a_cm * h_cm) / 1000.0
            return cap_l, f"Cajón {l_cm:g}×{a_cm:g}×{h_cm:g} cm ({cap_l:.1f} L)"
        else:
            d_cm = leer_numero(self.var_rec_d.get(), "Diámetro recipiente (cm)", minimo=5, maximo=300)
            h_cm = leer_numero(self.var_rec_h.get(), "Altura recipiente (cm)", minimo=5, maximo=300)
            cap_l = (math.pi * (d_cm ** 2) * h_cm / 4.0) / 1000.0
            return cap_l, f"Cilindro D={d_cm:g}×H={h_cm:g} cm ({cap_l:.1f} L)"

    def _calcular_volumen_segun_uso(self, desp):
        formulario = self.usos_mezcla[self.tipo_mezcla]["formulario"]
        entradas_geo = []
        detalle_extra = ""

        if formulario == "pega_bloques":
            lp = leer_numero(self.vars_geo["largo_pared"].get(), "Largo de la pared", maximo=1000)
            hp = leer_numero(self.vars_geo["alto_pared"].get(), "Altura de la pared", maximo=100)
            lb = leer_numero(self.vars_geo["largo_bloque"].get(), "Largo del bloque", minimo=0.05, maximo=2.0)
            hb = leer_numero(self.vars_geo["alto_bloque"].get(), "Alto del bloque", minimo=0.05, maximo=2.0)
            eb = leer_numero(self.vars_geo["esp_bloque"].get(), "Espesor del bloque", minimo=0.03, maximo=1.0)
            ej_cm = leer_numero(self.vars_geo["esp_junta_cm"].get(), "Espesor de juntas (cm)", minimo=0.2, maximo=10.0)
            cant = leer_numero(self.vars_geo["cant"].get(), "Número de paredes iguales", maximo=10000)
            if cant != int(cant):
                raise ErrorValidacion("«Número de paredes iguales» debe ser un entero.")
            cant = int(cant)

            ej_m = ej_cm / 100.0
            area_paredes = lp * hp * cant
            area_mod = (lb + ej_m) * (hb + ej_m)
            fraccion_junta = 1.0 - ((lb * hb) / area_mod)
            v_geom = area_paredes * fraccion_junta * eb
            bloques_netos = area_paredes / area_mod
            bloques_pedir = math.ceil(bloques_netos * (1 + desp / 100))

            detalle_extra = (
                f"Área muro: {area_paredes:.2f} m²  |  Bloques: {bloques_netos:.0f} und. "
                f"({bloques_pedir} und. con {desp:g}% desperdicio)"
            )
            entradas_geo = [
                ("Largo pared (m)", f"{lp:g}"), ("Altura pared (m)", f"{hp:g}"),
                ("Bloque L×H×E (m)", f"{lb:g}×{hb:g}×{eb:g}"), ("Espesor juntas (cm)", f"{ej_cm:g}"),
                ("Paredes iguales", f"{cant}"), ("Bloques con desperdicio", f"{bloques_pedir}"),
            ]

        elif formulario == "repello":
            ls = leer_numero(self.vars_geo["largo_sup"].get(), "Largo de la superficie", maximo=1000)
            hs = leer_numero(self.vars_geo["alto_sup"].get(), "Altura de la superficie", maximo=100)
            ep_cm = leer_numero(self.vars_geo["esp_panete_cm"].get(), "Espesor del pañete (cm)", minimo=0.2, maximo=15.0)
            caras = leer_numero(self.vars_geo["num_caras"].get(), "Número de caras a pañetar", maximo=10)
            cant = leer_numero(self.vars_geo["cant"].get(), "Número de superficies iguales", maximo=10000)
            if caras != int(caras) or cant != int(cant):
                raise ErrorValidacion("Caras y superficies deben ser números enteros.")
            caras, cant = int(caras), int(cant)

            area_total = ls * hs * caras * cant
            v_geom = area_total * (ep_cm / 100.0)
            detalle_extra = f"Área total a pañetar: {area_total:.2f} m² (espesor {ep_cm:g} cm)"
            entradas_geo = [
                ("Largo superficie (m)", f"{ls:g}"), ("Altura superficie (m)", f"{hs:g}"),
                ("Espesor panete (cm)", f"{ep_cm:g}"), ("Caras", f"{caras}"), ("Superficies iguales", f"{cant}"),
            ]

        elif formulario == "nivelacion":
            lp = leer_numero(self.vars_geo["largo_piso"].get(), "Largo del piso", maximo=1000)
            ap = leer_numero(self.vars_geo["ancho_piso"].get(), "Ancho del piso", maximo=1000)
            en_cm = leer_numero(self.vars_geo["esp_niv_cm"].get(), "Espesor de nivelación (cm)", minimo=0.5, maximo=30.0)
            cant = leer_numero(self.vars_geo["cant"].get(), "Número de áreas iguales", maximo=10000)
            if cant != int(cant):
                raise ErrorValidacion("«Número de áreas iguales» debe ser un entero.")
            cant = int(cant)

            area_total = lp * ap * cant
            v_geom = area_total * (en_cm / 100.0)
            detalle_extra = f"Área total de piso: {area_total:.2f} m² (espesor {en_cm:g} cm)"
            entradas_geo = [
                ("Largo piso (m)", f"{lp:g}"), ("Ancho piso (m)", f"{ap:g}"),
                ("Espesor nivelacion (cm)", f"{en_cm:g}"), ("Areas iguales", f"{cant}"),
            ]

        elif formulario == "zapata":
            lb = leer_numero(self.vars_geo["largo_base"].get(), "Largo de la base", maximo=100)
            ab = leer_numero(self.vars_geo["ancho_base"].get(), "Ancho de la base", maximo=100)
            hz = leer_numero(self.vars_geo["alto_zapata"].get(), "Altura de la zapata", maximo=20)
            cant = leer_numero(self.vars_geo["cant"].get(), "Zapatas iguales", maximo=10000)
            if cant != int(cant):
                raise ErrorValidacion("«Zapatas iguales» debe ser un entero.")
            cant = int(cant)

            v_base = lb * ab * hz
            v_ped = 0.0
            entradas_geo = [
                ("Base zapata L×A×H (m)", f"{lb:g}×{ab:g}×{hz:g}"), ("Zapatas iguales", f"{cant}")
            ]
            if self.var_tiene_pedestal.get():
                lp_ped = leer_numero(self.vars_geo["largo_ped"].get(), "Largo pedestal", maximo=20)
                ap_ped = leer_numero(self.vars_geo["ancho_ped"].get(), "Ancho pedestal", maximo=20)
                hp_ped = leer_numero(self.vars_geo["alto_ped"].get(), "Altura pedestal", maximo=20)
                v_ped = lp_ped * ap_ped * hp_ped
                detalle_extra = f"Bases: {v_base * cant:.3f} m³  +  Pedestales: {v_ped * cant:.3f} m³"
                entradas_geo.append(("Pedestal L×A×H (m)", f"{lp_ped:g}×{ap_ped:g}×{hp_ped:g}"))
            v_geom = (v_base + v_ped) * cant

        elif formulario == "columna":
            alt = leer_numero(self.vars_geo["col_alt"].get(), "Altura de columna", maximo=100)
            cant = leer_numero(self.vars_geo["cant"].get(), "Columnas iguales", maximo=10000)
            if cant != int(cant):
                raise ErrorValidacion("«Columnas iguales» debe ser un entero.")
            cant = int(cant)
            if self.var_forma_seccion.get() == "rectangular":
                b = leer_numero(self.vars_geo["col_b"].get(), "Base b", maximo=20)
                h = leer_numero(self.vars_geo["col_h"].get(), "Lado h", maximo=20)
                v_geom = b * h * alt * cant
                entradas_geo = [("Seccion rectangular (m)", f"{b:g}×{h:g}"), ("Altura (m)", f"{alt:g}"), ("Cantidad", f"{cant}")]
            else:
                d = leer_numero(self.vars_geo["col_d"].get(), "Diámetro D", maximo=20)
                v_geom = (math.pi * (d ** 2) * alt / 4.0) * cant
                detalle_extra = f"Columna cilíndrica D = {d:g} m, H = {alt:g} m (π·D²·H/4)"
                entradas_geo = [("Seccion circular D (m)", f"{d:g}"), ("Altura (m)", f"{alt:g}"), ("Cantidad", f"{cant}")]

        else:
            largo = leer_numero(self.vars_geo["largo"].get(), "Largo", maximo=1000)
            ancho = leer_numero(self.vars_geo["ancho"].get(), "Ancho", maximo=1000)
            esp = leer_numero(self.vars_geo["espesor"].get(), "Espesor / altura", maximo=100)
            cant = leer_numero(self.vars_geo["cant"].get(), "Elementos iguales", maximo=10000)
            if cant != int(cant):
                raise ErrorValidacion("«Elementos iguales» debe ser un entero.")
            cant = int(cant)
            v_geom = largo * ancho * esp * cant
            entradas_geo = [("Dimensiones L×A×E (m)", f"{largo:g}×{ancho:g}×{esp:g}"), ("Cantidad", f"{cant}")]

        return v_geom, entradas_geo, detalle_extra

    def calcular(self):
        if not self.es_mortero:
            psi_sel = int(self.cb.get().split()[0])
            if self.tipo_mezcla in ELEMENTOS_ESTRUCTURALES_BLOQUEADO_2000 and psi_sel == 2000:
                self.resultado = None
                self.tabla_tanda.delete(*self.tabla_tanda.get_children())
                self.tabla_pedido.delete(*self.tabla_pedido.get_children())
                self.l_vol.configure(text="Volumen de mezcla: —")
                self.l_prop.configure(text="")
                self.l_extra.pack_forget()
                self.frame_alertas.grid_forget()
                self.btn_ilustrar.configure(state="disabled")
                self.btn_csv.configure(state="disabled")
                self._estado(f"⚠ {MENSAJE_NSR10_2000}", "#b91c1c")
                messagebox.showwarning("Restricción NSR-10", MENSAJE_NSR10_2000)
                return

        try:
            c = leer_numero(self.v_c.get(), "Partes de cemento", maximo=100)
            a = leer_numero(self.v_a.get(), "Partes de arena", maximo=100)
            g = leer_numero(self.v_g.get(), "Partes de grava", maximo=100, permitir_cero=True)
            ac = leer_numero(self.v_ac.get(), "Relación a/c", minimo=0.20, maximo=1.5)
            desp = leer_numero(self.v_desp.get(), "Desperdicio (%)", maximo=50, permitir_cero=True)
            bultos_tanda = float(self.var_bultos_tanda.get())

            props = {
                "rho_cem": leer_numero(self.vars_props["rho_cem"].get(), "ρ suelta cemento", minimo=500, maximo=2500),
                "g_cem": leer_numero(self.vars_props["g_cem"].get(), "G cemento", minimo=1.5, maximo=4.5),
                "rho_are": leer_numero(self.vars_props["rho_are"].get(), "ρ suelta arena", minimo=800, maximo=2500),
                "g_are": leer_numero(self.vars_props["g_are"].get(), "G arena", minimo=1.5, maximo=4.0),
                "hum_are": leer_numero(self.vars_props["hum_are"].get(), "Humedad arena (%)", minimo=0, maximo=30, permitir_cero=True),
                "abs_are": leer_numero(self.vars_props["abs_are"].get(), "Absorción arena (%)", minimo=0, maximo=15, permitir_cero=True),
                "fab_are": leer_numero(self.vars_props["fab_are"].get(), "Abundamiento arena", minimo=1.0, maximo=2.0),
                "rho_gra": leer_numero(self.vars_props["rho_gra"].get(), "ρ suelta grava", minimo=800, maximo=2500),
                "g_gra": leer_numero(self.vars_props["g_gra"].get(), "G grava", minimo=1.5, maximo=4.0),
                "hum_gra": leer_numero(self.vars_props["hum_gra"].get(), "Humedad grava (%)", minimo=0, maximo=20, permitir_cero=True),
                "abs_gra": leer_numero(self.vars_props["abs_gra"].get(), "Absorción grava (%)", minimo=0, maximo=15, permitir_cero=True),
                "aire_pct": leer_numero(self.vars_props["aire_pct"].get(), "Aire (%)", minimo=0, maximo=15, permitir_cero=True),
            }
            cap_rec_l, nombre_rec = self._obtener_capacidad_recipiente()
            v_geom, entradas_geo, detalle_extra = self._calcular_volumen_segun_uso(desp)
        except ErrorValidacion as err:
            self._estado(f"⚠ {err}", "#b91c1c")
            messagebox.showwarning("Dato no válido", str(err))
            return

        r = calcular_mezcla_volumenes_absolutos(
            v_geom, desp, c, a, g, self.var_modo_prop.get(), ac,
            bultos_tanda, props, cap_rec_l, nombre_rec,
            es_mortero=self.es_mortero, detalle_extra=detalle_extra
        )
        self.resultado = r
        self.entradas = [("Uso / Clasificacion", self.cb.get())] + entradas_geo + [
            ("Modo dosificacion", self.var_modo_prop.get()),
            ("Proporcion normalizada vol.", r["prop_vol_str"]),
            ("Proporcion normalizada peso", r["prop_peso_str"]),
            ("Relacion a/c", f"{ac:g}"),
            ("Desperdicio (%)", f"{desp:g}"),
            ("Recipiente elegido", nombre_rec),
        ]

        self.l_vol.configure(
            text=f"Volumen geométrico: {r['v_geom']:.3f} m³  |  Con {desp:g}% desperdicio: {r['v_total']:.3f} m³  "
                 f"→  Producido ({r['num_tandas']:g} tandas): {r['v_producido_real']:.3f} m³"
        )
        self.l_prop.configure(
            text=f"Proporción vol.: {r['prop_vol_str']}  |  Peso: {r['prop_peso_str']}  |  "
                 f"Rendimiento: {r['v_tanda_l']:.2f} L/tanda ({r['bultos_por_m3']:.2f} bultos/m³)"
        )

        if detalle_extra:
            self.l_extra.configure(text=detalle_extra)
            self.l_extra.pack(anchor="w", pady=(2, 0))
        else:
            self.l_extra.pack_forget()

        # Mostrar alertas si existen
        if r["alertas"]:
            self.lbl_alertas.configure(text="⚠ " + "\n⚠ ".join(r["alertas"]))
            self.frame_alertas.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        else:
            self.frame_alertas.grid_forget()

        # Llenar Tarjeta de Mezcla por Tanda
        t = r["tanda"]
        self.lbl_titulo_tarjeta.configure(
            text=f"TARJETA DE MEZCLA POR TANDA ({bultos_tanda:g} bulto)  •  Recipiente: {nombre_rec}"
        )
        self.tabla_tanda.delete(*self.tabla_tanda.get_children())
        self.tabla_tanda.insert("", "end", values=(
            "Cemento", f"{t['cem_kg']:.1f} kg ({t['cem_l']:.1f} L)", f"{bultos_tanda:g} bulto", f"{bultos_tanda:g} bulto", "0.0%"
        ))
        self.tabla_tanda.insert("", "end", values=(
            "Arena húmeda", f"{t['are_obra_l']:.1f} L (f_ab={props['fab_are']:g})",
            f"{t['are_rec_ex']:.2f}", f"{t['are_rec_red']:g}", f"{t['are_desv']:+.1f}%"
        ))
        if t["gra_obra_l"] > 0:
            self.tabla_tanda.insert("", "end", values=(
                "Grava", f"{t['gra_obra_l']:.1f} L",
                f"{t['gra_rec_ex']:.2f}", f"{t['gra_rec_red']:g}", f"{t['gra_desv']:+.1f}%"
            ))
        self.tabla_tanda.insert("", "end", values=(
            "Agua a agregar", f"{t['agua_l']:.1f} L (corregida)",
            f"{t['agu_rec_ex']:.2f}", f"{t['agu_rec_red']:g}", f"{t['agu_desv']:+.1f}%"
        ))

        # Llenar Pedido Total de Materiales
        self.tabla_pedido.delete(*self.tabla_pedido.get_children())
        self.tabla_pedido.insert("", "end", values=(
            "Cemento", f"{r['bultos']:g} bultos de 50 kg",
            f"{r['cemento_kg']:.1f} kg totales (cálculo exacto: {r['bultos_exactos']:.2f} bultos)"
        ))
        self.tabla_pedido.insert("", "end", values=(
            "Arena húmeda", f"{r['arena_m3']:.3f} m³",
            f"Con abundamiento {props['fab_are']:g} (equivale a {r['arena_seca_m3']:.3f} m³ seca)"
        ))
        self.tabla_pedido.insert("", "end", values=(
            "Grava", f"{r['grava_m3']:.3f} m³",
            "No aplica (Mortero)" if r["grava_m3"] == 0 else "Agregado grueso en volumen suelto"
        ))
        self.tabla_pedido.insert("", "end", values=(
            "Agua neta", f"{r['agua_l']:.1f} L",
            f"Relación a/c = {ac:g} descontando agua libre de los agregados"
        ))

        # Actualizar Memoria de Cálculo
        self.txt_memoria.configure(state="normal")
        self.txt_memoria.delete("1.0", "end")
        self.txt_memoria.insert("1.0", r["memoria"])
        self.txt_memoria.configure(state="disabled")

        self.btn_ilustrar.configure(state="normal")
        self.btn_csv.configure(state="normal")
        self._estado("Cálculo realizado por el método de volúmenes absolutos.", "#15803d")

    def ver_ilustracion(self):
        if not self.resultado:
            return
        VentanaIlustracion(self, self.tipo_mezcla or "Mezcla", self.resultado)

    def exportar(self):
        if not self.resultado:
            return
        nombre_sugerido = f"dosificacion_{(self.tipo_mezcla or 'mezcla').lower().replace(' ', '_')}.csv"
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivo CSV", "*.csv")],
            initialfile=nombre_sugerido,
            title="Guardar reporte técnico",
        )
        if not ruta:
            return
        try:
            exportar_csv(ruta, self.tipo_mezcla or "No especificado", self.entradas, self.resultado)
            self._estado(f"Reporte guardado en: {ruta}", "#15803d")
        except OSError as err:
            messagebox.showerror("Error al guardar", f"No se pudo guardar el archivo.\n{err}")

    def limpiar(self):
        if self.tipo_mezcla:
            self.seleccionar_mezcla(self.tipo_mezcla)


if __name__ == "__main__":
    App().mainloop()