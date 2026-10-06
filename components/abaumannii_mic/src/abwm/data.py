"""Molecular features and provenance-preserving MIC curation, extracted from abwm."""
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold

FP_SIZE = 1024

def dump(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def fingerprint(smiles):
    m=Chem.MolFromSmiles(smiles)
    if m is None: raise ValueError('Invalid molecular structure')
    return rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=FP_SIZE,includeChirality=True).GetFingerprintAsNumPy(m).astype('float32')


def chemical_keys(smiles):
    m=Chem.MolFromSmiles(smiles)
    if m is None: raise ValueError('Invalid molecular structure')
    # Preserve tested full form in features; group salts and stereoisomers conservatively.
    fragments=Chem.GetMolFrags(m,asMols=True)
    parent=max(fragments,key=lambda x:x.GetNumHeavyAtoms())
    parent=rdMolStandardize.Uncharger().uncharge(parent)
    # ChEMBL parent-ID closure below also joins source-linked forms; no costly
    # partially converged tautomer enumeration is used to claim identity.
    key=Chem.MolToSmiles(parent,isomericSmiles=False)
    scaffold=MurckoScaffold.MurckoScaffoldSmiles(mol=parent,includeChirality=False) or 'ACYCLIC'
    return key,scaffold


def drugs(data_root):
    data_root = Path(data_root)
    saved = data_root / "curated/drugs.json"
    if saved.exists():
        return json.loads(saved.read_text())
    out={}
    for p in (data_root / 'raw/drug_structures').glob('*.json'):
        row=json.loads(p.read_text())['PropertyTable']['Properties'][0]
        smiles=row.get('SMILES') or row.get('IsomericSMILES') or row.get('ConnectivitySMILES')
        if smiles: out[p.stem]=dict(smiles=smiles,cid=row['CID'],source=str(p))
    return out


def freeze(name,frame,split_root):
    path=Path(split_root)/(name+'.csv'); path.parent.mkdir(parents=True,exist_ok=True)
    text=frame.to_csv(index=False)
    if path.exists():
        if path.read_text()!=text: raise RuntimeError(f'Frozen split changed: {path}; use a new experiment version')
    else:
        path.write_text(text); path.chmod(0o444)
    return hashlib.sha256(text.encode()).hexdigest()


def parse_mic(value,unit,relation='=',upper=None):
    if value is None or str(value).strip() in ['', 'nan','None']: return None
    value=str(value).strip().replace('≤','<=').replace('≥','>=')
    match=re.fullmatch(r'\s*(<=|>=|<|>|=)?\s*([0-9.]+(?:[eE][-+]?\d+)?)\s*',value)
    if not match: raise ValueError('Unsupported or missing MIC value')
    relation=match[1] or relation
    factor={'ug/mL':1,'ug.ml-1':1,'ug ml-1':1,'ug/mL-1':1,'ug ml(-1)':1,'ug.mL-1':1,
            'ug ml^-1':1,'mg/L':1,'mg l-1':1,'mg/l':1,'mg/mL':1000,'mg/ml':1000,
            'ug/ml':1,'µg/mL':1,'μg/mL':1,'ug ml(- 1)':1}.get(unit)
    if factor is None: raise ValueError('Unsupported unit or unverified molar tested form')
    v=float(match[2])*factor
    if not np.isfinite(v) or v<=0: raise ValueError('MIC must be finite and positive')
    lo=hi=float(np.log2(v)); censor='exact'
    if relation in ['<','<=']: lo=None; censor='left'
    elif relation in ['>','>=']: hi=None; censor='right'
    elif relation not in ['=','~']: raise ValueError('Unsupported relation')
    elif relation=='~': raise ValueError('Approximate MIC excluded')
    if upper is not None:
        if relation != '=': raise ValueError('Ambiguous inequality plus upper_value; retain raw record for review')
        u=float(upper)*factor
        if not np.isfinite(u) or u<v: raise ValueError('Conflicting MIC interval')
        hi=float(np.log2(u)); censor='interval' if u>v else 'exact'
    return dict(lower_log2=lo,upper_log2=hi,censor=censor,relation=relation,unit='ug/mL',raw_value=value,raw_unit=unit,
                lower_closed=relation not in ['>'],upper_closed=relation not in ['<'])


def group_split(key):
    x=int(hashlib.sha256(('abwm-v1:42:'+str(key)).encode()).hexdigest()[:8],16)/2**32
    return 'train' if x<.7 else ('val' if x<.85 else 'test')


def mic_split_path(scheme,data_root): return Path(data_root)/'splits'/f'mic_{scheme}_v3.csv'


def parent_closed_groups(df,column):
    """Hard grouping is the union of structural identity and supplied parent IDs."""
    roots={str(v):str(v) for v in df[column].unique()}
    def root(v):
        v=str(v)
        while roots[v]!=v:
            roots[v]=roots[roots[v]]; v=roots[v]
        return v
    for _,part in df[df.parent_id.notna() & df.parent_id.ne('')].groupby('parent_id'):
        keys=sorted({root(v) for v in part[column]})
        for key in keys[1:]: roots[root(key)]=root(keys[0])
    return df[column].map(lambda v:root(v)),{v:root(v) for v in roots}


def curate_mic(data_root):
    data_root = Path(data_root)
    CUR = data_root / "curated"
    SPLITS = data_root / "splits"
    records=[]; rejected=[]; seen=set(); structures={}
    for p in sorted((data_root / 'raw/chembl_mic').glob('activities_*.json')):
        for r in json.loads(p.read_text())['activities']:
            rid=str(r['activity_id'])
            if rid in seen: continue
            seen.add(rid)
            try:
                if r.get('type')!='MIC' or r.get('target_tax_id')!='470': raise ValueError('endpoint/taxon')
                if r.get('data_validity_comment'): raise ValueError('flagged validity')
                desc=(r.get('assay_description') or '')
                if re.search(r'\b(MIC\s*(?:50|90)|combination|combined|synerg\w*|predicted|calculated)\b',desc,re.I): raise ValueError('aggregate/combination/nonexperimental assay')
                label=parse_mic(r['value'],r['units'],r['relation'],r.get('upper_value'))
                if label is None: raise ValueError('missing MIC')
                smi=r.get('canonical_smiles')
                if not smi: raise ValueError('no structure')
                if smi not in structures:
                    key,scaff=chemical_keys(smi); structures[smi]=(key,scaff,fingerprint(smi))
                key,scaff,_=structures[smi]
                strain=re.search(r'\bATCC\s*[-:]?\s*(\d+)\b',desc,re.I)
                strain=('ATCC '+strain[1]) if strain else ''
                records.append(dict(record_id=rid,source_file=str(p),molecule_id=r['molecule_chembl_id'],parent_id=r['parent_molecule_chembl_id'],
                                    smiles=smi,compound_group=key,scaffold=scaff,study=r['document_chembl_id'],assay=r['assay_chembl_id'],
                                    strain=strain,strain_evidence='explicit_assay_description' if strain else 'unresolved',
                                    assay_description=desc,potential_duplicate=r['potential_duplicate'],src_id=r['src_id'],
                                    mic_world_eligible=False,mic_link='unresolved',**label))
            except (ValueError,TypeError) as e: rejected.append(dict(record_id=rid,reason=str(e),source_file=str(p)))
    df=pd.DataFrame(records)
    if df.empty: raise RuntimeError('No eligible MIC records after parsing')
    CUR.mkdir(parents=True,exist_ok=True)
    df.to_csv(CUR/'mic_measurements.csv',index=False)
    pd.DataFrame(rejected).to_csv(CUR/'mic_exclusions.csv',index=False)
    fps=np.stack([structures[s][2] for s in df.smiles])
    np.save(CUR/'mic_fingerprints.npy',fps)
    # Active response drugs are held consistently across chemical tasks.
    pins={}
    for drug,row in drugs(data_root).items():
        key,scaf=chemical_keys(row['smiles'])
        pins[drug]=(key,scaf,{'ciprofloxacin':'val','tetracycline':'test'}.get(drug,'train'))
    counts={}
    for scheme,column in [('compound','compound_group'),('scaffold','scaffold'),('study','study'),('isolate','strain')]:
        manifest=df[['record_id',column]].rename(columns={column:'group'}).copy()
        if scheme in ['compound','scaffold']:
            manifest['group'],aliases=parent_closed_groups(df,column)
        manifest['split']=manifest.group.map(group_split)
        if scheme in ['compound','scaffold']:
            for key,scaf,fold in pins.values():
                target=key if scheme=='compound' else scaf
                manifest.loc[manifest.group.eq(aliases.get(target,target)),'split']=fold
        if scheme=='isolate': manifest.loc[manifest.group.eq(''),'split']='excluded_unknown_isolate'
        # Within-source repeated parent/assay records stay together for all split definitions.
        digest=freeze('mic_'+scheme+'_v3',manifest,SPLITS)
        if scheme in ['compound','scaffold']:
            assert df.assign(fold=manifest.split).groupby('parent_id').fold.nunique().max()==1
        counts[scheme]=dict(groups=int(manifest[~manifest.split.str.startswith('excluded')].group.nunique()),
                            rows=manifest.split.value_counts().to_dict(),split_hash=digest)
    dump(CUR/'mic_summary.json',dict(downloaded_activities=len(seen),eligible=len(df),independent_structural_parents=counts['compound']['groups'],
         normalized_structure_keys=df.compound_group.nunique(),
         original_documents=df.study.nunique(),explicit_strains=df.loc[df.strain.ne(''),'strain'].nunique(),
         censoring=df.censor.value_counts().to_dict(),excluded=pd.Series([x['reason'] for x in rejected]).value_counts().to_dict(),splits=counts,
         compatible_world_model_records=0,scope='ChEMBL 37 species target seed cohort; not exhaustive organism-assay recall'))
    return counts
