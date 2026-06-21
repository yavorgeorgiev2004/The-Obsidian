/* ============================================
   THE OBSIDIAN — JAVASCRIPT
   Flawlessly Dark. Infinitely Refined.
   ============================================ */

// =============================================
// COSMIC CANVAS — background canvas element
// =============================================
// Guard against pages that do not include the canvas, so the script
// never throws and the rest of the page behaviour still runs.
const canvas = document.getElementById('cosmicCanvas');
let W, H, ctx;
if (canvas) {
  ctx = canvas.getContext('2d');
  function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
  resize();
  window.addEventListener('resize', resize);
}



// =============================================
// DIAMOND SPARKLE DOM ELEMENTS
// =============================================
// Skip the floating sparkles on auth pages (login/register) so they
// never drift over the sign-in form. Other pages get the full effect.
if (!document.body.classList.contains('no-sparkle')) {
  for (let i=0;i<14;i++) {
    const s=document.createElement('div');
    s.className='sparkle'; s.textContent='◆';
    s.style.setProperty('--dur',(6+Math.random()*10)+'s');
    s.style.setProperty('--delay',(Math.random()*12)+'s');
    s.style.left=(Math.random()*100)+'vw';
    s.style.top=(20+Math.random()*75)+'vh';
    s.style.fontSize=(0.3+Math.random()*0.5)+'rem';
    document.body.appendChild(s);
  }
}

// =============================================
// CUSTOM CURSOR
// =============================================
const cursor=document.querySelector('.cursor');
const follower=document.querySelector('.cursor-follower');
let mouseX=0,mouseY=0,followerX=0,followerY=0;
// Only run the custom cursor when its elements are present.
if (cursor && follower) {
document.addEventListener('mousemove',e=>{
  mouseX=e.clientX; mouseY=e.clientY;
  cursor.style.left=mouseX+'px'; cursor.style.top=mouseY+'px';
});
(function af(){
  followerX+=(mouseX-followerX)*0.12; followerY+=(mouseY-followerY)*0.12;
  follower.style.left=followerX+'px'; follower.style.top=followerY+'px';
  requestAnimationFrame(af);
})();
document.querySelectorAll('a,button,.room-card,.sig-card,.cat-item,.sports-card,.cs-item').forEach(el=>{
  el.addEventListener('mouseenter',()=>{
    cursor.style.transform='translate(-50%,-50%) scale(2.5)';
    cursor.style.background='transparent';
    cursor.style.border='1px solid var(--gold)';
    follower.style.opacity='0';
  });
  el.addEventListener('mouseleave',()=>{
    cursor.style.transform='translate(-50%,-50%) scale(1)';
    cursor.style.background='var(--gold)';
    cursor.style.border='none';
    follower.style.opacity='0.6';
  });
});
if('ontouchstart'in window){cursor.style.display='none';follower.style.display='none';document.body.style.cursor='auto';}
}

// =============================================
// NAVBAR
// =============================================
const nav=document.getElementById('nav');
// Only attach the scroll behaviour when the public nav is present.
if (nav) window.addEventListener('scroll',()=>nav.classList.toggle('scrolled',window.scrollY>60));

// =============================================
// MOBILE MENU
// =============================================
const hamburger=document.getElementById('hamburger');
const mobileMenu=document.getElementById('mobileMenu');
let menuOpen=false;
// Only wire the mobile menu when both elements exist (public pages).
if (hamburger && mobileMenu) hamburger.addEventListener('click',()=>{
  menuOpen=!menuOpen;
  mobileMenu.classList.toggle('open',menuOpen);
  document.body.style.overflow=menuOpen?'hidden':'';
  const spans=hamburger.querySelectorAll('span');
  spans[0].style.transform=menuOpen?'rotate(45deg) translate(4px,4px)':'';
  spans[1].style.opacity=menuOpen?'0':'';
  spans[2].style.transform=menuOpen?'rotate(-45deg) translate(4px,-4px)':'';
});
function closeMobile(){
  if (!hamburger || !mobileMenu) return;
  menuOpen=false; mobileMenu.classList.remove('open');
  document.body.style.overflow='';
  hamburger.querySelectorAll('span').forEach(s=>{s.style.transform='';s.style.opacity='';});
}

// =============================================
// SCROLL REVEAL
// =============================================
document.querySelectorAll(
  '.room-card,.dining-card,.spa-feature,.sig-card,.cat-item,.sports-card,.event-card,.transport-card,.kids-feat,.stat,.section-header,.intro-text,.intro-stats,.cs-item,.concierge-left,.concierge-form'
).forEach(el=>el.classList.add('reveal'));
const ro=new IntersectionObserver(entries=>{
  entries.forEach(entry=>{
    if(!entry.isIntersecting)return;
    // A smaller per-item stagger so a fast scroller does not catch items
    // still mid-animation; capped so the last item is barely delayed.
    const idx=Array.from(entry.target.parentElement.children).indexOf(entry.target)%6;
    setTimeout(()=>entry.target.classList.add('visible'),idx*35);
    ro.unobserve(entry.target);
  });
},{threshold:0.04,rootMargin:'0px 0px 80px 0px'});
document.querySelectorAll('.reveal').forEach(el=>ro.observe(el));

// =============================================
// DATE INPUTS
// =============================================
const today=new Date().toISOString().split('T')[0];
const tmr=new Date(); tmr.setDate(tmr.getDate()+1);
const tmrStr=tmr.toISOString().split('T')[0];
document.querySelectorAll('input[type="date"]').forEach(i=>{i.min=today;i.value=today;});
const [checkin,checkout]=document.querySelectorAll('input[type="date"]');
if(checkin&&checkout){
  checkout.value=tmrStr;
  checkin.addEventListener('change',()=>{
    checkout.min=checkin.value;
    if(checkout.value<=checkin.value){
      const nx=new Date(checkin.value);nx.setDate(nx.getDate()+1);
      checkout.value=nx.toISOString().split('T')[0];
    }
  });
}

// =============================================
// BOOKING SUBMIT
// =============================================
const bookBtn=document.querySelector('.btn-primary--book');
if(bookBtn) bookBtn.addEventListener('click',()=>{
  if(checkin&&checkout) showToast(`◆ Reservation request received\n${checkin.value} → ${checkout.value}\nOur concierge will confirm within 2 hours.`);
});

// =============================================
// CONCIERGE SUBMIT
// =============================================
// The homepage concierge request is now a link into the real, login-gated
// request flow, so no client-side submit handling is needed here.

// =============================================
// TOAST NOTIFICATION
// =============================================
function showToast(message) {
  document.querySelector('.obsidian-toast')?.remove();
  const toast=document.createElement('div');
  toast.className='obsidian-toast';
  toast.innerHTML=message.replace(/\n/g,'<br/>');
  Object.assign(toast.style,{
    position:'fixed',bottom:'2rem',right:'2rem',
    background:'var(--dark-grey)',border:'1px solid var(--gold)',
    color:'var(--white)',padding:'1.5rem 2rem',
    fontFamily:'var(--font-body)',fontSize:'0.8rem',lineHeight:'1.8',
    letterSpacing:'0.05em',zIndex:'9999',maxWidth:'360px',
    opacity:'0',transform:'translateY(20px)',transition:'all 0.4s ease',
    boxShadow:'0 0 40px rgba(201,168,76,0.12)',
  });
  document.body.appendChild(toast);
  setTimeout(()=>{toast.style.opacity='1';toast.style.transform='translateY(0)';},10);
  setTimeout(()=>{
    toast.style.opacity='0';toast.style.transform='translateY(10px)';
    setTimeout(()=>toast.remove(),400);
  },5000);
}

// =============================================
// HERO CLICK — GOLD PARTICLE BURST
// =============================================
// Only runs on pages that actually have a hero (the homepage).
const heroEl = document.querySelector('.hero');
if (heroEl) heroEl.addEventListener('click',e=>{
  for(let i=0;i<12;i++){
    const p=document.createElement('div');
    const isD=i%3===0;
    p.textContent=isD?'◆':'';
    Object.assign(p.style,{
      position:'fixed',left:e.clientX+'px',top:e.clientY+'px',
      width:isD?'auto':'4px',height:isD?'auto':'4px',
      background:isD?'transparent':'#C9A84C',
      color:'#C9A84C',fontSize:isD?'0.5rem':'0',
      borderRadius:'50%',pointerEvents:'none',zIndex:'9999',
      transition:'all 0.9s cubic-bezier(.25,.46,.45,.94)',
      transform:'translate(-50%,-50%)',
    });
    document.body.appendChild(p);
    const angle=(i/12)*Math.PI*2, dist=50+Math.random()*80;
    setTimeout(()=>{
      p.style.transform=`translate(calc(-50% + ${Math.cos(angle)*dist}px),calc(-50% + ${Math.sin(angle)*dist}px)) rotate(${Math.random()*360}deg)`;
      p.style.opacity='0';
    },10);
    setTimeout(()=>p.remove(),920);
  }
});

// =============================================
// CONCIERGE ITEM GLINT
// =============================================
document.querySelectorAll('.cs-item').forEach(item=>{
  item.addEventListener('mouseenter',function(){
    const rect=this.getBoundingClientRect();
    const g=document.createElement('div');
    g.textContent='◆';
    Object.assign(g.style,{
      position:'fixed',left:(rect.right-20)+'px',top:(rect.top+10)+'px',
      color:'var(--gold)',fontSize:'0.4rem',pointerEvents:'none',zIndex:'100',
      opacity:'0',transition:'opacity 0.3s,transform 0.5s',transform:'scale(0.5)',
    });
    document.body.appendChild(g);
    setTimeout(()=>{g.style.opacity='0.8';g.style.transform='scale(1.8)';},10);
    setTimeout(()=>{g.style.opacity='0';},400);
    setTimeout(()=>g.remove(),700);
  });
});

// =============================================
// CONSOLE SIGNATURE
// =============================================
console.log('%c◆ THE OBSIDIAN','color:#C9A84C;font-size:24px;font-family:Georgia,serif;');
console.log('%cFlawlessly Dark. Infinitely Refined.','color:#8C6A3F;font-size:12px;font-family:Georgia,serif;');
console.log('%cCode Institute L5 Django Project','color:#3D3D3D;font-size:10px;');

// =============================================
// MOBILE MENU LINK CLOSE (external, replaces inline onclick)
// =============================================
// Close the mobile menu whenever any link inside it is clicked
document.querySelectorAll('.mobile-menu a').forEach(function (link) {
  link.addEventListener('click', function () {
    if (typeof closeMobile === 'function') closeMobile();
  });
});
