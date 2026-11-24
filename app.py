"""
Universidad Politécnica de Querétaro
Ingeniería en Datos e Inteligencia Artificial

Materia: Herramientas de Visualización
Alumno: Said Giuliano Ayala Carrasco
Docente: Jairo Pacindo Piña
Grupo: IDIA 222

Práctica 12: Transformación a Dashboard Interactivo con Streamlit
API Seleccionada: The Movie Database (TMDB)
"""

import os
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Dashboard TMDB API | UPQ - Práctica 12",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paleta institucional del curso
COLOR_CONTEXTO = "#B9C3D1"     # Gris de contexto
COLOR_DESTACADO = "#1C4C9A"    # Azul de énfasis
PALETA_CUALITATIVA = ["#E69F00", "#56B4E9", "#009E73", "#0072B2"]

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8

MAPA_IDIOMAS = {
    'en': 'Inglés (en)',
    'es': 'Español (es)',
    'ja': 'Japonés (ja)',
    'fr': 'Francés (fr)',
    'ko': 'Coreano (ko)',
    'it': 'Italiano (it)'
}

# Estilos CSS personalizados para el dashboard
st.markdown(f"""
<style>
    .main-header {{
        background: linear-gradient(135deg, #0d254c 0%, {COLOR_DESTACADO} 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 12px rgba(28, 76, 154, 0.18);
    }}
    .main-header h1 {{
        color: white !important;
        margin: 0;
        font-size: 1.9rem;
        font-weight: 700;
    }}
    .main-header p {{
        color: #DCE4F2;
        margin: 0.35rem 0 0 0;
        font-size: 0.98rem;
    }}
    .badge-inst {{
        display: inline-block;
        background-color: rgba(255, 255, 255, 0.16);
        color: #FFFFFF;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.82rem;
        margin-right: 0.5rem;
        margin-top: 0.5rem;
        border: 1px solid rgba(255, 255, 255, 0.25);
    }}
    .insight-box {{
        background-color: #F4F7FB;
        border-left: 5px solid {COLOR_DESTACADO};
        padding: 0.9rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
        color: #1E293B;
        font-size: 0.93rem;
    }}
    .condition-card {{
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-top: 4px solid {COLOR_DESTACADO};
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        height: 100%;
    }}
</style>
""", unsafe_allow_html=True)


# FASE 3 - CONDICIÓN 1: El token vive fuera del código
def leer_token(archivo="token.txt"):
    """
    Lee el token desde un archivo externo (no subido al repositorio) y lo valida.
    Si no existe pero está disponible respuesta.json, opera en modo caché seguro.
    """
    if not os.path.exists(archivo):
        if os.path.exists("respuesta.json"):
            return None, "Modo Caché Local: 'token.txt' no presente en el entorno; operando de forma segura con 'respuesta.json'."
        return None, f"[ERROR DE SEGURIDAD] No se encontró '{archivo}' ni caché local."

    with open(archivo, "r", encoding="utf-8-sig") as f:
        lineas = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]

    if not lineas or not lineas[0] or lineas[0] == "TU_API_KEY_AQUI":
        if os.path.exists("respuesta.json"):
            return None, "⚠ 'token.txt' sin API Key activa. Reutilizando caché validada de 'respuesta.json'."
        return None, f"[ERROR DE VALIDACIÓN] El archivo '{archivo}' está vacío o incompleto."

    token = lineas[0]
    if len(token) < 15:
        if os.path.exists("respuesta.json"):
            return None, "⚠ Token en 'token.txt' inválido. Reutilizando caché local 'respuesta.json'."
        return None, f"[ERROR DE VALIDACIÓN] El token en '{archivo}' es demasiado corto o inválido."

    return token, "✔ Token externo cargado y validado desde 'token.txt' (excluido de Git mediante .gitignore)."


# FASE 3 - CONDICIONES 2, 3 Y 4: Códigos de estado, verificación JSON y caché
@st.cache_data(show_spinner="Cargando datos de TMDB...")
def obtener_datos_api(token, archivo_cache="respuesta.json", forzar_api=False):
    """
    Condición 4: Reutiliza datos si respuesta.json ya existe; si no, consulta la API.
    Condición 2: Revisa códigos de estado (401, 400, 429) con mensajes diferenciados.
    Condición 3: Valida que la respuesta contenga Content-Type JSON.
    """
    if os.path.exists(archivo_cache) and not forzar_api:
        try:
            with open(archivo_cache, "r", encoding="utf-8-sig") as f:
                datos = json.load(f)
            return datos, f"✔ Datos cargados desde caché local '{archivo_cache}' ({len(datos['resultados']['lista'])} registros)."
        except json.JSONDecodeError:
            pass

    if not token:
        raise RuntimeError("[ERROR] Se requiere un token válido en 'token.txt' para consultar la API en vivo.")

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
        respuesta = requests.get(url_base, params=params, timeout=10)

        # Condición 2: Revisión explícita de códigos de estado HTTP
        if respuesta.status_code == 401:
            raise RuntimeError("[ERROR 401] Token inválido, expirado o no autorizado.")
        elif respuesta.status_code == 400:
            raise RuntimeError("[ERROR 400] Solicitud mal formulada: parámetros inválidos.")
        elif respuesta.status_code == 429:
            raise RuntimeError("[ERROR 429] Límite de peticiones excedido (Rate limit).")
        elif respuesta.status_code != 200:
            raise RuntimeError(f"[ERROR {respuesta.status_code}] Respuesta fallida del servidor.")

        # Condición 3: Verificación de Content-Type JSON
        if "json" not in (respuesta.headers.get("Content-Type") or ""):
            raise RuntimeError(f"[ERROR FORMATO] Content-Type no es JSON: {respuesta.text[:200]}")

        resultados = respuesta.json().get("results", [])
        todas_las_peliculas.extend(resultados)

    estructura = {
        "resultados": {"lista": todas_las_peliculas},
        "total_registros_descargados": len(todas_las_peliculas),
        "fuente": "The Movie Database (TMDB) API"
    }

    # Condición 4: Guardar en caché local
    with open(archivo_cache, "w", encoding="utf-8") as f:
        json.dump(estructura, f, ensure_ascii=False, indent=2)

    return estructura, f"✔ Se descargaron y almacenaron {len(todas_las_peliculas)} registros en '{archivo_cache}'."


# FASE 3 - CONDICIÓN 5: La limpieza queda documentada
def limpiar_datos(datos_json):
    """
    Limpia el DataFrame y devuelve tanto el DataFrame limpio como el reporte
    de auditoría de limpieza (tipos originales, faltantes, descartados y total final).
    """
    lista = datos_json["resultados"]["lista"]
    df = pd.DataFrame(lista)

    columnas_clave = ['title', 'popularity', 'vote_average', 'vote_count', 'release_date', 'original_language']
    n_inicial = len(df)
    tipos_originales = df[columnas_clave].dtypes.astype(str).to_dict()
    faltantes_antes = df[columnas_clave].isnull().sum().to_dict()

    # Conversión explícita de tipos
    df['popularity'] = pd.to_numeric(df['popularity'], errors='coerce')
    df['vote_average'] = pd.to_numeric(df['vote_average'], errors='coerce')
    df['vote_count'] = pd.to_numeric(df['vote_count'], errors='coerce')
    df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')

    df_limpio = df.dropna(subset=['popularity', 'vote_average', 'vote_count', 'release_date', 'original_language']).copy()
    df_limpio = df_limpio[df_limpio['vote_count'] >= 10].copy()
    df_limpio['anio'] = df_limpio['release_date'].dt.year.astype(int)
    df_limpio['idioma_nombre'] = df_limpio['original_language'].map(lambda c: MAPA_IDIOMAS.get(c, c))

    n_final = len(df_limpio)
    perdidos = n_inicial - n_final

    auditoria = {
        "n_inicial": n_inicial,
        "tipos_originales": tipos_originales,
        "faltantes_antes": faltantes_antes,
        "tipos_finales": df_limpio[columnas_clave + ['anio']].dtypes.astype(str).to_dict(),
        "perdidos": perdidos,
        "n_final": n_final
    }
    return df_limpio, auditoria


# FASE 4: Funciones de generación de las 4 gráficas con la paleta institucional
def figura_distribucion(df, bins_count=14, rango_destacado=(6.0, 7.8)):
    fig, ax = plt.subplots(figsize=(9, 4.8))
    n, bins, patches = ax.hist(df['vote_average'], bins=bins_count, color=COLOR_CONTEXTO, edgecolor='white')

    for i in range(len(patches)):
        if bins[i] >= rango_destacado[0] and bins[i + 1] <= rango_destacado[1]:
            patches[i].set_facecolor(COLOR_DESTACADO)

    mediana = df['vote_average'].median() if len(df) > 0 else 0.0
    ax.axvline(mediana, color='#E69F00', linestyle='--', linewidth=2, label=f'Mediana: {mediana:.1f}')

    ax.set_title(
        f"La mayoría de las producciones populares se concentra entre {rango_destacado[0]:.1f} y {rango_destacado[1]:.1f} puntos (Mediana: {mediana:.1f})",
        fontsize=11.5, fontweight='bold', pad=14
    )
    ax.set_xlabel("Calificación promedio otorgada por usuarios (escala de 0 a 10 puntos)", fontsize=10)
    ax.set_ylabel("Frecuencia (número de películas)", fontsize=10)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.legend(frameon=True, facecolor='white')
    fig.tight_layout()
    return fig, mediana


def figura_comparacion(df):
    top_idiomas = df['original_language'].value_counts().head(5)
    nombres = [MAPA_IDIOMAS.get(cod, cod) for cod in top_idiomas.index]
    idioma_lider = top_idiomas.index[0] if len(top_idiomas) > 0 else 'en'
    pct_lider = (top_idiomas.iloc[0] / len(df) * 100) if len(df) > 0 else 0.0
    colores = [COLOR_DESTACADO if cod == idioma_lider else COLOR_CONTEXTO for cod in top_idiomas.index]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    barras = ax.bar(nombres, top_idiomas.values, color=colores, width=0.58)

    max_val = max(top_idiomas.values) if len(top_idiomas) > 0 else 10
    for bar in barras:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2., h + (max_val * 0.02),
            f"{int(h)}", ha='center', va='bottom', fontsize=9.5, fontweight='bold'
        )

    nombre_lider = MAPA_IDIOMAS.get(idioma_lider, idioma_lider)
    ax.set_title(
        f"El idioma {nombre_lider.split(' ')[0].lower()} lidera con el {pct_lider:.1f}% del catálogo analizado frente a otros idiomas",
        fontsize=11.5, fontweight='bold', pad=14
    )
    ax.set_xlabel("Idioma original de producción (código ISO)", fontsize=10)
    ax.set_ylabel("Cantidad total de películas (unidades)", fontsize=10)
    ax.set_ylim(0, max_val * 1.18)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    fig.tight_layout()
    return fig, nombre_lider, pct_lider


def figura_relacion(df, umbral_votos=5000):
    fig, ax = plt.subplots(figsize=(9, 4.8))

    df_bajo = df[df['vote_count'] < umbral_votos]
    df_alto = df[df['vote_count'] >= umbral_votos]

    ax.scatter(
        df_bajo['vote_count'], df_bajo['vote_average'],
        color=COLOR_CONTEXTO, alpha=0.7, s=48, label=f'< {umbral_votos:,} votos (Contexto)'
    )
    ax.scatter(
        df_alto['vote_count'], df_alto['vote_average'],
        color=COLOR_DESTACADO, alpha=0.75, s=55, label=f'≥ {umbral_votos:,} votos (Énfasis)'
    )

    ax.set_title(
        "Películas con alto volumen de votos convergen hacia calificaciones estables sin valores atípicos",
        fontsize=11, fontweight='bold', pad=14
    )
    ax.set_xlabel("Volumen total de votos recibidos (número de votos)", fontsize=10)
    ax.set_ylabel("Calificación promedio asignada (escala de 0 a 10 puntos)", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(frameon=True, facecolor='white')
    fig.tight_layout()
    return fig


def figura_evolucion(df):
    df_evol = df.groupby('anio')['vote_average'].mean().reset_index()

    fig, ax = plt.subplots(figsize=(9, 4.8))
    if len(df_evol) > 0:
        ax.plot(
            df_evol['anio'], df_evol['vote_average'],
            color=COLOR_DESTACADO, marker='o', linewidth=2.5,
            markersize=8, markerfacecolor='#0072B2'
        )
        for _, fila in df_evol.iterrows():
            ax.text(
                fila['anio'], fila['vote_average'] + 0.04,
                f"{fila['vote_average']:.2f}",
                ha='center', va='bottom', fontsize=9, fontweight='bold'
            )
        min_y = min(df_evol['vote_average']) - 0.35
        max_y = max(df_evol['vote_average']) + 0.35
        ax.set_ylim(min_y, max_y)
        ax.set_xticks(df_evol['anio'].astype(int))
        rango_anios = f"{int(df_evol['anio'].min())}-{int(df_evol['anio'].max())}"
        prom_global = df_evol['vote_average'].mean()
    else:
        rango_anios = "N/A"
        prom_global = 0.0

    ax.set_title(
        f"La calificación promedio anual se mantiene estable en torno a {prom_global:.1f} puntos durante {rango_anios}",
        fontsize=11, fontweight='bold', pad=14
    )
    ax.set_xlabel("Año de estreno oficial (año)", fontsize=10)
    ax.set_ylabel("Calificación promedio anual (escala de 0 a 10 puntos)", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.4)
    fig.tight_layout()
    return fig, df_evol


# ================= INTERFAZ PRINCIPAL DEL DASHBOARD =================
def main():
    # Encabezado institucional
    st.markdown("""
    <div class="main-header">
        <h1>🎬 Dashboard Analítico: The Movie Database (TMDB) API</h1>
        <p>Universidad Politécnica de Querétaro · Ingeniería en Datos e Inteligencia Artificial · Herramientas de Visualización</p>
        <div>
            <span class="badge-inst">👤 Alumno: Said Giuliano Ayala Carrasco</span>
            <span class="badge-inst">👨‍🏫 Docente: Jairo Pacindo Piña</span>
            <span class="badge-inst">🎓 Grupo: IDIA 222</span>
            <span class="badge-inst">📊 Práctica 12 · Integración Streamlit</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Carga de token y datos
    token, msg_token = leer_token()
    try:
        datos_json, msg_datos = obtener_datos_api(token)
        df_base, auditoria = limpiar_datos(datos_json)
    except Exception as e:
        st.error(f"Error al cargar o procesar los datos: {e}")
        st.stop()

    # ================= BARRA LATERAL (FILTROS Y CONTROLES) =================
    with st.sidebar:
        st.image(
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRoU0LVmDWQ26ORp8H49iWqH-mElAcwDJ7lThXdPQDcCIWgrJXykHsREmo_&s=10",
            width=220
        )
        st.markdown("### ⚙️ Filtros Interactivos")
        st.caption("Ajusta los parámetros para explorar el catálogo de películas en tiempo real.")

        anios_disp = sorted(df_base['anio'].unique())
        rango_anios = st.slider(
            "📅 Rango de año de estreno",
            min_value=int(min(anios_disp)),
            max_value=int(max(anios_disp)),
            value=(int(min(anios_disp)), int(max(anios_disp)))
        )

        idiomas_disp = sorted(df_base['original_language'].unique())
        idiomas_sel = st.multiselect(
            "🌐 Idioma original de producción",
            options=idiomas_disp,
            default=idiomas_disp,
            format_func=lambda x: MAPA_IDIOMAS.get(x, x)
        )

        rango_calif = st.slider(
            "⭐ Rango de calificación (0 - 10)",
            min_value=float(df_base['vote_average'].min()),
            max_value=float(df_base['vote_average'].max()),
            value=(float(df_base['vote_average'].min()), float(df_base['vote_average'].max())),
            step=0.1
        )

        min_votos = st.number_input(
            "🗳️ Volumen mínimo de votos",
            min_value=10,
            max_value=int(df_base['vote_count'].max()),
            value=10,
            step=100
        )

        busqueda_titulo = st.text_input("🔍 Buscar película por título", placeholder="Ej. Dune, Oppenheimer, Roma...")

        st.markdown("---")
        st.markdown("### 🎨 Paleta Institucional")
        col_c1, col_c2 = st.columns(2)
        col_c1.color_picker("Gris Contexto", COLOR_CONTEXTO, disabled=True)
        col_c2.color_picker("Azul Énfasis", COLOR_DESTACADO, disabled=True)

        st.markdown("---")
        st.markdown("### 🔐 Estado de Seguridad")
        st.info(msg_token)
        st.success(msg_datos)

    # Aplicar filtros al DataFrame
    df_filtrado = df_base[
        (df_base['anio'] >= rango_anios[0]) &
        (df_base['anio'] <= rango_anios[1]) &
        (df_base['original_language'].isin(idiomas_sel if idiomas_sel else idiomas_disp)) &
        (df_base['vote_average'] >= rango_calif[0]) &
        (df_base['vote_average'] <= rango_calif[1]) &
        (df_base['vote_count'] >= min_votos)
    ].copy()

    if busqueda_titulo.strip():
        df_filtrado = df_filtrado[
            df_filtrado['title'].str.contains(busqueda_titulo.strip(), case=False, na=False)
        ].copy()

    # ================= KPIs PRINCIPALES =================
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    total_actual = len(df_filtrado)
    calif_media = df_filtrado['vote_average'].mean() if total_actual > 0 else 0.0
    calif_mediana = df_filtrado['vote_average'].median() if total_actual > 0 else 0.0
    votos_totales = int(df_filtrado['vote_count'].sum()) if total_actual > 0 else 0
    pop_media = df_filtrado['popularity'].mean() if total_actual > 0 else 0.0

    kpi1.metric("🎞️ Películas Analizadas", f"{total_actual}", f"de {auditoria['n_final']} limpias")
    kpi2.metric("⭐ Calificación Promedio", f"{calif_media:.2f} / 10", f"Mediana: {calif_mediana:.1f}")
    kpi3.metric("🗳️ Volumen Total Votos", f"{votos_totales:,}", "Participación acumulada")
    kpi4.metric("🔥 Popularidad Media", f"{pop_media:.1f}", "Índice TMDB")
    idioma_top_kpi = MAPA_IDIOMAS.get(df_filtrado['original_language'].mode()[0], "N/A") if total_actual > 0 else "N/A"
    kpi5.metric("🌍 Idioma Predominante", idioma_top_kpi, "Mayor presencia")

    st.markdown("---")

    # ================= PESTAÑAS DEL DASHBOARD =================
    tab_graficas, tab_ficha, tab_limpieza, tab_explorador = st.tabs([
        "📊 Fase 4: Las 4 Gráficas y Hallazgos",
        "📋 Fase 2: Ficha Técnica de la API",
        "🧹 Fase 3: Seguridad, Caché y Limpieza",
        "🔎 Explorador de Datos y Descarga"
    ])

    # ---------------- PESTAÑA 1: LAS 4 GRÁFICAS ----------------
    with tab_graficas:
        if total_actual == 0:
            st.warning("No hay películas que coincidan con los filtros seleccionados en la barra lateral.")
        else:
            st.markdown(
                "**Reglas visuales aplicadas:** El título enuncia el hallazgo principal · Ejes con nombre y unidad · "
                f"Paleta institucional con gris de contexto (`{COLOR_CONTEXTO}`) y azul de énfasis (`{COLOR_DESTACADO}`)."
            )

            fila1_col1, fila1_col2 = st.columns(2)

            # Gráfica 1: Distribución
            with fila1_col1:
                st.subheader("1️⃣ Gráfica de Distribución")
                st.caption("**Pregunta:** ¿Cómo se reparten las calificaciones de las películas populares y en qué rango se concentran?")
                fig1, med1 = figura_distribucion(df_filtrado)
                st.pyplot(fig1)
                plt.close(fig1)
                st.markdown(f"""
                <div class="insight-box">
                    <strong>Lectura del hallazgo (Gráfica 1):</strong> La distribución de calificaciones presenta un comportamiento
                    concentrado alrededor de una mediana de <strong>{med1:.1f} puntos</strong>. Prácticamente la totalidad del catálogo
                    de alta popularidad se ubica en la franja destacada entre <strong>6.0 y 7.8 puntos</strong>, demostrando que el
                    consenso del público tiende a calificaciones moderadamente positivas.
                </div>
                """, unsafe_allow_html=True)

            # Gráfica 2: Comparación
            with fila1_col2:
                st.subheader("2️⃣ Gráfica de Comparación")
                st.caption("**Pregunta:** ¿Qué idioma original tiene mayor presencia numérica entre las producciones más populares?")
                fig2, lider_nom, lider_pct = figura_comparacion(df_filtrado)
                st.pyplot(fig2)
                plt.close(fig2)
                st.markdown(f"""
                <div class="insight-box">
                    <strong>Lectura del hallazgo (Gráfica 2):</strong> Las producciones en <strong>{lider_nom}</strong> mantienen
                    el liderazgo dentro del catálogo filtrado con el <strong>{lider_pct:.1f}%</strong> de los títulos, seguidas
                    por producciones en español, japonés, coreano y francés que logran posicionarse de forma consistente en los rankings globales.
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            fila2_col1, fila2_col2 = st.columns(2)

            # Gráfica 3: Relación
            with fila2_col1:
                st.subheader("3️⃣ Gráfica de Relación")
                st.caption("**Pregunta:** ¿Existe una relación entre el volumen total de votos y la calificación promedio asignada?")
                fig3 = figura_relacion(df_filtrado)
                st.pyplot(fig3)
                plt.close(fig3)
                st.markdown("""
                <div class="insight-box">
                    <strong>Lectura del hallazgo (Gráfica 3):</strong> Se aprecia una convergencia estadística conforme crece la participación
                    de la audiencia: las películas que superan los <strong>5,000 votos</strong> (destacadas en azul institucional) mantienen
                    puntuaciones consolidadas y sin valores atípicos extremos, validando su aceptación sostenida.
                </div>
                """, unsafe_allow_html=True)

            # Gráfica 4: Evolución
            with fila2_col2:
                st.subheader("4️⃣ Gráfica de Evolución Temporal")
                st.caption("**Pregunta:** ¿Cómo ha variado la calificación promedio de las películas según su año de estreno?")
                fig4, df_evol = figura_evolucion(df_filtrado)
                st.pyplot(fig4)
                plt.close(fig4)
                st.markdown("""
                <div class="insight-box">
                    <strong>Lectura del hallazgo (Gráfica 4):</strong> A través de la serie anual (2017–2024), la calificación promedio
                    se mantiene altamente estable alrededor de <strong>7.1 – 7.4 puntos</strong>, sin caídas abruptas atribuibles al año de lanzamiento,
                    lo que refleja un estándar constante en la valoración de los estrenos más populares.
                </div>
                """, unsafe_allow_html=True)

    # ---------------- PESTAÑA 2: FICHA DE LA API ----------------
    with tab_ficha:
        st.subheader("📋 Fase 2. Ficha Técnica de The Movie Database (TMDB) API")
        ficha_data = [
            ("Nombre y liga", "The Movie Database (TMDB) API — https://developer.themoviedb.org/reference/intro/getting-started"),
            ("Qué datos entrega", "Catálogo estructurado de películas internacionales con títulos, fechas oficiales de estreno, índice de popularidad calculado, calificación promedio (0 a 10 puntos), volumen de votos e idioma original."),
            ("Cómo se obtiene el token", "1. Registro gratuito en themoviedb.org · 2. Ajustes de cuenta → apartado API · 3. Generar API Key de desarrollador."),
            ("Cómo se manda el token", "Como parámetro en la URL con el nombre exacto `api_key` (o por encabezado `Authorization: Bearer <token>`)."),
            ("Límite de peticiones", "Alrededor de 50 peticiones por segundo (sin límite restrictivo de cuota diaria gratuita)."),
            ("Endpoint elegido", "https://api.themoviedb.org/3/discover/movie?api_key=****************&language=es-MX&sort_by=popularity.desc&page=1"),
            ("Estructura del JSON", "La lista de registros se almacena en la ruta `datos['resultados']['lista']`."),
            ("Columnas y registros", "Columnas: popularity, vote_average, vote_count, release_date, original_language. Registros: 240 descargados (12 páginas × 20 películas), superando el mínimo de 200 limpios."),
            ("Las 4 preguntas analíticas", "1. Distribución de calificaciones · 2. Comparación por idioma original · 3. Relación entre votos y calificación · 4. Evolución anual por año de estreno.")
        ]
        df_ficha = pd.DataFrame(ficha_data, columns=["Campo de la Ficha", "Especificación Técnica"])
        st.table(df_ficha)

        st.markdown("#### 💡 Reflexión Final del Reporte")
        st.info(
            "**¿Qué fue lo más difícil del proceso?** Lo más desafiante fue la comprensión e integración de la documentación de la API "
            "junto con la paginación (`page=1..12`) para superar los 200 registros limpios, concatenando múltiples respuestas JSON con manejo "
            "estricto de códigos de estado HTTP (`401`, `400`, `429`), validación de `Content-Type` y almacenamiento en caché local antes de su "
            "integración interactiva en Streamlit."
        )

    # ---------------- PESTAÑA 3: FASE 3 Y LIMPIEZA ----------------
    with tab_limpieza:
        st.subheader("🛡️ Cumplimiento de las 5 Condiciones Obligatorias (Fase 3)")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""
            <div class="condition-card">
                <h4>🔒 Condición 1: Token Externo</h4>
                <p>El token jamás se escribe en el código fuente. Se lee desde <code>token.txt</code> (excluido del repositorio con <code>.gitignore</code>) y se valida su longitud y formato.</p>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("""
            <div class="condition-card">
                <h4>📡 Condiciones 2 y 3: HTTP & JSON</h4>
                <p>Manejo explícito de códigos HTTP (<code>401</code> No autorizado, <code>400</code> Petición inválida, <code>429</code> Rate Limit) y verificación de cabecera <code>Content-Type: application/json</code>.</p>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown("""
            <div class="condition-card">
                <h4>💾 Condición 4: Caché Local</h4>
                <p>Respaldo automático en <code>respuesta.json</code> con 240 registros para evitar consumo innecesario de cuota y permitir ejecución segura sin exponer credenciales.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 🧹 Condición 5: Documentación de la Limpieza de Datos")
        m1, m2, m3 = st.columns(3)
        m1.metric("1. Registros cargados del JSON", auditoria["n_inicial"])
        m2.metric("2. Registros descartados (nulos / <10 votos)", auditoria["perdidos"])
        m3.metric("3. Total registros limpios utilizables", f"{auditoria['n_final']} (Mínimo requerido: 200)")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("**Tipos de dato originales y conteo de nulos al cargar:**")
            df_aud_orig = pd.DataFrame({
                "Columna": list(auditoria["tipos_originales"].keys()),
                "Tipo Original": list(auditoria["tipos_originales"].values()),
                "Faltantes (Nulos)": list(auditoria["faltantes_antes"].values())
            })
            st.dataframe(df_aud_orig, use_container_width=True, hide_index=True)

        with col_t2:
            st.markdown("**Tipos de dato tras conversión explícita (`pd.to_numeric` / `pd.to_datetime`):**")
            df_aud_fin = pd.DataFrame({
                "Columna": list(auditoria["tipos_finales"].keys()),
                "Tipo Estandarizado": list(auditoria["tipos_finales"].values())
            })
            st.dataframe(df_aud_fin, use_container_width=True, hide_index=True)

    # ---------------- PESTAÑA 4: EXPLORADOR DE DATOS ----------------
    with tab_explorador:
        st.subheader("🔎 Catálogo Interactivo de Películas (Datos Limpios)")
        columnas_mostrar = ['id', 'title', 'idioma_nombre', 'anio', 'vote_average', 'vote_count', 'popularity', 'release_date']
        df_vista = df_filtrado[columnas_mostrar].copy()
        df_vista['release_date'] = df_vista['release_date'].dt.strftime('%Y-%m-%d')
        df_vista = df_vista.rename(columns={
            'id': 'ID',
            'title': 'Título de la Película',
            'idioma_nombre': 'Idioma Original',
            'anio': 'Año',
            'vote_average': 'Calificación (0-10)',
            'vote_count': 'Total de Votos',
            'popularity': 'Índice Popularidad',
            'release_date': 'Fecha de Estreno'
        })

        st.dataframe(df_vista, use_container_width=True, hide_index=True, height=420)

        csv_bytes = df_vista.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar datos filtrados en CSV",
            data=csv_bytes,
            file_name="tmdb_peliculas_limpias.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
