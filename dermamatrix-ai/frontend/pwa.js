/* Progressive installation, without notification permission or health caching. */
(() => {
  let prompt=null;
  window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();prompt=event;const button=document.getElementById('installWorkspace');if(button)button.hidden=false;});
  window.addEventListener('appinstalled',()=>{prompt=null;const button=document.getElementById('installWorkspace');if(button)button.hidden=true;});
  window.addEventListener('load',async()=>{
    const button=document.getElementById('installWorkspace');
    if(button)button.onclick=async()=>{if(!prompt)return;const current=prompt;prompt=null;button.hidden=true;await current.prompt();};
    if('serviceWorker' in navigator&&window.isSecureContext){try{await navigator.serviceWorker.register('/sw.js',{scope:'/'});}catch{/* Installation is optional; the live app remains available. */}}
  });
})();
