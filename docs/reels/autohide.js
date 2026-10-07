(function(){
var st=document.createElement("style");
st.textContent="#tb{transition:transform .28s ease}html.tbh #tb{transform:translateY(calc(100% + 4px))}@media(prefers-reduced-motion:reduce){#tb{transition:none}}";
document.head.appendChild(st);
var root=document.documentElement;
function watch(get,el){var last=get(),acc=0;el.addEventListener("scroll",function(){var y=get(),d=y-last;last=y;if(y<40){root.classList.remove("tbh");acc=0;return}
if((d>0)!==(acc>0))acc=0;acc+=d;if(acc>24)root.classList.add("tbh");else if(acc<-12)root.classList.remove("tbh")},{passive:true})}
var f=document.getElementById("feed");
if(f)watch(function(){return f.scrollTop},f);
watch(function(){return window.pageYOffset},window);
})();
