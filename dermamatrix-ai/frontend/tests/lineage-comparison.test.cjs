const{test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8');
function extract(name){const start=source.indexOf('function '+name+'(');const end=source.indexOf('\nfunction ',start+10);return source.slice(start,end<0?source.length:end);}
function harness(){const insight={hidden:false,innerHTML:''};const context={$:()=>insight,escapeHTML:String};vm.createContext(context);for(const name of ['assessmentConcernScore','assessmentComparisonKey','renderDashboardInsight'])vm.runInContext(extract(name),context);return{context,insight};}
const record=(version,score)=>({area:'Skin',summary:{input_type:'image',assessment_risk:{score,methodology_version:'score-v1'},model_metadata:{model_id:'model',model_version:version,pipeline_version:'pipeline-v1',dataset_version:'data-v1',runtime_image_decoder:'pillow-13.0.0'}}});
test('different or unknown model lineage cannot become a numerical trend',()=>{const{context,insight}=harness();context.renderDashboardInsight([record('new',40),record('old',20)],[]);assert.doesNotMatch(insight.innerHTML,/points higher|points lower/);assert.match(insight.innerHTML,/different or unrecorded versions/);context.renderDashboardInsight([{area:'Skin',summary:{risk:{score:10}}},record('old',20)],[]);assert.doesNotMatch(insight.innerHTML,/points higher|points lower/);});
test('comparable recorded indicator remains distinct from healing',()=>{const{context,insight}=harness();context.renderDashboardInsight([record('same',40),record('same',20)],[]);assert.match(insight.innerHTML,/20 points higher/);assert.match(insight.innerHTML,/not measured healing or a clinical trend/);});

test('decoder runtime changes or missing decoder evidence cannot become a trend',()=>{const{context,insight}=harness();const latest=record('same',40),older=record('same',20);older.summary.model_metadata.runtime_image_decoder='pillow-11.3.0';context.renderDashboardInsight([latest,older],[]);assert.doesNotMatch(insight.innerHTML,/points higher|points lower/);delete older.summary.model_metadata.runtime_image_decoder;context.renderDashboardInsight([older,record('same',10)],[]);assert.doesNotMatch(insight.innerHTML,/points higher|points lower/);});
test('different concerns and assigned versus unassigned records cannot become a numerical trend',()=>{
 const{context,insight}=harness();const latest=record('same',40),older=record('same',20);
 latest.episode_link={episode_id:'concern-a'};older.episode_link={episode_id:'concern-b'};
 context.renderDashboardInsight([latest,older],[]);assert.doesNotMatch(insight.innerHTML,/points higher|points lower/);
 delete older.episode_link;context.renderDashboardInsight([latest,older],[]);assert.doesNotMatch(insight.innerHTML,/points higher|points lower/);
 older.episode_link={episode_id:'concern-a'};context.renderDashboardInsight([latest,older],[]);assert.match(insight.innerHTML,/20 points higher/);
});
test('a changed concern suppresses the original saved comparison without rewriting it',()=>{
 const context=vm.createContext({});vm.runInContext(extract('contextualProgress'),context);
 const summary={progress_comparison:{summary:'Original comparison',scope:{episode_id:'concern-a'},journey:{baseline_assessment_id:'old'}}};
 assert.equal(context.contextualProgress(summary,{episode_id:'concern-b'}).status,'CONCERN_SCOPE_CHANGED');
 assert.equal(summary.progress_comparison.summary,'Original comparison');assert.equal(summary.progress_comparison.journey.baseline_assessment_id,'old');
 assert.equal(context.contextualProgress(summary,{episode_id:'concern-a'}),summary.progress_comparison);
 assert.equal(context.contextualProgress({progress_comparison:{summary:'Legacy'}},{episode_id:'new'}).status,'CONCERN_SCOPE_CHANGED');
});
