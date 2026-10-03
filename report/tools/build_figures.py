"""Read frozen evidence; write only Reporter figures, chart data and QA records.

ReportLab supplies vector graphics; Pillow renders the identical primitives as PNG.
No model calls, rescoring writes, credential access or business-code edits.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
from collections import Counter
from html import escape
from PIL import Image, ImageDraw, ImageFont
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, Polygon, String
from reportlab.graphics import renderSVG
from reportlab.lib.colors import HexColor

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'report' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
NAVY, MUTED, GRID = '#172D43', '#526477', '#DFE7EF'
BLUE, TEAL, AMBER, RED = '#2766AD', '#148374', '#BD7409', '#B54D50'
LIGHT, WHITE = '#F4F7FB', '#FFFFFF'
SCALE = 2
font_root = Path('C:/Windows/Fonts')


class Figure:
    def __init__(self, name, height=400):
        self.name, self.w, self.h = name, 1200, height
        self.svg = Drawing(self.w, self.h)
        self.png = Image.new('RGB', (self.w*SCALE, self.h*SCALE), WHITE)
        self.draw = ImageDraw.Draw(self.png)
        self.boxes = []
        self.tex = []
        self.rect(0, 0, self.w, self.h, WHITE)

    def color(self, color):
        rgb=tuple(int(color[i:i+2],16)/255 for i in (1,3,5))
        return r'\color[rgb]{'+','.join(f'{v:.4f}' for v in rgb)+'}'

    def rect(self, x, y, w, h, fill, stroke=None):
        self.tex.append(r'\put'+f'({x:.3f},{self.h-y-h:.3f})'+'{'+self.color(fill)+r'\rule{'+f'{w:.3f}pt'+'}{'+f'{h:.3f}pt'+'}}')
        if stroke:
            self.line(x,y,x+w,y,stroke); self.line(x,y+h,x+w,y+h,stroke)
            self.line(x,y,x,y+h,stroke); self.line(x+w,y,x+w,y+h,stroke)
        self.svg.add(Rect(x, self.h-y-h, w, h, fillColor=HexColor(fill),
                          strokeColor=HexColor(stroke) if stroke else None))
        self.draw.rectangle((x*SCALE, y*SCALE, (x+w)*SCALE, (y+h)*SCALE),
                            fill=fill, outline=stroke, width=SCALE)

    def line(self, x1, y1, x2, y2, color=GRID, width=1):
        if y1==y2:
            self.tex.append(r'\put'+f'({min(x1,x2):.3f},{self.h-y1-width/2:.3f})'+'{'+self.color(color)+r'\rule{'+f'{abs(x2-x1):.3f}pt'+'}{'+f'{width:.3f}pt'+'}}')
        elif x1==x2:
            self.tex.append(r'\put'+f'({x1-width/2:.3f},{self.h-max(y1,y2):.3f})'+'{'+self.color(color)+r'\rule{'+f'{width:.3f}pt'+'}{'+f'{abs(y2-y1):.3f}pt'+'}}')
        else:
            self.tex.append(r'\put(0,0){'+self.color(color)+r'\linethickness{'+f'{width}pt'+r'}\qbezier'+
                f'({x1:.3f},{self.h-y1:.3f})({(x1+x2)/2:.3f},{self.h-(y1+y2)/2:.3f})({x2:.3f},{self.h-y2:.3f})'+'}')
        self.svg.add(Line(x1, self.h-y1, x2, self.h-y2, strokeColor=HexColor(color), strokeWidth=width))
        self.draw.line((x1*SCALE, y1*SCALE, x2*SCALE, y2*SCALE), fill=color, width=max(1,int(width*SCALE)))

    def circle(self, x, y, r, fill):
        self.tex.append(r'\put'+f'({x:.3f},{self.h-y:.3f})'+'{'+self.color(fill)+r'\circle*{'+f'{2*r:.3f}'+'}}')
        self.svg.add(Circle(x, self.h-y, r, fillColor=HexColor(fill), strokeColor=None))
        self.draw.ellipse(((x-r)*SCALE,(y-r)*SCALE,(x+r)*SCALE,(y+r)*SCALE), fill=fill)

    def text(self, x, y, value, size=16, color=NAVY, bold=False, anchor='start'):
        value = str(value)
        assert value.isascii(), value
        font = ImageFont.truetype(str(font_root / ('arialbd.ttf' if bold else 'arial.ttf')), size*SCALE)
        bounds = self.draw.textbbox((0,0), value, font=font)
        w = self.draw.textlength(value, font=font)/SCALE
        left = x if anchor=='start' else x-w if anchor=='end' else x-w/2
        self.boxes.append((left, y-size, left+w, y+4, value))
        self.draw.text((left*SCALE,y*SCALE),value,font=font,fill=color,anchor='ls')
        align={'start':'l','end':'r','middle':'c'}[anchor]
        self.tex.append(r'\put'+f'({x:.3f},{self.h-y:.3f})'+r'{\makebox(0,0)['+align+']{'+
            self.color(color)+r'\sffamily\fontsize{'+str(size)+'}{'+str(size+2)+r'}\selectfont '+
            (r'\bfseries ' if bold else '')+tex_escape(value)+'}}')
        self.svg.add(String(x,self.h-y,value,fontName='Helvetica-Bold' if bold else 'Helvetica',
                            fontSize=size,fillColor=HexColor(color),textAnchor=anchor))

    def arrow(self, x1,y1,x2,y2,color=BLUE):
        self.line(x1,y1,x2,y2,color,2)
        angle=math.atan2(y2-y1,x2-x1)
        pts=[(x2,y2),(x2-10*math.cos(angle-.5),y2-10*math.sin(angle-.5)),
             (x2-10*math.cos(angle+.5),y2-10*math.sin(angle+.5))]
        self.svg.add(Polygon([v for x,y in pts for v in (x,self.h-y)],fillColor=HexColor(color),strokeColor=None))
        self.draw.polygon([(x*SCALE,y*SCALE) for x,y in pts],fill=color)
        # Picture arrows use two short strokes, retaining the same direction.
        for x,y in pts[1:]:
            self.tex.append(r'\put(0,0){'+self.color(color)+r'\linethickness{2pt}\qbezier'+
                f'({x:.3f},{self.h-y:.3f})({(x+x2)/2:.3f},{self.h-(y+y2)/2:.3f})({x2:.3f},{self.h-y2:.3f})'+'}')

    def footer(self, lines):
        top=self.h-26*len(lines)-22
        self.line(44,top-18,1156,top-18)
        for i,line in enumerate(lines): self.text(44,top+i*26,line,13,color=MUTED)

    def save(self):
        # Rectangular label checks complement (not replace) required visual review.
        clipped=[t for x,y,r,b,t in self.boxes if x<0 or y<0 or r>self.w or b>self.h]
        overlaps=[]
        for i,a in enumerate(self.boxes):
            for b in self.boxes[i+1:]:
                if min(a[2],b[2])-max(a[0],b[0])>2 and min(a[3],b[3])-max(a[1],b[1])>2:
                    overlaps.append([a[4],b[4]])
        self.png.save(OUT/f'{self.name}.png')
        renderSVG.drawToFile(self.svg,str(OUT/f'{self.name}.svg'))
        panels[self.name]=r'\resizebox{\linewidth}{!}{\setlength{\unitlength}{1pt}\begin{picture}'+f'({self.w},{self.h})'+'\n'+'\n'.join(self.tex)+r'\end{picture}}'
        return {'figure':self.name,'clipped_labels':clipped,'overlapping_labels':overlaps}


def tex_escape(value):
    chars={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    return ''.join(chars.get(c,c) for c in value)

panels={}
def load(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))
def rows(path):
    with (ROOT/path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))


finalization=load('experiments/results/finalization.json')
bad=[f['path'] for f in finalization['files']
     if hashlib.sha256((ROOT/'experiments'/f['path']).read_bytes()).hexdigest()!=f['sha256']]
assert not bad, bad
bench=load('experiments/results/model-benchmark/summary.json')['arms']
bop=load('experiments/results/model-benchmark/operations.json')['by_arm']
bill=load('experiments/results/billing_clarification.json')
ab=load('experiments/results/ablation/summary.json')['arms']
aop=load('experiments/results/ablation/operations.json')['by_arm']
sem=load('experiments/results/ablation/semantic_summary.json')['arms']
data=[json.loads(x) for x in (ROOT/'experiments/data/frozen-core/dataset.jsonl').read_text(encoding='utf-8').splitlines()]
by_case={x['case_id']:x for x in data}
sr=rows('experiments/results/ablation/semantic_review.csv')


def passed(r):
    pred=json.loads(r['prediction'])
    case=by_case[r['case_id']]
    allowed=case.get('accepted_outcomes') or [{'status':case['gold']['status'],
        'action_count':int(r['expected_task_units'])}]
    joint=any(pred['status']==o['status'] and len(pred.get('actions',[]))==o['action_count'] for o in allowed)
    criteria=['ownership_currentness','commitment_faithful','deadline_correct','evidence_supports_meaning','review_appropriate']
    return (joint and all(r[c]!='no' for c in criteria) and
            int(r['matched_task_units'])==int(r['expected_task_units'])==int(r['proposed_task_units']))


for arm,s in sem.items():
    assert sum(passed(r) for r in sr if r['arm']==arm)==s['delivery_semantic_pass'],arm
qa=[]
chart_data={}

# Compact panels: no embedded title, narrative subtitle, source footer or scope note.
f=Figure('01_architecture',335)
def box(x,y,w,h,title,lines):
    f.rect(x,y,w,h,WHITE,NAVY);f.text(x+14,y+30,title,23,bold=True)
    for i,t in enumerate(lines):f.text(x+14,y+58+i*25,t,19)
box(25,20,330,103,'Normalize inputs',['Recipient, newest mail, thread','Declared source inventory'])
box(435,20,330,103,'Plan and read',['Select necessary sources','Bounded reading / segmentation'])
box(845,20,330,103,'Extract and validate',['Current tasks, dates, evidence','Contract and original-text checks'])
f.arrow(355,71,435,71,NAVY);f.arrow(765,71,845,71,NAVY)
box(845,216,330,103,'Repair allowance',['At most once per email','Validate the corrected output'])
f.arrow(953,123,953,216,AMBER);f.arrow(1068,216,1068,123,AMBER)
f.text(975,166,'Repairable',18);f.text(975,190,'failure',18)
box(25,216,330,103,'Reviewed output',['action / no_action / needs_review','Human accept / edit / reject'])
box(435,216,330,103,'Calendar draft',['Accepted task + reviewed date','Confirm saved fields / export'])
f.line(878,123,878,144,NAVY,2);f.line(878,144,190,144,NAVY,2);f.arrow(190,144,190,216,NAVY)
f.text(340,183,'Valid result or review fallback',19)
f.arrow(355,267,435,267,NAVY)
qa.append(f.save())

# Layer ownership: concise functional table; deployment states belong in prose.
f=Figure('06_scope_and_ownership',275)
for x,t in [(25,'Layer'),(330,'Sourcing'),(660,'Rationale / responsibility')]:f.text(x,29,t,23,bold=True)
f.line(25,42,1175,42,NAVY,1.5)
layers=[('Interface and serving','Own local CLI / review UI','Direct task review and confirmation'),
        ('Orchestration and policy','Own Python workflow','Control source budgets and repair'),
        ('Foundation model','Rent via OpenRouter','Avoid training; depend on API behavior'),
        ('Data and parsing','Own references; reuse parsers','Traceable sources and portable inputs'),
        ('Evaluation and logs','Own metrics and traces','Inspect outputs, failures and spend')]
for i,(a,b,c) in enumerate(layers):
    y=79+i*43
    f.text(25,y,a,21);f.text(330,y,b,20);f.text(660,y,c,20)
f.line(25,267,1175,267,NAVY,1.5)
qa.append(f.save())

# Provenance: labeled bars, with shared cumulative count axes and no commentary.
f=Figure('05_data_provenance',290)
origins=Counter(x['origin'] for x in data);status=Counter(x['gold']['status'] for x in data)
for y,title,items,colors in [(30,'Input origins',[('MailEx',33),('Enron export',1),('Authored JSON',19),('Authored EML',7)],[BLUE,AMBER,TEAL,RED]),
        (138,'Reference status',[(k,status[k]) for k in ['action','no_action','needs_review']],[BLUE,TEAL,AMBER])]:
    f.text(25,y+26,title,22,bold=True);x=250;w=920
    for (label,n),color in zip(items,colors):
        size=w*n/60;f.rect(x,y,size,32,color)
        if size>50:f.text(x+size/2,y+24,n,21,color=WHITE,anchor='middle')
        x+=size
    for i,((label,n),color) in enumerate(zip(items,colors)):
        lx=250+i*230;f.rect(lx,y+45,14,11,color);f.text(lx+23,y+57,f'{label}: {n}',18)
    f.line(250,y+76,1170,y+76,NAVY)
    for tick in [0,15,30,45,60]:
        x=250+w*tick/60;f.line(x,y+76,x,y+81,NAVY);f.text(x,y+101,tick,18,anchor='middle')
f.text(710,282,'Cumulative case count',20,anchor='middle')
sources=[s for x in data for s in x['email']['external_sources']]
chart_data['provenance']={'origins':dict(origins),'statuses':dict(status),'external_case_count':sum(bool(x['email']['external_sources']) for x in data),'external_source_entries':len(sources)}
assert chart_data['provenance']['external_case_count']==17 and len(sources)==20
qa.append(f.save())

# Benchmark: three aligned panels, zero-based axes and direct numeric labels.
mapping=rows('experiments/results/model-benchmark/model_mapping.csv')
f=Figure('02_model_comparison',475)
f.text(300,25,'a  Matched cases (/60)',22,bold=True)
f.text(655,25,'b  Case time (s)',22,bold=True)
f.text(963,25,'c  Subtotal (USD)',20,bold=True)
f.rect(300,44,16,10,BLUE);f.text(325,56,'Strict',18)
f.rect(413,44,16,10,TEAL);f.text(438,56,'Permitted',18)
f.circle(663,50,4,BLUE);f.text(679,56,'Median',18)
f.circle(778,50,4,AMBER);f.text(794,56,'95th percentile',18)
xs=[300,655,963];ws=[235,235,200];maxima=[60,60,.6]
for i,row in enumerate(mapping):
    arm=row['internal_arm_id'];y=94+i*52;s=bench[arm];o=bop[arm]
    f.text(25,y+7,row['model_name'],21)
    for off,key,color in [(-12,'strict_status_match',BLUE),(10,'accepted_joint_status_count_match',TEAL)]:
        v=s[key];f.rect(300,y+off,235*v/60,10,color);f.text(552,y+off+10,v,17)
    p50=o['case_wall_ms']['p50']/1000;p95=o['case_wall_ms']['p95']/1000
    f.line(655+235*p50/60,y,655+235*p95/60,y,NAVY,1.5)
    f.circle(655+235*p50/60,y,4,BLUE);f.circle(655+235*p95/60,y,4,AMBER)
    f.text(655,y+28,f'{p50:.2f} / {p95:.2f}',18)
    cost=bill['generation_verified_cost_by_completed_arm_usd'][arm]
    f.rect(963,y-8,200*cost/.6,14,TEAL);f.text(963,y+28,f'{cost:.6f}',18)
    chart_data.setdefault('benchmark',[]).append({'model':row['model_name'],'strict':s['strict_status_match'],'permitted_joint':s['accepted_joint_status_count_match'],'p50_seconds':p50,'p95_seconds':p95,'verified_fees_usd':cost})
for x,w,m,ticks in zip(xs,ws,maxima,[[0,30,60],[0,30,60],[0,.3,.6]]):
    f.line(x,407,x+w,407,NAVY)
    for v in ticks:
        xx=x+w*v/m;f.line(xx,407,xx,413,NAVY);f.text(xx,437,f'{v:g}',18,anchor='middle')
qa.append(f.save())

# Ablations: same-case semantic comparisons, n printed beside each condition.
f=Figure('03_paired_context',410)
f.rect(25,15,18,12,BLUE);f.text(52,28,'Full workflow (same cases)',20)
f.rect(435,15,18,12,AMBER);f.text(462,28,'Comparison condition',20)
conditions=[('prompt_only','Single prompt',60),('no_thread','No thread',12),('no_external','No external reading',17),('read_all','Read all sources',17)]
for col,(suffix,name) in enumerate([('m01','GPT-6 Luna'),('m06','Claude Sonnet 5.5')]):
    x=290+col*470;w=290
    f.text(x,65,name,23,bold=True)
    for i,(prefix,label,n) in enumerate(conditions):
        cond=[r for r in sr if r['arm']==f'{prefix}_{suffix}'];ids={r['case_id'] for r in cond}
        full=[r for r in sr if r['arm']==f'full_{suffix}' and r['case_id'] in ids]
        assert len(cond)==len(full)==n
        a,b=sum(passed(r) for r in full),sum(passed(r) for r in cond);y=91+i*64
        if col==0:f.text(25,y+19,label,21);f.text(25,y+43,f'n = {n}',18)
        f.rect(x,y,w*a/n,15,BLUE);f.text(x+w+12,y+14,f'{a}/{n}',19)
        f.rect(x,y+25,w*b/n,15,AMBER);f.text(x+w+12,y+39,f'{b}/{n}',19)
        chart_data.setdefault('paired_semantic',[]).append({'model':name,'condition':label,'n':n,'full':a,'comparison':b})
    f.line(x,350,x+w,350,NAVY)
    for v in [0,25,50,75,100]:
        xx=x+w*v/100;f.line(xx,350,xx,355,NAVY);f.text(xx,379,v,18,anchor='middle')
    f.text(x+w/2,406,'Semantic delivery (%)',20,anchor='middle')
qa.append(f.save())

# Metric table: no explanatory callout or deployment disclaimer inside artwork.
f=Figure('04_metrics_and_cost',325)
for x,t in [(25,'Model / condition'),(353,'Strict'),(490,'Semantic'),(637,'Tasks'),(791,'Median (s)'),(970,'Fee (USD)')]:f.text(x,29,t,23,bold=True)
f.line(25,44,1175,44,NAVY,1.5)
for i,(suffix,name,prefix,label) in enumerate([(s,n,p,l) for s,n in [('m01','Luna'),('m06','Sonnet')]
        for p,l in [('full','Full'),('prompt_only','Single prompt'),('no_repair','No repair')]]):
    arm=f'{prefix}_{suffix}';s=sem[arm];o=aop[arm];y=78+i*43
    f.text(25,y,f'{name} / {label}',21)
    f.text(353,y,f'{ab[arm]["strict_status_match"]}/60',21)
    f.text(490,y,f'{s["delivery_semantic_pass"]}/60',21)
    f.text(637,y,f'{s["matched_tasks"]}/{s["expected_tasks"]}',21)
    f.text(791,y,f'{o["case_wall_ms"]["p50"]/1000:.2f}',21)
    f.text(970,y,f'{o["known_billed_cost_usd"]:.6f}',21)
    if i==2:f.line(25,y+14,1175,y+14,GRID)
f.line(25,319,1175,319,NAVY,1.5)
qa.append(f.save())

(OUT/'chart_data.json').write_text(json.dumps(chart_data,indent=2),encoding='utf-8')
(OUT/'panel_code.json').write_text(json.dumps(panels,indent=2),encoding='utf-8')
tex_path=ROOT/'report/FINAL_REPORT.tex'
if tex_path.exists():
    source=tex_path.read_text(encoding='utf-8')
    macros='\n'.join(r'\expandafter\def\csname panel:'+k+r'\endcsname{'+v+'}' for k,v in panels.items())
    source=re.sub(r'% BEGIN GENERATED PANELS.*?% END GENERATED PANELS',lambda _: '% BEGIN GENERATED PANELS\n'+macros+'\n% END GENERATED PANELS',source,flags=re.S)
    tex_path.write_text(source,encoding='utf-8')
result={'frozen_files_checked':len(finalization['files']),'hash_mismatches':bad,'figure_label_checks':qa,
        'visual_review':'Pending: open each final PNG and the compiled document pages after generation.'}
(ROOT/'report/QA_RESULTS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))

