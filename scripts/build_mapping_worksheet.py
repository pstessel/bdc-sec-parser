import hashlib
import json
import re
from pathlib import Path

import pandas as pd

base = Path('/home/phs/.openclaw/workspace/bdc-sec-parser/out/normalized')
infile = base / 'investments.csv'
outfile = base / 'mapping_worksheet_top_unknown_layouts.csv'

df = pd.read_csv(infile, low_memory=False)
unk = df[df['layout_id'] == 'sched_unknown'].copy()


def _norm(s: str) -> str:
    s = str(s or '').lower()
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _page_from_source(source_file: str):
    # Placeholder heuristic: return None when no explicit page marker exists in source path.
    m = re.search(r'page[_-]?(\d+)', str(source_file), re.I)
    return int(m.group(1)) if m else None


# Build per-table fingerprints/previews
profiles = {}
for (source_file, table_index), g in unk.groupby(['source_file', 'table_index'], dropna=False):
    g2 = g.sort_values('row_index')
    headerish = g2[g2['is_header_like'] == True].head(3)
    header_lines = [str(x) for x in headerish['clean_row_text'].fillna('').tolist() if str(x).strip()]
    if not header_lines:
        header_lines = [str(x) for x in g2['clean_row_text'].fillna('').head(2).tolist() if str(x).strip()]

    table_preview = ' || '.join(header_lines[:2])
    first_row_preview = str(g2['clean_row_text'].fillna('').head(1).tolist()[0] if len(g2) else '')

    sig_input = _norm(' | '.join(header_lines[:3]))
    table_signature = hashlib.sha1(sig_input.encode('utf-8')).hexdigest()[:12] if sig_input else 'na'

    profiles[(source_file, table_index)] = {
        'table_preview': table_preview,
        'table_first_row_preview': first_row_preview,
        'table_signature': table_signature,
        'page_number': _page_from_source(source_file),
    }


bucket = (
    unk.groupby(['ticker', 'form', 'period_focus'], dropna=False)
    .size()
    .reset_index(name='rows')
    .sort_values('rows', ascending=False)
    .head(12)
)

samples = []
for _, b in bucket.iterrows():
    part = unk[
        (unk['ticker'] == b['ticker'])
        & (unk['form'] == b['form'])
        & (unk['period_focus'] == b['period_focus'])
    ]
    header = part[part['is_header_like'] == True].head(3)
    data = part[part['is_header_like'] != True].head(5)
    take = pd.concat([header, data], ignore_index=True)

    for _, r in take.iterrows():
        key = (r.get('source_file'), r.get('table_index'))
        p = profiles.get(key, {})
        samples.append(
            {
                'ticker': r.get('ticker'),
                'form': r.get('form'),
                'period_focus': r.get('period_focus'),
                'source_file': r.get('source_file'),
                'page_number': p.get('page_number'),
                'table_index': r.get('table_index'),
                'table_signature': p.get('table_signature'),
                'table_preview': p.get('table_preview'),
                'table_first_row_preview': p.get('table_first_row_preview'),
                'row_index': r.get('row_index'),
                'clean_row_text': r.get('clean_row_text'),
                'cells_json': r.get('cells_json'),
                'numeric_count': r.get('numeric_count'),
                'confidence': r.get('confidence'),
                # Human annotation columns
                'is_target_schedule': '',
                'non_target_table_type': '',
                'map_issuer_col': '',
                'map_business_description_col': '',
                'map_principal_col': '',
                'map_cost_col': '',
                'map_fair_value_col': '',
                'map_rate_spread_pik_col': '',
                'map_maturity_col': '',
                'map_prior_period_cols': '',
                'map_ignore_cols': '',
                'notes': '',
            }
        )

out = pd.DataFrame(samples)
out.to_csv(outfile, index=False)
print(outfile)
print(len(out))
