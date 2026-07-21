from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User, UserRole
from conversations.models import Conversation, ConversationParticipant, MessageType
from sign_videos.models import SignVideo


class SignVideoSequenceMessageTests(TestCase):
    """청인이 친 문장이 수어 시퀀스 메시지에 같이 실려 가는지 확인합니다.

    키워드로 쪼개면 조사·어순이 날아가서, 농인 화면 옆에서 같이 보고 있는 청인이
    자기가 뭘 보냈는지 알 수 없게 됩니다.
    """

    def setUp(self):
        self.hearing = User.objects.create_user(
            username='🦊🎈🌈', password='password', role=UserRole.HEARING_USER
        )
        self.sign = User.objects.create_user(
            username='🐶🍎⭐', password='1234', role=UserRole.SIGN_USER
        )

        self.conversation = Conversation.objects.create(
            title='테스트 대화', code='TEST01'
        )
        for user in (self.hearing, self.sign):
            ConversationParticipant.objects.create(
                conversation=self.conversation, user=user
            )

        self.bank = SignVideo.objects.create(keyword='은행', title='은행', emoji='🏦')
        self.receive = SignVideo.objects.create(
            keyword='받다', title='받다', emoji='🤲'
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.hearing)

    def sequence_for(self, keywords):
        videos = {'은행': self.bank, '받다': self.receive}
        return [
            {'position': index, 'sign_video': videos[keyword]}
            for index, keyword in enumerate(keywords, start=1)
        ]

    @patch('conversations.services.build_sign_video_sequence')
    def test_original_sentence_is_stored_and_returned(self, build):
        build.return_value = self.sequence_for(['은행', '받다'])

        response = self.client.post(
            f'/api/v1/conversations/{self.conversation.id}/messages/sign-video-sequence/',
            {'keywords': ['은행', '받다'], 'text': '은행에서 번호표 받으세요'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['type'], MessageType.SIGN_VIDEO_SEQUENCE)
        self.assertEqual(response.data['text'], '은행에서 번호표 받으세요')
        self.assertEqual(
            [item['sign_video']['emoji'] for item in response.data['sign_video_sequence']],
            ['🏦', '🤲'],
        )

    @patch('conversations.services.build_sign_video_sequence')
    def test_text_is_optional_for_directly_picked_keywords(self, build):
        build.return_value = self.sequence_for(['은행'])

        response = self.client.post(
            f'/api/v1/conversations/{self.conversation.id}/messages/sign-video-sequence/',
            {'keywords': ['은행']},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], '')

    @patch('conversations.services.build_sign_video_sequence')
    def test_conversation_preview_shows_the_original_sentence(self, build):
        build.return_value = self.sequence_for(['은행', '받다'])

        self.client.post(
            f'/api/v1/conversations/{self.conversation.id}/messages/sign-video-sequence/',
            {'keywords': ['은행', '받다'], 'text': '은행에서 번호표 받으세요'},
            format='json',
        )

        response = self.client.get('/api/v1/conversations/')

        self.assertEqual(
            response.data[0]['last_message_preview'],
            '🏦 🤲 은행에서 번호표 받으세요',
        )
