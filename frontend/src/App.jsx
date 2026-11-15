import React,{useState,useEffect,useCallback} from 'react';
import {Chess} from 'chess.js';
import {Chessboard} from 'react-chessboard';
import {GameSetup,GameRoom,ParentGame,GuestGame} from './GamePlay.jsx';
import {CoachHoang,CoachExplain,ParentCoachPreview} from './CoachHoang.jsx';
import {Rocket,Trophy,Shield,Zap,Brain,Crown,Compass,Users,BookOpen,Activity,LogOut,Play,Pause,RotateCcw,ChevronLeft,ChevronRight,ArrowRight,Plus,Star,Lightbulb,Target,CheckCircle2,LockKeyhole,Sparkles,Wifi,KeyRound,WandSparkles,Eye,EyeOff,Settings} from 'lucide-react';

const api=async(url,method='GET',body)=>{
 const r=await fetch('/api'+url,{method,credentials:'same-origin',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 let data;try{data=await r.json()}catch{data={detail:'Unexpected server response'}}
 if(!r.ok)throw Error(data.detail||'Request failed');
 return data;
};
const post=(url,body)=>api(url,'POST',body);
const AREAS={
 safety:{name:'Piece Protectors',short:'Protect pieces',emoji:'🛡️',icon:Shield,tone:'sky',desc:'Spot hanging pieces and save your army!'},
 tactics:{name:'Tactics Treasure',short:'Tactics',emoji:'⚡',icon:Zap,tone:'orange',desc:'Clever forks and surprising moves.'},
 thinking:{name:'Brain Power',short:'Think ahead',emoji:'🧠',icon:Brain,tone:'violet',desc:'Read your opponent’s next idea.'},
 endgames:{name:'Endgame Heroes',short:'Endgames',emoji:'👑',icon:Crown,tone:'mint',desc:'Promote pawns and find checkmate.'},
 openings:{name:'Opening Explorer',short:'Openings',emoji:'🧭',icon:Compass,tone:'pink',desc:'Build the best start for your game.'},
 strategy:{name:'Strategy Studio',short:'Strategy',emoji:'🎯',icon:Target,tone:'mint',desc:'Make plans, improve pieces and keep your king safe.'}
};
const area=k=>AREAS[k]||AREAS.tactics;
function Brand(){return <div className="brand"><span className="brand-icon">♞</span><b>JChess <em>Academy</em></b></div>}
function Action({children,onClick,kind='primary',disabled=false,icon:Icon,type='button'}){
 return <button type={type} className={'action '+kind} onClick={onClick} disabled={disabled}>{Icon&&<Icon size={18}/>} {children}</button>
}
function Stat({icon:Icon,number,label,color}){return <div className="stat"><div className={'stat-icon '+color}><Icon size={23}/></div><div><strong>{number}</strong><small>{label}</small></div></div>}
function Board({fen,onMove,onTap,readonly=false,name='board'}){
 const [selected,setSelected]=useState('');
 useEffect(()=>setSelected(''),[fen]);
 const move=(from,to)=>{
   if(readonly||onTap)return false;
   const g=new Chess(fen),p=g.get(from);
   if(!p)return false;
   const legal=g.moves({square:from,verbose:true}).some(x=>x.to===to);
   if(!legal)return false;
   const promotion=p.type==='p'&&('18'.includes(to[1]))?'q':'';
   onMove(from+to+promotion);return true;
 };
 const tap=sq=>{
   if(readonly)return;
   if(onTap){onTap(sq);return}
   const g=new Chess(fen),p=g.get(sq);
   if(selected && move(selected,sq)){setSelected('');return}
   setSelected(p&&p.color===g.turn()?sq:'');
 };
 return <div className="board-wrap"><Chessboard id={name} position={fen} boardOrientation="white" onPieceDrop={move} onSquareClick={tap}
  arePiecesDraggable={!readonly&&!onTap} animationDuration={350}
  customBoardStyle={{borderRadius:'13px',boxShadow:'0 18px 38px #27304b24'}}
  customLightSquareStyle={{backgroundColor:'#eff2e8'}} customDarkSquareStyle={{backgroundColor:'#86a7a5'}}
  customSquareStyles={selected?{[selected]:{backgroundColor:'#fadd7d'}}:{}}/></div>;
}
function Solution({puzzle,onClose}){
 const [step,setStep]=useState(0),[playing,setPlaying]=useState(false);
 const line=puzzle.solution||[];
 const fen=React.useMemo(()=>{const b=new Chess(puzzle.fen);for(let i=0;i<step;i++){try{b.move({from:line[i].slice(0,2),to:line[i].slice(2,4),promotion:line[i][4]||'q'})}catch{break}}return b.fen()},[puzzle.fen,step,line.join(',')]);
 useEffect(()=>{setStep(0);setPlaying(false)},[puzzle.id]);
 useEffect(()=>{if(!playing)return;if(step>=line.length){setPlaying(false);return}const t=setTimeout(()=>setStep(s=>s+1),850);return()=>clearTimeout(t)},[playing,step,line.length]);
 return <div className="solution"><div className="between"><div><span className="eyebrow">ANIMATED ANSWER</span><h2>See how it works! ✨</h2></div>{onClose&&<button className="plain" onClick={onClose}>Close</button>}</div>
 <div className="solution-layout"><Board fen={fen} readonly name="solution-board"/><div><p>{puzzle.explanation}</p><div className="playback"><button onClick={()=>{setStep(0);setPlaying(false)}}><RotateCcw/></button><button onClick={()=>{setStep(Math.max(0,step-1));setPlaying(false)}}><ChevronLeft/></button><button className="play-control" onClick={()=>{if(step>=line.length)setStep(0);setPlaying(!playing)}}>{playing?<Pause/>:<Play/>}</button><button onClick={()=>{setStep(Math.min(line.length,step+1));setPlaying(false)}}><ChevronRight/></button></div><p className="muted">Move {step} of {line.length}</p><div className="move-chips">{line.map((m,i)=><span className={i<step?'active':''} key={i}>{m}</span>)}</div></div></div></div>
}
function Auth({onLogin,notice}){
 const [mode,setMode]=useState('child'),[register,setRegister]=useState(false),[username,setUsername]=useState(''),[password,setPassword]=useState(''),[name,setName]=useState(''),[busy,setBusy]=useState(false);
 const submit=async e=>{e.preventDefault();setBusy(true);try{if(register){await post('/auth/register',{username,password,name});notice('Parent account created. Please sign in.');setRegister(false)}else onLogin(await post('/auth/login',{username,password}))}catch(err){notice(err.message)}finally{setBusy(false)}};
 return <div className="auth-page"><div className="auth-art"><Brand/><div className="art-stars">✦ <span>✧</span> ✦</div><div className="chess-mascot"><div className="mascot-glow"/><span>♞</span><div className="art-label">🏆 Future champion!</div></div><h1>Little moves.<br/><em>Big dreams.</em></h1><p>Welcome to a magical place where curious kids become clever chess thinkers.</p><div className="art-footer">✦ Made for young minds · Guided by parents</div></div>
 <div className="auth-content"><div className="auth-card"><span className="eyebrow">YOUR NEXT GREAT MOVE STARTS HERE</span><h2>{register?'Create your family account':'Welcome back! 👋'}</h2><p>Ready to grow a little smarter with every move?</p>
 {!register&&<div className="role-picker"><button className={mode==='child'?'chosen':''} onClick={()=>setMode('child')}>🚀 I'm a player</button><button className={mode==='parent'?'chosen':''} onClick={()=>setMode('parent')}>👨‍👧 I'm a parent</button></div>}
 <form onSubmit={submit} className="form">{register&&<label>Your name<input value={name} onChange={e=>setName(e.target.value)} required placeholder="Parent's name"/></label>}
 <label>Username<input autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} placeholder="Enter username" required/></label>
 <label>Password<input type="password" minLength={register?10:1} autoComplete={register?'new-password':'current-password'} value={password} onChange={e=>setPassword(e.target.value)} required placeholder="Enter password"/></label>
 <Action type="submit" disabled={busy} icon={ArrowRight}>{busy?'Just a moment...':register?'Create parent account':'Let’s play chess'}</Action></form>
 <p className="auth-foot">{register?'Already registered?':'New parent here?'} <button className="link" onClick={()=>setRegister(!register)}>{register?'Sign in':'Create a family account'}</button></p><small className="privacy"><LockKeyhole size={13}/> Private boards · Parent-controlled solutions</small></div></div></div>
}
function ResetPassword({user,notice,refresh,logout}){
 const [oldPw,setOld]=useState(''),[pw,setPw]=useState('');
 const save=async e=>{e.preventDefault();try{await post('/auth/password',{current:oldPw,new:pw});await refresh();notice('Password updated!')}catch(err){notice(err.message)}};
 return <div className="reset-page"><div className="panel reset"><Brand/><div className="reset-lock">🔒</div><h1>Secure your account, {user.name}!</h1><p>Change the starter password before practicing. Your new password must be at least 10 characters.</p><form className="form" onSubmit={save}><label>Current password<input type="password" required value={oldPw} onChange={e=>setOld(e.target.value)}/></label><label>New password<input type="password" minLength="10" required value={pw} onChange={e=>setPw(e.target.value)}/></label><Action type="submit">Save new password</Action></form><button className="link" onClick={logout}>Sign out</button></div></div>
}
function Header({user,logout,tab,setTab,parent=false}){
 const nav=parent?[['live','Live board',Activity],['games','Play together',Users],['library','Puzzle library',BookOpen],['children','Children',Users],['ai','AI coach',WandSparkles]]:[['home','My home',Rocket],['coach','Coach Hoang',Brain],['gameSetup','Play',Users],['lessons','Lessons',BookOpen],['practice','Practice',Target],['progress','Progress',Trophy]];
 return <header className="header"><Brand/><nav>{nav.map(([id,name,Icon])=><button key={id} className={id===tab?'active':''} onClick={()=>setTab(id)}><Icon size={17}/>{name}</button>)}</nav><div className="profile"><span className="avatar">{user.role==='parent'?'H':'J'}</span><div><strong>{user.name}</strong><small>{parent?'Parent':'Player'}</small></div><button className="logout" title="Sign out" onClick={logout}><LogOut size={19}/></button></div></header>;
}
function Category({id,c,count,accuracy,onStart}){
 const Icon=c.icon;return <button className={'area-card '+c.tone} onClick={()=>onStart(id)}><div className="between"><span className="area-icon"><Icon size={26}/></span><span className="area-emoji">{c.emoji}</span></div><h3>{c.name}</h3><p>{c.desc}</p><div className="area-bottom"><span>{count} puzzles</span><span>{accuracy==null?'Explore →':accuracy+'% first try'}</span></div></button>
}
function Child({user,notice,logout}){
 const [tab,setTab]=useState('home'),[catalog,setCatalog]=useState(null),[lessons,setLessons]=useState([]),[selectedLesson,setSelectedLesson]=useState(null),[stats,setStats]=useState(null),[active,setActive]=useState(null),[playGame,setPlayGame]=useState(null),[inviteToken,setInviteToken]=useState(''),[gameBusy,setGameBusy]=useState(false),[busy,setBusy]=useState(false),[hint,setHint]=useState(false),[feedback,setFeedback]=useState(''),[viewSolution,setViewSolution]=useState(false);
 const refresh=useCallback(async()=>{try{const[d,c,l,g]=await Promise.all([api('/child/dashboard'),api('/catalog'),api('/lessons'),api('/child/game/current').catch(()=>null)]);setStats(d.stats);setCatalog(c);setLessons(l);setActive(d.active);setPlayGame(g);if(g?.id)setInviteToken(sessionStorage.getItem('jchess-invite-'+g.id)||'')}catch(e){notice(e.message)}},[notice]);
 useEffect(()=>{refresh()},[refresh]);
 useEffect(()=>{if(tab!=='mission'||!active||active.solved)return;let t=setInterval(async()=>{try{const p=await api('/child/current');setActive(prev=>prev&&p&&prev.id===p.id&&p.version!==prev.version?p:prev)}catch{}},1800);return()=>clearInterval(t)},[tab,active?.id,active?.solved]);
 const start=async(category,lessonId=null)=>{setBusy(true);try{setActive(await post('/child/puzzle/start',{category,lesson_id:lessonId}));setFeedback('');setHint(false);setViewSolution(false);setTab('mission')}catch(e){notice(e.message)}finally{setBusy(false)}};
 const startCoachMission=(session)=>{setActive(session);setFeedback('');setHint(false);setViewSolution(false);setTab('mission')};
  const game=()=>setTab('gameSetup');
 const startGame=async choice=>{
   if(choice===null){setTab('match');return}
   const g=await post('/child/game/start',choice);
   setPlayGame(g);if(g.invite_token){sessionStorage.setItem('jchess-invite-'+g.id,g.invite_token);setInviteToken(g.invite_token)}else setInviteToken('');
   setTab('match');
 };
 const endGame=async()=>{
   if(!playGame||!window.confirm('End this game'+(playGame.mode==='friend'?' and revoke the friend link':'')+'?'))return;
   setGameBusy(true);
   try{setPlayGame(await post('/child/game/close',{game_id:playGame.id}));sessionStorage.removeItem('jchess-invite-'+playGame.id);setInviteToken('')}
   catch(e){notice(e.message)}finally{setGameBusy(false)}
 };
 const gameMove=async uci=>{
   if(!playGame||gameBusy)return;
   setGameBusy(true);
   try{setPlayGame(await post('/child/game/move',{game_id:playGame.id,uci}))}
   catch(e){notice(e.message);api('/child/game/current').then(setPlayGame).catch(()=>{})}
   finally{setGameBusy(false)}
 };
 useEffect(()=>{if(tab!=='match'||!playGame||playGame.status!=='active')return;const t=setInterval(()=>{
   api('/child/game/current').then(g=>setPlayGame(prev=>prev&&g&&prev.id===g.id&&g.version!==prev.version?g:prev)).catch(()=>{})
 },1800);return()=>clearInterval(t)},[tab,playGame?.id,playGame?.status]);
 const onMove=async uci=>{if(busy)return;setBusy(true);try{const result=active.mode==='sandbox'?{state:await post('/child/sandbox/move',{uci}),correct:true}:await post('/child/puzzle/move',{uci});setActive(result.state);setFeedback(active.mode==='sandbox'?'':result.correct?'yes':result.model_move?'model':'try');if(result.state.solved){const d=await api('/child/dashboard');setStats(d.stats)}}catch(e){notice(e.message)}finally{setBusy(false)}};
 const onTap=async square=>{if(busy)return;setBusy(true);try{const result=await post('/child/puzzle/spot',{square});setActive(result.state);setFeedback(result.correct?'yes':'try');if(result.state.solved){const d=await api('/child/dashboard');setStats(d.stats)}}catch(e){notice(e.message)}finally{setBusy(false)}};
 const currentLesson=active?.puzzle?lessons.find(l=>l.category===active.puzzle.category&&l.theme===active.puzzle.theme):null;
 const title=(mini,main,sub)=><div className="section-title"><span className="eyebrow">{mini}</span><h2>{main}</h2><p>{sub}</p></div>;
 const cards=<div className="areas">{Object.entries(AREAS).map(([id,c])=><Category key={id} id={id} c={c} count={catalog?.categories?.[id]?.count||0} accuracy={stats?.by_category?.[id]?.accuracy} onStart={start}/>)}</div>;
 return <div className="app"><Header user={user} logout={logout} tab={tab} setTab={setTab}/><main className="container">
 {tab==='home'&&<><div className="hero"><div className="hero-text"><span className="eyebrow light">✦ YOUR CHESS ADVENTURE</span><h1>Hey, {user.name}! 👋<br/><em>Ready to shine?</em></h1><p>Great players grow one smart move at a time. Your next little victory is waiting!</p><Action kind="white" icon={Rocket} onClick={()=>start(null)}>Start today's mission</Action></div><div className="hero-image"><div className="hero-halo"/><span>♞</span><div className="hero-sticker">🏆 Future champion!</div></div></div>
 <div className="stats"><Stat color="orange" icon={Trophy} number={stats?.completed||0} label="Puzzles solved"/><Stat color="violet" icon={Star} number={stats?.xp||0} label="XP earned"/><Stat color="mint" icon={Target} number={stats?.completed?Math.round(100*stats.correct/stats.completed)+'%':'0%'} label="First-try accuracy"/></div>
 {playGame?.status==='active'&&<div className="resume"><span>♟</span><div><strong>Your chess game is ready!</strong><p>Continue playing {playGame.mode==='bot'?'the robot':playGame.mode==='parent'?'your parent':playGame.mode==='friend'?'your friend':'together'}.</p></div><Action kind="outline" onClick={()=>setTab('match')}>Resume game →</Action></div>}
 {active&&!active.solved&&<div className="resume"><span>♟</span><div><strong>One puzzle is waiting for you!</strong><p>Continue your chess adventure.</p></div><Action kind="outline" onClick={()=>setTab('mission')}>Continue →</Action></div>}
 <div className="strip study-strip coach-home-strip"><div><span className="eyebrow">YOUR PERSONAL CHESS TRAINER</span><h3>Meet Coach Hoang ♞</h3><p>Six personalized tactics and strategy challenges based on the chess skills you've practiced.</p></div><Action kind="soft" icon={Brain} onClick={()=>setTab('coach')}>Train with Coach Hoang →</Action></div>
  <div className="strip study-strip"><div><span className="eyebrow">TACTICS + STRATEGY</span><h3>New: Learn the idea, then play it</h3><p>14 short lessons on forks, pins, skewers, king safety, pawn plans and more. Learn it on the board, not just in a book.</p></div><Action kind="soft" icon={BookOpen} onClick={()=>setTab('lessons')}>Explore lessons</Action></div>
 {title('CHOOSE YOUR ADVENTURE','The training islands','Six ways to become a stronger chess player.')}{cards}
 <div className="tip"><span>💡</span><div><span className="eyebrow">CHAMPION'S SECRET</span><h3>Think before you touch.</h3><p>Before every move: “What can my opponent capture next?”</p></div></div><div className="strip"><div><h3>Want to play a full chess game?</h3><p>Challenge a robot, your parent or a friend. All moves follow real chess rules.</p></div><Action kind="soft" onClick={game}>Choose game mode →</Action></div></>}
 {tab==='coach'&&<CoachHoang onMission={startCoachMission} notice={notice}/>}
  {tab==='lessons'&&<>{title('THE CHESS CLASSROOM','Learn, then make your move','Each 5–7 minute lesson teaches an idea, a thinking checklist, and a board challenge.')}
 {['tactics','strategy'].map(group=><section className="course-section" key={group}><div className="course-heading"><span className="eyebrow">{group==='tactics'?'FIND THE WINNING IDEA':'BUILD A SMART PLAN'}</span><h2>{group==='tactics'?'⚡ Tactics lessons':'🎯 Strategy lessons'}</h2><p>{group==='tactics'?'Train your eyes for forcing moves: checks, captures and double attacks.':'Practice the decisions that make your whole position stronger.'}</p></div>
 <div className="lesson-grid">{lessons.filter(l=>l.category===group).map((l,i)=><button className="lesson-card" key={l.id} onClick={()=>{setSelectedLesson(l);setTab('lesson')}}><div className="lesson-card-top"><span className="lesson-emoji">{l.emoji}</span><span className="lesson-level">{l.level}</span></div><small>LESSON {i+1} · {l.time}</small><h3>{l.title}</h3><p>{l.why}</p><div className="lesson-card-bottom"><span>{l.puzzles} positions · {l.attempted} practiced</span><strong>Start lesson →</strong></div></button>)}</div></section>)}</>}
 {tab==='lesson'&&selectedLesson&&<><button className="plain back" onClick={()=>setTab('lessons')}>← All lessons</button><div className="lesson-detail"><div className="lesson-detail-header"><span className="lesson-emoji">{selectedLesson.emoji}</span><div><span className="eyebrow">{selectedLesson.category.toUpperCase()} · {selectedLesson.level} · {selectedLesson.time}</span><h1>{selectedLesson.title}</h1><p>{selectedLesson.why}</p></div></div><div className="lesson-detail-grid"><div className="panel"><span className="eyebrow">THREE THINGS TO THINK ABOUT</span><h2>Your move-by-move checklist</h2><ol className="lesson-steps">{selectedLesson.steps.map((step,i)=><li key={i}><span>{i+1}</span><p>{step}</p></li>)}</ol></div><div className="panel lesson-drill"><span className="eyebrow">NOW TRY IT YOURSELF</span><span className="lesson-emoji">♟️</span><h2>{selectedLesson.question}</h2><p>Think about the answer before moving. Your parent keeps control of the animated solution.</p><div className="lesson-count">{selectedLesson.puzzles} legal board positions ready</div><Action icon={Play} disabled={!selectedLesson.puzzles||busy} onClick={()=>start(selectedLesson.category,selectedLesson.id)}>Practice this lesson →</Action><small>Strategy exercises demonstrate one model plan; other legal plans can also be reasonable.</small></div></div></div></>}
 {tab==='gameSetup'&&<GameSetup onStart={startGame} resume={playGame} notice={notice}/>}
 {tab==='match'&&<GameRoom game={playGame} role="child" onMove={gameMove} invite={playGame?.id?inviteToken||sessionStorage.getItem('jchess-invite-'+playGame.id)||'':''} busy={gameBusy} onEnd={endGame} onNew={()=>setTab('gameSetup')}/>}
 {tab==='practice'&&<>{title('THE TRAINING ROOM','Pick your superpower','Choose a skill and train at your own pace.')}{cards}<div className="strip"><div><h3>Play chess with a robot or friend</h3><p>Easy, Medium and Hard robot games, parent matches, friend invitations, and shared-screen play.</p></div><Action kind="soft" onClick={game}>Choose how to play</Action></div></>}
 {tab==='progress'&&<>{title('YOUR CHESS JOURNEY','Look how far you’ve come!','Every smart try counts.') }<div className="progress-hero"><span>🏆</span><div><small>CHESS ADVENTURER</small><h2>{stats?.xp||0} XP</h2><p>Keep building your chess brain!</p></div></div><div className="stats"><Stat color="orange" icon={Trophy} number={stats?.completed||0} label="Exercises"/><Stat color="violet" icon={Star} number={stats?.correct||0} label="Perfect tries"/><Stat color="mint" icon={Target} number={stats?.completed?Math.round(100*stats.correct/stats.completed)+'%':'0%'} label="Accuracy"/></div>
 <div className="progress-list">{Object.entries(AREAS).map(([k,c])=>{const a=stats?.by_category?.[k]||{};return <div className="progress-item" key={k}><span>{c.emoji}</span><div><strong>{c.name}</strong><small>{a.attempts||0} completed</small><div className="track"><div style={{width:(a.accuracy||0)+'%'}}/></div></div><b>{a.accuracy??0}%</b></div>})}</div><p className="gentle">💜 Mistakes are opportunities to learn. Keep going!</p></>}
 {tab==='mission'&&active&&<><button className="plain back" onClick={()=>setTab('home')}>← Back home</button><div className="between mission-title"><div><span className="eyebrow">YOUR CHESS CHALLENGE</span><h1>{active.mode==='sandbox'?'Your practice board':active.puzzle?.title}</h1><p>{active.mode==='sandbox'?'Explore chess freely. Your parent sees every move.':'Take your time. Smart thinking wins!'}</p></div><span className="badge">{active.solved?'✓ Mission complete':'● In progress'}</span></div>
 <div className="mission-layout"><div className="panel board-panel"><div className="between"><span className="eyebrow">♚ {active.mode==='sandbox'?'FREE PLAY':'PLAYING AS WHITE'}</span><span className="muted">♟ CHESS</span></div><Board name="child-board" fen={active.fen} onMove={onMove} onTap={active.puzzle?.kind==='spot'?onTap:null} readonly={active.solved||busy}/><div className="board-instruction">{active.puzzle?.kind==='spot'?'👆 Tap the threatened piece':'👆 Tap or drag a piece to move'}</div></div>
 <div className="mission-aside"><div className="panel lesson-panel"><span className="lesson-symbol">{active.mode==='sandbox'?'🎮':area(active.puzzle?.category).emoji}</span><span className="eyebrow">TODAY'S LESSON</span><h2>{active.mode==='sandbox'?'Learn by playing':active.puzzle.title}</h2><p>{active.mode==='sandbox'?'Try out moves and experiment with the board.':area(active.puzzle?.category).desc}</p>
 {active.mode==='puzzle'&&<><div className="track"><div style={{width:active.solved?'100%':Math.min(80,active.step*25)+'%'}}/></div>
 {feedback==='try'&&!active.solved&&<div className="feedback warn"><Lightbulb size={18}/> Not quite. Look again and try a new idea!</div>}
 {feedback==='model'&&!active.solved&&<div className="feedback hint"><Lightbulb size={18}/> That move may be reasonable. Find the model move for this lesson; we won't count another legal plan as a mistake.</div>}
 {feedback==='yes'&&!active.solved&&<div className="feedback ok"><CheckCircle2 size={18}/> Great thinking! Keep going.</div>}
 {hint&&<div className="feedback hint">{currentLesson?.steps?.[0]||"Check the opponent's threats, checks, and captures before choosing."}</div>}
 {active.solved&&<div className="celebrate"><div className="confetti">✧ ✦ ✨ ✦</div><span>🏆</span><h3>Brilliant move!</h3><p>{active.puzzle?.takeaway||"Every puzzle makes your chess brain stronger."}</p><Action onClick={()=>start(active.puzzle?.category,currentLesson?.id||null)}>Next practice →</Action></div>}
 <div className="lesson-actions"><button onClick={()=>setHint(!hint)}><Lightbulb size={16}/> Hint</button><button onClick={()=>start(active.puzzle?.category,currentLesson?.id||null)}><RotateCcw size={16}/> New puzzle</button></div>
 <CoachExplain sessionId={active.id} solved={active.solved} revealed={active.revealed} notice={notice}/>
  {active.revealed?<div className="permission">✨ Your parent unlocked the answer. <button onClick={()=>setViewSolution(!viewSolution)}>{viewSolution?'Hide it':'Watch it →'}</button></div>:<small className="locked"><LockKeyhole size={14}/> Parent can unlock the animated answer.</small>}
 </>}
 {active.mode==='sandbox'&&<Action kind="soft" onClick={game}>Start a new game</Action>}</div>
 {currentLesson&&<div className="coach-tip"><span>{currentLesson.emoji}</span><div><strong>{currentLesson.title}</strong><p>{currentLesson.why}</p></div></div>}
 {!currentLesson&&<div className="coach-tip"><span>♞</span><div><strong>Champion's reminder</strong><p>Smart beats fast. You have time!</p></div></div>}
 <div className="panel moves-panel"><span className="eyebrow">YOUR MOVES & ATTEMPTS</span><div className="move-chips">{active.moves.length?active.moves.slice(-12).map((m,i)=><span className={m.correct===false?'error':''} key={i}>{m.san||m.move||m.square}</span>):<small>No moves yet. Your first one is next!</small>}</div></div></div></div>
 {viewSolution&&active.revealed&&active.puzzle&&<Solution puzzle={active.puzzle} onClose={()=>setViewSolution(false)}/>}
 </>}
 </main><footer>JChess Academy · Learn bravely. Think kindly. Play joyfully.</footer></div>;
}
function Parent({user,notice,logout}){
 const [tab,setTab]=useState('live'),[kids,setKids]=useState([]),[chosen,setChosen]=useState(null),[data,setData]=useState(null),[catalog,setCatalog]=useState(null),[library,setLibrary]=useState([]),[filter,setFilter]=useState('tactics'),[page,setPage]=useState(0),[solution,setSolution]=useState(null),[newKid,setNewKid]=useState({name:'',username:'',password:''}),[ai,setAi]=useState({enabled:false,has_key:false,daily_limit:3,used_today:0,remaining_today:3,cloud_enabled:false,cloud_daily_limit:20,cloud_moves_today:0,cloud_moves_remaining:20,coach_enabled:false,coach_daily_limit:3,coach_requests_today:0,coach_remaining_today:3}),[key,setKey]=useState(''),[advice,setAdvice]=useState(''),[busy,setBusy]=useState(false);
 const refreshKids=useCallback(async()=>{try{const d=await api('/parent/children');setKids(d);setChosen(c=>c??d[0]?.user?.id??null)}catch(e){notice(e.message)}},[notice]);
 useEffect(()=>{refreshKids();api('/catalog').then(setCatalog).catch(()=>{});api('/parent/ai').then(setAi).catch(()=>{})},[refreshKids]);
 const refresh=useCallback(async()=>{if(chosen==null){setData(null);return}try{setData(await api('/parent/children/'+chosen+'/live'))}catch(e){notice(e.message)}},[chosen,notice]);
 useEffect(()=>{refresh();const t=setInterval(refresh,1800);return()=>clearInterval(t)},[refresh]);
 useEffect(()=>{if(tab==='library')api('/parent/puzzles?category='+filter+'&skip='+(page*16)+'&limit=16').then(setLibrary).catch(e=>notice(e.message))},[tab,filter,page,notice]);
 const addKid=async e=>{e.preventDefault();setBusy(true);try{const k=await post('/parent/children',newKid);notice(k.name+' can now practice!');setNewKid({name:'',username:'',password:''});await refreshKids();setChosen(k.id);setTab('live')}catch(e){notice(e.message)}finally{setBusy(false)}};
 const toggle=async()=>{try{await post('/parent/sessions/'+data.active.id+'/reveal',{reveal:!data.active.revealed});refresh()}catch(e){notice(e.message)}};
 const saveAI=async()=>{setBusy(true);try{setAi(await post('/parent/ai',{enabled:ai.enabled,api_key:key||undefined,daily_limit:ai.daily_limit,cloud_enabled:ai.cloud_enabled,cloud_daily_limit:ai.cloud_daily_limit,coach_enabled:ai.coach_enabled,coach_daily_limit:ai.coach_daily_limit}));setKey('');notice('AI settings saved')}catch(e){notice(e.message)}finally{setBusy(false)}};
 const generate=async()=>{setBusy(true);try{const result=await post('/parent/children/'+chosen+'/coach');setAdvice(result.feedback);setAi(await api('/parent/ai'))}catch(e){notice(e.message)}finally{setBusy(false)}};
 const title=(eyebrow,heading,sub)=><div className="section-title"><span className="eyebrow">{eyebrow}</span><h1>{heading}</h1><p>{sub}</p></div>;
 const a=data?.active;
 return <div className="app parent"><Header user={user} logout={logout} tab={tab} setTab={setTab} parent/><main className="container">
 {tab==='live'&&<>{title('PARENT DASHBOARD',<>Every move, <em>in sight.</em></>,'Follow your child’s board live, see every try, and decide when to share the answer.')}
 <div className="children-strip">{kids.map(k=><button className={chosen===k.user.id?'picked':''} onClick={()=>setChosen(k.user.id)} key={k.user.id}><span>♟</span><div><strong>{k.user.name}</strong><small>{k.stats.completed} puzzles</small></div></button>)}<button onClick={()=>setTab('children')}>+ Add child</button></div>
 {!data?<div className="panel empty">No children yet. Add a child to see live games. <Action onClick={()=>setTab('children')}>Add a child</Action></div>:<>
 <div className="stats"><Stat color="violet" icon={Trophy} number={data.stats.completed} label="Exercises finished"/><Stat color="orange" icon={Star} number={data.stats.xp} label="XP earned"/><Stat color="mint" icon={Target} number={data.stats.completed?Math.round(100*data.stats.correct/data.stats.completed)+'%':'0%'} label="First-try accuracy"/></div>
 <div className="parent-grid"><div className="panel board-panel"><div className="between"><div><span className="eyebrow">LIVE FAMILY BOARD</span><h2>{data.child.name}'s chessboard</h2></div><span className="live"><Wifi size={15}/> Live</span></div>{a?<Board fen={a.fen} readonly name="parent-board"/>:<div className="empty-board"><span>♙</span><h3>Waiting for a game</h3><p>Your child's next chessboard will appear here.</p></div>}<div className="board-instruction">{a?'Last activity · '+new Date(a.updated_at).toLocaleTimeString():'No active session yet'}</div></div>
 <aside><div className="panel"><span className="eyebrow">CURRENT LESSON</span><h2>{a?.puzzle?.title||'Waiting for a lesson'}</h2><p>{a?.puzzle?area(a.puzzle.category).desc:'Your child can pick a puzzle on their home screen.'}</p>
 {a?.puzzle&&<><div className="info-line"><span>Category</span><b>{area(a.puzzle.category).name}</b></div><div className="info-line"><span>Incorrect attempts</span><b>{a.errors}</b></div><div className="info-line"><span>Status</span><b>{a.solved?'Solved!':'Practicing'}</b></div><div className="reveal"><div><LockKeyhole size={22}/><span><b>Reveal solution to child</b><small>You control when they see the answer.</small></span></div><button role="switch" aria-checked={a.revealed} className={'toggle '+(a.revealed?'on':'')} onClick={toggle}><span/></button></div><Action kind="soft" icon={Play} onClick={()=>setSolution(a.puzzle)}>Watch animated solution</Action></>}</div>
 <div className="panel activity"><span className="eyebrow">LIVE ACTIVITY</span><h2>Move-by-move</h2>{a?.moves.length?<div className="activity-list">{a.moves.slice(-12).reverse().map((m,i)=><div key={i}><span className={m.correct===false?'err-dot':''}/><b>{m.san||m.move||('Tap '+m.square)}</b><small>{m.correct===false?'Incorrect try':m.auto?'Automatic opponent reply':'Move recorded'}</small></div>)}</div>:<p>No moves yet. Activity appears here automatically.</p>}</div></aside></div>
 <div className="section-title"><span className="eyebrow">WHAT TO PRACTICE NEXT</span><h2>Progress by skill</h2></div><div className="panel progress-list">{Object.entries(AREAS).map(([k,c])=>{const s=data.stats.by_category[k];return <div className="progress-item" key={k}><span>{c.emoji}</span><div><strong>{c.name}</strong><small>{s.attempts} completed</small><div className="track"><div style={{width:(s.accuracy||0)+'%'}}/></div></div><b>{s.accuracy==null?'New':s.accuracy+'%'}</b></div>})}</div></>}
 </>}
 {tab==='games'&&<><div className="children-strip">{kids.map(k=><button className={chosen===k.user.id?'picked':''} onClick={()=>setChosen(k.user.id)} key={k.user.id}><span>♟</span><div><strong>{k.user.name}</strong><small>View their game</small></div></button>)}</div><ParentGame childId={chosen} notice={notice}/></>}
 {tab==='library'&&<>{title('THE EXERCISE VAULT','A whole library of clever moves','Every answer is legally validated by the chess engine. Parents can preview it first.')}
 <div className="filters">{Object.entries(AREAS).map(([k,c])=><button key={k} className={filter===k?'active':''} onClick={()=>{setFilter(k);setPage(0)}}>{c.emoji} {c.name} <small>{catalog?.categories?.[k]?.count||0}</small></button>)}</div>
 <div className="library-grid">{library.map(p=><button className="panel puzzle-card" key={p.id} onClick={()=>setSolution(p)}><span>{area(p.category).emoji}</span><div><strong>{p.title}</strong><small>{p.theme} · Rating {p.rating} · {p.source}</small></div><Play size={18}/></button>)}</div>
 <div className="pagination"><Action kind="outline" disabled={!page} onClick={()=>setPage(Math.max(0,page-1))}>← Previous</Action><b>Page {page+1}</b><Action kind="outline" disabled={library.length<16} onClick={()=>setPage(page+1)}>Next →</Action></div></>}
 {tab==='children'&&<>{title('FAMILY SPACE','Manage your young players','Every child has a private login, progress history and live board.')}
 <div className="two-columns"><div className="panel"><h2>My children</h2>{kids.map(k=><div className="child-line" key={k.user.id}><span>♟</span><div><b>{k.user.name}</b><small>@{k.user.username} · {k.stats.completed} puzzles</small></div><button className="link" onClick={()=>{setChosen(k.user.id);setTab('live')}}>See board →</button></div>)}{!kids.length&&<p>Add a child to begin!</p>}</div>
 <div className="panel"><h2>Add a child</h2><p>Create a separate account, managed only by you.</p><form className="form" onSubmit={addKid}><label>Child's name<input required value={newKid.name} onChange={e=>setNewKid({...newKid,name:e.target.value})} placeholder="First name"/></label><label>Username<input required pattern="[a-zA-Z][a-zA-Z0-9_]{2,39}" value={newKid.username} onChange={e=>setNewKid({...newKid,username:e.target.value})} placeholder="e.g. sophiachess"/></label><label>Password (10+ characters)<input type="password" minLength="10" required value={newKid.password} onChange={e=>setNewKid({...newKid,password:e.target.value})}/></label><Action type="submit" disabled={busy} icon={Plus}>Create child account</Action></form></div></div></>}
 {tab==='ai'&&<>{title('OPTIONAL AI COACH','Personal coaching, your way','Your API key stays encrypted on the backend. AI never writes puzzle answer keys.')}
 <div className="two-columns"><div className="panel"><span className="big-icon">🤖</span><h2>Connect your OpenAI API key</h2><p>Off by default. The key is encrypted in the server database. We never return it to the browser after saving, and never put it in GitHub or localStorage.</p><label className="form">OpenAI API key<input value={key} type="password" autoComplete="off" placeholder={ai.has_key?'Encrypted key saved · enter to replace':'Paste an sk-... API key'} onChange={e=>setKey(e.target.value)}/></label>
 <label className="form">Maximum AI reports per day<select value={ai.daily_limit} onChange={e=>setAi({...ai,daily_limit:Number(e.target.value)})}>{[1,3,5,10].map(n=><option key={n} value={n}>{n} per day</option>)}</select></label>
 <p className="ai-meter"><Shield size={16}/> {ai.used_today||0} of {ai.daily_limit} requests used today (UTC). The server enforces this limit even if the page is refreshed.</p><div className="reveal"><div><span><b>Enable AI reports</b><small>API usage may cost money.</small></span></div><button role="switch" aria-checked={ai.enabled} className={'toggle '+(ai.enabled?'on':'')} onClick={()=>setAi({...ai,enabled:!ai.enabled})}><span/></button></div><div className="gp-cloud-setting"><div className="reveal"><div><span><b>Allow AI explanations during robot games</b><small>Optional. Stockfish selects moves; OpenAI explains learning moments. The adaptive chess engine works without a key.</small></span></div><button role="switch" aria-checked={ai.cloud_enabled} className={'toggle '+(ai.cloud_enabled?'on':'')} onClick={()=>setAi({...ai,cloud_enabled:!ai.cloud_enabled})}><span/></button></div>
 <label className="form">Maximum AI explanations per day<select value={ai.cloud_daily_limit} onChange={e=>setAi({...ai,cloud_daily_limit:Number(e.target.value)})}>{[5,10,20,30,50].map(n=><option key={n} value={n}>{n} explanations</option>)}</select></label>
 <p className="ai-meter"><Shield size={16}/> {ai.cloud_moves_today||0} of {ai.cloud_daily_limit} optional explanations used today. Children cannot turn this on themselves.</p></div>
 <div className="gp-cloud-setting"><div className="reveal"><div><span><b>Enable Coach Hoang's AI training plans and explanations</b><small>Parent permission required. JChess chooses verified puzzles; AI helps explain the ideas, and Stockfish handles chess accuracy.</small></span></div><button role="switch" aria-checked={ai.coach_enabled} className={'toggle '+(ai.coach_enabled?'on':'')} onClick={()=>setAi({...ai,coach_enabled:!ai.coach_enabled})}><span/></button></div>
 <label className="form">Student coach AI requests per day<select value={ai.coach_daily_limit} onChange={e=>setAi({...ai,coach_daily_limit:Number(e.target.value)})}>{[1,3,5,10,20,50].map(n=><option key={n} value={n}>{n} requests</option>)}</select></label>
 <p className="ai-meter"><Shield size={16}/> {ai.coach_requests_today||0} of {ai.coach_daily_limit} student coach AI requests used today (UTC). Each new AI-assisted training plan or post-exercise explanation uses one request. Verified lessons and thinking hints are always free.</p></div>
 <Action icon={KeyRound} onClick={saveAI} disabled={busy}>Save settings</Action><button className="link" onClick={async()=>{if(!window.confirm('Disable AI and permanently delete the encrypted API key from JChess?'))return;try{setAi(await post('/parent/ai',{enabled:false,api_key:''}));setKey('');setAdvice('');notice('AI disabled and saved key deleted')}catch(e){notice(e.message)}}}>Disable AI and delete saved key</button><p className="privacy-note">Only parents can change this setting. The child cannot see or use the key. Disable AI at any time; revoke the key on the OpenAI dashboard if you suspect exposure.</p></div>
 <div className="panel"><span className="big-icon">♞</span><h2>Coach Hoang · Student training</h2><p>Coach Hoang evaluates patterns in completed exercises, creates six verified drills per session, and gives short explanations after problems are solved. Without an API key, the training plan and hints still work using verified chess data.</p><ParentCoachPreview childId={chosen} notice={notice}/></div>
 <div className="panel"><span className="big-icon">✨</span><h2>Personal learning report</h2><p>Only when you press the button, JChess sends category names and aggregated correct/attempted counts to OpenAI. No child name, username, moves, board positions or passwords are sent. AI suggestions are not chess-engine-validated.</p><label className="form">Child<select value={chosen??''} onChange={e=>setChosen(Number(e.target.value))}>{kids.map(k=><option key={k.user.id} value={k.user.id}>{k.user.name}</option>)}</select></label><Action icon={WandSparkles} onClick={generate} disabled={!ai.enabled||!chosen||busy||!ai.remaining_today}>{busy?'Analyzing...':!ai.remaining_today?'Daily limit reached':'Get learning recommendations'}</Action>{advice&&<div className="advice">{advice}</div>}</div></div></>}
 </main><footer>JChess Academy · Private family learning</footer>
 {solution&&<div className="overlay" onClick={()=>setSolution(null)}><div className="modal" onClick={e=>e.stopPropagation()}><Solution puzzle={solution} onClose={()=>setSolution(null)}/></div></div>}
 </div>;
}
export default function App(){
 const guestToken=new URLSearchParams(window.location.hash.slice(1)).get('join');
 const [user,setUser]=useState(undefined),[notice,setNotice]=useState('');
 const refresh=useCallback(async()=>{try{setUser(await api('/auth/me'))}catch{setUser(null)}},[]);
 useEffect(()=>{refresh()},[refresh]);
 const logout=async()=>{try{await post('/auth/logout')}catch{}setUser(null)};
 useEffect(()=>{if(!notice)return;const t=setTimeout(()=>setNotice(''),4500);return()=>clearTimeout(t)},[notice]);
 return guestToken?<GuestGame token={guestToken}/>:<>{notice&&<div role="status" className="toast">{notice}</div>}{user===undefined?<div className="loading">♞<p>Preparing your chess adventure...</p></div>:!user?<Auth onLogin={setUser} notice={setNotice}/>:user.must_reset?<ResetPassword user={user} notice={setNotice} refresh={refresh} logout={logout}/>:user.role==='parent'?<Parent user={user} notice={setNotice} logout={logout}/>:<Child user={user} notice={setNotice} logout={logout}/>}</>
}
