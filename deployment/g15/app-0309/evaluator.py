from datetime import datetime, timezone

def active_rule(rule, now=None):
    now=now or datetime.now(timezone.utc)
    return bool(rule.get('active',True) and not rule.get('deleted_at') and
      (not rule.get('starts_at') or rule['starts_at']<=now) and
      (not rule.get('ends_at') or rule['ends_at']>now))

def subject_matches(rule, actor, permission_group_ids):
    return (rule['subject_type']=='user' and rule['subject_id']==actor['id']) or (
      rule['subject_type']=='permission_group' and rule['subject_id'] in permission_group_ids)

def resource_matches(rule, program, program_group_ids):
    return (rule['resource_type']=='program' and rule['resource_id']==program['id']) or (
      rule['resource_type']=='program_group' and rule['resource_id'] in program_group_ids)

def scope_matches(rule, actor, record, department_descendants, actor_data_group_ids):
    if record is None:return True
    scope=rule['scope']
    if scope=='all':return True
    if scope=='self':return record['owner_user_id']==actor['id']
    if scope=='department':return record['department_id']==actor['department_id']
    if scope=='department_tree':return record['department_id'] in department_descendants
    if scope=='data_group':return record.get('data_group_id')==rule.get('scope_ref') and rule.get('scope_ref') in actor_data_group_ids
    return False

def evaluate(actor,program,record,action,rules,permission_group_ids,program_group_ids,department_descendants,actor_data_group_ids,now=None):
    trace=[]
    if not actor or not actor.get('enabled') or actor.get('deleted_at'):return {'allowed':False,'reason':'教學使用者未啟用。','trace':trace}
    if not program or not program.get('enabled') or program.get('deleted_at'):return {'allowed':False,'reason':'程式未啟用。','trace':trace}
    if record and record['classification']>actor['clearance']:return {'allowed':False,'reason':'資料分級超過使用者 clearance。','trace':trace}
    if action=='approve' and record and record['owner_user_id']==actor['id']:return {'allowed':False,'reason':'禁止核准自己的資料。','trace':trace}
    applicable=[r for r in rules if active_rule(r,now) and subject_matches(r,actor,permission_group_ids) and resource_matches(r,program,program_group_ids)]
    enter=[r for r in applicable if r['action']=='enter']
    if any(r['effect']=='deny' for r in enter):return {'allowed':False,'reason':'enter 明確拒絕優先。','trace':[r['name'] for r in enter]}
    if not any(r['effect']=='allow' for r in enter):return {'allowed':False,'reason':'缺少 enter 進入權限。','trace':[r['name'] for r in enter]}
    action_rules=[r for r in applicable if r['action']==action and scope_matches(r,actor,record,department_descendants,actor_data_group_ids) and (not record or record['classification']<=r['max_classification'])]
    trace=[r['name'] for r in action_rules]
    if any(r['effect']=='deny' for r in action_rules):return {'allowed':False,'reason':'明確 deny 優先於 allow。','trace':trace}
    if not any(r['effect']=='allow' for r in action_rules):return {'allowed':False,'reason':'沒有同時符合動作與資料範圍的允許規則。','trace':trace}
    return {'allowed':True,'reason':'操作權限與資料範圍同時通過。','trace':trace}
