from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings

from project.errors import ApiError, ErrorCode
from sign_videos import ai_client, services
from sign_videos.models import SignVideo


@override_settings(
    AI_SIGN_SERVER_BASE_URL='https://sign.example.test',
    AI_SIGN_TIMEOUT_SECONDS=10,
)
class SignVideoAiIntegrationTests(TestCase):
    def response(self, payload, status_code=200):
        response = Mock(status_code=status_code)
        response.json.return_value = payload
        return response

    @patch('sign_videos.ai_client.requests.post')
    def test_sentence_sequence_converts_relative_urls_and_syncs_db(self, post):
        post.return_value = self.response(
            {
                'items': [
                    {
                        'keyword': '화장실',
                        'video_url': '/media/sign_words/화장실/화장실_F.mp4',
                    },
                    {
                        'keyword': '약속',
                        'video_url': '/media/sign_words/약속/약속_F.mp4',
                    },
                ],
                'missing_keywords': [],
            }
        )

        result = services.build_sign_video_sequence_from_sentence(
            '화장실에서 약속이 있어요'
        )

        self.assertEqual(result['keywords'], ['화장실', '약속'])
        self.assertEqual(len(result['sequence']), 2)
        self.assertEqual(
            SignVideo.objects.get(keyword='화장실').external_url,
            'https://sign.example.test/media/sign_words/화장실/화장실_F.mp4',
        )
        post.assert_called_once_with(
            'https://sign.example.test/sign-sequence-from-sentence',
            json={'sentence': '화장실에서 약속이 있어요'},
            timeout=10,
        )

    @patch('sign_videos.ai_client.requests.post')
    def test_nested_sequence_response_is_supported(self, post):
        post.return_value = self.response(
            {
                'sequence': [
                    {
                        'position': 1,
                        'sign_video': {
                            'keyword': '친구',
                            'title': '친구',
                            'emoji': '👫',
                            'video_url': '/media/sign_words/친구/친구_F.mp4',
                        },
                    }
                ]
            }
        )

        result = services.build_sign_video_sequence_from_sentence('친구')

        self.assertEqual(result['keywords'], ['친구'])
        self.assertEqual(result['sequence'][0]['sign_video'].emoji, '👫')

    @patch('sign_videos.ai_client.requests.post')
    def test_missing_keyword_keeps_existing_404_contract(self, post):
        post.return_value = self.response(
            {'items': [], 'missing_keywords': ['없는단어']}
        )

        with self.assertRaises(ApiError) as raised:
            services.build_sign_video_sequence(['없는단어'])

        self.assertEqual(raised.exception.code, ErrorCode.SIGN_VIDEO_NOT_FOUND)

    @patch('sign_videos.ai_client.requests.post')
    def test_timeout_is_converted_to_api_error(self, post):
        post.side_effect = requests.Timeout

        with self.assertRaises(ApiError) as raised:
            ai_client.fetch_sequence_from_sentence('친구')

        self.assertEqual(raised.exception.code, ErrorCode.AI_TIMEOUT)

# Create your tests here.
