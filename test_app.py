import unittest
import json
import os
import tempfile
from app import create_app
from database.db import init_db, get_db
from models.user import create_user, authenticate_user, get_user_by_username
from models.conversation import get_or_create_direct_conversation, create_group_conversation, get_user_conversations
from models.message import create_message, edit_message, delete_message, toggle_reaction, search_messages

class ConnectlyTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app()
        self.app.config['DATABASE_PATH'] = self.db_path
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret'
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db(self.app)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_user_registration_and_login(self):
        with self.app.app_context():
            # 1. Register User
            user = create_user(
                name="Test Alice",
                username="alice",
                email="alice@test.com",
                password="Password123!"
            )
            self.assertEqual(user['name'], "Test Alice")
            self.assertEqual(user['username'], "alice")

            # 2. Authenticate
            auth_user = authenticate_user("alice", "Password123!")
            self.assertIsNotNone(auth_user)
            self.assertEqual(auth_user['id'], user['id'])

            # 3. Test duplicate registration prevention
            with self.assertRaises(ValueError):
                create_user("Alice Duplicate", "alice", "alice2@test.com", "Password123!")

    def test_direct_and_group_conversations(self):
        with self.app.app_context():
            u1 = create_user("Alice", "alice", "alice@test.com", "Password123!")
            u2 = create_user("Bob", "bob", "bob@test.com", "Password123!")
            u3 = create_user("Charlie", "charlie", "charlie@test.com", "Password123!")

            # Direct conversation
            c1_id = get_or_create_direct_conversation(u1['id'], u2['id'])
            # Calling again should retrieve the same conversation
            c2_id = get_or_create_direct_conversation(u2['id'], u1['id'])
            self.assertEqual(c1_id, c2_id)

            # Group conversation
            g_id = create_group_conversation(
                created_by=u1['id'],
                name="Dev Team 🚀",
                member_ids=[u1['id'], u2['id'], u3['id']],
                description="Engineering channel"
            )
            self.assertTrue(g_id > 0)

            # Check user conversations list
            convs = get_user_conversations(u1['id'])
            self.assertEqual(len(convs), 2)

    def test_messaging_reactions_and_search(self):
        with self.app.app_context():
            u1 = create_user("Alice", "alice", "alice@test.com", "Password123!")
            u2 = create_user("Bob", "bob", "bob@test.com", "Password123!")
            c_id = get_or_create_direct_conversation(u1['id'], u2['id'])

            # 1. Send Message
            msg = create_message(
                conversation_id=c_id,
                sender_id=u1['id'],
                message="Hello Bob! Welcome to Connectly."
            )
            self.assertEqual(msg['message'], "Hello Bob! Welcome to Connectly.")
            self.assertEqual(msg['sender_name'], "Alice")

            # 2. Reply Message
            reply = create_message(
                conversation_id=c_id,
                sender_id=u2['id'],
                message="Hey Alice, real-time messaging is awesome!",
                reply_to=msg['id']
            )
            self.assertEqual(reply['reply_to'], msg['id'])
            self.assertIsNotNone(reply['reply_info'])

            # 3. Add & Toggle Reaction
            rx_result = toggle_reaction(msg['id'], u2['id'], "❤️")
            self.assertEqual(rx_result['action'], 'added')
            self.assertEqual(len(rx_result['reactions']), 1)

            # 4. Edit Message
            edited = edit_message(msg['id'], u1['id'], "Hello Bob! Welcome to Connectly 2.0.")
            self.assertEqual(edited['message'], "Hello Bob! Welcome to Connectly 2.0.")
            self.assertIsNotNone(edited['edited_at'])

            # 5. Search Messages
            search_res = search_messages("Connectly", u1['id'])
            self.assertTrue(len(search_res) >= 1)

            # 6. Delete Message
            del_msg = delete_message(msg['id'], u1['id'])
            self.assertEqual(del_msg['is_deleted'], 1)

    def test_http_routes(self):
        # 1. Landing Page
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Connectly', res.data)
        self.assertIn(b'Connect. Chat. Share.', res.data)

        # 2. Register API
        res = self.client.post('/register', json={
            'name': 'API User',
            'username': 'apiuser',
            'email': 'apiuser@connectly.app',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # 3. Login API
        res = self.client.post('/login', json={
            'username': 'apiuser',
            'password': 'Password123!'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # 4. Authenticated API me
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['user']['username'], 'apiuser')

if __name__ == '__main__':
    unittest.main()
