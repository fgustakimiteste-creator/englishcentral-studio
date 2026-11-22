from pathlib import Path
import re

ROOT = Path('/app')
page = ROOT / 'web' / 'index.html'
s = page.read_text(encoding='utf-8')

marker = "let token='',connected=false,opened=false,running=false,busy=false,viewing=false,refreshing=false,courseRefreshing=false,lastCourseRefresh=0,lastCourseUrl='',lastUrl=null,manualPointerAt=0,platformType='';\n"
bridge_state = """let localBridgeActive=false;
const localBridgeBase='http://127.0.0.1:8765/';
function apiUrl(path){return (localBridgeActive?localBridgeBase:panelBase)+'api/'+path}
function apiTargetOptions(){return localBridgeActive?{targetAddressSpace:'loopback'}:{}}
"""
if 'let localBridgeActive=false;' not in s:
    if marker not in s: raise SystemExit('Frontend state marker not found')
    s = s.replace(marker, marker + bridge_state, 1)

# The hosted UI must offer the Chrome action even though its own browser is remote.
s = s.replace("for(const id of ['connectChrome','emptyConnectChrome'])$(id).hidden=remoteMode;",
              "for(const id of ['connectChrome','emptyConnectChrome'])$(id).hidden=false;", 1)

# Explain that a small Windows companion runs on the same PC as Chrome.
lines = s.splitlines(keepends=True)
for i, line in enumerate(lines):
    if "text('browserSessionHelp',remoteMode?" in line:
        indent = line[:len(line) - len(line.lstrip())]
        lines[i] = indent + "text('browserSessionHelp',remoteMode?'No PC onde o Chrome está aberto, execute INICIAR_PC.bat e mantenha a janela do conector aberta. Depois clique em “Já estou conectado no Chrome”. Cada PC usa seu próprio login.':'Seu Chrome usa as contas já conectadas nele.');\n"
        break
else:
    if "INICIAR_PC.bat" not in s:
        raise SystemExit('browserSessionHelp line not found')
s = ''.join(lines)

if 'async function connectLocalPCBridge()' not in s:
    marker = "async function api(path,method='GET',data){\n"
    bootstrap = '''async function connectLocalPCBridge(){
 if(localBridgeActive)return true;
 if(!window.isSecureContext)throw Error('Abra o painel pelo endereço HTTPS do Render.');
 try{
  const permission=await navigator.permissions?.query?.({name:'loopback-network'});
  if(permission?.state==='denied')throw Error('O Chrome bloqueou o acesso à rede de loopback. Abra as permissões deste site e permita o acesso ao computador.');
 }catch(error){if(error?.message?.includes('bloqueou'))throw error}
 let response;
 try{
  response=await fetch(localBridgeBase+'api/bridge/bootstrap',{method:'GET',mode:'cors',cache:'no-store',targetAddressSpace:'loopback'});
 }catch(error){throw Error('Conector deste PC não encontrado. Execute INICIAR_PC.bat no computador, mantenha a janela aberta e permita “Rede de loopback” no Chrome.')}
 if(!response.ok)throw Error(response.status===403?'O conector local recusou esta origem. Atualize o pacote Windows.':'O conector local respondeu HTTP '+response.status+'.');
 const data=await response.json();
 if(!data.ok||!data.token)throw Error('O conector local não forneceu uma sessão válida. Reinicie INICIAR_PC.bat.');
 token=data.token;localBridgeActive=true;remoteMode=false;
 const status=await api('status');renderAppRuntime(status.aplicativo||{remoto:false});
 await refresh();return true;
}

'''
    if marker not in s: raise SystemExit('API wrapper marker not found')
    s=s.replace(marker, bootstrap+marker, 1)

# Route API, screenshots, and agent previews to this PC after the user opts in.
s = s.replace("fetch(panelBase+'api/'+path,{method,headers:",
              "fetch(apiUrl(path),{method,mode:localBridgeActive?'cors':'same-origin',headers:", 1)
s = s.replace("...(controller?{signal:controller.signal}:{})});",
              "...(controller?{signal:controller.signal}:{}),...apiTargetOptions()});", 1)
s = s.replace("fetch(panelBase+'api/moodle/automation/lanes/'+encodeURIComponent(lane.id)+'/screenshot',{headers:{'X-EC-Token':token},cache:'no-store'})",
              "fetch(apiUrl('moodle/automation/lanes/'+encodeURIComponent(lane.id)+'/screenshot'),{headers:{'X-EC-Token':token},cache:'no-store',...apiTargetOptions()})")
s = s.replace("fetch(panelBase+'api/screenshot',{cache:'no-store',headers:{'X-EC-Token':token},signal:controller.signal})",
              "fetch(apiUrl('screenshot'),{cache:'no-store',headers:{'X-EC-Token':token},signal:controller.signal,...apiTargetOptions()})")

# Never persist the local agent's token in the visitor's browser storage or URL.
if 'if(localBridgeActive){text(\'deviceAccessStatus\'' not in s:
    s = re.sub(r'(function storeAccess\(\)\{\n)',
               r"\1 if(localBridgeActive){text('deviceAccessStatus','Conectado ao conector deste PC. O token não é salvo no navegador.');return}\n",
               s, count=1)

# Replace the earlier mobile/Termux dialog with Windows instructions and bootstrap.
start = s.find('function showBrowserConnect(){')
if start < 0: raise SystemExit('showBrowserConnect function not found')
end = s.find("$('closeBrowserDialog').onclick=", start)
if end < 0: raise SystemExit('showBrowserConnect end marker not found')
new_show = '''async function showBrowserConnect(){
 text('browserConnectMessage','');$('browserConsent').checked=false;
 text('browserDialogTitle','Conectar o Chrome deste Windows');
 text('browserDialogIntro','Execute INICIAR_PC.bat neste computador e mantenha a janela aberta. O painel HTTPS conversa com o conector local somente após a sua permissão; senhas e cookies não são enviados ao Render.');
 const steps=$('browserSteps');steps.replaceChildren();
 const items=[
  'Extraia o pacote EnglishCentral Studio no Windows e execute INICIAR_PC.bat. Aguarde a instalação inicial e mantenha a janela aberta.',
  'No Chrome, abra chrome://inspect/#remote-debugging e ative as conexões de depuração remota.',
  'Deixe o EnglishCentral aberto e conectado à sua conta na mesma janela do Chrome.',
  'Volte aqui, marque a autorização e clique em Conectar meu Chrome. Aceite a solicitação que aparecer no próprio Chrome.'
 ];
 for(const value of items){const li=document.createElement('li');li.textContent=value;steps.append(li)}
 if(remoteMode&&!localBridgeActive){try{await connectLocalPCBridge();text('browserConnectMessage','Conector deste PC encontrado. Agora autorize o Chrome.')}catch(error){text('browserConnectMessage',error.message||String(error))}}
 $('browserDialog').showModal()
}
'''
s = s[:start] + new_show + s[end:]

# The Android gateway installer blocks cloud-side CDP; replace that with local bridge bootstrap.
s = re.sub(r"if\(remoteMode\)\{text\('browserConnectMessage'.*?;return\}",
           "if(remoteMode&&!localBridgeActive){try{await connectLocalPCBridge()}catch(error){text('browserConnectMessage',error.message||String(error));return}}",
           s, count=1, flags=re.S)
# Retain a guard for source variants that did not receive the earlier gateway guard.
s = s.replace("event.preventDefault();if(!$('browserConsent').checked)return;",
              "event.preventDefault();if(remoteMode&&!localBridgeActive){try{await connectLocalPCBridge()}catch(error){text('browserConnectMessage',error.message||String(error));return}}if(!$('browserConsent').checked)return;", 1)
s = s.replace("event.preventDefault();\n if(!$('browserConsent').checked)return;",
              "event.preventDefault();\n if(remoteMode&&!localBridgeActive){try{await connectLocalPCBridge()}catch(error){text('browserConnectMessage',error.message||String(error));return}}\n if(!$('browserConsent').checked)return;", 1)

page.write_text(s, encoding='utf-8')
