(function(){
var L={en:"members",fr:"membres",ar:"عضو",ary:"عضو",es:"miembros",pt:"membros",de:"Mitglieder",tr:"üye"};
var st=document.createElement("style");
st.textContent=".mem{display:none;align-items:center;gap:4px;font-size:11px;font-weight:700;color:#d4a017;border:1px solid rgba(212,160,23,.45);border-radius:999px;padding:3px 8px;white-space:nowrap;margin-inline-start:6px}.mem.on{display:inline-flex}.mem+#join{margin-inline-start:auto}";
document.head.appendChild(st);
var N=null;
function txt(){var lg=localStorage.getItem("lang")||"en";return "\u{1F465} "+Number(N).toLocaleString("en-US")+" "+(L[lg]||L.en)}
function place(){if(N===null)return;document.querySelectorAll("#hd .r1 .brand,#gtop .brand").forEach(function(b){var n=b.nextElementSibling;if(n&&n.classList.contains("mem")){n.textContent=txt();return}var el=document.createElement("span");el.className="mem on";el.setAttribute("aria-live","polite");el.textContent=txt();b.insertAdjacentElement("afterend",el)})}
function show(n){N=n;place();setTimeout(place,1000);setTimeout(place,3000)}
// public aggregate view: public.member_stats(members). Per-country counters can later be added as a sibling view without changing this file's contract.
fetch("https://eyasbfywyatrkpkljxek.supabase.co/rest/v1/member_stats?select=members",{headers:{apikey:"sb_publishable_1hlN6DuTPcl-rCJufPHBZw_gAr502Jq"}}).then(function(r){return r.ok?r.json():[]}).then(function(j){if(j&&j[0]&&typeof j[0].members==="number")show(j[0].members)}).catch(function(){});
})();
