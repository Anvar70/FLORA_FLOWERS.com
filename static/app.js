const BOOT=JSON.parse(document.getElementById('boot').textContent);
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
let lang=BOOT.user?.language||localStorage.getItem('flora-language')||'uz';
if(!['en','uz','ru'].includes(lang))lang='uz';
let user=BOOT.user, path=location.pathname, page=1, modalReturn=null, currentConversation=null, pollBusy=false, authMode='login', authRole=new URLSearchParams(location.search).get('role')==='admin'?'admin':'customer', authLanguageChosen=false;
const t=k=>window.I18N[k]?.[['en','uz','ru'].indexOf(lang)]||k;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tr=v=>typeof v==='object'&&v?(v[lang]||v.en||Object.values(v)[0]||''):String(v??'');
const icon=(name)=>'<svg class="icon" aria-hidden="true" viewBox="0 0 24 24">'+(ICONS[name]||ICONS.flower)+'</svg>';
const money=(v,c=BOOT.currency)=>new Intl.NumberFormat({uz:'uz-UZ',en:'en-US',ru:'ru-RU'}[lang],{maximumFractionDigits:2}).format(Number(v))+' '+esc(c);
const date=v=>new Date(v).toLocaleString({uz:'uz-UZ',en:'en-GB',ru:'ru-RU'}[lang],{dateStyle:'medium',timeStyle:'short'});
const root=()=>user?.is_staff?'/manage/':'/workspace/';
const csrf=()=>document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1]||'';
async function api(url,method='GET',data){
  const generation=rendering;
  let response;
  try{response=await fetch(url,{method,credentials:'same-origin',headers:{'X-CSRFToken':csrf(),...(data instanceof FormData?{}:{'Content-Type':'application/json'})},...(data!==undefined?{body:data instanceof FormData?data:JSON.stringify(data)}:{})});}
  catch(e){throw Error(t('network_error'));}
  let result=await response.json().catch(()=>({}));
  if(method==='GET'&&generation!==rendering){const e=Error('Stale view');e.stale=true;throw e;}
  if(!response.ok){const err=result.error||{};let code=err.code;if(Array.isArray(code))code=code[0];if(!code){const values=[];const flatten=v=>{if(Array.isArray(v))v.forEach(flatten);else if(v&&typeof v==='object')Object.values(v).forEach(flatten);else values.push(v);};flatten(err);code=values.find(v=>typeof v==='string'&&I18N[v]);}throw Error(t(code||(response.status===403?'not_allowed':response.status===429?'try_later':'invalid_form')));}
  return result;
}
let toastTimer;
function toast(text){$('#toast').textContent=text;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),4500);}
function button(label,action,cls='secondary',extra=''){return '<button type="button" class="'+cls+'" data-action="'+action+'" '+extra+'>'+t(label)+'</button>';}
function field(name,label,value='',type='text',extra=''){return '<label>'+t(label)+'<input name="'+name+'" type="'+type+'" value="'+esc(value)+'" '+extra+'></label>';}
function area(name,label,value='',extra=''){return '<label>'+t(label)+'<textarea name="'+name+'" '+extra+'>'+esc(value)+'</textarea></label>';}
function select(name,label,options,value='',extra=''){return '<label>'+t(label)+'<select name="'+name+'" '+extra+'>'+options.map(([v,l])=>'<option value="'+esc(v)+'" '+(String(v)===String(value)?'selected':'')+'>'+esc(l)+'</option>').join('')+'</select></label>';}
function check(name,label,value=false){return '<label class="check"><input type="checkbox" name="'+name+'" '+(value?'checked':'')+'>'+t(label)+'</label>';}
function formError(){return '<div class="form-error" role="alert"></div>';}
function empty(text='empty',action=''){return '<div class="empty">'+icon('flower')+'<h3>'+t('empty')+'</h3><p>'+t(text)+'</p>'+action+'</div>';}
function heading(title,subtitle=''){return '<div class="page-heading"><div class="eyebrow">FLORA / '+(user?.is_staff?t('admin'):t('customer'))+'</div><h1>'+t(title)+'</h1>'+(subtitle?'<p>'+t(subtitle)+'</p>':'')+'</div>';}
function langControl(){return '<div class="language-control"><img class="flag" alt="" src="/static/flags/'+lang+'.svg"><select id="global-language" aria-label="'+t('language')+'"><option value="uz" '+(lang==='uz'?'selected':'')+'>O‘zbekcha</option><option value="en" '+(lang==='en'?'selected':'')+'>English</option><option value="ru" '+(lang==='ru'?'selected':'')+'>Русский</option></select></div>';}
function shell(){
 $('.skip-link').textContent=t('skip_content');
 const publicPage=path==='/',authPage=path==='/auth/';
 document.body.classList.toggle('public-shell', publicPage||authPage);
 const entries=publicPage||authPage?[['home','home','/'],['shop','flower',user?root()+'shop/':'/auth/'],['finder','sparkles','#finder'],['about','leaf','/#story']]:user?.is_staff?[['overview','dashboard','overview'],['products','flower','products'],['categories','grid','categories'],['orders','package','orders'],['customers','users','customers'],['conversations','message','conversations'],['notifications','bell','notifications'],['guide_admin','sparkles','guide'],['profile','user','profile'],['settings','settings','settings']]:[['dashboard','dashboard','dashboard'],['shop','flower','shop'],['categories','grid','categories'],['cart','bag','cart'],['orders','package','orders'],['messages','message','messages'],['profile','user','profile'],['settings','settings','settings']];
 $('#app').innerHTML='<aside class="sidebar" id="sidebar" aria-label="'+t('menu')+'"><a href="/" class="brand">flora<span>·</span></a><div class="brand-sub">FLOWERS & FEELINGS</div><div class="nav-label">'+(publicPage||authPage?'FLORAL STUDIO':t(user?.is_staff?'admin':'customer').toUpperCase())+'</div><nav class="nav-links">'+entries.map(([key,ic,href])=>{let link=href.startsWith('/')||href.startsWith('#')?href:root()+href+'/';return '<a href="'+link+'" '+(href==='#finder'?'data-action="finder"':'')+' class="'+(path===link?'active':'')+'" '+(path===link?'aria-current="page"':'')+'>'+icon(ic)+'<span>'+t(key)+'</span>'+(['notifications','messages','conversations'].includes(key)?'<span class="count" data-count="'+key+'"></span>':'')+'</a>';}).join('')+'</nav><div class="nav-foot">'+(publicPage?'<div class="side-note">'+t('footer_line')+'<small>'+t('demo')+'</small></div>':'')+langControl()+(user?'<button class="text-button small" data-action="logout">'+icon('logout')+t('logout')+'</button>':'')+'</div></aside><div class="layout"><header class="topbar"><button class="icon-button mobile-menu" data-action="menu" aria-label="'+t('menu')+'" aria-expanded="false">'+icon('menu')+'</button><div class="topbar-left">'+t(publicPage||authPage?'footer_line':'workspace_intro')+'</div><div class="top-actions"><button class="text-button" data-action="theme" aria-label="'+t(document.documentElement.dataset.theme==='dark'?'light':'dark')+'">'+icon(document.documentElement.dataset.theme==='dark'?'sun':'moon')+'</button>'+(user?'<a href="'+root()+'notifications/" aria-label="'+t('notifications')+'">'+icon('bell')+'<span data-count="notifications" class="count"></span></a><a href="'+root()+'cart/" aria-label="'+t('cart')+'">'+icon('bag')+'</a><a href="'+root()+'profile/">'+esc(user.name||t('profile'))+'</a>':'<a href="/auth/" data-auth="login">'+t('login')+'</a><a class="button" href="/auth/" data-auth="register">'+t('register')+'</a>')+'</div></header><main id="content" tabindex="-1" class="content '+(publicPage?'public-content':'')+'"><div class="loading"><span class="spinner"></span><div>'+t('loading')+'</div></div></main></div>';
}
function card(p){
 const available=p.variants.filter(v=>v.active),v=available.find(v=>v.stock>0)||available[0];
 return '<article class="product-card"><a class="product-picture" href="'+root()+'product/'+p.id+'/"><img src="'+esc(p.image_url)+'" alt="'+esc(tr(p.name))+'" loading="lazy"></a><button class="favorite-button" data-action="favorite" data-id="'+p.id+'" aria-label="'+t('save_favorite')+'">'+icon('heart')+'</button><div class="product-meta"><small>'+esc(tr(p.category_name))+'</small><h3><a href="'+root()+'product/'+p.id+'/">'+esc(tr(p.name))+'</a></h3><div class="product-bottom"><span class="price">'+(v?money(Math.min(...available.map(x=>Number(x.price)))):t('unavailable'))+'</span><button class="icon-button" data-action="quick-add" data-variant="'+(v?.id||'')+'" '+(!v?.stock?'disabled':'')+' aria-label="'+t('add_cart')+'">'+icon('plus')+'</button></div></div></article>';
}
async function landing(){
 const result=await api('/api/products/?page_size=3');const products=result.results.slice(0,3);
 $('#content').innerHTML='<section class="hero"><div class="hero-copy"><div class="eyebrow">'+t('eyebrow')+'</div><h1>'+t('hero_title')+'</h1><p>'+t('hero_text')+'</p><div class="hero-actions"><a class="button" href="'+(user?root()+'shop/':'/auth/')+'">'+t('explore')+icon('arrow-right')+'</a><button class="text-button" data-action="finder">'+t('find_match')+' ↗</button></div></div><div class="hero-media"><img src="/static/images/hero.jpg" alt="'+t('photo_alt')+'" fetchpriority="high"><div class="hero-stamp">FLORA<br>BOTANICAL<br>STUDIO</div><div class="hero-caption"><span>'+t('hero_caption')+'</span><small>'+t('seasonal')+'</small></div></div></section><section class="benefits">'+[['fresh','fresh_text','leaf'],['handmade','handmade_text','flower'],['delivery','delivery_text','truck'],['little_note','note_text','mail']].map(([a,b,c])=>'<div class="benefit">'+icon(c)+'<div><strong>'+t(a)+'</strong><p>'+t(b)+'</p></div></div>').join('')+'</section><section><div class="section-head"><div><div class="eyebrow">'+t('seasonal')+'</div><h2>'+t('bestsellers')+'</h2></div><a href="'+(user?root()+'shop/':'/auth/')+'">'+t('view_all')+' ↗</a></div><div class="product-grid">'+products.map(card).join('')+'</div></section><section class="public-section story" id="story"><img src="/static/images/tulips.jpg" alt="'+t('photo_alt')+'" loading="lazy"><div class="story-copy"><div class="eyebrow">'+t('about')+'</div><h2>'+t('story_title')+'</h2><p>'+t('story_text')+'</p><span class="demo-tag">'+t('demo')+'</span></div></section><section class="public-section"><div class="section-head"><h2>'+t('how')+'</h2></div><div class="steps">'+[1,2,3].map(n=>'<div><span class="step-num">0'+n+'</span><h3>'+t('step'+n)+'</h3><p>'+t('step'+n+'text')+'</p></div>').join('')+'</div></section><section class="faq"><h2>'+t('faq')+'</h2>'+['delivery','payment','care'].map(k=>'<details><summary>'+t('faq_'+k)+'</summary><p>'+t('faq_'+k+'_a')+'</p></details>').join('')+'</section><footer class="contact-footer"><div><a class="brand" href="/">flora<span>·</span></a><p>'+t('footer_line')+'</p><span class="demo-tag">'+t('demo')+'</span></div><div><h3>'+t('contact')+'</h3><div class="contact-list">'+[['phone','phone'],['address','pin'],['email','mail']].map(([k,i])=>'<div>'+icon(i)+'<span>'+esc(BOOT.contact[k].startsWith('[Configure')?t(k==='address'?'address':k)+': '+t('not_configured'):BOOT.contact[k])+'</span></div>').join('')+'</div></div></footer>';
}
function authPage(){
 $('#content').innerHTML='<div class="auth-shell"><div class="auth-visual"><img src="/static/images/hero.jpg" alt="'+t('photo_alt')+'"><h2>'+t('auth_intro')+'</h2></div><section class="auth-card">'+(!authLanguageChosen?'<div class="eyebrow">FLORA / '+t('welcome')+'</div><h1>'+t('choose_language')+'</h1><p>'+t('language_intro')+'</p><div class="language-options">'+[['uz','O‘zbekcha'],['en','English'],['ru','Русский']].map(([k,v])=>'<button data-action="auth-language" data-language="'+k+'" class="'+(lang===k?'selected':'')+'"><img class="flag" src="/static/flags/'+k+'.svg" alt="">'+v+'</button>').join('')+'</div>':'<div class="eyebrow">'+t('choose_language')+'</div><h1>'+t(authMode==='register'?'register':authMode==='reset'?'reset':'welcome')+'</h1><div class="tabs">'+['customer','admin'].map(k=>'<button data-action="auth-role" data-role="'+k+'" class="'+(authRole===k?'selected':'')+'">'+icon(k==='admin'?'shield':'user')+t(k)+'</button>').join('')+'</div>'+(authRole==='admin'?'<p class="small">'+t('admin_note')+'</p>':'')+'<form id="auth-form" class="stack">'+formError()+(authMode==='register'?field('name','name','','text','required maxlength="150" autocomplete="name"'):'')+field('email','email','','email','required autocomplete="email"')+(authMode!=='reset'?field('password','password','','password','required minlength="8" autocomplete="'+(authMode==='register'?'new-password':'current-password')+'"'):'')+(authMode==='register'?field('password_confirm','password_confirm','','password','required minlength="8" autocomplete="new-password"'):'')+'<button type="submit">'+t(authMode==='register'?'register':authMode==='reset'?'reset':'login')+icon('arrow-right')+'</button></form><div class="row wrap" style="margin-top:20px">'+(authRole!=='admin'?'<button class="text-button small" data-action="auth-mode" data-mode="'+(authMode==='register'?'login':'register')+'">'+t(authMode==='register'?'login':'register')+'</button>':'')+'<button class="text-button small" data-action="auth-mode" data-mode="'+(authMode==='reset'?'login':'reset')+'">'+t(authMode==='reset'?'login':'forgot')+'</button></div>')+'</section></div>';
}
let productsCache=[];
let checkoutDraft={};
function captureCheckout(){const f=$('#checkout-form');if(f)checkoutDraft=Object.fromEntries(new FormData(f));}
document.addEventListener('input',e=>{if(e.target.closest('#checkout-form'))captureCheckout();});
async function shop(){
 const params=new URLSearchParams(location.search);const cats=(await api('/api/categories/')).results;
 $('#content').innerHTML=heading('shop','finder_intro')+'<div class="toolbar"><input class="search-input" id="catalog-search" value="'+esc(params.get('search')||'')+'" placeholder="'+t('search')+'" aria-label="'+t('search')+'"><button class="secondary" data-action="finder">'+icon('sparkles')+t('finder')+'</button></div><div class="shop-layout"><aside class="filters"><h3>'+t('filters')+'</h3><form id="filter-form">'+select('category','category',[['',t('all')],...cats.map(c=>[c.id,tr(c.name)])],params.get('category'))+select('occasion','occasion',[['',t('all')],...['birthday','romance','thanks','everyday'].map(x=>[x,t(x)])],params.get('occasion'))+select('color','color',[['',t('all')],...['pink','white','red','yellow','mixed'].map(x=>[x,t(x)])],params.get('color'))+field('min_price','min_price',params.get('min_price')||'','number','min="0"')+field('max_price','max_price',params.get('max_price')||'','number','min="0"')+select('sort','sort',['newest','price_asc','price_desc'].map(x=>[x,t(x)]),params.get('sort'))+check('available','available',params.get('available')==='true')+check('favorites','favorites',params.get('favorites')==='true')+'<button>'+t('use_filters')+'</button><button type="button" class="text-button" data-action="reset-filters">'+t('reset_filters')+'</button></form></aside><section><div id="product-results" aria-live="polite"><div class="loading">'+t('loading')+'</div></div></section></div>';
 const data=await api('/api/products/?'+params);productsCache=data.results;
 $('#product-results').innerHTML=data.results.length?'<div class="product-grid">'+data.results.map(card).join('')+'</div>'+pagination(data):empty('no_products');
}
function pagination(data){return data.next||data.previous?'<div class="pagination">'+(data.previous?button('back','paginate','secondary','data-url="'+esc(data.previous)+'"'):'')+(data.next?button('next','paginate','secondary','data-url="'+esc(data.next)+'"'):'')+'</div>':'';}
async function productDetail(id){
 const p=await api('/api/products/'+id+'/');productsCache=[p];const variants=p.variants.filter(v=>v.active);const first=variants.find(v=>v.stock>0)||variants[0];
 $('#content').innerHTML='<div class="toolbar"><a href="'+root()+'shop/">'+icon('arrow-left')+' '+t('shop')+'</a></div><div class="product-detail"><img src="'+esc(p.image_url)+'" alt="'+esc(tr(p.name))+'"><section class="product-info"><div class="eyebrow">'+esc(tr(p.category_name))+'</div><h1>'+esc(tr(p.name))+'</h1><p>'+esc(tr(p.description))+'</p><div class="price" id="detail-price">'+(first?money(first.price):t('unavailable'))+'</div><form id="product-form" class="stack">'+select('variant','size',variants.map(v=>[v.id,tr(v.name)+' · '+money(v.price)+' · '+t('stock')+': '+v.stock]),first?.id)+field('quantity','quantity',1,'number','min="1" max="99" required')+formError()+'<button '+(!first?.stock?'disabled':'')+'>'+icon('bag')+t('add_cart')+'</button></form><div class="row wrap"><button class="text-button" data-action="contact-seller" data-product="'+p.id+'">'+icon('message')+t('contact_seller')+'</button><button class="text-button" data-action="favorite" data-id="'+p.id+'">'+icon('heart')+t('favorites')+'</button></div><details open><summary>'+t('care')+'</summary><p>'+esc(tr(p.care))+'</p></details></section></div>';
}
function orderTable(rows){return rows.length?'<div class="table-wrap"><table><thead><tr><th>'+t('order')+'</th><th>'+t('recipient')+'</th><th>'+t('total')+'</th><th>'+t('status')+'</th><th>'+t('delivery_date')+'</th></tr></thead><tbody>'+rows.map(o=>'<tr><td><a href="'+root()+'orders/'+o.id+'/">#FL-'+String(o.id).padStart(5,'0')+'</a></td><td>'+esc(o.recipient)+'</td><td>'+money(o.total,o.currency)+'</td><td><span class="badge '+o.status+'">'+t(o.status)+'</span></td><td>'+esc(o.delivery_date)+'</td></tr>').join('')+'</tbody></table></div>':empty();}
async function dashboard(){
 const d=await api('/api/dashboard/');applyCounts(d);
 const metrics=user.is_staff?[['order_count',d.orders],['revenue',money(d.revenue),'revenue_note'],['low_stock',d.low_stock],['customers',d.customers]]:[['order_count',d.orders],['active_orders',d.active],['unread',d.unread],['messages',d.unread_messages]];
 $('#content').innerHTML='<div class="page-heading"><div class="eyebrow">'+t(user.is_staff?'admin':'customer')+' / FLORA</div><h1>'+t('greeting')+', '+esc(user.name.split(' ')[0])+'<span style="color:#9caa88">.</span></h1><p>'+t('workspace_intro')+'</p></div><section class="metrics">'+metrics.map(([k,v,n])=>'<div class="metric"><span>'+t(k)+'</span><strong>'+v+'</strong>'+(n?'<small>'+t(n)+'</small>':'')+'</div>').join('')+'</section><div class="toolbar"><a class="button" href="'+root()+(user.is_staff?'products':'shop')+'/">'+icon('flower')+t(user.is_staff?'products':'browse')+'</a><a class="button secondary" href="'+root()+(user.is_staff?'conversations':'messages')+'/">'+icon('message')+t('messages')+'</a>'+(!user.is_staff?button('finder','finder'):'')+'</div><section class="card"><div class="section-head"><h3>'+t('recent_orders')+'</h3><a href="'+root()+'orders/">'+t('orders')+' ↗</a></div>'+orderTable(d.recent)+'</section>';
}
function summary(c,action=''){return '<aside class="card summary-card"><h3>'+t('summary')+'</h3><div class="row"><span>'+t('subtotal')+'</span><strong>'+money(c.subtotal,c.currency)+'</strong></div><div class="row"><span>'+t('delivery_fee')+'</span><strong>'+money(c.delivery_fee,c.currency)+'</strong></div><div class="row summary-total"><span>'+t('total')+'</span><strong>'+money(c.total,c.currency)+'</strong></div><p class="small">'+t('cod')+'</p>'+action+'</aside>';}
async function cartPage(){
 const c=await api('/api/cart/');
 $('#content').innerHTML=heading('cart')+(!c.items.length?empty('empty_cart','<a class="button" href="'+root()+'shop/">'+t('browse')+'</a>'):'<div class="cart-layout"><div>'+c.items.map(i=>'<article class="cart-row"><img src="'+esc(i.image_url)+'" alt="'+esc(tr(i.name))+'"><div><h3><a href="'+root()+'product/'+i.product+'/">'+esc(tr(i.name))+'</a></h3><div class="small muted">'+esc(tr(i.variant_name))+' · '+t('unit_price')+': '+money(i.price)+'</div><div class="small '+(!i.available?'form-error':'muted')+'">'+t(i.available?'stock':'unavailable')+': '+i.stock+'</div><div class="quantity-controls"><button data-action="cart-quantity" data-variant="'+i.variant+'" data-quantity="'+(i.quantity-1)+'" aria-label="'+t('remove')+'" '+(i.quantity<=1?'disabled':'')+'>−</button><input type="number" min="1" max="99" data-cart-variant="'+i.variant+'" value="'+i.quantity+'" aria-label="'+t('quantity')+'"><button data-action="cart-quantity" data-variant="'+i.variant+'" data-quantity="'+(i.quantity+1)+'" aria-label="'+t('quantity')+'">+</button></div></div><div><strong class="price">'+money(i.subtotal)+'</strong><br><button class="text-button small" data-action="cart-remove" data-id="'+i.id+'">'+t('remove')+'</button></div></article>').join('')+'</div>'+summary(c,'<a class="button" href="'+root()+'checkout/">'+t('checkout')+icon('arrow-right')+'</a>')+'</div>');
}
async function checkoutPage(){
 const [c,a]=await Promise.all([api('/api/cart/'),api('/api/addresses/')]);
 if(!c.items.length){$('#content').innerHTML=heading('checkout')+empty('cart_empty');return;}
 const address=a.results.find(x=>x.is_default)||{};
 const tomorrow=new Date();tomorrow.setDate(tomorrow.getDate()+1);const max=new Date();max.setDate(max.getDate()+30);const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
 window.addressCache=a.results;
 $('#content').innerHTML=heading('checkout')+'<div class="cart-layout"><form id="checkout-form" class="card stack">'+formError()+select('saved_address','select_address',[['',t('custom_address')],...a.results.map(x=>[x.id,x.label])],address.id||'')+'<div class="form-grid">'+field('recipient','recipient',address.recipient||user.name,'text','required maxlength="120" autocomplete="name"')+field('phone','phone',address.phone||'','tel','required minlength="7" maxlength="30" autocomplete="tel"')+'<div class="full">'+area('address','address',address.address||'','required minlength="8" maxlength="500" autocomplete="street-address"')+'</div>'+field('delivery_date','delivery_date',iso(tomorrow),'date','required min="'+iso(tomorrow)+'" max="'+iso(max)+'"')+select('slot','slot',BOOT.slots.map(s=>[s,s]))+'<div class="full">'+area('gift_message','gift_message','','maxlength="500"')+'</div><div class="full">'+area('notes','notes','','maxlength="1000"')+'</div></div><div class="card"><strong>'+t('cod')+'</strong><p class="small" style="margin:6px 0 0">'+t('faq_payment_a')+'</p></div><h3>'+t('review')+'</h3><div class="checkout-items">'+c.items.map(x=>'<div class="row"><span>'+esc(tr(x.name))+' · '+esc(tr(x.variant_name))+' × '+x.quantity+'</span><strong>'+money(x.subtotal)+'</strong></div>').join('')+'</div><button type="submit">'+t('place_order')+icon('arrow-right')+'</button></form>'+summary(c)+'</div>';
 const checkoutForm=$('#checkout-form');if(checkoutForm)for(const [k,v] of Object.entries(checkoutDraft)){if(checkoutForm.elements[k])checkoutForm.elements[k].value=v;}
}
async function ordersPage(){
 const d=await api('/api/orders/?'+location.search.slice(1));
 $('#content').innerHTML=heading('orders')+'<form id="order-filter" class="toolbar">'+field('search','search',new URLSearchParams(location.search).get('search')||'')+select('status','status',[['',t('all')],...['pending','confirmed','preparing','out_for_delivery','delivered','cancelled'].map(k=>[k,t(k)])],new URLSearchParams(location.search).get('status'))+'<button>'+t('use_filters')+'</button></form><div class="card">'+orderTable(d.results)+'</div>'+pagination(d);
}
const transitions={pending:['confirmed','cancelled'],confirmed:['preparing','cancelled'],preparing:['out_for_delivery','cancelled'],out_for_delivery:['delivered'],delivered:[],cancelled:[]};
async function orderDetail(id,success=false){
 const o=await api('/api/orders/'+id+'/');
 $('#content').innerHTML=(success?'<div class="confirmation">'+icon('check')+'<h1>'+t('received')+'</h1><p>'+t('order')+' #FL-'+String(o.id).padStart(5,'0')+'</p></div>':heading('order'))+'<div class="cart-layout"><div class="stack"><section class="card"><div class="row wrap"><h3>#FL-'+String(o.id).padStart(5,'0')+'</h3><span class="badge '+o.status+'">'+t(o.status)+'</span></div><p>'+date(o.created)+'</p><div class="table-wrap"><table><thead><tr><th>'+t('products')+'</th><th>'+t('quantity')+'</th><th>'+t('subtotal')+'</th></tr></thead><tbody>'+o.items.map(i=>'<tr><td>'+esc(tr(i.product_name))+'<br><small>'+esc(tr(i.variant_name))+'</small></td><td>'+i.quantity+'</td><td>'+money(i.subtotal,o.currency)+'</td></tr>').join('')+'</tbody></table></div></section><section class="card"><h3>'+t('delivery')+'</h3><p>'+esc(o.recipient)+'<br>'+esc(o.phone)+'<br>'+esc(o.address)+'<br>'+esc(o.delivery_date)+' · '+esc(o.slot)+'</p>'+(o.gift_message?'<p><strong>'+t('gift_message')+':</strong> '+esc(o.gift_message)+'</p>':'')+(o.notes?'<p><strong>'+t('notes')+':</strong> '+esc(o.notes)+'</p>':'')+'<p>'+t('payment_status')+': <strong>'+t(o.payment_status)+'</strong> · '+t('cod')+'</p>'+(user.is_staff?'<div class="toolbar">'+transitions[o.status].map(s=>'<button data-action="order-status" data-id="'+o.id+'" data-status="'+s+'" class="'+(s==='cancelled'?'danger':'secondary')+'">'+t(s)+'</button>').join('')+(o.status==='delivered'&&o.payment_status==='unpaid'?'<button data-action="order-paid" data-id="'+o.id+'">'+t('mark_paid')+'</button>':'')+'</div>':'<button class="secondary" data-action="contact-seller" data-order="'+o.id+'">'+icon('message')+t('contact_seller')+'</button>')+'</section></div>'+summary(o)+'</div>';
}
async function notificationsPage(){
 const d=await api('/api/notifications/?'+location.search.slice(1));
 $('#content').innerHTML=heading('notifications')+'<div class="toolbar">'+button('read_all','read-all')+'</div><div class="card">'+(d.results.length?d.results.map(n=>'<article class="notification '+(!n.read?'unread':'')+'">'+icon('bell')+'<div><small class="muted">'+t('system')+'</small><br><a href="'+root()+'orders/'+n.order+'/"><strong>'+t(n.kind)+' · #FL-'+String(n.order).padStart(5,'0')+'</strong></a><p class="small">'+esc(n.customer)+' · '+money(n.amount,n.currency)+(n.status?' · '+t(n.status):'')+'</p><small class="muted">'+date(n.created)+'</small></div>'+(!n.read?button('mark_read','read','secondary','data-id="'+n.id+'"'):'')+'</article>').join(''):empty())+'</div>'+pagination(d);
}
let conversationData=[];
async function messagesPage(){
 const d=await api('/api/conversations/?'+location.search.slice(1));conversationData=d.results;
 $('#content').innerHTML=heading(user.is_staff?'conversations':'messages','chat_note')+'<div class="toolbar">'+button('new_conversation','new-conversation')+'</div><div class="chat-layout"><div class="conversation-list">'+d.results.map(c=>'<button class="conversation-item '+(currentConversation===c.id?'selected':'')+'" data-action="open-conversation" data-id="'+c.id+'"><strong>'+esc(c.subject)+'</strong><br><small>'+esc(c.customer_name)+' · '+date(c.updated)+'</small>'+(c.unread?'<span class="count">'+c.unread+'</span>':'')+'</button>').join('')+pagination(d)+'</div><section id="chat-panel" class="card">'+empty()+'</section></div>';
 if(currentConversation)await loadConversation(currentConversation);
}
async function loadConversation(id){
 currentConversation=Number(id);const c=conversationData.find(x=>x.id===currentConversation);if(!$('#chat-panel'))return;
 $('#chat-panel').innerHTML='<h3>'+esc(c?.subject||t('messages'))+'</h3><div class="chat-history" id="chat-history"><div class="loading">'+t('loading')+'</div></div><form id="message-form" class="stack" style="margin-top:18px">'+area('body','message','','required maxlength="2000"')+formError()+'<button>'+t('send')+icon('arrow-right')+'</button></form>';
 await refreshMessages();
}
async function refreshMessages(){
 if(!currentConversation||!$('#chat-history'))return;
 const d=await api('/api/conversations/'+currentConversation+'/messages/');const history=$('#chat-history');if(!history)return;
 const atBottom=history.scrollHeight-history.scrollTop-history.clientHeight<80;
 const oldLast=history.dataset.last;
 history.innerHTML=(d.next?'<button class="text-button small" data-action="older-messages" data-url="'+esc(d.next)+'">'+t('back')+'</button>':'')+d.results.slice().reverse().map(m=>messageBubble(m)).join('');
 history.dataset.last=d.results[0]?.id||'';
 if(atBottom||oldLast!==history.dataset.last)history.scrollTop=history.scrollHeight;
}
function messageBubble(m){return '<div class="bubble '+(m.seller===Boolean(user.is_staff)?'mine':'')+'"><small>'+t(m.seller?'seller':'customer')+' · '+date(m.created)+'</small>'+esc(m.body)+'</div>';}
async function profilePage(){
 const [p,a]=await Promise.all([api('/api/profile/'),api('/api/addresses/')]);window.addressCache=a.results;
 $('#content').innerHTML=heading('profile')+'<div class="stack"><section class="card"><form id="profile-form" class="stack">'+formError()+'<div class="row wrap"><div>'+(p.avatar?'<img class="avatar" src="'+esc(p.avatar)+'" alt="'+t('avatar')+'">':icon('user'))+'</div>'+button('remove_avatar','remove-avatar')+'</div><div class="form-grid">'+field('first_name','name',p.first_name,'text','required maxlength="150"')+field('phone','phone',p.phone,'tel','maxlength="30"')+field('avatar','avatar','','file','accept="image/png,image/jpeg,image/webp"')+'<label>'+t('email')+'<input value="'+esc(p.email)+'" disabled></label></div><button>'+t('save')+'</button></form></section><section class="card"><div class="section-head"><h3>'+t('addresses')+'</h3>'+button('new_address','new-address')+'</div><div class="address-grid">'+a.results.map(x=>'<article class="card"><strong>'+esc(x.label)+'</strong> '+(x.is_default?'<span class="badge">'+t('default_address')+'</span>':'')+'<p>'+esc(x.recipient)+'<br>'+esc(x.phone)+'<br>'+esc(x.address)+'</p><div class="toolbar">'+button('edit','edit-address','secondary','data-id="'+x.id+'"')+button('delete','delete-address','danger','data-id="'+x.id+'"')+'</div></article>').join('')+'</div></section><section class="card"><h3>'+t('change_password')+'</h3><form id="password-form" class="stack">'+formError()+'<div class="form-grid">'+field('current_password','current_password','','password','required autocomplete="current-password"')+field('password','password','','password','required minlength="8" autocomplete="new-password"')+'</div><button>'+t('change_password')+'</button></form></section><section class="card"><h3>'+t('change_email')+'</h3><p>'+t('secure_email')+'</p><form id="email-form" class="stack">'+formError()+'<div class="form-grid">'+field('email','email','','email','required')+field('password','current_password','','password','required autocomplete="current-password"')+'</div><button>'+t('change_email')+'</button></form></section><section class="card"><h3>'+t('delete_account')+'</h3><p>'+t('delete_warning')+'</p>'+button('delete_account','delete-account','danger')+'</section></div>';
}
function settingsPage(){
 $('#content').innerHTML=heading('settings','preferences_note')+'<div class="stack"><section class="card"><h3>'+t('theme')+'</h3><div class="toolbar">'+['light','dark'].map(k=>'<button class="'+(document.documentElement.dataset.theme===k?'':'secondary')+'" data-action="set-theme" data-theme="'+k+'">'+icon(k==='light'?'sun':'moon')+t(k)+'</button>').join('')+'</div></section><section class="card"><h3>'+t('language')+'</h3><div class="language-options">'+[['uz','O‘zbekcha'],['en','English'],['ru','Русский']].map(([k,v])=>'<button data-action="set-language" data-language="'+k+'" class="'+(lang===k?'selected':'')+'"><img class="flag" src="/static/flags/'+k+'.svg" alt="">'+v+'</button>').join('')+'</div></section></div>';
}
async function categoriesPage(){
 const d=await api('/api/categories/?'+location.search.slice(1));window.categoryCache=d.results;
 $('#content').innerHTML=heading('categories')+(user.is_staff?'<div class="toolbar">'+button('create','new-category')+'</div>':'')+'<div class="address-grid">'+d.results.map(c=>'<article class="card"><div class="eyebrow">'+(c.active?'FLORA':t('archive'))+'</div><h3>'+esc(tr(c.name))+'</h3><p>'+esc(tr(c.description))+'</p>'+(user.is_staff?'<div class="toolbar">'+button('edit','edit-category','secondary','data-id="'+c.id+'"')+button('archive','archive-category','danger','data-id="'+c.id+'"')+'</div>':'<a class="button secondary" href="'+root()+'shop/?category='+c.id+'">'+t('browse')+icon('arrow-right')+'</a>')+'</article>').join('')+'</div>'+pagination(d);
}
async function adminProducts(){
 const d=await api('/api/products/?'+location.search.slice(1));productsCache=d.results;
 $('#content').innerHTML=heading('products')+'<div class="toolbar">'+button('create','new-product')+'<form id="admin-product-search" class="toolbar" style="margin:0">'+field('search','search',new URLSearchParams(location.search).get('search')||'')+'<button>'+t('search')+'</button></form></div><div class="card table-wrap"><table><thead><tr><th>'+t('products')+'</th><th>'+t('variants')+'</th><th>'+t('status')+'</th><th>'+t('edit')+'</th></tr></thead><tbody>'+d.results.map(p=>'<tr><td><div class="row" style="justify-content:flex-start"><img class="admin-thumb" src="'+esc(p.image_url)+'" alt=""><span>'+esc(tr(p.name))+'</span></div></td><td>'+p.variants.map(v=>esc(tr(v.name))+': '+v.stock+' · '+money(v.price)).join('<br>')+'</td><td>'+t(p.active?'active':'archive')+'</td><td><div class="toolbar" style="margin:0">'+button('edit','edit-product','secondary','data-id="'+p.id+'"')+button('variants','edit-variants','secondary','data-id="'+p.id+'"')+button('archive','archive-product','danger','data-id="'+p.id+'"')+'</div></td></tr>').join('')+'</tbody></table></div>'+pagination(d);
}
async function customersPage(){
 const d=await api('/api/customers/?'+location.search.slice(1));
 $('#content').innerHTML=heading('customers')+'<form id="customer-search" class="toolbar">'+field('search','search',new URLSearchParams(location.search).get('search')||'')+'<button>'+t('search')+'</button></form><div class="card table-wrap"><table><thead><tr><th>'+t('name')+'</th><th>'+t('email')+'</th><th>'+t('phone')+'</th><th>'+t('language')+'</th></tr></thead><tbody>'+d.results.map(c=>'<tr><td>'+esc(c.first_name)+'</td><td>'+esc(c.email)+'</td><td>'+esc(c.phone)+'</td><td>'+esc(c.language)+'</td></tr>').join('')+'</tbody></table></div>'+pagination(d);
}
async function guideAdmin(){
 const config=await api('/api/guide/');
 $('#content').innerHTML=heading('guide_admin')+'<section class="card"><p>'+t('guide_config_note')+'</p><form id="guide-config-form" class="stack">'+formError()+area('data','guide_config',JSON.stringify(config,null,2),'class="json-editor" required')+'<button>'+t('save')+'</button></form></section>';
}
let rendering=0;
async function render(preserve=false){
 const token=++rendering;const snapshots=preserve?$$('form').map(f=>({id:f.id,values:$$('input:not([type=file]),textarea,select',f).map(x=>({name:x.name,value:x.value,checked:x.checked}))})):[];
 shell();syncDrawer();
 try{
  if(path==='/')await landing();
  else if(path==='/auth/')authPage();
  else if(!user){navigate('/auth/');return;}
  else{
   const parts=path.split('/').filter(Boolean),section=parts[1],id=parts[2];
   if(['dashboard','overview'].includes(section))await dashboard();
   else if(section==='shop')await shop();
   else if(section==='product'&&id)await productDetail(id);
   else if(section==='cart')await cartPage();
   else if(section==='checkout')await checkoutPage();
   else if(section==='orders'&&id)await orderDetail(id,new URLSearchParams(location.search).has('success'));
   else if(section==='orders')await ordersPage();
   else if(section==='notifications')await notificationsPage();
   else if(['messages','conversations'].includes(section))await messagesPage();
   else if(section==='profile')await profilePage();
   else if(section==='settings')settingsPage();
   else if(section==='categories')await categoriesPage();
   else if(section==='products'&&user.is_staff)await adminProducts();
   else if(section==='customers'&&user.is_staff)await customersPage();
   else if(section==='guide'&&user.is_staff)await guideAdmin();
   else $('#content').innerHTML=empty();
  }
  if(token===rendering&&preserve)for(const f of snapshots){const el=document.getElementById(f.id);if(el)for(const v of f.values){const x=[...el.elements].find(x=>x.name===v.name);if(x){x.value=v.value;x.checked=v.checked;}}}
 }catch(e){if(token!==rendering||e.stale)return;$('#content').innerHTML='<div class="empty"><h3>'+t('error')+'</h3><p>'+esc(e.message)+'</p>'+button('retry','retry')+'</div>';}
}
function navigate(url){
 const u=new URL(url,location.origin);
 if(u.origin!==location.origin)return;
 if(!user&&u.pathname.startsWith('/workspace')){u.pathname='/auth/';u.search='';}
 history.pushState({},'',u.pathname+u.search+u.hash);path=u.pathname;closeModal();render();window.scrollTo(0,0);
 if(u.hash)setTimeout(()=>document.getElementById(u.hash.slice(1))?.scrollIntoView(),300);
}
function showModal(title,body,wide=false){
 modalReturn=document.activeElement;
 $('#overlay').innerHTML='<div class="modal-backdrop"><section role="dialog" aria-modal="true" aria-labelledby="modal-title" class="modal '+(wide?'wide':'')+'"><div class="modal-head"><h2 id="modal-title">'+t(title)+'</h2><button class="icon-button" data-action="close" aria-label="'+t('close')+'">'+icon('x')+'</button></div>'+body+'</section></div>';
 document.body.style.overflow='hidden';$('.modal button,.modal input')?.focus();
}
function closeModal(){ $('#overlay').innerHTML='';document.body.style.overflow='';modalReturn?.focus?.();}
let languageQueue=Promise.resolve();
function setLanguage(value){captureCheckout();languageQueue=languageQueue.catch(()=>{}).then(()=>applyLanguage(value));return languageQueue;}
async function applyLanguage(value){
 if(user){const p=await api('/api/profile/','PATCH',{language:value});user.language=p.language;}
 lang=value;localStorage.setItem('flora-language',value);document.cookie='django_language='+value+';path=/;SameSite=Lax';document.documentElement.lang=value;await render(true);
}
async function setTheme(value){
 if(user)await api('/api/profile/','PATCH',{theme:value});
 localStorage.setItem('flora-theme',value);document.documentElement.dataset.theme=value;if(user)user.theme=value;
 if(path.endsWith('/settings/'))settingsPage();
 const toggle=$('[data-action="theme"]');if(toggle){toggle.innerHTML=icon(value==='dark'?'sun':'moon');toggle.setAttribute('aria-label',t(value==='dark'?'light':'dark'));}
}
let guideConfig=null,guideAnswers=[],guideResponse='';
async function openGuide(){guideConfig=await api('/api/guide/');guideAnswers=[];guideResponse='';await drawGuide();}
async function drawGuide(){
 const step=guideConfig.steps[guideAnswers.length];
 const intro='<div class="eyebrow">'+t('rule_based')+'</div><p>'+t('finder_intro')+'</p><div class="guide-progress"><span style="width:'+(guideAnswers.length/Math.max(1,guideConfig.steps.length)*100)+'%"></span></div>'+(guideResponse?'<div class="guide-response"><small>'+t('prepared')+'</small><br>'+esc(tr(guideResponse))+'</div>':'');
 let body;
 if(step)body='<h3>'+esc(tr(step.question))+'</h3><div class="guide-choices">'+step.choices.map((c,i)=>'<button data-action="guide-answer" data-index="'+i+'">'+esc(tr(c.label))+icon('arrow-right')+'</button>').join('')+'</div>';
 else{
  const params=new URLSearchParams({available:'true'});guideAnswers.forEach((a,i)=>{if(a.value)params.set(guideConfig.steps[i].field,a.value);});
  const d=await api('/api/products/?'+params);
  body='<h3>'+t('matches')+'</h3>'+(d.results.length?'<div class="product-grid">'+d.results.slice(0,6).map(card).join('')+'</div>':empty('no_products',button('broaden','guide-broaden')));
 }
 body+='<div class="toolbar" style="margin-top:25px">'+(guideAnswers.length?button('back','guide-back'):'')+button('restart','finder')+button('contact_seller','contact-seller')+'</div><div>'+guideConfig.faq.map((f,i)=>'<details><summary>'+esc(tr(f.question))+'</summary><p>'+esc(tr(f.answer))+'</p></details>').join('')+'</div>';
 showModal('finder',intro+body,true);
}
function translationFields(name,label,obj={}){return ['en','uz','ru'].map(l=>'<label>'+t(label)+' · '+l.toUpperCase()+'<textarea name="'+name+'_'+l+'" required maxlength="5000">'+esc(obj[l]||'')+'</textarea></label>').join('');}
function collectTranslations(form,key){return Object.fromEntries(['en','uz','ru'].map(l=>[l,form.elements[key+'_'+l].value]));}
async function editCatalog(kind,id){
 let obj={};if(id)obj=kind==='product'?await api('/api/products/'+id+'/'):await api('/api/categories/'+id+'/');
 let body='<form id="catalog-form" data-kind="'+kind+'" data-id="'+(id||'')+'" class="stack">'+formError()+'<div class="form-grid">'+translationFields('name',kind==='product'?'product_name':'name',obj.name)+translationFields('description','description',obj.description);
 if(kind==='product'){
  const cats=(await api('/api/categories/')).results;
  body+=translationFields('care','care',obj.care)+select('category','category',cats.map(c=>[c.id,tr(c.name)]),obj.category)+select('color','color',['pink','white','red','yellow','mixed'].map(k=>[k,t(k)]),obj.color)+select('occasion','occasion',['birthday','romance','thanks','everyday'].map(k=>[k,t(k)]),obj.occasion)+select('flower_type','flower_type',['roses','tulips','seasonal_type'].map(k=>[k,t(k)]),obj.flower_type)+field('image','image','','file','accept="image/png,image/jpeg,image/webp"');
 }
 body+='</div>'+check('active','active',obj.active!==false)+'<button>'+t('save')+'</button></form>';
 showModal(kind==='product'?'products':'categories',body,true);
}
async function editVariants(id){
 const p=await api('/api/products/'+id+'/');
 showModal('variants','<h3>'+esc(tr(p.name))+'</h3><div class="stack">'+p.variants.map(v=>'<div class="card row wrap"><span>'+esc(tr(v.name))+' · '+money(v.price)+' · '+t('stock')+': '+v.stock+' · '+t(v.active?'active':'archive')+'</span>'+button('edit','variant-form','secondary','data-product="'+p.id+'" data-id="'+v.id+'"')+'</div>').join('')+'</div><div class="toolbar" style="margin-top:20px">'+button('create','variant-form','secondary','data-product="'+p.id+'"')+'</div>',true);productsCache=[p];
}
function variantForm(product,id){
 const p=productsCache.find(p=>p.id===Number(product)),v=p?.variants.find(v=>v.id===Number(id))||{};
 showModal('variant','<form id="variant-edit-form" data-product="'+product+'" data-id="'+(id||'')+'" class="stack">'+formError()+translationFields('name','name',v.name)+'<div class="form-grid">'+field('price','price',v.price||'','number','required min="0" step="0.01"')+field('stock','stock',v.stock??0,'number','required min="0" max="1000000"')+'</div>'+check('active','active',v.active!==false)+'<button>'+t('save')+'</button></form>');
}
function addressForm(id){
 const a=window.addressCache?.find(a=>a.id===Number(id))||{};
 showModal('addresses','<form id="address-form" data-id="'+(id||'')+'" class="stack">'+formError()+field('label','label',a.label||'','text','required maxlength="60"')+field('recipient','recipient',a.recipient||user.name,'text','required maxlength="120"')+field('phone','phone',a.phone||'','tel','required minlength="7" maxlength="30"')+area('address','address',a.address||'','required maxlength="500"')+check('is_default','default_address',a.is_default)+'<button>'+t('save')+'</button></form>');
}
function confirmModal(title,action,extra='',text='confirmation_required'){
 showModal(title,'<p>'+t(text)+'</p><div class="toolbar">'+button('confirm',action,'danger',extra)+button('cancel','close')+'</div>');
}
document.addEventListener('click',async e=>{
 const target=e.target.closest('[data-action],a');if(!target)return;
 if(target.matches('a')&&!target.dataset.action){const href=target.getAttribute('href');if(!href||!href.startsWith('/')||e.ctrlKey||e.metaKey||e.shiftKey)return;e.preventDefault();if(target.dataset.auth){authMode=target.dataset.auth;authLanguageChosen=false;}navigate(href);return;}
 const a=target.dataset.action;if(!a)return;e.preventDefault();
 try{
  if(a==='menu'){setDrawer(!$('#sidebar').classList.contains('open'));}
  else if(a==='close')closeModal();
  else if(a==='retry')await render();
  else if(a==='theme')await setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');
  else if(a==='set-theme')await setTheme(target.dataset.theme);
  else if(a==='set-language')await setLanguage(target.dataset.language);
  else if(a==='logout'){await api('/auth/logout/','POST',{});location.href='/';}
  else if(a==='auth-language'){lang=target.dataset.language;localStorage.setItem('flora-language',lang);document.documentElement.lang=lang;authLanguageChosen=true;shell();authPage();}
  else if(a==='auth-role'){authRole=target.dataset.role;if(authRole==='admin')authMode='login';authPage();}
  else if(a==='auth-mode'){authMode=target.dataset.mode;authPage();}
  else if(a==='finder')await openGuide();
  else if(a==='guide-answer'){const choice=guideConfig.steps[guideAnswers.length].choices[Number(target.dataset.index)];guideAnswers.push(choice);guideResponse=choice.response;await drawGuide();}
  else if(a==='guide-back'){guideAnswers.pop();guideResponse='';await drawGuide();}
  else if(a==='guide-broaden'){closeModal();navigate(root()+'shop/?available=true');}
  else if(a==='quick-add'){if(!user){navigate('/auth/');return;}target.disabled=true;await api('/api/cart/','POST',{variant:Number(target.dataset.variant),quantity:1});toast(t('added'));}
  else if(a==='favorite'){if(!user){navigate('/auth/');return;}const d=await api('/api/products/'+target.dataset.id+'/favorite/','POST',{});target.style.background=d.saved?'#e8cfcc':'';target.setAttribute('aria-pressed',d.saved);toast(t('saved'));}
  else if(a==='reset-filters')navigate(root()+'shop/');
  else if(a==='paginate'){const u=new URL(target.dataset.url,location.origin);navigate(path+u.search);}
  else if(a==='cart-quantity'){await api('/api/cart/','PATCH',{variant:Number(target.dataset.variant),quantity:Number(target.dataset.quantity)});await cartPage();}
  else if(a==='cart-remove'){await api('/api/cart/','DELETE',{id:Number(target.dataset.id)});await cartPage();}
  else if(a==='order-status'){if(target.dataset.status==='cancelled'){confirmModal('cancel','confirm-status','data-id="'+target.dataset.id+'" data-status="cancelled"');}else{await api('/api/orders/'+target.dataset.id+'/transition/','POST',{status:target.dataset.status});await orderDetail(target.dataset.id);}}
  else if(a==='confirm-status'){await api('/api/orders/'+target.dataset.id+'/transition/','POST',{status:target.dataset.status});closeModal();await orderDetail(target.dataset.id);}
  else if(a==='order-paid'){await api('/api/orders/'+target.dataset.id+'/payment/','POST',{payment_status:'paid'});await orderDetail(target.dataset.id);}
  else if(a==='read-all'){await api('/api/notifications/read_all/','POST',{});await notificationsPage();await poll();}
  else if(a==='read'){await api('/api/notifications/'+target.dataset.id+'/mark_read/','POST',{});await notificationsPage();await poll();}
  else if(a==='new-conversation'||a==='contact-seller'){
   if(!user){navigate('/auth/');return;}
   showModal('new_conversation','<form id="conversation-form" data-product="'+(target.dataset.product||'')+'" data-order="'+(target.dataset.order||'')+'" class="stack">'+formError()+field('subject','subject',target.dataset.order?t('order')+' #'+target.dataset.order:'','text','required maxlength="150"')+area('body','message','','required maxlength="2000"')+'<button>'+t('send')+'</button></form>');
  }
  else if(a==='open-conversation')await loadConversation(target.dataset.id);
  else if(a==='older-messages'){const d=await api(target.dataset.url);target.outerHTML=(d.next?button('back','older-messages','text-button','data-url="'+esc(d.next)+'"'):'')+d.results.slice().reverse().map(messageBubble).join('');}
  else if(a==='new-address')addressForm();
  else if(a==='edit-address')addressForm(target.dataset.id);
  else if(a==='delete-address')confirmModal('delete','confirm-address-delete','data-id="'+target.dataset.id+'"');
  else if(a==='confirm-address-delete'){await api('/api/addresses/'+target.dataset.id+'/','DELETE');closeModal();await profilePage();}
  else if(a==='remove-avatar'){await api('/api/profile/','PATCH',{avatar:null});await profilePage();}
  else if(a==='delete-account')showModal('delete_account','<p>'+t('delete_warning')+'</p><form id="delete-account-form" class="stack">'+formError()+field('password','current_password','','password','required')+'<button class="danger">'+t('delete_account')+'</button></form>');
  else if(a==='new-product')await editCatalog('product');
  else if(a==='edit-product')await editCatalog('product',target.dataset.id);
  else if(a==='new-category')await editCatalog('category');
  else if(a==='edit-category')await editCatalog('category',target.dataset.id);
  else if(a==='archive-product'||a==='archive-category')confirmModal('archive','confirm-archive','data-kind="'+(a==='archive-product'?'products':'categories')+'" data-id="'+target.dataset.id+'"','archive_confirm');
  else if(a==='confirm-archive'){await api('/api/'+target.dataset.kind+'/'+target.dataset.id+'/','DELETE');closeModal();await render();}
  else if(a==='edit-variants')await editVariants(target.dataset.id);
  else if(a==='variant-form')variantForm(target.dataset.product,target.dataset.id);
 }catch(error){if(!error.stale)toast(error.message);}finally{if(a==='quick-add')target.disabled=false;}
});
document.addEventListener('change',async e=>{
 const el=e.target;try{
  if(el.id==='global-language')await setLanguage(el.value);
  if(el.dataset.cartVariant){await api('/api/cart/','PATCH',{variant:Number(el.dataset.cartVariant),quantity:Number(el.value)});await cartPage();}
  if(el.name==='variant'&&el.closest('#product-form')){const v=productsCache[0].variants.find(v=>v.id===Number(el.value));$('#detail-price').textContent=money(v.price);$('#product-form button[type=submit],#product-form button:not([type])').disabled=v.stock<1;}
  if(el.closest('#checkout-form'))captureCheckout();
  if(el.name==='saved_address'){const a=window.addressCache.find(x=>x.id===Number(el.value));if(a){const f=$('#checkout-form');['recipient','phone','address'].forEach(k=>f.elements[k].value=a[k]);captureCheckout();}}
 }catch(error){toast(error.message);}
});
document.addEventListener('keydown',e=>{
 if(e.key==='Escape'){closeModal();setDrawer(false);}
 const modal=$('.modal')||$('.sidebar.open');
 if(modal&&e.key==='Tab'){const els=$$('button,a,input,select,textarea,[tabindex="0"]',modal).filter(x=>!x.disabled);const first=els[0],last=els.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
 if(e.key==='Enter'&&e.target.id==='catalog-search'){e.preventDefault();$('#filter-form').requestSubmit();}
});
document.addEventListener('submit',async e=>{
 e.preventDefault();const f=e.target;if(!f.id)return;
 const submit=$('button[type=submit],button:not([type])',f);if(submit)submit.disabled=true;
 const err=$('.form-error',f);if(err)err.textContent='';
 const d=Object.fromEntries(new FormData(f));try{
  if(f.id==='auth-form'){const result=await api('/auth/'+authMode+'/','POST',{...d,role:authRole,language:lang});if(authMode==='reset')toast(t('reset_sent'));else location.href=result.redirect;}
  else if(f.id==='filter-form'){const p=new URLSearchParams();Object.entries(d).forEach(([k,v])=>{if(v)p.set(k,['available','favorites'].includes(k)?'true':v);});if($('#catalog-search').value)p.set('search',$('#catalog-search').value);navigate(root()+'shop/?'+p);}
  else if(['order-filter','admin-product-search','customer-search'].includes(f.id)){const p=new URLSearchParams(d);navigate(path+'?'+p);}
  else if(f.id==='product-form'){await api('/api/cart/','POST',{variant:Number(d.variant),quantity:Number(d.quantity)});toast(t('added'));}
  else if(f.id==='checkout-form'){
   let key=sessionStorage.getItem('flora-checkout-key');if(!key){key=crypto.randomUUID();sessionStorage.setItem('flora-checkout-key',key);}
   const o=await api('/api/checkout/','POST',{...d,key});sessionStorage.removeItem('flora-checkout-key');checkoutDraft={};navigate(root()+'orders/'+o.id+'/?success=1');
  }
  else if(f.id==='message-form'){await api('/api/conversations/'+currentConversation+'/messages/','POST',d);f.reset();await refreshMessages();}
  else if(f.id==='conversation-form'){let c;if(f.dataset.created)c={id:Number(f.dataset.created)};else {c=await api('/api/conversations/','POST',{subject:d.subject,...(f.dataset.product?{product:Number(f.dataset.product)}:{}),...(f.dataset.order?{order:Number(f.dataset.order)}:{})});f.dataset.created=c.id;}await api('/api/conversations/'+c.id+'/messages/','POST',{body:d.body});currentConversation=c.id;closeModal();navigate(root()+(user.is_staff?'conversations':'messages')+'/');}
  else if(f.id==='profile-form'){const fd=new FormData(f);if(!fd.get('avatar').size)fd.delete('avatar');const p=await api('/api/profile/','PATCH',fd);user.name=p.first_name;toast(t('saved'));await render();}
  else if(f.id==='password-form'){await api('/api/password/','POST',d);f.reset();toast(t('saved'));}
  else if(f.id==='email-form'){await api('/api/email/','POST',d);toast(t('email_verification'));f.reset();}
  else if(f.id==='delete-account-form'){await api('/api/profile/','DELETE',{...d,confirm:true});location.href='/';}
  else if(f.id==='address-form'){await api('/api/addresses/'+(f.dataset.id?f.dataset.id+'/':''),f.dataset.id?'PATCH':'POST',{...d,is_default:f.elements.is_default.checked});closeModal();await profilePage();toast(t('saved'));}
  else if(f.id==='catalog-form'){
   const kind=f.dataset.kind,fd=new FormData();fd.set('name',JSON.stringify(collectTranslations(f,'name')));fd.set('description',JSON.stringify(collectTranslations(f,'description')));fd.set('active',f.elements.active.checked);
   if(kind==='product'){fd.set('care',JSON.stringify(collectTranslations(f,'care')));['category','color','occasion','flower_type'].forEach(k=>fd.set(k,d[k]));if(f.elements.image.files[0])fd.set('image',f.elements.image.files[0]);}
   const result=await api('/api/'+(kind==='product'?'products':'categories')+'/'+(f.dataset.id?f.dataset.id+'/':''),f.dataset.id?'PATCH':'POST',fd);closeModal();await render();if(kind==='product'&&!f.dataset.id){productsCache=[{...result,variants:[]}];variantForm(result.id);}else toast(t('saved'));
  }
  else if(f.id==='variant-edit-form'){await api('/api/variants/'+(f.dataset.id?f.dataset.id+'/':''),f.dataset.id?'PATCH':'POST',{product:Number(f.dataset.product),name:collectTranslations(f,'name'),price:d.price,stock:Number(d.stock),active:f.elements.active.checked});closeModal();await render();toast(t('saved'));}
  else if(f.id==='guide-config-form'){let data;try{data=JSON.parse(d.data);}catch(e){throw Error(t('guide_invalid'));}await api('/api/guide/','PUT',{data});toast(t('saved'));}
 }catch(error){if(err)err.textContent=error.message;else toast(error.message);}finally{if(submit)submit.disabled=false;}
});
function applyCounts(d){$$('[data-count]').forEach(el=>{const count=el.dataset.count==='notifications'?d.unread:d.unread_messages;el.textContent=count||'';});}
async function poll(){if(!user||document.hidden||pollBusy)return;pollBusy=true;try{const d=await api('/api/dashboard/');applyCounts(d);if($('#chat-history'))await refreshMessages();if(path.endsWith('/notifications/'))await notificationsPage();}catch(e){if(!e.stale&&$('#chat-history'))toast(t('network_error'));}finally{pollBusy=false;}}
window.addEventListener('popstate',()=>{path=location.pathname;render();});
document.addEventListener('click',e=>{const side=$('#sidebar');if(side?.classList.contains('open')&&!side.contains(e.target)&&!e.target.closest('[data-action=menu]'))setDrawer(false);});
function syncDrawer(){const side=$('#sidebar');if(side){side.inert=matchMedia('(max-width:900px)').matches&&!side.classList.contains('open');side.setAttribute('aria-hidden',String(side.inert));}}
function setDrawer(open){const side=$('#sidebar');if(!side)return;side.classList.toggle('open',open);syncDrawer();$('[data-action="menu"]')?.setAttribute('aria-expanded',String(open));if(open)$('a',side).focus();else $('[data-action="menu"]')?.focus();}
matchMedia('(max-width:900px)').addEventListener('change',syncDrawer);
localStorage.setItem('flora-language',lang);render();setInterval(poll,12000);setTimeout(poll,1500);
