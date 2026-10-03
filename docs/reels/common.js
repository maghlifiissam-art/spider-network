const SB=supabase.createClient("https://eyasbfywyatrkpkljxek.supabase.co","sb_publishable_1hlN6DuTPcl-rCJufPHBZw_gAr502Jq");
const BASE=location.origin+location.pathname.replace(/[^/]*$/,"");
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
