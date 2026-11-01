#!/usr/bin/env python3
"""Private, loopback-only content editor. Never copy this server into public hosting."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from datetime import datetime,timezone,date
import argparse,base64,hashlib,hmac,html,json,mimetypes,os,re,secrets,shutil,subprocess,sys,threading,unicodedata,uuid
ROOT=Path(__file__).resolve().parents[1];CONTENT=ROOT/'content';PRIVATE=ROOT/'.local-editor';BUILD=PRIVATE/'builds';HISTORY=PRIVATE/'history';UI=ROOT/'editor';DIST=ROOT/'dist'
PAGES={
 'home-introduction':('Home — introduction','/'),
 'home-cv':('Home — CV link','/'),
 'research':('Research','/research/'),
 'teaching':('Teaching','/about/'),
 'press':('Press','/press/'),
 'contact':('Contact','/contact/'),
 'speaking-workshops':('Speaking & Workshops','/speaking-workshops/'),
 'workwell-introduction':('WorkWell — introduction','/workwell-diplomacy/')}
NEWS='content/pages/home-news.html';CV='public/assets/documents/mislin-cv-april-2026.pdf';LOCK=threading.RLock();RESULTS={};TOKEN=secrets.token_urlsafe(32)
LEGACY=set(json.loads((CONTENT/'legacy-routes.json').read_text()));PROJECT=hashlib.sha256(str(ROOT).encode()).hexdigest()[:20]
for p in (PRIVATE,BUILD,HISTORY):p.mkdir(exist_ok=True)
class EditError(Exception):
 def __init__(self,message,status=400):super().__init__(message);self.status=status
class Plain(HTMLParser):
 def __init__(self,s):super().__init__(convert_charrefs=True);self.parts=[];self.feed(s)
 def handle_data(self,s):self.parts.append(s)
def text(s):return re.sub(r'\s+',' ',''.join(Plain(s).parts)).strip()
def now():return datetime.now(timezone.utc).isoformat()
def digest(data):return hashlib.sha256(data).hexdigest()
def path(rel):
 if not isinstance(rel,str) or not (rel in {NEWS,CV} or rel in {'content/pages/'+k+'.html' for k in PAGES} or re.fullmatch(r'content/posts/[A-Za-z0-9][A-Za-z0-9_-]{0,90}\.(?:json|html)',rel)):raise EditError('That content location is not editable.')
 p=ROOT/rel
 if p.is_symlink() or any(a.is_symlink() for a in p.parents if a!=ROOT.parent):raise EditError('Linked content locations cannot be edited.')
 if ROOT not in p.resolve().parents:raise EditError('The content location is outside this project.')
 return p
def read(rel):return path(rel).read_bytes()
def write(rel,data):
 p=path(rel)
 if data is None:
  if p.exists():p.unlink()
  return
 p.parent.mkdir(exist_ok=True);temp=p.with_name('.'+p.name+'.'+uuid.uuid4().hex+'.tmp');temp.write_bytes(data);os.replace(temp,p)
def version(files):
 h=hashlib.sha256()
 for rel in sorted(files):
  h.update(rel.encode());p=path(rel);h.update(p.read_bytes() if p.exists() else b'ABSENT')
 return h.hexdigest()
def globalversion():return version([str(p.relative_to(ROOT)) for p in (CONTENT/'pages').glob('*.html') if p.name=='home-news.html' or p.stem in PAGES]+[str(p.relative_to(ROOT)) for p in (CONTENT/'posts').glob('*') if p.suffix in ('.json','.html')]+[CV])
def post(key):
 if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,90}',str(key)):raise EditError('Choose an existing article.',404)
 meta='content/posts/'+key+'.json';p=path(meta)
 if not p.is_file():raise EditError('This article no longer exists. Reload the list.',404)
 data=json.loads(p.read_text());body='content/posts/'+str(data['body_file']);path(body)
 return data,meta,body
class TopBlocks(HTMLParser):
 def __init__(self,s):
  super().__init__(convert_charrefs=False);self.s=s;self.lines=[0];self.lines.extend(m.end() for m in re.finditer('\n',s));self.depth=0;self.start=None;self.spans=[];self.feed(s)
 def at(self):line,col=self.getpos();return self.lines[line-1]+col
 def handle_starttag(self,t,a):
  if self.depth==0:self.start=self.at()
  if t not in ('br','hr','img','input','meta','link','source'):self.depth+=1
  elif self.depth==0:self.spans.append((self.start,self.at()+len(self.get_starttag_text())))
 def handle_endtag(self,t):
  if t in ('br','hr','img','input','meta','link','source'):return
  self.depth-=1
  if self.depth==0 and self.start is not None:self.spans.append((self.start,self.at()+len('</'+t+'>')));self.start=None

def newsitems():
 s=read(NEWS).decode();spans=TopBlocks(s).spans;items=[]
 for i,(a,b) in enumerate(spans):
  raw=s[a:b]
  if not text(raw):continue
  inner=re.sub(r'^<(p|section|div)(?:\s[^>]*)?>(.*)</\1>$',r'\2',raw,flags=re.S).strip()
  # Existing imported entries have a plain English date at the beginning.
  m=re.match(r'^(?:<p>\s*)?((?:January|February|March|April|May|June|July|August|September|October|November|December)[,\s]+(?:\d{1,2}[,\s]+)?\d{4})([.\s,]+)',inner)
  label=m.group(1) if m else '';separator=m.group(2) if m else '. '
  body=inner
  if m:body=inner[:m.start()]+('<p>' if inner.startswith('<p>') else '')+inner[m.end():]
  items.append({'id':str(i),'date':label,'body_html':body,'label':(label+' · ' if label else '')+text(body)[:88],'start':a,'end':b,'separator':separator,'raw':raw})
 return s,items
ALLOWED={'p','div','section','h1','h2','h3','h4','h5','h6','strong','b','em','i','u','ul','ol','li','a','blockquote','br','hr','figure','figcaption','img','table','thead','tbody','tr','th','td','sup','sub','time','code','span','font'}
VOID={'br','hr','img'}
class SafeHTML(HTMLParser):
 def __init__(self,s,body=False):super().__init__(convert_charrefs=True);self.out=[];self.stack=[];self.body=body;self.feed(s);self.close();
 def handle_starttag(self,t,attrs):
  if t in ('script','style','iframe','object','embed','svg','math','form','input','button','textarea','link','meta','base'):raise EditError('This content includes an unsupported embedded element. Paste text or use the formatting buttons.')
  if t not in ALLOWED:raise EditError('This formatting is not supported. Paste as plain text and format it here.')
  if any(k.lower().startswith('on') for k,v in attrs):raise EditError('Embedded event code is not allowed in content.')
  original=t;t='h2' if self.body and t=='h1' else t;d=dict(attrs);parts=[]
  if t=='a':
   v=d.get('href','').strip();p=urlsplit(v)
   if p.scheme not in ('','http','https','mailto','tel') or v.startswith('//') or any(ord(x)<32 for x in v):raise EditError('Use a normal https://, mailto:, or local website link.')
   if p.scheme in ('http','https') and (not p.hostname or ' ' in v):raise EditError('Please check the link address; it is not a valid website link.')
   parts.append(('href',v))
   if d.get('title'):parts.append(('title',d['title'][:300]))
  if t=='img':
   src=d.get('src','')
   if not src.startswith('/assets/images/') or '..' in unquote(src) or not (DIST/src.lstrip('/')).is_file():raise EditError('Keep an existing website image, or ask for a new image to be added first.')
   parts=[('src',src),('alt',d.get('alt','')),('loading','lazy'),('decoding','async')]
  if t in ('td','th'):
   for k in ('colspan','rowspan'):
    if d.get(k,'').isdigit() and 0<int(d[k])<=20:parts.append((k,d[k]))
  if t=='time' and d.get('datetime'):parts.append(('datetime',d['datetime'][:80]))
  self.out.append('<'+t+''.join(' '+k+'="'+html.escape(v,quote=True)+'"' for k,v in parts)+'>')
  if original not in VOID:self.stack.append((original,t))
 def handle_endtag(self,t):
  if t in VOID:return
  if not self.stack or self.stack[-1][0]!=t:raise EditError('The pasted formatting could not be read safely. Try pasting plain text.')
  _,out=self.stack.pop();self.out.append('</'+out+'>')
 def handle_startendtag(self,t,a):self.handle_starttag(t,a);self.handle_endtag(t)
 def handle_data(self,s):self.out.append(html.escape(s))
 def close(self):
  super().close()
  if self.stack:raise EditError('The text formatting is incomplete. Try pasting plain text.')
def safe(s,body=False):
 if not isinstance(s,str) or len(s)>350000:raise EditError('This text is too large for one edit.')
 cleaned=''.join(SafeHTML(s,body).out).strip()
 if not text(cleaned):raise EditError('Add some text before saving. An empty save would erase this content.')
 return cleaned+'\n'
def string(value,label,limit=300,required=True):
 if not isinstance(value,str) or len(value)>limit or (required and not value.strip()):raise EditError('Please enter '+label+'.')
 return value.strip()
def metadata_summary():
 items=[]
 for f in (CONTENT/'posts').glob('*.json'):
  d=json.loads(f.read_text());items.append({'id':f.stem,'label':d['title'],'date':d['published_at'][:10],'draft':bool(d.get('draft',False))})
 items.sort(key=lambda p:p['date'],reverse=True)
 _,news=newsitems()
 return {'project':PROJECT,'revision':globalversion(),'news_revision':version([NEWS]),'cv_revision':version([CV]),'pages':[{'id':k,'label':v[0],'preview':v[1]} for k,v in PAGES.items()],'news':[{'id':x['id'],'label':x['label']} for x in news],'posts':items,'images':[{'path':'/assets/images/'+f.name,'label':f.stem.replace('-',' ')} for f in sorted((ROOT/'public/assets/images').glob('*'))],'history':historylist()}
def getitem(kind,key):
 if kind=='page':
  if key not in PAGES:raise EditError('Choose a page.',404)
  rel='content/pages/'+key+'.html';return {'kind':kind,'id':key,'title':PAGES[key][0],'body_html':read(rel).decode(),'revision':version([rel]),'preview':PAGES[key][1]}
 if kind=='news':
  _,items=newsitems();item=next((x for x in items if x['id']==key),None)
  if not item:raise EditError('This news entry moved. Reload the list.',404)
  return {'kind':kind,'id':key,'title':'News entry','date':item['date'],'body_html':item['body_html'],'revision':version([NEWS]),'preview':'/'}
 if kind=='post':
  d,m,b=post(key);return {'kind':kind,'id':key,'title':d['title'],'date':d['published_at'][:10],'body_html':read(b).decode(),'summary':text(d['excerpt_html']),'draft':bool(d.get('draft',False)),'image':d.get('image',''),'slug':d['slug'],'revision':version([m,b]),'preview':d['slug'].rstrip('/')+'/' ,'legacy':d['slug'] in LEGACY}
 raise EditError('Choose an item to edit.',404)
def historylist():
 records=[]
 for p in sorted(HISTORY.glob('*.json'),reverse=True)[:100]:
  try:
   d=json.loads(p.read_text())
   if d.get('committed'):records.append({'id':p.stem,'label':d['label'],'time':d['time']})
  except (ValueError,OSError):continue
 return records

def runbuild(output,draft=None):
 env=dict(os.environ,SITE_OUTPUT_DIR=str(output),SITE_EDITOR_BUILD='1',SITE_CHECK_REPORT=str(output.parent/(output.name+'-check.json')))
 if draft:env['SITE_PREVIEW_DRAFT_ID']=draft
 else:env.pop('SITE_PREVIEW_DRAFT_ID',None)
 result=subprocess.run([sys.executable,str(ROOT/'tools/build.py')],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45)
 if result.returncode:raise EditError('The preview could not rebuild. Your saved content has been restored.',422)
 if not draft:
  result=subprocess.run([sys.executable,str(ROOT/'tools/check.py')],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45)
  if result.returncode:
   try:errors=json.loads(Path(env['SITE_CHECK_REPORT']).read_text())['errors']
   except Exception:errors=[]
   reason=next((x for x in errors if 'broken internal link' in x),'The page needs its original heading and valid local links.')
   raise EditError('Save cancelled to protect the website. '+reason,422)
def swap(output):
 old=BUILD/(uuid.uuid4().hex+'-previous')
 if DIST.exists():os.replace(DIST,old)
 try:os.replace(output,DIST)
 except Exception:
  if old.exists():os.replace(old,DIST)
  raise
 if old.exists():shutil.rmtree(old)
def transact(changes,label,draft=None):
 before={rel:(base64.b64encode(path(rel).read_bytes()).decode() if path(rel).exists() else None) for rel in changes}
 identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'-'+uuid.uuid4().hex[:10];record={'time':now(),'label':label,'before':before,'committed':False};recordpath=HISTORY/(identity+'.json');recordpath.write_text(json.dumps(record))
 output=BUILD/(uuid.uuid4().hex+'-site')
 try:
  for rel,data in changes.items():write(rel,data)
  runbuild(output)
  private_draft=None
  if draft:private_draft=BUILD/(uuid.uuid4().hex+'-draft');runbuild(private_draft,draft)
  if private_draft:shutil.rmtree(private_draft)
  record['committed']=True;recordpath.write_text(json.dumps(record));swap(output);return identity
 except Exception:
  for rel,data in before.items():write(rel,base64.b64decode(data) if data is not None else None)
  if output.exists():shutil.rmtree(output)
  record['committed']=False;record['rolled_back']=True;recordpath.write_text(json.dumps(record))
  raise

def saveitem(data):
 kind=data.get('kind');key=data.get('id');revision=data.get('revision');new=bool(data.get('new',False));preview='/';changes={};draftkey=None
 if not isinstance(revision,str):raise EditError('Reload the item before saving.',409)
 if kind=='page':
  if key not in PAGES:raise EditError('Choose a valid page.')
  rel='content/pages/'+key+'.html'
  if revision!=version([rel]):raise EditError('This page changed in another tab. Reload it before saving; your unsaved edit is kept in this browser.',409)
  changes[rel]=safe(data.get('body_html')).encode();label='Saved '+PAGES[key][0];preview=PAGES[key][1]
 elif kind=='news':
  source,items=newsitems()
  if revision!=version([NEWS]):raise EditError('The news list changed in another tab. Reload it before saving.',409)
  d=string(data.get('date',''),'a short date label',80,False);body=safe(data.get('body_html'),True).strip();prefix=html.escape(d)+(' ' if d.endswith('.') else '. ') if d else ''
  if re.match(r'^<p>',body):entry='<section>'+body.replace('<p>','<p>'+prefix,1)+'</section>'
  elif re.search(r'<(?:p|div|section|ul|ol|h[2-6]|blockquote)\b',body):entry='<section><p>'+prefix+'</p>'+body+'</section>'
  else:entry='<p>'+prefix+body+'</p>'
  if new:source=entry+'\n'+source;key='0'
  else:
   item=next((x for x in items if x['id']==str(key)),None)
   if not item:raise EditError('This news item moved. Reload the list.',409)
   source=source[:item['start']]+entry+source[item['end']:]
  changes[NEWS]=source.encode();label='Added news' if new else 'Updated news';preview='/'
 elif kind=='post':
  title=string(data.get('title'),'an article title',220);datestring=string(data.get('date'),'a publication date',10)
  try:published=date.fromisoformat(datestring)
  except ValueError:raise EditError('Choose a valid publication date.')
  if published.year<1900 or published.year>2100:raise EditError('Choose a publication date between 1900 and 2100.')
  if new:
   if revision!=globalversion():raise EditError('The website changed while you started this article. Reload before saving.',409)
   key='post-'+uuid.uuid4().hex;meta='content/posts/'+key+'.json';bodyrel='content/posts/'+key+'.html';slug=re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',title).encode('ascii','ignore').decode().lower()).strip('-') or 'new-article';slug='/workwelldiplomacy/'+datestring.replace('-','/')+'/'+slug
   if any(json.loads(f.read_text())['slug']==slug for f in (CONTENT/'posts').glob('*.json')):slug+='-'+key[-6:]
   instant=datetime(published.year,published.month,published.day,tzinfo=timezone.utc);old={'slug':slug,'published_at':instant.isoformat(),'publishOn':int(instant.timestamp()*1000),'author':'Alexandra Mislin','tags':[],'categories':[],'body_file':key+'.html'}
  else:
   old,meta,bodyrel=post(key)
   if revision!=version([meta,bodyrel]):raise EditError('This article changed in another tab. Reload before saving; your unsaved draft is still in this browser.',409)
  draft=bool(data.get('draft',False))
  if old['slug'] in LEGACY and draft:raise EditError('Existing published articles keep their original links. You can edit their text here.')
  if datestring!=old['published_at'][:10]:
   instant=datetime(published.year,published.month,published.day,tzinfo=timezone.utc);old['published_at']=instant.isoformat();old['publishOn']=int(instant.timestamp()*1000)
  summary=string(data.get('summary',''),'a short summary',3000,False)
  excerpt=old.get('excerpt_html','') if summary==text(old.get('excerpt_html','')) else '<p>'+html.escape(summary)+'</p>'
  image=data.get('image','')
  if image and image not in ['/assets/images/'+p.name for p in (ROOT/'public/assets/images').glob('*')]:raise EditError('Choose an existing website image.')
  old.update({'title':title,'draft':draft,'updated_at':now(),'updatedOn':int(datetime.now(timezone.utc).timestamp()*1000),'excerpt_html':excerpt,'image':image,'image_alt':title})
  changes={meta:(json.dumps(old,indent=2,ensure_ascii=False)+'\n').encode(),bodyrel:safe(data.get('body_html'),True).encode()};label=('Created ' if new else 'Updated ')+title;preview=old['slug'].rstrip('/')+'/'
  if draft:draftkey=key;preview='/editor/draft/'+key
 else:raise EditError('Choose a page, news entry or article.')
 identity=transact(changes,label,draftkey);return {'ok':True,'kind':kind,'id':str(key),'history_id':identity,'preview':preview,'manifest':metadata_summary(),'item':getitem(kind,str(key)),'message':'Saved on this Mac. Nothing has been published.'}
def restore(data):
 if data.get('revision')!=globalversion():raise EditError('The website changed. Reload the history before restoring.',409)
 identity=data.get('history_id','')
 if not re.fullmatch(r'\d{8}T\d{12}-[a-f0-9]{10}',identity):raise EditError('Choose a saved version.')
 f=HISTORY/(identity+'.json')
 if not f.is_file():raise EditError('That saved version is not available.',404)
 r=json.loads(f.read_text())
 if not r.get('committed'):raise EditError('That save did not change the website.')
 changes={rel:(base64.b64decode(value,validate=True) if value is not None else None) for rel,value in r['before'].items()}
 for rel in changes:path(rel)
 new=transact(changes,'Restored version before: '+r['label']);return {'ok':True,'history_id':new,'manifest':metadata_summary(),'preview':'/','message':'Previous content restored locally. The version you replaced is also recoverable in history.'}
def uploadcv(data):
 if data.get('revision')!=version([CV]):raise EditError('The CV changed in another tab. Reload before replacing it.',409)
 try:b=base64.b64decode(data.get('pdf_base64',''),validate=True)
 except Exception:raise EditError('Choose a readable PDF file.')
 if not b.startswith(b'%PDF-') or b'%%EOF' not in b[-4096:] or len(b)>8*1024*1024:raise EditError('Choose a valid PDF no larger than 8 MB.')
 identity=transact({CV:b},'Replaced CV PDF');return {'ok':True,'history_id':identity,'revision':version([CV]),'manifest':metadata_summary(),'preview':'/assets/documents/mislin-cv-april-2026.pdf','message':'CV replaced locally. The old PDF is recoverable in history. Nothing is published.'}
class Handler(BaseHTTPRequestHandler):
 server_version='LocalWebsiteEditor'
 def log_message(self,fmt,*args):print(self.log_date_time_string(),self.command,urlsplit(self.path).path,flush=True)
 def validhost(self):
  values=self.headers.get_all('Host',[])
  return len(values)==1 and values[0] in self.server.hosts
 def headers_safe(self,ctype,editor=True):
  self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Cross-Origin-Resource-Policy','same-origin')
  if editor:self.send_header('X-Frame-Options','DENY');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
  else:self.send_header('X-Frame-Options','SAMEORIGIN')
 def send(self,status,body,ctype='application/json; charset=utf-8',editor=True):
  if not isinstance(body,bytes):body=json.dumps(body,ensure_ascii=False).encode()
  self.send_response(status);self.headers_safe(ctype,editor);self.send_header('Content-Length',str(len(body)));self.end_headers()
  if self.command!='HEAD':self.wfile.write(body)
 def requestcheck(self,write=False):
  if not self.validhost():raise EditError('This editor accepts only its own local address.',403)
  origin=self.headers.get('Origin')
  if not write and not urlsplit(self.path).path.startswith('/editor/api/') and self.headers.get('Sec-Fetch-Mode')=='navigate' and self.headers.get('Sec-Fetch-Dest')=='document':return
  if origin and origin not in self.server.origins:raise EditError('This request did not come from the local editor.',403)
  if self.headers.get('Sec-Fetch-Site') in ('cross-site','same-site'):raise EditError('Open the editor directly in your browser.',403)
  if write:
   if origin not in self.server.origins:raise EditError('Reload the local editor before saving.',403)
   if not hmac.compare_digest(self.headers.get('X-Editor-Token',''),TOKEN):raise EditError('The editor restarted. Reload this tab; your unsaved edits remain in this browser.',403)
   if self.headers.get_content_type()!='application/json':raise EditError('Use the local editor to save content.',415)
 def do_GET(self):
  try:
   self.requestcheck();p=urlsplit(self.path).path
   if p=='/editor/health':return self.send(200,{'app':'alexandra-local-editor','project':PROJECT})
   if p=='/editor/api/session':
    if self.headers.get('X-Editor-Client')!='local-editor':raise EditError('Open the local editor to continue.',403)
    
    with LOCK:return self.send(200,{'token':TOKEN,'manifest':metadata_summary(),'cv_revision':version([CV])})
   if p.startswith('/editor/api/item/'):
    if self.headers.get('X-Editor-Client')!='local-editor':raise EditError('Open the editor first.',403)
    bits=p.split('/')
    with LOCK:return self.send(200,getitem(bits[-2],bits[-1]))
   if p.startswith('/editor/draft/'):
    key=p.rsplit('/',1)[-1]
    with LOCK:
     d,_,_=post(key);output=BUILD/(uuid.uuid4().hex+'-draft-view')
     try:
      runbuild(output,key);page=(output/d['slug'].lstrip('/')/'index.html').read_bytes()
     finally:
      if output.exists():shutil.rmtree(output)
    return self.send(200,page,'text/html; charset=utf-8',False)
   if p in ('/editor','/editor/') or p in ('/editor/app.js','/editor/editor.css'):
    filename='index.html' if p in ('/editor','/editor/') else p.rsplit('/',1)[-1];f=UI/filename;return self.send(200,f.read_bytes(),mimetypes.guess_type(f.name)[0]+'; charset=utf-8')
   if p.startswith('/editor/'):raise EditError('This local editor page was not found.',404)
   f=(DIST/unquote(p).lstrip('/')).resolve()
   if DIST.resolve()!=f and DIST.resolve() not in f.parents:raise EditError('This path is not available.',404)
   if f.is_dir():f=f/'index.html'
   if not f.is_file():return self.send(404,(DIST/'404.html').read_bytes(),'text/html; charset=utf-8',False)
   return self.send(200,f.read_bytes(),mimetypes.guess_type(f.name)[0] or 'application/octet-stream',False)
  except EditError as e:self.send(e.status,{'error':str(e)})
  except Exception:self.send(500,{'error':'This item could not be loaded. Reload the editor; your saved files are unchanged.'})
 def do_HEAD(self):self.do_GET()
 def do_POST(self):
  try:
   self.requestcheck(True);endpoint=urlsplit(self.path).path
   if endpoint not in ('/editor/api/save','/editor/api/restore','/editor/api/cv'):raise EditError('This editing action is not available.',404)
   limit=12*1024*1024 if endpoint.endswith('/cv') else 1024*1024
   try:length=int(self.headers.get('Content-Length','-1'))
   except ValueError:raise EditError('The save request is incomplete.')
   if length<1 or length>limit or self.headers.get('Transfer-Encoding'):raise EditError('The save request is too large or incomplete.',413)
   try:data=json.loads(self.rfile.read(length))
   except (ValueError,UnicodeError):raise EditError('The save could not be read. Your existing content has not changed.')
   if not isinstance(data,dict):raise EditError('Use the editor form to save.')
   operation=data.get('request_id','')
   if not re.fullmatch(r'[a-f0-9-]{20,60}',operation):raise EditError('Reload the editor before saving.')
   with LOCK:
    if operation in RESULTS:return self.send(200,RESULTS[operation])
    result=saveitem(data) if endpoint.endswith('/save') else restore(data) if endpoint.endswith('/restore') else uploadcv(data)
    RESULTS[operation]=result
    if len(RESULTS)>128:RESULTS.pop(next(iter(RESULTS)))
   self.send(200,result)
  except EditError as e:self.send(e.status,{'error':str(e)})
  except Exception as e:self.send(500,{'error':'The save did not complete. Your previous content was protected; reload before trying again.'})
 def do_OPTIONS(self):self.send(405,{'error':'Cross-origin editing is not supported.'})
 def do_PUT(self):self.send(405,{'error':'Use the editor save form.'})
 def do_DELETE(self):self.send(405,{'error':'Deleting content is not supported. Use recoverable history.'})
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8767);args=parser.parse_args()
 if not 1024<=args.port<=65535:raise SystemExit('Choose a local port above 1023.')
 # Recover interrupted multi-file saves before serving any editor requests.
 for recordpath in sorted(HISTORY.glob('*.json')):
  record=json.loads(recordpath.read_text())
  if not record.get('committed') and not record.get('rolled_back'):
   for rel,value in record['before'].items():write(rel,base64.b64decode(value) if value is not None else None)
   record['rolled_back']=True;record['recovered_after_interrupt']=True;recordpath.write_text(json.dumps(record))
 startup=BUILD/(uuid.uuid4().hex+'-startup');runbuild(startup);swap(startup)
 server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.daemon_threads=True;server.hosts={'127.0.0.1:'+str(args.port),'localhost:'+str(args.port)};server.origins={'http://'+x for x in server.hosts}
 print('Local editor: http://127.0.0.1:'+str(args.port)+'/editor/',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
if __name__=='__main__':main()
