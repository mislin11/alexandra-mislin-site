#!/usr/bin/env python3
"""Create an editable draft; nothing is published or sent anywhere."""
import argparse,json,re
from pathlib import Path
from datetime import datetime,timezone
from html import escape
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--title',required=True);p.add_argument('--date',required=True,help='YYYY-MM-DD');p.add_argument('--slug',required=True,help='Path after /workwelldiplomacy/, e.g. my-new-post');a=p.parse_args()
slug=a.slug.strip('/');
if not re.fullmatch('[a-z0-9]+(?:[/-][a-z0-9]+)*',slug):p.error('Use lowercase letters, numbers, hyphens and optional date path separators.')
date=datetime.fromisoformat(a.date).replace(tzinfo=timezone.utc);key=slug.replace('/','-');folder=ROOT/'content/posts';meta=folder/(key+'.json');body=folder/(key+'.html')
if meta.exists() or body.exists():p.error('That post already exists; choose another slug.')
data={'title':a.title,'slug':'/workwelldiplomacy/'+slug,'draft':True,'published_at':date.isoformat(),'updated_at':date.isoformat(),'publishOn':int(date.timestamp()*1000),'updatedOn':int(date.timestamp()*1000),'author':'Alexandra Mislin','tags':[],'categories':[],'excerpt_html':'<p>Write a short summary here.</p>','image':'','image_alt':'','body_file':body.name}
meta.write_text(json.dumps(data,indent=2)+'\n');body.write_text('<!-- Replace the paragraphs below. Change draft to false in the JSON when ready. -->\n<p>Write your opening paragraph here.</p>\n<h2>A section heading</h2>\n<p>Continue your article. Add a <a href="https://example.com">descriptive link</a> when useful.</p>\n');print('Draft created:',meta,'and',body);print('It is excluded from the build until draft is false. No live site changes were made.')
