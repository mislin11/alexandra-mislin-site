#!/usr/bin/env python3
"""Local preview or optional container serving. No external services required."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from functools import partial
from pathlib import Path
import argparse,os,sys
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=int(os.environ.get('PORT','8766')));args=p.parse_args()
if not (ROOT/'dist/index.html').is_file():sys.exit('Run python3 tools/build.py first.')
REDIRECTS={}
for line in (ROOT/'dist/_redirects').read_text().splitlines():
 parts=line.split()
 if len(parts)==3:REDIRECTS[parts[0]]=parts[1]
class Handler(SimpleHTTPRequestHandler):
 def legacy_redirect(self):
  parsed=urlsplit(self.path);key=parsed.path.rstrip('/')+'/'
  if key not in REDIRECTS:return False
  target=REDIRECTS[key]+('?' +parsed.query if parsed.query else '')
  self.send_response(301);self.send_header('Location',target);self.send_header('Content-Length','0');self.end_headers();return True
 def do_GET(self):
  if not self.legacy_redirect():super().do_GET()
 def do_HEAD(self):
  if not self.legacy_redirect():super().do_HEAD()
 def end_headers(self):
  self.send_header('Cache-Control','no-cache');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
 def send_error(self,code,message=None,explain=None):
  if code==404:
   body=(ROOT/'dist/404.html').read_bytes();self.send_response(404);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers()
   if self.command!='HEAD':self.wfile.write(body)
  else:super().send_error(code,message,explain)
server=ThreadingHTTPServer((args.host,args.port),partial(Handler,directory=str(ROOT/'dist')))
print('Local preview: http://'+('127.0.0.1' if args.host=='0.0.0.0' else args.host)+':'+str(server.server_port)+'/',flush=True)
try:server.serve_forever()
except KeyboardInterrupt:pass
finally:server.server_close()
