# HANDOFF — Dashboard Solar FERCHEGAS EL VIEJÓN
**Fecha:** 26 mayo 2026  
**Estado:** Activo · Streamlit corriendo en http://localhost:8501

---

## Meta principal

Construir un sistema de monitoreo y pronóstico de generación solar para **FERCHEGAS EL VIEJÓN** (45 kWp, Veracruz) que:

1. **Reporte en tiempo real** el estado de generación vs pronóstico oficial (CFE/operador).
2. **Supere al pronóstico oficial** con un modelo propio de machine learning (GBM Lean).
3. **Pronostique los días restantes del mes** usando el modelo entrenado en datos propios de la planta.
4. **Valide automáticamente** el forecast contra datos reales conforme se van recibiendo los reportes semanales.

El modelo GBM ya demostró su valor: MAPE 5.5% vs 14.4% del pronóstico oficial en la validación del 18–24 mayo 2026 (5 de 7 días ganados, error semanal +32 kWh vs +157 kWh del oficial).

---

## Archivos activos

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app.py` | Python · 1,182 líneas | Dashboard Streamlit — **archivo principal** |
| `Modelos_Prediccion.ipynb` | Notebook · 18 celdas | Análisis de modelos horario y diario (+1h, +1d) con ACF |
| `Forecast_Solar_FERCHEGAS.ipynb` | Notebook · 27 celdas | Forecast combinado (perfil+análogo+GBM) con validación |
| `.streamlit/config.toml` | Config | Tema verde del dashboard |
| `Ferchegas_El_viejon_3años.xls` | Datos horarios | Serie completa 2024–may2026 (20,808 registros) |
| `Ferchegaselviejon_generacioncompleto.csv` | Datos diarios | Serie diaria para KPIs y tendencia |
| `Clima_ferchegaselviejon.csv` | Clima horario | Irradiación, nubosidad, temp, humedad, viento |
| `Reporte_generacion_FERCHEGAS_EL_VIEJÓN_18_may_2026_-_24_may_2026.xls` | Validación | Datos reales may 18–24 para comparar vs forecast |

---

## Estado actual del código

### `app.py` — Dashboard Streamlit

**KPIs (líneas 308–353):**
- Generación total, promedio diario, cumplimiento pronóstico, variabilidad
- Función `kpi()` con altura fija `105px` para que todos los cuadros sean iguales
- Sin emojis (removidos en esta sesión: ☀️ del page_icon, sidebar y 🔋 del header)

**Tab 1 — Estado Actual:** Real vs Pronóstico horario + error + perfil horario con banda ±1σ

**Tab 2 — Contexto Estacional:** Heatmap hora×mes + perfiles por mes + boxplot mensual histórico

**Tab 3 — Histórico:** Generación mensual por año + barras+MM3 + acumulada anual 2024–2026

**Tab 4 — Tendencia:** Scatter diario con regresión (+1.11 kWh/día/día, p<0.0001) + mes actual vs histórico + días sobre promedio por mes

**Tab 5 — Pronóstico (líneas 690–1182):**
```
Fila 1: Tabla métricas GBM vs Oficial (6 métricas) + 4 barras comparativas
Fila 2: Evolución mensual del MAPE (2 paneles: MAPE + delta mensual)
Fila 3: Generación diaria año test vs GBM (línea roja) vs Oficial (gris punteado)
Fila 4: Generación diaria mes actual:
         - Barras VERDE_MED = real (días 1-17)
         - Barras rojo semitransparente = GBM validación (mismos días)
         - Barras rojo sólido = forecast (días 18-31)
Fila 5: Tabla validación + gráfico barras agrupadas (si existe Reporte del mes)
```

**Modelo GBM en el dashboard** (`train_gbm_model`, línea 149):
- Features: `lag1,lag2,lag3,lag4,Hora,Mes,dow,rs3,rs6,rm6`
- Entrena en `año_max - 1` (2025), predice generación HORA ACTUAL
- Test en 2024 + 2026 (fuera de muestra)
- Métricas: RMSE~4.07 kWh/h, R²~0.85, MAPE~29.7% (horas diurnas >1 kWh/h)
- El forecast mensual corrige con ratio 2026/pred + irradiación diaria CSV + tendencia lineal

**Validación automática** (líneas 1019–1115):
- Busca archivos `Reporte_generacion_FERCHEGAS*{mes}*{año}*.xls` en la carpeta DATA
- Si existe y tiene días del período pronosticado → muestra tabla + gráfico agrupado
- Colores tabla: verde=error<10 kWh, naranja=10-30 kWh, rojo≥30 kWh
- Envuelto en `try/except` para no romper el tab si falta el archivo

### `Modelos_Prediccion.ipynb` — Análisis de modelos

**Celdas 1–2:** Setup, carga datos horarios + irradiación diaria  
**Celdas 3–7:** Modelo horario +1h (predice siguiente hora):
- Features con `lag0` (hora actual) como el más importante
- `FEATS_H = [lag0, hora_sin/cos, mes_sin/cos, diurno, Pron_kWh, irr_dia, lag1-4, rs3/6/24, rm6]`
- Métricas: RMSE=4.75, MAPE=17.1%, R²=0.72 (horas donde gen_actual>5 Y target>5)

**Celdas 8–11:** Modelo diario +1d (predice día siguiente):
- `lag0d` (generación de hoy) + `irr_lead1` (irradiación de mañana)
- `FEATS_D = [lag0d, lag1d-3d, lag7d, roll_mean/std 7/14, irr_lead1, irr_dia, irr_lag1, Mes, dow]`
- Métricas: RMSE=51.2, MAPE=21.4%, R²=0.38

**Celda 12:** Tabla comparativa de 3 modelos (dashboard, horario nuevo, diario nuevo)

**Celdas 13–15 (NUEVAS esta sesión):**
- Sección ACF — análisis de cuántos lags usar
- Código ACF: serie COMPLETA (incluye noches=0) para que lag24 = misma hora ayer
- **Hallazgo clave:** lag24 tiene ACF=0.88 (casi igual que lag1=0.93) y NO está en el modelo
- Lag48: ACF=0.86, también faltante
- Para el modelo diario: todos los lags 1–30 son significativos; lag14d (ACF=0.73) es el único faltante relevante
- Conclusión markdown: por qué el clima no está bien capturado (resolución temporal + variables sin usar)

### `Forecast_Solar_FERCHEGAS.ipynb` — Forecast combinado

**Celdas 1–15 (existentes):** Carga, perfil histórico, análogo -1año, forecast combinado 60/40, GBM diario con clima+tendencia, gráficos

**Celdas 16–17 (NUEVAS esta sesión — markdown + código validación):**
- Carga `Reporte_generacion_FERCHEGAS*18*may*.xls`
- Une con `daily_fc` que tiene `Gen_GBM` por día
- Calcula errores, determina ganador por día
- Tabla Plotly con colores del dashboard + gráfico barras agrupadas

---

## Todo lo hecho esta sesión

### Cambios en `app.py`

| Cambio | Líneas | Descripción |
|--------|--------|-------------|
| Quitar emojis | 16, 225, 258 | `☀️` y `🔋` eliminados |
| KPI misma altura | 89–94, 198–206 | `height:105px` fijo + placeholder invisible en cards sin delta |
| GBM Lean línea roja | 863 | `color=VERDE` → `color="#e53935"` en chart test |
| GBM validación rojo | 981 | `marker_color=VERDE_LIGHT` → `marker_color="#e53935"` |
| Forecast rojo | 987 | `marker_color="#FF8F00"` → `marker_color="#e53935"` |
| Validación automática | 1019–1115 | Tabla + gráfico Real vs Pronóstico vs GBM si hay reporte |

### Cambios en `Modelos_Prediccion.ipynb`

- Agregadas celdas 15–17: análisis ACF horario (serie completa, lag1–50) + ACF diario (lag1–30)
- Colores: azul=ya en modelo, verde=clave faltante, gris=no incluido
- Conclusión con valores reales: lag24=0.88, lag48=0.86, lag14d=0.73
- Explicación de por qué el clima no está capturado correctamente

### Cambios en `Forecast_Solar_FERCHEGAS.ipynb`

- Celdas de validación May 18–24 con tabla Plotly y gráfico de barras agrupadas
- Resultado: GBM MAPE 5.5% vs Oficial 14.4% | GBM ganó 5/7 días | error semanal +32 vs +157 kWh

---

## Lo que falló / tuvo que rehacerse

| Problema | Causa | Solución aplicada |
|----------|-------|------------------|
| `ValueError: NaN to integer` en Tab5 | `may_real` vacío cuando el mes no tiene datos en `cmp_h` | Guard `if len(may_real) else 0` |
| Forecast bars todas igual altura | Perfil usa medianas históricas fijas por hora — sin variación día a día | Agregar factor de irradiación diaria del CSV de clima + tendencia lineal |
| Título "2026 + 2026" en Tab5 | `train_yr+1=2026` y `dh["Anio"].max()=2026` | Computed `test_years` dinámicamente |
| MAPE = inf en modelo horario | Filtro `Gen_kWh > 1.0` mantenía horas donde Target=0 | Filtrar ambos: `Gen_kWh>5 AND Target>5` |
| R²=0.16 en modelo diario | `irr_lead1` ausente — usaba irradiación de hoy para predecir mañana | Añadir `irr_lead1 = irr_dia.shift(-1)` |
| sklearn features mismatch (11 vs 12) | Celda de simulación iterativa no incluyó `irr_lead1_fut` | Añadir el valor al array numpy |
| ACF daba lag24 engañoso | Usaba serie filtrada solo horas diurnas — lag24 no era "misma hora ayer" | Cambiar a serie COMPLETA (con noches=0) donde lag24 = clock exacto |
| Script Python no encontraba XLS | Nombre con ñ: `Ferchegas_El_viejon_3años.xls` — se usaba sin ñ | Usar `chr(241)` o glob para encontrar el archivo |
| `Write` tool no creaba archivos en OneDrive | Ruta de OneDrive tiene sincronización activa | Escribir scripts en `C:\Users\ajasa\AppData\Local\Temp\` y ejecutar desde ahí |

---

## Métricas de referencia (para comparar en la próxima sesión)

### Modelo GBM Dashboard (nowcast hora actual)
- Entrena: 2025 | Test: 2024+2026
- RMSE: ~4.07 kWh/h | MAPE: ~29.7% | R²: ~0.85

### Modelo GBM Horario nuevo (predice +1h)
- RMSE: 4.75 kWh/h | MAPE: 17.1% | R²: 0.72
- Features actuales: lag0–4, hora_sin/cos, mes_sin/cos, irr_dia, rs3/6/24, rm6

### Modelo GBM Diario nuevo (predice +1d)
- RMSE: 51.2 kWh/día | MAPE: 21.4% | R²: 0.38
- Features actuales: lag0d, lag1–3d, lag7d, irr_lead1, irr_dia, irr_lag1, roll_mean/std 7/14, Mes, dow

### Validación real May 18–24, 2026
- MAPE GBM Lean: **5.5%** | MAPE Pronóstico oficial: **14.4%**
- GBM ganó: 5/7 días | Error total semana: GBM +32 kWh vs Oficial +157 kWh

---

## Próximo paso (acordado)

### 1. Mejorar el modelo horario con lag24 y lag48

El ACF demostró que lag24 (ACF=0.88) y lag48 (ACF=0.86) son casi tan informativos como lag1 (0.93) y no están en el modelo. Agregar en `Modelos_Prediccion.ipynb`:

```python
# En feature engineering horario
df_h['lag24'] = df_h['Gen_kWh'].shift(24)   # misma hora ayer
df_h['lag48'] = df_h['Gen_kWh'].shift(48)   # misma hora anteayer

FEATS_H = ['lag0','hora_sin','hora_cos','mes_sin','mes_cos','diurno',
           'Pron_kWh','irr_dia',
           'lag1','lag2','lag3','lag4',
           'lag24','lag48',          # <-- NUEVO
           'rs3','rs6','rs24','rm6']
```

Impacto esperado: R² sube de 0.72 → ~0.82–0.85.

### 2. Reemplazar irradiación diaria por irradiación horaria

El CSV `Clima_ferchegaselviejon.csv` tiene datos horarios (columna `fh`). El modelo horario actualmente usa `irr_dia` (mismo valor para las 24 horas del día). Cambiar a:

```python
# En el notebook de modelos
clim_h = clim['irr'].reset_index()
clim_h.columns = ['Datetime', 'irr_hora']
df_h = df_h.merge(clim_h, on='Datetime', how='left')
df_h['irr_hora'] = df_h['irr_hora'].fillna(0)
# Reemplazar 'irr_dia' por 'irr_hora' en FEATS_H
```

### 3. Agregar nubosidad horaria (`nub`) como feature

La columna `nub` (0–8 oktas) del CSV es la variable climática más relevante para solar horario. Agregarla permitiría distinguir mañanas despejadas de tardes nubladas dentro del mismo día.

### 4. (Opcional) Incorporar el modelo mejorado al dashboard

Una vez validadas las mejoras en el notebook, replicar la función `train_gbm_model` en `app.py` con los nuevos features y actualizar el Tab 5.

---

## Arquitectura de datos

```
Ferchegas_El_viejon_3años.xls          → hourly: Datetime, Gen_kWh, Pron_kWh
Ferchegaselviejon_generacioncompleto.csv → daily:  Fecha, Gen_kWh
Clima_ferchegaselviejon.csv             → hourly: fh(datetime), irr, nub, hum, temp, vv
Reporte_generacion_FERCHEGAS_*.xls      → weekly: Fecha, Generación_kWh, Pronóstico_kWh
```

Los reportes semanales son la fuente de validación. Cada semana que llega uno nuevo, el Tab 5 del dashboard lo detecta automáticamente (busca por patrón de nombre de archivo) y muestra la tabla de validación actualizada.

---

## Cómo correr el dashboard

```powershell
cd "c:\Users\ajasa\OneDrive\Documentos\Graficos"
& "C:\Users\ajasa\AppData\Local\Programs\Python\Launcher\py.exe" -m streamlit run app.py
# Abre http://localhost:8501
```
