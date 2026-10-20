import hashlib,hmac,json,os,re,secrets,sys
from datetime import date
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from http import cookies
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

GROUP_NAME=os.environ['GROUP_NAME'];SECRET=os.environ['APP_SECRET'].encode();DB=dict(host=os.environ['POSTGRES_HOST'],port=os.environ['POSTGRES_PORT'],dbname=os.environ['POSTGRES_DB'],user=os.environ['POSTGRES_USER'],password=os.environ['POSTGRES_PASSWORD'])
FIELDS=['application_no','application_name','department','owner_name','email','phone','category','priority','status','start_date','end_date','currency','budget','tags','meeting_method','meeting_value','discount_percent','tax_rate','billing_type','invoice_title','tax_id','details','subtotal','discount_amount','tax_amount','total','notes','confirmed']
Q=Decimal('0.01')
def dec(v):
    try:return Decimal(str(v)).quantize(Q,rounding=ROUND_HALF_UP)
    except (InvalidOperation,ValueError,TypeError):return None
def encode(value):
    if isinstance(value,(Decimal,date)):return str(value)
    raise TypeError
def validate(data):
    e={}; req=['application_no','application_name','department','owner_name','email','phone','category','priority','status','start_date','end_date','currency','meeting_method','meeting_value','billing_type']
    for k in req:
        if not str(data.get(k,'')).strip():e[k]='此欄位為必填。'
    no=str(data.get('application_no','')).upper()
    if not re.fullmatch(r'[A-Z0-9-]{4,32}',no):e['application_no']='編號需為 4～32 個大寫英文字母、數字或連字號。'
    name=str(data.get('application_name',''));owner=str(data.get('owner_name',''))
    if not 4<=len(name)<=120:e['application_name']='名稱需為 4～120 字。'
    if not 2<=len(owner)<=40:e['owner_name']='負責人需為 2～40 字。'
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',str(data.get('email',''))):e['email']='Email 格式不正確。'
    phone=re.sub(r'[\s()-]','',str(data.get('phone','')))
    if not re.fullmatch(r'(?:\+886|0)(?:2\d{8}|[3-8]\d{8}|9\d{8})',phone):e['phone']='台灣電話格式不正確。'
    try:start=date.fromisoformat(str(data.get('start_date')))
    except (ValueError,TypeError):start=None;e['start_date']='開始日期不合法。'
    try:end=date.fromisoformat(str(data.get('end_date')))
    except (ValueError,TypeError):end=None;e['end_date']='結束日期不合法。'
    if start and end and end<start:e['end_date']='結束日期不可早於開始日期。'
    budget=dec(data.get('budget'));discount=dec(data.get('discount_percent'));tax=data.get('tax_rate');items=data.get('details')
    if budget is None or not Decimal('0')<=budget<=Decimal('10000000'):e['budget']='預算需介於 0～10,000,000。'
    if discount is None or not Decimal('0')<=discount<=Decimal('50'):e['discount_percent']='折扣需介於 0～50%。'
    try:tax=int(tax)
    except (ValueError,TypeError):tax=-1
    if tax not in (0,5,10):e['tax_rate']='稅率只能是 0、5 或 10。'
    allowed={'priority':{'一般','重要','緊急'},'status':{'草稿','審核中','已核准','已退回'},'currency':{'TWD','USD','JPY'},'meeting_method':{'online','onsite'},'billing_type':{'company','personal'}}
    for key,values in allowed.items():
        if data.get(key) not in values:e[key]='選項不合法。'
    if not isinstance(data.get('tags',[]),list):e['tags']='標籤格式不正確。';data['tags']=[]
    if not isinstance(items,list) or not 1<=len(items)<=12:e['details']='明細需為 1～12 筆。';items=[]
    subtotal=Decimal('0')
    clean=[]
    for i,item in enumerate(items):
        if not isinstance(item,dict):e['details']=f'第 {i+1} 筆明細格式不正確。';continue
        desc=str(item.get('description','')).strip();price=dec(item.get('unit_price'))
        try:qty=int(item.get('quantity'));integer=str(item.get('quantity')).strip()==str(qty)
        except (ValueError,TypeError):qty=0;integer=False
        if not desc:e['details']=f'第 {i+1} 筆明細缺少說明。'
        if not integer or not 1<=qty<=9999:e['details']=f'第 {i+1} 筆數量需為 1～9,999 整數。'
        if price is None or not Decimal('0')<=price<=Decimal('1000000'):e['details']=f'第 {i+1} 筆單價需介於 0～1,000,000。';price=Decimal('0')
        subtotal+=qty*price;clean.append({'description':desc,'category':str(item.get('category','')),'quantity':qty,'unit_price':str(price)})
    discount_amount=(subtotal*(discount or Decimal('0'))/100).quantize(Q);taxable=subtotal-discount_amount;tax_amount=(taxable*tax/100).quantize(Q);total=(taxable+tax_amount).quantize(Q)
    if budget is not None and budget<total:e['budget']='預算不得小於總計。'
    method=data.get('meeting_method');meeting=str(data.get('meeting_value','')).strip()
    if method=='online' and not re.match(r'^https://',meeting,re.I):e['meeting_value']='線上會議必須使用 HTTPS 網址。'
    if method=='onsite' and not meeting:e['meeting_value']='實體會議必須填寫地點。'
    billing=data.get('billing_type')
    if billing=='company':
        if not str(data.get('invoice_title','')).strip():e['invoice_title']='公司請款需填發票抬頭。'
        if not re.fullmatch(r'\d{8}',str(data.get('tax_id',''))):e['tax_id']='統一編號需為 8 碼數字。'
    if len(str(data.get('notes','')))>2000:e['notes']='備註最多 2,000 字。'
    if data.get('confirmed') is not True:e['confirmed']='儲存前必須勾選確認。'
    data=dict(data);data.update(application_no=no,budget=budget,discount_percent=discount,tax_rate=tax,details=clean,subtotal=subtotal.quantize(Q),discount_amount=discount_amount,tax_amount=tax_amount,total=total)
    if billing=='personal':data.update(invoice_title='',tax_id='')
    return data,e
def owner_from(handler):
    jar=cookies.SimpleCookie(handler.headers.get('Cookie',''));raw=jar.get('ai_demo_0305')
    if raw:
        try:
            ident,sig=raw.value.split('.',1);expected=hmac.new(SECRET,ident.encode(),hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig,expected) and re.fullmatch(r'[0-9a-f]{32}',ident):return ident,None
        except ValueError:pass
    ident=secrets.token_hex(16);sig=hmac.new(SECRET,ident.encode(),hashlib.sha256).hexdigest();return ident,f'ai_demo_0305={ident}.{sig}; Path=/api/03.05; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000'
def public(row):
    result=dict(row);result['tags']=result.get('tags') or [];result['details']=result.get('details') or []
    for k,v in list(result.items()):
        if isinstance(v,Decimal):result[k]=float(v)
        elif isinstance(v,date):result[k]=v.isoformat()
    result.pop('owner_session',None);return result
class Handler(BaseHTTPRequestHandler):
    def send_json(self,status,payload,cookie=None):
        body=json.dumps(payload,ensure_ascii=False,default=encode).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)))
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(body)
    def body(self):
        size=int(self.headers.get('Content-Length','0'))
        if size>300000:raise ValueError('payload too large')
        return json.loads(self.rfile.read(size) or b'{}')
    def route(self):return urlparse(self.path).path
    def do_GET(self):
        path=self.route()
        if path=='/healthz':return self.send_json(200,{'status':'ok','group':GROUP_NAME,'python':sys.version.split()[0],'postgres_host':os.environ['POSTGRES_HOST']})
        if not path.startswith('/api/03.05/'):return self.send_json(404,{'detail':'not found'})
        owner,cookie=owner_from(self)
        try:
            with psycopg.connect(**DB,row_factory=dict_row) as con:
                if path=='/api/03.05/applications':
                    rows=con.execute('SELECT * FROM module_0305_applications WHERE owner_session=%s ORDER BY updated_at DESC',(owner,)).fetchall();return self.send_json(200,{'items':[public(x) for x in rows]},cookie)
                match=re.fullmatch(r'/api/03\.05/applications/(\d+)',path)
                if match:
                    row=con.execute('SELECT * FROM module_0305_applications WHERE id=%s AND owner_session=%s',(int(match.group(1)),owner)).fetchone();return self.send_json(200,public(row),cookie) if row else self.send_json(404,{'message':'找不到申請資料。'},cookie)
        except Exception as exc:return self.send_json(503,{'message':'資料庫暫時無法讀取，請稍後重試。'},cookie)
        self.send_json(404,{'message':'not found'},cookie)
    def do_POST(self):self.write_action('POST')
    def do_PUT(self):self.write_action('PUT')
    def do_DELETE(self):self.write_action('DELETE')
    def write_action(self,method):
        path=self.route();owner,cookie=owner_from(self)
        if not path.startswith('/api/03.05/'):return self.send_json(404,{'message':'not found'},cookie)
        try:data=self.body()
        except Exception:return self.send_json(400,{'message':'要求內容格式不正確。'},cookie)
        try:
            with psycopg.connect(**DB,row_factory=dict_row) as con:
                if method=='POST' and path=='/api/03.05/demo':
                    created=0
                    for i in range(1,11):
                        d=demo(i);d,e=validate(d)
                        cols=','.join(FIELDS);marks=','.join(['%s']*len(FIELDS));values=[Jsonb(d[x]) if x in ('tags','details') else d[x] for x in FIELDS]
                        result=con.execute(f'INSERT INTO module_0305_applications(owner_session,{cols}) VALUES(%s,{marks}) ON CONFLICT(owner_session,application_no) DO NOTHING RETURNING id',[owner,*values]).fetchone();created+=bool(result)
                    return self.send_json(201,{'created':created},cookie)
                match=re.fullmatch(r'/api/03\.05/applications/(\d+)',path);rid=int(match.group(1)) if match else None
                if method=='DELETE' and rid:
                    row=con.execute('DELETE FROM module_0305_applications WHERE id=%s AND owner_session=%s AND version=%s RETURNING id',(rid,owner,int(data.get('version',0)))).fetchone();return self.send_json(200,{'deleted':True},cookie) if row else self.send_json(409,{'message':'資料版本衝突，未執行刪除。'},cookie)
                clean,errors=validate(data)
                if errors:return self.send_json(422,{'message':'請修正輸入欄位。','errors':errors},cookie)
                vals=[Jsonb(clean[x]) if x in ('tags','details') else clean[x] for x in FIELDS]
                if method=='POST' and path=='/api/03.05/applications':
                    cols=','.join(FIELDS);marks=','.join(['%s']*len(FIELDS));row=con.execute(f'INSERT INTO module_0305_applications(owner_session,{cols}) VALUES(%s,{marks}) RETURNING *',[owner,*vals]).fetchone();return self.send_json(201,public(row),cookie)
                if method=='PUT' and rid:
                    sets=','.join(f'{x}=%s' for x in FIELDS);row=con.execute(f'UPDATE module_0305_applications SET {sets},version=version+1,updated_at=NOW() WHERE id=%s AND owner_session=%s AND version=%s RETURNING *',[*vals,rid,owner,int(data.get('version',0))]).fetchone();return self.send_json(200,public(row),cookie) if row else self.send_json(409,{'message':'資料已被其他操作更新，內容未覆蓋。'},cookie)
        except psycopg.errors.UniqueViolation:return self.send_json(409,{'message':'申請編號已存在，內容未儲存。','errors':{'application_no':'此編號已存在。'}},cookie)
        except Exception as exc:return self.send_json(503,{'message':'伺服器或資料庫操作失敗，未宣稱成功。'},cookie)
        self.send_json(404,{'message':'not found'},cookie)
    def log_message(self,fmt,*args):print(f'{self.client_address[0]} {fmt%args}',flush=True)
def demo(i):
    return {'application_no':f'DEMO-{i:04d}','application_name':f'虛構專案申請 {i:02d}','department':['資訊部','行銷部','營運部'][i%3],'owner_name':['林沛安','陳品妤','王奕辰'][i%3],'email':f'demo{i:02d}@example.com','phone':'0912345678','category':'系統建置','priority':'一般','status':'草稿','start_date':'2026-10-20','end_date':'2026-11-20','currency':'TWD','budget':200000,'tags':['年度計畫'],'meeting_method':'online','meeting_value':'https://example.com/demo','discount_percent':5,'tax_rate':5,'billing_type':'company','invoice_title':'AI-DEMO 虛構公司','tax_id':'12345678','details':[{'description':'虛構服務項目','category':'服務','quantity':1,'unit_price':100000}],'notes':'本資料為虛構 Demo。','confirmed':True}
if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',8000),Handler).serve_forever()
