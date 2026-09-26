from pathlib import Path
import html,json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
OUT=ROOT/'dist'
DATA=json.loads((ROOT/'projects.json').read_text(encoding='utf8'))
# Both local and CI builds must use the documented source revisions.
for project in DATA:
 source=BASE/project['slug']
 expected=project.get('source_sha','')
 if not re.fullmatch(r'[0-9a-f]{40}',expected):
  raise ValueError(f"Missing full source SHA: {project['slug']}")
 actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
 if actual!=expected:
  raise RuntimeError(f"{project['slug']}: expected {expected}, found {actual}. Check out the pinned revision before building.")
 dirty=subprocess.check_output(['git','status','--porcelain','--','docs','screenshots'],cwd=source,text=True).strip()
 if dirty:
  raise RuntimeError(f"Uncommitted documentation or screenshots: {project['slug']}")
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
shutil.copy2(ROOT/'style.css',OUT/'style.css')
(OUT/'.nojekyll').write_text('')
def E(s):return html.escape(str(s),quote=True)
def inline(s):
 s=E(s)
 s=re.sub(r'`([^`]+)`',lambda m:'<code>'+m.group(1)+'</code>',s)
 s=re.sub(r'\[([^]]+)\]\((https?://[^)]+)\)',lambda m:'<a href="'+E(m.group(2))+'">'+m.group(1)+'</a>',s)
 return s
def markdown(s):
 result=[];para=[];listed=False;code=False
 def flush():
  nonlocal para
  if para:result.append('<p>'+inline(' '.join(para))+'</p>');para=[]
 for line in s.splitlines():
  if line.startswith('```'):
   flush()
   if listed:result.append('</ul>');listed=False
   result.append('<pre><code>' if not code else '</code></pre>');code=not code;continue
  if code:result.append(E(line)+'\n');continue
  if not line.strip():flush();continue
  if line.startswith('#'):
   flush()
   if listed:result.append('</ul>');listed=False
   n=min(len(line)-len(line.lstrip('#')),4);result.append(f'<h{n}>'+inline(line[n:].strip())+f'</h{n}>');continue
  if line.startswith('- '):
   flush()
   if not listed:result.append('<ul>');listed=True
   result.append('<li>'+inline(line[2:])+'</li>');continue
  if listed:result.append('</ul>');listed=False
  para.append(line.strip())
 flush()
 if listed:result.append('</ul>')
 return '\n'.join(result)
def layout(title,body):
 return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#09121e"><meta name="description" content="직접 플레이하고 제작 과정을 읽을 수 있는 다섯 게임의 포트폴리오"><link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%2309121e'/%3E%3Cpath d='M13 22h38v20H13z' fill='none' stroke='%2388ceea' stroke-width='5'/%3E%3Cpath d='M23 28v10m-5-5h10' stroke='%23f3ca72' stroke-width='4'/%3E%3Ccircle cx='41' cy='30' r='3' fill='%23f3ca72'/%3E%3C/svg%3E"><link rel="stylesheet" href="{('../../' if title!='게임 전시관' else '')}style.css"><title>{E(title)} · Vibe Game Portfolio</title></head><body><a class="skip" href="#main">본문으로 건너뛰기</a><header class="top shell"><a class="brand" href="{('../../' if title!='게임 전시관' else './')}">VIBE <span>GAME</span> PORTFOLIO</a><nav aria-label="주 메뉴"><a href="{('../../' if title!='게임 전시관' else '#games')}">게임</a><a href="https://github.com/seowooyoo2014">GitHub</a></nav></header><main id="main" class="shell">{body}</main><footer class="footer"><div class="shell">seowooyoo2014 · 플레이 가능한 게임과 제작 기록</div></footer></body></html>'''
def card(p):
 slug=p['slug'];src=BASE/slug;im=p.get('image','');image=f'<img src="images/{slug}/{Path(im).name}" alt="{E(p["title"])} 실제 화면" loading="lazy">' if im and (src/im).exists() else f'<span class="monogram">{E(p["title"])}</span>'
 return f'<article class="card" style="--accent:{p["color"]}"><div class="visual">{image}</div><div class="copy"><div class="type">{E(p["genre"])}</div><h2>{E(p["title"])}</h2><p>{E(p["desc"])}</p><div class="effort"><span>만들며 집중한 것</span><p>{E(p["effort"])}</p></div><div class="tech">{E(p["tech"])}</div><div class="actions"><a class="btn primary" href="https://seowooyoo2014.github.io/{slug}/">플레이</a><a class="btn" href="games/{slug}/">제작 기록</a></div></div></article>'
intro='<div class="intro"><div><div class="eyebrow">YOUNG CREATOR · GROWING THROUGH GAMES</div><h1>상상한 세계를,<br>플레이할 수 있도록.</h1><p>게임을 좋아하는 초등학생의 바이브 코딩 포트폴리오. 아이디어를 실행하고, 고치고, 더 큰 세계로 발전시키는 과정을 기록합니다.</p></div><span class="count">05 GAMES · 05 STORIES</span></div>'
(OUT/'index.html').write_text(layout('게임 전시관',intro+'<div id="games" class="grid">'+''.join(card(p) for p in DATA)+'</div>'),encoding='utf8')
for p in DATA:
 slug=p['slug'];src=BASE/slug;dest=OUT/'games'/slug;dest.mkdir(parents=True)
 sections=[];toc=[]
 docs=[('gameplay','게임 방법'),('running','실행 방법'),('technology','사용 기술'),('architecture','아키텍처'),('history','발전 히스토리'),('verification','검증 결과'),('assets','에셋과 출처')]
 for key,label in docs:
  f=src/'docs'/f'{key}.md'
  if not f.exists():raise FileNotFoundError(f)
  body=markdown(f.read_text(encoding='utf8'))
  body=re.sub(r'^<h1>.*?</h1>', '',body,count=1)
  body=re.sub(r'<(/?)h([2-4])>',lambda m:'<'+m[1]+'h'+str(int(m[2])+1)+'>',body)
  sections.append(f'<section id="{key}"><h2>{label}</h2>{body}</section>');toc.append(f'<a href="#{key}">{label}</a>')
 images=[]
 for f in sorted((src/'docs'/'screenshots').glob('*')) if (src/'docs'/'screenshots').exists() else []:
  if f.suffix.lower() in ['.png','.jpg','.jpeg','.webp']:
   images.append(f)
 for f in sorted((src/'screenshots').glob('*')) if (src/'screenshots').exists() else []:
  if f.suffix.lower() in ['.png','.jpg','.jpeg','.webp']:images.append(f)
 if p.get('image'):
  hero=src/p['image']
  if hero.exists():
   images=[hero]+[x for x in images if x != hero]
 image_dir=OUT/'images'/slug;image_dir.mkdir(parents=True,exist_ok=True)
 # The portfolio uses a bounded, real-game screenshot selection, never render intermediates.
 selected=[]
 for f in images:
  if f.name not in [x.name for x in selected]:selected.append(f)
  if len(selected)>=3:break
 for f in selected:shutil.copy2(f,image_dir/f.name)
 if p.get('image') and (src/p['image']).exists() and (image_dir/Path(p['image']).name).exists():hero=f'<img class="hero-shot" src="../../images/{slug}/{Path(p["image"]).name}" alt="{E(p["title"])} 게임 화면">'
 elif selected:hero=f'<img class="hero-shot" src="../../images/{slug}/{selected[0].name}" alt="{E(p["title"])} 게임 화면">'
 else:hero=''
 captions={'current-battle':'1장 전투','current-chapters':'챕터 선택','current-victory':'전투 결과','current-menu':'시작 화면','current-captain':'선장 선택','current-gameplay':'항해 플레이','current-performance':'성능 모드','current-city':'도시 플레이','current-select':'레이서 선택','current-race':'경주 플레이','current-story':'이야기 도입','current-cutscene':'도입 컷신'}
 gallery='<div class="gallery">'+''.join(f'<figure><a href="../../images/{slug}/{f.name}"><img src="../../images/{slug}/{f.name}" alt="{E(p["title"])} — {E(captions.get(f.stem,"실제 플레이 화면"))}" loading="lazy"></a><figcaption>{E(captions.get(f.stem,"실제 플레이 화면"))}</figcaption></figure>' for i,f in enumerate(selected))+'</div>' if selected else ''
 head=f'<div class="detail-header" style="--accent:{p["color"]}"><a class="back" href="../../">← 전체 게임</a><div class="eyebrow">{E(p["genre"])}</div><h1>{E(p["title"])}</h1><p>{E(p["desc"])}</p><div class="actions"><a class="btn primary" href="https://seowooyoo2014.github.io/{slug}/">바로 플레이</a><a class="btn" href="https://github.com/seowooyoo2014/{slug}">GitHub 저장소</a></div></div>'
 focus=f'<section class="project-focus"><div><div class="eyebrow">THE CONCEPT</div><h2>어떤 게임을 만들었나요?</h2><p>{E(p["concept"])}</p></div><div><div class="eyebrow">THE PROCESS</div><h2>어디에 힘을 쏟았나요?</h2><p>{E(p["effort"])}</p><p class="muted">아래 제작 기록은 남아 있는 코드와 기획 문서를 근거로 정리했습니다.</p></div></section>'
 body=head+hero+focus+gallery+'<div class="detail-layout"><nav class="toc" aria-label="이 게임 문서 목차">'+''.join(toc)+'</nav><div class="content">'+''.join(sections)+'</div></div>'
 (dest/'index.html').write_text(layout(p['title'],body),encoding='utf8')
print('built',len(DATA),'games')
