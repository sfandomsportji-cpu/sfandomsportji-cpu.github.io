from pathlib import Path
p = Path('tools/temp_mlb_20260906_build.py')
src = p.read_text(encoding='utf-8')
src = src.replace('candidates.sort(reverse=True)', 'candidates.sort(key=lambda x: x[:5], reverse=True)')
exec(compile(src, str(p), 'exec'))
