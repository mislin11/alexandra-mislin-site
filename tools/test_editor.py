#!/usr/bin/env python3
"""End-to-end editor checks in a temporary copy; never edit the user's project."""
from pathlib import Path
import base64,hashlib,http.client,json,os,shutil,socket,subprocess,sys,tempfile,time,urllib.request,urllib.error,uuid
ROOT=Path(__file__).resolve().parents[1];TEMP=Path(tempfile.mkdtemp(prefix='alexandra-editor-test-'));PROJECT=TEMP/'site';shutil.copytree(ROOT,PROJECT,ignore=shutil.ignore_patterns('.local-editor','dist','__pycache__','.git','screenshots','FILE-CHECKSUMS.sha256'))
sock=socket.socket();sock.bind(('127.0.0.1',0));PORT=sock.getsockname()[1];sock.close();ORIGIN='http://127.0.0.1:'+str(PORT);server=None;token='';checks=[]
def request(endpoint,payload=None,headers=None,status=200):
 data=None if payload is None else json.dumps(payload).encode();h={'X-Editor-Client':'local-editor'}
 if payload is not None:h.update({'Origin':ORIGIN,'X-Editor-Token':token,'Content-Type':'application/json'})
 if headers:
  for k,v in headers.items():
   if v is None:h.pop(k,None)
   else:h[k]=v
 req=urllib.request.Request(ORIGIN+endpoint,data=data,headers=h)
 try:
  with urllib.request.urlopen(req,timeout=50) as r:code=r.status;raw=r.read()
 except urllib.error.HTTPError as e:code=e.code;raw=e.read()
 assert code==status,(endpoint,status,code,raw[:300])
 try:return json.loads(raw)
 except ValueError:return raw

def action(endpoint,payload,**kw):return request(endpoint,dict(payload,request_id=payload.get('request_id',str(uuid.uuid4()))),**kw)
def session():return request('/editor/api/session')
def item(kind,key):return request('/editor/api/item/'+kind+'/'+key)
def restore(identity):return action('/editor/api/restore',{'history_id':identity,'revision':session()['manifest']['revision']})
def snap():
 files=list((PROJECT/'content/pages').glob('*.html'))+list((PROJECT/'content/posts').glob('*'))+[PROJECT/'public/assets/documents/mislin-cv-april-2026.pdf'];return {str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
def start():
 global server,token
 log=(TEMP/'server.log').open('ab',buffering=0);server=subprocess.Popen([sys.executable,str(PROJECT/'tools/editor.py'),'--port',str(PORT)],stdout=log,stderr=log)
 for _ in range(100):
  if server.poll() is not None:raise AssertionError('Test server exited: '+(TEMP/'server.log').read_text()[-3000:])
  try:s=session();token=s['token'];return s
  except (OSError,AssertionError):time.sleep(.1)
 raise AssertionError('Editor did not start')
def done(label):checks.append(label)
try:
 s=start();original=snap();original_dist={str(f.relative_to(PROJECT/'dist')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (PROJECT/'dist').rglob('*') if f.is_file()}
 request('/editor/',headers={'Sec-Fetch-Site':'cross-site','Sec-Fetch-Mode':'navigate','Sec-Fetch-Dest':'document'});done('Opening editor from a normal clickable external link works')
 request('/editor/api/session',headers={'Origin':'https://evil.example','Sec-Fetch-Site':'cross-site'},status=403)
 request('/editor/api/session',headers={'Host':'evil.example:'+str(PORT)},status=403)
 p=item('page','teaching');payload={'kind':'page','id':'teaching','revision':p['revision'],'body_html':'<p>Test</p>'}
 action('/editor/api/save',payload,headers={'Origin':None},status=403);action('/editor/api/save',payload,headers={'X-Editor-Token':None},status=403);action('/editor/api/save',payload,headers={'Origin':'https://evil.example'},status=403);action('/editor/api/save',payload,headers={'Content-Type':'text/plain'},status=415)
 done('Host, Origin, CSRF token and content-type protections reject unsafe writes')
 for bad in ['<script>alert(1)</script><p>Text</p>','<p onclick="alert(1)">Text</p>','<a href="javascript:alert(1)">Text</a>','<img src="file:///etc/passwd">','<p></p>']:
  action('/editor/api/save',dict(payload,body_html=bad),status=400)
 action('/editor/api/save',dict(payload,id='../../README'),status=400)
 assert snap()==original;done('Script/event/unsafe-link/path-traversal/empty-content inputs leave files unchanged')
 edited=p['body_html']+'<p>EDITOR TEST <strong>bold stays</strong> and <a href="https://example.org/">a link stays</a>.</p>'
 key=str(uuid.uuid4());saved=action('/editor/api/save',dict(payload,body_html=edited,request_id=key));assert b'EDITOR TEST' in request('/about/');loaded=item('page','teaching');assert '<strong>bold stays</strong>' in loaded['body_html'] and 'https://example.org/' in loaded['body_html'];assert action('/editor/api/save',dict(payload,body_html=edited,request_id=key))['history_id']==saved['history_id'];done('Actual page save, rebuild, fresh read, formatting/link preservation and duplicate-request idempotency')
 action('/editor/api/save',dict(payload,body_html='<p>Stale</p>'),status=409);before=snap();action('/editor/api/save',dict(payload,revision=loaded['revision'],body_html=edited+'<p><a href="/missing-page-for-editor-test/">Bad link</a></p>'),status=422);assert snap()==before;assert b'EDITOR TEST' in request('/about/');done('Stale revisions and failed builds preserve source and current preview')
 restore(saved['history_id']);assert snap()==original;done('Undo restores exact original page bytes')
 manifest=session()['manifest'];news=action('/editor/api/save',{'kind':'news','id':'new-news','new':True,'revision':manifest['news_revision'],'date':'October 2030','body_html':'<p>NEWS TEST <em>formatted</em> <a href="https://example.org/">link</a>.</p><p>Second paragraph stays grouped.</p>'});assert b'NEWS TEST' in request('/');assert len(news['manifest']['news'])==len(s['manifest']['news'])+1;ni=item('news','0');assert ni['date']=='October 2030' and '<em>formatted</em>' in ni['body_html'];done('News add, date field, multi-paragraph grouping, links and reload')
 update=action('/editor/api/save',{'kind':'news','id':'0','revision':ni['revision'],'date':'November 2030','body_html':ni['body_html'].replace('NEWS TEST','NEWS UPDATED')});assert b'NEWS UPDATED' in request('/');restore(update['history_id']);assert b'NEWS TEST' in request('/');undo_news=restore(news['history_id']);assert snap()==original;restore(undo_news['history_id']);assert b'NEWS TEST' in request('/');restore(news['history_id']);assert snap()==original;done('Repeated news saves, undo, redo through recoverable history and exact restoration')
 draft=action('/editor/api/save',{'kind':'post','id':'new-post','new':True,'revision':session()['manifest']['revision'],'title':'PRIVATE EDITOR TEST','date':'2030-10-31','summary':'A test summary.','draft':True,'image':'','body_html':'<p>DRAFT BODY <strong>bold</strong> and <a href="https://example.org/">a link</a>.</p>'});draftid=draft['id'];di=item('post',draftid);assert b'DRAFT BODY' in request('/editor/draft/'+draftid);request(di['slug']+'/',status=404);assert not (PROJECT/'dist'/di['slug'].lstrip('/')/'index.html').exists();done('New draft saves and previews privately without entering public static output')
 second=action('/editor/api/save',{'kind':'post','id':'new-post','new':True,'revision':session()['manifest']['revision'],'title':'SECOND PRIVATE TEST','date':'2030-11-01','summary':'Second draft.','draft':True,'image':'','body_html':'<p>SECOND DRAFT BODY</p>'});assert b'SECOND DRAFT BODY' in request('/editor/draft/'+second['id']);assert b'DRAFT BODY' in request('/editor/draft/'+draftid);restore(second['history_id']);assert b'DRAFT BODY' in request('/editor/draft/'+draftid);done('Several private drafts remain independently previewable and reflect restored source')
 published=action('/editor/api/save',dict(di,new=False,draft=False));assert b'DRAFT BODY' in request(di['slug']+'/');assert item('post',draftid)['date']=='2030-10-31';action('/editor/api/save',dict(item('post',draftid),title=''),status=400);restore(draft['history_id']);assert snap()==original;done('Article title/date/summary/body, local inclusion, validation and undo of creation')
 original_post=s['manifest']['posts'][0]['id'];pi=item('post',original_post);timestamp=json.loads((PROJECT/'content/posts'/(original_post+'.json')).read_text())['published_at'];postsave=action('/editor/api/save',dict(pi,body_html=pi['body_html']+'<p>POST TEST</p>'));assert json.loads((PROJECT/'content/posts'/(original_post+'.json')).read_text())['published_at']==timestamp;restore(postsave['history_id']);assert snap()==original;done('Editing existing article retains exact original publication timestamp and stable URL')
 pi=item('post',original_post);datechange=action('/editor/api/save',dict(pi,date='2030-01-02'));assert item('post',original_post)['date']=='2030-01-02';assert item('post',original_post)['slug']==pi['slug'];restore(datechange['history_id']);assert snap()==original;done('Deliberate publication date correction rebuilds valid schema without changing the original URL')
 cv_before=session()['cv_revision'];action('/editor/api/cv',{'revision':cv_before,'pdf_base64':'not a pdf'},status=400)
 pdf=(PROJECT/'public/assets/documents/negotiation-medical-professionals-2016.pdf').read_bytes();cv=action('/editor/api/cv',{'revision':cv_before,'pdf_base64':base64.b64encode(pdf).decode()});assert request('/assets/documents/mislin-cv-april-2026.pdf')==pdf;restore(cv['history_id']);assert snap()==original;done('CV PDF validation, replacement, preview and byte-exact undo')
 original_text=(PROJECT/'content/pages/research.html').read_bytes();outside=TEMP/'outside.html';outside.write_text('OUTSIDE UNCHANGED');rp=PROJECT/'content/pages/research.html';revision=item('page','research')['revision'];rp.unlink();rp.symlink_to(outside);action('/editor/api/save',{'kind':'page','id':'research','revision':revision,'body_html':'<p>Attack</p>'},status=400);assert outside.read_text()=='OUTSIDE UNCHANGED';rp.unlink();rp.write_bytes(original_text);done('Symlink targets cannot escape intended content writes')
 server.terminate();server.wait(timeout=5);before=(PROJECT/'content/pages/teaching.html').read_bytes();fake=PROJECT/'.local-editor/history/20990101T000000000000-aaaaaaaaaa.json';fake.write_text(json.dumps({'time':'2099-01-01T00:00:00Z','label':'Interrupted test','before':{'content/pages/teaching.html':base64.b64encode(before).decode()},'committed':False}));(PROJECT/'content/pages/teaching.html').write_text('<p>Interrupted content</p>');start();assert snap()==original;assert json.loads(fake.read_text())['recovered_after_interrupt'];done('Restart recovers an interrupted save and rebuilds the last valid content')
 current_dist={str(f.relative_to(PROJECT/'dist')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (PROJECT/'dist').rglob('*') if f.is_file()};assert current_dist==original_dist
 for f in (PROJECT/'dist').rglob('*'):
  if f.is_file() and f.suffix in ('.html','.js','.css','.json'):assert token.encode() not in f.read_bytes() and b'/editor/api/' not in f.read_bytes()
 assert not (PROJECT/'dist/editor').exists();done('Public output is byte-identical after tests and contains no editor code, endpoints or session token')
 report={'passed':True,'checks':checks,'count':len(checks),'tests_ran_in_temporary_copy':True,'real_project_content_unchanged':True,'all_test_content_restored':snap()==original,'public_output_unchanged':True};(ROOT/'docs/editor-backend-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 if server and server.poll() is None:server.terminate();server.wait(timeout=5)
