#!/usr/bin/env python3
"""Build the portable website using Python 3.9+ and its standard library only."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import quote,urlsplit,unquote
from html.parser import HTMLParser
import json,re,html,shutil,os,hashlib,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];CONTENT=ROOT/'content';DIST=Path(os.environ.get('SITE_OUTPUT_DIR',str(ROOT/'dist'))).resolve()
if DIST!=ROOT/'dist' and ROOT/'.local-editor/builds' not in DIST.parents:raise SystemExit('Build output must be dist/ or an editor staging folder.')
site=json.loads((CONTENT/'site.json').read_text());base=os.environ.get('SITE_BASE_PATH','').rstrip('/')
if base and not re.fullmatch(r'/[A-Za-z0-9_-]+',base):raise SystemExit('Invalid site base path.')
origin=os.environ.get('SITE_ORIGIN',site['canonical_origin']).rstrip('/')+base
style_version=hashlib.sha256((ROOT/'public/assets/site.css').read_bytes()).hexdigest()[:12]
# dist/ is generated output owned by this build; editable source is never removed.
if DIST.exists():shutil.rmtree(DIST)
shutil.copytree(ROOT/'public',DIST)
posts=[]
for f in (CONTENT/'posts').glob('*.json'):
 p=json.loads(f.read_text());
 if p.get('draft',False) and f.stem!=os.environ.get('SITE_PREVIEW_DRAFT_ID'):continue
 p['body_html']=(f.parent/p['body_file']).read_text();posts.append(p)
posts.sort(key=lambda p:p['publishOn'],reverse=True)
routes={};redirects=[]
def read(name):return (CONTENT/'pages'/(name+'.html')).read_text()
def esc(s):return html.escape(str(s),quote=True)
def mainheading(fragment,label):
 m=re.search(r'<h([1-3])(?:\s[^>]*)?>(.*?)</h\1>',fragment,re.S)
 if not m:return '<h1 class="visually-hidden">'+esc(label)+'</h1>'+fragment
 return fragment[:m.start()]+'<h1>'+m.group(2)+'</h1>'+fragment[m.end():]
def date(p):return datetime.fromisoformat(p['published_at']).strftime('%B %d, %Y').replace(' 0',' ')
def navigation(active,mobile=False):
 links=''.join('<a href="'+esc(n['path'])+'"'+(' aria-current="page"' if active==n['path'] else '')+'>'+esc(n['label'])+'</a>' for n in site['navigation'])
 if mobile:return '<details class="mobile-navigation"><summary>Menu</summary><nav aria-label="Mobile navigation">'+links+'</nav></details>'
 return '<nav class="desktop-navigation" aria-label="Primary navigation">'+links+'</nav>'
def layout(title,body,path,kind='',description=None,noindex=False,extra_head=''):
 canonical=origin+path;description=description or site['description']
 # Backup-only annotations stay in maintenance source, never in visitor-facing link tooltips.
 body=body.replace(' title="Original reference unavailable at the 30 October 2026 backup; see reference link notes"','')
 return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>'''+esc(title if path=='/' else title+' — '+site['name'])+'''</title><meta name="description" content="'''+esc(description)+'''">
<link rel="canonical" href="'''+esc(canonical)+'''"><meta property="og:title" content="'''+esc(title)+'''"><meta property="og:description" content="'''+esc(description)+'''"><meta property="og:type" content="website"><meta property="og:url" content="'''+esc(canonical)+'''"><meta property="og:image" content="'''+esc(origin+site['portrait'])+'''">
'''+('<meta name="robots" content="noindex,follow">' if noindex else '')+'''<link rel="alternate" type="application/rss+xml" title="WorkWell Diplomacy" href="/feed.xml">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/site.css?v='''+style_version+'''"><link rel="preload" as="font" type="font/woff2" href="/assets/fonts/source-sans-3-roman.woff2" crossorigin>
<script src="/assets/site.js" defer></script>'''+extra_head+'''</head>
<body><a class="skip-link" href="#main">Skip to content</a><div class="site-shell"><header class="site-header"><a class="site-title" href="/">'''+esc(site['name'])+'''</a>'''+navigation(path)+navigation(path,True)+'''</header>
<main id="main" class="'''+esc(kind)+'''">'''+body+'''</main>
<footer class="site-footer"><span>© Alexandra Mislin</span></footer></div></body></html>'''
def write(path,title,body,kind='',**kw):
 p=DIST/path.lstrip('/')/'index.html';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(layout(title,body,path,kind,**kw));routes[path]={'file':str(p.relative_to(DIST)),'title':title,'kind':kind}
def redirect(path,target,reason):
 target=target if target.startswith('/') else '/'+target
 write(path,'Page moved','<h1>Page moved</h1><p><a href="'+esc(target)+'">Continue to '+esc(site['name'])+'</a>.</p>',noindex=True,extra_head='<meta http-equiv="refresh" content="0;url='+esc(target)+'">');redirects.append({'from':path,'to':target,'reason':reason})
# Core editorial pages.
write('/',site['name'],'<h1 class="visually-hidden">Alexandra Mislin</h1><section class="home-introduction"><aside class="home-portrait"><img src="'+site['portrait']+'" alt="Alexandra Mislin" width="294" height="294" fetchpriority="high">'+read('home-cv')+'</aside><div>'+read('home-introduction')+'</div></section><section class="home-news" aria-labelledby="news-title"><h2 id="news-title">What&#39;s New?</h2>'+read('home-news')+'</section>','home')
write('/research/','Research','<h1 class="visually-hidden">Research</h1>'+read('research'),'research editorial')
write('/about/','Teaching','<h1 class="visually-hidden">Teaching</h1>'+read('teaching'),'teaching editorial')
write('/press/','Press','<article class="right-column">'+mainheading(read('press'),'Press')+'</article>','post editorial press')
write('/contact/','Contact','<aside class="contact-portrait"><img src="'+site['contact_portrait']+'" alt="Alexandra Mislin" width="294" height="295"></aside><article class="right-column">'+mainheading(read('contact'),'Contact')+'</article>','sidebar-layout contact')
write('/speaking-workshops/','Speaking & Workshops',read('speaking-workshops'),'post editorial',description='I give talks and workshops on everyday negotiation, building trust, and gaining influence in complex organizational and social settings.')
# All published posts retain their original paths and millisecond publication timestamps.
for p in posts:
 schema={'@context':'https://schema.org','@type':'BlogPosting','headline':p['title'],'datePublished':p['published_at'],'dateModified':p['updated_at'],'author':{'@type':'Person','name':p['author']},'mainEntityOfPage':origin+p['slug']}
 if p['image']:schema['image']=origin+p['image']
 topics=[]
 for typ in ('categories','tags'):
  for t in p[typ]:topics.append('<a href="/workwelldiplomacy/'+('category' if typ=='categories' else 'tag')+'/'+quote(t.replace(' ','+'),safe='+')+'/">'+esc(t)+'</a>')
 body='<article><header class="post-heading"><h1>'+esc(p['title'])+'</h1><p><time datetime="'+esc(p['published_at'])+'">'+date(p)+'</time><span aria-hidden="true"> · </span>'+esc(p['author'])+'</p></header><div class="post-body">'+p['body_html']+'</div>'+('<p class="post-topics">'+', '.join(topics)+'</p>' if topics else '')+'<nav class="post-navigation" aria-label="Post navigation"><a href="/workwell-diplomacy/">← All WorkWell Diplomacy posts</a></nav></article>'
 write(p['slug'].rstrip('/')+'/',p['title'],body,'post',extra_head='<script type="application/ld+json">'+json.dumps(schema).replace('</','<\\/')+'</script>')
def postrow(p,hidden=False):
 picture='<img src="'+esc(p['image'])+'" alt="" width="210" height="140" loading="lazy">' if p['image'] else '<span class="typographic-thumbnail" aria-hidden="true">'+('Curiosity<br>in negotiation' if 'curiosity' in p['title'].lower() else 'WorkWell<br>Diplomacy')+'</span>'
 return '<article class="post-row" data-published="'+str(p['publishOn'])+'"'+(' hidden' if hidden else '')+'><a class="post-thumbnail" href="'+esc(p['slug'])+'/" aria-label="Read '+esc(p['title'])+'">'+picture+'</a><div><h2><a href="'+esc(p['slug'])+'/">'+esc(p['title'])+'</a></h2><div class="post-excerpt">'+p['excerpt_html']+'</div><time datetime="'+esc(p['published_at'])+'">'+date(p)+'</time></div></article>'
def listbody(selected,landing=False,page=1,filtered=False):
 banner='<div class="workwell-intro"><h1 class="visually-hidden">WorkWell Diplomacy: The Insider’s Guide to Thriving at Work</h1>'
 if site['workwell_banner']:banner+='<img class="workwell-banner" src="'+site['workwell_banner']+'" width="950" height="211" alt="The Insider’s Guide to Workplace Diplomacy…">'
 else:banner+='<h2>The Insider’s Guide to Workplace Diplomacy…</h2>'
 banner+=read('workwell-introduction')+'</div>'
 if landing:return banner+''.join(postrow(p) for p in selected)
 a=(page-1)*3;shown=selected[a:a+3]
 rows=''.join(postrow(p,hidden=(p not in shown)) for p in selected)
 pager='<nav class="pagination" aria-label="Blog pages">'+''.join('<a href="/workwelldiplomacy/'+('' if n==1 else 'page/'+str(n)+'/')+'"'+(' aria-current="page"' if n==page else '')+'>Page '+str(n)+'</a>' for n in range(1,(len(selected)+2)//3+1))+'</nav>' if not filtered else ''
 return (banner if not filtered else '')+'<section class="blog-list"'+(' data-legacy-pagination="true"' if not filtered and page==1 else '')+'>'+rows+'</section>'+pager
write('/workwell-diplomacy/','WorkWell Diplomacy',listbody(posts,True),'blog-landing')
write('/workwelldiplomacy/','WorkWell Diplomacy',listbody(posts),'blog-collection')
for n in range(2,(len(posts)+2)//3+1):write('/workwelldiplomacy/page/'+str(n)+'/','WorkWell Diplomacy — Page '+str(n),listbody(posts[(n-1)*3:n*3],True),'blog-collection')
filters={}
for p in posts:
 for typ in ('categories','tags'):
  for t in p[typ]:filters.setdefault((typ,t),[]).append(p)
for (typ,t),items in filters.items():
 route='/workwelldiplomacy/'+('category' if typ=='categories' else 'tag')+'/'+quote(t.replace(' ','+'),safe='+')+'/'
 write(unquote(route),t,'<h1 class="filter-heading">'+esc(t)+'</h1>'+listbody(items,True,filtered=True).replace('<h1 class="visually-hidden">WorkWell Diplomacy: The Insider’s Guide to Thriving at Work</h1>',''),'blog-filter',noindex=True)
# Preserve legacy author-owned PDF path, independently of Squarespace's /s/ download router.
legacy_pdf='/s/1-June-CNMC-Hospital-Grand-Rounds-flyer-Mislin.pdf';dest=DIST/legacy_pdf.lstrip('/');dest.parent.mkdir(exist_ok=True);shutil.copyfile(DIST/'assets/documents/negotiation-medical-professionals-2016.pdf',dest)
redirect('/home/','/','Original homepage alias')
redirect('/teaching/','/about/','Helpful teaching alias; original /about route remains canonical')
redirect('/read-me-om/','/','Squarespace template documentation excluded from the public rebuild; original preserved in backup')
# Host-neutral redirect plan; HTML fallbacks already work on a plain static server.
(DIST/'_redirects').write_text('\n'.join(x['from']+' '+x['to']+' 301' for x in redirects)+'\n')
if not os.environ.get('SITE_EDITOR_BUILD'):(ROOT/'docs/redirects.json').write_text(json.dumps(redirects,indent=2))
# Real 404 document, with a working return route.
(DIST/'404.html').write_text(layout('Page not found','<h1>Page not found</h1><p>The page may have moved. Visit <a href="/">the homepage</a> or <a href="/workwell-diplomacy/">WorkWell Diplomacy</a>.</p>','/404/','editorial',noindex=True))
# Portable discoverability files; no external build service is involved.
sitemap=ET.Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
for path,r in routes.items():
 if r['kind'] in ('blog-filter',) or path in [x['from'] for x in redirects]:continue
 item=ET.SubElement(sitemap,'url');ET.SubElement(item,'loc').text=origin+quote(path,safe='/+');
(DIST/'sitemap.xml').write_bytes(ET.tostring(sitemap,encoding='utf-8',xml_declaration=True))
(DIST/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+origin+'/sitemap.xml\n')
rss=ET.Element('rss',version='2.0');channel=ET.SubElement(rss,'channel')
for k,v in [('title','WorkWell Diplomacy — Alexandra Mislin'),('link',origin+'/workwell-diplomacy/'),('description',site['description'])]:ET.SubElement(channel,k).text=v
for p in posts:
 it=ET.SubElement(channel,'item');ET.SubElement(it,'title').text=p['title'];ET.SubElement(it,'link').text=origin+p['slug'];ET.SubElement(it,'guid',isPermaLink='true').text=origin+p['slug'];ET.SubElement(it,'description').text=p['excerpt_html'];ET.SubElement(it,'pubDate').text=datetime.fromisoformat(p['published_at']).strftime('%a, %d %b %Y %H:%M:%S +0000')
(DIST/'feed.xml').write_bytes(ET.tostring(rss,encoding='utf-8',xml_declaration=True))
if not os.environ.get('SITE_EDITOR_BUILD'):(ROOT/'docs/build-routes.json').write_text(json.dumps(routes,indent=2,ensure_ascii=False))
print('Built',len(routes),'page routes and',len(posts),'posts into',DIST)

# Project Pages uses a path prefix; custom domains and local preview use none.
if base:
 for f in DIST.rglob('*'):
  if f.is_file() and f.suffix in ('.html','.css'):
   value=f.read_text()
   value=re.sub(r'(\b(?:href|src|action)=[\"\'])/(?!/)',lambda m:m.group(1)+base+'/',value)
   value=re.sub(r'(url\([\"\']?)/(?!/)',lambda m:m.group(1)+base+'/',value)
   value=value.replace('url=/','url='+base+'/')
   f.write_text(value)
(DIST/'.nojekyll').write_text('')
