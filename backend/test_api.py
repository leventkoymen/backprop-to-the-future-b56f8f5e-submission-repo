import sys, os, json
sys.path.insert(0, os.getcwd())
import api
c = api.app.test_client()
def show(label, r):
    j = r.get_json()
    keep = {k: j.get(k) for k in ['error','message','resolved','unknown','pairs_evaluated'] if k in j}
    if 'ranked' in j and isinstance(j['ranked'], list):
        keep['top'] = [(x['drug_a'], x['drug_b'], x['tier'], x['score']) for x in j['ranked'][:2]]
        keep['withheld'] = len(j['withheld'])
    if 'predicted_score' in j: keep.update(tier=j.get('tier'), score=j.get('predicted_score'), ranked=j.get('ranked'))
    print(f"\n[{r.status_code}] {label}\n   {json.dumps(keep)[:420]}")
show('pembrolizumab + docetaxel', c.post('/rank', json={'drugs': ['Pembrolizumab', 'Docetaxel']}))
show('pembrolizumab + 2 known', c.post('/rank', json={'drugs': ['pembrolizumab', 'Docetaxel', 'Gefitinib']}))
show('common names: tamoxifen, erlotinib, gemcitabine, taxol, cisplatin',
     c.post('/rank', json={'drugs': ['tamoxifen', 'erlotinib', 'gemcitabine', 'Taxol', 'cisplatin']}))
show('typo: docetaxol + gefitnib', c.post('/rank', json={'drugs': ['docetaxol', 'gefitnib']}))
show('one drug only', c.post('/rank', json={'drugs': ['Docetaxel']}))
show('empty + blank boxes', c.post('/rank', json={'drugs': ['', ' ']}))
show('no body', c.post('/rank'))
show('drugs as a string', c.post('/rank', json={'drugs': 'Docetaxel, Gefitinib'}))
show('bad top', c.post('/rank', json={'drugs': ['Docetaxel', 'Gefitinib'], 'top': 'abc'}))
show('NSC not in screen', c.post('/rank', json={'drugs': [123, 628503]}))
show('/pair by names', c.get('/pair/docetaxel/gefitinib'))
show('/pair by numbers (old way)', c.get('/pair/628503/715055'))
show('/pair unknown drug', c.get('/pair/Pembrolizumab/Docetaxel'))
show('/pair same drug', c.get('/pair/Docetaxel/docetaxel'))
show('/surface by names', c.get('/pair/Dactinomycin/tamoxifen/surface'))
show('/surface unknown', c.get('/pair/Pembrolizumab/Docetaxel/surface'))
show('missing route', c.get('/nonsense'))
show('vemurafenib resolves', c.post('/rank', json={'drugs': ['Vemurafenib', 'Zelboraf', 'Docetaxel']}))
