#!/usr/bin/env python3
"""Check the built site offline. Optional --url adds local HTTP route checks only."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin,unquote
from datetime import datetime
import argparse,json,re,hashlib,csv,collections,urllib.request,urllib.error,os,io
ROOT=Path(__file__).resolve().parents[1];DIST=Path(os.environ.get('SITE_OUTPUT_DIR',str(ROOT/'dist'))).resolve();errors=[];links=[];runtime=[];checked=0;ids={};changes=[]
parser=argparse.ArgumentParser();parser.add_argument('--url');parser.add_argument('--strict-migration',action='store_true');args=parser.parse_args()
class P(HTMLParser):
 def __init__(self,s):super().__init__(convert_charrefs=True);self.anchors=[];self.resources=[];self.ids=set();self.h1=0;self.feed(s)
 def handle_starttag(self,t,a):
  d=dict(a)
  if d.get('id'):self.ids.add(d['id'])
  if t=='h1':self.h1+=1
  if t=='a' and d.get('href'):self.anchors.append(d['href'])
  if t in ('script','img','source','iframe') and d.get('src'):self.resources.append(d['src'])
  if t=='link' and d.get('rel') in ('stylesheet','preload') and d.get('href'):self.resources.append(d['href'])
  if t=='img' and 'alt' not in d:errors.append('Missing alt attribute in '+str(current))
BASE=os.environ.get('SITE_BASE_PATH','').rstrip('/')
def target(path):
 if BASE and (path==BASE or path.startswith(BASE+'/')):path=path[len(BASE):] or '/'
 p=DIST/unquote(path).lstrip('/')
 if p.is_dir():p=p/'index.html'
 return p
htmlfiles=list(DIST.rglob('*.html'))
for current in htmlfiles:
 relative=current.relative_to(DIST);url='/' + str(relative.parent).replace('\\','/')+'/' if relative.parent!=Path('.') else '/'
 parsed=P(current.read_text());ids[str(current)]=parsed.ids
 if parsed.h1!=1:errors.append(str(relative)+': expected exactly one main h1, found '+str(parsed.h1))
 for v in parsed.anchors:links.append((url,v,str(relative)))
 for v in parsed.resources:
  runtime.append(v)
  if urlsplit(v).scheme or v.startswith('//'):errors.append('Remote runtime resource: '+v)
  elif not target(urlsplit(urljoin(url,v)).path).is_file():errors.append('Missing runtime resource: '+v)
 for v in parsed.anchors:
  p=urlsplit(urljoin(url,v))
  if p.scheme or p.netloc:continue
  checked+=1;q=target(p.path)
  if not q.is_file():errors.append(str(relative)+': broken internal link '+v)
  elif p.fragment and q.suffix=='.html':
   if str(q) not in ids:ids[str(q)]=P(q.read_text()).ids
   if p.fragment not in ids[str(q)]:errors.append(str(relative)+': missing anchor '+v)
 # No platform runtime, account traces or unpublished source caches may leak into output.
 if re.search(r'(?i)(squarespace[^<\s]*(?:\.js|\.css)|use\.typekit\.net|\.sqs-block|shoppingCart|websiteSettings|access_token|refresh_token|sk-[A-Za-z0-9]{25})',current.read_text()):errors.append('Disallowed platform/private data in '+str(relative))
css=(DIST/'assets/site.css').read_text()
for v in re.findall(r'url\([\'\"]?([^\)\'\"]+)',css):
 if urlsplit(v).scheme or not target(v).is_file():errors.append('Missing/remote CSS asset '+v)
# Every originally published personal path resolves; template documentation has an explicit redirect.
legacy=json.loads((ROOT/'content/legacy-routes.json').read_text())
for path in legacy:
 if not target(path).is_file():errors.append('Missing legacy route '+path)
# Visible article text and original dates remain exactly as imported from the verified archive.
class Text(HTMLParser):
 def __init__(self,s):super().__init__(convert_charrefs=True);self.out=[];self.feed(s)
 def handle_data(self,s):self.out.append(s)
def texthash(s):return hashlib.sha256(re.sub(r'\s+',' ',''.join(Text(s).out)).strip().encode()).hexdigest()
baseline=json.loads((ROOT/'docs/migration-baseline.json').read_text())
for key,file in [('home_introduction','home-introduction'),('home_news','home-news'),('research','research'),('teaching','teaching'),('press','press')]:
 if texthash((ROOT/'content/pages'/(file+'.html')).read_text())!=baseline[key]['visible_text_sha256']:changes.append('Source content changed from imported baseline: '+file)
for p in baseline['posts']:
 meta=next((json.loads(f.read_text()) for f in (ROOT/'content/posts').glob('*.json') if json.loads(f.read_text())['slug']==p['slug']),None)
 if not meta or meta['published_at']!=p['published_at'] or meta['title']!=p['title']:changes.append('Post metadata mismatch '+p['slug'])
 if texthash((ROOT/'content/posts'/p['body_file']).read_text())!=p['visible_text_sha256']:changes.append('Post body mismatch '+p['slug'])
 page=target(p['slug']).read_text()
 expected_date=p['published_at'] if args.strict_migration else (meta or p)['published_at']
 if '"datePublished": "'+expected_date+'"' not in page:errors.append('Missing publication date schema '+p['slug'])
# Public failures are recorded, not silently replaced.
gaps=json.loads((ROOT/'content/reference-link-status.json').read_text());assert len(gaps)==7
for gap in gaps:
 if gap['url'] not in [v for _,v,_ in links]:errors.append('Original inaccessible reference disappeared '+gap['url'])
# Inventory all external links; no repeated requests to access-denied targets.
external=collections.defaultdict(set)
for _,v,source in links:
 if urlsplit(v).scheme in ('http','https'):external[v].add(source)
with ((ROOT/'docs/external-links.csv').open('w',newline='') if not os.environ.get('SITE_EDITOR_BUILD') else io.StringIO()) as f:
 w=csv.writer(f);w.writerow(['url','status_at_backup','pages'])
 for v,sources in sorted(external.items()):
  g=next((x for x in gaps if x['url']==v),None);w.writerow([v,('HTTP '+str(g['status']) if g['status'] else 'TLS failure') if g else 'Not rechecked; preserved original link',' | '.join(sorted(sources))])
# Minimal asset-format checks catch common downloaded error placeholders.
for f in (DIST/'assets/fonts').glob('*'):
 if f.suffix in ('.woff2','.ttf') and f.read_bytes()[:4] not in (b'wOF2',b'\x00\x01\x00\x00',b'OTTO'):errors.append('Unreadable font header '+f.name)
for f in (DIST/'assets/documents').glob('*.pdf'):
 if not f.read_bytes().startswith(b'%PDF-'):errors.append('Invalid PDF '+f.name)

if args.strict_migration:errors.extend(changes)
http=[]
if args.url:
 for path in sorted(set(legacy+list(json.loads((ROOT/'docs/build-routes.json').read_text())))):
  url=args.url.rstrip('/')+urllib.parse.quote(path,safe='/+')
  try:
   with urllib.request.urlopen(url,timeout=10) as r:http.append({'route':path,'status':r.status})
  except Exception as e:errors.append('HTTP route failed '+path+': '+str(e))
 try:urllib.request.urlopen(args.url.rstrip('/')+'/definitely-not-a-page',timeout=10);errors.append('Missing route did not return 404')
 except urllib.error.HTTPError as e:
  if e.code!=404:errors.append('Unexpected missing-route status '+str(e.code))
report={'html_pages':len(htmlfiles),'legacy_routes_verified':len(legacy),'internal_links_checked':checked,'runtime_resources_checked':len(runtime),'remote_runtime_resources':sum(bool(urlsplit(x).scheme or x.startswith('//')) for x in runtime),'posts_preserved':len(baseline['posts']),'external_links_inventoried':len(external),'known_unavailable_external_downloads':len(gaps),'external_links_retried':False,'http_routes_checked':len(http),'content_changes_since_migration':changes,'strict_migration_check':args.strict_migration,'errors':errors}
report_path=Path(os.environ.get('SITE_CHECK_REPORT',str(ROOT/'docs/verification.json')));report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if errors:raise SystemExit(1)
