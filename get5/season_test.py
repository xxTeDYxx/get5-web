import unittest

import get5_test
from flask import url_for
from datetime import datetime, timedelta, date
from models import User, Match, GameServer, MapStats, Season


class SeasonTests(get5_test.Get5Test):

    def test_render_pages_loggedin(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1
            self.assertEqual(self.app.get('/seasons').status_code, 200)
            self.assertEqual(self.app.get('/season/1').status_code, 200)

    def test_render_pages_not_loggedin(self):
        self.assertEqual(self.app.get('/seasons').status_code, 200)
        self.assertEqual(self.app.get('/season/1').status_code, 200)

    # Test trying to create a season
    def test_season_create(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1

            # Make sure we can render the match creation page
            response = c.get('/season/create')
            self.assertEqual(response.status_code, 200)

            # Fill in its form
            response = c.post('/season/create',
                              follow_redirects=False,
                              data={
                                  'user_id': 1,
                                  'season_title': 'TestSeasonTwo',
                                  'start_date': datetime.today().strftime('%m/%d/%Y'),
                                  'end_date': (datetime.today() + timedelta(days=1)).strftime('%m/%d/%Y'),
                              })
            self.assertEqual(response.status_code, 302)
        # Verify data was correctly given.
        season = Season.query.get(2)
        self.assertEqual(season.user_id, 1)
        self.assertEqual(season.name, 'TestSeasonTwo')
        self.assertEqual(season.start_date.strftime('%m/%d/%Y'),
                         (datetime.today().strftime('%m/%d/%Y')))
        self.assertEqual(season.end_date.strftime(
            '%m/%d/%Y'), (datetime.today() + timedelta(days=1)).strftime('%m/%d/%Y'))
    # Try creating a season with no start date given.

    def test_season_create_start_date_null(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1

            # Make sure we can render the match creation page
            response = c.get('/season/create')
            self.assertEqual(response.status_code, 200)

            # Fill in its form
            response = c.post('/season/create',
                              follow_redirects=False,
                              data={
                                  'user_id': 1,
                                  'season_title': 'TestSeasonTwo',
                                  'start_date': (datetime.today() + timedelta(days=1)).strftime('%m/%d/%Y'),
                                  'end_date': (datetime.today().strftime('%m/%d/%Y')),
                              })
            self.assertEqual(response.status_code, 200)
            self.assertIn(
                'End date must be greater than start date', response.data)

    # Try editing a season that doesn't belong to you.
    def test_season_edit_not_my_season(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 2

            # Make sure we can render the match creation page
            response = c.get('/season/1/edit')
            self.assertEqual(response.status_code, 400)

            self.assertIn('Not your season', response.data)

if __name__ == '__main__':
    unittest.main()
