"""Descarga todos los programas con RVOE de SIRVOES (sirvoes.sep.gob.mx) a CSV/XLSX.
Uso: python -I scrape_sirvoes.py  -> data/sirvoes_raw/*.json, data/rvoes_sirvoes.csv / .xlsx
Reanudable: los planteles ya descargados en data/sirvoes_raw/ no se vuelven a pedir.
"""
import json, ssl, time, urllib.request
from pathlib import Path
import pandas as pd

API = "https://sirvoes.sep.gob.mx/sirvoes/mvc/consultas/"
RAW = Path("data/sirvoes_raw")
FILTROS = dict(municipio="0", estatus="0", area="0", modalidad="0", nivel="0", trvoe="0",
               institucion=None, programa=None, acuerdo=None, indiceInferior=0, indiceSuperior=100000)
PAUSA = 0.3  # ponytail: pausa fija entre llamadas; subir si el servidor empieza a fallar
# El servidor de SEP solo negocia cifrados viejos; OpenSSL 3 los rechaza con SECLEVEL=2.
# Se sigue verificando el certificado, solo se baja el nivel de cifrado para este host.
CTX = ssl.create_default_context()
CTX.set_ciphers("DEFAULT:@SECLEVEL=0")

def post(endpoint, body, intentos=5):
    req = urllib.request.Request(API + endpoint, data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    for i in range(intentos):
        try:
            with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
                return json.load(r)
        except Exception as e:
            if i == intentos - 1:
                raise
            print(f"  reintento {endpoint} {body.get('idPlantel') or body.get('entidad')}: {e}")
            time.sleep(5 * (i + 1))

def descargar():
    RAW.mkdir(parents=True, exist_ok=True)
    for ent in range(1, 33):
        planteles = post("consultaGeneral", {**FILTROS, "entidad": str(ent)})
        print(f"entidad {ent}: {len(planteles)} planteles")
        for p in planteles:
            f = RAW / f"{p['idPlantel']}.json"
            if f.exists():
                continue
            progs = post("detallesIdPlantel", {"idPlantel": p["idPlantel"], "indiceInferior": 0, "indiceSuperior": 100000})
            f.write_text(json.dumps({"plantel": p, "programas": progs}, ensure_ascii=False), encoding="utf-8")
            time.sleep(PAUSA)

def s(x):
    return x.strip() if isinstance(x, str) else x

def aplanar():
    filas = []
    for f in RAW.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        id_plantel = d["plantel"]["idPlantel"]
        for x in d["programas"]:
            pl, ins = x["fkIdPlantel"], x["fkIdPlantel"]["fkIdInstitucion"]
            dirc, tel = pl["fkIdDireccion"] or {}, pl["fkIdTelefono"] or {}
            mun = dirc.get("fkIdMunicipio") or {}
            filas.append({
                "id_programa": x["idPrograma"], "llave": s(x["llave"]), "id_plantel": id_plantel,
                "institucion": s(ins["nombreInstitucion"]), "razon_social": s(ins["razonSocial"]),
                "grupo": s((ins["fkIdGrupo"] or {}).get("nombreGrupo")),
                "tipo_rvoe": s((ins["fkIdTipoRvoe"] or {}).get("nombreRvoe")),
                "autorizada_equivalencias": s(ins["autorizadaEquivalencias"]),
                "plantel": s(pl["nombrePlantel"]),
                "estado": s((mun.get("fkIdEntidad") or {}).get("nombreEntidad")), "municipio": s(mun.get("nombreMunicipio")),
                "domicilio": s(dirc.get("calle")), "cp": s(dirc.get("codigoPostal")),
                "telefono": " ".join(filter(None, [s(tel.get("lada")), s(tel.get("telefono"))])),
                "correo": s(pl["correoElect"]), "pagina_web": s(pl["paginaWeb"]), "excelencia": s(pl["excelencia"]),
                "nivel": s(x["fkIdNivel"]["descripcionNivel"]), "programa": s(x["nombrePrograma"]),
                "modalidad": s(x["fkIdModalidad"]["nombreModalidad"]), "area": s(x["fkIdArea"]["descripcionArea"]),
                "rvoe": s(x["acuerdo"]), "estatus": s(x["fkIdEstatus"]["nombreEstatus"]),
                "fecha_otorgamiento": s(x["fecOtorRvoe"]), "fecha_fin": s(x["fecFinRvoe"]),
                "fecha_retiro": s(x["fecRetiroRvoe"]), "motivo_retiro": s(x["fkIdMotivoRetiro"]["descripcionRetiro"]),
            })
    df = pd.DataFrame(filas).replace("", None)
    for c in ("fecha_otorgamiento", "fecha_fin", "fecha_retiro"):
        df[c] = pd.to_datetime(df[c], format="%d-%m-%Y", errors="coerce")
    return df.sort_values(["estado", "institucion", "plantel", "programa"])

if __name__ == "__main__":
    descargar()
    df = aplanar()
    df.to_csv("data/rvoes_sirvoes.csv", index=False, encoding="utf-8-sig")
    df.to_excel("data/rvoes_sirvoes.xlsx", index=False)
    print(f"{len(df)} programas, {df['id_plantel'].nunique()} planteles")
    print(df["estatus"].value_counts().to_string())
    assert df["rvoe"].notna().mean() > 0.99, "muchos programas sin RVOE: revisar el aplanado"
