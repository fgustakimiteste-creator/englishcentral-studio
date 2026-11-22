from pathlib import Path
import re

ROOT = Path('/app')
page = ROOT / 'web' / 'index.html'
s = page.read_text(encoding='utf-8')

dialog_start = s.find('<dialog id="browserDialog"')
if dialog_start < 0:
    raise SystemExit('Dialogo de conexão do Chrome não encontrado.')
dialog_end = s.find('</dialog>', dialog_start)
if dialog_end < 0:
    raise SystemExit('Fechamento do diálogo não encontrado.')
dialog = s[dialog_start:dialog_end]
if 'id="browserDialogIntro"' not in dialog:
    dialog, n = re.subn(r'<p class="note">', '<p id="browserDialogIntro" class="note">', dialog, count=1)
    if n != 1:
        raise SystemExit('Parágrafo de instruções do diálogo não encontrado.')
if 'id="browserSteps"' not in dialog:
    dialog, n = re.subn(r'<ol class="browserSteps">', '<ol id="browserSteps" class="browserSteps">', dialog, count=1)
    if n != 1:
        raise SystemExit('Lista de passos do diálogo não encontrada.')
s = s[:dialog_start] + dialog + s[dialog_end:]

start = s.find('async function showBrowserConnect(){')
if start < 0:
    raise SystemExit('Função showBrowserConnect não encontrada.')
end = s.find("$('closeBrowserDialog').onclick=", start)
if end < 0:
    raise SystemExit('Fim da função showBrowserConnect não encontrado.')
new_show = '''function showBrowserConnect(){
 text('browserConnectMessage','');$('browserConsent').checked=false;
 text('browserDialogTitle','Conectar o Chrome deste Windows');
 text('browserDialogIntro','Execute INICIAR_PC.bat neste computador e mantenha a janela aberta. Depois, autorize o painel a acessar o conector local. Senhas e cookies ficam no seu PC e não são enviados ao Render.');
 const steps=$('browserSteps');steps.replaceChildren();
 const items=[
  'No Chrome 144 ou superior, abra chrome://inspect/#remote-debugging e habilite “Allow remote debugging for this browser instance”.',
  'Deixe o EnglishCentral aberto e conectado à sua conta na mesma janela do Chrome.',
  'Mantenha INICIAR_PC.bat em execução neste computador.',
  'Marque a autorização abaixo e clique em Conectar meu Chrome. Permita o acesso à rede local quando o Chrome perguntar e aceite a solicitação de controle do navegador.'
 ];
 for(const value of items){const li=document.createElement('li');li.textContent=value;steps.append(li)}
 $('browserDialog').showModal()
}
'''
s = s[:start] + new_show + s[end:]

form_start = s.find("$('browserConnectForm').onsubmit=async event=>{")
if form_start < 0:
    raise SystemExit('Manipulador do formulário de conexão não encontrado.')
expected = " event.preventDefault();if(remoteMode&&!localBridgeActive){try{await connectLocalPCBridge()}catch(error){text('browserConnectMessage',error.message||String(error));return}}if(!$('browserConsent').checked)return;"
replacement = """ event.preventDefault();
 if(!$('browserConsent').checked)return;
 if(remoteMode&&!localBridgeActive){text('browserConnectMessage','Conectando ao serviço local deste PC…');$('submitBrowserConnect').disabled=true;try{await connectLocalPCBridge()}catch(error){text('browserConnectMessage',error.message||String(error));$('submitBrowserConnect').disabled=false;return}}"""
if expected in s:
    s = s.replace(expected, replacement, 1)
elif replacement not in s:
    raise SystemExit('Não encontrei a sequência de consentimento/conexão esperada no formulário.')

if "const localBridgeBase='http://127.0.0.1:8765/';" not in s:
    raise SystemExit('Ponte local não encontrada no painel.')
if "fetch(localBridgeBase+'api/bridge/bootstrap'" not in s:
    raise SystemExit('Bootstrap real do conector não encontrado.')
if "fetch(apiUrl(path)" not in s or "fetch(apiUrl('screenshot')" not in s:
    raise SystemExit('Nem todas as chamadas principais foram direcionadas ao conector local.')

page.write_text(s, encoding='utf-8')
