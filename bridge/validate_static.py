#!/usr/bin/env python3
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BLOG = ROOT / "blog"
FORBIDDEN = [r"fetch\s*\(", r"api\.github\.com", r"raw\.githubusercontent\.com", r"blogger\.googleapis\.com", r"element\.innerHTML\s*=", r"<script\b", r"javascript:", r"\son\w+\s*="]

def check(p):
    t=p.read_text(encoding='utf-8'); errs=[]; listing=p.resolve()==(BLOG/'index.html').resolve(); min_text=20 if listing else 120
    tests={"doctype":"<!doctype html" in t.lower(),"title":bool(re.search(r'<title>.+?</title>',t,re.I|re.S)),"h1":bool(re.search(r'<h1\b',t,re.I)),"canonical":bool(re.search(r'rel=["\']canonical["\']',t,re.I)),"text":len(re.sub(r'<[^>]+>',' ',t).strip())>min_text}
    errs += [k for k,v in tests.items() if not v]
    for pat in FORBIDDEN:
        if re.search(pat,t,re.I): errs.append('forbidden:'+pat)
    return errs

def main():
    files=list(BLOG.rglob('*.html'))
    if not files: print('BLOCKED: no generated HTML'); return 1
    bad=0
    for p in files:
        e=check(p); print(('PASS' if not e else 'FAIL'),p,('' if not e else ' | '+','.join(e))); bad += bool(e)
    return 1 if bad else 0
if __name__=='__main__': raise SystemExit(main())
