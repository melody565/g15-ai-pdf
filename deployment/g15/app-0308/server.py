import hashlib,hmac,json,os,re,secrets,sys
from datetime import datetime,timedelta,timezone
from http import cookies
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from validation import password_hash,password_ok,validate_registration

GROUP_NAME=os.environ['GROUP_NAME'];SECRET=os.environ['APP_SECRET'].encode();DB=dict(host=os.environ['POSTGRES_HOST'],port=os.environ.get('POSTGRES_PORT','5432'),dbname=os.environ['POSTGRES_DB'],user=os.environ['POSTGRES_USER'],password=os.environ['POSTGRES_PASSWORD'])
DEMO_CODE='246810';MAX_ATTEMPTS=5;CODE_TTL_MINUTES=10;RESEND_SECONDS=30
def code_hash(application_id):return hmac.new(SECRET,f'{application_id}:{DEMO_CODE}'.encode(),hashlib.sha256).hexdigest()
def code_ok(application_id,value,encoded):return hmac.compare_digest(code_hash(application_id),encoded) and hmac.compare_digest(value,DEMO_CODE)
def utcnow():return datetime.now(timezone.utc)
def mask_destination(method,value):
    if method=='email':
        local,domain=value.split('@',1);return f'{local[:2]}***@{domain}'
    return f'{value[:4]}***{value[-3:]}'
def owner_from(handler):
    jar=cookies.SimpleCookie(handler.headers.get('Cookie',''));raw=jar.get('ai_demo_0308')
    if raw:
        try:
            ident,sig=raw.value.split('.',1);expected=hmac.new(SECRET,ident.encode(),hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig,expected) and re.fullmatch(r'[0-9a-f]{32}',ident):return ident,None
        except ValueError:pass
    ident=secrets.token_hex(16);sig=hmac.new(SECRET,ident.encode(),hashlib.sha256).hexdigest();return ident,f'ai_demo_0308={ident}.{sig}; Path=/api/03.08; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000'
def serial(value):
    if isinstance(value,(datetime,)):return value.isoformat()
    raise TypeError
def public(row):
    if not row:return None
    result=dict(row)
    for key in ('password_hash','code_hash','session_id'):result.pop(key,None)
    return result
def audit(con,session,entity_type,entity_id,event_type,detail=None):con.execute('INSERT INTO module_0308_audit_events(session_id,entity_type,entity_id,event_type,detail) VALUES(%s,%s,%s,%s,%s)',(session,entity_type,entity_id,event_type,Jsonb(detail or {})))
def ensure_session(con,session):con.execute('INSERT INTO module_0308_sessions(id) VALUES(%s) ON CONFLICT(id) DO UPDATE SET last_seen_at=NOW()',(session,))

class Handler(BaseHTTPRequestHandler):
    def send_json(self,status,payload,cookie=None):
        body=json.dumps(payload,ensure_ascii=False,default=serial).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(body)
    def body(self):
        size=int(self.headers.get('Content-Length','0'))
        if size>100000:raise ValueError('payload too large')
        return json.loads(self.rfile.read(size) or b'{}')
    def route(self):return urlparse(self.path).path
    def do_GET(self):
        path=self.route()
        if path=='/healthz':return self.send_json(200,{'status':'ok','group':GROUP_NAME,'module':'03.08','python':sys.version.split()[0]})
        if not path.startswith('/api/03.08/'):return self.send_json(404,{'message':'not found'})
        session,cookie=owner_from(self)
        try:
            with psycopg.connect(**DB,row_factory=dict_row) as con:
                ensure_session(con,session)
                if path=='/api/03.08/state':
                    apps=con.execute('SELECT * FROM module_0308_applications WHERE session_id=%s ORDER BY updated_at DESC',(session,)).fetchall();deliveries=con.execute('SELECT * FROM module_0308_deliveries WHERE session_id=%s ORDER BY created_at DESC',(session,)).fetchall();users=con.execute('SELECT * FROM module_0308_users WHERE session_id=%s ORDER BY updated_at DESC',(session,)).fetchall();events=con.execute('SELECT * FROM module_0308_audit_events WHERE session_id=%s ORDER BY created_at DESC LIMIT 100',(session,)).fetchall()
                    return self.send_json(200,{'sandbox':session[:8],'demoCode':DEMO_CODE,'applications':[public(x) for x in apps],'deliveries':[public(x) for x in deliveries],'users':[public(x) for x in users],'events':[public(x) for x in events]},cookie)
        except Exception:return self.send_json(503,{'message':'PostgreSQL 暫時無法讀取，請稍後重試。'},cookie)
        self.send_json(404,{'message':'not found'},cookie)
    def do_POST(self):
        path=self.route();session,cookie=owner_from(self)
        if not path.startswith('/api/03.08/'):return self.send_json(404,{'message':'not found'},cookie)
        try:data=self.body()
        except Exception:return self.send_json(400,{'message':'要求內容格式不正確。'},cookie)
        try:
            with psycopg.connect(**DB,row_factory=dict_row) as con:
                ensure_session(con,session)
                if path=='/api/03.08/register':return self.register(con,session,data,cookie)
                if path=='/api/03.08/login':return self.login(con,session,data,cookie)
                if path=='/api/03.08/demo/scenarios':return self.seed_scenarios(con,session,cookie)
                match=re.fullmatch(r'/api/03\.08/deliveries/(\d+)/(verify|resend|expire)',path)
                if match:return self.delivery_action(con,session,int(match.group(1)),match.group(2),data,cookie)
                match=re.fullmatch(r'/api/03\.08/applications/(\d+)/review',path)
                if match:return self.review(con,session,int(match.group(1)),data,cookie)
                match=re.fullmatch(r'/api/03\.08/users/(\d+)/status',path)
                if match:return self.user_status(con,session,int(match.group(1)),data,cookie)
        except psycopg.errors.UniqueViolation:return self.send_json(409,{'message':'此帳號已有申請，未建立重複資料。','errors':{'username':'帳號已存在於目前教學沙盒。'}},cookie)
        except Exception as exc:
            print(f'ERROR {type(exc).__name__}: {exc}',flush=True);return self.send_json(503,{'message':'伺服器或 PostgreSQL 操作失敗，未宣稱成功。'},cookie)
        self.send_json(404,{'message':'not found'},cookie)
    def register(self,con,session,data,cookie):
        clean,errors=validate_registration(data)
        if errors:return self.send_json(422,{'message':'請修正欄位錯誤，已輸入內容會保留。','errors':errors},cookie)
        row=con.execute('''INSERT INTO module_0308_applications(session_id,username,full_name,email,phone,organization,title,requested_role,purpose,contact_method,password_hash) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',(session,clean['username'],clean['full_name'],clean['email'],clean['phone'],clean['organization'],clean['title'],clean['requested_role'],clean['purpose'],clean['contact_method'],password_hash(clean['password']))).fetchone()
        destination=clean['email'] if clean['contact_method']=='email' else clean['phone'];delivery_status='simulated_failed' if clean['simulate_failure'] else 'simulated_ready';now=utcnow();delivery=con.execute('''INSERT INTO module_0308_deliveries(session_id,application_id,channel,destination_masked,delivery_status,code_hash,expires_at,resend_available_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',(session,row['id'],clean['contact_method'],mask_destination(clean['contact_method'],destination),delivery_status,code_hash(row['id']),now+timedelta(minutes=CODE_TTL_MINUTES),now+timedelta(seconds=RESEND_SECONDS))).fetchone()
        audit(con,session,'application',row['id'],'registration_created',{'status':'pending_contact'});audit(con,session,'delivery',delivery['id'],'simulation_failed' if clean['simulate_failure'] else 'simulation_ready',{'channel':clean['contact_method'],'realMessageSent':False})
        return self.send_json(201,{'message':'已建立待聯絡驗證申請；尚未啟用登入。','application':public(row),'delivery':public(delivery),'demoCode':DEMO_CODE,'realMessageSent':False},cookie)
    def delivery_action(self,con,session,did,action,data,cookie):
        delivery=con.execute('SELECT * FROM module_0308_deliveries WHERE id=%s AND session_id=%s FOR UPDATE',(did,session)).fetchone()
        if not delivery:return self.send_json(404,{'message':'找不到模擬寄送資料。'},cookie)
        now=utcnow()
        if action=='expire':
            row=con.execute("UPDATE module_0308_deliveries SET expires_at=NOW()-INTERVAL '1 minute',delivery_status='expired' WHERE id=%s RETURNING *",(did,)).fetchone();audit(con,session,'delivery',did,'demo_expired');return self.send_json(200,{'message':'已在教學沙盒模擬驗證碼過期。','delivery':public(row)},cookie)
        if action=='resend':
            if delivery['resend_available_at']>now:return self.send_json(429,{'message':'重送過於頻繁，請稍後再試。','retryAfterSeconds':max(1,int((delivery['resend_available_at']-now).total_seconds()))},cookie)
            con.execute("UPDATE module_0308_deliveries SET delivery_status='superseded' WHERE application_id=%s AND delivery_status IN ('simulated_ready','simulated_failed','expired')",(delivery['application_id'],));newrow=con.execute('''INSERT INTO module_0308_deliveries(session_id,application_id,channel,destination_masked,delivery_status,code_hash,expires_at,resend_available_at) VALUES(%s,%s,%s,%s,'simulated_ready',%s,%s,%s) RETURNING *''',(session,delivery['application_id'],delivery['channel'],delivery['destination_masked'],code_hash(delivery['application_id']),now+timedelta(minutes=CODE_TTL_MINUTES),now+timedelta(seconds=RESEND_SECONDS))).fetchone();audit(con,session,'delivery',newrow['id'],'simulation_resent',{'realMessageSent':False});return self.send_json(201,{'message':'已建立新的模擬寄送，未發送真實訊息。','delivery':public(newrow),'demoCode':DEMO_CODE,'realMessageSent':False},cookie)
        if delivery['delivery_status']=='simulated_failed':return self.send_json(409,{'message':'此筆模擬寄送失敗，請等待限流後重送。'},cookie)
        if delivery['expires_at']<=now or delivery['delivery_status']=='expired':return self.send_json(410,{'message':'驗證碼已過期，請重新模擬寄送。'},cookie)
        if delivery['attempts']>=MAX_ATTEMPTS:return self.send_json(429,{'message':'錯誤次數已達上限，請重新模擬寄送。'},cookie)
        if not code_ok(delivery['application_id'],str(data.get('code','')),delivery['code_hash']):
            con.execute('UPDATE module_0308_deliveries SET attempts=attempts+1 WHERE id=%s',(did,));audit(con,session,'delivery',did,'verification_code_rejected',{'attempt':delivery['attempts']+1});return self.send_json(422,{'message':f'驗證碼錯誤，尚可嘗試 {MAX_ATTEMPTS-delivery["attempts"]-1} 次。','errors':{'code':'驗證碼不正確。'}},cookie)
        con.execute("UPDATE module_0308_deliveries SET delivery_status='verified',verified_at=NOW() WHERE id=%s",(did,));app=con.execute("UPDATE module_0308_applications SET status='pending_review',version=version+1,updated_at=NOW() WHERE id=%s AND session_id=%s RETURNING *",(delivery['application_id'],session)).fetchone();audit(con,session,'application',app['id'],'contact_verified',{'channel':delivery['channel']});return self.send_json(200,{'message':'聯絡方式已完成模擬驗證，申請已轉入待審核。','application':public(app)},cookie)
    def review(self,con,session,aid,data,cookie):
        app=con.execute('SELECT * FROM module_0308_applications WHERE id=%s AND session_id=%s FOR UPDATE',(aid,session)).fetchone()
        if not app:return self.send_json(404,{'message':'找不到申請。'},cookie)
        if int(data.get('version',0))!=app['version']:return self.send_json(409,{'message':'版本衝突，請重新讀取後再操作。'},cookie)
        action=data.get('action');mapping={'approve':'approved','changes':'changes_requested','reject':'rejected'}
        if action not in mapping:return self.send_json(422,{'message':'審核動作不合法。'},cookie)
        if app['status']!='pending_review':return self.send_json(409,{'message':'只有待審核申請可執行此操作。'},cookie)
        updated=con.execute('UPDATE module_0308_applications SET status=%s,version=version+1,updated_at=NOW() WHERE id=%s RETURNING *',(mapping[action],aid)).fetchone()
        if action=='approve':con.execute('''INSERT INTO module_0308_users(session_id,application_id,username,display_name,sandbox_role,password_hash) VALUES(%s,%s,%s,%s,%s,%s)''',(session,aid,app['username'],app['full_name'],app['requested_role'],app['password_hash']))
        audit(con,session,'application',aid,f'review_{action}',{'sandboxAdmin':True,'formalPermissionGranted':False});return self.send_json(200,{'message':{'approve':'教學管理者已核准，沙盒使用者現在可模擬登入。','changes':'已退回補件，未建立使用者。','reject':'已拒絕申請，未建立使用者。'}[action],'application':public(updated)},cookie)
    def user_status(self,con,session,uid,data,cookie):
        status=data.get('status')
        if status not in ('active','disabled'):return self.send_json(422,{'message':'使用者狀態不合法。'},cookie)
        row=con.execute('UPDATE module_0308_users SET user_status=%s,version=version+1,updated_at=NOW() WHERE id=%s AND session_id=%s AND version=%s RETURNING *',(status,uid,session,int(data.get('version',0)))).fetchone()
        if not row:return self.send_json(409,{'message':'權限不足、資料不存在或版本衝突。'},cookie)
        audit(con,session,'user',uid,f'user_{status}',{'sandboxOnly':True});return self.send_json(200,{'message':'沙盒使用者狀態已更新。','user':public(row)},cookie)
    def login(self,con,session,data,cookie):
        username=str(data.get('username','')).strip();password=str(data.get('password',''));row=con.execute('SELECT * FROM module_0308_users WHERE session_id=%s AND LOWER(username)=LOWER(%s)',(session,username)).fetchone()
        if not row or not password_ok(password,row['password_hash']):audit(con,session,'login',None,'login_rejected',{'reason':'credentials'});return self.send_json(401,{'message':'帳號或密碼不正確，登入被拒。'},cookie)
        if row['user_status']!='active':audit(con,session,'user',row['id'],'login_rejected',{'reason':'disabled'});return self.send_json(403,{'message':'此沙盒使用者已停用，登入被拒。'},cookie)
        audit(con,session,'user',row['id'],'login_succeeded',{'sandboxOnly':True});return self.send_json(200,{'message':'模擬登入成功；未建立正式登入工作階段。','user':public(row),'formalLogin':False},cookie)
    def seed_scenarios(self,con,session,cookie):
        con.execute('DELETE FROM module_0308_audit_events WHERE session_id=%s',(session,));con.execute('DELETE FROM module_0308_users WHERE session_id=%s',(session,));con.execute('DELETE FROM module_0308_applications WHERE session_id=%s',(session,))
        scenarios=[('demo.success','成功流程','approved'),('demo.wrong','錯碼測試','pending_contact'),('demo.expired','過期測試','pending_contact'),('demo.changes','退回補件','changes_requested'),('demo.rejected','拒絕案例','rejected'),('demo.disabled','停用案例','approved')]
        for index,(username,name,status) in enumerate(scenarios):
            pwd=password_hash('DemoPass123');app=con.execute('''INSERT INTO module_0308_applications(session_id,username,full_name,email,phone,organization,title,requested_role,purpose,contact_method,password_hash,status) VALUES(%s,%s,%s,%s,%s,'AI-DEMO 虛構學系','學生','student','課程教學驗收','email',%s,%s) RETURNING *''',(session,username,name,f'{username}@example.invalid',f'09120000{index:02d}',pwd,status)).fetchone();now=utcnow();delivery_status='expired' if username=='demo.expired' else ('verified' if status!='pending_contact' else 'simulated_ready');attempts=1 if username=='demo.wrong' else 0;con.execute('''INSERT INTO module_0308_deliveries(session_id,application_id,channel,destination_masked,delivery_status,code_hash,expires_at,attempts,resend_available_at,verified_at) VALUES(%s,%s,'email',%s,%s,%s,%s,%s,%s,%s)''',(session,app['id'],mask_destination('email',f'{username}@example.invalid'),delivery_status,code_hash(app['id']),now-timedelta(minutes=1) if username=='demo.expired' else now+timedelta(minutes=10),attempts,now-timedelta(seconds=1),now if delivery_status=='verified' else None))
            if status=='approved':con.execute('''INSERT INTO module_0308_users(session_id,application_id,username,display_name,sandbox_role,password_hash,user_status) VALUES(%s,%s,%s,%s,'student',%s,%s)''',(session,app['id'],username,name,pwd,'disabled' if username=='demo.disabled' else 'active'))
            audit(con,session,'application',app['id'],'demo_scenario_created',{'scenario':name})
        return self.send_json(201,{'message':'已建立六種教學驗收情境，全部使用 example.invalid 與 Demo 手機。','demoCode':DEMO_CODE},cookie)
    def log_message(self,fmt,*args):print(f'{self.client_address[0]} {fmt%args}',flush=True)

if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',8000),Handler).serve_forever()
