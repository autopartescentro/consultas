
import re
import io
import json
import base64
import urllib.parse
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image
from openai import OpenAI


st.set_page_config(
    page_title="IA Vidrios - Autopartes Centro",
    page_icon="🚘",
    layout="centered"
)

WHATSAPP_NUMERO = "5493571636868"
LISTAS_DIR = Path("listas_precios")
COLOCACION_FILE = LISTAS_DIR / "listas_colocacion.xlsx"
LOGO_PATH = Path("assets/logo_ac.jpeg")


# =========================
# ESTILO AC SOBRE FORMATO CORRECTO
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

:root{
    --ac-green:#36d6bb;
    --ac-green-soft:#e6fff9;
    --ac-black:#111111;
    --ac-dark:#202020;
    --ac-white:#ffffff;
    --ac-red:#c51632;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(180deg, #ffffff 0%, #f5f7f7 100%);
    color: var(--ac-black);
}

.block-container {
    max-width: 920px;
    padding-top: 2.5rem;
}

.ac-header{
    display:flex;
    align-items:center;
    gap:18px;
    margin-bottom:10px;
}

.ac-logo{
    width:82px;
    height:82px;
    border-radius:50%;
    object-fit:cover;
    box-shadow:0 8px 24px rgba(0,0,0,.18);
    border:3px solid var(--ac-green);
    background:#222;
}

.ac-title-wrap h1{
    margin:0 !important;
    font-size:42px !important;
    font-weight:800 !important;
    color:#111 !important;
    letter-spacing:-.8px;
}

.ac-title-wrap p{
    margin:7px 0 0 0;
    color:#3b3b3b;
    font-size:15px;
}

.ac-badge{
    display:inline-block;
    background:var(--ac-green);
    color:#101010;
    padding:6px 12px;
    border-radius:999px;
    font-size:12px;
    font-weight:800;
    margin-right:6px;
    margin-bottom:8px;
}

.info-box {
    background: linear-gradient(90deg, #e6fff9 0%, #f7fffd 100%);
    border-radius: 12px;
    padding: 14px 18px;
    border-left: 6px solid var(--ac-green);
    margin: 18px 0 22px 0;
    color: #0b3c35;
    font-weight: 700;
}

.count-box {
    background: #ffffff;
    border: 1px solid #e9eeee;
    border-radius: 14px;
    padding: 14px 18px;
    margin: 18px 0;
    color: #333333;
    box-shadow:0 4px 16px rgba(0,0,0,.04);
}

.best-box {
    background: linear-gradient(135deg, #e6fff9 0%, #ffffff 100%);
    border: 2px solid var(--ac-green);
    border-radius: 16px;
    padding: 20px;
    margin-top: 18px;
    box-shadow:0 10px 28px rgba(54,214,187,.18);
}

.result-box {
    background: #ffffff;
    border-radius: 14px;
    border: 1px solid #e9eeee;
    padding: 18px;
    margin-top: 18px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.05);
}

div.stButton > button {
    background: var(--ac-red);
    color: white;
    border-radius: 10px;
    border: none;
    font-weight: 800;
    padding: 0.65rem 1.15rem;
    box-shadow:0 6px 16px rgba(197,22,50,.20);
}

div.stButton > button:hover {
    background: #a91128;
    color: white;
}

a {
    color: #0f9f8b !important;
    font-weight: 800;
}

h2, h3 {
    color: #111111 !important;
    font-weight: 800 !important;
}

.small-text {
    font-size: 13px;
    color: #555555;
}

.stSelectbox label, .stCheckbox label, .stTextInput label, .stFileUploader label {
    color: #222 !important;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)


# =========================
# HELPERS
# =========================
def normalize(text):
    text = str(text).lower()
    for a, b in {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "-": " ", "_": " ", "/": " ", ".": " "
    }.items():
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def parse_price(value):
    if value is None or pd.isna(value):
        return None
    txt = str(value).replace("$", "").replace(" ", "").strip()
    if "," in txt and "." in txt:
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt:
        txt = txt.replace(",", ".")
    else:
        if txt.count(".") >= 1:
            txt = txt.replace(".", "")
    try:
        return float(txt)
    except Exception:
        return None


def money(value):
    try:
        if value is None or pd.isna(value):
            return "-"
        n = float(value)
        return "$ " + f"{n:,.0f}".replace(",", ".")
    except Exception:
        return str(value)


def canonical_piece(tipo):
    t = normalize(tipo)
    if "parab" in t:
        return "parabrisas"
    if "luneta" in t:
        return "luneta"
    return "vidrio de puerta"


def find_column(df, options):
    cols = {normalize(c): c for c in df.columns}
    for op in options:
        opn = normalize(op)
        for norm, original in cols.items():
            if opn == norm or opn in norm:
                return original
    return None


def brand_aliases(brand):
    b = normalize(brand)
    aliases = {
        "ford": ["ford", "fo"],
        "fiat": ["fiat", "fi"],
        "volkswagen": ["volkswagen", "vw", "volks"],
        "chevrolet": ["chevrolet", "ch", "chev", "gm"],
        "renault": ["renault", "re"],
        "peugeot": ["peugeot", "pe"],
        "citroen": ["citroen", "ci"],
        "toyota": ["toyota", "to"],
        "nissan": ["nissan", "ni"],
        "honda": ["honda", "ho"],
    }
    return aliases.get(b, [b])


def extract_year_ranges(text):
    d = normalize(text)
    ranges = []
    for pat in [r"(\d{2})\s*[-/]\s*(\d{2})", r"(\d{4})\s*[-/]\s*(\d{4})"]:
        for m in re.finditer(pat, d):
            a, b = m.groups()
            a, b = int(a), int(b)
            if a < 100:
                a += 2000 if a < 40 else 1900
            if b < 100:
                b += 2000 if b < 40 else 1900
            ranges.append((a, b))
    return ranges


def year_ok(desc, year):
    if not year:
        return True
    try:
        y = int(str(year)[:4])
    except Exception:
        return True
    ranges = extract_year_ranges(desc)
    if not ranges:
        return True
    return any(a <= y <= b for a, b in ranges)


def piece_ok(desc, tipo):
    d = normalize(desc)
    p = canonical_piece(tipo)
    if p == "parabrisas":
        return any(x in d for x in ["parab", "parabrisa", "pbr", "psas"])
    if p == "luneta":
        return any(x in d for x in ["luneta", "lun", "ltas"])
    return any(x in d for x in ["puerta", "lateral", "vidrio", "vde", "vdi", "dde", "ddi", "cristal"])


def captor_ok(desc, filtro):
    if filtro == "Todos":
        return True
    d = normalize(desc)
    tiene = any(x in d for x in ["captor", "sensor", "lluvia", "rain"])
    if filtro == "Con captor":
        return tiene
    if filtro == "Sin captor":
        return not tiene
    return True


def vehicle_tokens(modelo):
    bad = {"auto", "modelo", "version", "nuevo", "viejo"}
    return [t for t in normalize(modelo).split() if len(t) >= 3 and t not in bad]


def score_row(desc, marca, modelo, year, tipo, captor_filter):
    d = normalize(desc)

    if not piece_ok(d, tipo):
        return -999

    if canonical_piece(tipo) == "parabrisas" and not captor_ok(d, captor_filter):
        return -999

    aliases = brand_aliases(marca)
    brand_match = any(re.search(rf"\b{re.escape(a)}\b", d) for a in aliases if a)
    if marca and not brand_match:
        return -999

    tokens = vehicle_tokens(modelo)
    if tokens:
        model_matches = sum(1 for t in tokens if t in d)
        if model_matches == 0:
            return -999
    else:
        model_matches = 0

    if not year_ok(d, year):
        return -999

    score = 30
    score += 40 if brand_match else 0
    score += model_matches * 40
    score += 30 if year_ok(d, year) else 0
    if extract_year_ranges(d):
        score += 20
    return score


@st.cache_data(show_spinner=False)
def load_lists():
    LISTAS_DIR.mkdir(exist_ok=True)
    rows = []
    for file in LISTAS_DIR.glob("*.xlsx"):
        if file.name.lower() == "listas_colocacion.xlsx":
            continue
        proveedor = file.stem.replace("_", " ").replace("-", " ").title()
        try:
            excel = pd.ExcelFile(file)
            for sheet in excel.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet)
                if df.empty:
                    continue
                df.columns = [str(c).strip() for c in df.columns]
                code_col = find_column(df, ["codigo", "cod", "item", "articulo"])
                desc_col = find_column(df, ["descripcion", "detalle", "producto", "articulo", "nombre"])
                price_col = find_column(df, ["precio", "importe", "valor", "lista"])

                if desc_col is None:
                    desc_col = df.columns[min(1, len(df.columns)-1)]

                if price_col is None:
                    candidates = []
                    for c in df.columns:
                        if df[c].apply(parse_price).notna().sum() > max(2, len(df) * 0.15):
                            candidates.append(c)
                    price_col = candidates[-1] if candidates else df.columns[-1]

                for _, r in df.iterrows():
                    desc = r.get(desc_col, "")
                    price = parse_price(r.get(price_col, None))
                    if not str(desc).strip() or price is None:
                        continue
                    rows.append({
                        "proveedor": proveedor,
                        "codigo": r.get(code_col, "") if code_col else "",
                        "descripcion": str(desc),
                        "precio": price,
                        "archivo": file.name,
                        "hoja": sheet
                    })
        except Exception as e:
            st.warning(f"No pude leer {file.name}: {e}")

    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def load_colocacion():
    if not COLOCACION_FILE.exists():
        return {}
    try:
        df = pd.read_excel(COLOCACION_FILE)
        df.columns = [str(c).strip() for c in df.columns]
        tipo_col = find_column(df, ["tipo", "pieza", "articulo", "vidrio"])
        price_col = find_column(df, ["precio", "importe", "valor", "colocacion"])
        if tipo_col is None or price_col is None:
            return {}
        out = {}
        for _, r in df.iterrows():
            tipo = canonical_piece(r.get(tipo_col, ""))
            precio = parse_price(r.get(price_col, None))
            if precio is not None:
                out[tipo] = precio
        return out
    except Exception:
        return {}


def img_to_b64(uploaded):
    image = Image.open(uploaded).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def detect_vehicle(uploaded, manual=""):
    if manual.strip():
        txt = manual.strip()
        year = ""
        m = re.search(r"(19|20)\d{2}", txt)
        if m:
            year = m.group(0)
        parts = txt.replace(year, "").split()
        marca = parts[0] if parts else ""
        modelo = " ".join(parts[1:]) if len(parts) > 1 else txt
        return {"marca": marca, "modelo": modelo, "anio": year, "detalle": txt}

    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        st.error("Falta API Key fija. Cargá OPENAI_API_KEY en Secrets de Streamlit Cloud.")
        return None

    client = OpenAI(api_key=api_key)
    b64 = img_to_b64(uploaded)
    prompt = """
    Identificá el vehículo de la foto para buscar cristales.
    Devolvé SOLO JSON válido:
    {"marca":"", "modelo":"", "anio":"", "detalle":""}
    Si no sabés año exacto, estimá año probable.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]
        }],
        temperature=0.1
    )
    content = response.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()
    data = json.loads(content)
    return {
        "marca": str(data.get("marca", "")).strip(),
        "modelo": str(data.get("modelo", "")).strip(),
        "anio": str(data.get("anio", "")).strip()[:4],
        "detalle": str(data.get("detalle", "")).strip()
    }


def search(df, vehicle, tipo, captor_filter):
    rows = []
    for _, r in df.iterrows():
        s = score_row(
            r["descripcion"],
            vehicle.get("marca", ""),
            vehicle.get("modelo", ""),
            vehicle.get("anio", ""),
            tipo,
            captor_filter
        )
        if s > 0:
            item = r.to_dict()
            item["coincidencia"] = s
            rows.append(item)

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["precio", "coincidencia"], ascending=[True, False])


def whatsapp_url(tipo, precio_cristal, colocacion, total):
    pieza = canonical_piece(tipo)
    if colocacion:
        msg = (
            f"Hola! 👋\n\n"
            f"Te paso el precio del artículo {pieza} que solicitaste.\n\n"
            f"🪟 Cristal: {money(precio_cristal)}\n"
            f"🔧 Colocación: {money(colocacion)}\n"
            f"💰 Total final: {money(total)}\n\n"
            f"Cualquier consulta, estamos a disposición 😊\n"
            f"🔧 Autopartes Centro"
        )
    else:
        msg = (
            f"Hola! 👋\n\n"
            f"Te paso el precio del artículo {pieza} que solicitaste, {money(precio_cristal)}.\n\n"
            f"Cualquier consulta, estamos a disposición 😊\n"
            f"🔧 Autopartes Centro"
        )
    return f"https://wa.me/{WHATSAPP_NUMERO}?text={urllib.parse.quote(msg)}"


# =========================
# INTERFAZ
# =========================
if LOGO_PATH.exists():
    logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
    logo_html = f'<img class="ac-logo" src="data:image/jpeg;base64,{logo_b64}" />'
else:
    logo_html = '<div class="ac-logo"></div>'

st.markdown(
    f"""
    <div class="ac-header">
        {logo_html}
        <div class="ac-title-wrap">
            <div>
                <span class="ac-badge">🚘 IA VIDRIOS</span>
                <span class="ac-badge">🔧 AUTOPARTES CENTRO</span>
            </div>
            <h1>Buscador IA de vidrios</h1>
            <p>Sacá o subí una foto, elegí el tipo de vidrio y compará precios entre proveedores ya cargados.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="info-box">🌐 Versión online lista: usá cámara o subí foto desde el celular.</div>', unsafe_allow_html=True)

tipo = st.selectbox("¿Qué querés buscar?", ["Parabrisas", "Luneta", "Vidrio de puerta"])

captor_filter = "Todos"
if canonical_piece(tipo) == "parabrisas":
    captor_filter = st.selectbox("Sensor / captor", ["Todos", "Con captor", "Sin captor"])

agregar_colocacion = st.checkbox("🔧 Agregar colocación", value=False)

st.header("📋 Listas de precios fijas")
st.caption("La app carga automáticamente todos los Excel que estén dentro de la carpeta `listas_precios`. El nombre del archivo se usa como nombre del proveedor.")

df_prices = load_lists()
colocaciones = load_colocacion()

proveedores = 0 if df_prices.empty else df_prices["proveedor"].nunique()
productos = 0 if df_prices.empty else len(df_prices)

st.markdown(f'<div class="count-box">Listas fijas cargadas: <b>{proveedores} proveedor(es)</b> / <b>{productos} productos</b> en total</div>', unsafe_allow_html=True)

with st.expander("Ver proveedores cargados"):
    if df_prices.empty:
        st.warning("Todavía no hay listas cargadas.")
    else:
        for p in sorted(df_prices["proveedor"].unique()):
            st.write(f"🏪 {p}")

st.subheader("Foto del auto")

modo = st.radio("", ["Subir foto", "Sacar foto con cámara"], horizontal=True)

foto = None
if modo == "Subir foto":
    foto = st.file_uploader("Subí una foto del auto", type=["jpg", "jpeg", "png"])
else:
    foto = st.camera_input("Sacá una foto del auto")

manual = st.text_input("Búsqueda manual opcional", placeholder="Ej: Ford EcoSport 2018")

col_a, col_b = st.columns([1, 1])
with col_a:
    buscar = st.button("🔎 Detectar auto y comparar precios")
with col_b:
    nueva = st.button("🔄 Nueva búsqueda")

if nueva:
    st.rerun()

if foto:
    st.image(foto, caption="Foto cargada", use_container_width=True)

if buscar:
    if df_prices.empty:
        st.error("No hay listas de precios cargadas.")
        st.stop()

    if not foto and not manual.strip():
        st.error("Subí una foto o escribí una búsqueda manual.")
        st.stop()

    with st.spinner("Detectando auto y buscando coincidencias..."):
        vehicle = detect_vehicle(foto, manual)

    if not vehicle:
        st.stop()

    st.markdown("### 🔍 Búsqueda manual")
    st.write(f"**{vehicle.get('marca','')} {vehicle.get('modelo','')} — {vehicle.get('anio','')}**")
    st.write(f"**Pieza:** {tipo}")

    results = search(df_prices, vehicle, tipo, captor_filter)

    if results.empty:
        st.error("No encontré coincidencias exactas por marca + modelo + año. Probá búsqueda manual o revisá cómo aparece cargado en los Excel.")
        st.stop()

    best = results.iloc[0].to_dict()
    precio_cristal = best["precio"]
    colocacion = 0

    if agregar_colocacion:
        colocacion = colocaciones.get(canonical_piece(tipo), 0)
        if colocacion == 0:
            st.warning("Colocación activada, pero todavía falta cargar `listas_colocacion.xlsx` con precios.")

    total = precio_cristal + colocacion
    wa = whatsapp_url(tipo, precio_cristal, colocacion, total)

    st.markdown('<div class="best-box">', unsafe_allow_html=True)
    st.markdown("### 🏆 Mejor precio encontrado")
    st.write(f"🏪 **Proveedor:** {best.get('proveedor','')}")
    st.write(f"🔢 **Código:** {best.get('codigo','')}")
    st.write(f"📝 **Descripción:** {best.get('descripcion','')}")
    st.write(f"🪟 **Cristal:** {money(precio_cristal)}")
    st.write(f"🔧 **Colocación:** {money(colocacion) if colocacion else 'No incluida'}")
    st.write(f"💰 **Total final:** {money(total)}")
    st.markdown(f"[📲 Enviar cotización por WhatsApp]({wa})")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Resultados en la lista")
    show = results.head(20).copy()
    show["precio"] = show["precio"].apply(money)
    st.dataframe(
        show[["proveedor", "codigo", "descripcion", "precio", "coincidencia"]],
        use_container_width=True,
        hide_index=True
    )
