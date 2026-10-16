import pandas as pd
import matplotlib.pyplot as plt
import os

# --- FILE PATHS ---
file_path_ensemble = r'model\dati_bitcoin_ensemble.csv'
file_path_true = r'model\dati_btc.csv'

# --- ENSEMBLE CONFIG ---
colonna_prezzo = 'model-price'
colonna_switch = 'tick-switch-fase'
colonna_counter = 'above-threshold-counter'
FINESTRA_PRE_STACCO = 100  # Quanti tick prima della Fase 2 vogliamo visualizzare

print("Caricamento dei dati in corso...")

if not os.path.exists(file_path_ensemble) or os.path.getsize(file_path_ensemble) == 0:
    print(f"ERRORE: File ensemble inesistente o vuoto.")
    exit()

header_row_index = -1
with open(file_path_ensemble, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if '[run number]' in line:
            header_row_index = i
            break

df = pd.read_csv(file_path_ensemble, skiprows=header_row_index, dtype=str)
df = df[['[run number]', '[step]', colonna_prezzo, colonna_switch, colonna_counter]].copy()
df.columns = ['run', 'tick', 'prezzo', 'tick_switch', 'counter']

for col in ['run', 'tick', 'prezzo', 'tick_switch', 'counter']:
    df[col] = df[col].astype(str).str.replace('"', '', regex=False).str.replace("'", '', regex=False).str.replace(',', '.', regex=False).str.strip()
    df[col] = pd.to_numeric(df[col], errors='coerce')

df = df.dropna()

tick_stacco_automatico = int(df['tick_switch'].iloc[0])
max_tick_simulato = int(df['tick'].max())
tick_inizio_grafico = max(0, tick_stacco_automatico - FINESTRA_PRE_STACCO)

# ==========================================
# 2. IDENTIFICAZIONE RUN VALIDE E SCARTATE
# ==========================================
run_valide_set = set()
for run_id, group_data in df.groupby('run'):
    dati_fase1 = group_data[group_data['tick'] <= tick_stacco_automatico]
    # Se il counter ha superato 5 prima dello stacco, la run è valida
    if (dati_fase1['counter'] > 5).any():
        run_valide_set.add(run_id)

# Aggiungiamo una colonna Booleana (True/False) per filtrare comodamente
df['a_regime'] = df['run'].isin(run_valide_set)
run_valide = len(run_valide_set)
run_scartate = df['run'].nunique() - run_valide

y_min_window = float('inf')
y_max_window = float('-inf')

# ==========================================
# 3. GENERAZIONE GRAFICO (ENSEMBLE)
# ==========================================
plt.figure(figsize=(14, 8))

label_blue_added = False
label_red_added = False

for run_id, group_data in df.groupby('run'):
    group_data = group_data.sort_values('tick')
    plot_data = group_data[group_data['tick'] >= tick_inizio_grafico]
    if plot_data.empty: continue

    y_min_window = min(y_min_window, plot_data['prezzo'].min())
    y_max_window = max(y_max_window, plot_data['prezzo'].max())
    
    a_regime = group_data['a_regime'].iloc[0]
    
    if a_regime:
        colore = '#1f77b4' 
        label = 'Simulazione: A Regime' if not label_blue_added else None
        label_blue_added = True
    else:
        colore = 'red'     
        label = 'Simulazione: Non a Regime' if not label_red_added else None
        label_red_added = True

    plt.plot(
        plot_data['tick'], 
        plot_data['prezzo'], 
        alpha=0.20, # Leggermente più trasparenti per far risaltare le medie
        linewidth=1.2,
        color=colore,
        label=label,
        zorder=1
    )

# ==========================================
# 4. CALCOLO E PLOT DELLE MEDIE
# ==========================================
# Isoliamo solo i tick che ci interessa disegnare
df_window = df[df['tick'] >= tick_inizio_grafico]

# Media di TUTTE le run
media_tutti = df_window.groupby('tick')['prezzo'].mean()
plt.plot(
    media_tutti.index, 
    media_tutti.values, 
    color='darkorange', 
    linewidth=3, 
    linestyle='--', 
    label='Valore Medio (Tutte le Run)', 
    zorder=6
)

# Media delle SOLAS RUN VALIDE
df_valide_window = df_window[df_window['a_regime']]
if not df_valide_window.empty:
    media_valide = df_valide_window.groupby('tick')['prezzo'].mean()
    plt.plot(
        media_valide.index, 
        media_valide.values, 
        color='limegreen', 
        linewidth=3.5, 
        linestyle='-', 
        label='Valore Medio (Solo Valide)', 
        zorder=7
    )

# ==========================================
# 5. CARICAMENTO E PLOT DATI REALI (TRUE BTC)
# ==========================================
if os.path.exists(file_path_true):
    df_true = pd.read_csv(file_path_true, header=None)
    true_prices = pd.to_numeric(df_true[1], errors='coerce').dropna().values
    
    true_prices_plot = true_prices[tick_inizio_grafico : max_tick_simulato + 1]
    ticks_reali = range(tick_inizio_grafico, tick_inizio_grafico + len(true_prices_plot))
    
    if len(true_prices_plot) > 0:
        y_min_window = min(y_min_window, min(true_prices_plot))
        y_max_window = max(y_max_window, max(true_prices_plot))
    
    plt.plot(
        ticks_reali, 
        true_prices_plot, 
        color='black', 
        linewidth=2.5, 
        label='Prezzo Reale (True BTC)',
        zorder=10
    )

# ==========================================
# 6. ESTETICA FINALE E LIMITI DINAMICI
# ==========================================
plt.title(f'Focus Transizione (Valide: {run_valide} | Scartate: {run_scartate})', fontsize=16, fontweight='bold')
plt.xlabel('Tick temporali', fontsize=12)
plt.ylabel('Prezzo (USD)', fontsize=12)

# Linea di switch
plt.axvline(
    x=tick_stacco_automatico, 
    color='black', 
    linestyle=':', 
    linewidth=2, 
    label=f'Inizio Fase 2 (Tick {tick_stacco_automatico})',
    zorder=5
)

plt.xlim(tick_inizio_grafico, max_tick_simulato)

margine_y = (y_max_window - y_min_window) * 0.05
plt.ylim(y_min_window - margine_y, y_max_window + margine_y)

# Spostiamo la legenda per renderla più leggibile dato il numero di voci
plt.legend(fontsize=11, loc='upper left', bbox_to_anchor=(1.01, 1), borderaxespad=0.)

plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()

print(f"Grafico aggiornato! Run valide: {run_valide}, Run rosse: {run_scartate}")
plt.show()