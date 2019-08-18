import unittest

import get5_test
from flask import url_for
from models import User, Team, Match, GameServer, MapStats, Season


class LeaderboardTests(get5_test.Get5Test):

    def test_render_pages_loggedin(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1
            self.assertEqual(self.app.get('/leaderboard').status_code, 200)
            self.assertEqual(self.app.get(
                '/leaderboard/season/1').status_code, 200)
            self.assertEqual(self.app.get(
                '/leaderboard/players').status_code, 200)
            self.assertEqual(self.app.get(
                '/leaderboard/season/1/players').status_code, 200)

    def test_render_pages_not_loggedin(self):
        self.assertEqual(self.app.get('/leaderboard').status_code, 200)
        self.assertEqual(self.app.get(
            '/leaderboard/season/1').status_code, 200)
        self.assertEqual(self.app.get('/leaderboard/players').status_code, 200)
        self.assertEqual(self.app.get(
            '/leaderboard/season/1/players').status_code, 200)

    def test_render_pages_not_found(self):
        self.assertEqual(self.app.get(
            '/leaderboard/season/2').status_code, 404)
        self.assertEqual(self.app.get(
            '/leaderboard/season/2/players').status_code, 404)

if __name__ == '__main__':
    unittest.main()
