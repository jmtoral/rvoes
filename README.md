# RVOEs de educación superior en México

Tablas sistematizadas de los Reconocimientos de Validez Oficial de Estudios (RVOE) del tipo superior, a partir de dos fuentes públicas de la SEP.

| Archivo | Fuente | Contenido |
|---|---|---|
| **`data/rvoes.csv` / `.xlsx`** | ambas | **Tabla unificada**: todo SIRVOES + los RVOE vigentes que solo aparecen en DGAIR (`fuente`). `en_dgair` indica si DGAIR también lo lista; `nota` marca casos a revisar |
| `data/rvoes_dgair.csv` / `.xlsx` | [DGAIR – instituciones federales vigentes](https://dgair.sep.gob.mx/federales_vigentes) (5 PDFs) | RVOE federales **vigentes**: institución, estado, nivel, programa, modalidad, RVOE, fecha de otorgamiento |
| `data/rvoes_sirvoes.csv` / `.xlsx` | [SIRVOES](https://sirvoes.sep.gob.mx/sirvoes/mvc/consultas) | Programas **vigentes y retirados**, con plantel, municipio, domicilio, contacto, razón social, área de estudios, fechas de retiro y motivo |
| `data/cruce_dgair_sirvoes.csv` | ambas | Tabla DGAIR con el estatus que cada RVOE tiene en SIRVOES |

## Reproducir

```powershell
pip install -r requirements.txt
# 1. PDFs de DGAIR
mkdir data/pdfs
foreach ($f in "A_C","D_H","I_J","K_T","U_Z") { curl.exe -sL -o "data/pdfs/inst_fed_vig_$f.pdf" "https://dgair.sep.gob.mx/storage/recursos/DREOE/inst_fed_vig_$f.pdf" }
python parse_dgair.py data/pdfs
# 2. SIRVOES (≈1 h; reanudable, guarda el JSON crudo en data/sirvoes_raw/)
python scrape_sirvoes.py
# 3. Cruce
python cruce.py
```

## Cómo se unifican

- La base es SIRVOES, que trae más campos e incluye los retirados.
- Se agregan las filas de DGAIR cuyo RVOE no está en SIRVOES (casi todas otorgadas en 2025–2026: SIRVOES va rezagado). Estado, nivel y modalidad se homologan al catálogo de SIRVOES.
- Las instituciones con acuerdo secretarial (UVM, Tec, UNITEC, Anáhuac…) tienen en DGAIR una sola clave institucional (`ACUERDO 131`) y en SIRVOES una por programa (`ACUERDO 131/3067`). Se consideran cubiertas por SIRVOES cuando coincide la base del acuerdo.
- `nota = "acuerdo/decreto con clave irregular…"`: filas de DGAIR con claves mal escritas (`ACUERDO-131`, `DECRETO PRESIDENCIAL`) que no se pudieron cruzar; probablemente duplican un registro de SIRVOES.
- `nota = "retirado en SIRVOES pero DGAIR lo lista como vigente"`: discrepancias entre fuentes.

Notas:
- SIRVOES expone una API JSON (`/sirvoes/mvc/consultas/consultaGeneral` para los planteles de cada estado y `detallesIdPlantel` para los programas de cada plantel). El servidor solo acepta cifrados TLS antiguos, por eso el script baja `SECLEVEL` (el certificado se sigue verificando).
- Los registros de SIRVOES son informativos según la propia SEP. Ante cualquier inconsistencia, la autoridad educativa correspondiente es la que tiene la última palabra.
