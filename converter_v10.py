import pandas as pd
import json
import os
import glob
import numpy as np

# --- 設定 ---
INPUT_EXCEL = 'neko_finance.xlsx'
OUTPUT_FILE = 'js/data/data.js'

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super(NpEncoder, self).default(obj)

def load_data():
    if os.path.exists(INPUT_EXCEL):
        print(f"Loading Excel: {INPUT_EXCEL}")
        try:
            return pd.read_excel(INPUT_EXCEL, sheet_name='Expenditure'), pd.read_excel(INPUT_EXCEL, sheet_name='Revenue')
        except Exception as e: print(f"Excel load failed: {e}")
    tsvs = glob.glob("*.tsv") + glob.glob("*.csv")
    df_exp = None
    df_rev = None
    for f in tsvs:
        sep = '\t' if f.endswith('.tsv') else ','
        if 'exp' in f.lower() or '支出' in f: df_exp = pd.read_csv(f, sep=sep)
        elif 'rev' in f.lower() or '収入' in f: df_rev = pd.read_csv(f, sep=sep)
    return df_exp, df_rev

def clean_df(df):
    if df is None: return pd.DataFrame()
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    df = df.dropna(subset=['Year'])
    df['Year'] = df['Year'].astype(int)
    if 'Amount' in df.columns: df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0).astype(int)
    if 'Planned_Investment' in df.columns: df['Planned_Investment'] = pd.to_numeric(df['Planned_Investment'], errors='coerce').fillna(0).astype(int)
    return df

def main():
    df_exp, df_rev = load_data()
    if df_exp is None or df_rev is None: print("Error: Input files not found."); return
    df_exp = clean_df(df_exp)
    df_rev = clean_df(df_rev)
    project_master = {}
    def update_master(df):
        if 'Project_ID' not in df.columns: return
        for _, row in df.iterrows():
            pid = str(row['Project_ID'])
            name = str(row.get('Project_Name', ''))
            group = str(row.get('Group_Name', ''))
            if pid not in project_master: project_master[pid] = {'name': '不明', 'group': 'その他'}
            if name and name != 'nan': project_master[pid]['name'] = name
            if group and group != 'nan': project_master[pid]['group'] = group
    update_master(df_exp)
    update_master(df_rev)
    years = sorted(list(set(df_exp['Year'].unique()) | set(df_rev['Year'].unique())))
    neko_data = {}
    for year in years:
        print(f"Processing Year: {year}...")
        year_str = str(year)
        exp_y = df_exp[df_exp['Year'] == year]
        rev_y = df_rev[df_rev['Year'] == year]
        all_pids = set(exp_y['Project_ID'].unique()) | set(rev_y['Project_ID'].unique())
        acc_values = { 'tax_revenue': 0, 'subsidy': 0, 'loan_in': 0, 'dividend_in': 0, 'asset_sold': 0, 'carried_forward': 0, 'direct_biz': 0, 'support_biz': 0, 'loan_repay': 0, 'loan_out': 0, 'dividend_out': 0, 'asset_buy': 0 }
        sub_projects_data = []
        for pid in all_pids:
            info = project_master.get(str(pid), {'name': '不明', 'group': 'その他'})
            p_exp_rows = exp_y[exp_y['Project_ID'] == pid]
            p_rev_rows = rev_y[rev_y['Project_ID'] == pid]
            val_exp = int(p_exp_rows['Amount'].sum())
            val_rev = int(p_rev_rows['Amount'].sum())
            val_budget = int(p_exp_rows['Planned_Investment'].fillna(0).sum()) if 'Planned_Investment' in p_exp_rows.columns else 0
            kpi_txt = f"予算比 {(val_exp/val_budget*100):.0f}%" if val_budget > 0 else (f"売上 {val_rev:,}円" if val_rev > 0 else "-")
            sub_projects_data.append({ "id": str(pid), "name": info['name'], "group": info['group'], "amount": val_exp, "recovery_target": 0.0, "financials": { "revenue": val_rev, "expenditure": val_exp, "budget": val_budget }, "pnl_kpi": { "kpi_actual": kpi_txt } })
            if "直営" in info['group']: acc_values['direct_biz'] += val_exp
            elif "支援" in info['group']: acc_values['support_biz'] += val_exp
            elif "貸付" in info['group']: acc_values['loan_out'] += val_exp
            elif "返済" in info['group']: acc_values['loan_repay'] += val_exp
            elif "資産" in info['group']: acc_values['asset_buy'] += val_exp
            elif "配当" in info['group']: acc_values['dividend_out'] += val_exp
            else: acc_values['direct_biz'] += val_exp
            acc_values['tax_revenue'] += val_rev
        distributions = []
        if sub_projects_data:
            df_sub = pd.DataFrame(sub_projects_data)
            for g_name, g_df in df_sub.groupby('group'):
                g_total_exp = int(g_df['amount'].sum())
                g_total_rev = int(sum(d['financials']['revenue'] for d in g_df.to_dict('records')))
                g_id = "direct"
                if "支援" in g_name: g_id = "support"
                elif "貸付" in g_name: g_id = "loan_out"
                elif "返済" in g_name: g_id = "loan_repay"
                elif "資産" in g_name: g_id = "asset_buy"
                distributions.append({ "id": g_id, "name": g_name, "type": "事業", "amount": g_total_exp, "recovery_target": 0.0, "financials": { "revenue": g_total_rev, "expenditure": g_total_exp }, "balanceSheet": { "assets_column": [{"label": "収益", "value": g_total_rev}], "liabilities_column": [{"label": "支出", "value": g_total_exp}], "netAssets": g_total_rev - g_total_exp }, "sub_projects": g_df.to_dict('records') })
        total_rev = sum([acc_values[k] for k in ['tax_revenue', 'subsidy', 'loan_in', 'asset_sold']])
        total_exp = sum([acc_values[k] for k in ['direct_biz', 'support_biz', 'loan_repay', 'loan_out', 'asset_buy']])
        neko_data[year_str] = { "year": int(year), "generalAccount": { "values": acc_values, "netAssets": total_rev - total_exp }, "distributions": distributions }
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f: f.write(f"/** Auto-generated by converter_v10.py */\nexport const NEKO_CITY_DATA = {json.dumps(neko_data, ensure_ascii=False, indent=4, cls=NpEncoder)};\n")
    print(f"Success! Generated {OUTPUT_FILE}")

if __name__ == "__main__": main()
