import unittest
from validation import validate_registration,password_hash,password_ok

class ValidationTests(unittest.TestCase):
    def payload(self):
        return {'username':'demo.student','full_name':'虛構學生','email':'student@example.invalid','phone':'0912000037','organization':'AI-DEMO 虛構學系','title':'學生','requested_role':'student','purpose':'課程教學驗收','contact_method':'email','password':'DemoPass123','password_confirm':'DemoPass123','consent':True}
    def test_valid_demo(self):
        _,errors=validate_registration(self.payload());self.assertEqual(errors,{})
    def test_contact_and_password_errors(self):
        data=self.payload();data.update(contact_method='sms',phone='',password='abcdefgh',password_confirm='other')
        _,errors=validate_registration(data);self.assertIn('phone',errors);self.assertIn('password',errors);self.assertIn('password_confirm',errors)
    def test_scrypt_hash(self):
        encoded=password_hash('DemoPass123');self.assertTrue(encoded.startswith('scrypt$'));self.assertTrue(password_ok('DemoPass123',encoded));self.assertFalse(password_ok('wrong',encoded));self.assertNotIn('DemoPass123',encoded)

if __name__=='__main__':unittest.main()
