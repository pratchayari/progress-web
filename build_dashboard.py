import json
from datetime import datetime
from pathlib import Path
BASE=Path(__file__).resolve().parent
roster=json.loads((BASE/'students.json').read_text(encoding='utf-8'))['students']
students=[];total_files=reviewed_twice=three_rounds=0
for profile in roster:
    sid=profile['student_id'];paths=sorted((BASE/sid).glob('week??-round??.json'))
    if not paths:continue
    total_files+=len(paths);reviewed_twice+=len(paths)>=2;three_rounds+=len(paths)>=3
    latest=json.loads(paths[-1].read_text(encoding='utf-8'));passed=sum(i.get('status')=='pass' for i in latest.get('items',[]));total=len(latest.get('items',[])) or 20
    students.append({'student_id':sid,'github_owner':profile.get('github_owner',''),'latest_round':latest.get('review_round',len(paths)),'latest_pass':passed,'latest_total':total,'latest_percent':round(passed*100/total),'review_count':len(paths)})
payload={'generated_at':datetime.now().strftime('%d/%m/%Y %H:%M'),'summary':{'total_students':len(students),'reviewed_twice':reviewed_twice,'three_rounds':three_rounds,'total_review_files':total_files},'students':students}
(BASE/'dashboard-data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(f"Dashboard data: {len(students)} students, {total_files} review files")
