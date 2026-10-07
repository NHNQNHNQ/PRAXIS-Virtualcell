"""Execute the dependency-free UI script against a small DOM and mocked API."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("species_reference", [False, True])
def test_ui_disables_unavailable_inputs_and_submits_a_real_combination(species_reference):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed to execute the static UI script")
    html = (Path(__file__).parents[1] / "praxis_virtualcell/web/static/index.html").read_text()
    values = re.findall(r'<input type="checkbox" value="([^"]+)"', html)
    assert values == ["genome", "transcriptome", "proteome"]
    script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
    harness = r'''
const vm=require('node:vm');
const elements=new Map();
function element(){return {value:'',textContent:'',disabled:false,children:[],style:{},dataset:{},listeners:{},classList:{remove(){}},
 addEventListener(name,fn){this.listeners[name]=fn;},appendChild(child){this.children.push(child);},replaceChildren(){this.children=[];}};}
const inputs=VALUES.map(value=>({...element(),value,checked:false}));
function get(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);}
get('modalities').querySelectorAll=()=>inputs;
get('profile').value='test-profile';get('candidate').value='C1';get('smiles').value='CCO';
let available=['transcriptome'];let submitted=null;
const profile=selected=>({profile_id:'test-profile',species:{scientific_name:'Test bacterium'},strain:REFERENCE?null:'S1',
 input_role:REFERENCE?'species_reference':'measured_pre_treatment',
 modalities:REFERENCE?Object.fromEntries(selected.map(name=>[name,{strain:'source-'+name,
  condition:{condition_id:'condition-'+name,medium:'medium-'+name}}])):{},
 available_modalities:available,selected_modalities:selected,feature_count:2,annotated_feature_count:2,
 source_samples:['untreated-1'],unknown_fields:[],unit:'source_native'});
const context={document:{getElementById:get,createElement:()=>element()},URLSearchParams,
 location:{search:''},history:{replaceState(){}},console,
 fetch:async(url,options)=>{
  let result;
  if(url==='/api/health')result={model:'mock',credential_configured:true};
  else if(url==='/api/profiles')result={profiles:[{profile_id:'test-profile',label:'Test profile'}]};
  else if(url.startsWith('/api/profiles/test-profile')){
   const selected=new URL(url,'http://local').searchParams.getAll('modalities');
   result=profile(selected.length?selected:available);
  }else if(url==='/api/analyze'){
   submitted=JSON.parse(options.body);
   result={status:'completed',report_id:'r1',report_markdown:'Public report',profile:profile(submitted.modalities),
    agent_trace:{stages:[{stage:'planning',status:'completed'},{stage:'review',status:'completed'},{stage:'revision',status:'completed'}]},
    agent_review:{decision:'revise',summary:'Repair unsupported claim',issues:[{severity:'blocking',finding:'No binding experiment'}]},
    review_resolution:'revised'};
  }else throw new Error('Unexpected mock route '+url);
  return {ok:true,json:async()=>result};
 }};
vm.createContext(context);new vm.Script(SCRIPT).runInContext(context);
(async()=>{
 await context.init();
 const first=inputs.map(i=>({value:i.value,disabled:i.disabled,checked:i.checked}));
 for(const i of inputs)i.checked=false;
 await context.selectionChanged();
 const emptyDisabled=get('analyze').disabled;
 await get('analyze').listeners.click();
 if(submitted!==null)throw new Error('Empty selection reached analysis');
 available=['genome','transcriptome','proteome'];
 await context.profileChanged();
 for(const i of inputs)i.checked=['genome','proteome'].includes(i.value);
 await context.selectionChanged();
 await get('analyze').listeners.click();
 process.stdout.write(JSON.stringify({first,emptyDisabled,submitted,
  stages:get('agent-stages').children.map(x=>x.textContent),review:get('agent-review').textContent,
  summary:get('profile-summary').textContent}));
})().catch(error=>{console.error(error);process.exitCode=1;});
'''.replace("VALUES", json.dumps(values)).replace("SCRIPT", json.dumps(script)).replace("REFERENCE", json.dumps(species_reference))
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, check=True)
    state = json.loads(result.stdout)
    assert state["first"] == [
        {"value": "genome", "disabled": True, "checked": False},
        {"value": "transcriptome", "disabled": False, "checked": True},
        {"value": "proteome", "disabled": True, "checked": False},
    ]
    assert state["emptyDisabled"] is True
    assert state["submitted"]["modalities"] == ["genome", "proteome"]
    assert state["submitted"]["smiles"] == "CCO"
    assert "规划 · completed" in state["stages"]
    assert "修订 · completed" in state["stages"]
    assert "审核决定：revise" in state["review"]
    assert "No binding experiment" in state["review"]
    assert "null" not in state["summary"] and "undefined" not in state["summary"]
    if species_reference:
        assert "物种参考背景" in state["summary"]
        assert "不表示同一样本" in state["summary"]
        assert "source-genome" in state["summary"] and "source-proteome" in state["summary"]
        assert "source-transcriptome" not in state["summary"]
