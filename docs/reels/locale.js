/* Country selects UI language only. Content and legal copy are never translated here. */
(function(){
'use strict';
const supported=['en','fr','ar','es','pt','de','tr'];
const groups={ar:'MA DZ TN LY EG SD MR SO DJ KM SA YE OM AE QA BH KW IQ JO LB SY PS',fr:'FR MC',es:'ES MX GT HN SV NI CR PA CU DO PR CO VE EC PE BO CL AR PY UY',pt:'BR PT'};
const normal=value=>{const base=String(value||'').toLowerCase().split('-')[0];return base==='ary'?'ar':supported.includes(base)?base:null};
const read=key=>{try{return localStorage.getItem(key)}catch(e){return null}};
const write=(key,value)=>{try{if(value===null)localStorage.removeItem(key);else localStorage.setItem(key,value)}catch(e){}};
const manualKey='rimaz.language.manual';
let manual=normal(read(manualKey));
if(read('rimaz.language.v1')!=='1'){manual=manual||normal(read('lang'));if(manual)write(manualKey,manual);write('rimaz.language.v1','1')}
const fromCountry=country=>{const code=String(country||'').toUpperCase();for(const [lang,codes] of Object.entries(groups)){if(codes.split(' ').includes(code))return lang}return 'en'};
const apply=lang=>{write('lang',lang);document.documentElement.lang=lang;document.documentElement.dir=lang==='ar'?'rtl':'ltr';return lang};
apply(manual||'en');
const guard=document.createElement('style');guard.textContent='html[data-rimaz-locale-pending] body{visibility:hidden}';document.head.append(guard);document.documentElement.dataset.rimazLocalePending='';
const country=async()=>{const control=new AbortController();let timer;try{return await Promise.race([fetch('https://rimaz-country.magpro369.workers.dev/',{signal:control.signal,credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer'}).then(async response=>{if(!response.ok)throw new Error('country unavailable');const data=await response.json();return /^[A-Z]{2}$/.test(data.country||'')?data.country:null}),new Promise(resolve=>{timer=setTimeout(()=>{control.abort();resolve(null)},1200)})])}catch(e){return null}finally{clearTimeout(timer)}};
const ready=manual?Promise.resolve(apply(manual)):country().then(code=>apply(fromCountry(code)));
window.RimazLocale={ready,normal,fromCountry,getManual:()=>normal(read(manualKey)),setManual:value=>{const choice=normal(value);write(manualKey,choice);write('rimaz.language.v1','1');if(choice)apply(choice);location.reload()},automaticLabel:()=>({en:'Automatic (country)',fr:'Automatique (pays)',ar:'تلقائي (حسب البلد)',es:'Automático (país)',pt:'Automático (país)',de:'Automatisch (Land)',tr:'Otomatik (ülke)'})[document.documentElement.lang]||'Automatic (country)'};
const run=async()=>{await ready;try{for(const original of document.querySelectorAll('script[type="text/rimaz-locale"]')){const script=document.createElement('script');for(const attr of original.attributes){if(!['type','defer','async'].includes(attr.name))script.setAttribute(attr.name,attr.value)}if(original.src){await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('startup timed out')),8000);script.onload=()=>{clearTimeout(timer);resolve()};script.onerror=()=>{clearTimeout(timer);if(original.getAttribute('onerror')){try{Function(original.getAttribute('onerror'))()}catch(e){}}reject(new Error('startup unavailable'))};original.replaceWith(script)})}else{script.textContent=original.textContent;original.replaceWith(script)}}if(typeof applyLang==='function')applyLang()}catch(e){const notice=document.createElement('p');notice.textContent=({en:'Could not load the page. Please reload.',fr:'Impossible de charger la page. Veuillez recharger.',ar:'تعذر تحميل الصفحة. يرجى إعادة تحميلها.'})[document.documentElement.lang]||'Could not load the page. Please reload.';notice.setAttribute('role','alert');document.body.prepend(notice)}finally{delete document.documentElement.dataset.rimazLocalePending;guard.remove()}};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
})();
