import re,sys,glob,os
from pathlib import Path
root=Path('.')
files=[Path(p) for p in ['README.md','CONTRIBUTING.md','testenv/README.md','eval/EXPERIMENTS.md']]+sorted(Path('docs').rglob('*.md'))+sorted(Path('rules').rglob('*.md'))
bad=0
def skip(t): return t.startswith(('http://','https://','#','mailto:')) or 'runs/' in t or '<' in t or '*' in t
for f in files:
    if not f.exists(): continue
    txt=f.read_text()
    in_code=False
    for n,line in enumerate(txt.splitlines(),1):
        if line.startswith('```'): in_code=not in_code; continue
        if in_code: continue
        # headings
        m=re.match(r'#+\s+(.*)',line)
        if m:
            h=re.sub(r'`[^`]*`','',m.group(1))
            if not re.search(r'[一-鿿]',h) and len(re.findall(r'[A-Za-z]{2,}',h))>=2:
                print(f'{f}:{n} HEADING {line}'); bad+=1
        for t in re.findall(r'\]\(([^)\s]+)\)',line):
            if skip(t): continue
            p=t.split('#')[0]
            if not p: continue
            if not (f.parent/p).exists(): print(f'{f}:{n} LINK {t}'); bad+=1
        for t in re.findall(r'`([^`]+)`',line):
            if skip(t) or ' ' in t or '/' not in t: continue
            if not re.match(r'^[\w./-]+$',t): continue
            p=t.rstrip('/')
            if not ((root/p).exists() or (f.parent/p).exists()): print(f'{f}:{n} PATH {t}'); bad+=1
print('bad=',bad)
sys.exit(1 if bad else 0)
