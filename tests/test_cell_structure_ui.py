"""Show only structure evidence used by the assessment, with source scope."""
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest


def test_structure_ui_distinguishes_prior_strain_and_unknown_reports():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed to execute the static UI script")
    html = (Path(__file__).parents[1] / "praxis_virtualcell/web/static/index.html").read_text()
    script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
    assert 'aria-label="细胞结构分析"' in html
    harness = r'''
const vm=require('node:vm');
const elements=new Map();
function element(){return {value:'',textContent:'',disabled:false,children:[],style:{},dataset:{},
 classList:{remove(){}},addEventListener(){},appendChild(child){this.children.push(child);},
 replaceChildren(){this.children=[];},querySelectorAll(){return [];}};}
function get(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);}
const context={document:{getElementById:get,createElement:()=>element()},URLSearchParams,console,
 location:{search:''},history:{replaceState(){}},fetch:async url=>({ok:true,json:async()=>
  url==='/api/health'?{model:'fixture',credential_configured:false}:{profiles:[]}})};
vm.createContext(context);new vm.Script(SCRIPT).runInContext(context);
const citation={tool_call_id:'used-structure',pointer:'/structures/0/compartment',source_id:'structure:used',value:'outer_membrane'};
const claim={structure_id:'used:outer_membrane',compartment:'outer_membrane',evidence_scope:'species_prior',
 evidence_type:'reference_knowledge',hypothesis:'Transport is unknown.',evidence_refs:[citation]};
context.showStructure({assessment:{structure_analysis:{compartment_hypotheses:[claim],limitations:['Strain location unknown.']}},
 execution_trace:{tool_calls:[{data:{structures:[{structure_id:'unused:secret'}]}}]}});
const prior=get('structure-summary').textContent;
context.showStructure({assessment:{structure_analysis:{compartment_hypotheses:[{...claim,
 evidence_scope:'strain_evidence',evidence_type:'source_annotation',protein_id:'NATIVE_P1',protein_namespace:'author_accession'}]}}});
const strain=get('structure-summary').textContent;
context.showStructure({assessment:{structure_analysis:{accessibility_barriers:[{...claim,
 accessibility:'potential_barrier',hypothesis:'<script>not executed</script>'}]}}});
const barrier=get('structure-summary').textContent;
context.showStructure({assessment:{structure_analysis:null}});
const unknown=get('structure-summary').textContent;
context.showStructure({assessment:{structure_analysis:{limitations:['No records were returned.']}}});
process.stdout.write(JSON.stringify({prior,strain,barrier,unknown,empty:get('structure-summary').textContent}));
'''.replace("SCRIPT", json.dumps(script))
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, check=True)
    state = json.loads(result.stdout)
    assert "物种背景（species_prior）" in state["prior"]
    assert "当前菌株结构与状态未知" in state["prior"]
    assert "蛋白定位：未知" in state["prior"]
    assert "structure:used（used-structure/structures/0/compartment）" in state["prior"]
    assert "unused:secret" not in state["prior"]
    assert "菌株来源证据（strain_evidence）" in state["strain"]
    assert "NATIVE_P1（author_accession）" in state["strain"]
    assert "当前细胞状态仍未验证" in state["strain"]
    assert "可能构成屏障（假说）" in state["barrier"]
    assert "<script>not executed</script>" in state["barrier"]
    assert "本报告未提供经引用核验的结构分析" in state["unknown"]
    assert "used:outer_membrane" not in state["unknown"]
    assert "结构与可达性：未知" in state["empty"]
    assert "No records were returned." in state["empty"]
    assert not any("undefined" in text or "null" in text for text in state.values())
