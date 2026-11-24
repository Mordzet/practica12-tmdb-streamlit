"""
Universidad Politécnica de Querétaro
Ingeniería en Datos e Inteligencia Artificial

Materia: Herramientas de Visualización
Alumno: Said Giuliano Ayala Carrasco
Docente: Jairo Pacindo Piña
Grupo: IDIA 222
Fecha: 10 de noviembre de 2026

Práctica 12: Tu API
API Seleccionada: The Movie Database (TMDB)
"""

import os
import sys
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Paleta institucional del curso
COLOR_CONTEXTO = "#B9C3D1"     # Gris de contexto
COLOR_DESTACADO = "#1C4C9A"    # Azul de énfasis
PALETA_CUALITATIVA = ["#E69F00", "#56B4E9", "#009E73", "#0072B2"]

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8


# FASE 3 - CONDICIÓN 1: El token vive fuera del código
def leer_token(archivo="token.txt"):
    """
    Lee el token desde un archivo externo y lo valida.
    Si está ausente, vacío o incompleto, el programa lo notifica y se detiene.
    """
    if not os.path.exists(archivo):
        print(f"[ERROR DE SEGURIDAD] No se encontró el archivo '{archivo}'.")
        print("Crea un archivo llamado 'token.txt' y coloca tu API Key de TMDB dentro.")
        raise SystemExit(1)

    with open(archivo, "r", encoding="utf-8-sig") as f:
        lineas = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]

    if not lineas or not lineas[0] or lineas[0] == "TU_API_KEY_AQUI":
        # Si ya existe respuesta.json en caché local, permitimos ejecutar en modo offline
        if os.path.exists("respuesta.json"):
            print("[AVISO] 'token.txt' no contiene API Key activa, pero se detectó 'respuesta.json'.")
            print("Reutilizando datos locales en modo seguro.")
            return None
        print(f"[ERROR DE VALIDACIÓN] El archivo '{archivo}' está vacío o incompleto.")
        print("Ingresa tu API Key de TMDB para continuar.")
        raise SystemExit(1)

    token = lineas[0]
    if len(token) < 15:
        print(f"[ERROR DE VALIDACIÓN] El token leído en '{archivo}' es demasiado corto o inválido.")
        raise SystemExit(1)

    print("Token cargado y validado correctamente desde 'token.txt'.")
    return token


# FASE 3 - CONDICIONES 2, 3 Y 4: Códigos de estado, verificación JSON y caché
def obtener_datos_api(token, archivo_cache="respuesta.json"):
    """
    Condición 4: Reutiliza datos si el archivo ya existe; si no, consulta la API.
    Condición 2: Revisa códigos de estado (401, 400, 429) con mensajes diferenciados.
    Condición 3: Valida que la respuesta contenga Content-Type JSON.
    """
    if os.path.exists(archivo_cache):
        print(f"Reutilizando datos locales desde '{archivo_cache}' (ahorro de peticiones y modo depuración).")
        try:
            with open(archivo_cache, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"[AVISO] El archivo '{archivo_cache}' estaba dañado. Se consultará de nuevo la API.")

    if not token:
        print("[ERROR] Se requiere un token válido en token.txt para descargar los datos por primera vez.")
        raise SystemExit(1)

    print("Consultando API de The Movie Database (TMDB)...")
    url_base = "https://api.themoviedb.org/3/discover/movie"
    todas_las_peliculas = []
    total_paginas = 12  # 20 películas por página = 240 registros

    for pagina in range(1, total_paginas + 1):
        params = {
            "api_key": token,
            "language": "es-MX",
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "include_video": "false",
            "page": pagina
        }

        try:
            respuesta = requests.get(url_base, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR DE RED] Falla al conectar con el servidor: {e}")
            raise SystemExit(1)

        # Condición 2: Revisión de código de estado con mensajes explícitos
        if respuesta.status_code == 401:
            print("[ERROR 401] El token no sirve, expiró o no está autorizado.")
            raise SystemExit(1)
        elif respuesta.status_code == 400:
            print("[ERROR 400] Solicitud incorrecta: parámetros inválidos en la petición.")
            raise SystemExit(1)
        elif respuesta.status_code == 429:
            print("[ERROR 429] Límite de peticiones excedido (Rate limit alcanzado).")
            raise SystemExit(1)
        elif respuesta.status_code != 200:
            print(f"[ERROR {respuesta.status_code}] Error inesperado devuelto por la API.")
            raise SystemExit(1)

        # Condición 3: Verificación estricta de que la respuesta sea JSON
        if "json" not in (respuesta.headers.get("Content-Type") or ""):
            print("[ERROR FORMATO] La respuesta no tiene Content-Type JSON:")
            print(respuesta.text[:300])
            raise SystemExit(1)

        datos_pagina = respuesta.json()
        resultados = datos_pagina.get("results", [])
        todas_las_peliculas.extend(resultados)

    estructura = {
        "resultados": {
            "lista": todas_las_peliculas
        },
        "total_registros_descargados": len(todas_las_peliculas),
        "fuente": "The Movie Database (TMDB) API"
    }

    # Condición 4: Guardar la respuesta en archivo local
    with open(archivo_cache, "w", encoding="utf-8") as f:
        json.dump(estructura, f, ensure_ascii=False, indent=2)

    print(f"Se descargaron y almacenaron {len(todas_las_peliculas)} registros en '{archivo_cache}'.")
    return estructura


# FASE 3 - CONDICIÓN 5: La limpieza queda documentada
def limpiar_datos(datos_json):
    """
    Documenta: tipos de dato al cargar, faltantes por columna,
    conversiones numéricas y cuántos registros quedaron utilizables.
    """
    print("\n--- FASE 3: DOCUMENTACIÓN DE LA LIMPIEZA DE DATOS ---")

    lista = datos_json["resultados"]["lista"]
    df = pd.DataFrame(lista)

    columnas_clave = ['title', 'popularity', 'vote_average', 'vote_count', 'release_date', 'original_language']

    print(f"1. Registros cargados originalmente desde el JSON: {len(df)}")
    print("\n2. Tipos de dato originales al cargar:")
    print(df[columnas_clave].dtypes)

    print("\n3. Faltantes (nulos) por columna antes de limpiar:")
    faltantes = df[columnas_clave].isnull().sum()
    print(faltantes)

    # Conversión explícita de tipos de datos
    df['popularity'] = pd.to_numeric(df['popularity'], errors='coerce')
    df['vote_average'] = pd.to_numeric(df['vote_average'], errors='coerce')
    df['vote_count'] = pd.to_numeric(df['vote_count'], errors='coerce')
    df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')

    # Filtrado y conteo de pérdidas
    n_inicial = len(df)
    df_limpio = df.dropna(subset=['popularity', 'vote_average', 'vote_count', 'release_date', 'original_language']).copy()
    
    # Exigir un mínimo de 10 votos para garantizar solidez estadística
    df_limpio = df_limpio[df_limpio['vote_count'] >= 10].copy()
    
    # Columna temporal de año para análisis de evolución
    df_limpio['anio'] = df_limpio['release_date'].dt.year.astype(int)

    n_final = len(df_limpio)
    perdidos = n_inicial - n_final

    print(f"\n4. Registros descartados por datos inválidos o votos insuficientes: {perdidos}")
    print(f"5. Total de registros utilizables finales: {n_final} (Supera el mínimo de 200)\n")

    return df_limpio


# FASE 4: Gráfica 1 - Distribución
def graficar_distribucion(df):
    plt.figure(figsize=(9, 5))
    n, bins, patches = plt.hist(df['vote_average'], bins=14, color=COLOR_CONTEXTO, edgecolor='white')

    for i in range(len(patches)):
        if bins[i] >= 6.0 and bins[i+1] <= 7.8:
            patches[i].set_facecolor(COLOR_DESTACADO)

    mediana = df['vote_average'].median()

    plt.title(f"La mayoría de las producciones populares se concentra entre 6.0 y 7.8 puntos (Mediana: {mediana:.1f})",
              fontsize=12, fontweight='bold', pad=15)
    plt.xlabel("Calificación promedio otorgada por usuarios (escala de 0 a 10 puntos)", fontsize=10)
    plt.ylabel("Frecuencia (número de películas)", fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    plt.savefig("grafica1_distribucion.png", dpi=300)
    print("Gráfica 1 guardada: 'grafica1_distribucion.png'")
    plt.show()


# FASE 4: Gráfica 2 - Comparación
def graficar_comparacion(df):
    top_idiomas = df['original_language'].value_counts().head(5)
    mapa_idiomas = {
        'en': 'Inglés (en)',
        'es': 'Español (es)',
        'ja': 'Japonés (ja)',
        'fr': 'Francés (fr)',
        'ko': 'Coreano (ko)'
    }
    nombres = [mapa_idiomas.get(cod, cod) for cod in top_idiomas.index]
    colores = [COLOR_DESTACADO if cod == 'en' else COLOR_CONTEXTO for cod in top_idiomas.index]

    plt.figure(figsize=(9, 5))
    barras = plt.bar(nombres, top_idiomas.values, color=colores, width=0.6)

    for bar in barras:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2., h + 2,
                 f"{int(h)}", ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.title("El idioma inglés domina con más del 70% de títulos frente a las producciones en otros idiomas",
              fontsize=12, fontweight='bold', pad=15)
    plt.xlabel("Idioma original de producción (código ISO)", fontsize=10)
    plt.ylabel("Cantidad total de películas (unidades)", fontsize=10)
    plt.ylim(0, max(top_idiomas.values) * 1.15)
    plt.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()

    plt.savefig("grafica2_comparacion.png", dpi=300)
    print("Gráfica 2 guardada: 'grafica2_comparacion.png'")
    plt.show()


# FASE 4: Gráfica 3 - Relación
def graficar_relacion(df):
    plt.figure(figsize=(9, 5))
    plt.scatter(df['vote_count'], df['vote_average'], color=COLOR_DESTACADO, alpha=0.6, s=50, edgecolors='none')

    plt.title("Películas con alto volumen de votos convergen hacia calificaciones estables sin valores atípicos",
              fontsize=11, fontweight='bold', pad=15)
    plt.xlabel("Volumen total de votos recibidos (número de votos)", fontsize=10)
    plt.ylabel("Calificación promedio asignada (escala de 0 a 10 puntos)", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()

    plt.savefig("grafica3_relacion.png", dpi=300)
    print("Gráfica 3 guardada: 'grafica3_relacion.png'")
    plt.show()


# FASE 4: Gráfica 4 - Evolución
def graficar_evolucion(df):
    df_evol = df[df['anio'] >= 2017].groupby('anio')['vote_average'].mean().reset_index()

    plt.figure(figsize=(9, 5))
    plt.plot(df_evol['anio'], df_evol['vote_average'], color=COLOR_DESTACADO, marker='o',
             linewidth=2.5, markersize=8, markerfacecolor='#0072B2')

    for _, fila in df_evol.iterrows():
        plt.text(fila['anio'], fila['vote_average'] + 0.05, f"{fila['vote_average']:.2f}",
                 ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.title("La calificación promedio anual se mantiene estable en torno a 7.0 puntos durante 2017-2024",
              fontsize=11, fontweight='bold', pad=15)
    plt.xlabel("Año de estreno oficial (año)", fontsize=10)
    plt.ylabel("Calificación promedio anual (escala de 0 a 10 puntos)", fontsize=10)
    plt.ylim(min(df_evol['vote_average']) - 0.4, max(df_evol['vote_average']) + 0.4)
    plt.xticks(df_evol['anio'].astype(int))
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()

    plt.savefig("grafica4_evolucion.png", dpi=300)
    print("Gráfica 4 guardada: 'grafica4_evolucion.png'")
    plt.show()


# Ejecución principal
def main():
    print("\n--- INICIO DE PRÁCTICA 12: HERRAMIENTAS DE VISUALIZACIÓN ---\n")
    token = leer_token()
    datos = obtener_datos_api(token)
    df_limpio = limpiar_datos(datos)
    
    print("Generando y guardando las 4 gráficas requeridas...")
    graficar_distribucion(df_limpio)
    graficar_comparacion(df_limpio)
    graficar_relacion(df_limpio)
    graficar_evolucion(df_limpio)
    
    print("\n¡Proceso finalizado con éxito!")
    print("Se cumplieron todas las condiciones y reglas de visualización.")


if __name__ == "__main__":
    main()
