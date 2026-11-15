import React,{useState,useEffect,useCallback} from 'react';
import {Chess} from 'chess.js';
import {Chessboard} from 'react-chessboard';
import {Bot,Users,UserRound,Smartphone,Cloud,ShieldCheck,Copy,ArrowLeft,RotateCcw,Play,Clock,Wifi,CheckCircle2,AlertCircle} from 'lucide-react';

async function apiGame(path,data){
 const response=await fetch('/api'+path,{method:data===undefined?'GET':'POST',
   credentials:'same-origin',headers:{'Content-Type':'application/json'},
   body:data===undefined?undefined:JSON.stringify(data)});
 const payload=await response.json().catch(()=>({detail:'Server unavailable'}));
 if(!response.ok)throw Error(payload.detail||'Unable to update chess game');
 return payload;
}
const MODES=[
 {id:'bot',name:'Play a robot',icon:Bot,desc:'Free chess opponent with three levels. No API key required.'},
 {id:'parent',name:'Play a parent',icon:UserRound,desc:'Play White while your parent plays Black from their account.'},
 {id:'friend',name:'Invite a friend',icon:Users,desc:'Share a private link so a friend can join from their device.'},
 {id:'local',name:'Share one screen',icon:Smartphone,desc:'Take turns together on the same tablet or computer.'}
];
const LEVELS=[
 {id:'easy',title:'Easy',desc:'Explores and sometimes makes mistakes'},
 {id:'medium',title:'Medium',desc:'Notices pieces and simple threats'},
 {id:'hard',title:'Hard',desc:'Thinks further ahead and punishes blunders'}
];

export function GameSetup({onStart,resume,notice}){
 const [options,setOptions]=useState({offline_available:true,cloud_available:false,parent_available:true});
 const [mode,setMode]=useState('bot'),[level,setLevel]=useState('easy'),[provider,setProvider]=useState('builtin'),[busy,setBusy]=useState(false);
 useEffect(()=>{apiGame('/child/game/options').then(setOptions).catch(e=>notice(e.message))},[notice]);
 const start=async()=>{setBusy(true);try{await onStart({mode,level,provider:mode==='bot'?provider:'builtin'})}catch(e){notice(e.message)}finally{setBusy(false)}};
 return <section className="gp-setup">
  <div className="gp-intro"><span className="eyebrow">CHESS PLAYROOM</span><h1>Who do you want to play? ♟️</h1><p>Practice against a robot or challenge a real person. All games use real chess rules.</p></div>
  {resume&&resume.status==='active'&&<button className="gp-resume" onClick={()=>onStart(null)}><Play size={18}/> Continue your {resume.mode==='bot'?'robot':resume.mode==='local'?'two-player':'friendly'} game <span>→</span></button>}
  <div className="gp-modes">{MODES.map(m=>{const Icon=m.icon;return <button key={m.id} onClick={()=>{setMode(m.id);if(m.id!=='bot')setProvider('builtin')}} className={'gp-mode '+(mode===m.id?'selected':'')}><Icon size={25}/><strong>{m.name}</strong><span>{m.desc}</span></button>})}</div>
  {mode==='bot'&&<div className="gp-config"><div><span className="eyebrow">ROBOT DIFFICULTY</span><h2>Choose your challenge</h2></div><div className="gp-levels">{LEVELS.map(l=><button className={level===l.id?'selected':''} key={l.id} onClick={()=>setLevel(l.id)}><strong>{l.title}</strong><small>{l.desc}</small></button>)}</div>
   <div className="gp-provider"><div><Bot size={21}/><div><b>Built-in chess robot</b><small>Free, private, and works without AI API credits</small></div></div><button className={provider==='builtin'?'selected':''} onClick={()=>setProvider('builtin')}>{provider==='builtin'?'Selected':'Choose'}</button></div>
   {options.cloud_available?<div className="gp-provider"><div><Cloud size={21}/><div><b>Cloud AI robot</b><small>Parent-enabled OpenAI key · {options.cloud_moves_remaining} moves left today</small></div></div><button className={provider==='cloud'?'selected':''} onClick={()=>setProvider('cloud')}>{provider==='cloud'?'Selected':'Choose'}</button></div>:<div className="gp-locked"><ShieldCheck size={17}/><span>Cloud AI is turned off by your parent. The free built-in robot is always ready.</span></div>}
  </div>}
  {mode==='friend'&&<p className="gp-note"><ShieldCheck size={17}/> An invite link grants the other player control of Black's pieces. Share it only with someone you trust.</p>}
  {mode==='parent'&&<p className="gp-note"><Wifi size={17}/> Ask your parent to sign in and open <b>Play together</b> after you start the game.</p>}
  {mode==='local'&&<p className="gp-note"><Smartphone size={17}/> One screen, two people. The board flips each turn.</p>}
  <button className="gp-start" disabled={busy||mode==='parent'&&!options.parent_available||mode==='bot'&&provider==='cloud'&&!options.cloud_available} onClick={start}>{busy?'Starting…':'Start the game'} <Play size={18}/></button>
 </section>;
}

function MatchBoard({game,role,onMove,busy}){
 const [selected,setSelected]=useState('');
 useEffect(()=>setSelected(''),[game?.fen]);
 if(!game)return null;
 const orientation=role==='child'&&game.mode==='local'?game.turn:role==='child'?'white':'black';
 const myTurn=(role==='child'?(game.mode==='local'||game.turn==='white'):game.turn==='black');
 const canMove=game.status==='active'&&myTurn&&!busy;
 const tryMove=(from,to)=>{
   if(!canMove)return false;
   const chess=new Chess(game.fen),piece=chess.get(from);
   if(!piece||piece.color!==chess.turn())return false;
   if(!chess.moves({square:from,verbose:true}).some(m=>m.to===to))return false;
   const promotion=piece.type==='p'&&['1','8'].includes(to[1])?'q':'';
   onMove(from+to+promotion);setSelected('');return true;
 };
 const clickSquare=square=>{
   if(!canMove)return;
   if(selected&&tryMove(selected,square))return;
   const chess=new Chess(game.fen),p=chess.get(square);
   setSelected(p&&p.color===chess.turn()?square:'');
 };
 return <div className="gp-board"><Chessboard id={'game-'+role} position={game.fen} boardOrientation={orientation} arePiecesDraggable={canMove} onPieceDrop={tryMove} onSquareClick={clickSquare}
  animationDuration={400} customBoardStyle={{borderRadius:'14px',boxShadow:'0 14px 35px #18315528'}}
  customLightSquareStyle={{backgroundColor:'#f1f1e5'}} customDarkSquareStyle={{backgroundColor:'#84aaa5'}}
  customSquareStyles={selected?{[selected]:{backgroundColor:'#fedb68'}}:{}}/></div>;
}
export function GameRoom({game,role='child',onMove,onNew,invite,busy=false}){
 const [copied,setCopied]=useState(false);
 if(!game)return <div className="gp-empty"><span>♟️</span><h2>No game started</h2><p>Choose a game mode to begin.</p>{onNew&&<button onClick={onNew}>Choose a game</button>}</div>;
 const title=game.mode==='bot'?(game.provider==='cloud'?'Cloud AI robot':'Built-in robot')+' · '+game.level:game.mode==='parent'?'Play with parent':game.mode==='friend'?'Play with a friend':'Pass and play';
 const message=game.status==='active'?(role==='child'?(game.mode==='local'?'Pass the board to '+(game.turn==='white'?'White':'Black'):game.turn==='white'?'Your move!':'Waiting for your opponent…'):game.turn==='black'?'Your move!':'Waiting for White…'):
   game.status==='draw'?'Game drawn 🤝':game.status==='white_wins'?'White wins! 🏆':'Black wins! 🏆';
 const inviteLink=invite?window.location.origin+'/?guest=1#join='+encodeURIComponent(invite):'';
 const copy=async()=>{try{await navigator.clipboard.writeText(inviteLink);setCopied(true)}catch{setCopied(false)}};
 return <section className="gp-room">
  <div className="gp-room-head"><div><span className="eyebrow">CHESS PLAYROOM</span><h1>{title}</h1><p>{game.status==='active'?'Think before moving. Checks, captures and threats!':'You finished the game. Time for a new challenge?'}</p></div><span className={'gp-status '+(game.status==='active'?'playing':'finished')}><span/> {game.status==='active'?'Game in progress':'Game over'}</span></div>
  <div className="gp-room-grid"><div className="panel gp-board-panel"><div className="gp-turn"><span>{role==='child'?'♙ You play White':role==='parent'?'♟ You play Black':'♟ Friend plays Black'}</span><strong>{busy?'Moving…':message}</strong></div><MatchBoard game={game} role={role} onMove={onMove} busy={busy}/><div className="gp-under-board"><span>{game.turn==='white'?'♔ White to move':'♚ Black to move'}</span><small>{game.moves.length} half-moves</small></div></div>
  <aside className="gp-aside">
   {role==='child'&&game.mode==='friend'&&<div className="panel gp-share"><span className="eyebrow">INVITE A FRIEND</span><h2>Send your game link</h2>{inviteLink?<><p>Send this private link to your friend. They can play Black without making an account.</p><input aria-label="Private friend invitation" value={inviteLink} readOnly onFocus={e=>e.target.select()}/><button onClick={copy}><Copy size={16}/> {copied?'Copied!':'Copy invitation'}</button></>:<p>The invite link was available when this game started. Use the same browser session, or create a new friend game for a new link.</p>}</div>}
   {role==='child'&&game.mode==='parent'&&<div className="panel gp-share"><span className="eyebrow">FAMILY GAME</span><h2>Waiting for your parent</h2><p>Your parent can open their account and choose <b>Play together</b>. Moves appear on both screens.</p></div>}
   <div className="panel gp-history"><span className="eyebrow">MOVE HISTORY</span><h2>Every move counts</h2>{game.moves.length?<div className="gp-moves">{game.moves.slice(-16).map((move,i)=><div key={i}><span>{move.color==='white'?'♙':'♟'}</span><strong>{move.san}</strong><small>{move.actor==='cloud'?'Cloud AI':move.actor==='builtin'?'Robot':move.actor==='fallback'?'Free bot fallback':move.actor==='white'?'White':'Black'}</small></div>)}</div>:<p>It's your first move. Let's begin!</p>}</div>
   {onNew&&<button className="gp-new" onClick={onNew}><RotateCcw size={17}/> Start another game</button>}
   {game.provider==='cloud'&&<p className="gp-note"><ShieldCheck size={17}/> Cloud moves use the parent's allowance. If unavailable, the free robot takes over.</p>}
  </aside></div>
 </section>;
}

export function ParentGame({childId,notice}){
 const [game,setGame]=useState(null),[busy,setBusy]=useState(false);
 const refresh=useCallback(async()=>{if(!childId){setGame(null);return}try{const data=await apiGame('/parent/game/current?child_id='+childId);setGame(data)}catch(e){notice(e.message)}},[childId,notice]);
 useEffect(()=>{refresh();const t=setInterval(refresh,1800);return()=>clearInterval(t)},[refresh]);
 const move=async uci=>{if(!game||busy)return;setBusy(true);try{setGame(await apiGame('/parent/game/move',{game_id:game.id,uci}))}catch(e){notice(e.message);refresh()}finally{setBusy(false)}};
 return <><div className="gp-intro"><span className="eyebrow">PARENT VS CHILD</span><h1>Play together from any device</h1><p>When your child starts a Parent game, you can play Black here. The board updates automatically.</p></div>{game?<><GameRoom game={game} role="parent" onMove={move} busy={busy}/>{game.mode!=='parent'&&<p className="gp-note"><ShieldCheck size={16}/> This is the child's latest game. Ask them to choose <b>Play a parent</b> to give you the Black seat.</p>}</>:<div className="gp-empty"><Clock size={25}/><h2>Waiting for a game</h2><p>Ask your child to choose Play a parent.</p></div>}</>;
}

export function GuestGame({token}){
 const [game,setGame]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const refresh=useCallback(async()=>{try{setGame(await apiGame('/guest/game/current',{token}));setError('')}catch(e){setError(e.message)}},[token]);
 useEffect(()=>{refresh();const t=setInterval(refresh,1800);return()=>clearInterval(t)},[refresh]);
 const move=async uci=>{if(!game||busy)return;setBusy(true);try{setGame(await apiGame('/guest/game/move',{token,uci}))}catch(e){setError(e.message);refresh()}finally{setBusy(false)}};
 return <div className="app gp-guest-page"><header className="gp-guest-header"><strong>♞ JChess Academy</strong><small>Friendly chess match</small></header><main className="container"><div className="gp-intro"><span className="eyebrow">YOUR FRIEND INVITED YOU</span><h1>Let's play chess! ♟️</h1><p>You control Black's pieces. Make your move when it's your turn.</p></div>{error&&<div role="alert" className="gp-error"><AlertCircle size={18}/>{error}</div>}{game?<GameRoom game={game} role="friend" onMove={move} busy={busy}/>:<div className="gp-empty">Opening your private game…</div>}</main></div>;
}
