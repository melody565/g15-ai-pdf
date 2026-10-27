import hashlib,hmac,re,secrets

USERNAME_RE=re.compile(r'^[A-Za-z0-9._-]{4,32}$')
EMAIL_RE=re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PHONE_RE=re.compile(r'^(?:\+886|0)9\d{8}$')

def password_hash(value):
    salt=secrets.token_bytes(16)
    digest=hashlib.scrypt(value.encode(),salt=salt,n=16384,r=8,p=1)
    return f'scrypt$16384$8$1${salt.hex()}${digest.hex()}'

def password_ok(value,encoded):
    try:
        _,n,r,p,salt,digest=encoded.split('$')
        actual=hashlib.scrypt(value.encode(),salt=bytes.fromhex(salt),n=int(n),r=int(r),p=int(p))
        return hmac.compare_digest(actual.hex(),digest)
    except Exception:
        return False

def validate_registration(data):
    errors={};username=str(data.get('username','')).strip();name=str(data.get('full_name','')).strip();email=str(data.get('email','')).strip();phone=re.sub(r'[\s()-]','',str(data.get('phone','')));password=str(data.get('password',''));confirm=str(data.get('password_confirm',''));method=data.get('contact_method')
    for field in ('organization','title','requested_role','purpose'):
        if not str(data.get(field,'')).strip():errors[field]='此欄位為必填。'
    if not USERNAME_RE.fullmatch(username):errors['username']='帳號需為 4～32 個英數字及 . _ -。'
    if not 2<=len(name)<=60:errors['full_name']='姓名需為 2～60 字。'
    if method not in ('email','sms'):errors['contact_method']='請選擇 Email 或手機簡訊驗證。'
    if method=='email' and not EMAIL_RE.fullmatch(email):errors['email']='Email 為必填且格式需正確。'
    if method=='sms' and not PHONE_RE.fullmatch(phone):errors['phone']='手機為必填，請輸入臺灣手機格式。'
    if not 8<=len(password)<=128 or not re.search(r'[A-Za-z]',password) or not re.search(r'\d',password):errors['password']='密碼需為 8～128 字元且同時包含英文字母與數字。'
    if password!=confirm:errors['password_confirm']='兩次密碼不一致。'
    if data.get('consent') is not True:errors['consent']='請勾選同意教學沙盒說明。'
    clean={k:str(data.get(k,'')).strip() for k in ('username','full_name','email','organization','title','requested_role','purpose')};clean.update(phone=phone,contact_method=method,password=password,simulate_failure=data.get('simulate_failure') is True)
    return clean,errors
