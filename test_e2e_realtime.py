import unittest
import time
import os
from app import app, socketio
from database.db import init_db
from models.user import get_user_by_username
from models.conversation import get_or_create_direct_conversation

class RealtimeSocketIOTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        
        with self.app.app_context():
            init_db(self.app)
            
        self.client1 = socketio.test_client(self.app, flask_test_client=self.app.test_client())
        self.client2 = socketio.test_client(self.app, flask_test_client=self.app.test_client())

    def test_realtime_messaging_flow(self):
        with self.app.test_request_context():
            # Get users
            u_aarav = get_user_by_username('aarav')
            u_priya = get_user_by_username('priya')
            self.assertIsNotNone(u_aarav)
            self.assertIsNotNone(u_priya)

            conv_id = get_or_create_direct_conversation(u_aarav['id'], u_priya['id'])
            
            # Authenticate client 1 session
            with self.client1.flask_test_client.session_transaction() as sess:
                sess['user_id'] = u_aarav['id']
                sess['username'] = u_aarav['username']
                sess['name'] = u_aarav['name']

            # Authenticate client 2 session
            with self.client2.flask_test_client.session_transaction() as sess:
                sess['user_id'] = u_priya['id']
                sess['username'] = u_priya['username']
                sess['name'] = u_priya['name']

            # Connect clients
            c1 = socketio.test_client(self.app, flask_test_client=self.client1.flask_test_client)
            c2 = socketio.test_client(self.app, flask_test_client=self.client2.flask_test_client)
            self.assertTrue(c1.is_connected())
            self.assertTrue(c2.is_connected())

            # Both join conversation room
            c1.emit('join_conversation', {'conversation_id': conv_id})
            c2.emit('join_conversation', {'conversation_id': conv_id})

            # Client 1 types
            c1.emit('typing_start', {'conversation_id': conv_id})
            received_c2 = c2.get_received()
            typing_events = [e for e in received_c2 if e['name'] == 'user_typing']
            self.assertTrue(len(typing_events) >= 1)
            self.assertTrue(typing_events[0]['args'][0]['is_typing'])

            # Client 1 sends message
            c1.emit('send_message', {
                'conversation_id': conv_id,
                'message': 'Real-time test message via Socket.IO!'
            })

            # Check Client 2 receives new_message event
            received_c2 = c2.get_received()
            msg_events = [e for e in received_c2 if e['name'] == 'new_message']
            self.assertTrue(len(msg_events) >= 1)
            new_msg = msg_events[0]['args'][0]['message']
            self.assertEqual(new_msg['message'], 'Real-time test message via Socket.IO!')
            self.assertEqual(new_msg['sender_id'], u_aarav['id'])

            # Client 2 reacts with ❤️
            c2.emit('react_message', {
                'message_id': new_msg['id'],
                'conversation_id': conv_id,
                'reaction': '❤️'
            })

            received_c1 = c1.get_received()
            rx_events = [e for e in received_c1 if e['name'] == 'message_reaction_updated']
            self.assertTrue(len(rx_events) >= 1)

            c1.disconnect()
            c2.disconnect()

if __name__ == '__main__':
    unittest.main()
