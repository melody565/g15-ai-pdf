import hashlib,hmac,json,os,re,secrets,sys
from datetime import datetime,timezone
from http import cookies
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from evaluator import evaluate

GROUP_NAME=os.environ['GROUP_NAME'];SECRET=os.environ['APP_SECRET'].encode()
DB=dict(host=os.environ['POSTGRES_HOST'],port=os.environ.get('POSTGRES_PORT','5432'),dbname=os.environ['POSTGRES_DB'],user=os.environ['POSTGRES_USER'],password=os.environ['POSTGRES_PASSWORD'])
TABLES={'users':'module_0309_users','departments':'module_0309_departments','permission_groups':'module_0309_permission_groups','program_groups':'module_0309_program_groups','programs':'module_0309_programs','data_groups':'module_0309_data_groups','records':'module_0309_records','rules':'module_0309_rules'}
EDITABLE={'users':{'display_name','clearance','enabled'},'departments':{'name'},'permission_groups':{'name','description','enabled'},'program_groups':{'name','enabled'},'programs':{'name','enabled'},'data_groups':{'name'},'records':{'title','classification'},'rules':{'name','active'}}

def utcnow():return datetime.now(timezone.utc)
def serial(v):
    if isinstance(v,datetime):return v.isoformat()
    raise TypeError
def owner_from(handler):
    trusted=handler.headers.get('X-Authenticated-User') or handler.headers.get('Remote-User')
    if trusted:
        return hashlib.sha256((GROUP_NAME+':'+trusted).encode()).hexdigest()[:32],None,'proxy_identity'
    jar=cookies.SimpleCookie(handler.headers.get('Cookie',''));raw=jar.get('ai_demo_0309')
    if raw:
        try:
            ident,sig=raw.value.split('.',1);expected=hmac.new(SECRET,ident.encode(),hashlib.sha256).hexdigest()
            if re.fullmatch(r'[0-9a-f]{32}',ident) and hmac.compare_digest(sig,expected):return ident,None,'signed_teaching_session'
        except ValueError:pass
    ident=secrets.token_hex(16);sig=hmac.new(SECRET,ident.encode(),hashlib.sha256).hexdigest()
    return ident,f'ai_demo_0309={ident}.{sig}; Path=/api/03.09; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000','signed_teaching_session'
def ensure_session(con,owner,source):con.execute('INSERT INTO module_0309_sessions(id,owner_source) VALUES(%s,%s) ON CONFLICT(id) DO UPDATE SET last_seen_at=NOW(),owner_source=EXCLUDED.owner_source',(owner,source))
def audit(con,owner,event,entity,eid=None,detail=None):con.execute('INSERT INTO module_0309_audit_events(session_id,event_type,entity_type,entity_id,detail) VALUES(%s,%s,%s,%s,%s)',(owner,event,entity,eid,Jsonb(detail or {})))
def public(row):return dict(row) if row else None
def rows(con,sql,args):return [dict(x) for x in con.execute(sql,args).fetchall()]

def seed(con,owner):
    for table in ('module_0309_audit_events','module_0309_rules','module_0309_records','module_0309_user_data_groups','module_0309_data_groups','module_0309_program_group_members','module_0309_programs','module_0309_program_groups','module_0309_user_permission_groups','module_0309_permission_groups','module_0309_users','module_0309_departments'):
        con.execute(f'DELETE FROM {table} WHERE session_id=%s',(owner,))
    dept={}
    for name,parent in [('總部',None),('產品部','總部'),('產品實驗室','產品部'),('財務部','總部')]:
        dept[name]=con.execute('INSERT INTO module_0309_departments(session_id,name,parent_id) VALUES(%s,%s,%s) RETURNING id',(owner,name,dept.get(parent))).fetchone()['id']
    users={}
    for username,name,dep,level,enabled in [('alice','虛構－艾莉絲','總部',3,True),('bob','虛構－柏勃','產品部',2,True),('carol','虛構－卡蘿','產品實驗室',4,True),('dave','虛構－大衛','財務部',2,True),('erin','虛構－艾琳','總部',1,False),('frank','虛構－法蘭克','產品部',3,True)]:
        users[username]=con.execute('INSERT INTO module_0309_users(session_id,username,display_name,department_id,clearance,enabled) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id',(owner,username,name,dept[dep],level,enabled)).fetchone()['id']
    pgs={}
    for name,desc in [('分析人員','查閱與分析'),('編輯人員','資料維護'),('核准人員','流程核准'),('稽核人員','唯讀稽核')]:pgs[name]=con.execute('INSERT INTO module_0309_permission_groups(session_id,name,description) VALUES(%s,%s,%s) RETURNING id',(owner,name,desc)).fetchone()['id']
    for u,g in [('bob','分析人員'),('carol','編輯人員'),('carol','核准人員'),('dave','稽核人員'),('frank','分析人員'),('frank','編輯人員')]:con.execute('INSERT INTO module_0309_user_permission_groups VALUES(%s,%s,%s)',(owner,users[u],pgs[g]))
    prog_groups={}
    for name in ('營運工具','治理工具'):prog_groups[name]=con.execute('INSERT INTO module_0309_program_groups(session_id,name) VALUES(%s,%s) RETURNING id',(owner,name)).fetchone()['id']
    programs={}
    for code,name,manager,group in [('CRM','客戶管理','alice','營運工具'),('DOC','文件中心','bob','營運工具'),('BUD','預算中心','dave','治理工具'),('APR','核准中心','carol','治理工具')]:
        programs[code]=con.execute('INSERT INTO module_0309_programs(session_id,code,name,owner_user_id) VALUES(%s,%s,%s,%s) RETURNING id',(owner,code,name,users[manager])).fetchone()['id'];con.execute('INSERT INTO module_0309_program_group_members VALUES(%s,%s,%s)',(owner,prog_groups[group],programs[code]))
    dgs={}
    for name in ('專案 Alpha','專案 Beta','跨部門共用'):dgs[name]=con.execute('INSERT INTO module_0309_data_groups(session_id,name) VALUES(%s,%s) RETURNING id',(owner,name)).fetchone()['id']
    for u,g in [('alice','專案 Alpha'),('alice','跨部門共用'),('bob','專案 Alpha'),('carol','專案 Beta'),('carol','跨部門共用'),('dave','跨部門共用')]:con.execute('INSERT INTO module_0309_user_data_groups VALUES(%s,%s,%s)',(owner,users[u],dgs[g]))
    records=[]
    specs=[('A-本人草稿','alice','總部','專案 Alpha',1),('A-機密規劃','alice','總部','專案 Alpha',3),('B-產品需求','bob','產品部','專案 Alpha',2),('B-個人筆記','bob','產品部',None,1),('C-實驗紀錄','carol','產品實驗室','專案 Beta',3),('C-高機密模型','carol','產品實驗室','專案 Beta',4),('D-預算草稿','dave','財務部','跨部門共用',2),('D-付款清單','dave','財務部',None,2),('E-停用測試','erin','總部',None,1),('F-產品報告','frank','產品部','跨部門共用',2),('跨部門公告','alice','總部','跨部門共用',1),('子部門彙整','carol','產品實驗室','跨部門共用',2)]
    for title,u,d,g,c in specs:records.append(con.execute('INSERT INTO module_0309_records(session_id,title,owner_user_id,department_id,data_group_id,classification) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id',(owner,title,users[u],dept[d],dgs.get(g),c)).fetchone()['id'])
    def rule(name,st,sid,rt,rid,action,effect,scope,scope_ref=None,maxc=4,active=True,start=None,end=None):
        con.execute('''INSERT INTO module_0309_rules(session_id,name,subject_type,subject_id,resource_type,resource_id,action,effect,scope,scope_ref,max_classification,active,starts_at,ends_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',(owner,name,st,sid,rt,rid,action,effect,scope,scope_ref,maxc,active,start,end))
    rule('Alice 直接進 CRM','user',users['alice'],'program',programs['CRM'],'enter','allow','all')
    rule('Alice 本人查閱','user',users['alice'],'program',programs['CRM'],'view','allow','self',maxc=3)
    rule('分析群組進營運工具','permission_group',pgs['分析人員'],'program_group',prog_groups['營運工具'],'enter','allow','all')
    rule('分析群組部門含子部門查閱','permission_group',pgs['分析人員'],'program_group',prog_groups['營運工具'],'view','allow','department_tree',maxc=3)
    rule('Bob 直接進文件中心','user',users['bob'],'program',programs['DOC'],'enter','allow','all')
    rule('編輯群組進文件中心','permission_group',pgs['編輯人員'],'program',programs['DOC'],'enter','allow','all')
    rule('編輯群組同部門修改','permission_group',pgs['編輯人員'],'program',programs['DOC'],'edit','allow','department',maxc=3)
    rule('核准群組進治理工具','permission_group',pgs['核准人員'],'program_group',prog_groups['治理工具'],'enter','allow','all')
    rule('核准群組子部門核准','permission_group',pgs['核准人員'],'program_group',prog_groups['治理工具'],'approve','allow','department_tree',maxc=4)
    rule('稽核群組進治理工具','permission_group',pgs['稽核人員'],'program_group',prog_groups['治理工具'],'enter','allow','all')
    rule('稽核共用群組查閱','permission_group',pgs['稽核人員'],'program_group',prog_groups['治理工具'],'view','allow','data_group',dgs['跨部門共用'],2)
    rule('Frank 跨部門共用查閱','user',users['frank'],'program',programs['CRM'],'view','allow','data_group',dgs['跨部門共用'],3)
    rule('Frank CRM 進入','user',users['frank'],'program',programs['CRM'],'enter','allow','all')
    rule('拒絕 Frank 檢視 CRM','user',users['frank'],'program',programs['CRM'],'view','deny','all')
    rule('過期直接授權','user',users['dave'],'program',programs['CRM'],'view','allow','all',maxc=4,end='2025-01-01T00:00:00Z')
    rule('尚未生效授權','user',users['dave'],'program',programs['CRM'],'enter','allow','all',start='2099-01-01T00:00:00Z')
    rule('停用規則','user',users['alice'],'program',programs['DOC'],'edit','allow','all',active=False)
    rule('全部範圍不繞過分級','user',users['bob'],'program',programs['DOC'],'view','allow','all',maxc=4)
    audit(con,owner,'demo_initialized','sandbox',None,{'counts':{'users':6,'departments':4,'permissionGroups':4,'programGroups':2,'programs':4,'dataGroups':3,'records':12,'rules':18}})

class Handler(BaseHTTPRequestHandler):
    def send_json(self,status,payload,cookie=None):
        body=json.dumps(payload,ensure_ascii=False,default=serial).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(body)
    def body(self):
        n=int(self.headers.get('Content-Length','0'))
        if n>100000:raise ValueError('payload too large')
        return json.loads(self.rfile.read(n) or b'{}')
    def route(self):return urlparse(self.path).path
    def context(self):return owner_from(self)
    def do_GET(self):
        path=self.route()
        if path=='/healthz':return self.send_json(200,{'status':'ok','module':'03.09','group':GROUP_NAME,'python':sys.version.split()[0]})
        if path!='/api/03.09/state':return self.send_json(404,{'message':'not found'})
        owner,cookie,source=self.context()
        try:
            with psycopg.connect(**DB,row_factory=dict_row) as con:
                ensure_session(con,owner,source);payload={'sandbox':owner[:8],'ownerSource':source}
                for key,table in TABLES.items():payload[key]=rows(con,f'SELECT * FROM {table} WHERE session_id=%s AND deleted_at IS NULL ORDER BY id',(owner,))
                payload['userPermissionGroups']=rows(con,'SELECT * FROM module_0309_user_permission_groups WHERE session_id=%s',(owner,));payload['programGroupMembers']=rows(con,'SELECT * FROM module_0309_program_group_members WHERE session_id=%s',(owner,));payload['userDataGroups']=rows(con,'SELECT * FROM module_0309_user_data_groups WHERE session_id=%s',(owner,));payload['events']=rows(con,'SELECT * FROM module_0309_audit_events WHERE session_id=%s ORDER BY created_at DESC LIMIT 150',(owner,))
                return self.send_json(200,payload,cookie)
        except Exception as exc:print(type(exc).__name__,exc,flush=True);return self.send_json(503,{'message':'PostgreSQL 暫時無法讀取。'},cookie)
    def do_POST(self):
        path=self.route();owner,cookie,source=self.context()
        try:data=self.body()
        except Exception:return self.send_json(400,{'message':'要求格式不正確。'},cookie)
        try:
            with psycopg.connect(**DB,row_factory=dict_row) as con:
                ensure_session(con,owner,source)
                if path=='/api/03.09/demo/initialize':seed(con,owner);return self.send_json(201,{'message':'已建立 03.09 教學示範資料；未修改正式帳號或角色。'},cookie)
                if path=='/api/03.09/simulate':return self.simulate(con,owner,data,cookie)
                match=re.fullmatch(r'/api/03\.09/entities/([a-z_]+)/(\d+)',path)
                if match:return self.edit_entity(con,owner,match.group(1),int(match.group(2)),data,cookie)
        except Exception as exc:print(type(exc).__name__,exc,flush=True);return self.send_json(503,{'message':'伺服器或 PostgreSQL 操作失敗，未宣稱成功。'},cookie)
        return self.send_json(404,{'message':'not found'},cookie)
    def do_DELETE(self):
        owner,cookie,source=self.context();match=re.fullmatch(r'/api/03\.09/entities/([a-z_]+)/(\d+)',self.route())
        if not match:return self.send_json(404,{'message':'not found'},cookie)
        try:
            with psycopg.connect(**DB,row_factory=dict_row) as con:
                ensure_session(con,owner,source);kind,eid=match.group(1),int(match.group(2));table=TABLES.get(kind)
                if not table:return self.send_json(404,{'message':'未知資料類型。'},cookie)
                deps={'users':['module_0309_user_permission_groups','module_0309_user_data_groups','module_0309_records','module_0309_programs'],'permission_groups':['module_0309_user_permission_groups'],'program_groups':['module_0309_program_group_members'],'programs':['module_0309_program_group_members'],'data_groups':['module_0309_user_data_groups','module_0309_records']}.get(kind,[])
                for dep in deps:
                    column={'module_0309_user_permission_groups':'user_id' if kind=='users' else 'group_id','module_0309_user_data_groups':'user_id' if kind=='users' else 'data_group_id','module_0309_records':'owner_user_id' if kind=='users' else 'data_group_id','module_0309_programs':'owner_user_id','module_0309_program_group_members':'program_group_id' if kind=='program_groups' else 'program_id'}[dep]
                    if con.execute(f'SELECT 1 FROM {dep} WHERE session_id=%s AND {column}=%s LIMIT 1',(owner,eid)).fetchone():return self.send_json(409,{'message':f'此資料仍被 {dep} 相依，已阻擋刪除並保留資料。'},cookie)
                row=con.execute(f'UPDATE {table} SET deleted_at=NOW(),version=version+1 WHERE id=%s AND session_id=%s AND deleted_at IS NULL RETURNING id',(eid,owner)).fetchone()
                if not row:return self.send_json(404,{'message':'資料不存在或不屬於目前沙盒。'},cookie)
                audit(con,owner,'soft_deleted',kind,eid);return self.send_json(200,{'message':'已軟刪除並保留稽核紀錄。'},cookie)
        except Exception:return self.send_json(503,{'message':'刪除失敗，未變更資料。'},cookie)
    def edit_entity(self,con,owner,kind,eid,data,cookie):
        table=TABLES.get(kind);allowed=EDITABLE.get(kind)
        if not table or not allowed:return self.send_json(404,{'message':'未知資料類型。'},cookie)
        row=con.execute(f'SELECT * FROM {table} WHERE id=%s AND session_id=%s AND deleted_at IS NULL FOR UPDATE',(eid,owner)).fetchone()
        if not row:return self.send_json(404,{'message':'資料不存在或不可跨沙盒引用。'},cookie)
        if int(data.get('version',0))!=row['version']:return self.send_json(409,{'message':'版本衝突，未覆寫資料；請重新讀取。'},cookie)
        changes={k:v for k,v in data.items() if k in allowed}
        if not changes:return self.send_json(422,{'message':'沒有可更新欄位。'},cookie)
        if 'clearance' in changes:changes['clearance']=int(changes['clearance'])
        sets=','.join(f'{k}=%s' for k in changes);params=list(changes.values())+[eid,owner,row['version']]
        updated=con.execute(f'UPDATE {table} SET {sets},version=version+1 WHERE id=%s AND session_id=%s AND version=%s RETURNING *',params).fetchone()
        if not updated:return self.send_json(409,{'message':'版本衝突，未覆寫資料。'},cookie)
        audit(con,owner,'entity_updated',kind,eid,{'fields':list(changes)});return self.send_json(200,{'message':'教學沙盒資料已更新。','item':public(updated)},cookie)
    def simulate(self,con,owner,data,cookie):
        try:uid,pid,rid=int(data['userId']),int(data['programId']),int(data['recordId']);action=data['action']
        except Exception:return self.send_json(422,{'message':'請選擇使用者、程式、資料及動作。'},cookie)
        if action not in ('view','edit','approve'):return self.send_json(422,{'message':'模擬動作不合法。'},cookie)
        actor=con.execute('SELECT * FROM module_0309_users WHERE id=%s AND session_id=%s',(uid,owner)).fetchone();program=con.execute('SELECT * FROM module_0309_programs WHERE id=%s AND session_id=%s',(pid,owner)).fetchone();record=con.execute('SELECT * FROM module_0309_records WHERE id=%s AND session_id=%s',(rid,owner)).fetchone()
        if not actor or not program or not record:return self.send_json(404,{'message':'資料不存在或 ID 不屬於目前沙盒。'},cookie)
        pgs={x['group_id'] for x in con.execute('SELECT group_id FROM module_0309_user_permission_groups WHERE session_id=%s AND user_id=%s',(owner,uid))};prog_groups={x['program_group_id'] for x in con.execute('SELECT program_group_id FROM module_0309_program_group_members WHERE session_id=%s AND program_id=%s',(owner,pid))};dgs={x['data_group_id'] for x in con.execute('SELECT data_group_id FROM module_0309_user_data_groups WHERE session_id=%s AND user_id=%s',(owner,uid))}
        descendants={actor['department_id']};pending=[actor['department_id']]
        while pending:
            children=[x['id'] for x in con.execute('SELECT id FROM module_0309_departments WHERE session_id=%s AND parent_id=ANY(%s) AND deleted_at IS NULL',(owner,pending))];descendants.update(children);pending=children
        rules=rows(con,'SELECT * FROM module_0309_rules WHERE session_id=%s',(owner,));result=evaluate(dict(actor),dict(program),dict(record),action,rules,pgs,prog_groups,descendants,dgs)
        result.update({'actor':actor['display_name'],'program':program['name'],'record':record['title'],'action':action,'recomputedAt':utcnow(),'programOwnerIsPermission':False})
        audit(con,owner,'access_allowed' if result['allowed'] else 'access_denied','simulation',None,{k:v for k,v in result.items() if k!='recomputedAt'})
        return self.send_json(200,result,cookie)
    def log_message(self,format,*args):return

ThreadingHTTPServer(('0.0.0.0',8000),Handler).serve_forever()
