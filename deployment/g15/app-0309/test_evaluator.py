import unittest
from datetime import datetime,timedelta,timezone
from evaluator import evaluate

class EvaluatorTest(unittest.TestCase):
    def setUp(self):
        self.user={'id':1,'department_id':10,'clearance':2,'enabled':True}
        self.program={'id':20,'enabled':True}
        self.record={'id':30,'owner_user_id':1,'department_id':10,'data_group_id':40,'classification':2}
        base={'subject_type':'user','subject_id':1,'resource_type':'program','resource_id':20,'effect':'allow','scope':'all','scope_ref':None,'max_classification':4,'active':True,'starts_at':None,'ends_at':None,'deleted_at':None}
        self.enter={**base,'name':'enter','action':'enter'};self.view={**base,'name':'view','action':'view','scope':'self'}
    def run_eval(self,action='view',rules=None,record=None):
        return evaluate(self.user,self.program,self.record if record is None else record,action,rules or [self.enter,self.view],set(),set(),{10},set())
    def test_dual_gate_and_self_scope(self):self.assertTrue(self.run_eval()['allowed'])
    def test_missing_enter_denied(self):self.assertIn('enter',self.run_eval(rules=[self.view])['reason'])
    def test_deny_precedence(self):
        deny={**self.view,'name':'deny','effect':'deny'};self.assertFalse(self.run_eval(rules=[self.enter,self.view,deny])['allowed'])
    def test_clearance_cannot_be_bypassed(self):
        high={**self.record,'classification':4};self.assertIn('clearance',self.run_eval(record=high)['reason'])
    def test_self_approval_denied(self):self.assertIn('自己',self.run_eval('approve',[self.enter,{**self.view,'action':'approve'}])['reason'])
    def test_expired_rule_ignored(self):
        past=datetime.now(timezone.utc)-timedelta(days=1);expired={**self.view,'ends_at':past};self.assertFalse(self.run_eval(rules=[self.enter,expired])['allowed'])
    def test_disabled_actor_revoked(self):
        self.user['enabled']=False;self.assertFalse(self.run_eval()['allowed'])
    def test_department_tree_scope(self):
        child={**self.record,'owner_user_id':9,'department_id':11};rule={**self.view,'scope':'department_tree'}
        result=evaluate(self.user,self.program,child,'view',[self.enter,rule],set(),set(),{10,11},set())
        self.assertTrue(result['allowed'])
    def test_data_group_requires_membership(self):
        shared={**self.view,'scope':'data_group','scope_ref':40};other={**self.record,'owner_user_id':9}
        denied=evaluate(self.user,self.program,other,'view',[self.enter,shared],set(),set(),{10},set())
        allowed=evaluate(self.user,self.program,other,'view',[self.enter,shared],set(),set(),{10},{40})
        self.assertFalse(denied['allowed']);self.assertTrue(allowed['allowed'])

if __name__=='__main__':unittest.main()
