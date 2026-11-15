(() => {
 'use strict';
 const panel = document.querySelector('.push-panel-content');
 if (!panel) return;
 const status = document.getElementById('push-status');
 const summary = document.getElementById('push-summary-state');
 const enable = document.getElementById('push-enable');
 const disable = document.getElementById('push-disable');
 const test = document.getElementById('push-test');
 const csrf = panel.dataset.csrf;
 const preferencesForm=document.getElementById('push-preferences-form');
 const preferencesStatus=document.getElementById('push-preferences-status');
 const expenseEnabled=document.getElementById('push-expense-enabled');
 const incomeEnabled=document.getElementById('push-income-enabled');
 const minAmount=document.getElementById('push-min-amount');
 const detailLevel=document.getElementById('push-detail-level');
 const savePreferences=document.getElementById('push-save-preferences');
 const exampleBody=document.getElementById('push-example-body');
 const example = () => {
    const level=detailLevel.value;
    let body='Neue Ausgabe erfasst.';
    if (level==='amount') body='Ausgabe: 149,90 €';
    if (level==='full') body='Ausgabe: 149,90 €\nEmpfänger: Edeka\nKonto: Comdirect\nNotiz: Wocheneinkauf';
    exampleBody.textContent=body;
 };
 detailLevel.addEventListener('change',example);
 const supported = ('serviceWorker' in navigator && 'PushManager' in window &&
                    'Notification' in window && window.isSecureContext);
 let registration, subscription, publicKey;
 const setStatus = (msg,active=false) => {
    status.textContent = msg;
    summary.textContent = active ? 'Aktiv' : 'Nicht aktiv';
    summary.classList.toggle('status-on',active);
    summary.classList.toggle('status-off',!active);
    enable.hidden=active; disable.hidden=!active; test.hidden=!active;
 };
 const asUint8 = b64 => {
   const s=atob(b64.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-b64.length%4)%4));
   return Uint8Array.from(s, c=>c.charCodeAt(0));
 };
 async function call(path,payload) {
    const res=await fetch(path,{method:'POST',credentials:'same-origin',
       cache:'no-store',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},
       body:JSON.stringify(payload)});
    const obj=await res.json().catch(()=>({}));
    if (!res.ok) throw new Error(obj.error || 'Serverfehler '+res.status);
    return obj;
 }
 async function refresh() {
   if (!supported) {setStatus('Dieser Browser unterstützt Web Push nicht.'); enable.hidden=true;return;}
   registration=await navigator.serviceWorker.register('/sw.js',{scope:'/'});
   const info=await (await fetch('/api/push/config',{cache:'no-store'})).json();
   if (!info.publicKey) throw new Error('Push-Schlüssel ist nicht verfügbar.');
   publicKey=info.publicKey;
   const pref=info.preferences;
   expenseEnabled.checked=Boolean(pref.expense_enabled);
   incomeEnabled.checked=Boolean(pref.income_enabled);
   minAmount.value=(Number(pref.min_amount_cents)/100).toFixed(2).replace('.',',');
   detailLevel.value=pref.detail_level || 'private';
   example();
   subscription=await registration.pushManager.getSubscription();
   if (subscription && Notification.permission==='granted') {
      // Do not silently transfer device subscriptions between user accounts.
      const result=await call('/api/push/device-status',{endpoint:subscription.endpoint});
      if (result.enabled) {
        setStatus('Push ist auf diesem Gerät aktiviert. Weitere Geräte müssen separat angemeldet werden.',true);
      } else {
        setStatus('Dieses Gerät ist für dein Benutzerkonto noch nicht aktiviert.');
      }
   } else {
      setStatus(Notification.permission==='denied' ?
        'Benachrichtigungen sind im Browser gesperrt. Bitte in den Website-Einstellungen zulassen.' :
        'Push ist auf diesem Gerät noch nicht aktiviert.');
   }
 }
 enable.addEventListener('click',async () => {
   enable.disabled=true;
   try {
     if (Notification.permission==='default') await Notification.requestPermission();
     if (Notification.permission!=='granted') throw new Error('Benachrichtigungsberechtigung nicht erteilt.');
     registration=registration||await navigator.serviceWorker.ready;
     subscription=await registration.pushManager.getSubscription() ||
        await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:asUint8(publicKey)});
     await call('/api/push/subscribe',{subscription:subscription.toJSON()});
     setStatus('Push wurde für dieses Gerät eingeschaltet.',true);
   } catch(e) {setStatus('Aktivierung fehlgeschlagen: '+e.message);}
   finally{enable.disabled=false;}
 });
 disable.addEventListener('click',async () => {
   disable.disabled=true;
   try {
     const sub=subscription || await registration.pushManager.getSubscription();
     if (sub) {
       await call('/api/push/unsubscribe',{endpoint:sub.endpoint});
       await sub.unsubscribe();
     }
     subscription=null;
     setStatus('Push ist auf diesem Gerät deaktiviert.');
   } catch(e) {setStatus('Deaktivierung fehlgeschlagen: '+e.message,true);}
   finally{disable.disabled=false;}
 });
 test.addEventListener('click',async () => {
   test.disabled=true;
   try{
     if (!subscription) throw new Error('Gerät nicht registriert.');
     await call('/api/push/test',{endpoint:subscription.endpoint});
     setStatus('Test-Push in die Versandwarteschlange gestellt.',true);
   }catch(e){setStatus('Test fehlgeschlagen: '+e.message,true);}
   finally{test.disabled=false;}
 });
 preferencesForm.addEventListener('submit', async event => {
   event.preventDefault();
   savePreferences.disabled=true;
   preferencesStatus.textContent='Einstellungen werden gespeichert …';
   try {
     const result=await call('/api/push/preferences',{
       expenseEnabled:expenseEnabled.checked,
       incomeEnabled:incomeEnabled.checked,
       minAmount:minAmount.value,
       detailLevel:detailLevel.value
     });
     preferencesStatus.textContent='Deine Benachrichtigungseinstellungen wurden gespeichert.';
   } catch(e) { preferencesStatus.textContent='Speichern fehlgeschlagen: '+e.message; }
   finally { savePreferences.disabled=false; }
 });
 refresh().catch(e=>{setStatus('Push-Einrichtung derzeit nicht verfügbar: '+e.message);enable.hidden=true;savePreferences.disabled=true;});
})();
