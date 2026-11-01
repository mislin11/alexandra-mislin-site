#!/usr/bin/env python3
"""Open the local editor with no terminal interaction or remote account."""
from pathlib import Path
import argparse,hashlib,json,os,socket,subprocess,sys,time,urllib.request,webbrowser
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'.local-editor';PROJECT=hashlib.sha256(str(ROOT).encode()).hexdigest()[:20]
def health(port):
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/editor/health',timeout=.7) as r:data=json.loads(r.read())
  return data.get('app')=='alexandra-local-editor' and data.get('project')==PROJECT
 except Exception:return False

def main():
 p=argparse.ArgumentParser();p.add_argument('--no-browser',action='store_true',help='Start/check the server without opening any UI (for verification).');args=p.parse_args();PRIVATE.mkdir(exist_ok=True)
 state=PRIVATE/'launcher.json';port=None
 if state.exists():
  try:
   previous=json.loads(state.read_text())
   if health(previous['port']):port=previous['port']
  except Exception:pass
 if port is None:
  for candidate in range(8767,8780):
   if health(candidate):port=candidate;break
   sock=socket.socket()
   try:sock.bind(('127.0.0.1',candidate))
   except OSError:continue
   finally:sock.close()
   log=(PRIVATE/'editor-server.log').open('ab',buffering=0)
   child=subprocess.Popen([sys.executable,str(ROOT/'tools/editor.py'),'--port',str(candidate)],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
   for _ in range(60):
    if child.poll() is not None:break
    if health(candidate):port=candidate;break
    time.sleep(.15)
   if port is not None:state.write_text(json.dumps({'pid':child.pid,'port':port}));break
  if port is None:raise SystemExit('The editor could not start. Please ask for help; your website files have not been removed. The local log is .local-editor/editor-server.log.')
 url='http://127.0.0.1:'+str(port)+'/editor/'
 if not args.no_browser:webbrowser.open(url,new=2)
 print(json.dumps({'editor_url':url,'local_only':True,'browser_open_requested':not args.no_browser}),flush=True)
if __name__=='__main__':main()
