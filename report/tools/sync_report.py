"""Derive linked Markdown and counts from the sole editable .tex source."""
from pathlib import Path
import re
import json
ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'report/FINAL_REPORT.tex').read_text(encoding='utf-8')
content=source.split('% BEGIN EDITORIAL CONTENT')[1].split('% END EDITORIAL CONTENT')[0]
refs={k:i for i,k in enumerate(re.findall(r'\\bibitem\{([^}]+)\}',content),1)}
labels={}
fig=tab=0
for kind,name,caption,label in re.findall(r'\\report(figure|table)\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',content):
    if kind=='figure': fig+=1; labels[label]=('Figure',fig)
    else: tab+=1; labels[label]=('Table',tab)
attribution=re.search(r'\\newcommand\{\\reportattribution\}\{\\par\\smallskip\{\\footnotesize\s*(.*?)\\par\}\}',source,re.S).group(1)

def clean(t,markdown=False):
    t=t.replace(r'\reportattribution',attribution)
    t=re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}',lambda m:f'[{m[2]}]({m[1]})' if markdown else m[2],t)
    t=re.sub(r'\\hyperref\[([^]]+)\]\{([^}]+)\}',lambda m:f'[{m[2]}](#{m[1].replace(":","-")})' if markdown else m[2],t)
    t=re.sub(r'\\cite\{([^}]+)\}',lambda m:', '.join(f'[{refs[k]}](#ref-{k})' if markdown else f'[{refs[k]}]' for k in m[1].split(',')),t)
    t=re.sub(r'\\ref\{([^}]+)\}',lambda m:str(labels[m[1]][1]),t)
    t=re.sub(r'\\reportsection\{([^}]+)\}\{([^}]+)\}',lambda m:f'<a id="{m[2].replace(":","-")}"></a>\n\n## {m[1]}' if markdown else m[1],t)
    t=re.sub(r'\\reporttitle\{([^}]+)\}',lambda m:(f'![NTU Singapore](assets/ntu_template_logo.png)\n\n# {m[1]}\n\nPE6201 - Individual course project report' if markdown else f'{m[1]}\nPE6201 - Individual course project report'),t)
    t=re.sub(r'\\bibitem\{([^}]+)\}',lambda m:f'<a id="ref-{m[1]}"></a>\n\n[{refs[m[1]]}]' if markdown else f'[{refs[m[1]]}]',t)
    t=re.sub(r'\\renewcommand\{[^}]+\}\{[^}]+\}','',t)
    t=re.sub(r'\\setlength\{[^}]+\}\{[^}]+\}','',t)
    t=re.sub(r'\\addcontentsline\{[^}]+\}\{[^}]+\}\{[^}]+\}','',t)
    t=re.sub(r'\\begin\{thebibliography\}\{[^}]+\}','\n\n## References\n' if markdown else '\nReferences\n',t)
    t=re.sub(r'\\begin\{[^}]+\}|\\end\{[^}]+\}','',t)
    t=re.sub(r'\\(?:Large|bfseries|begingroup|small|endgroup|phantomsection|raggedright)\b','',t)
    return t.replace(r'\_','_').replace(r'\%','%').replace('--','-').replace('~',' ')

counted=re.sub(r'\\report(?:figure|table)\{[^}]+\}\{[^}]+\}\{[^}]+\}','',content)
body=clean(counted)
assert not re.search(r'\\[A-Za-z]+',body),'Unsupported manuscript command in word count'

def panel(m):
    kind,name,caption,label=m.groups()
    prefix,number=labels[label]
    anchor=f'<a id="{label.replace(":","-")}"></a>'
    image=f'![{prefix} {number}](figures/{name}.png)'
    title=f'*{prefix} {number}. {caption}*'
    return anchor+'\n\n'+('\n\n'.join([title,image]) if kind=='table' else '\n\n'.join([image,title]))

md=content
for label,(kind,number) in labels.items():
    md=md.replace(kind+r'~\ref{'+label+'}',f'[{kind} {number}](#{label.replace(":","-")})')
md=re.sub(r'\\report(figure|table)\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',panel,md)
md=clean(md,markdown=True)
md=re.sub(r'\n{3,}','\n\n',md).strip()+'\n'
assert not re.search(r'\\[A-Za-z]+',md),'Unsupported manuscript command in Markdown'
(ROOT/'report/FINAL_REPORT.md').write_text(md,encoding='utf-8')
counts={'whitespace_including_title_headings_references':len(body.split()),'conservative_lexical_including_title_headings_references':len(re.findall(r'[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*',body)),'figure_and_table_captions_excluded':'Owner-confirmed graphics exclusion; references, title metadata and template attribution included.'}
assert max(v for v in counts.values() if isinstance(v,int))<=1200
p=ROOT/'report/QA_RESULTS.json';q=json.loads(p.read_text(encoding='utf-8'))
q['word_counts']=counts
q['source']='FINAL_REPORT.tex is the editable source; FINAL_REPORT.md is its generated review rendering.'
q['references']={'count':len(refs),'keys':list(refs),'all_cited':set(refs)==set(re.findall(r'\\cite\{([^}]+)\}',content+attribution))}
q['visual_review']['status']='pending after NTU styling and citation update'
p.write_text(json.dumps(q,indent=2),encoding='utf-8')
print(json.dumps(counts,indent=2))
