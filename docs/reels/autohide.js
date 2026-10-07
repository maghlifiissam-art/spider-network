(function(){
var st=document.createElement("style");
st.textContent="#tb{transition:transform .28s ease}html.tbh #tb{transform:translateY(calc(100% + 4px))}@media(prefers-reduced-motion:reduce){#tb{transition:none}}";
document.head.appendChild(st);
var st2=document.createElement("style");st2.textContent="\n@media(max-width:999px){\nhtml .card.v .tag{display:none!important}\nhtml .card.v{padding-bottom:78px!important;transition:padding-bottom .28s ease}\nhtml.tbh .card.v{padding-bottom:22px!important}\nhtml .card.v .rail{transition:bottom .28s ease}html.tbh .card.v .rail{bottom:50px!important}\nhtml .card.v>h2{font-size:17px!important;line-height:1.25!important;margin:2px 0!important;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}\nhtml .card.v>p{font-size:12.5px!important;line-height:1.4!important;margin:0!important;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden;opacity:.85}\nhtml .card.v>p.ex{-webkit-line-clamp:6}\nhtml .card.v>.creator-row{margin:0 0 2px!important;transform:scale(.9);transform-origin:left bottom}\n}";document.head.appendChild(st2);
var root=document.documentElement;
function watch(get,el){var last=get(),acc=0;el.addEventListener("scroll",function(){var y=get(),d=y-last;last=y;if(y<40){root.classList.remove("tbh");acc=0;return}
if((d>0)!==(acc>0))acc=0;acc+=d;if(acc>24)root.classList.add("tbh");else if(acc<-12)root.classList.remove("tbh")},{passive:true})}
var f=document.getElementById("feed");
if(f)watch(function(){return f.scrollTop},f);
watch(function(){return window.pageYOffset},window);
})();
