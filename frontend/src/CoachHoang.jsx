import React,{useEffect,useState,useCallback} from 'react';
import {Brain,BookOpen,Target,ShieldCheck,Play,Lightbulb,RefreshCcw,CheckCircle2,Clock,LockKeyhole,GraduationCap,Sparkles} from 'lucide-react';
import './CoachHoang.css';

async function call(path,body){
 const r=await fetch('/api'+path,{
  credentials:'same-origin',method:body===undefined?'GET':'POST',
  headers:{'Content-Type':'application/json'},
  body:body===undefined?undefined:JSON.stringify(body)
 });
 const data=await r.json().catch(()=>({detail:'Server unavailable'}));
 if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Unable to reach your coach');
 return data;
}
const COLORS={tactics:'#ede8ff',safety:'#e5f5e9',thinking:'#fef2da',strategy:'#e7f0ff',endgames:'#ffe9ef',openings:'#e7f6f5'};
const ICONS={tactics:'♞',safety:'🛡️',thinking:'🧠',strategy:'♜',endgames:'♛',openings:'♙'};
function CoachAvatar({size='medium'}){
 return <div className={'coach-avatar '+size} aria-label="Coach Hoang chess mentor">
  <span>♞</span><small>HOANG</small>
 </div>;
}
export function CoachHoang({onMission,notice}){
 const [status,setStatus]=useState(null),[plan,setPlan]=useState(null),[busy,setBusy]=useState(false),[activeMission,setActiveMission]=useState('');
 const refresh=useCallback(async()=>{try{const d=await call('/child/coach/status');setStatus(d);setPlan(d.plan)}catch(e){notice(e.message)}},[notice]);
 useEffect(()=>{refresh()},[refresh]);
 const generate=async()=>{
   setBusy(true);
   try{const p=await call('/child/coach/plan',{});setPlan(p);await refresh()}
   catch(e){notice(e.message)}
   finally{setBusy(false)}
 };
 const start=async m=>{
  if(!plan||activeMission)return;
  setActiveMission(m.puzzle_id);
  try{const exercise=await call('/child/coach/mission/start',{plan_id:plan.id,puzzle_id:m.puzzle_id});
      onMission(exercise)}
  catch(e){notice(e.message)}finally{setActiveMission('')}
 };
 return <section className="coach-page">
   <div className="coach-hero">
    <CoachAvatar size="large"/>
    <div className="coach-hero-copy"><span className="eyebrow">YOUR PERSONAL CHESS MENTOR</span>
      <h1>Meet Coach Hoang</h1>
      <p>We train like thoughtful champions: spot the threats, find a plan, try a move, and learn from it. Your progress sets the pace.</p>
      <div className="coach-status">
       <span><ShieldCheck size={15}/>{status?.ai_available?'Parent-enabled AI explanations':'Verified lessons work without an AI key'}</span>
       {status?.ai_available&&<span><Sparkles size={15}/>{status.remaining_today} coaching requests left today</span>}
      </div></div>
    </div>
    <div className="coach-principles">
      <div><Target size={21}/><strong>Train your current skills</strong><p>We choose harder exercises as you show progress.</p></div>
      <div><Brain size={21}/><strong>Think before moving</strong><p>Good habits matter more than speed.</p></div>
      <div><BookOpen size={21}/><strong>Learn from each try</strong><p>Every mistake gives us something useful to practice.</p></div>
    </div>
    <div className="coach-plan-top">
      <div><span className="eyebrow">YOUR PRACTICE SESSION</span><h2>{plan?'Your six-mission training plan':'Start a new training plan'}</h2>
      <p>{plan?'A mix of tactics, safe play, calculation and endgame practice, based on your recorded exercises.':'Coach Hoang selects six real, rules-checked chess exercises from the training library.'}</p></div>
      <button className="coach-start" disabled={busy} onClick={generate}><RefreshCcw size={17}/>{busy?'Preparing your training…':plan?'Prepare a fresh plan':'Build my training plan'}</button>
    </div>
    {plan&&<><div className="coach-message">
      <div className="coach-mini-avatar">♞</div>
      <div><span className="eyebrow">{plan.source==='ai-assisted'?'AI-ASSISTED COACHING':'VERIFIED PRACTICE'}</span><h3>{plan.message}</h3><p>{plan.weakness_note}</p>
       {plan.profile&&<p><strong>Current practice band:</strong> {plan.profile.band} · {plan.profile.puzzles_reviewed} recent attempts. This is a learning indicator, not an official rating.</p>}<p className="coach-speech">{plan.focus}</p><strong>Coach's tip: {plan.tip}</strong></div>
    </div>
    <div className="coach-missions">{plan.missions.map(m=><div className="coach-mission" key={m.puzzle_id}>
      <div className="coach-mission-icon" style={{background:COLORS[m.category]||'#e9edff'}}>{ICONS[m.category]||'♞'}</div>
      <div className="coach-mission-content"><span className="eyebrow">MISSION {m.number} · {m.category.toUpperCase()} · {m.duration_minutes} MIN</span><h3>{m.title}</h3><p>{m.goal}</p><small><Lightbulb size={14}/>{m.thinking_tip}</small></div>
      <button className="coach-play" disabled={!!activeMission} onClick={()=>start(m)}>{activeMission===m.puzzle_id?'Loading…':<>Train <Play size={16}/></>}</button>
    </div>)}</div>
    <p className="coach-disclaimer"><ShieldCheck size={17}/> The exercises come from JChess's rules-validated library. The coach never invents a solution or changes chess rules. A performance pattern only becomes a possible weak area after enough attempts.</p>
    </>}
    {!plan&&<div className="coach-empty"><GraduationCap size={35}/><h3>Ready for your chess adventure?</h3><p>Six short puzzles, one thinking habit at a time. No pressure or speed test.</p></div>}
 </section>;
}

export function CoachExplain({sessionId,solved,revealed=false,notice}){
 const [result,setResult]=useState(null),[busy,setBusy]=useState(false);
 useEffect(()=>setResult(null),[sessionId,solved]);
 const ask=async mode=>{
  setBusy(true);
  try{setResult(await call('/child/coach/explain',{session_id:sessionId,mode}))}
  catch(e){notice(e.message)}finally{setBusy(false)}
 };
 return <div className="coach-explain">
   <div className="coach-explain-title"><span className="coach-mini-avatar">♞</span><div><b>Ask Coach Hoang</b><small>{solved||revealed?'Why did that idea work?':'Need a thinking hint?'}</small></div></div>
   <button disabled={busy} onClick={()=>ask(solved||revealed?'explain':'hint')}>
     <Lightbulb size={16}/>{busy?'Coach is thinking…':solved||revealed?'Explain this lesson':'Give me a hint'}
   </button>
   {result&&<div className="coach-explain-feedback">
    <strong>{result.opening}</strong>
    <p>{result.focus}</p>
    <small>{result.tip}</small>
    {result.source==='ai-assisted'&&<span className="coach-ai-note">AI-assisted explanation · Verified exercise</span>}
   </div>}
 </div>;
}

export function ParentCoachPreview({childId,notice}){
 const [plan,setPlan]=useState(null);
 const [loading,setLoading]=useState(false);
 useEffect(()=>{
   if(!childId){setPlan(null);return;}
   let cancelled=false;setLoading(true);
   call('/parent/children/'+childId+'/coach').then(data=>{if(!cancelled)setPlan(data.plan)})
     .catch(e=>{if(!cancelled)notice(e.message)})
     .finally(()=>{if(!cancelled)setLoading(false)});
   return ()=>{cancelled=true};
 },[childId,notice]);
 if(!childId)return <p className="privacy-note">Add or select a child to view their training sessions.</p>;
 if(loading)return <p className="privacy-note">Loading Coach Hoang's latest plan…</p>;
 if(!plan)return <p className="privacy-note">No training plan yet. Your child can open the Coach Hoang tab to prepare the first session.</p>;
 return <div className="coach-parent-preview">
  <span className="eyebrow">LATEST TRAINING PLAN</span>
  <strong>{plan.source==='ai-assisted'?'AI-assisted':'Rules-verified'} · {plan.missions.length} challenges</strong>
  <p>{plan.weakness_note}</p>
  <div className="coach-parent-tags">{plan.missions.map(x=><span key={x.puzzle_id}>{ICONS[x.category]||'♞'} {x.category}</span>)}</div>
  <small>Selected from a legally checked exercise library. The student's account never sees your API key.</small>
 </div>;
}
